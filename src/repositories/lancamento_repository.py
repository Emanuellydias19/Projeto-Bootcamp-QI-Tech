from datetime import datetime
from uuid import uuid4

from sqlalchemy import func

from database import Context
from models import Cobranca, Conta, ItemCobranca, Lancamento, Transacao


class LancamentoRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(
        self, transacao: Transacao, conta: Conta, natureza: str, valor_centavos: int, item: ItemCobranca
    ) -> Lancamento:
        lancamento = Lancamento()

        lancamento.chave = str(uuid4())
        lancamento.transacao = transacao
        lancamento.conta_id = conta.id
        lancamento.natureza = natureza
        lancamento.valor_centavos = valor_centavos

        if item is not None:
            lancamento.item_cobranca_id = item.id

        self.session.add(lancamento)
        return lancamento

    def list_pagamentos_da_cobranca(self, cobranca: Cobranca) -> list:
        return (
            self.session.query(Lancamento, Transacao.pago_em)
            .join(Transacao, Lancamento.transacao_id == Transacao.id)
            .filter(Transacao.cobranca_id == cobranca.id, Transacao.tipo == Transacao.TIPO_RECEBIMENTO)
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
