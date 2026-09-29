import re
from datetime import timedelta
from uuid import uuid4

from tests.utils import (
    UUID_PATTERN,
    ConcurrentRequests,
    ObjectGenerator,
    PayloadGenerator,
    RequestGenerator,
    extrato_completo,
    saldos_pelo_extrato,
    today_in_sao_paulo,
)
from tests.utils.requisition import ClientRequisition


UNKNOWN_CHAVE = "00000000-0000-0000-0000-000000000000"
MOMENT_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
CAMPOS_DA_LINHA = {
    "lancamento_chave",
    "transacao_chave",
    "tipo",
    "natureza",
    "valor_centavos",
    "criado_em",
    "transacao_estornada_chave",
}
SIMULTANEOUS_REQUESTS = 3
NATUREZAS = ["aluguel", "condominio", "iptu", "despesa_extra", "multa", "juros", "taxa", "repasse"]
VENCIMENTO = today_in_sao_paulo() - timedelta(days=30)


def new_conta_chave() -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]


def new_cobranca_chave(conta_chave: str, itens: list = None, competencia: str = None) -> str:
    return ObjectGenerator.create_cobranca(
        conta_chave, vencimento=VENCIMENTO.isoformat(), itens=itens, competencia=competencia
    )["cobranca_chave"]


def receber(cobranca_chave: str, valor_centavos: int) -> dict:
    return ObjectGenerator.create_recebimento(cobranca_chave, valor_centavos, VENCIMENTO.isoformat())


def extrato(conta_chave: str, params: dict = None) -> dict:
    status, response = RequestGenerator.GET_conta_extrato(conta_chave, params)
    assert status == 200

    return response


def resumo(linhas: list) -> list:
    resultado = []
    for linha in linhas:
        resultado.append((linha["tipo"], linha["natureza"], linha["valor_centavos"]))

    return resultado


def saldos(conta_chave: str) -> dict:
    status, response = RequestGenerator.GET_conta_saldo(conta_chave)
    assert status == 200

    return {
        "disponivel": response["saldo_disponivel_centavos"],
        "reservado": response["saldo_reservado_centavos"],
    }


def conta_com_recebimento_e_repasse() -> dict:
    conta_chave = new_conta_chave()
    recebimento = receber(new_cobranca_chave(conta_chave), 200000)
    repasse = ObjectGenerator.create_repasse(conta_chave, 150000)

    return {"conta_chave": conta_chave, "recebimento": recebimento, "repasse": repasse}


