from sqlalchemy import CHAR, BigInteger, Column, DateTime, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class PoliticaImputacao(Base):
    __tablename__ = "politica_imputacao"

    id = Column(BigInteger, primary_key=True)
    chave = Column(CHAR(36), nullable=False)
    nome = Column(Text, nullable=False)
    versao = Column(Integer, nullable=False)
    ordem_naturezas = Column(JSONB, nullable=False)
    vigente_desde = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("chave", name="uq_politica_imputacao_chave"),
        UniqueConstraint("nome", "versao", name="uq_politica_imputacao_nome_versao"),
    )
