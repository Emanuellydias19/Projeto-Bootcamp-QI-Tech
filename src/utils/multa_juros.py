from datetime import date

BPS_DENOMINATOR = 10000
DAYS_IN_A_MONTH = 30


def calcular_multa(valores_em_aberto: list, multa_bps: int, data: date) -> int:
    total_em_atraso = 0
    for data_de_referencia, valor_em_aberto in valores_em_aberto:
        if data > data_de_referencia:
            total_em_atraso = total_em_atraso + valor_em_aberto

    return total_em_atraso * multa_bps // BPS_DENOMINATOR


def calcular_juros(valores_em_aberto: list, juros_mensal_bps: int, data: date) -> int:
    total_por_dia = 0
    for data_de_referencia, valor_em_aberto in valores_em_aberto:
        dias_em_atraso = (data - data_de_referencia).days

        if dias_em_atraso > 0:
            total_por_dia = total_por_dia + valor_em_aberto * dias_em_atraso

    return total_por_dia * juros_mensal_bps // (BPS_DENOMINATOR * DAYS_IN_A_MONTH)
