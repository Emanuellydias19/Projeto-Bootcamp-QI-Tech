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

    def get_by_conta_and_chave(self, conta: Conta, chave: str) -> Lancamento:
        return self.session.query(Lancamento).filter(Lancamento.conta_id == conta.id, Lancamento.chave == chave).first()

    def list_extrato(self, conta: Conta, natureza: str, antes_do_id: int, limite: int) -> list:
        return self._query_extrato(conta, natureza, antes_do_id).limit(limite).all()

    def list_extrato_da_transacao(self, conta: Conta, natureza: str, lancamento: Lancamento) -> list:
        return (
            self._query_extrato(conta, natureza, lancamento.id)
            .filter(Lancamento.transacao_id == lancamento.transacao_id)
            .all()
        )

    def has_extrato_antes_do_id(self, conta: Conta, natureza: str, antes_do_id: int) -> bool:
        query = self._filter_extrato(self.session.query(Lancamento.id), conta, natureza, antes_do_id)

        return query.first() is not None

    def has_extrato_da_transacao_antes_do(self, conta: Conta, natureza: str, lancamento: Lancamento) -> bool:
        query = self._filter_extrato(self.session.query(Lancamento.id), conta, natureza, lancamento.id)

        return query.filter(Lancamento.transacao_id == lancamento.transacao_id).first() is not None

    def _query_extrato(self, conta: Conta, natureza: str, antes_do_id: int):
        transacao_estornada = aliased(Transacao)

        query = (
            self.session.query(Lancamento, Transacao.chave, Transacao.tipo, transacao_estornada.chave)
            .join(Transacao, Lancamento.transacao_id == Transacao.id)
            .outerjoin(transacao_estornada, Transacao.transacao_estornada_id == transacao_estornada.id)
        )

        return self._filter_extrato(query, conta, natureza, antes_do_id).order_by(Lancamento.id.desc())

    def _filter_extrato(self, query, conta: Conta, natureza: str, antes_do_id: int):
        query = query.filter(Lancamento.conta_id == conta.id)

        if natureza is not None:
            query = query.filter(Lancamento.natureza == natureza)

        if antes_do_id is not None:
            query = query.filter(Lancamento.id < antes_do_id)

        return query

    def get_ultimo_criado_em(self, conta: Conta) -> datetime:
        return self.session.query(func.max(Lancamento.criado_em)).filter(Lancamento.conta_id == conta.id).scalar()
