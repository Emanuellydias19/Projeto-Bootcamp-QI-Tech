from uuid import uuid4

from database import Context
from models import Conta, PoliticaImputacao, Proprietario


class ContaRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, proprietario: Proprietario, politica: PoliticaImputacao, conta_data: dict) -> Conta:
        conta = Conta()

        conta.chave = str(uuid4())
        conta.proprietario_id = proprietario.id
        conta.imovel_referencia = conta_data["imovel_referencia"]
        conta.saldo_disponivel = 0
        conta.saldo_reservado = 0
        conta.taxa_administracao_bps = conta_data["taxa_administracao_bps"]
        conta.multa_bps = conta_data["multa_bps"]
        conta.juros_mensal_bps = conta_data["juros_mensal_bps"]
        conta.politica_id = politica.id

        self.session.add(conta)
        return conta

    def get_by_chave(self, chave: str) -> Conta:
        return self.session.query(Conta).filter(Conta.chave == chave).first()

    def get_by_id_for_update(self, conta_id: int) -> Conta:
        return self.session.query(Conta).filter(Conta.id == conta_id).populate_existing().with_for_update().one()

    def update_saldos(self, conta: Conta, variacao_disponivel: int, variacao_reservado: int) -> None:
        conta.saldo_disponivel = conta.saldo_disponivel + variacao_disponivel
        conta.saldo_reservado = conta.saldo_reservado + variacao_reservado
