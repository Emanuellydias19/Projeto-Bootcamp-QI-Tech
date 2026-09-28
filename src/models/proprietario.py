from sqlalchemy import CHAR, BigInteger, Column, DateTime, String, Text, UniqueConstraint, func

from models.base import Base


class Proprietario(Base):
    __tablename__ = "proprietario"

    DOCUMENTO_UNIQUE_CONSTRAINT = "uq_proprietario_documento"

    id = Column(BigInteger, primary_key=True)
    chave = Column(CHAR(36), nullable=False)
    documento = Column(String(18), nullable=False)
    nome = Column(Text, nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("chave", name="uq_proprietario_chave"),
        UniqueConstraint("documento", name=DOCUMENTO_UNIQUE_CONSTRAINT),
    )
