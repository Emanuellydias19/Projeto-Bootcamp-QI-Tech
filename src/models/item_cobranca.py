from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Text, func

from models.base import Base
from models.cobranca import Cobranca


class ItemCobranca(Base):
    __tablename__ = "item_cobranca"

    id = Column(BigInteger, primary_key=True)
    cobranca_id = Column(BigInteger, ForeignKey(Cobranca.id, name="fk_item_cobranca_cobranca"), nullable=False)
    natureza = Column(Text, nullable=False)
    valor_devido_centavos = Column(BigInteger, nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "natureza IN ('aluguel', 'condominio', 'iptu', 'despesa_extra')", name="ck_item_cobranca_natureza"
        ),
        CheckConstraint("valor_devido_centavos > 0", name="ck_item_cobranca_valor_devido"),
        Index("ix_item_cobranca_cobranca_id", "cobranca_id"),
    )
