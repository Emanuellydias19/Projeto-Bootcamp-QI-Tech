import re

from tests.utils import UUID_PATTERN, ConcurrentRequests, ObjectGenerator, PayloadGenerator, RequestGenerator
from tests.utils.requisition import ClientRequisition


UNKNOWN_CHAVE = "00000000-0000-0000-0000-000000000000"
MAXIMUM_CENTAVOS = 9007199254740991
SIMULTANEOUS_REQUESTS = 5


def new_conta_chave() -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]


class TestCobrancaCreate:
    def test_creates_cobranca(self):
        conta_chave = new_conta_chave()

        status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, PayloadGenerator.create_cobranca_payload())
        assert status == 201
        assert list(response.keys()) == ["cobranca_chave"]
        assert re.fullmatch(UUID_PATTERN, response["cobranca_chave"])

        cobranca_chave = response["cobranca_chave"]

        status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": "2026-10-05"})
        assert status == 200
        assert response == {
            "cobranca_chave": cobranca_chave,
            "conta_chave": conta_chave,
            "competencia": "2026-10",
            "vencimento": "2026-10-05",
            "status": "aberta",
            "itens": [
                {
                    "natureza": "aluguel",
                    "valor_devido_centavos": 150000,
                    "valor_pago_centavos": 0,
                    "valor_em_aberto_centavos": 150000,
                },
                {
                    "natureza": "condominio",
                    "valor_devido_centavos": 35000,
                    "valor_pago_centavos": 0,
                    "valor_em_aberto_centavos": 35000,
                },
                {
                    "natureza": "iptu",
                    "valor_devido_centavos": 15000,
                    "valor_pago_centavos": 0,
                    "valor_em_aberto_centavos": 15000,
                },
            ],
            "total_em_aberto_centavos": 200000,
            "data": "2026-10-05",
            "multa_centavos": 0,
            "juros_centavos": 0,
            "total_devido_na_data_centavos": 200000,
        }

    def test_creates_the_same_competencia_in_another_conta(self):
        for _conta in range(2):
            status, _response = RequestGenerator.POST_conta_cobrancas(
                new_conta_chave(), PayloadGenerator.create_cobranca_payload()
            )
            assert status == 201

    def test_refuses_duplicated_competencia(self):
        conta_chave = new_conta_chave()
        payload = PayloadGenerator.create_cobranca_payload()

        status, _response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
        assert status == 201

        status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
        assert status == 409
        assert response["code"] == "QIT001016"

    def test_refuses_duplicated_competencia_sent_at_the_same_time(self):
        conta_chave = new_conta_chave()
        payload = PayloadGenerator.create_cobranca_payload()

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_conta_cobrancas, (conta_chave, payload), SIMULTANEOUS_REQUESTS
        )

        statuses = []
        for status, response in results:
            statuses.append(status)

            if status == 409:
                assert response["code"] == "QIT001016"

        assert statuses.count(201) == 1
        assert statuses.count(409) == SIMULTANEOUS_REQUESTS - 1

    def test_accepts_valor_at_the_maximum(self):
        payload = PayloadGenerator.create_cobranca_payload(
            itens=[{"natureza": "aluguel", "valor_centavos": MAXIMUM_CENTAVOS}]
        )

        status, _response = RequestGenerator.POST_conta_cobrancas(new_conta_chave(), payload)
        assert status == 201

    def test_refuses_conta_that_does_not_exist(self):
        conta_chave_real = new_conta_chave()

        for conta_chave in [UNKNOWN_CHAVE, "abc", conta_chave_real + " ", conta_chave_real.upper()]:
            status, response = RequestGenerator.POST_conta_cobrancas(
                conta_chave, PayloadGenerator.create_cobranca_payload()
            )
            assert status == 404, repr(conta_chave)
            assert response["code"] == "QIT001011"

    def test_refuses_item_with_valor_not_positive(self):
        conta_chave = new_conta_chave()

        for valor in [0, -1]:
            payload = PayloadGenerator.create_cobranca_payload(itens=[{"natureza": "aluguel", "valor_centavos": valor}])

            status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
            assert status == 422, valor
            assert response["code"] == "QIT001018"

    def test_refuses_date_that_does_not_exist_in_the_calendar(self):
        conta_chave = new_conta_chave()
        payloads = [
            PayloadGenerator.create_cobranca_payload(vencimento="2026-02-30"),
            PayloadGenerator.create_cobranca_payload(competencia="2026-13"),
            PayloadGenerator.create_cobranca_payload(competencia="2026-00"),
        ]

        for payload in payloads:
            status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
            assert status == 422, payload
            assert response["code"] == "QIT001025"

    def test_checks_conta_before_values(self):
        payload = PayloadGenerator.create_cobranca_payload(
            vencimento="2026-02-30", itens=[{"natureza": "aluguel", "valor_centavos": 0}]
        )

        status, response = RequestGenerator.POST_conta_cobrancas(UNKNOWN_CHAVE, payload)
        assert status == 404
        assert response["code"] == "QIT001011"

    def test_schema_refuses_missing_field(self):
        conta_chave = new_conta_chave()

        for field in ["competencia", "vencimento", "itens"]:
            payload = PayloadGenerator.create_cobranca_payload()
            del payload[field]

            status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
            assert status == 400, field
            assert response["code"] == "QIT000001"

    def test_schema_refuses_item_with_missing_field(self):
        conta_chave = new_conta_chave()

        for field in ["natureza", "valor_centavos"]:
            payload = PayloadGenerator.create_cobranca_payload()
            del payload["itens"][0][field]

            status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
            assert status == 400, field
            assert response["code"] == "QIT000001"

    def test_schema_refuses_empty_itens(self):
        payload = PayloadGenerator.create_cobranca_payload(itens=[])

        status, response = RequestGenerator.POST_conta_cobrancas(new_conta_chave(), payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_schema_refuses_natureza_outside_the_list(self):
        conta_chave = new_conta_chave()

        for natureza in ["multa", "juros", "encargos", "taxa", "repasse"]:
            payload = PayloadGenerator.create_cobranca_payload(itens=[{"natureza": natureza, "valor_centavos": 1000}])

            status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
            assert status == 400, natureza
            assert response["code"] == "QIT000001"

    def test_schema_refuses_valor_with_decimal_places_or_above_the_maximum(self):
        conta_chave = new_conta_chave()

        for valor in [150000.0, MAXIMUM_CENTAVOS + 1]:
            payload = PayloadGenerator.create_cobranca_payload(itens=[{"natureza": "aluguel", "valor_centavos": valor}])

            status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
            assert status == 400, valor
            assert response["code"] == "QIT000001"

    def test_schema_refuses_date_out_of_format(self):
        conta_chave = new_conta_chave()
        payloads = [
            PayloadGenerator.create_cobranca_payload(vencimento="05/10/2026"),
            PayloadGenerator.create_cobranca_payload(vencimento="2026-10-5"),
            PayloadGenerator.create_cobranca_payload(vencimento="2026-10-05\n"),
            PayloadGenerator.create_cobranca_payload(vencimento="2026-10-0٥"),
            PayloadGenerator.create_cobranca_payload(competencia="10/2026"),
            PayloadGenerator.create_cobranca_payload(competencia="2026-1"),
            PayloadGenerator.create_cobranca_payload(competencia="2026-10\n"),
            PayloadGenerator.create_cobranca_payload(competencia="2026-1٠"),
        ]

        for payload in payloads:
            status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
            assert status == 400, payload
            assert response["code"] == "QIT000001"

    def test_schema_refuses_unknown_field(self):
        conta_chave = new_conta_chave()

        payload = PayloadGenerator.create_cobranca_payload()
        payload["status"] = "quitada"

        status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
        assert status == 400
        assert response["code"] == "QIT000001"

        payload = PayloadGenerator.create_cobranca_payload(
            itens=[{"natureza": "aluguel", "valor_centavos": 150000, "item_cobranca_id": 1}]
        )

        status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_request_without_token_and_records_nothing(self):
        conta_chave = new_conta_chave()
        payload = PayloadGenerator.create_cobranca_payload()

        response = ClientRequisition.send("POST", f"/contas/{conta_chave}/cobrancas", payload=payload)
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        status, _response = RequestGenerator.POST_conta_cobrancas(conta_chave, payload)
        assert status == 201
