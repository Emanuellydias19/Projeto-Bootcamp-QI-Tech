from datetime import date

from controllers.base_controller import BaseController
from dtos import TransacaoDTO
from errors import (
    InsufficientSaldoDisponivel,
    InsufficientSaldoReservado,
    InvalidPagoEm,
    NotFoundCobranca,
    NotFoundConta,
    NotFoundTransacao,
    NotLastRecebimento,
    ReusedIdempotencyKey,
    SaldoAboveMaximum,
    TransacaoNotEstornavel,
    ValorAboveDevido,
    ValorNotAboveTaxa,
)
from models import Conta, Lancamento, Transacao
from repositories import (
    CobrancaRepository,
    ContaRepository,
    LancamentoRepository,
    RecebimentoRepository,
    TransacaoRepository,
)
from utils.dates import today_in_sao_paulo
from utils.idempotency import hash_requisicao
from utils.imputacao import imputar
from utils.posicao_cobranca import calcular_posicao, data_do_ultimo_pagamento
from utils.taxa_administracao import calcular_taxa_pendente

NATUREZAS_DO_RESERVADO = ["condominio", "iptu"]
MAXIMUM_SALDO_CENTAVOS = 9007199254740991


class TransacaoController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.cobranca_repository = CobrancaRepository(self.context)
        self.conta_repository = ContaRepository(self.context)
        self.transacao_repository = TransacaoRepository(self.context)
        self.recebimento_repository = RecebimentoRepository(self.context)
        self.lancamento_repository = LancamentoRepository(self.context)

    def receber(self, cobranca_chave: str, recebimento_data: dict, chave_idempotencia: str) -> tuple:
        self.logger.debug("Registrando um recebimento")

        cobranca = self._get_or_raise(self.cobranca_repository, cobranca_chave, NotFoundCobranca)
        conta = self.conta_repository.get_by_id_for_update(cobranca.conta_id)
        self.cobranca_repository.refresh_itens(cobranca)

        hash_da_requisicao = hash_requisicao(Transacao.TIPO_RECEBIMENTO, cobranca_chave, recebimento_data)
        transacao_anterior = self._get_transacao_anterior(conta, chave_idempotencia, hash_da_requisicao)

        if transacao_anterior is not None:
            return transacao_anterior.resultado, False

        valor = recebimento_data["valor_centavos"]
        self._check_valor(valor)

        pago_em = self._parse_date_or_raise("pago_em", recebimento_data["pago_em"])
        pagamentos = self.lancamento_repository.list_pagamentos_da_cobranca(cobranca)
        self._check_pago_em(pago_em, pagamentos)

        posicao = calcular_posicao(cobranca, conta, pagamentos, pago_em)

        if valor > posicao["total_devido_na_data_centavos"]:
            raise ValorAboveDevido(valor, posicao["total_devido_na_data_centavos"])

        imputacao = imputar(valor, conta.politica.ordem_naturezas, posicao)
        self._check_teto_dos_saldos(conta, imputacao["rateio"])

        transacao = self.transacao_repository.create(
            conta, Transacao.TIPO_RECEBIMENTO, chave_idempotencia, hash_da_requisicao
        )
        self.recebimento_repository.create(transacao, cobranca, valor, pago_em)
        self._lancar(transacao, conta, imputacao["rateio"])

        resultado = TransacaoDTO.recebimento_to_dict(transacao, imputacao)
        self._guardar_resultado(transacao, resultado)

        self.session.commit()

        return resultado, True

    def pagar_encargo(self, conta_chave: str, encargo_data: dict, chave_idempotencia: str) -> tuple:
        self.logger.debug("Pagando um encargo com o saldo reservado")

        conta = self._get_for_update_or_raise(self.conta_repository, conta_chave, NotFoundConta)

        hash_da_requisicao = hash_requisicao(Transacao.TIPO_ENCARGO, conta_chave, encargo_data)
        transacao_anterior = self._get_transacao_anterior(conta, chave_idempotencia, hash_da_requisicao)

        if transacao_anterior is not None:
            return transacao_anterior.resultado, False

        natureza = encargo_data["natureza"]
        valor = encargo_data["valor_centavos"]
        self._check_valor(valor)

        reservado_da_natureza = self.lancamento_repository.sum_by_natureza(conta, natureza)

        if valor > reservado_da_natureza:
            raise InsufficientSaldoReservado(natureza, valor, reservado_da_natureza)

        transacao = self.transacao_repository.create(conta, Transacao.TIPO_ENCARGO, chave_idempotencia, hash_da_requisicao)
        self._lancar(transacao, conta, [self._parcela(natureza, -valor)])

        resultado = TransacaoDTO.encargo_to_dict(transacao, natureza, valor)
        self._guardar_resultado(transacao, resultado)

        self.session.commit()

        return resultado, True

    def repassar(self, conta_chave: str, repasse_data: dict, chave_idempotencia: str) -> tuple:
        self.logger.debug("Registrando um repasse")

        conta = self._get_for_update_or_raise(self.conta_repository, conta_chave, NotFoundConta)

        hash_da_requisicao = hash_requisicao(Transacao.TIPO_REPASSE, conta_chave, repasse_data)
        transacao_anterior = self._get_transacao_anterior(conta, chave_idempotencia, hash_da_requisicao)

        if transacao_anterior is not None:
            return transacao_anterior.resultado, False

        valor = repasse_data["valor_centavos"]
        self._check_valor(valor)

        if valor > conta.saldo_disponivel:
            raise InsufficientSaldoDisponivel(valor, conta.saldo_disponivel)

        taxa = calcular_taxa_pendente(
            self.lancamento_repository.sum_by_natureza(conta, Lancamento.NATUREZA_ALUGUEL),
            -self.lancamento_repository.sum_by_natureza(conta, Lancamento.NATUREZA_TAXA),
            conta.taxa_administracao_bps,
        )

        if valor <= taxa:
            raise ValorNotAboveTaxa(valor, taxa)

        parcelas = []
        if taxa > 0:
            parcelas.append(self._parcela(Lancamento.NATUREZA_TAXA, -taxa))

        parcelas.append(self._parcela(Lancamento.NATUREZA_REPASSE, taxa - valor))

        transacao = self.transacao_repository.create(conta, Transacao.TIPO_REPASSE, chave_idempotencia, hash_da_requisicao)
        self._lancar(transacao, conta, parcelas)

        resultado = TransacaoDTO.repasse_to_dict(transacao, valor, taxa)
        self._guardar_resultado(transacao, resultado)

        self.session.commit()

        return resultado, True

    def estornar(self, transacao_chave: str, chave_idempotencia: str) -> tuple:
        self.logger.debug("Registrando um estorno")

        transacao_estornada = self._get_or_raise(self.transacao_repository, transacao_chave, NotFoundTransacao)
        conta = self.conta_repository.get_by_id_for_update(transacao_estornada.conta_id)

        hash_da_requisicao = hash_requisicao(Transacao.TIPO_ESTORNO, transacao_chave, {})
        transacao_anterior = self._get_transacao_anterior(conta, chave_idempotencia, hash_da_requisicao)

        if transacao_anterior is not None:
            return transacao_anterior.resultado, False

        if transacao_estornada.tipo == Transacao.TIPO_ESTORNO:
            raise TransacaoNotEstornavel()

        if self.transacao_repository.get_by_transacao_estornada(transacao_estornada) is not None:
            raise TransacaoNotEstornavel()

        if transacao_estornada.tipo == Transacao.TIPO_RECEBIMENTO:
            recebimento = self.recebimento_repository.get_by_transacao(transacao_estornada)
            ultimo_recebimento = self.recebimento_repository.get_ultimo_da_cobranca(recebimento.cobranca_id)

            if ultimo_recebimento.id != recebimento.id:
                raise NotLastRecebimento()

        parcelas = []
        for lancamento in self.lancamento_repository.list_by_transacao(transacao_estornada):
            parcelas.append(self._parcela(lancamento.natureza, -lancamento.valor_centavos, lancamento.item_cobranca_id))

        self._check_saldos_do_estorno(conta, parcelas)
        self._check_teto_dos_saldos(conta, parcelas)

        transacao = self.transacao_repository.create_estorno(
            conta, transacao_estornada, chave_idempotencia, hash_da_requisicao
        )
        self._lancar(transacao, conta, parcelas)

        resultado = TransacaoDTO.estorno_to_dict(transacao, transacao_estornada, parcelas)
        self._guardar_resultado(transacao, resultado)

        self.session.commit()

        return resultado, True

    def _get_transacao_anterior(self, conta: Conta, chave_idempotencia: str, hash_da_requisicao: str) -> Transacao:
        transacao_anterior = self.transacao_repository.get_by_idempotency_key(conta, chave_idempotencia)

        if transacao_anterior is not None and transacao_anterior.hash_requisicao != hash_da_requisicao:
            raise ReusedIdempotencyKey()

        return transacao_anterior

    def _check_pago_em(self, pago_em: date, pagamentos: list) -> None:
        if pago_em > today_in_sao_paulo():
            raise InvalidPagoEm("pago_em", pago_em.isoformat())

        ultimo_pagamento = data_do_ultimo_pagamento(pagamentos)

        if ultimo_pagamento is not None and pago_em < ultimo_pagamento:
            raise InvalidPagoEm("pago_em", pago_em.isoformat())

    def _check_saldos_do_estorno(self, conta: Conta, parcelas: list) -> None:
        variacao_disponivel, _variacao_reservado = self._variacoes_dos_saldos(parcelas)

        if conta.saldo_disponivel + variacao_disponivel < 0:
            raise InsufficientSaldoDisponivel(-variacao_disponivel, conta.saldo_disponivel)

        for natureza in NATUREZAS_DO_RESERVADO:
            variacao_da_natureza = 0
            for parcela in parcelas:
                if parcela["natureza"] == natureza:
                    variacao_da_natureza = variacao_da_natureza + parcela["valor_centavos"]

            reservado_da_natureza = self.lancamento_repository.sum_by_natureza(conta, natureza)

            if reservado_da_natureza + variacao_da_natureza < 0:
                raise InsufficientSaldoReservado(natureza, -variacao_da_natureza, reservado_da_natureza)

    def _check_teto_dos_saldos(self, conta: Conta, parcelas: list) -> None:
        variacao_disponivel, variacao_reservado = self._variacoes_dos_saldos(parcelas)

        if conta.saldo_disponivel + variacao_disponivel > MAXIMUM_SALDO_CENTAVOS:
            raise SaldoAboveMaximum(MAXIMUM_SALDO_CENTAVOS)

        if conta.saldo_reservado + variacao_reservado > MAXIMUM_SALDO_CENTAVOS:
            raise SaldoAboveMaximum(MAXIMUM_SALDO_CENTAVOS)

    def _parcela(self, natureza: str, valor_centavos: int, item_cobranca_id: int = None) -> dict:
        return {"natureza": natureza, "valor_centavos": valor_centavos, "item_cobranca_id": item_cobranca_id}

    def _variacoes_dos_saldos(self, parcelas: list) -> tuple:
        variacao_disponivel = 0
        variacao_reservado = 0
        for parcela in parcelas:
            if parcela["natureza"] in NATUREZAS_DO_RESERVADO:
                variacao_reservado = variacao_reservado + parcela["valor_centavos"]
            else:
                variacao_disponivel = variacao_disponivel + parcela["valor_centavos"]

        return variacao_disponivel, variacao_reservado

    def _lancar(self, transacao: Transacao, conta: Conta, parcelas: list) -> None:
        for parcela in parcelas:
            self.lancamento_repository.create(
                transacao, conta, parcela["natureza"], parcela["valor_centavos"], parcela["item_cobranca_id"]
            )

        variacao_disponivel, variacao_reservado = self._variacoes_dos_saldos(parcelas)
        self.conta_repository.update_saldos(conta, variacao_disponivel, variacao_reservado)

    def _guardar_resultado(self, transacao: Transacao, resultado: dict) -> None:
        self.transacao_repository.set_resultado(transacao, resultado)

        self._flush_or_raise(
            {
                Transacao.CONTA_IDEMPOTENCIA_UNIQUE_CONSTRAINT: ReusedIdempotencyKey,
                Transacao.ESTORNADA_UNIQUE_CONSTRAINT: TransacaoNotEstornavel,
            }
        )
