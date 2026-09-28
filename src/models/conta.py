from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.politica_imputacao import PoliticaImputacao
from models.proprietario import Proprietario


class Conta(Base):
    __tablename__ = "conta"

    PROPRIETARIO_IMOVEL_UNIQUE_CONSTRAINT = "uq_conta_proprietario_imovel"

    id = Column(BigInteger, primary_key=True)
    chave = Column(CHAR(36), nullable=False)
    proprietario_id = Column(BigInteger, ForeignKey(Proprietario.id, name="fk_conta_proprietario"), nullable=False)
    imovel_referencia = Column(Text, nullable=False)
    saldo_disponivel = Column(BigInteger, nullable=False, server_default="0")
    saldo_reservado = Column(BigInteger, nullable=False, server_default="0")
    taxa_administracao_bps = Column(Integer, nullable=False)
    multa_bps = Column(Integer, nullable=False)
    juros_mensal_bps = Column(Integer, nullable=False)
    politica_id = Column(BigInteger, ForeignKey(PoliticaImputacao.id, name="fk_conta_politica_imputacao"), nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    politica = relationship(PoliticaImputacao)

    __table_args__ = (
        UniqueConstraint("chave", name="uq_conta_chave"),
        UniqueConstraint("proprietario_id", "imovel_referencia", name=PROPRIETARIO_IMOVEL_UNIQUE_CONSTRAINT),
        CheckConstraint("saldo_disponivel >= 0", name="ck_conta_saldo_disponivel"),
        CheckConstraint("saldo_reservado >= 0", name="ck_conta_saldo_reservado"),
        CheckConstraint("taxa_administracao_bps BETWEEN 0 AND 10000", name="ck_conta_taxa_administracao_bps"),
        CheckConstraint("multa_bps BETWEEN 0 AND 10000", name="ck_conta_multa_bps"),
        CheckConstraint("juros_mensal_bps BETWEEN 0 AND 10000", name="ck_conta_juros_mensal_bps"),
    )
