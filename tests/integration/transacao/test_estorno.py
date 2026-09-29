import re
from datetime import date, timedelta
from uuid import uuid4

from tests.utils import (
    INTERNAL_TOKEN,
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
SIMULTANEOUS_REQUESTS = 5
VENCIMENTO = today_in_sao_paulo() - timedelta(days=30)


def new_conta_chave(taxa_administracao_bps: int = None) -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave, taxa_administracao_bps=taxa_administracao_bps)[
        "conta_chave"
    ]


def new_cobranca_chave(conta_chave: str, itens: list = None, competencia: str = None) -> str:
    return ObjectGenerator.create_cobranca(
        conta_chave, vencimento=VENCIMENTO.isoformat(), itens=itens, competencia=competencia
    )["cobranca_chave"]


def receber(cobranca_chave: str, valor_centavos: int, pago_em: date = VENCIMENTO) -> str:
    return ObjectGenerator.create_recebimento(cobranca_chave, valor_centavos, pago_em.isoformat())["transacao_chave"]


def conta_com_recebimento(taxa_administracao_bps: int = None) -> dict:
    conta_chave = new_conta_chave(taxa_administracao_bps)
    cobranca_chave = new_cobranca_chave(conta_chave)
    recebimento_chave = receber(cobranca_chave, 200000)

    return {"conta_chave": conta_chave, "cobranca_chave": cobranca_chave, "recebimento_chave": recebimento_chave}


def repassar(conta_chave: str, valor_centavos: int, idempotency_key: str = None) -> tuple:
    payload = PayloadGenerator.create_repasse_payload(valor_centavos)

    return RequestGenerator.POST_conta_repasses(conta_chave, payload, idempotency_key)


def pagar_encargo(conta_chave: str, natureza: str, valor_centavos: int) -> tuple:
    payload = PayloadGenerator.create_encargo_payload(natureza, valor_centavos)

    return RequestGenerator.POST_conta_encargo_pagamentos(conta_chave, payload)


def estornar(transacao_chave: str, idempotency_key: str = None) -> tuple:
    return RequestGenerator.POST_transacao_estornos(transacao_chave, idempotency_key)


def saldos(conta_chave: str) -> dict:
    status, response = RequestGenerator.GET_conta_saldo(conta_chave)
    assert status == 200

    return {
        "disponivel": response["saldo_disponivel_centavos"],
        "reservado": response["saldo_reservado_centavos"],
    }


def posicao(cobranca_chave: str, data: date = VENCIMENTO) -> dict:
    status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": data.isoformat()})
    assert status == 200

    return response


def itens_da_posicao(response: dict) -> list:
    itens = []
    for item in response["itens"]:
        itens.append((item["natureza"], item["valor_pago_centavos"], item["valor_em_aberto_centavos"]))

    return itens


def naturezas(response: dict) -> list:
    resultado = []
    for lancamento in response["lancamentos"]:
        resultado.append(lancamento["natureza"])

    return resultado


