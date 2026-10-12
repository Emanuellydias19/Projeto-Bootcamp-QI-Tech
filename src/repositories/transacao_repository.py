from uuid import uuid4

from database import Context
from models import Conta, Transacao


class TransacaoRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, conta: Conta, tipo: str, chave_idempotencia: str, hash_requisicao: str) -> Transacao:
        transacao = Transacao()

        transacao.chave = str(uuid4())
        transacao.conta_id = conta.id
        transacao.tipo = tipo
        transacao.chave_idempotencia = chave_idempotencia
        transacao.hash_requisicao = hash_requisicao

        self.session.add(transacao)
        return transacao

    def create_estorno(
        self, conta: Conta, transacao_estornada: Transacao, chave_idempotencia: str, hash_requisicao: str
    ) -> Transacao:
        transacao = self.create(conta, Transacao.TIPO_ESTORNO, chave_idempotencia, hash_requisicao)

        transacao.transacao_estornada_id = transacao_estornada.id

        return transacao

    def get_by_chave(self, chave: str) -> Transacao:
        return self.session.query(Transacao).filter(Transacao.chave == chave).first()

    def get_by_transacao_estornada(self, transacao: Transacao) -> Transacao:
        return self.session.query(Transacao).filter(Transacao.transacao_estornada_id == transacao.id).first()

    def set_resultado(self, transacao: Transacao, resultado: dict) -> None:
        transacao.resultado = resultado

    def get_by_idempotency_key(self, conta: Conta, chave_idempotencia: str) -> Transacao:
        return (
            self.session.query(Transacao)
            .filter(Transacao.conta_id == conta.id, Transacao.chave_idempotencia == chave_idempotencia)
            .first()
        )
