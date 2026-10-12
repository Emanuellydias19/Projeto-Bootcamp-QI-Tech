from sqlalchemy import create_engine, text

from tests.utils.db_utils import DbUtils


ADIANTAR_OS_ITENS = (
    "UPDATE item_cobranca SET criado_em = criado_em + INTERVAL '1 minute' "
    "WHERE cobranca_id = (SELECT id FROM cobranca WHERE chave = :chave)"
)
ADIANTAR_A_COBRANCA = "UPDATE cobranca SET criado_em = criado_em + INTERVAL '1 minute' WHERE chave = :chave"


def adiantar_o_relogio_da_cobranca(cobranca_chave: str) -> None:
    engine = create_engine(DbUtils.database_url(), isolation_level="AUTOCOMMIT")

    try:
        with engine.connect() as connection:
            connection.execute(text(ADIANTAR_OS_ITENS), {"chave": cobranca_chave})
            connection.execute(text(ADIANTAR_A_COBRANCA), {"chave": cobranca_chave})
    finally:
        engine.dispose()
