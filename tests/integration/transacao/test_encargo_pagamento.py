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
SO_ALUGUEL = [{"natureza": "aluguel", "valor_centavos": 150000}]


def new_conta_chave() -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]


def conta_com_recebimento(valor_centavos: int = 200000, itens: list = None) -> str:
    conta_chave = new_conta_chave()
    cobranca_chave = ObjectGenerator.create_cobranca(conta_chave, vencimento=VENCIMENTO.isoformat(), itens=itens)[
        "cobranca_chave"
    ]
    ObjectGenerator.create_recebimento(cobranca_chave, valor_centavos, VENCIMENTO.isoformat())

    return conta_chave


def pagar_encargo(conta_chave: str, natureza: str, valor_centavos: int, idempotency_key: str = None) -> tuple:
    payload = PayloadGenerator.create_encargo_payload(natureza, valor_centavos)

    return RequestGenerator.POST_conta_encargo_pagamentos(conta_chave, payload, idempotency_key)


def repassar(conta_chave: str, valor_centavos: int, idempotency_key: str = None) -> tuple:
    payload = PayloadGenerator.create_repasse_payload(valor_centavos)

    return RequestGenerator.POST_conta_repasses(conta_chave, payload, idempotency_key)


def saldos(conta_chave: str) -> dict:
    status, response = RequestGenerator.GET_conta_saldo(conta_chave)
    assert status == 200

    return {
        "disponivel": response["saldo_disponivel_centavos"],
        "reservado": response["saldo_reservado_centavos"],
    }


