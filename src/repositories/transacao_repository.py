from datetime import date
from uuid import uuid4

from database import Context
from models import Cobranca, Conta, Transacao


class TransacaoRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create_recebimento(
        self, conta: Conta, cobranca: Cobranca, chave_idempotencia: str, hash_requisicao: str, pago_em: date
    ) -> Transacao:
        transacao = Transacao()

        transacao.chave = str(uuid4())
        transacao.conta_id = conta.id
        transacao.tipo = Transacao.TIPO_RECEBIMENTO
        transacao.cobranca_id = cobranca.id
        transacao.chave_idempotencia = chave_idempotencia
        transacao.hash_requisicao = hash_requisicao
        transacao.pago_em = pago_em

        self.session.add(transacao)
        return transacao

    def set_resultado(self, transacao: Transacao, resultado: dict) -> None:
        transacao.resultado = resultado

    def get_by_idempotency_key(self, conta: Conta, chave_idempotencia: str) -> Transacao:
        return (
            self.session.query(Transacao)
            .filter(Transacao.conta_id == conta.id, Transacao.chave_idempotencia == chave_idempotencia)
            .first()
        )
