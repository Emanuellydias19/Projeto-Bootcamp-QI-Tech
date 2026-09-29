from tests.utils.request_generator import RequestGenerator


NATUREZAS_DO_RESERVADO = ["condominio", "iptu"]


def extrato_completo(conta_chave: str, params: dict = None) -> list:
    if params is None:
        params = {}

    linhas = []
    cursores_vistos = set()
    proximo_cursor = None
    while True:
        params_da_pagina = dict(params)

        if proximo_cursor is not None:
            params_da_pagina["cursor"] = proximo_cursor

        status, pagina = RequestGenerator.GET_conta_extrato(conta_chave, params_da_pagina)
        assert status == 200

        linhas.extend(pagina["data"])
        proximo_cursor = pagina["proximo_cursor"]

        if proximo_cursor is None:
            return linhas

        assert proximo_cursor not in cursores_vistos
        cursores_vistos.add(proximo_cursor)


def saldos_pelo_extrato(linhas: list) -> dict:
    disponivel = 0
    reservado = 0
    for linha in linhas:
        if linha["natureza"] in NATUREZAS_DO_RESERVADO:
            reservado = reservado + linha["valor_centavos"]
        else:
            disponivel = disponivel + linha["valor_centavos"]

    return {"disponivel": disponivel, "reservado": reservado}
