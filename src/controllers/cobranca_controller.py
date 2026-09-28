from controllers.base_controller import BaseController
from dtos import CobrancaDTO
from errors import (
    CobrancaQuitada,
    DuplicatedCobranca,
    InvalidDate,
    InvalidPagoEm,
    NotFoundCobranca,
    NotFoundConta,
)
from models import Cobranca
from repositories import CobrancaRepository, ContaRepository, LancamentoRepository
from utils.dates import is_valid_competencia, today_in_sao_paulo
from utils.posicao_cobranca import STATUS_QUITADA, calcular_posicao, data_do_ultimo_pagamento


class CobrancaController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.cobranca_repository = CobrancaRepository(self.context)
        self.conta_repository = ContaRepository(self.context)
        self.lancamento_repository = LancamentoRepository(self.context)

    def create(self, conta_chave: str, cobranca_data: dict) -> dict:
        self.logger.debug("Registrando uma nova cobranca")

        conta = self._get_or_raise(self.conta_repository, conta_chave, NotFoundConta)

        vencimento = self._parse_date_or_raise("vencimento", cobranca_data["vencimento"])

        if not is_valid_competencia(cobranca_data["competencia"]):
            raise InvalidDate("competencia", cobranca_data["competencia"])

        for item_data in cobranca_data["itens"]:
            self._check_valor(item_data["valor_centavos"])

        cobranca = self.cobranca_repository.create(conta, cobranca_data, vencimento)

        self._flush_or_raise({Cobranca.CONTA_COMPETENCIA_UNIQUE_CONSTRAINT: DuplicatedCobranca})

        cobranca_dto = CobrancaDTO.only_obj_key(cobranca)

        self.session.commit()

        return cobranca_dto

    def add_item(self, cobranca_chave: str, item_data: dict) -> dict:
        self.logger.debug("Incluindo um item na cobranca")

        cobranca = self._get_or_raise(self.cobranca_repository, cobranca_chave, NotFoundCobranca)
        conta = self.conta_repository.get_by_id_for_update(cobranca.conta_id)
        self.cobranca_repository.refresh_itens(cobranca)

        self._check_valor(item_data["valor_centavos"])

        pagamentos = self.lancamento_repository.list_pagamentos_da_cobranca(cobranca)
        posicao = calcular_posicao(cobranca, conta, pagamentos, today_in_sao_paulo())

        if posicao["status"] == STATUS_QUITADA:
            raise CobrancaQuitada(cobranca_chave)

        self.cobranca_repository.add_item(cobranca, item_data)

        cobranca_dto = CobrancaDTO.itens_to_dict(cobranca)

        self.session.commit()

        return cobranca_dto

    def get_by_chave(self, cobranca_chave: str, data_texto: str) -> dict:
        cobranca = self._get_or_raise(self.cobranca_repository, cobranca_chave, NotFoundCobranca)
        pagamentos = self.lancamento_repository.list_pagamentos_da_cobranca(cobranca)

        if data_texto is None:
            data = today_in_sao_paulo()
        else:
            data = self._parse_date_or_raise("data", data_texto)

        ultimo_pagamento = data_do_ultimo_pagamento(pagamentos)

        if ultimo_pagamento is not None and data < ultimo_pagamento:
            raise InvalidPagoEm("data", data.isoformat())

        posicao = calcular_posicao(cobranca, cobranca.conta, pagamentos, data)

        return CobrancaDTO.obj_to_dict(cobranca, posicao)
