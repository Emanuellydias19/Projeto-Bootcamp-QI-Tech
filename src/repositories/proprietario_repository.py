from uuid import uuid4

from database import Context
from models import Proprietario


class ProprietarioRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, proprietario_data: dict) -> Proprietario:
        proprietario = Proprietario()

        proprietario.chave = str(uuid4())
        proprietario.documento = proprietario_data["documento"]
        proprietario.nome = proprietario_data["nome"]

        self.session.add(proprietario)
        return proprietario

    def get_by_chave(self, chave: str) -> Proprietario:
        return self.session.query(Proprietario).filter(Proprietario.chave == chave).first()
