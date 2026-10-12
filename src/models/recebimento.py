from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from models.base import Base
from models.cobranca import Cobranca
from models.transacao import Transacao


class Recebimento(Base):
    __tablename__ = "recebimento"

    id = Column(BigInteger, primary_key=True)
    chave = Column(CHAR(36), nullable=False)
    transacao_id = Column(BigInteger, nullable=False)
    transacao_tipo = Column(Text, nullable=False, server_default=Transacao.TIPO_RECEBIMENTO)
    cobranca_id = Column(BigInteger, ForeignKey(Cobranca.id, name="fk_recebimento_cobranca"), nullable=False)
    valor_centavos = Column(BigInteger, nullable=False)
    pago_em = Column(Date, nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    transacao = relationship(Transacao)

    __table_args__ = (
        ForeignKeyConstraint(
            ["transacao_id", "transacao_tipo"], ["transacao.id", "transacao.tipo"], name="fk_recebimento_transacao"
        ),
        UniqueConstraint("chave", name="uq_recebimento_chave"),
        UniqueConstraint("transacao_id", name="uq_recebimento_transacao"),
        CheckConstraint("transacao_tipo = 'recebimento'", name="ck_recebimento_transacao_tipo"),
        CheckConstraint("valor_centavos BETWEEN 1 AND 9007199254740991", name="ck_recebimento_valor"),
        Index("ix_recebimento_cobranca_id", "cobranca_id", "pago_em", "transacao_id"),
    )
