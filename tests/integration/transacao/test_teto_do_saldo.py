from datetime import timedelta

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator, today_in_sao_paulo


MAXIMUM_CENTAVOS = 9007199254740991
VENCIMENTO = today_in_sao_paulo() - timedelta(days=30)


def new_conta_chave(taxa_administracao_bps: int = None) -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave, taxa_administracao_bps=taxa_administracao_bps)[
        "conta_chave"
    ]


def new_cobranca_chave(conta_chave: str, natureza: str, valor_centavos: int, competencia: str) -> str:
    itens = [{"natureza": natureza, "valor_centavos": valor_centavos}]

    return ObjectGenerator.create_cobranca(
        conta_chave, vencimento=VENCIMENTO.isoformat(), itens=itens, competencia=competencia
    )["cobranca_chave"]


def receber(cobranca_chave: str, valor_centavos: int) -> tuple:
    payload = PayloadGenerator.create_recebimento_payload(valor_centavos, VENCIMENTO.isoformat())

    return RequestGenerator.POST_cobranca_recebimentos(cobranca_chave, payload)


def saldos(conta_chave: str) -> dict:
    status, response = RequestGenerator.GET_conta_saldo(conta_chave)
    assert status == 200

    return {
        "disponivel": response["saldo_disponivel_centavos"],
        "reservado": response["saldo_reservado_centavos"],
    }


class TestTetoDoSaldo:
    def test_accepts_a_saldo_exactly_at_the_maximum(self):
        conta_chave = new_conta_chave()

        status, _response = receber(new_cobranca_chave(conta_chave, "aluguel", MAXIMUM_CENTAVOS - 1, "2026-10"), MAXIMUM_CENTAVOS - 1)
        assert status == 201
        status, _response = receber(new_cobranca_chave(conta_chave, "aluguel", 1, "2026-11"), 1)
        assert status == 201

        assert saldos(conta_chave) == {"disponivel": MAXIMUM_CENTAVOS, "reservado": 0}

    def test_refuses_recebimento_that_would_take_the_disponivel_above_the_maximum(self):
        conta_chave = new_conta_chave()

        status, _response = receber(new_cobranca_chave(conta_chave, "aluguel", MAXIMUM_CENTAVOS, "2026-10"), MAXIMUM_CENTAVOS)
        assert status == 201

        cobranca_chave = new_cobranca_chave(conta_chave, "despesa_extra", 1, "2026-11")
        status, response = receber(cobranca_chave, 1)
        assert status == 422
        assert response["code"] == "QIT001029"

        assert saldos(conta_chave) == {"disponivel": MAXIMUM_CENTAVOS, "reservado": 0}

        status, posicao = RequestGenerator.GET_cobranca(cobranca_chave, {"data": VENCIMENTO.isoformat()})
        assert status == 200
        assert posicao["status"] == "aberta"

    def test_refuses_recebimento_that_would_take_the_reservado_above_the_maximum(self):
        conta_chave = new_conta_chave()

        status, _response = receber(new_cobranca_chave(conta_chave, "condominio", MAXIMUM_CENTAVOS, "2026-10"), MAXIMUM_CENTAVOS)
        assert status == 201

        status, response = receber(new_cobranca_chave(conta_chave, "iptu", 1, "2026-11"), 1)
        assert status == 422
        assert response["code"] == "QIT001029"

        assert saldos(conta_chave) == {"disponivel": 0, "reservado": MAXIMUM_CENTAVOS}

    def test_refuses_estorno_that_would_take_the_disponivel_above_the_maximum(self):
        conta_chave = new_conta_chave(taxa_administracao_bps=0)

        status, _response = receber(new_cobranca_chave(conta_chave, "aluguel", MAXIMUM_CENTAVOS, "2026-10"), MAXIMUM_CENTAVOS)
        assert status == 201

        repasse = ObjectGenerator.create_repasse(conta_chave, 100)

        status, _response = receber(new_cobranca_chave(conta_chave, "aluguel", 100, "2026-11"), 100)
        assert status == 201
        assert saldos(conta_chave) == {"disponivel": MAXIMUM_CENTAVOS, "reservado": 0}

        status, response = RequestGenerator.POST_transacao_estornos(repasse["transacao_chave"])
        assert status == 422
        assert response["code"] == "QIT001029"

        assert saldos(conta_chave) == {"disponivel": MAXIMUM_CENTAVOS, "reservado": 0}
