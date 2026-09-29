from datetime import timedelta
from uuid import uuid4

from tests.utils import (
    ConcurrentRequests,
    ObjectGenerator,
    PayloadGenerator,
    RequestGenerator,
    extrato_completo,
    saldos_pelo_extrato,
    today_in_sao_paulo,
)


SIMULTANEOUS_REQUESTS = 5
VENCIMENTO = today_in_sao_paulo() - timedelta(days=30)


def new_conta_chave() -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]


def new_cobranca_chave(conta_chave: str, competencia: str = None) -> str:
    return ObjectGenerator.create_cobranca(conta_chave, vencimento=VENCIMENTO.isoformat(), competencia=competencia)[
        "cobranca_chave"
    ]


def recebimento_payload(valor_centavos: int) -> dict:
    return PayloadGenerator.create_recebimento_payload(valor_centavos, VENCIMENTO.isoformat())


def saldo_total(conta_chave: str) -> int:
    status, response = RequestGenerator.GET_conta_saldo(conta_chave)
    assert status == 200

    return response["saldo_disponivel_centavos"] + response["saldo_reservado_centavos"]


class TestRecebimentoIdempotencia:
    def test_returns_the_original_result_when_repeated(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        idempotency_key = str(uuid4())

        status, first_response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(50000), idempotency_key
        )
        assert status == 201

        status, second_response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(50000), idempotency_key
        )
        assert status == 200
        assert second_response == first_response

        assert saldo_total(conta_chave) == 50000

    def test_returns_the_original_result_even_after_the_cobranca_changed(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        idempotency_key = str(uuid4())

        status, first_response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(150000), idempotency_key
        )
        assert status == 201

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave,
            PayloadGenerator.create_recebimento_payload(51016, (VENCIMENTO + timedelta(days=1)).isoformat()),
        )
        assert status == 201

        status, repeated_response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(150000), idempotency_key
        )
        assert status == 200
        assert repeated_response == first_response

        assert saldo_total(conta_chave) == 201016

    def test_ignores_spaces_and_tabs_around_the_key(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        idempotency_key = str(uuid4())

        status, first_response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(50000), idempotency_key
        )
        assert status == 201

        for variante in [idempotency_key + " ", idempotency_key + "\t", idempotency_key + " \t "]:
            status, response = RequestGenerator.POST_cobranca_recebimentos(
                cobranca_chave, recebimento_payload(50000), variante
            )
            assert status == 200, repr(variante)
            assert response == first_response

        assert saldo_total(conta_chave) == 50000

    def test_counts_the_key_length_without_the_spaces_around(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(50000), "k" * 255 + "  "
        )
        assert status == 201

    def test_refuses_the_same_key_with_another_body(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        idempotency_key = str(uuid4())

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(50000), idempotency_key
        )
        assert status == 201

        status, response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(60000), idempotency_key
        )
        assert status == 409
        assert response["code"] == "QIT001022"

        assert saldo_total(conta_chave) == 50000

    def test_refuses_the_same_key_on_another_cobranca_of_the_same_conta(self):
        conta_chave = new_conta_chave()
        idempotency_key = str(uuid4())

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            new_cobranca_chave(conta_chave, "2026-09"), recebimento_payload(50000), idempotency_key
        )
        assert status == 201

        status, response = RequestGenerator.POST_cobranca_recebimentos(
            new_cobranca_chave(conta_chave, "2026-10"), recebimento_payload(50000), idempotency_key
        )
        assert status == 409
        assert response["code"] == "QIT001022"

    def test_accepts_the_same_key_on_another_conta(self):
        idempotency_key = str(uuid4())

        for _conta in range(2):
            cobranca_chave = new_cobranca_chave(new_conta_chave())

            status, _response = RequestGenerator.POST_cobranca_recebimentos(
                cobranca_chave, recebimento_payload(50000), idempotency_key
            )
            assert status == 201

    def test_runs_again_after_a_failed_attempt_with_the_same_key(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)
        idempotency_key = str(uuid4())

        status, response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(200001), idempotency_key
        )
        assert status == 422
        assert response["code"] == "QIT001019"

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, recebimento_payload(200000), idempotency_key
        )
        assert status == 201

        assert saldo_total(conta_chave) == 200000

    def test_processes_simultaneous_repetitions_only_once(self):
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave)

        results = ConcurrentRequests.send_at_the_same_time(
            RequestGenerator.POST_cobranca_recebimentos,
            (cobranca_chave, recebimento_payload(50000), str(uuid4())),
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

        assert saldo_total(conta_chave) == 50000

        pelo_extrato = saldos_pelo_extrato(extrato_completo(conta_chave))
        assert pelo_extrato["disponivel"] + pelo_extrato["reservado"] == 50000
