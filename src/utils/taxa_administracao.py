from utils.multa_juros import BPS_DENOMINATOR


def calcular_taxa_pendente(aluguel_recebido: int, taxa_retida: int, taxa_administracao_bps: int) -> int:
    taxa_devida = aluguel_recebido * taxa_administracao_bps // BPS_DENOMINATOR

    return max(0, taxa_devida - taxa_retida)
