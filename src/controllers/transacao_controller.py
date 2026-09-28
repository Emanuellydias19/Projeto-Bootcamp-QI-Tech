from datetime import date

from controllers.base_controller import BaseController
from dtos import TransacaoDTO
from errors import InvalidPagoEm, NotFoundCobranca, ReusedIdempotencyKey, ValorAboveDevido
from models import Conta, Transacao
from repositories import CobrancaRepository, ContaRepository, LancamentoRepository, TransacaoRepository
from utils.dates import today_in_sao_paulo
from utils.idempotency import hash_requisicao
from utils.imputacao import imputar
from utils.posicao_cobranca import calcular_posicao, data_do_ultimo_pagamento

NATUREZAS_DO_RESERVADO = ["condominio", "iptu"]


class TransacaoController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.cobranca_repository = CobrancaRepository(self.context)
        self.conta_repository = ContaRepository(self.context)
        self.transacao_repository = TransacaoRepository(self.context)
        self.lancamento_repository = LancamentoRepository(self.context)

    def receber(self, cobranca_chave: str, recebimento_data: dict, chave_idempotencia: str) -> tuple:
        self.logger.debug("Registrando um recebimento")

        cobranca = self._get_or_raise(self.cobranca_repository, cobranca_chave, NotFoundCobranca)
        conta = self.conta_repository.get_by_id_for_update(cobranca.conta_id)
        self.cobranca_repository.refresh_itens(cobranca)

        hash_da_requisicao = hash_requisicao(Transacao.TIPO_RECEBIMENTO, cobranca_chave, recebimento_data)
        transacao_anterior = self.transacao_repository.get_by_idempotency_key(conta, chave_idempotencia)

        if transacao_anterior is not None:
            if transacao_anterior.hash_requisicao != hash_da_requisicao:
                raise ReusedIdempotencyKey()

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

        transacao = self.transacao_repository.create_recebimento(
            conta, cobranca, chave_idempotencia, hash_da_requisicao, pago_em
        )
        self._lancar(transacao, conta, imputacao["rateio"])

        resultado = TransacaoDTO.recebimento_to_dict(transacao, imputacao)
        self.transacao_repository.set_resultado(transacao, resultado)

        self._flush_or_raise({Transacao.CONTA_IDEMPOTENCIA_UNIQUE_CONSTRAINT: ReusedIdempotencyKey})

        self.session.commit()

        return resultado, True

    def _check_pago_em(self, pago_em: date, pagamentos: list) -> None:
        if pago_em > today_in_sao_paulo():
            raise InvalidPagoEm("pago_em", pago_em.isoformat())

        ultimo_pagamento = data_do_ultimo_pagamento(pagamentos)

        if ultimo_pagamento is not None and pago_em < ultimo_pagamento:
            raise InvalidPagoEm("pago_em", pago_em.isoformat())

    def _lancar(self, transacao: Transacao, conta: Conta, rateio: list) -> None:
        variacao_disponivel = 0
        variacao_reservado = 0
        for parcela in rateio:
            self.lancamento_repository.create(
                transacao, conta, parcela["natureza"], parcela["valor_centavos"], parcela["item"]
            )

            if parcela["natureza"] in NATUREZAS_DO_RESERVADO:
                variacao_reservado = variacao_reservado + parcela["valor_centavos"]
            else:
                variacao_disponivel = variacao_disponivel + parcela["valor_centavos"]

        self.conta_repository.update_saldos(conta, variacao_disponivel, variacao_reservado)
