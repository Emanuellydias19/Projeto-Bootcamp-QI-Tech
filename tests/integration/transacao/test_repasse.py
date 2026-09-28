import re
from datetime import timedelta
from uuid import uuid4

from tests.utils import (
    INTERNAL_TOKEN,
    UUID_PATTERN,
    ConcurrentRequests,
    ObjectGenerator,
    PayloadGenerator,
    RequestGenerator,
    today_in_sao_paulo,
)
from tests.utils.requisition import ClientRequisition


UNKNOWN_CHAVE = "00000000-0000-0000-0000-000000000000"
MAXIMUM_CENTAVOS = 9007199254740991
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


def receber(cobranca_chave: str, valor_centavos: int) -> None:
    ObjectGenerator.create_recebimento(cobranca_chave, valor_centavos, VENCIMENTO.isoformat())


def conta_com_recebimento(taxa_administracao_bps: int = None) -> str:
    conta_chave = new_conta_chave(taxa_administracao_bps)
    receber(new_cobranca_chave(conta_chave), 200000)

    return conta_chave


def repassar(conta_chave: str, valor_centavos: int, idempotency_key: str = None) -> tuple:
    payload = PayloadGenerator.create_repasse_payload(valor_centavos)

    return RequestGenerator.POST_conta_repasses(conta_chave, payload, idempotency_key)


def pagar_encargo(conta_chave: str, natureza: str, valor_centavos: int, idempotency_key: str = None) -> tuple:
    payload = PayloadGenerator.create_encargo_payload(natureza, valor_centavos)

    return RequestGenerator.POST_conta_encargo_pagamentos(conta_chave, payload, idempotency_key)


def saldos(conta_chave: str) -> dict:
    status, response = RequestGenerator.GET_conta_saldo(conta_chave)
    assert status == 200

    return {
        "disponivel": response["saldo_disponivel_centavos"],
        "reservado": response["saldo_reservado_centavos"],
    }


def valores(response: dict) -> dict:
    return {
        "valor_bruto_centavos": response["valor_bruto_centavos"],
        "taxa_centavos": response["taxa_centavos"],
        "liquido_centavos": response["liquido_centavos"],
    }


