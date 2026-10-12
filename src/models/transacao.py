from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base
from models.conta import Conta


class Transacao(Base):
    __tablename__ = "transacao"

    TIPO_RECEBIMENTO = "recebimento"
    TIPO_ENCARGO = "encargo"
    TIPO_REPASSE = "repasse"
    TIPO_ESTORNO = "estorno"
    CONTA_IDEMPOTENCIA_UNIQUE_CONSTRAINT = "uq_transacao_conta_idempotencia"
    ESTORNADA_UNIQUE_CONSTRAINT = "uq_transacao_estornada"

    id = Column(BigInteger, primary_key=True)
    chave = Column(CHAR(36), nullable=False)
    conta_id = Column(BigInteger, ForeignKey(Conta.id, name="fk_transacao_conta"), nullable=False)
    tipo = Column(Text, nullable=False)
    transacao_estornada_id = Column(BigInteger, ForeignKey("transacao.id", name="fk_transacao_estornada"))
    chave_idempotencia = Column(Text, nullable=False)
    hash_requisicao = Column(CHAR(64), nullable=False)
    resultado = Column(JSONB, nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("chave", name="uq_transacao_chave"),
        UniqueConstraint("conta_id", "chave_idempotencia", name=CONTA_IDEMPOTENCIA_UNIQUE_CONSTRAINT),
        UniqueConstraint("transacao_estornada_id", name=ESTORNADA_UNIQUE_CONSTRAINT),
        UniqueConstraint("id", "tipo", name="uq_transacao_id_tipo"),
        CheckConstraint("tipo IN ('recebimento', 'encargo', 'repasse', 'estorno')", name="ck_transacao_tipo"),
        CheckConstraint("(tipo = 'estorno') = (transacao_estornada_id IS NOT NULL)", name="ck_transacao_estornada"),
    )