class TestContaExtrato:
    def test_lists_the_lancamentos_from_the_most_recent_with_all_fields(self):
        conta = conta_com_recebimento_e_repasse()

        response = extrato(conta["conta_chave"])
        assert set(response.keys()) == {"data", "limite", "proximo_cursor"}
        assert response["limite"] == 10
        assert response["proximo_cursor"] is None

        linhas = response["data"]
        assert resumo(linhas) == [
            ("repasse", "repasse", -135000),
            ("repasse", "taxa", -15000),
            ("recebimento", "aluguel", 150000),
            ("recebimento", "iptu", 15000),
            ("recebimento", "condominio", 35000),
        ]

        chaves = set()
        for linha in linhas:
            assert set(linha.keys()) == CAMPOS_DA_LINHA
            assert re.fullmatch(UUID_PATTERN, linha["lancamento_chave"])
            assert re.fullmatch(MOMENT_PATTERN, linha["criado_em"])
            assert linha["transacao_estornada_chave"] is None
            chaves.add(linha["lancamento_chave"])
        assert len(chaves) == 5

        transacoes = []
        for linha in linhas:
            transacoes.append(linha["transacao_chave"])
        assert transacoes == [conta["repasse"]["transacao_chave"]] * 2 + [conta["recebimento"]["transacao_chave"]] * 3

        status, saldo = RequestGenerator.GET_conta_saldo(conta["conta_chave"])
        assert status == 200
        assert saldo["ultimo_lancamento_em"] == linhas[0]["criado_em"]

    def test_reconstructs_both_saldos_from_the_extrato(self):
        conta_chave = new_conta_chave()
        receber(new_cobranca_chave(conta_chave, competencia="2026-10"), 200000)
        ObjectGenerator.create_encargo_pagamento(conta_chave, "condominio", 35000)
        repasse = ObjectGenerator.create_repasse(conta_chave, 100000)
        receber(new_cobranca_chave(conta_chave, competencia="2026-11"), 80000)
        ObjectGenerator.create_estorno(repasse["transacao_chave"])

        atrasada = new_cobranca_chave(conta_chave, competencia="2026-12")
        hoje = today_in_sao_paulo().isoformat()
        status, posicao = RequestGenerator.GET_cobranca(atrasada, {"data": hoje})
        assert status == 200
        assert posicao["total_devido_na_data_centavos"] == 206000
        ObjectGenerator.create_recebimento(atrasada, 206000, hoje)

        linhas = extrato_completo(conta_chave, {"limite": "2"})

        assert saldos_pelo_extrato(linhas) == saldos(conta_chave)
        assert saldos(conta_chave) == {"disponivel": 336000, "reservado": 115000}

        for natureza in NATUREZAS:
            filtradas = extrato_completo(conta_chave, {"natureza": natureza})
            esperadas = [linha for linha in linhas if linha["natureza"] == natureza]
            assert filtradas == esperadas, natureza

        assert ("recebimento", "multa", 4000) in resumo(linhas)
        assert ("recebimento", "juros", 2000) in resumo(linhas)

    def test_pages_with_the_cursor_without_repeating_or_skipping(self):
        conta_chave = new_conta_chave()
        receber(new_cobranca_chave(conta_chave), 200000)
        for _encargo in range(6):
            ObjectGenerator.create_encargo_pagamento(conta_chave, "condominio", 1000)

        paginas = extrato_completo(conta_chave, {"limite": "2"})
        de_uma_vez = extrato(conta_chave, {"limite": "50"})

        assert de_uma_vez["proximo_cursor"] is None
        assert paginas == de_uma_vez["data"]
        assert len(paginas) == 9

    def test_never_splits_a_transacao_between_pages(self):
        conta = conta_com_recebimento_e_repasse()

        primeira = extrato(conta["conta_chave"], {"limite": "1"})
        assert resumo(primeira["data"]) == [("repasse", "repasse", -135000), ("repasse", "taxa", -15000)]
        assert primeira["limite"] == 1
        assert primeira["proximo_cursor"] == primeira["data"][-1]["lancamento_chave"]

        segunda = extrato(conta["conta_chave"], {"limite": "1", "cursor": primeira["proximo_cursor"]})
        assert resumo(segunda["data"]) == [
            ("recebimento", "aluguel", 150000),
            ("recebimento", "iptu", 15000),
            ("recebimento", "condominio", 35000),
        ]
        assert segunda["proximo_cursor"] is None

        completa = extrato(conta["conta_chave"], {"limite": "4"})
        assert len(completa["data"]) == 5
        assert completa["proximo_cursor"] is None

    def test_filters_by_natureza(self):
        conta_chave = new_conta_chave()
        receber(new_cobranca_chave(conta_chave, competencia="2026-10"), 200000)
        receber(new_cobranca_chave(conta_chave, competencia="2026-11"), 200000)
        ObjectGenerator.create_encargo_pagamento(conta_chave, "condominio", 35000)

        assert resumo(extrato_completo(conta_chave, {"natureza": "aluguel", "limite": "1"})) == [
            ("recebimento", "aluguel", 150000),
            ("recebimento", "aluguel", 150000),
        ]
        assert resumo(extrato_completo(conta_chave, {"natureza": "condominio"})) == [
            ("encargo", "condominio", -35000),
            ("recebimento", "condominio", 35000),
            ("recebimento", "condominio", 35000),
        ]
        assert extrato(conta_chave, {"natureza": "taxa"})["data"] == []

        so_aluguel = extrato(conta_chave, {"natureza": "aluguel", "limite": "2"})
        assert len(so_aluguel["data"]) == 2
        assert so_aluguel["proximo_cursor"] is None

        so_condominio = extrato(conta_chave, {"natureza": "condominio", "limite": "3"})
        assert len(so_condominio["data"]) == 3
        assert so_condominio["proximo_cursor"] is None

    def test_completes_the_transacao_within_the_natureza_filter(self):
        conta_chave = new_conta_chave()
        itens = [
            {"natureza": "aluguel", "valor_centavos": 150000},
            {"natureza": "despesa_extra", "valor_centavos": 8000},
            {"natureza": "despesa_extra", "valor_centavos": 12000},
        ]
        recebimento = receber(new_cobranca_chave(conta_chave, itens), 170000)

        response = extrato(conta_chave, {"natureza": "despesa_extra", "limite": "1"})
        assert resumo(response["data"]) == [
            ("recebimento", "despesa_extra", 12000),
            ("recebimento", "despesa_extra", 8000),
        ]
        for linha in response["data"]:
            assert linha["transacao_chave"] == recebimento["transacao_chave"]
        assert response["limite"] == 1
        assert response["proximo_cursor"] is None

    def test_returns_a_transacao_larger_than_the_limite_in_one_page(self):
        conta_chave = new_conta_chave()
        itens = []
        for _item in range(51):
            itens.append({"natureza": "despesa_extra", "valor_centavos": 100})
        recebimento = receber(new_cobranca_chave(conta_chave, itens), 5100)

        for limite in ["50", "1"]:
            response = extrato(conta_chave, {"limite": limite})
            assert len(response["data"]) == 51
            assert response["limite"] == int(limite)
            assert response["proximo_cursor"] is None

            for linha in response["data"]:
                assert linha["transacao_chave"] == recebimento["transacao_chave"]

    def test_uses_10_as_the_default_limite(self):
        conta_chave = new_conta_chave()
        receber(new_cobranca_chave(conta_chave), 200000)
        for _encargo in range(11):
            ObjectGenerator.create_encargo_pagamento(conta_chave, "condominio", 1000)

        response = extrato(conta_chave)
        assert response["limite"] == 10
        assert len(response["data"]) == 10
        assert response["proximo_cursor"] == response["data"][-1]["lancamento_chave"]

        for linha in response["data"]:
            assert linha["tipo"] == "encargo"

    def test_accepts_limite_from_1_to_50(self):
        conta = conta_com_recebimento_e_repasse()

        for limite in ["1", "9", "10", "49", "50"]:
            response = extrato(conta["conta_chave"], {"limite": limite})
            assert response["limite"] == int(limite)

    def test_refuses_limite_out_of_range_or_not_integer(self):
        conta = conta_com_recebimento_e_repasse()

        for limite in ["0", "51", "100", "-1", "abc", "10.5", "", "01", " 5", "5 ", "5\n", "50\n"]:
            status, response = RequestGenerator.GET_conta_extrato(conta["conta_chave"], {"limite": limite})
            assert status == 400, repr(limite)
            assert response["code"] == "QIT000001"

    def test_refuses_unknown_parameter_and_generic_natureza(self):
        conta = conta_com_recebimento_e_repasse()
        params_list = [
            {"page": "1"},
            {"limit": "5"},
            {"natureza": "generica"},
            {"natureza": "CONDOMINIO"},
            {"natureza": ""},
            {"natureza": "aluguel "},
        ]

        for params in params_list:
            status, response = RequestGenerator.GET_conta_extrato(conta["conta_chave"], params)
            assert status == 400, params
            assert response["code"] == "QIT000001"

    def test_refuses_a_cursor_that_is_not_a_lancamento_of_the_conta(self):
        conta = conta_com_recebimento_e_repasse()
        outra = conta_com_recebimento_e_repasse()
        lancamento_de_outra_conta = extrato(outra["conta_chave"])["data"][0]["lancamento_chave"]
        lancamento_da_conta = extrato(conta["conta_chave"])["data"][1]["lancamento_chave"]
        assert extrato(conta["conta_chave"], {"cursor": lancamento_da_conta})["data"] != []

        cursores = [
            lancamento_de_outra_conta,
            str(uuid4()),
            conta["repasse"]["transacao_chave"],
            "abc",
            lancamento_da_conta.upper(),
            lancamento_da_conta + " ",
            lancamento_da_conta + "\n",
            "",
        ]

        for cursor in cursores:
            status, response = RequestGenerator.GET_conta_extrato(conta["conta_chave"], {"cursor": cursor})
            assert status == 400, repr(cursor)
            assert response["code"] == "QIT000001"

    def test_refuses_a_cursor_in_the_middle_of_a_transacao(self):
        conta = conta_com_recebimento_e_repasse()
        linhas = extrato(conta["conta_chave"])["data"]

        for posicao in [0, 2, 3]:
            status, response = RequestGenerator.GET_conta_extrato(
                conta["conta_chave"], {"cursor": linhas[posicao]["lancamento_chave"]}
            )
            assert status == 400, posicao
            assert response["code"] == "QIT000001"

        depois_do_repasse = extrato(conta["conta_chave"], {"cursor": linhas[1]["lancamento_chave"]})
        assert resumo(depois_do_repasse["data"]) == resumo(linhas[2:])
        assert depois_do_repasse["proximo_cursor"] is None

        depois_da_mais_antiga = extrato(conta["conta_chave"], {"cursor": linhas[4]["lancamento_chave"]})
        assert depois_da_mais_antiga == {"data": [], "limite": 10, "proximo_cursor": None}

    def test_refuses_a_cursor_reused_with_another_natureza_filter(self):
        conta_chave = new_conta_chave()
        receber(new_cobranca_chave(conta_chave, competencia="2026-10"), 200000)
        receber(new_cobranca_chave(conta_chave, competencia="2026-11"), 200000)

        primeira = extrato(conta_chave, {"natureza": "aluguel", "limite": "1"})
        cursor = primeira["proximo_cursor"]
        assert cursor == primeira["data"][0]["lancamento_chave"]

        for params in [{"cursor": cursor}, {"cursor": cursor, "natureza": "condominio"}]:
            status, response = RequestGenerator.GET_conta_extrato(conta_chave, params)
            assert status == 400, params
            assert response["code"] == "QIT000001"

        segunda = extrato(conta_chave, {"natureza": "aluguel", "limite": "1", "cursor": cursor})
        assert resumo(segunda["data"]) == [("recebimento", "aluguel", 150000)]
        assert segunda["proximo_cursor"] is None

    def test_refuses_a_cursor_of_another_natureza_under_a_filter(self):
        conta_chave = new_conta_chave()
        receber(new_cobranca_chave(conta_chave, competencia="2026-10"), 200000)
        receber(new_cobranca_chave(conta_chave, competencia="2026-11"), 200000)

        cursor = extrato(conta_chave, {"natureza": "condominio", "limite": "1"})["proximo_cursor"]
        assert cursor is not None

        for natureza in ["aluguel", "iptu"]:
            status, response = RequestGenerator.GET_conta_extrato(conta_chave, {"cursor": cursor, "natureza": natureza})
            assert status == 400, natureza
            assert response["code"] == "QIT000001"

        segunda = extrato(conta_chave, {"natureza": "condominio", "limite": "1", "cursor": cursor})
        assert resumo(segunda["data"]) == [("recebimento", "condominio", 35000)]

    def test_checks_the_query_then_the_conta_then_the_cursor(self):
        outra = conta_com_recebimento_e_repasse()
        lancamento_de_outra_conta = extrato(outra["conta_chave"])["data"][1]["lancamento_chave"]

        for params in [{"limite": "51"}, {"natureza": "generica"}]:
            status, response = RequestGenerator.GET_conta_extrato(UNKNOWN_CHAVE, params)
            assert status == 400, params
            assert response["code"] == "QIT000001"

        for cursor in [str(uuid4()), lancamento_de_outra_conta]:
            status, response = RequestGenerator.GET_conta_extrato(UNKNOWN_CHAVE, {"cursor": cursor})
            assert status == 404, cursor
            assert response["code"] == "QIT001011"

    def test_refuses_conta_that_does_not_exist(self):
        conta_chave = new_conta_chave()

        for chave in [UNKNOWN_CHAVE, "abc", conta_chave.upper(), conta_chave + " "]:
            status, response = RequestGenerator.GET_conta_extrato(chave)
            assert status == 404, repr(chave)
            assert response["code"] == "QIT001011"

    def test_returns_an_empty_page_for_a_conta_without_lancamentos(self):
        response = extrato(new_conta_chave())

        assert response == {"data": [], "limite": 10, "proximo_cursor": None}

    def test_shows_the_estorno_with_the_reversed_transacao(self):
        conta = conta_com_recebimento_e_repasse()
        estorno = ObjectGenerator.create_estorno(conta["repasse"]["transacao_chave"])

        linhas = extrato(conta["conta_chave"])["data"]
        assert resumo(linhas[:2]) == [("estorno", "repasse", 135000), ("estorno", "taxa", 15000)]

        lancamentos_do_estorno = []
        for linha in linhas[:2]:
            assert linha["transacao_chave"] == estorno["transacao_chave"]
            assert linha["transacao_estornada_chave"] == conta["repasse"]["transacao_chave"]
            lancamentos_do_estorno.append({"natureza": linha["natureza"], "valor_centavos": linha["valor_centavos"]})
        assert lancamentos_do_estorno == estorno["lancamentos"]

        for linha in linhas[2:]:
            assert linha["transacao_estornada_chave"] is None

        assert saldos_pelo_extrato(linhas) == saldos(conta["conta_chave"])

    def test_keeps_the_pages_stable_when_new_lancamentos_arrive(self):
        conta = conta_com_recebimento_e_repasse()

        primeira = extrato(conta["conta_chave"], {"limite": "2"})
        assert resumo(primeira["data"]) == [("repasse", "repasse", -135000), ("repasse", "taxa", -15000)]

        receber(new_cobranca_chave(conta["conta_chave"], competencia="2026-11"), 200000)

        segunda = extrato(conta["conta_chave"], {"limite": "2", "cursor": primeira["proximo_cursor"]})
        assert resumo(segunda["data"]) == [
            ("recebimento", "aluguel", 150000),
            ("recebimento", "iptu", 15000),
            ("recebimento", "condominio", 35000),
        ]
        assert segunda["data"][0]["transacao_chave"] == conta["recebimento"]["transacao_chave"]
        assert segunda["proximo_cursor"] is None

    def test_refuses_request_without_token(self):
        conta = conta_com_recebimento_e_repasse()

        response = ClientRequisition.send("GET", f"/contas/{conta['conta_chave']}/extrato")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

    def test_matches_the_saldos_after_simultaneous_operations(self):
        conta_chave = new_conta_chave()
        recebimento = receber(new_cobranca_chave(conta_chave), 200000)
        repasse_payload = PayloadGenerator.create_repasse_payload(30000)
        encargo_payload = PayloadGenerator.create_encargo_payload("condominio", 5000)

        calls = [(RequestGenerator.POST_transacao_estornos, (recebimento["transacao_chave"],))]
        for _call in range(SIMULTANEOUS_REQUESTS):
            calls.append((RequestGenerator.POST_conta_repasses, (conta_chave, repasse_payload)))
            calls.append((RequestGenerator.POST_conta_encargo_pagamentos, (conta_chave, encargo_payload)))

        for status, _response in ConcurrentRequests.send_different_at_the_same_time(calls):
            assert status in [201, 409]

        linhas = extrato_completo(conta_chave, {"limite": "3"})

        assert saldos_pelo_extrato(linhas) == saldos(conta_chave)
