import re
from datetime import date, timedelta

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
MAXIMUM_CENTAVOS = 9007199254740991
SIMULTANEOUS_REQUESTS = 5
ALUGUEL_DE_2000 = [{"natureza": "aluguel", "valor_centavos": 200000}]


def new_cobranca(vencimento: date, itens: list = None) -> dict:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]
    conta_chave = ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]
    cobranca_chave = ObjectGenerator.create_cobranca(conta_chave, vencimento=vencimento.isoformat(), itens=itens)[
        "cobranca_chave"
    ]

    return {"conta_chave": conta_chave, "cobranca_chave": cobranca_chave}


def receber(cobranca_chave: str, valor_centavos: int, pago_em: date) -> tuple:
    payload = PayloadGenerator.create_recebimento_payload(valor_centavos, pago_em.isoformat())

    return RequestGenerator.POST_cobranca_recebimentos(cobranca_chave, payload)


def saldos(conta_chave: str) -> dict:
    status, response = RequestGenerator.GET_conta_saldo(conta_chave)
    assert status == 200

    return {
        "disponivel": response["saldo_disponivel_centavos"],
        "reservado": response["saldo_reservado_centavos"],
    }


def posicao(cobranca_chave: str, data: date) -> dict:
    status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": data.isoformat()})
    assert status == 200

    return response


