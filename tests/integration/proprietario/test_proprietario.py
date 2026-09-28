import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from tests.utils import PayloadGenerator, RequestGenerator
from tests.utils.random_generator import RandomGenerator
from tests.utils.requisition import ClientRequisition


UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
SIMULTANEOUS_REQUESTS = 5


def post_proprietario_after_barrier(barrier: Barrier, payload: dict) -> tuple:
    barrier.wait()
    return RequestGenerator.POST_proprietarios(payload)


class TestProprietario:
    def test_creates_proprietario_with_cpf(self):
        payload = PayloadGenerator.create_proprietario_payload()

        status, response = RequestGenerator.POST_proprietarios(payload)
        assert status == 201
        assert list(response.keys()) == ["proprietario_chave"]
        assert re.fullmatch(UUID_PATTERN, response["proprietario_chave"])

    def test_creates_proprietario_with_cnpj(self):
        payload = PayloadGenerator.create_proprietario_payload(documento=RandomGenerator.generate_cnpj())

        status, response = RequestGenerator.POST_proprietarios(payload)
        assert status == 201
        assert re.fullmatch(UUID_PATTERN, response["proprietario_chave"])

    def test_refuses_documento_with_wrong_check_digit(self):
        for documento in ["111.222.333-44", "11.222.333/0001-80"]:
            payload = PayloadGenerator.create_proprietario_payload(documento=documento)

            status, response = RequestGenerator.POST_proprietarios(payload)
            assert status == 422
            assert response["code"] == "QIT001008"
            assert documento not in response["description"]

    def test_refuses_documento_with_all_digits_equal(self):
        for documento in ["111.111.111-11", "00.000.000/0000-00"]:
            payload = PayloadGenerator.create_proprietario_payload(documento=documento)

            status, response = RequestGenerator.POST_proprietarios(payload)
            assert status == 422
            assert response["code"] == "QIT001008"

    def test_refuses_duplicated_documento(self):
        documento = RandomGenerator.generate_cpf()

        status, _response = RequestGenerator.POST_proprietarios(
            PayloadGenerator.create_proprietario_payload(documento=documento)
        )
        assert status == 201

        status, response = RequestGenerator.POST_proprietarios(
            PayloadGenerator.create_proprietario_payload(documento=documento, nome="João Pereira")
        )
        assert status == 409
        assert response["code"] == "QIT001009"
        assert documento not in response["description"]

    def test_refuses_duplicated_documento_sent_at_the_same_time(self):
        payload = PayloadGenerator.create_proprietario_payload(documento=RandomGenerator.generate_cnpj())
        barrier = Barrier(SIMULTANEOUS_REQUESTS)

        with ThreadPoolExecutor(max_workers=SIMULTANEOUS_REQUESTS) as executor:
            futures = []
            for _request in range(SIMULTANEOUS_REQUESTS):
                futures.append(executor.submit(post_proprietario_after_barrier, barrier, payload))

        statuses = []
        for future in futures:
            status, response = future.result()
            statuses.append(status)

            if status == 409:
                assert response["code"] == "QIT001009"

        assert statuses.count(201) == 1
        assert statuses.count(409) == SIMULTANEOUS_REQUESTS - 1

    def test_schema_refuses_missing_documento(self):
        payload = PayloadGenerator.create_proprietario_payload()
        del payload["documento"]

        status, response = RequestGenerator.POST_proprietarios(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_schema_refuses_missing_nome(self):
        payload = PayloadGenerator.create_proprietario_payload()
        del payload["nome"]

        status, response = RequestGenerator.POST_proprietarios(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_schema_refuses_empty_nome(self):
        payload = PayloadGenerator.create_proprietario_payload(nome="")

        status, response = RequestGenerator.POST_proprietarios(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_schema_refuses_nome_with_wrong_type(self):
        for nome in [None, 123]:
            payload = PayloadGenerator.create_proprietario_payload()
            payload["nome"] = nome

            status, response = RequestGenerator.POST_proprietarios(payload)
            assert status == 400
            assert response["code"] == "QIT000001"

    def test_schema_refuses_documento_without_mask(self):
        for documento in ["52998224725", "11222333000181"]:
            payload = PayloadGenerator.create_proprietario_payload(documento=documento)

            status, response = RequestGenerator.POST_proprietarios(payload)
            assert status == 400
            assert response["code"] == "QIT000001"

    def test_schema_refuses_documento_with_digits_outside_0_to_9(self):
        for documento in ["٥٢٩.٩٨٢.٢٤٧-٢٥", "١١.٢٢٢.٣٣٣/٠٠٠١-٨١"]:
            payload = PayloadGenerator.create_proprietario_payload(documento=documento)

            status, response = RequestGenerator.POST_proprietarios(payload)
            assert status == 400
            assert response["code"] == "QIT000001"

    def test_schema_refuses_documento_with_line_break_at_the_end(self):
        for documento in [RandomGenerator.generate_cpf(), RandomGenerator.generate_cnpj()]:
            payload = PayloadGenerator.create_proprietario_payload(documento=documento + "\n")

            status, response = RequestGenerator.POST_proprietarios(payload)
            assert status == 400
            assert response["code"] == "QIT000001"

    def test_schema_refuses_unknown_field(self):
        payload = PayloadGenerator.create_proprietario_payload()
        payload["id"] = 1

        status, response = RequestGenerator.POST_proprietarios(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_request_without_token_and_records_nothing(self):
        payload = PayloadGenerator.create_proprietario_payload()

        response = ClientRequisition.send("POST", "/proprietarios", payload=payload)
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        status, _response = RequestGenerator.POST_proprietarios(payload)
        assert status == 201
