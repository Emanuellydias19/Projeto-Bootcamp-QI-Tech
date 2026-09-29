from controllers.base_controller import BaseController
from dtos import ContaDTO, LancamentoDTO
from errors import (
    DuplicatedConta,
    InvalidBps,
    InvalidSchema,
    NotFoundConta,
    NotFoundPoliticaImputacao,
    NotFoundProprietario,
)
from models import Conta
from repositories import ContaRepository, LancamentoRepository, PoliticaImputacaoRepository, ProprietarioRepository

BPS_FIELDS = ["taxa_administracao_bps", "multa_bps", "juros_mensal_bps"]
MINIMUM_BPS = 0
MAXIMUM_BPS = 10000


class ContaController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.conta_repository = ContaRepository(self.context)
        self.proprietario_repository = ProprietarioRepository(self.context)
        self.politica_imputacao_repository = PoliticaImputacaoRepository(self.context)
        self.lancamento_repository = LancamentoRepository(self.context)

    def create(self, conta_data: dict) -> dict:
        self.logger.debug("Abrindo uma nova conta")

        proprietario = self._get_or_raise(
            self.proprietario_repository, conta_data["proprietario_chave"], NotFoundProprietario
        )
        politica = self._get_or_raise(
            self.politica_imputacao_repository, conta_data["politica_imputacao_chave"], NotFoundPoliticaImputacao
        )

        for field in BPS_FIELDS:
            if conta_data[field] < MINIMUM_BPS or conta_data[field] > MAXIMUM_BPS:
                raise InvalidBps(field, MINIMUM_BPS, MAXIMUM_BPS)

        conta = self.conta_repository.create(proprietario, politica, conta_data)

        self._flush_or_raise({Conta.PROPRIETARIO_IMOVEL_UNIQUE_CONSTRAINT: DuplicatedConta})

        conta_dto = ContaDTO.only_obj_key(conta)

        self.session.commit()

        return conta_dto

    def get_saldo(self, conta_chave: str) -> dict:
        conta = self._get_or_raise(self.conta_repository, conta_chave, NotFoundConta)
        ultimo_lancamento_em = self.lancamento_repository.get_ultimo_criado_em(conta)

        return ContaDTO.saldo_to_dict(conta, ultimo_lancamento_em)

    def get_extrato(self, conta_chave: str, cursor: str, limite: int, natureza: str) -> dict:
        conta = self._get_or_raise(self.conta_repository, conta_chave, NotFoundConta)

        antes_do_id = None
        if cursor is not None:
            lancamento_do_cursor = self.lancamento_repository.get_by_conta_and_chave(conta, cursor)

            if lancamento_do_cursor is None:
                raise InvalidSchema(f"The cursor {cursor} is not a lancamento of this account.")

            if natureza is not None and lancamento_do_cursor.natureza != natureza:
                raise InvalidSchema(f"The cursor {cursor} is not a lancamento of the natureza {natureza}.")

            if self.lancamento_repository.has_extrato_da_transacao_antes_do(conta, natureza, lancamento_do_cursor):
                raise InvalidSchema(f"The cursor {cursor} is not the last lancamento of its transacao in this extrato.")

            antes_do_id = lancamento_do_cursor.id

        linhas = self.lancamento_repository.list_extrato(conta, natureza, antes_do_id, limite)
        proximo_cursor = None

        if len(linhas) == limite:
            linhas = linhas + self.lancamento_repository.list_extrato_da_transacao(conta, natureza, linhas[-1][0])
            ultimo_lancamento = linhas[-1][0]

            if self.lancamento_repository.has_extrato_antes_do_id(conta, natureza, ultimo_lancamento.id):
                proximo_cursor = ultimo_lancamento.chave

        return LancamentoDTO.extrato_to_dict(linhas, limite, proximo_cursor)