class TestRecebimento:
    def test_imputes_a_partial_payment_in_the_order_of_the_politica(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)

        status, response = receber(cobranca["cobranca_chave"], 180000, vencimento)
        assert status == 201
        assert re.fullmatch(UUID_PATTERN, response["transacao_chave"])
        assert response["rateio"] == [
            {"natureza": "condominio", "valor_centavos": 35000},
            {"natureza": "iptu", "valor_centavos": 15000},
            {"natureza": "aluguel", "valor_centavos": 130000},
        ]
        assert response["em_aberto"] == [{"natureza": "aluguel", "valor_centavos": 20000}]

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 130000, "reservado": 50000}

        cobranca_na_data = posicao(cobranca["cobranca_chave"], vencimento)
        assert cobranca_na_data["status"] == "parcial"
        assert cobranca_na_data["itens"] == [
            {
                "natureza": "aluguel",
                "valor_devido_centavos": 150000,
                "valor_pago_centavos": 130000,
                "valor_em_aberto_centavos": 20000,
            },
            {
                "natureza": "condominio",
                "valor_devido_centavos": 35000,
                "valor_pago_centavos": 35000,
                "valor_em_aberto_centavos": 0,
            },
            {
                "natureza": "iptu",
                "valor_devido_centavos": 15000,
                "valor_pago_centavos": 15000,
                "valor_em_aberto_centavos": 0,
            },
        ]
        assert cobranca_na_data["total_em_aberto_centavos"] == 20000
        assert cobranca_na_data["total_devido_na_data_centavos"] == 20000

    def test_keeps_a_partial_encargo_reserved(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)

        status, response = receber(cobranca["cobranca_chave"], 20000, vencimento)
        assert status == 201
        assert response["rateio"] == [{"natureza": "condominio", "valor_centavos": 20000}]
        assert response["em_aberto"] == [
            {"natureza": "condominio", "valor_centavos": 15000},
            {"natureza": "iptu", "valor_centavos": 15000},
            {"natureza": "aluguel", "valor_centavos": 150000},
        ]

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 0, "reservado": 20000}

    def test_settles_the_cobranca(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)

        status, response = receber(cobranca["cobranca_chave"], 200000, vencimento)
        assert status == 201
        assert response["em_aberto"] == []

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 150000, "reservado": 50000}
        assert posicao(cobranca["cobranca_chave"], vencimento)["status"] == "quitada"

    def test_pays_juros_and_multa_first_when_late(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento, ALUGUEL_DE_2000)

        status, response = receber(cobranca["cobranca_chave"], 204666, vencimento + timedelta(days=10))
        assert status == 201
        assert response["rateio"] == [
            {"natureza": "juros", "valor_centavos": 666},
            {"natureza": "multa", "valor_centavos": 4000},
            {"natureza": "aluguel", "valor_centavos": 200000},
        ]
        assert response["em_aberto"] == []

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 204666, "reservado": 0}

    def test_keeps_unpaid_multa_and_juros_owed(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento, ALUGUEL_DE_2000)

        status, response = receber(cobranca["cobranca_chave"], 2000, vencimento + timedelta(days=10))
        assert status == 201
        assert response["rateio"] == [
            {"natureza": "juros", "valor_centavos": 666},
            {"natureza": "multa", "valor_centavos": 1334},
        ]
        assert response["em_aberto"] == [
            {"natureza": "multa", "valor_centavos": 2666},
            {"natureza": "aluguel", "valor_centavos": 200000},
        ]

        cobranca_na_data = posicao(cobranca["cobranca_chave"], vencimento + timedelta(days=10))
        assert cobranca_na_data["status"] == "parcial"
        assert cobranca_na_data["multa_centavos"] == 2666
        assert cobranca_na_data["juros_centavos"] == 0
        assert cobranca_na_data["total_devido_na_data_centavos"] == 202666

        cobranca_na_data = posicao(cobranca["cobranca_chave"], vencimento + timedelta(days=20))
        assert cobranca_na_data["multa_centavos"] == 2666
        assert cobranca_na_data["juros_centavos"] == 667
        assert cobranca_na_data["total_devido_na_data_centavos"] == 203333

        status, response = receber(cobranca["cobranca_chave"], 203333, vencimento + timedelta(days=20))
        assert status == 201
        assert response["rateio"] == [
            {"natureza": "juros", "valor_centavos": 667},
            {"natureza": "multa", "valor_centavos": 2666},
            {"natureza": "aluguel", "valor_centavos": 200000},
        ]
        assert response["em_aberto"] == []

    def test_charges_multa_only_on_what_was_open_on_the_vencimento(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento, ALUGUEL_DE_2000)

        status, _response = receber(cobranca["cobranca_chave"], 150000, vencimento)
        assert status == 201

        cobranca_na_data = posicao(cobranca["cobranca_chave"], vencimento + timedelta(days=10))
        assert cobranca_na_data["multa_centavos"] == 1000
        assert cobranca_na_data["juros_centavos"] == 166
        assert cobranca_na_data["total_devido_na_data_centavos"] == 51166

        status, response = receber(cobranca["cobranca_chave"], 51167, vencimento + timedelta(days=10))
        assert status == 422
        assert response["code"] == "QIT001019"

        status, response = receber(cobranca["cobranca_chave"], 51166, vencimento + timedelta(days=10))
        assert status == 201
        assert response["rateio"] == [
            {"natureza": "juros", "valor_centavos": 166},
            {"natureza": "multa", "valor_centavos": 1000},
            {"natureza": "aluguel", "valor_centavos": 50000},
        ]
        assert response["em_aberto"] == []

    def test_ignores_an_item_included_after_the_payment_date(self):
        today = today_in_sao_paulo()
        cobranca = new_cobranca(today + timedelta(days=5))

        status, _response = RequestGenerator.POST_cobranca_itens(
            cobranca["cobranca_chave"], PayloadGenerator.create_item_payload(valor_centavos=30000)
        )
        assert status == 201

        status, response = receber(cobranca["cobranca_chave"], 230000, today - timedelta(days=1))
        assert status == 422
        assert response["code"] == "QIT001019"

        status, response = receber(cobranca["cobranca_chave"], 200000, today - timedelta(days=1))
        assert status == 201
        assert response["em_aberto"] == []

        cobranca_hoje = posicao(cobranca["cobranca_chave"], today)
        assert cobranca_hoje["status"] == "parcial"
        assert cobranca_hoje["total_em_aberto_centavos"] == 30000

    def test_sees_an_item_included_while_waiting_for_the_lock(self):
        today = today_in_sao_paulo()

        for _round in range(10):
            cobranca = new_cobranca(today + timedelta(days=5))
            item_payload = PayloadGenerator.create_item_payload(valor_centavos=8000)
            recebimento_payload = PayloadGenerator.create_recebimento_payload(200000, today.isoformat())

            item_result, recebimento_result = ConcurrentRequests.send_different_at_the_same_time(
                [
                    (RequestGenerator.POST_cobranca_itens, (cobranca["cobranca_chave"], item_payload)),
                    (RequestGenerator.POST_cobranca_recebimentos, (cobranca["cobranca_chave"], recebimento_payload)),
                ]
            )
            item_status, item_response = item_result
            recebimento_status, recebimento_response = recebimento_result

            assert recebimento_status == 201

            if item_status == 201:
                assert recebimento_response["em_aberto"] == [{"natureza": "despesa_extra", "valor_centavos": 8000}]
            else:
                assert item_status == 409
                assert item_response["code"] == "QIT001017"
                assert recebimento_response["em_aberto"] == []

    def test_accepts_idempotency_key_with_1_to_255_characters(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)

        for idempotency_key in ["b", "a" * 255]:
            payload = PayloadGenerator.create_recebimento_payload(1000, vencimento.isoformat())

            status, _response = RequestGenerator.POST_cobranca_recebimentos(
                cobranca["cobranca_chave"], payload, idempotency_key
            )
            assert status == 201, len(idempotency_key)

    def test_charges_juros_only_on_what_is_still_open(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento, ALUGUEL_DE_2000)

        status, response = receber(cobranca["cobranca_chave"], 104666, vencimento + timedelta(days=10))
        assert status == 201
        assert response["em_aberto"] == [{"natureza": "aluguel", "valor_centavos": 100000}]

        cobranca_na_data = posicao(cobranca["cobranca_chave"], vencimento + timedelta(days=20))
        assert cobranca_na_data["multa_centavos"] == 0
        assert cobranca_na_data["juros_centavos"] == 334
        assert cobranca_na_data["total_devido_na_data_centavos"] == 100334

    def test_imputes_each_despesa_extra_in_the_order_it_was_included(self):
        vencimento = today_in_sao_paulo() + timedelta(days=5)
        cobranca = new_cobranca(vencimento, [{"natureza": "aluguel", "valor_centavos": 10000}])

        for valor in [3000, 4000]:
            status, _response = RequestGenerator.POST_cobranca_itens(
                cobranca["cobranca_chave"], PayloadGenerator.create_item_payload(valor_centavos=valor)
            )
            assert status == 201

        status, response = receber(cobranca["cobranca_chave"], 15000, today_in_sao_paulo())
        assert status == 201
        assert response["rateio"] == [
            {"natureza": "aluguel", "valor_centavos": 10000},
            {"natureza": "despesa_extra", "valor_centavos": 3000},
            {"natureza": "despesa_extra", "valor_centavos": 2000},
        ]
        assert response["em_aberto"] == [{"natureza": "despesa_extra", "valor_centavos": 2000}]

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 15000, "reservado": 0}

    def test_refuses_valor_above_what_is_owed_on_the_date(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento, ALUGUEL_DE_2000)

        for valor, pago_em in [(200001, vencimento), (204667, vencimento + timedelta(days=10))]:
            status, response = receber(cobranca["cobranca_chave"], valor, pago_em)
            assert status == 422, valor
            assert response["code"] == "QIT001019"

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 0, "reservado": 0}
        assert posicao(cobranca["cobranca_chave"], vencimento)["status"] == "aberta"

    def test_refuses_valor_not_positive(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)

        for valor in [0, -1]:
            status, response = receber(cobranca["cobranca_chave"], valor, vencimento)
            assert status == 422, valor
            assert response["code"] == "QIT001018"

    def test_refuses_pago_em_in_the_future(self):
        cobranca = new_cobranca(today_in_sao_paulo() - timedelta(days=30))

        status, response = receber(cobranca["cobranca_chave"], 1000, today_in_sao_paulo() + timedelta(days=1))
        assert status == 422
        assert response["code"] == "QIT001027"

    def test_refuses_pago_em_before_the_last_recebimento(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)

        status, _response = receber(cobranca["cobranca_chave"], 1000, vencimento + timedelta(days=10))
        assert status == 201

        status, response = receber(cobranca["cobranca_chave"], 1000, vencimento + timedelta(days=5))
        assert status == 422
        assert response["code"] == "QIT001027"

        status, _response = receber(cobranca["cobranca_chave"], 1000, vencimento + timedelta(days=10))
        assert status == 201

    def test_refuses_pago_em_that_does_not_exist_in_the_calendar(self):
        cobranca = new_cobranca(today_in_sao_paulo() - timedelta(days=30))

        payload = PayloadGenerator.create_recebimento_payload(1000, "2026-02-30")

        status, response = RequestGenerator.POST_cobranca_recebimentos(cobranca["cobranca_chave"], payload)
        assert status == 422
        assert response["code"] == "QIT001025"

    def test_schema_refuses_invalid_body(self):
        cobranca = new_cobranca(today_in_sao_paulo() - timedelta(days=30))
        pago_em = (today_in_sao_paulo() - timedelta(days=30)).isoformat()
        payloads = [
            {"pago_em": pago_em},
            {"valor_centavos": 1000},
            {"valor_centavos": 1000.0, "pago_em": pago_em},
            {"valor_centavos": MAXIMUM_CENTAVOS + 1, "pago_em": pago_em},
            {"valor_centavos": "1000", "pago_em": pago_em},
            {"valor_centavos": 1000, "pago_em": "05/10/2026"},
            {"valor_centavos": 1000, "pago_em": pago_em + "\n"},
            {"valor_centavos": 1000, "pago_em": pago_em, "conta_chave": UNKNOWN_CHAVE},
        ]

        for payload in payloads:
            status, response = RequestGenerator.POST_cobranca_recebimentos(cobranca["cobranca_chave"], payload)
            assert status == 400, payload
            assert response["code"] == "QIT000001"

    def test_refuses_cobranca_that_does_not_exist(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)
        chave_real = cobranca["cobranca_chave"]

        for cobranca_chave in [UNKNOWN_CHAVE, "abc", chave_real + " ", chave_real.upper()]:
            status, response = receber(cobranca_chave, 1000, vencimento)
            assert status == 404, repr(cobranca_chave)
            assert response["code"] == "QIT001015"

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 0, "reservado": 0}

    def test_refuses_request_without_idempotency_key(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)
        payload = PayloadGenerator.create_recebimento_payload(1000, vencimento.isoformat())
        endpoint = f"/cobrancas/{cobranca['cobranca_chave']}/recebimentos"

        headers_list = [
            {"INTERNAL-TOKEN": INTERNAL_TOKEN},
            {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": ""},
            {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": "a" * 256},
        ]

        for headers in headers_list:
            response = ClientRequisition.send("POST", endpoint, payload=payload, headers=headers)
            assert response.response_status == 400, headers
            assert response.response_json["code"] == "QIT000001"

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 0, "reservado": 0}

    def test_refuses_request_without_token_and_records_nothing(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento)
        payload = PayloadGenerator.create_recebimento_payload(1000, vencimento.isoformat())

        response = ClientRequisition.send(
            "POST",
            f"/cobrancas/{cobranca['cobranca_chave']}/recebimentos",
            payload=payload,
            headers={"Idempotency-Key": "chave-sem-token"},
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        assert saldos(cobranca["conta_chave"]) == {"disponivel": 0, "reservado": 0}

    def test_never_records_more_than_what_is_owed_when_payments_arrive_at_the_same_time(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca = new_cobranca(vencimento, ALUGUEL_DE_2000)
        payload = PayloadGenerator.create_recebimento_payload(50000, vencimento.isoformat())

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_cobranca_recebimentos, (cobranca["cobranca_chave"], payload), SIMULTANEOUS_REQUESTS
        )

        statuses = []
        for status, response in results:
            statuses.append(status)

            if status == 422:
                assert response["code"] == "QIT001019"

        assert statuses.count(201) == 4
        assert statuses.count(422) == 1
        assert saldos(cobranca["conta_chave"]) == {"disponivel": 200000, "reservado": 0}
        assert posicao(cobranca["cobranca_chave"], vencimento)["status"] == "quitada"

        assert saldos_pelo_extrato(extrato_completo(cobranca["conta_chave"])) == saldos(cobranca["conta_chave"])
