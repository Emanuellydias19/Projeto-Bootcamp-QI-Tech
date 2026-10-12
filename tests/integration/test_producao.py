import re
import time
from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import create_engine, text

from tests.utils import (
    INTERNAL_TOKEN,
    DbUtils,
    ObjectGenerator,
    PayloadGenerator,
    RequestGenerator,
    today_in_sao_paulo,
)
from tests.utils.requisition import ClientRequisition


UUID_IN_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
METRIC_LINE = re.compile(r'^(?P<name>[a-z_]+)\{(?P<labels>.*)\} (?P<value>[0-9.e+-]+)$')
MAXIMUM_BODY_BYTES = 65536
SEGUNDOS_ATE_DESISTIR_DA_TRAVA = 10
JSON_HEADERS = {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Content-Type": "application/json"}


def metricas() -> dict:
    response = ClientRequisition.send("GET", "/metrics", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
    assert response.response_status == 200
    assert response.response.headers["content-type"].startswith("text/plain")

    valores = {}
    for linha in response.response.text.splitlines():
        encontrada = METRIC_LINE.match(linha)
        if encontrada:
            valores[(encontrada["name"], encontrada["labels"])] = float(encontrada["value"])

    return valores


def requisicoes(valores: dict, method: str, route: str, status: str) -> float:
    labels = f'method="{method}",route="{route}",status="{status}"'

    return valores.get(("orca_http_requests_total", labels), 0.0)


@contextmanager
def conta_travada(conta_chave: str):
    engine = create_engine(DbUtils.database_url())

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT id FROM conta WHERE chave = :chave FOR UPDATE"), {"chave": conta_chave})
            yield
    finally:
        engine.dispose()


def corpo_com_tamanho(tamanho: int) -> bytes:
    inicio = b'{"documento": "529.982.247-25", "nome": "'
    fim = b'"}'
    corpo = inicio + b"M" * (tamanho - len(inicio) - len(fim)) + fim
    assert len(corpo) == tamanho

    return corpo


def itens(quantidade: int) -> list:
    lista = []
    for _item in range(quantidade):
        lista.append({"natureza": "despesa_extra", "valor_centavos": 100})

    return lista


class TestProducao:
    def test_reports_readiness_checking_the_database(self):
        response = ClientRequisition.send("GET", "/health_check/ready")
        assert response.response_status == 200
        assert response.response_json == {"status": "pronto", "banco": "ok"}

    def test_keeps_liveness_without_body(self):
        response = ClientRequisition.send("GET", "/health_check")
        assert response.response_status == 204

    def test_counts_each_request_by_route_template_and_status(self):
        antes = metricas()

        status, _response = RequestGenerator.POST_proprietarios(PayloadGenerator.create_proprietario_payload())
        assert status == 201
        status, _response = RequestGenerator.POST_proprietarios({"documento": "123"})
        assert status == 400
        status, _response = RequestGenerator.GET_conta_saldo(str(uuid4()))
        assert status == 404

        depois = metricas()

        assert requisicoes(depois, "POST", "/proprietarios", "201") - requisicoes(antes, "POST", "/proprietarios", "201") == 1
        assert requisicoes(depois, "POST", "/proprietarios", "400") - requisicoes(antes, "POST", "/proprietarios", "400") == 1
        assert (
            requisicoes(depois, "GET", "/contas/{conta_chave}/saldo", "404")
            - requisicoes(antes, "GET", "/contas/{conta_chave}/saldo", "404")
            == 1
        )

    def test_counts_the_unexpected_errors(self):
        antes = metricas()

        response = ClientRequisition.send(
            "GET", "/sample_entities", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}, query_params={"name": "\u0000"}
        )
        assert response.response_status == 500

        depois = metricas()

        assert requisicoes(depois, "GET", "/sample_entities", "500") - requisicoes(antes, "GET", "/sample_entities", "500") == 1

    def test_groups_the_unusual_methods_in_a_single_label(self):
        antes = metricas()

        response = ClientRequisition.send("PROPFIND", "/proprietarios", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        assert response.response_status == 405

        depois = metricas()

        assert requisicoes(depois, "OUTRO", "/proprietarios", "405") - requisicoes(antes, "OUTRO", "/proprietarios", "405") == 1
        for (_name, labels) in depois:
            assert 'method="PROPFIND"' not in labels

    def test_gives_up_waiting_for_the_conta_lock_with_503(self):
        conta_chave = ObjectGenerator.create_conta(ObjectGenerator.create_proprietario()["proprietario_chave"])["conta_chave"]
        cobranca_chave = ObjectGenerator.create_cobranca(conta_chave, itens=itens(1))["cobranca_chave"]
        ObjectGenerator.create_recebimento(cobranca_chave, 100, today_in_sao_paulo().isoformat())
        repasse = {"valor_centavos": 100}
        headers = {**JSON_HEADERS, "Idempotency-Key": str(uuid4())}

        with conta_travada(conta_chave):
            inicio = time.perf_counter()
            response = ClientRequisition.send("POST", f"/contas/{conta_chave}/repasses", payload=repasse, headers=headers)
            segundos = time.perf_counter() - inicio

        assert response.response_status == 503
        assert segundos < SEGUNDOS_ATE_DESISTIR_DA_TRAVA
        assert response.response_json["code"] == "QIT000503"
        assert response.response.headers["Retry-After"] == "1"
        assert response.response.headers["X-Request-ID"]

        status, saldo = RequestGenerator.GET_conta_saldo(conta_chave)
        assert status == 200
        assert saldo["saldo_disponivel_centavos"] == 100

        repetido = ClientRequisition.send("POST", f"/contas/{conta_chave}/repasses", payload=repasse, headers=headers)
        assert repetido.response_status == 201

    def test_measures_the_duration_of_each_route(self):
        RequestGenerator.POST_proprietarios(PayloadGenerator.create_proprietario_payload())

        valores = metricas()

        contagem = valores.get(("orca_http_request_duration_seconds_count", 'method="POST",route="/proprietarios"'), 0)
        soma = valores.get(("orca_http_request_duration_seconds_sum", 'method="POST",route="/proprietarios"'), 0)
        assert contagem >= 1
        assert soma > 0

    def test_never_puts_a_chave_in_the_metric_labels(self):
        conta_chave = ObjectGenerator.create_conta(ObjectGenerator.create_proprietario()["proprietario_chave"])["conta_chave"]
        RequestGenerator.GET_conta_saldo(conta_chave)
        assert ClientRequisition.send("GET", f"/contas/{conta_chave}/saldo").response_status == 403
        assert ClientRequisition.send(
            "GET", f"/contas/{conta_chave}/rota_que_nao_existe", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}
        ).response_status == 404

        for (_name, labels) in metricas():
            assert not UUID_IN_TEXT.search(labels), labels

    def test_refuses_metrics_without_token(self):
        response = ClientRequisition.send("GET", "/metrics")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

    def test_refuses_body_larger_than_the_limit(self):
        corpo = corpo_com_tamanho(MAXIMUM_BODY_BYTES + 1)

        response = ClientRequisition.send("POST", "/proprietarios", data=corpo, headers=JSON_HEADERS)
        assert response.response_status == 413
        assert response.response_json["code"] == "QIT000413"

    def test_accepts_body_up_to_the_limit(self):
        corpo = corpo_com_tamanho(MAXIMUM_BODY_BYTES)

        response = ClientRequisition.send("POST", "/proprietarios", data=corpo, headers=JSON_HEADERS)
        assert response.response_status == 400
        assert response.response_json["code"] == "QIT000001"

    def test_refuses_body_without_length(self):
        def pedacos():
            yield b'{"documento": "529.982.247-25", '
            yield b'"nome": "Maria"}'

        response = ClientRequisition.send("POST", "/proprietarios", data=pedacos(), headers=JSON_HEADERS)
        assert response.response_status == 411
        assert response.response_json["code"] == "QIT000411"

    def test_accepts_cobranca_with_up_to_100_itens(self):
        conta_chave = ObjectGenerator.create_conta(ObjectGenerator.create_proprietario()["proprietario_chave"])["conta_chave"]

        status, _response = RequestGenerator.POST_conta_cobrancas(
            conta_chave, PayloadGenerator.create_cobranca_payload(itens=itens(100))
        )
        assert status == 201

    def test_refuses_cobranca_with_more_than_100_itens(self):
        conta_chave = ObjectGenerator.create_conta(ObjectGenerator.create_proprietario()["proprietario_chave"])["conta_chave"]

        status, response = RequestGenerator.POST_conta_cobrancas(
            conta_chave, PayloadGenerator.create_cobranca_payload(itens=itens(101))
        )
        assert status == 400
        assert response["code"] == "QIT000001"
