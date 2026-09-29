BPS_DENOMINATOR = 10000
DAYS_IN_A_MONTH = 30


def calcular_multa(valor_em_atraso: int, multa_bps: int) -> int:
    return valor_em_atraso * multa_bps // BPS_DENOMINATOR


def calcular_juros(valor_vezes_dias: int, juros_mensal_bps: int) -> int:
    return valor_vezes_dias * juros_mensal_bps // (BPS_DENOMINATOR * DAYS_IN_A_MONTH)
