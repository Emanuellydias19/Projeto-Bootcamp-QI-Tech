from sqlalchemy import CHAR, BigInteger, Column, Date, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.conta import Conta


class Cobranca(Base):
    __tablename__ = "cobranca"

    CONTA_COMPETENCIA_UNIQUE_CONSTRAINT = "uq_cobranca_conta_competencia"

    id = Column(BigInteger, primary_key=True)
    chave = Column(CHAR(36), nullable=False)
    conta_id = Column(BigInteger, ForeignKey(Conta.id, name="fk_cobranca_conta"), nullable=False)
    competencia = Column(Text, nullable=False)
    vencimento = Column(Date, nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    conta = relationship(Conta)
    itens = relationship("ItemCobranca", lazy="selectin", order_by="ItemCobranca.id")

    __table_args__ = (
        UniqueConstraint("chave", name="uq_cobranca_chave"),
        UniqueConstraint("conta_id", "competencia", name=CONTA_COMPETENCIA_UNIQUE_CONSTRAINT),
    )
