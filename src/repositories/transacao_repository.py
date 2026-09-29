from datetime import date
from uuid import uuid4

from sqlalchemy import exists
from sqlalchemy.orm import aliased

from database import Context
from models import Cobranca, Conta, Transacao


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

    def create_recebimento(
        self, conta: Conta, cobranca: Cobranca, chave_idempotencia: str, hash_requisicao: str, pago_em: date
    ) -> Transacao:
        transacao = self.create(conta, Transacao.TIPO_RECEBIMENTO, chave_idempotencia, hash_requisicao)

        transacao.cobranca_id = cobranca.id
        transacao.pago_em = pago_em

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

    def get_ultimo_recebimento(self, cobranca_id: int) -> Transacao:
        estorno = aliased(Transacao)

        return (
            self.session.query(Transacao)
            .filter(
                Transacao.cobranca_id == cobranca_id,
                Transacao.tipo == Transacao.TIPO_RECEBIMENTO,
                ~exists().where(estorno.transacao_estornada_id == Transacao.id),
            )
            .order_by(Transacao.pago_em.desc(), Transacao.id.desc())
            .first()
        )

    def set_resultado(self, transacao: Transacao, resultado: dict) -> None:
        transacao.resultado = resultado

    def get_by_idempotency_key(self, conta: Conta, chave_idempotencia: str) -> Transacao:
        return (
            self.session.query(Transacao)
            .filter(Transacao.conta_id == conta.id, Transacao.chave_idempotencia == chave_idempotencia)
            .first()
        )
