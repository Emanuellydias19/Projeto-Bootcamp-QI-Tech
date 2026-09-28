from sqlalchemy import CHAR, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.conta import Conta
from models.item_cobranca import ItemCobranca
from models.transacao import Transacao


class Lancamento(Base):
    __tablename__ = "lancamento"

    NATUREZA_JUROS = "juros"
    NATUREZA_MULTA = "multa"

    id = Column(BigInteger, primary_key=True)
    chave = Column(CHAR(36), nullable=False)
    transacao_id = Column(BigInteger, ForeignKey(Transacao.id, name="fk_lancamento_transacao"), nullable=False)
    conta_id = Column(BigInteger, ForeignKey(Conta.id, name="fk_lancamento_conta"), nullable=False)
    natureza = Column(Text, nullable=False)
    valor_centavos = Column(BigInteger, nullable=False)
    item_cobranca_id = Column(BigInteger, ForeignKey(ItemCobranca.id, name="fk_lancamento_item_cobranca"))
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    transacao = relationship(Transacao)

    __table_args__ = (
        UniqueConstraint("chave", name="uq_lancamento_chave"),
        CheckConstraint(
            "natureza IN ('aluguel', 'condominio', 'iptu', 'despesa_extra', 'multa', 'juros', 'taxa', 'repasse')",
            name="ck_lancamento_natureza",
        ),
        CheckConstraint("valor_centavos <> 0", name="ck_lancamento_valor"),
        Index("ix_lancamento_conta_id", "conta_id"),
        Index("ix_lancamento_transacao_id", "transacao_id"),
        Index("ix_lancamento_item_cobranca_id", "item_cobranca_id"),
    )
