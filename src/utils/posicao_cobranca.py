from datetime import date

from models import Cobranca, Conta, ItemCobranca, Lancamento
from utils.dates import date_in_sao_paulo
from utils.multa_juros import calcular_juros, calcular_multa

STATUS_ABERTA = "aberta"
STATUS_PARCIAL = "parcial"
STATUS_QUITADA = "quitada"


def calcular_posicao(cobranca: Cobranca, conta: Conta, pagamentos: list, data: date) -> dict:
    valor_pago_total = 0
    multa_paga = 0
    juros_pagos = 0
    for lancamento, _pago_em in pagamentos:
        valor_pago_total = valor_pago_total + lancamento.valor_centavos

        if lancamento.natureza == Lancamento.NATUREZA_MULTA:
            multa_paga = multa_paga + lancamento.valor_centavos

        if lancamento.natureza == Lancamento.NATUREZA_JUROS:
            juros_pagos = juros_pagos + lancamento.valor_centavos

    itens = []
    total_em_aberto = 0
    valor_em_atraso = 0
    valor_vezes_dias = 0
    for item in cobranca.itens:
        if _incluido_depois_de(cobranca, item, data):
            continue

        pagamentos_do_item = _pagamentos_do_item(item, pagamentos)
        referencia = _data_de_referencia(cobranca, item)

        valor_pago = 0
        for _pago_em, valor in pagamentos_do_item:
            valor_pago = valor_pago + valor

        valor_em_aberto = item.valor_devido_centavos - valor_pago

        if data > referencia:
            valor_em_atraso = valor_em_atraso + _valor_em_aberto_na_data(item, pagamentos_do_item, referencia)

        valor_vezes_dias = valor_vezes_dias + _valor_vezes_dias(item, pagamentos_do_item, referencia, data)
        total_em_aberto = total_em_aberto + valor_em_aberto
        itens.append({"item": item, "valor_pago_centavos": valor_pago, "valor_em_aberto_centavos": valor_em_aberto})

    multa = calcular_multa(valor_em_atraso, conta.multa_bps) - multa_paga
    juros = calcular_juros(valor_vezes_dias, conta.juros_mensal_bps) - juros_pagos
    total_devido = total_em_aberto + multa + juros

    return {
        "status": _status(valor_pago_total, total_devido),
        "itens": itens,
        "total_em_aberto_centavos": total_em_aberto,
        "data": data,
        "multa_centavos": multa,
        "juros_centavos": juros,
        "total_devido_na_data_centavos": total_devido,
    }


def _data_de_referencia(cobranca: Cobranca, item: ItemCobranca) -> date:
    referencia = cobranca.vencimento

    if not _enviado_na_criacao(cobranca, item):
        data_de_inclusao = date_in_sao_paulo(item.criado_em)

        if data_de_inclusao > cobranca.vencimento:
            referencia = data_de_inclusao

    return referencia


def _incluido_depois_de(cobranca: Cobranca, item: ItemCobranca, data: date) -> bool:
    return not _enviado_na_criacao(cobranca, item) and date_in_sao_paulo(item.criado_em) > data


def _enviado_na_criacao(cobranca: Cobranca, item: ItemCobranca) -> bool:
    return item.criado_em == cobranca.criado_em


def data_do_ultimo_pagamento(pagamentos: list) -> date:
    ultimo_pagamento = None
    for _lancamento, pago_em in pagamentos:
        ultimo_pagamento = pago_em

    return ultimo_pagamento


def _pagamentos_do_item(item: ItemCobranca, pagamentos: list) -> list:
    pagamentos_do_item = []
    for lancamento, pago_em in pagamentos:
        if lancamento.item_cobranca_id == item.id:
            pagamentos_do_item.append((pago_em, lancamento.valor_centavos))

    return pagamentos_do_item


def _valor_em_aberto_na_data(item: ItemCobranca, pagamentos_do_item: list, data: date) -> int:
    valor_em_aberto = item.valor_devido_centavos
    for pago_em, valor in pagamentos_do_item:
        if pago_em <= data:
            valor_em_aberto = valor_em_aberto - valor

    return valor_em_aberto


def _valor_vezes_dias(item: ItemCobranca, pagamentos_do_item: list, referencia: date, data: date) -> int:
    total = 0
    valor_em_aberto = item.valor_devido_centavos
    inicio = referencia
    for pago_em, valor in pagamentos_do_item:
        if pago_em >= data:
            break

        if pago_em > inicio:
            total = total + valor_em_aberto * (pago_em - inicio).days
            inicio = pago_em

        valor_em_aberto = valor_em_aberto - valor

    if data > inicio:
        total = total + valor_em_aberto * (data - inicio).days

    return total


def _status(valor_pago_total: int, total_devido: int) -> str:
    status = STATUS_PARCIAL

    if valor_pago_total == 0:
        status = STATUS_ABERTA
    elif total_devido == 0:
        status = STATUS_QUITADA

    return status