class TestEstorno:
    def test_reverses_a_repasse_and_gives_the_money_back(self):
        conta = conta_com_recebimento()

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, response = estornar(repasse["transacao_chave"])
        assert status == 201
        assert re.fullmatch(UUID_PATTERN, response["transacao_chave"])
        assert response["transacao_chave"] != repasse["transacao_chave"]
        assert response == {
            "transacao_chave": response["transacao_chave"],
            "transacao_estornada_chave": repasse["transacao_chave"],
            "lancamentos": [
                {"natureza": "repasse", "valor_centavos": 135000},
                {"natureza": "taxa", "valor_centavos": 15000},
            ],
        }

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_retains_the_taxa_again_after_reversing_a_repasse(self):
        conta = conta_com_recebimento()

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, _response = estornar(repasse["transacao_chave"])
        assert status == 201

        status, response = repassar(conta["conta_chave"], 150000)
        assert status == 201
        assert response["taxa_centavos"] == 15000
        assert response["liquido_centavos"] == 135000

        assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 50000}

    def test_reverses_a_repasse_without_taxa_with_one_lancamento(self):
        conta = conta_com_recebimento(taxa_administracao_bps=0)

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, response = estornar(repasse["transacao_chave"])
        assert status == 201
        assert response["lancamentos"] == [{"natureza": "repasse", "valor_centavos": 150000}]

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_reverses_an_encargo_and_gives_the_reserve_back(self):
        conta = conta_com_recebimento()

        status, encargo = pagar_encargo(conta["conta_chave"], "iptu", 15000)
        assert status == 201

        status, response = estornar(encargo["transacao_chave"])
        assert status == 201
        assert response["transacao_estornada_chave"] == encargo["transacao_chave"]
        assert response["lancamentos"] == [{"natureza": "iptu", "valor_centavos": 15000}]
        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

        status, _response = pagar_encargo(conta["conta_chave"], "iptu", 15000)
        assert status == 201

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 35000}

    def test_reverses_a_recebimento_and_reopens_the_cobranca(self):
        conta = conta_com_recebimento()
        assert posicao(conta["cobranca_chave"])["status"] == "quitada"
        antes_do_recebimento = {"data": (VENCIMENTO - timedelta(days=1)).isoformat()}

        status, response = RequestGenerator.GET_cobranca(conta["cobranca_chave"], antes_do_recebimento)
        assert status == 422
        assert response["code"] == "QIT001027"

        status, response = estornar(conta["recebimento_chave"])
        assert status == 201
        assert response["transacao_estornada_chave"] == conta["recebimento_chave"]
        assert response["lancamentos"] == [
            {"natureza": "aluguel", "valor_centavos": -150000},
            {"natureza": "iptu", "valor_centavos": -15000},
            {"natureza": "condominio", "valor_centavos": -35000},
        ]

        assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 0}

        reaberta = posicao(conta["cobranca_chave"])
        assert reaberta["status"] == "aberta"
        assert itens_da_posicao(reaberta) == [
            ("aluguel", 0, 150000),
            ("condominio", 0, 35000),
            ("iptu", 0, 15000),
        ]
        assert reaberta["total_devido_na_data_centavos"] == 200000

        status, response = RequestGenerator.GET_cobranca(conta["cobranca_chave"], antes_do_recebimento)
        assert status == 200
        assert response["status"] == "aberta"

    def test_accepts_a_pago_em_before_the_reversed_recebimento(self):
        conta = conta_com_recebimento()

        status, _response = estornar(conta["recebimento_chave"])
        assert status == 201

        receber(conta["cobranca_chave"], 200000, VENCIMENTO - timedelta(days=1))

        assert posicao(conta["cobranca_chave"])["status"] == "quitada"
        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_makes_multa_and_juros_owed_again_after_reversing_a_late_recebimento(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        hoje = today_in_sao_paulo()

        posicao_antes = posicao(cobranca_chave, hoje)
        assert posicao_antes["multa_centavos"] > 0
        assert posicao_antes["juros_centavos"] > 0

        recebimento_chave = receber(cobranca_chave, posicao_antes["total_devido_na_data_centavos"], hoje)
        assert posicao(cobranca_chave, hoje)["status"] == "quitada"

        status, response = estornar(recebimento_chave)
        assert status == 201
        assert naturezas(response) == ["aluguel", "iptu", "condominio", "multa", "juros"]

        assert posicao(cobranca_chave, hoje) == posicao_antes
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_refuses_reversing_a_recebimento_before_a_later_one(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        primeiro = receber(cobranca_chave, 50000)
        segundo = receber(cobranca_chave, 150000)

        status, response = estornar(primeiro)
        assert status == 409
        assert response["code"] == "QIT001028"
        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

        status, response = estornar(segundo)
        assert status == 201
        assert response["lancamentos"] == [{"natureza": "aluguel", "valor_centavos": -150000}]

        status, response = estornar(primeiro)
        assert status == 201
        assert response["lancamentos"] == [
            {"natureza": "iptu", "valor_centavos": -15000},
            {"natureza": "condominio", "valor_centavos": -35000},
        ]
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

        status, response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, PayloadGenerator.create_recebimento_payload(150000, VENCIMENTO.isoformat())
        )
        assert status == 201
        assert response["rateio"] == [
            {"natureza": "condominio", "valor_centavos": 35000},
            {"natureza": "iptu", "valor_centavos": 15000},
            {"natureza": "aluguel", "valor_centavos": 100000},
        ]
        assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 50000}

    def test_checks_the_later_recebimento_before_the_saldos(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        primeiro = receber(cobranca_chave, 100000)
        receber(cobranca_chave, 100000)

        status, _response = repassar(conta_chave, 150000)
        assert status == 201
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 50000}

        status, response = estornar(primeiro)
        assert status == 409
        assert response["code"] == "QIT001028"

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 50000}

    def test_reverses_each_lancamento_even_with_the_same_natureza(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(
            conta_chave,
            [
                {"natureza": "despesa_extra", "valor_centavos": 30000},
                {"natureza": "despesa_extra", "valor_centavos": 20000},
            ],
        )
        recebimento = receber(cobranca_chave, 50000)

        status, response = estornar(recebimento)
        assert status == 201
        assert response["lancamentos"] == [
            {"natureza": "despesa_extra", "valor_centavos": -20000},
            {"natureza": "despesa_extra", "valor_centavos": -30000},
        ]

        assert itens_da_posicao(posicao(cobranca_chave)) == [("despesa_extra", 0, 30000), ("despesa_extra", 0, 20000)]
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_allows_reversing_a_recebimento_whose_later_one_was_reversed(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        primeiro = receber(cobranca_chave, 50000)
        segundo = receber(cobranca_chave, 150000)

        status, _response = estornar(segundo)
        assert status == 201

        status, _response = estornar(primeiro)
        assert status == 201

        assert posicao(cobranca_chave)["status"] == "aberta"
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_restores_the_position_after_reversing_the_last_late_recebimento(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        receber(cobranca_chave, 100000, VENCIMENTO + timedelta(days=10))

        antes = posicao(cobranca_chave, VENCIMENTO + timedelta(days=20))
        assert antes["juros_centavos"] == 349
        assert antes["multa_centavos"] == 0
        assert antes["total_devido_na_data_centavos"] == 105015

        segundo = receber(cobranca_chave, 105015, VENCIMENTO + timedelta(days=20))

        status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": (VENCIMENTO + timedelta(days=15)).isoformat()})
        assert status == 422
        assert response["code"] == "QIT001027"

        status, response = estornar(segundo)
        assert status == 201
        assert response["lancamentos"] == [
            {"natureza": "aluguel", "valor_centavos": -104666},
            {"natureza": "juros", "valor_centavos": -349},
        ]

        assert posicao(cobranca_chave, VENCIMENTO + timedelta(days=20)) == antes
        assert posicao(cobranca_chave, VENCIMENTO + timedelta(days=15))["status"] == "parcial"
        assert saldos(conta_chave) == {"disponivel": 50000, "reservado": 50000}

    def test_reverses_a_recebimento_that_paid_only_multa_and_juros(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        data = VENCIMENTO + timedelta(days=10)

        antes = posicao(cobranca_chave, data)
        assert antes["status"] == "aberta"
        assert antes["total_devido_na_data_centavos"] == 204666

        recebimento = receber(cobranca_chave, 4666, data)
        assert posicao(cobranca_chave, data)["status"] == "parcial"

        status, response = estornar(recebimento)
        assert status == 201
        assert response["lancamentos"] == [
            {"natureza": "multa", "valor_centavos": -4000},
            {"natureza": "juros", "valor_centavos": -666},
        ]

        assert posicao(cobranca_chave, data) == antes
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_accepts_item_after_the_recebimento_that_settled_the_cobranca_is_reversed(self):
        conta = conta_com_recebimento()
        item = PayloadGenerator.create_item_payload()

        status, response = RequestGenerator.POST_cobranca_itens(conta["cobranca_chave"], item)
        assert status == 409
        assert response["code"] == "QIT001017"

        status, _response = estornar(conta["recebimento_chave"])
        assert status == 201

        status, _response = RequestGenerator.POST_cobranca_itens(conta["cobranca_chave"], item)
        assert status == 201

    def test_refuses_reversing_a_recebimento_whose_money_was_passed_on(self):
        conta = conta_com_recebimento()

        status, _response = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, response = estornar(conta["recebimento_chave"])
        assert status == 409
        assert response["code"] == "QIT001020"

        assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 50000}
        assert posicao(conta["cobranca_chave"])["status"] == "quitada"

    def test_checks_the_disponivel_before_the_reserve(self):
        conta = conta_com_recebimento()

        status, _response = repassar(conta["conta_chave"], 150000)
        assert status == 201
        status, _response = pagar_encargo(conta["conta_chave"], "condominio", 35000)
        assert status == 201

        status, response = estornar(conta["recebimento_chave"])
        assert status == 409
        assert response["code"] == "QIT001020"

        assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 15000}

    def test_checks_the_reserve_of_iptu_too(self):
        conta_chave = new_conta_chave()
        encargos = receber(
            new_cobranca_chave(
                conta_chave,
                [
                    {"natureza": "condominio", "valor_centavos": 35000},
                    {"natureza": "iptu", "valor_centavos": 15000},
                ],
                "2026-10",
            ),
            50000,
        )
        receber(new_cobranca_chave(conta_chave, [{"natureza": "condominio", "valor_centavos": 50000}], "2026-11"), 50000)

        status, _response = pagar_encargo(conta_chave, "iptu", 15000)
        assert status == 201

        status, response = estornar(encargos)
        assert status == 409
        assert response["code"] == "QIT001021"
        assert "iptu" in response["description"]

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 85000}

    def test_checks_the_reserve_of_condominio_before_iptu(self):
        conta = conta_com_recebimento()

        for natureza, valor_centavos in [("condominio", 35000), ("iptu", 15000)]:
            status, _response = pagar_encargo(conta["conta_chave"], natureza, valor_centavos)
            assert status == 201

        status, response = estornar(conta["recebimento_chave"])
        assert status == 409
        assert response["code"] == "QIT001021"
        assert "condominio" in response["description"]

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 0}

    def test_refuses_reversing_a_recebimento_whose_reserve_was_paid(self):
        conta = conta_com_recebimento()

        status, _response = pagar_encargo(conta["conta_chave"], "condominio", 35000)
        assert status == 201

        status, response = estornar(conta["recebimento_chave"])
        assert status == 409
        assert response["code"] == "QIT001021"

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 15000}
        assert posicao(conta["cobranca_chave"])["status"] == "quitada"

    def test_checks_the_reserve_of_each_natureza(self):
        conta_chave = new_conta_chave()
        so_condominio = receber(
            new_cobranca_chave(conta_chave, [{"natureza": "condominio", "valor_centavos": 35000}], "2026-10"), 35000
        )
        receber(new_cobranca_chave(conta_chave, [{"natureza": "iptu", "valor_centavos": 50000}], "2026-11"), 50000)

        status, _response = pagar_encargo(conta_chave, "condominio", 35000)
        assert status == 201

        status, response = estornar(so_condominio)
        assert status == 409
        assert response["code"] == "QIT001021"
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 50000}

        status, _response = pagar_encargo(conta_chave, "iptu", 50000)
        assert status == 201

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_keeps_the_reversed_transacao_as_it_was(self):
        conta = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, repasse = repassar(conta["conta_chave"], 150000, idempotency_key)
        assert status == 201

        status, _response = estornar(repasse["transacao_chave"])
        assert status == 201

        status, response = repassar(conta["conta_chave"], 150000, idempotency_key)
        assert status == 200
        assert response == repasse

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_reversing_the_same_transacao_twice(self):
        conta = conta_com_recebimento()

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, _response = estornar(repasse["transacao_chave"])
        assert status == 201

        status, response = estornar(repasse["transacao_chave"])
        assert status == 409
        assert response["code"] == "QIT001024"

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_reversing_a_recebimento_twice(self):
        conta = conta_com_recebimento()

        status, _response = estornar(conta["recebimento_chave"])
        assert status == 201

        status, response = estornar(conta["recebimento_chave"])
        assert status == 409
        assert response["code"] == "QIT001024"

        assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 0}

    def test_refuses_reversing_an_estorno(self):
        conta = conta_com_recebimento()

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, estorno = estornar(repasse["transacao_chave"])
        assert status == 201

        status, response = estornar(estorno["transacao_chave"])
        assert status == 409
        assert response["code"] == "QIT001024"

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_ignores_a_body_sent_to_the_estorno(self):
        conta = conta_com_recebimento()
        endpoint = f"/transacoes/{conta['recebimento_chave']}/estornos"
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": str(uuid4())}

        first = ClientRequisition.send("POST", endpoint, payload={"valor_centavos": 1000}, headers=headers)
        assert first.response_status == 201
        assert len(first.response_json["lancamentos"]) == 3
        assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 0}

        second = ClientRequisition.send("POST", endpoint, payload={"valor_centavos": 2000}, headers=headers)
        assert second.response_status == 200
        assert second.response_json == first.response_json

    def test_refuses_transacao_that_does_not_exist(self):
        conta = conta_com_recebimento()
        chave_real = conta["recebimento_chave"]

        for transacao_chave in [UNKNOWN_CHAVE, "abc", chave_real + " ", chave_real.upper()]:
            status, response = estornar(transacao_chave)
            assert status == 404, repr(transacao_chave)
            assert response["code"] == "QIT001023"

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_request_without_idempotency_key(self):
        conta = conta_com_recebimento()
        endpoint = f"/transacoes/{conta['recebimento_chave']}/estornos"

        response = ClientRequisition.send("POST", f"/transacoes/{UNKNOWN_CHAVE}/estornos", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert response.response_status == 400
        assert response.response_json["code"] == "QIT000001"

        headers_list = [
            {"INTERNAL-TOKEN": INTERNAL_TOKEN},
            {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": ""},
            {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": "a" * 256},
        ]

        for headers in headers_list:
            response = ClientRequisition.send("POST", endpoint, headers=headers)
            assert response.response_status == 400, headers
            assert response.response_json["code"] == "QIT000001"

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_request_without_token_and_records_nothing(self):
        conta = conta_com_recebimento()

        response = ClientRequisition.send(
            "POST",
            f"/transacoes/{conta['recebimento_chave']}/estornos",
            headers={"Idempotency-Key": "chave-sem-token"},
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_keeps_the_taxa_already_retained_after_reversing_the_aluguel(self):
        conta_chave = new_conta_chave()
        aluguel = receber(new_cobranca_chave(conta_chave, [{"natureza": "aluguel", "valor_centavos": 150000}], "2026-10"), 150000)

        status, response = repassar(conta_chave, 20000)
        assert status == 201
        assert response["taxa_centavos"] == 15000

        receber(new_cobranca_chave(conta_chave, [{"natureza": "despesa_extra", "valor_centavos": 200000}], "2026-11"), 200000)

        status, _response = estornar(aluguel)
        assert status == 201
        assert saldos(conta_chave) == {"disponivel": 180000, "reservado": 0}

        status, response = repassar(conta_chave, 180000)
        assert status == 201
        assert response["taxa_centavos"] == 0
        assert response["liquido_centavos"] == 180000

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_offsets_the_taxa_retained_on_a_reversed_aluguel(self):
        conta_chave = new_conta_chave()
        primeiro = receber(new_cobranca_chave(conta_chave, [{"natureza": "aluguel", "valor_centavos": 150000}], "2026-10"), 150000)

        status, response = repassar(conta_chave, 20000)
        assert status == 201
        assert response["taxa_centavos"] == 15000

        receber(new_cobranca_chave(conta_chave, [{"natureza": "aluguel", "valor_centavos": 150000}], "2026-11"), 150000)

        status, _response = estornar(primeiro)
        assert status == 201
        assert saldos(conta_chave) == {"disponivel": 130000, "reservado": 0}

        status, response = repassar(conta_chave, 130000)
        assert status == 201
        assert response["taxa_centavos"] == 0
        assert response["liquido_centavos"] == 130000

    def test_refuses_repasse_above_the_disponivel_when_the_taxa_pendente_passes_it(self):
        conta_chave = new_conta_chave()
        primeiro = receber(
            new_cobranca_chave(
                conta_chave,
                [
                    {"natureza": "aluguel", "valor_centavos": 100000},
                    {"natureza": "despesa_extra", "valor_centavos": 100000},
                ],
                "2026-10",
            ),
            200000,
        )

        status, response = repassar(conta_chave, 200000)
        assert status == 201
        assert response["taxa_centavos"] == 10000

        receber(new_cobranca_chave(conta_chave, [{"natureza": "aluguel", "valor_centavos": 200000}], "2026-11"), 200000)

        status, _response = estornar(primeiro)
        assert status == 201
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

        status, response = repassar(conta_chave, 5000)
        assert status == 409
        assert response["code"] == "QIT001020"

        receber(new_cobranca_chave(conta_chave, [{"natureza": "despesa_extra", "valor_centavos": 8000}], "2026-12"), 8000)

        status, response = repassar(conta_chave, 8000)
        assert status == 422
        assert response["code"] == "QIT001026"

        status, response = repassar(conta_chave, 8001)
        assert status == 409
        assert response["code"] == "QIT001020"

        assert saldos(conta_chave) == {"disponivel": 8000, "reservado": 0}

    def test_reverses_only_once_when_estornos_arrive_at_the_same_time(self):
        conta = conta_com_recebimento()

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_transacao_estornos, (repasse["transacao_chave"],), SIMULTANEOUS_REQUESTS
        )

        statuses = []
        for status, response in results:
            statuses.append(status)

            if status == 409:
                assert response["code"] == "QIT001024"

        assert statuses.count(201) == 1
        assert statuses.count(409) == SIMULTANEOUS_REQUESTS - 1

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

        assert saldos_pelo_extrato(extrato_completo(conta["conta_chave"])) == saldos(conta["conta_chave"])

    def test_keeps_the_saldos_consistent_when_estorno_and_repasses_arrive_at_the_same_time(self):
        conta = conta_com_recebimento()
        repasse_payload = PayloadGenerator.create_repasse_payload(30000)

        calls = [(RequestGenerator.POST_transacao_estornos, (conta["recebimento_chave"],))]
        for _call in range(SIMULTANEOUS_REQUESTS - 1):
            calls.append((RequestGenerator.POST_conta_repasses, (conta["conta_chave"], repasse_payload)))

        results = ConcurrentRequests.send_different_at_the_same_time(calls)
        estorno_status, estorno_response = results[0]

        repasses_aceitos = 0
        for status, response in results[1:]:
            if status == 201:
                repasses_aceitos = repasses_aceitos + 1
            else:
                assert status == 409
                assert response["code"] == "QIT001020"

        if estorno_status == 201:
            assert repasses_aceitos == 0
            assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 0}
        else:
            assert estorno_status == 409
            assert estorno_response["code"] == "QIT001020"
            assert repasses_aceitos == SIMULTANEOUS_REQUESTS - 1
            assert saldos(conta["conta_chave"]) == {"disponivel": 30000, "reservado": 50000}

        assert saldos_pelo_extrato(extrato_completo(conta["conta_chave"])) == saldos(conta["conta_chave"])

    def test_keeps_the_cobranca_consistent_when_estorno_and_recebimento_arrive_at_the_same_time(self):
        conta = conta_com_recebimento()
        payload = PayloadGenerator.create_recebimento_payload(200000, VENCIMENTO.isoformat())

        estorno_result, recebimento_result = ConcurrentRequests.send_different_at_the_same_time(
            [
                (RequestGenerator.POST_transacao_estornos, (conta["recebimento_chave"],)),
                (RequestGenerator.POST_cobranca_recebimentos, (conta["cobranca_chave"], payload)),
            ]
        )

        assert estorno_result[0] == 201

        if recebimento_result[0] == 201:
            assert posicao(conta["cobranca_chave"])["status"] == "quitada"
            assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}
        else:
            assert recebimento_result[0] == 422
            assert recebimento_result[1]["code"] == "QIT001019"
            assert posicao(conta["cobranca_chave"])["status"] == "aberta"
            assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 0}

        assert saldos_pelo_extrato(extrato_completo(conta["conta_chave"])) == saldos(conta["conta_chave"])

    def test_keeps_the_imputacao_in_order_when_estorno_and_a_later_recebimento_arrive_at_the_same_time(self):
        payload = PayloadGenerator.create_recebimento_payload(150000, VENCIMENTO.isoformat())

        for _rodada in range(SIMULTANEOUS_REQUESTS):
            conta_chave = new_conta_chave()
            cobranca_chave = new_cobranca_chave(conta_chave)
            primeiro = receber(cobranca_chave, 50000)

            estorno_result, recebimento_result = ConcurrentRequests.send_different_at_the_same_time(
                [
                    (RequestGenerator.POST_transacao_estornos, (primeiro,)),
                    (RequestGenerator.POST_cobranca_recebimentos, (cobranca_chave, payload)),
                ]
            )

            assert recebimento_result[0] == 201

            if estorno_result[0] == 201:
                assert recebimento_result[1]["rateio"] == [
                    {"natureza": "condominio", "valor_centavos": 35000},
                    {"natureza": "iptu", "valor_centavos": 15000},
                    {"natureza": "aluguel", "valor_centavos": 100000},
                ]
                assert posicao(cobranca_chave)["status"] == "parcial"
                assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 50000}
            else:
                assert estorno_result[0] == 409
                assert estorno_result[1]["code"] == "QIT001028"
                assert recebimento_result[1]["rateio"] == [{"natureza": "aluguel", "valor_centavos": 150000}]
                assert posicao(cobranca_chave)["status"] == "quitada"
                assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

            assert saldos_pelo_extrato(extrato_completo(conta_chave)) == saldos(conta_chave)

    def test_keeps_the_reserve_right_when_estorno_and_encargo_arrive_at_the_same_time(self):
        conta = conta_com_recebimento()
        encargo_payload = PayloadGenerator.create_encargo_payload("condominio", 35000)

        estorno_result, encargo_result = ConcurrentRequests.send_different_at_the_same_time(
            [
                (RequestGenerator.POST_transacao_estornos, (conta["recebimento_chave"],)),
                (RequestGenerator.POST_conta_encargo_pagamentos, (conta["conta_chave"], encargo_payload)),
            ]
        )

        if estorno_result[0] == 201:
            assert encargo_result[0] == 409
            assert encargo_result[1]["code"] == "QIT001021"
            assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 0}
        else:
            assert estorno_result[0] == 409
            assert estorno_result[1]["code"] == "QIT001021"
            assert encargo_result[0] == 201
            assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 15000}

        assert saldos_pelo_extrato(extrato_completo(conta["conta_chave"])) == saldos(conta["conta_chave"])

    def test_keeps_the_cobranca_consistent_when_estorno_and_item_arrive_at_the_same_time(self):
        conta = conta_com_recebimento()
        item = PayloadGenerator.create_item_payload()

        estorno_result, item_result = ConcurrentRequests.send_different_at_the_same_time(
            [
                (RequestGenerator.POST_transacao_estornos, (conta["recebimento_chave"],)),
                (RequestGenerator.POST_cobranca_itens, (conta["cobranca_chave"], item)),
            ]
        )

        assert estorno_result[0] == 201

        if item_result[0] == 201:
            assert len(posicao(conta["cobranca_chave"], today_in_sao_paulo())["itens"]) == 4
        else:
            assert item_result[0] == 409
            assert item_result[1]["code"] == "QIT001017"
            assert len(posicao(conta["cobranca_chave"], today_in_sao_paulo())["itens"]) == 3

        assert saldos_pelo_extrato(extrato_completo(conta["conta_chave"])) == saldos(conta["conta_chave"])


