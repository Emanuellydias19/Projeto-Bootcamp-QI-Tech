from tests.utils import INTERNAL_TOKEN, PayloadGenerator
from tests.utils.requisition import ClientRequisition


UNKNOWN_CHAVE = "00000000-0000-0000-0000-000000000000"
REQUEST_ID_HEADER = "X-Request-ID"
JSON_HEADERS = {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Content-Type": "application/json"}


def enviar_bytes(endpoint: str, corpo: bytes, headers: dict = None):
    if headers is None:
        headers = JSON_HEADERS

    return ClientRequisition.send("POST", endpoint, data=corpo, headers=headers)


class TestRequisicoesMalformadas:
    def test_refuses_body_that_is_not_utf8(self):
        for corpo in [b'{"documento": "\xff\xfe", "nome": "Maria"}', b'{"documento": "123", "nome": "\xed\xa0\x80"}']:
            response = enviar_bytes("/proprietarios", corpo)
            assert response.response_status == 400, corpo
            assert response.response_json["code"] == "QIT000001"
            assert response.response.headers.get(REQUEST_ID_HEADER)

    def test_refuses_integer_with_too_many_digits(self):
        headers = {**JSON_HEADERS, "Idempotency-Key": "chave-digitos"}
        corpo = b'{"valor_centavos": 1' + b"0" * 5000 + b"}"

        response = enviar_bytes(f"/contas/{UNKNOWN_CHAVE}/repasses", corpo, headers)
        assert response.response_status == 400
        assert response.response_json["code"] == "QIT000001"

    def test_refuses_json_nested_too_deep(self):
        corpo = b"[" * 5000 + b"]" * 5000

        response = enviar_bytes("/proprietarios", corpo)
        assert response.response_status == 400
        assert response.response_json["code"] == "QIT000001"

    def test_refuses_options_without_token(self):
        for endpoint in ["/proprietarios", f"/contas/{UNKNOWN_CHAVE}/repasses", "/rota_que_nao_existe"]:
            response = ClientRequisition.send("OPTIONS", endpoint)
            assert response.response_status == 403, endpoint
            assert response.response_json["code"] == "QIT000002"

    def test_returns_the_request_id_on_every_error(self):
        proprietario = PayloadGenerator.create_proprietario_payload()

        chamadas = [
            ("POST", "/proprietarios", {"documento": "123"}, JSON_HEADERS, 400),
            ("POST", "/proprietarios", proprietario, {}, 403),
            ("GET", "/rota_que_nao_existe", None, JSON_HEADERS, 404),
            ("DELETE", "/proprietarios", None, JSON_HEADERS, 405),
            ("POST", "/proprietarios", {"documento": "111.222.333-44", "nome": "Maria"}, JSON_HEADERS, 422),
            ("GET", f"/contas/{UNKNOWN_CHAVE}/saldo", None, JSON_HEADERS, 404),
        ]

        for method, endpoint, payload, headers, esperado in chamadas:
            response = ClientRequisition.send(method, endpoint, payload=payload, headers={**headers, REQUEST_ID_HEADER: "protocolo-123"})
            assert response.response_status == esperado, (method, endpoint)
            assert response.response.headers.get(REQUEST_ID_HEADER) == "protocolo-123", (method, endpoint)