class TestEncargoPagamento:
    def test_pays_condominio_with_the_reserved_money(self):
        conta_chave = conta_com_recebimento()

        status, response = pagar_encargo(conta_chave, "condominio", 35000)
        assert status == 201
        assert re.fullmatch(UUID_PATTERN, response["transacao_chave"])
        assert response == {
            "transacao_chave": response["transacao_chave"],
            "natureza": "condominio",
            "valor_centavos": 35000,
        }

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 15000}

    def test_pays_iptu_with_the_reserved_money(self):
        conta_chave = conta_com_recebimento()

        status, response = pagar_encargo(conta_chave, "iptu", 15000)
        assert status == 201
        assert response["natureza"] == "iptu"
        assert response["valor_centavos"] == 15000

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 35000}

    def test_pays_each_encargo_from_its_own_reserve(self):
        conta_chave = conta_com_recebimento()

        status, _response = pagar_encargo(conta_chave, "iptu", 15000)
        assert status == 201

        status, response = pagar_encargo(conta_chave, "iptu", 1)
        assert status == 409
        assert response["code"] == "QIT001021"

        status, _response = pagar_encargo(conta_chave, "condominio", 35000)
        assert status == 201

        status, response = pagar_encargo(conta_chave, "condominio", 1)
        assert status == 409
        assert response["code"] == "QIT001021"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 0}

    def test_refuses_when_the_natureza_has_not_enough_reserved_even_if_the_total_has(self):
        conta_chave = conta_com_recebimento()

        status, response = pagar_encargo(conta_chave, "iptu", 15001)
        assert status == 409
        assert response["code"] == "QIT001021"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_counts_what_was_already_paid_from_the_natureza(self):
        conta_chave = conta_com_recebimento()

        status, _response = pagar_encargo(conta_chave, "condominio", 20000)
        assert status == 201

        status, response = pagar_encargo(conta_chave, "condominio", 20000)
        assert status == 409
        assert response["code"] == "QIT001021"

        status, _response = pagar_encargo(conta_chave, "condominio", 15000)
        assert status == 201

        status, response = pagar_encargo(conta_chave, "condominio", 1)
        assert status == 409
        assert response["code"] == "QIT001021"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 15000}

    def test_does_not_pay_the_whole_encargo_with_a_partial_reserve(self):
        conta_chave = conta_com_recebimento(20000)
        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 20000}

        status, response = pagar_encargo(conta_chave, "condominio", 35000)
        assert status == 409
        assert response["code"] == "QIT001021"

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": 20000}

    def test_refuses_encargo_on_a_conta_without_reserve(self):
        conta_chave = conta_com_recebimento(150000, SO_ALUGUEL)

        for natureza in ["condominio", "iptu"]:
            status, response = pagar_encargo(conta_chave, natureza, 1)
            assert status == 409, natureza
            assert response["code"] == "QIT001021"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 0}

    def test_does_not_change_the_position_of_the_cobranca(self):
        conta_chave = new_conta_chave()
        cobranca_chave = ObjectGenerator.create_cobranca(conta_chave, vencimento=VENCIMENTO.isoformat())[
            "cobranca_chave"
        ]
        ObjectGenerator.create_recebimento(cobranca_chave, 180000, VENCIMENTO.isoformat())
        params = {"data": VENCIMENTO.isoformat()}

        status, posicao_antes = RequestGenerator.GET_cobranca(cobranca_chave, params)
        assert status == 200

        status, _response = pagar_encargo(conta_chave, "condominio", 35000)
        assert status == 201

        status, posicao_depois = RequestGenerator.GET_cobranca(cobranca_chave, params)
        assert status == 200
        assert posicao_depois == posicao_antes
        assert posicao_depois["status"] == "parcial"
        assert posicao_depois["total_devido_na_data_centavos"] == 20000

    def test_never_uses_the_reserve_of_another_conta(self):
        conta_com_reserva = conta_com_recebimento()
        conta_sem_reserva = conta_com_recebimento(150000, SO_ALUGUEL)

        status, response = pagar_encargo(conta_sem_reserva, "condominio", 35000)
        assert status == 409
        assert response["code"] == "QIT001021"

        assert saldos(conta_com_reserva) == {"disponivel": 150000, "reservado": 50000}
        assert saldos(conta_sem_reserva) == {"disponivel": 150000, "reservado": 0}

    def test_refuses_valor_not_positive(self):
        conta_chave = conta_com_recebimento()

        for valor_centavos in [0, -1, -35000]:
            status, response = pagar_encargo(conta_chave, "condominio", valor_centavos)
            assert status == 422, valor_centavos
            assert response["code"] == "QIT001018"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_a_generic_natureza_naming_the_field(self):
        conta_chave = conta_com_recebimento()
        payloads = [
            {"valor_centavos": 1000},
            {"natureza": "", "valor_centavos": 1000},
            {"natureza": "aluguel", "valor_centavos": 1000},
            {"natureza": "despesa_extra", "valor_centavos": 1000},
            {"natureza": "multa", "valor_centavos": 1000},
            {"natureza": "juros", "valor_centavos": 1000},
            {"natureza": "taxa", "valor_centavos": 1000},
            {"natureza": "repasse", "valor_centavos": 1000},
            {"natureza": "CONDOMINIO", "valor_centavos": 1000},
            {"natureza": "condominio ", "valor_centavos": 1000},
            {"natureza": None, "valor_centavos": 1000},
        ]

        for payload in payloads:
            status, response = RequestGenerator.POST_conta_encargo_pagamentos(conta_chave, payload)
            assert status == 400, payload
            assert response["code"] == "QIT000001"
            assert "natureza" in response["description"], payload

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_schema_refuses_invalid_body(self):
        conta_chave = conta_com_recebimento()
        payloads = [
            {},
            {"natureza": "condominio"},
            {"natureza": "condominio", "valor_centavos": 1000.0},
            {"natureza": "condominio", "valor_centavos": "1000"},
            {"natureza": "condominio", "valor_centavos": True},
            {"natureza": "condominio", "valor_centavos": None},
            {"natureza": "condominio", "valor_centavos": MAXIMUM_CENTAVOS + 1},
            {"natureza": "condominio", "valor_centavos": 1000, "credor": "Condominio Flores"},
        ]

        for payload in payloads:
            status, response = RequestGenerator.POST_conta_encargo_pagamentos(conta_chave, payload)
            assert status == 400, payload
            assert response["code"] == "QIT000001"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_conta_that_does_not_exist(self):
        conta_chave = conta_com_recebimento()

        for chave in [UNKNOWN_CHAVE, "abc", conta_chave + " ", conta_chave.upper()]:
            status, response = pagar_encargo(chave, "condominio", 1000)
            assert status == 404, repr(chave)
            assert response["code"] == "QIT001011"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_refuses_request_without_idempotency_key(self):
        conta_chave = conta_com_recebimento()
        payload = PayloadGenerator.create_encargo_payload("condominio", 1000)
        endpoint = f"/contas/{conta_chave}/encargos/pagamentos"

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
        payload = PayloadGenerator.create_encargo_payload("condominio", 1000)

        response = ClientRequisition.send(
            "POST",
            f"/contas/{conta_chave}/encargos/pagamentos",
            payload=payload,
            headers={"Idempotency-Key": "chave-sem-token"},
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_never_pays_more_than_reserved_when_payments_arrive_at_the_same_time(self):
        conta_chave = conta_com_recebimento()
        payload = PayloadGenerator.create_encargo_payload("condominio", 10000)

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_conta_encargo_pagamentos, (conta_chave, payload), SIMULTANEOUS_REQUESTS
        )

        statuses = []
        for status, response in results:
            statuses.append(status)

            if status == 409:
                assert response["code"] == "QIT001021"

        assert statuses.count(201) == 3
        assert statuses.count(409) == SIMULTANEOUS_REQUESTS - 3

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 20000}


