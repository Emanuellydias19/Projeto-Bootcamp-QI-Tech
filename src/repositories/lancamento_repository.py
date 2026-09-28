from datetime import datetime
from uuid import uuid4

from sqlalchemy import exists, func
from sqlalchemy.orm import aliased

from database import Context
from models import Cobranca, Conta, Lancamento, Transacao


class LancamentoRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(
        self, transacao: Transacao, conta: Conta, natureza: str, valor_centavos: int, item_cobranca_id: int
    ) -> Lancamento:
        lancamento = Lancamento()

        lancamento.chave = str(uuid4())
        lancamento.transacao = transacao
        lancamento.conta_id = conta.id
        lancamento.natureza = natureza
        lancamento.valor_centavos = valor_centavos
        lancamento.item_cobranca_id = item_cobranca_id

        self.session.add(lancamento)
        return lancamento

    def list_by_transacao(self, transacao: Transacao) -> list:
        return (
            self.session.query(Lancamento)
            .filter(Lancamento.transacao_id == transacao.id)
            .order_by(Lancamento.id)
            .all()
        )

    def list_pagamentos_da_cobranca(self, cobranca: Cobranca) -> list:
        estorno = aliased(Transacao)

        return (
            self.session.query(Lancamento, Transacao.pago_em)
            .join(Transacao, Lancamento.transacao_id == Transacao.id)
            .filter(
                Transacao.cobranca_id == cobranca.id,
                Transacao.tipo == Transacao.TIPO_RECEBIMENTO,
                ~exists().where(estorno.transacao_estornada_id == Transacao.id),
            )
            .order_by(Transacao.pago_em, Lancamento.id)
            .all()
        )

    def sum_by_natureza(self, conta: Conta, natureza: str) -> int:
        total = (
            self.session.query(func.coalesce(func.sum(Lancamento.valor_centavos), 0))
            .filter(Lancamento.conta_id == conta.id, Lancamento.natureza == natureza)
            .scalar()
        )
        return int(total)

    def get_ultimo_criado_em(self, conta: Conta) -> datetime:
        return self.session.query(func.max(Lancamento.criado_em)).filter(Lancamento.conta_id == conta.id).scalar()
