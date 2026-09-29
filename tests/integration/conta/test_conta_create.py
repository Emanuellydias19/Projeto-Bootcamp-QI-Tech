import re

from tests.utils import UUID_PATTERN, ConcurrentRequests, ObjectGenerator, PayloadGenerator, RequestGenerator
from tests.utils.requisition import ClientRequisition


UNKNOWN_CHAVE = "00000000-0000-0000-0000-000000000000"
BPS_FIELDS = ["taxa_administracao_bps", "multa_bps", "juros_mensal_bps"]
TEXT_FIELDS = ["proprietario_chave", "imovel_referencia", "politica_imputacao_chave"]
SIMULTANEOUS_REQUESTS = 5
TEXTOS_FORA_DO_FORMATO = [
    "M" * 256,
    "   ",
    "\t",
    "\u00a0",
    "Ma\u0000ria",
    "Ma\ud800ria",
    "Ma\nria",
    "Ma\u007fria",
    "Maria\n",
]


def new_proprietario_chave() -> str:
    return ObjectGenerator.create_proprietario()["proprietario_chave"]


class TestContaCreate:
    def test_creates_conta(self):
        payload = PayloadGenerator.create_conta_payload(new_proprietario_chave())

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 201
        assert list(response.keys()) == ["conta_chave"]
        assert re.fullmatch(UUID_PATTERN, response["conta_chave"])

    def test_creates_another_conta_for_the_same_proprietario_with_another_imovel(self):
        proprietario_chave = new_proprietario_chave()

        for imovel_referencia in ["Rua A, 10", "Rua B, 20"]:
            payload = PayloadGenerator.create_conta_payload(proprietario_chave, imovel_referencia=imovel_referencia)

            status, _response = RequestGenerator.POST_contas(payload)
            assert status == 201

    def test_creates_conta_for_the_same_imovel_of_another_proprietario(self):
        for _proprietario in range(2):
            payload = PayloadGenerator.create_conta_payload(
                new_proprietario_chave(), imovel_referencia="Avenida Brasil, 500"
            )

            status, _response = RequestGenerator.POST_contas(payload)
            assert status == 201

    def test_creates_conta_with_bps_at_the_limits(self):
        for limit in [0, 10000]:
            payload = PayloadGenerator.create_conta_payload(
                new_proprietario_chave(),
                taxa_administracao_bps=limit,
                multa_bps=limit,
                juros_mensal_bps=limit,
            )

            status, _response = RequestGenerator.POST_contas(payload)
            assert status == 201

    def test_refuses_proprietario_that_does_not_exist(self):
        payload = PayloadGenerator.create_conta_payload(UNKNOWN_CHAVE)

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 404
        assert response["code"] == "QIT001010"

    def test_refuses_politica_that_does_not_exist(self):
        payload = PayloadGenerator.create_conta_payload(new_proprietario_chave(), politica_imputacao_chave=UNKNOWN_CHAVE)

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 404
        assert response["code"] == "QIT001014"

    def test_refuses_bps_out_of_range(self):
        proprietario_chave = new_proprietario_chave()

        for field in BPS_FIELDS:
            for value in [-1, 10001]:
                payload = PayloadGenerator.create_conta_payload(proprietario_chave)
                payload[field] = value

                status, response = RequestGenerator.POST_contas(payload)
                assert status == 422, f"{field}={value}"
                assert response["code"] == "QIT001013"

    def test_checks_proprietario_then_politica_then_bps(self):
        payload = PayloadGenerator.create_conta_payload(
            UNKNOWN_CHAVE, politica_imputacao_chave=UNKNOWN_CHAVE, taxa_administracao_bps=10001
        )

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 404
        assert response["code"] == "QIT001010"

        payload = PayloadGenerator.create_conta_payload(
            new_proprietario_chave(), politica_imputacao_chave=UNKNOWN_CHAVE, taxa_administracao_bps=10001
        )

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 404
        assert response["code"] == "QIT001014"

    def test_checks_bps_before_duplicated_conta(self):
        payload = PayloadGenerator.create_conta_payload(new_proprietario_chave())

        status, _response = RequestGenerator.POST_contas(payload)
        assert status == 201

        payload["taxa_administracao_bps"] = 10001

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 422
        assert response["code"] == "QIT001013"

    def test_refuses_duplicated_conta(self):
        payload = PayloadGenerator.create_conta_payload(new_proprietario_chave())

        status, _response = RequestGenerator.POST_contas(payload)
        assert status == 201

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 409
        assert response["code"] == "QIT001012"

    def test_refuses_duplicated_conta_sent_at_the_same_time(self):
        payload = PayloadGenerator.create_conta_payload(new_proprietario_chave())

        results = ConcurrentRequests.send_at_the_same_time(RequestGenerator.POST_contas, (payload,), SIMULTANEOUS_REQUESTS)

        statuses = []
        for status, response in results:
            statuses.append(status)

            if status == 409:
                assert response["code"] == "QIT001012"

        assert statuses.count(201) == 1
        assert statuses.count(409) == SIMULTANEOUS_REQUESTS - 1

    def test_schema_refuses_bps_with_decimal_places(self):
        proprietario_chave = new_proprietario_chave()

        for field in BPS_FIELDS:
            payload = PayloadGenerator.create_conta_payload(proprietario_chave)
            payload[field] = 1000.0

            status, response = RequestGenerator.POST_contas(payload)
            assert status == 400, field
            assert response["code"] == "QIT000001"

    def test_schema_refuses_field_with_wrong_type(self):
        proprietario_chave = new_proprietario_chave()

        for field in TEXT_FIELDS:
            for value in [None, 123]:
                payload = PayloadGenerator.create_conta_payload(proprietario_chave)
                payload[field] = value

                status, response = RequestGenerator.POST_contas(payload)
                assert status == 400, f"{field}={value!r}"
                assert response["code"] == "QIT000001"

    def test_schema_refuses_missing_field(self):
        proprietario_chave = new_proprietario_chave()

        for field in PayloadGenerator.create_conta_payload(proprietario_chave).keys():
            payload = PayloadGenerator.create_conta_payload(proprietario_chave)
            del payload[field]

            status, response = RequestGenerator.POST_contas(payload)
            assert status == 400, field
            assert response["code"] == "QIT000001"

    def test_schema_refuses_malformed_chave(self):
        proprietario_chave = new_proprietario_chave()

        for field in ["proprietario_chave", "politica_imputacao_chave"]:
            for chave in ["abc", proprietario_chave + "\n", proprietario_chave.upper()]:
                payload = PayloadGenerator.create_conta_payload(proprietario_chave)
                payload[field] = chave

                status, response = RequestGenerator.POST_contas(payload)
                assert status == 400, f"{field}={chave!r}"
                assert response["code"] == "QIT000001"

    def test_refuses_the_same_imovel_with_spaces_around(self):
        proprietario_chave = new_proprietario_chave()

        status, _response = RequestGenerator.POST_contas(
            PayloadGenerator.create_conta_payload(proprietario_chave, imovel_referencia="Rua das Flores, 120")
        )
        assert status == 201

        for imovel_referencia in ["Rua das Flores, 120 ", "  Rua das Flores, 120", "\u00a0Rua das Flores, 120\u2003"]:
            payload = PayloadGenerator.create_conta_payload(proprietario_chave, imovel_referencia=imovel_referencia)

            status, response = RequestGenerator.POST_contas(payload)
            assert status == 409, repr(imovel_referencia)
            assert response["code"] == "QIT001012"

    def test_accepts_imovel_referencia_with_up_to_255_characters(self):
        proprietario_chave = new_proprietario_chave()

        for imovel_referencia in ["R" * 255, "é" * 255, "Rua 😀 " + "x" * 248]:
            payload = PayloadGenerator.create_conta_payload(proprietario_chave, imovel_referencia=imovel_referencia)

            status, _response = RequestGenerator.POST_contas(payload)
            assert status == 201, repr(imovel_referencia)

    def test_schema_refuses_imovel_referencia_out_of_format(self):
        proprietario_chave = new_proprietario_chave()

        for imovel_referencia in TEXTOS_FORA_DO_FORMATO + ["R" * 3000]:
            payload = PayloadGenerator.create_conta_payload(proprietario_chave, imovel_referencia=imovel_referencia)

            status, response = RequestGenerator.POST_contas(payload)
            assert status == 400, repr(imovel_referencia)[:40]
            assert response["code"] == "QIT000001"

    def test_schema_refuses_empty_imovel_referencia(self):
        payload = PayloadGenerator.create_conta_payload(new_proprietario_chave(), imovel_referencia="")

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_schema_refuses_unknown_field(self):
        payload = PayloadGenerator.create_conta_payload(new_proprietario_chave())
        payload["saldo_disponivel"] = 1000000

        status, response = RequestGenerator.POST_contas(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_request_without_token_and_records_nothing(self):
        payload = PayloadGenerator.create_conta_payload(new_proprietario_chave())

        response = ClientRequisition.send("POST", "/contas", payload=payload)
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        status, _response = RequestGenerator.POST_contas(payload)
        assert status == 201
