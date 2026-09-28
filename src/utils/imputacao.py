from models import Lancamento


def imputar(valor_centavos: int, ordem_naturezas: list, posicao: dict) -> dict:
    restante = valor_centavos
    rateio = []
    em_aberto = []
    for natureza in ordem_naturezas:
        for devido in _devidos_da_natureza(natureza, posicao):
            valor_pago = min(restante, devido["valor_centavos"])

            if valor_pago > 0:
                rateio.append({"natureza": natureza, "item": devido["item"], "valor_centavos": valor_pago})
                restante = restante - valor_pago

            if devido["valor_centavos"] > valor_pago:
                em_aberto.append({"natureza": natureza, "valor_centavos": devido["valor_centavos"] - valor_pago})

    return {"rateio": rateio, "em_aberto": em_aberto}


def _devidos_da_natureza(natureza: str, posicao: dict) -> list:
    devidos = []

    if natureza == Lancamento.NATUREZA_JUROS:
        devidos.append({"item": None, "valor_centavos": posicao["juros_centavos"]})
    elif natureza == Lancamento.NATUREZA_MULTA:
        devidos.append({"item": None, "valor_centavos": posicao["multa_centavos"]})
    else:
        for linha in posicao["itens"]:
            if linha["item"].natureza == natureza:
                devidos.append({"item": linha["item"], "valor_centavos": linha["valor_em_aberto_centavos"]})

    return devidos