class TestEstornoIdempotencia:
    def test_returns_the_original_result_when_repeated(self):
        conta = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, first_response = estornar(repasse["transacao_chave"], idempotency_key)
        assert status == 201

        status, second_response = estornar(repasse["transacao_chave"], idempotency_key)
        assert status == 200
        assert second_response == first_response

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_ignores_spaces_and_tabs_around_the_key(self):
        conta = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, first_response = estornar(repasse["transacao_chave"], idempotency_key)
        assert status == 201

        for variante in [idempotency_key + " ", idempotency_key + "\t"]:
            status, response = estornar(repasse["transacao_chave"], variante)
            assert status == 200, repr(variante)
            assert response == first_response

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_the_same_key_on_another_transacao_of_the_conta(self):
        conta = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, primeiro = repassar(conta["conta_chave"], 50000)
        assert status == 201
        status, segundo = repassar(conta["conta_chave"], 50000)
        assert status == 201

        status, _response = estornar(primeiro["transacao_chave"], idempotency_key)
        assert status == 201

        status, response = estornar(segundo["transacao_chave"], idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001022"

        assert saldos(conta["conta_chave"]) == {"disponivel": 100000, "reservado": 50000}

    def test_refuses_a_key_already_used_by_another_operation_of_the_conta(self):
        conta = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, repasse = repassar(conta["conta_chave"], 50000, idempotency_key)
        assert status == 201

        status, response = estornar(repasse["transacao_chave"], idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001022"

        assert saldos(conta["conta_chave"]) == {"disponivel": 100000, "reservado": 50000}

    def test_accepts_the_same_key_on_another_conta(self):
        idempotency_key = str(uuid4())

        for _conta in range(2):
            conta = conta_com_recebimento()

            status, repasse = repassar(conta["conta_chave"], 150000)
            assert status == 201

            status, _response = estornar(repasse["transacao_chave"], idempotency_key)
            assert status == 201

            assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

    def test_runs_again_after_a_failed_attempt_with_the_same_key(self):
        conta = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        status, response = estornar(conta["recebimento_chave"], idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001020"

        status, _response = estornar(repasse["transacao_chave"])
        assert status == 201

        status, _response = estornar(conta["recebimento_chave"], idempotency_key)
        assert status == 201

        assert saldos(conta["conta_chave"]) == {"disponivel": 0, "reservado": 0}

    def test_processes_simultaneous_repetitions_only_once(self):
        conta = conta_com_recebimento()

        status, repasse = repassar(conta["conta_chave"], 150000)
        assert status == 201

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_transacao_estornos, (repasse["transacao_chave"], str(uuid4())), SIMULTANEOUS_REQUESTS
        )

        statuses = []
        bodies = []
        for status, response in results:
            statuses.append(status)
            bodies.append(response)

        assert statuses.count(201) == 1
        assert statuses.count(200) == SIMULTANEOUS_REQUESTS - 1
        for body in bodies:
            assert body == bodies[0]

        assert saldos(conta["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}

        assert saldos_pelo_extrato(extrato_completo(conta["conta_chave"])) == saldos(conta["conta_chave"])