class TestEncargoPagamentoIdempotencia:
    def test_returns_the_original_result_when_repeated(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, first_response = pagar_encargo(conta_chave, "condominio", 35000, idempotency_key)
        assert status == 201

        status, second_response = pagar_encargo(conta_chave, "condominio", 35000, idempotency_key)
        assert status == 200
        assert second_response == first_response

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 15000}

    def test_returns_the_original_result_even_when_the_reserve_is_gone(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, first_response = pagar_encargo(conta_chave, "iptu", 15000, idempotency_key)
        assert status == 201

        status, second_response = pagar_encargo(conta_chave, "iptu", 15000, idempotency_key)
        assert status == 200
        assert second_response == first_response

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 35000}

    def test_accepts_the_same_body_with_the_keys_in_another_order(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, first_response = RequestGenerator.POST_conta_encargo_pagamentos(
            conta_chave, {"natureza": "condominio", "valor_centavos": 35000}, idempotency_key
        )
        assert status == 201

        status, second_response = RequestGenerator.POST_conta_encargo_pagamentos(
            conta_chave, {"valor_centavos": 35000, "natureza": "condominio"}, idempotency_key
        )
        assert status == 200
        assert second_response == first_response

    def test_refuses_the_same_key_with_another_body(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, _response = pagar_encargo(conta_chave, "condominio", 10000, idempotency_key)
        assert status == 201

        for natureza, valor_centavos in [("condominio", 10001), ("iptu", 10000)]:
            status, response = pagar_encargo(conta_chave, natureza, valor_centavos, idempotency_key)
            assert status == 409, (natureza, valor_centavos)
            assert response["code"] == "QIT001022"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 40000}

    def test_refuses_a_key_already_used_by_another_operation_of_the_conta(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, _response = repassar(conta_chave, 50000, idempotency_key)
        assert status == 201

        status, response = pagar_encargo(conta_chave, "condominio", 10000, idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001022"

        assert saldos(conta_chave) == {"disponivel": 100000, "reservado": 50000}

    def test_refuses_a_key_already_used_by_a_recebimento_of_the_conta(self):
        conta_chave = new_conta_chave()
        cobranca_chave = ObjectGenerator.create_cobranca(conta_chave, vencimento=VENCIMENTO.isoformat())[
            "cobranca_chave"
        ]
        idempotency_key = str(uuid4())

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave,
            PayloadGenerator.create_recebimento_payload(200000, VENCIMENTO.isoformat()),
            idempotency_key,
        )
        assert status == 201

        status, response = pagar_encargo(conta_chave, "condominio", 35000, idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001022"

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 50000}

    def test_accepts_the_same_key_on_another_conta(self):
        idempotency_key = str(uuid4())

        for _conta in range(2):
            conta_chave = conta_com_recebimento()

            status, _response = pagar_encargo(conta_chave, "condominio", 35000, idempotency_key)
            assert status == 201

            assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 15000}

    def test_runs_again_after_a_failed_attempt_with_the_same_key(self):
        conta_chave = conta_com_recebimento()
        idempotency_key = str(uuid4())

        status, _response = pagar_encargo(conta_chave, "condominio", 30000)
        assert status == 201

        status, response = pagar_encargo(conta_chave, "condominio", 35000, idempotency_key)
        assert status == 409
        assert response["code"] == "QIT001021"

        cobranca_chave = ObjectGenerator.create_cobranca(
            conta_chave, vencimento=VENCIMENTO.isoformat(), competencia="2026-11"
        )["cobranca_chave"]
        ObjectGenerator.create_recebimento(cobranca_chave, 35000, VENCIMENTO.isoformat())

        status, _response = pagar_encargo(conta_chave, "condominio", 35000, idempotency_key)
        assert status == 201

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 20000}

    def test_processes_simultaneous_repetitions_only_once(self):
        conta_chave = conta_com_recebimento()
        payload = PayloadGenerator.create_encargo_payload("condominio", 35000)

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_conta_encargo_pagamentos,
            (conta_chave, payload, str(uuid4())),
            SIMULTANEOUS_REQUESTS,
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

        assert saldos(conta_chave) == {"disponivel": 150000, "reservado": 15000}
