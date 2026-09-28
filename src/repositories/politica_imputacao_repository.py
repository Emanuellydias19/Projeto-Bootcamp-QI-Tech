from database import Context
from models import PoliticaImputacao


class PoliticaImputacaoRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_by_chave(self, chave: str) -> PoliticaImputacao:
        return self.session.query(PoliticaImputacao).filter(PoliticaImputacao.chave == chave).first()