class TestRepasse:
    def test_retains_the_taxa_over_the_aluguel_and_records_the_liquido(self):
        conta_chave = conta_com_recebimento()

        status, response = repassar(conta_chave, 150000)
        assert status == 201
        assert re.fullmatch(UUID_PATTERN, response["transacao_chave"])
        assert response == {
            "transacao_chave": response["transacao_chave"],
            "valor_bruto_centavos": 150000,
            "taxa_centavos": 15000,
            "liquido_centavos": 135000,
        }

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 50000}

    def test_charges_the_taxa_only_over_the_aluguel(self):
        conta_chave = new_conta_chave()
        itens = [
            {"natureza": "aluguel", "valor_centavos": 100000},
            {"natureza": "despesa_extra", "valor_centavos": 8000},
            {"natureza": "condominio", "valor_centavos": 35000},
        ]
        cobranca_chave = new_cobranca_chave(conta_chave, itens)
        hoje = today_in_sao_paulo().isoformat()

        status, posicao = RequestGenerator.GET_cobranca(cobranca_chave, {"data": hoje})
        assert status == 200
        assert posicao["multa_centavos"] > 0
        assert posicao["juros_centavos"] > 0

        ObjectGenerator.create_recebimento(cobranca_chave, posicao["total_devido_na_data_centavos"], hoje)
        disponivel = saldos(conta_chave)["disponivel"]
        assert disponivel == posicao["total_devido_na_data_centavos"] - 35000

        status, response = repassar(conta_chave, disponivel)
        assert status == 201
        assert valores(response) == {
            "valor_bruto_centavos": disponivel,
            "taxa_centavos": 10000,
            "liquido_centavos": disponivel - 10000,
        }

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 35000}

    def test_truncates_the_taxa_down(self):
        conta_chave = new_conta_chave()
        receber(new_cobranca_chave(conta_chave, [{"natureza": "aluguel", "valor_centavos": 100009}]), 100009)

        status, response = repassar(conta_chave, 100009)
        assert status == 201
        assert valores(response) == {
            "valor_bruto_centavos": 100009,
            "taxa_centavos": 10000,
            "liquido_centavos": 90009,
        }

    def test_retains_the_taxa_only_once_across_repasses(self):
        conta_chave = conta_com_recebimento()

        esperados = [
            {"valor_bruto_centavos": 50000, "taxa_centavos": 15000, "liquido_centavos": 35000},
            {"valor_bruto_centavos": 50000, "taxa_centavos": 0, "liquido_centavos": 50000},
            {"valor_bruto_centavos": 50000, "taxa_centavos": 0, "liquido_centavos": 50000},
        ]

        for esperado in esperados:
            status, response = repassar(conta_chave, 50000)
            assert status == 201
            assert valores(response) == esperado

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 50000}

    def test_truncates_the_taxa_over_the_total_aluguel_received(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave, [{"natureza": "aluguel", "valor_centavos": 100010}])

        receber(cobranca_chave, 50005)
        status, response = repassar(conta_chave, 50005)
        assert status == 201
        assert valores(response) == {"valor_bruto_centavos": 50005, "taxa_centavos": 5000, "liquido_centavos": 45005}

        receber(cobranca_chave, 50005)
        status, response = repassar(conta_chave, 50005)
        assert status == 201
        assert valores(response) == {"valor_bruto_centavos": 50005, "taxa_centavos": 5001, "liquido_centavos": 45004}

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_does_not_retain_taxa_when_the_conta_has_no_taxa(self):
        conta_chave = conta_com_recebimento(taxa_administracao_bps=0)

        status, response = repassar(conta_chave, 150000)
        assert status == 201
        assert valores(response) == {"valor_bruto_centavos": 150000, "taxa_centavos": 0, "liquido_centavos": 150000}

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 50000}

    def test_computes_the_taxa_with_the_lancamentos_of_the_conta_only(self):
        for _conta in range(2):
            conta_chave = conta_com_recebimento()

            status, response = repassar(conta_chave, 150000)
            assert status == 201
            assert response["taxa_centavos"] == 15000

        conta_sem_aluguel = new_conta_chave()
        receber(new_cobranca_chave(conta_sem_aluguel, [{"natureza": "despesa_extra", "valor_centavos": 8000}]), 8000)

        status, response = repassar(conta_sem_aluguel, 8000)
        assert status == 201
        assert response["taxa_centavos"] == 0

    def test_computes_the_taxa_exactly_with_the_largest_value(self):
        conta_chave = new_conta_chave(taxa_administracao_bps=9999)
        receber(
            new_cobranca_chave(conta_chave, [{"natureza": "aluguel", "valor_centavos": MAXIMUM_CENTAVOS}]),
            MAXIMUM_CENTAVOS,
        )

        status, response = repassar(conta_chave, MAXIMUM_CENTAVOS)
        assert status == 201
        assert valores(response) == {
            "valor_bruto_centavos": MAXIMUM_CENTAVOS,
            "taxa_centavos": 9006298534815516,
            "liquido_centavos": 900719925475,
        }

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_retains_a_taxa_of_100_percent_only_with_money_that_is_not_aluguel(self):
        conta_chave = new_conta_chave(taxa_administracao_bps=10000)
        cobranca_chave = new_cobranca_chave(
            conta_chave,
            [
                {"natureza": "aluguel", "valor_centavos": 100000},
                {"natureza": "despesa_extra", "valor_centavos": 5000},
            ],
        )
        receber(cobranca_chave, 100000)

        status, response = repassar(conta_chave, 100000)
        assert status == 422
        assert response["code"] == "QIT001026"

        status, response = repassar(conta_chave, 100001)
        assert status == 409
        assert response["code"] == "QIT001020"

        assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 0}

        receber(cobranca_chave, 5000)

        status, response = repassar(conta_chave, 105000)
        assert status == 201
        assert valores(response) == {"valor_bruto_centavos": 105000, "taxa_centavos": 100000, "liquido_centavos": 5000}

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_follows_the_example_of_the_contract(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        receber(cobranca_chave, 180000)

        status, response = repassar(conta_chave, 150000)
        assert status == 409
        assert response["code"] == "QIT001020"

        status, response = pagar_encargo(conta_chave, "condominio", 35000)
        assert status == 201
        assert response["natureza"] == "condominio"
        assert response["valor_centavos"] == 35000

        receber(cobranca_chave, 20000)

        status, response = repassar(conta_chave, 150000)
        assert status == 201
        assert valores(response) == {"valor_bruto_centavos": 150000, "taxa_centavos": 15000, "liquido_centavos": 135000}

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 15000}

    def test_does_not_retain_taxa_over_money_that_is_not_aluguel(self):
        conta_chave = new_conta_chave()
        receber(new_cobranca_chave(conta_chave, [{"natureza": "despesa_extra", "valor_centavos": 8000}]), 8000)

        status, response = repassar(conta_chave, 8000)
        assert status == 201
        assert valores(response) == {"valor_bruto_centavos": 8000, "taxa_centavos": 0, "liquido_centavos": 8000}

    def test_refuses_valor_above_the_disponivel(self):
        conta_chave = conta_com_recebimento()

        status, response = repassar(conta_chave, 150001)
        assert status == 409
        assert response["code"] == "QIT001020"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_repasse_on_a_conta_without_disponivel(self):
        conta_chave = new_conta_chave()

        status, response = repassar(conta_chave, 1)
        assert status == 409
        assert response["code"] == "QIT001020"

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 0}

    def test_refuses_valor_not_above_the_taxa_pendente(self):
        conta_chave = conta_com_recebimento()

        for valor_centavos in [1, 14999, 15000]:
            status, response = repassar(conta_chave, valor_centavos)
            assert status == 422, valor_centavos
            assert response["code"] == "QIT001026"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

        status, response = repassar(conta_chave, 15001)
        assert status == 201
        assert valores(response) == {"valor_bruto_centavos": 15001, "taxa_centavos": 15000, "liquido_centavos": 1}

        assert saldos(conta_chave) == {"disponivel": 134999, "reservado": 50000}

    def test_refuses_valor_not_positive_before_looking_at_the_taxa(self):
        conta_chave = conta_com_recebimento()

        for valor_centavos in [0, -1, -150000]:
            status, response = repassar(conta_chave, valor_centavos)
            assert status == 422, valor_centavos
            assert response["code"] == "QIT001018"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_never_uses_the_disponivel_of_another_conta(self):
        conta_com_dinheiro = conta_com_recebimento()
        conta_sem_dinheiro = new_conta_chave()

        status, response = repassar(conta_sem_dinheiro, 50000)
        assert status == 409
        assert response["code"] == "QIT001020"

        assert saldos(conta_com_dinheiro) == {"disponivel": 150000, "reservado": 50000}
        assert saldos(conta_sem_dinheiro) == {"disponivel": 0, "reservado": 0}

    def test_schema_refuses_invalid_body(self):
        conta_chave = conta_com_recebimento()
        payloads = [
            {},
            {"valor_centavos": 50000.0},
            {"valor_centavos": "50000"},
            {"valor_centavos": True},
            {"valor_centavos": None},
            {"valor_centavos": MAXIMUM_CENTAVOS + 1},
            {"valor_centavos": 50000, "taxa_centavos": 0},
            {"valor_centavos": 50000, "natureza": "repasse"},
        ]

        for payload in payloads:
            status, response = RequestGenerator.POST_conta_repasses(conta_chave, payload)
            assert status == 400, payload
            assert response["code"] == "QIT000001"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_conta_that_does_not_exist(self):
        conta_chave = conta_com_recebimento()

        for chave in [UNKNOWN_CHAVE, "abc", conta_chave + " ", conta_chave.upper()]:
            status, response = repassar(chave, 50000)
            assert status == 404, repr(chave)
            assert response["code"] == "QIT001011"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_request_without_idempotency_key(self):
        conta_chave = conta_com_recebimento()
        payload = PayloadGenerator.create_repasse_payload(50000)
        endpoint = f"/contas/{conta_chave}/repasses"

        headers_list = [
            {"INTERNAL-TOKEN": INTERNAL_TOKEN},
            {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": ""},
            {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": "a" * 256},
        ]

        for headers in headers_list:
            response = ClientRequisition.send("POST", endpoint, payload=payload, headers=headers)
            assert response.response_status == 400, headers
            assert response.response_json["code"] == "QIT000001"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_request_without_token_and_records_nothing(self):
        conta_chave = conta_com_recebimento()
        payload = PayloadGenerator.create_repasse_payload(50000)

        response = ClientRequisition.send(
            "POST",
            f"/contas/{conta_chave}/repasses",
            payload=payload,
            headers={"Idempotency-Key": "chave-sem-token"},
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_never_leaves_the_disponivel_negative_when_repasses_arrive_at_the_same_time(self):
        conta_chave = conta_com_recebimento()
        payload = PayloadGenerator.create_repasse_payload(40000)

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_conta_repasses, (conta_chave, payload), SIMULTANEOUS_REQUESTS
        )

        statuses = []
        taxa_total = 0
        for status, response in results:
            statuses.append(status)

            if status == 201:
                taxa_total = taxa_total + response["taxa_centavos"]

            if status == 409:
                assert response["code"] == "QIT001020"

        assert statuses.count(201) == 3
        assert statuses.count(409) == SIMULTANEOUS_REQUESTS - 3
        assert taxa_total == 15000

        assert saldos(conta_chave) == {"disponivel": 30000, "reservado": 50000}

    def test_retains_the_taxa_only_once_when_repasses_arrive_at_the_same_time(self):
        conta_chave = conta_com_recebimento()
        payload = PayloadGenerator.create_repasse_payload(20000)

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_conta_repasses, (conta_chave, payload), SIMULTANEOUS_REQUESTS
        )

        taxas = []
        for status, response in results:
            assert status == 201
            taxas.append(response["taxa_centavos"])

        assert sorted(taxas) == [0, 0, 0, 0, 15000]

        assert saldos(conta_chave) == {"disponivel": 50000, "reservado": 50000}

    def test_keeps_both_saldos_right_when_encargos_and_repasses_arrive_at_the_same_time(self):
        conta_chave = conta_com_recebimento()
        repasse_payload = PayloadGenerator.create_repasse_payload(20000)
        encargo_payload = PayloadGenerator.create_encargo_payload("condominio", 5000)

        calls = []
        for _call in range(SIMULTANEOUS_REQUESTS):
            calls.append((RequestGenerator.POST_conta_repasses, (conta_chave, repasse_payload)))
            calls.append((RequestGenerator.POST_conta_encargo_pagamentos, (conta_chave, encargo_payload)))

        results = ConcurrentRequests.send_different_at_the_same_time(calls)

        for status, _response in results:
            assert status == 201

        assert saldos(conta_chave) == {"disponivel": 50000, "reservado": 25000}


class TestRepasseIdempotencia:
    def test_returns_the_original_result_when_repeated(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, first_response = repassar(conta_chave, 50000, idempotency_key)
        assert status == 201

        status, second_response = repassar(conta_chave, 50000, idempotency_key)
        assert status == 200
        assert second_response == first_response

        assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 50000}

    def test_returns_the_original_result_even_when_the_disponivel_is_gone(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, first_response = repassar(conta_chave, 150000, idempotency_key)
        assert status == 201
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 50000}

        status, response = repassar(conta_chave, 150000, idempotency_key)
        assert status == 200
        assert response == first_response

        receber(new_cobranca_chave(conta_chave, competencia="2026-11"), 200000)

        status, response = repassar(conta_chave, 150000, idempotency_key)
        assert status == 200
        assert response == first_response

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 100000}

    def test_refuses_the_same_key_with_another_body(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, _response = repassar(conta_chave, 50000, idempotency_key)
        assert status == 201

        status, response = repassar(conta_chave, 50001, idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001022"

        assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 50000}

    def test_refuses_a_key_already_used_by_another_operation_of_the_conta(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, _response = pagar_encargo(conta_chave, "condominio", 35000, idempotency_key)
        assert status == 201

        status, response = repassar(conta_chave, 50000, idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001022"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 15000}

    def test_refuses_a_key_already_used_by_a_recebimento_of_the_conta(self):
        conta_chave = new_conta_chave()
        idempotency_key = str(uuid4())

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            new_cobranca_chave(conta_chave),
            PayloadGenerator.create_recebimento_payload(200000, VENCIMENTO.isoformat()),
            idempotency_key,
        )
        assert status == 201

        status, response = repassar(conta_chave, 50000, idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001022"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_accepts_the_same_key_on_another_conta(self):
        idempotency_key = str(uuid4())

        for _conta in range(2):
            conta_chave = conta_com_recebimento()

            status, _response = repassar(conta_chave, 50000, idempotency_key)
            assert status == 201

            assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 50000}

    def test_runs_again_after_a_failed_attempt_with_the_same_key(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, response = repassar(conta_chave, 200000, idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001020"

        receber(new_cobranca_chave(conta_chave, competencia="2026-11"), 200000)

        status, response = repassar(conta_chave, 200000, idempotency_key)
        assert status == 201
        assert valores(response) == {"valor_bruto_centavos": 200000, "taxa_centavos": 30000, "liquido_centavos": 170000}

        assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 100000}

    def test_processes_simultaneous_repetitions_only_once(self):
        conta_chave = conta_com_recebimento()
        payload = PayloadGenerator.create_repasse_payload(50000)

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_conta_repasses, (conta_chave, payload, str(uuid4())), SIMULTANEOUS_REQUESTS
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

        assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 50000}
