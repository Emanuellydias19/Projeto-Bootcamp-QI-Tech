from datetime import date
from uuid import uuid4

from database import Context
from models import Cobranca, Conta, ItemCobranca


class CobrancaRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, conta: Conta, cobranca_data: dict, vencimento: date) -> Cobranca:
        cobranca = Cobranca()

        cobranca.chave = str(uuid4())
        cobranca.conta = conta
        cobranca.competencia = cobranca_data["competencia"]
        cobranca.vencimento = vencimento

        for item_data in cobranca_data["itens"]:
            self.add_item(cobranca, item_data)

        self.session.add(cobranca)
        return cobranca

    def add_item(self, cobranca: Cobranca, item_data: dict) -> ItemCobranca:
        item = ItemCobranca()

        item.natureza = item_data["natureza"]
        item.valor_devido_centavos = item_data["valor_centavos"]

        cobranca.itens.append(item)
        return item

    def get_by_chave(self, chave: str) -> Cobranca:
        return self.session.query(Cobranca).filter(Cobranca.chave == chave).first()
