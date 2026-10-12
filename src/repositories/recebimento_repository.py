from datetime import date
from uuid import uuid4

from sqlalchemy import exists
from sqlalchemy.orm import aliased

from database import Context
from models import Cobranca, Recebimento, Transacao


class RecebimentoRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, transacao: Transacao, cobranca: Cobranca, valor_centavos: int, pago_em: date) -> Recebimento:
        recebimento = Recebimento()

        recebimento.chave = str(uuid4())
        recebimento.transacao = transacao
        recebimento.cobranca_id = cobranca.id
        recebimento.valor_centavos = valor_centavos
        recebimento.pago_em = pago_em

        self.session.add(recebimento)
        return recebimento

    def get_by_transacao(self, transacao: Transacao) -> Recebimento:
        return self.session.query(Recebimento).filter(Recebimento.transacao_id == transacao.id).first()

    def list_by_cobranca(self, cobranca: Cobranca) -> list:
        estorno = aliased(Transacao)

        return (
            self.session.query(Recebimento, Transacao.chave, estorno.id)
            .join(Transacao, Recebimento.transacao_id == Transacao.id)
            .outerjoin(estorno, estorno.transacao_estornada_id == Recebimento.transacao_id)
            .filter(Recebimento.cobranca_id == cobranca.id)
            .order_by(Recebimento.pago_em, Recebimento.transacao_id)
            .all()
        )

    def get_ultimo_da_cobranca(self, cobranca_id: int) -> Recebimento:
        estorno = aliased(Transacao)

        return (
            self.session.query(Recebimento)
            .filter(
                Recebimento.cobranca_id == cobranca_id,
                ~exists().where(estorno.transacao_estornada_id == Recebimento.transacao_id),
            )
            .order_by(Recebimento.pago_em.desc(), Recebimento.transacao_id.desc())
            .first()
        )
