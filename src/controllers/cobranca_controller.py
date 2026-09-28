from datetime import date

from controllers.base_controller import BaseController
from dtos import CobrancaDTO
from errors import DuplicatedCobranca, InvalidDate, InvalidValor, NotFoundCobranca, NotFoundConta
from models import Cobranca, ItemCobranca
from repositories import CobrancaRepository, ContaRepository
from utils.dates import date_in_sao_paulo, is_valid_competencia, parse_date, today_in_sao_paulo
from utils.multa_juros import calcular_juros, calcular_multa

STATUS_ABERTA = "aberta"


class CobrancaController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.cobranca_repository = CobrancaRepository(self.context)
        self.conta_repository = ContaRepository(self.context)

    def create(self, conta_chave: str, cobranca_data: dict) -> dict:
        self.logger.debug("Registrando uma nova cobranca")

        conta = self._get_or_raise(self.conta_repository, conta_chave, NotFoundConta)

        vencimento = self._parse_date("vencimento", cobranca_data["vencimento"])

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

        self._check_valor(item_data["valor_centavos"])

        self.cobranca_repository.add_item(cobranca, item_data)

        cobranca_dto = CobrancaDTO.itens_to_dict(cobranca)

        self.session.commit()

        return cobranca_dto

    def get_by_chave(self, cobranca_chave: str, data_texto: str) -> dict:
        cobranca = self._get_or_raise(self.cobranca_repository, cobranca_chave, NotFoundCobranca)

        if data_texto is None:
            data = today_in_sao_paulo()
        else:
            data = self._parse_date("data", data_texto)

        itens = []
        valores_em_aberto = []
        total_em_aberto = 0
        for item in cobranca.itens:
            valor_pago = 0
            valor_em_aberto = item.valor_devido_centavos - valor_pago

            itens.append({"item": item, "valor_pago_centavos": valor_pago, "valor_em_aberto_centavos": valor_em_aberto})
            valores_em_aberto.append((self._data_de_referencia(cobranca, item), valor_em_aberto))
            total_em_aberto = total_em_aberto + valor_em_aberto

        multa = calcular_multa(valores_em_aberto, cobranca.conta.multa_bps, data)
        juros = calcular_juros(valores_em_aberto, cobranca.conta.juros_mensal_bps, data)

        posicao = {
            "status": STATUS_ABERTA,
            "itens": itens,
            "total_em_aberto_centavos": total_em_aberto,
            "data": data,
            "multa_centavos": multa,
            "juros_centavos": juros,
            "total_devido_na_data_centavos": total_em_aberto + multa + juros,
        }

        return CobrancaDTO.obj_to_dict(cobranca, posicao)

    def _data_de_referencia(self, cobranca: Cobranca, item: ItemCobranca) -> date:
        data_de_referencia = cobranca.vencimento

        if item.criado_em > cobranca.criado_em:
            data_de_inclusao = date_in_sao_paulo(item.criado_em)

            if data_de_inclusao > cobranca.vencimento:
                data_de_referencia = data_de_inclusao

        return data_de_referencia

    def _parse_date(self, field: str, text: str) -> date:
        parsed_date = parse_date(text)

        if parsed_date is None:
            raise InvalidDate(field, text)

        return parsed_date

    def _check_valor(self, valor_centavos: int) -> None:
        if valor_centavos <= 0:
            raise InvalidValor(valor_centavos)
