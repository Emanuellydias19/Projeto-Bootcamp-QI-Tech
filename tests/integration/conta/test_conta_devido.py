import re
from datetime import date, timedelta

from tests.utils import INTERNAL_TOKEN, UUID_PATTERN, ObjectGenerator, PayloadGenerator, RequestGenerator, today_in_sao_paulo
from tests.utils.requisition import ClientRequisition


UNKNOWN_CHAVE = "00000000-0000-4000-8000-000000000000"
MOMENT_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
ALUGUEL_DE_2000 = [{"natureza": "aluguel", "valor_centavos": 200000}]


def new_conta_chave() -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave, multa_bps=200, juros_mensal_bps=100)["conta_chave"]


def new_cobranca_chave(conta_chave: str, competencia: str, vencimento: date, itens: list = None) -> str:
    return ObjectGenerator.create_cobranca(
        conta_chave, vencimento=vencimento.isoformat(), itens=itens, competencia=competencia
    )["cobranca_chave"]


def devido(conta_chave: str, data: date = None) -> dict:
    params = None
    if data is not None:
        params = {"data": data.isoformat()}

    status, response = RequestGenerator.GET_conta_devido(conta_chave, params)
    assert status == 200

    return response


def sem_os_recebimentos(cobranca: dict) -> dict:
    resumo = dict(cobranca)
    del resumo["recebimentos"]

    return resumo


class TestContaDevido:
    def test_returns_zero_for_a_conta_without_cobrancas(self):
        conta_chave = new_conta_chave()

        assert devido(conta_chave) == {
            "conta_chave": conta_chave,
            "data": today_in_sao_paulo().isoformat(),
            "multa_bps": 200,
            "juros_mensal_bps": 100,
            "total_em_aberto_centavos": 0,
            "multa_centavos": 0,
            "juros_centavos": 0,
            "total_pago_centavos": 0,
            "total_devido_na_data_centavos": 0,
            "cobrancas": [],
        }

    def test_sums_the_cobrancas_that_are_not_quitadas_on_the_date(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        primeira = new_cobranca_chave(conta_chave, "2026-08", today - timedelta(days=40))
        segunda = new_cobranca_chave(conta_chave, "2026-09", today - timedelta(days=10), ALUGUEL_DE_2000)
        recebimento = ObjectGenerator.create_recebimento(primeira, 180000, (today - timedelta(days=40)).isoformat())

        response = devido(conta_chave, today)

        assert len(response["cobrancas"]) == 2
        assert len(response["cobrancas"][0]["recebimentos"]) == 1
        linha = response["cobrancas"][0]["recebimentos"][0]
        assert re.fullmatch(UUID_PATTERN, linha["recebimento_chave"])
        assert re.fullmatch(MOMENT_PATTERN, linha["criado_em"])
        assert linha == {
            "recebimento_chave": linha["recebimento_chave"],
            "transacao_chave": recebimento["transacao_chave"],
            "pago_em": (today - timedelta(days=40)).isoformat(),
            "criado_em": linha["criado_em"],
            "valor_centavos": 180000,
            "estornado": False,
        }
        assert response == {
            "conta_chave": conta_chave,
            "data": today.isoformat(),
            "multa_bps": 200,
            "juros_mensal_bps": 100,
            "total_em_aberto_centavos": 220000,
            "multa_centavos": 4400,
            "juros_centavos": 932,
            "total_pago_centavos": 180000,
            "total_devido_na_data_centavos": 225332,
            "cobrancas": [
                {
                    "cobranca_chave": primeira,
                    "competencia": "2026-08",
                    "vencimento": (today - timedelta(days=40)).isoformat(),
                    "status": "parcial",
                    "total_em_aberto_centavos": 20000,
                    "multa_centavos": 400,
                    "juros_centavos": 266,
                    "total_pago_centavos": 180000,
                    "total_devido_na_data_centavos": 20666,
                    "recebimentos": [linha],
                },
                {
                    "cobranca_chave": segunda,
                    "competencia": "2026-09",
                    "vencimento": (today - timedelta(days=10)).isoformat(),
                    "status": "aberta",
                    "total_em_aberto_centavos": 200000,
                    "multa_centavos": 4000,
                    "juros_centavos": 666,
                    "total_pago_centavos": 0,
                    "total_devido_na_data_centavos": 204666,
                    "recebimentos": [],
                },
            ],
        }

    def test_matches_the_position_of_each_cobranca(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        primeira = new_cobranca_chave(conta_chave, "2026-08", today - timedelta(days=40))
        new_cobranca_chave(conta_chave, "2026-09", today - timedelta(days=10), ALUGUEL_DE_2000)
        ObjectGenerator.create_recebimento(primeira, 50000, (today - timedelta(days=20)).isoformat())

        for data in [today, today + timedelta(days=17)]:
            response = devido(conta_chave, data)
            assert len(response["cobrancas"]) == 2

            for linha in response["cobrancas"]:
                status, cobranca = RequestGenerator.GET_cobranca(linha["cobranca_chave"], {"data": data.isoformat()})
                assert status == 200
                assert linha["status"] == cobranca["status"]
                assert linha["total_em_aberto_centavos"] == cobranca["total_em_aberto_centavos"]
                assert linha["multa_centavos"] == cobranca["multa_centavos"]
                assert linha["juros_centavos"] == cobranca["juros_centavos"]
                assert linha["total_devido_na_data_centavos"] == cobranca["total_devido_na_data_centavos"]

    def test_total_devido_of_a_cobranca_is_the_limit_of_the_recebimento(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave, "2026-09", today - timedelta(days=10), ALUGUEL_DE_2000)

        total = devido(conta_chave, today)["cobrancas"][0]["total_devido_na_data_centavos"]
        assert total == 204666

        status, response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, PayloadGenerator.create_recebimento_payload(total + 1, today.isoformat())
        )
        assert status == 422
        assert response["code"] == "QIT001019"

        ObjectGenerator.create_recebimento(cobranca_chave, total, today.isoformat())

        response = devido(conta_chave, today)
        assert response["cobrancas"] == []
        assert response["total_devido_na_data_centavos"] == 0

    def test_leaves_a_quitada_cobranca_out_of_the_list_and_of_the_totals(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        quitada = new_cobranca_chave(conta_chave, "2026-08", today + timedelta(days=5), ALUGUEL_DE_2000)
        aberta = new_cobranca_chave(conta_chave, "2026-09", today + timedelta(days=5), ALUGUEL_DE_2000)
        ObjectGenerator.create_recebimento(quitada, 200000, today.isoformat())

        response = devido(conta_chave, today)

        assert [linha["cobranca_chave"] for linha in response["cobrancas"]] == [aberta]
        assert response["total_em_aberto_centavos"] == 200000
        assert response["total_pago_centavos"] == 0
        assert response["total_devido_na_data_centavos"] == 200000

    def test_includes_a_cobranca_not_yet_due_without_encargos(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        new_cobranca_chave(conta_chave, "2026-09", today + timedelta(days=5), ALUGUEL_DE_2000)

        response = devido(conta_chave, today)

        assert sem_os_recebimentos(response["cobrancas"][0])["status"] == "aberta"
        assert response["multa_centavos"] == 0
        assert response["juros_centavos"] == 0
        assert response["total_devido_na_data_centavos"] == 200000

    def test_shows_a_reversed_recebimento_without_counting_it(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave, "2026-09", today + timedelta(days=5), ALUGUEL_DE_2000)
        estornado = ObjectGenerator.create_recebimento(cobranca_chave, 50000, today.isoformat())
        ObjectGenerator.create_estorno(estornado["transacao_chave"])
        valido = ObjectGenerator.create_recebimento(cobranca_chave, 30000, today.isoformat())

        response = devido(conta_chave, today)
        linha = response["cobrancas"][0]

        assert linha["status"] == "parcial"
        assert linha["total_pago_centavos"] == 30000
        assert linha["total_em_aberto_centavos"] == 170000
        assert [(r["transacao_chave"], r["valor_centavos"], r["estornado"]) for r in linha["recebimentos"]] == [
            (estornado["transacao_chave"], 50000, True),
            (valido["transacao_chave"], 30000, False),
        ]
        assert response["total_pago_centavos"] == 30000

    def test_uses_the_date_of_sao_paulo_when_data_is_missing(self):
        conta_chave = new_conta_chave()
        new_cobranca_chave(conta_chave, "2026-09", today_in_sao_paulo() - timedelta(days=10), ALUGUEL_DE_2000)

        response = devido(conta_chave)

        assert response["data"] == today_in_sao_paulo().isoformat(), "o dia virou em Sao Paulo durante o teste; rode de novo"
        assert response["total_devido_na_data_centavos"] == 204666

    def test_accepts_a_future_data_to_simulate(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        new_cobranca_chave(conta_chave, "2026-09", today - timedelta(days=10), ALUGUEL_DE_2000)

        response = devido(conta_chave, today + timedelta(days=20))

        assert response["multa_centavos"] == 4000
        assert response["juros_centavos"] == 2000
        assert response["total_devido_na_data_centavos"] == 206000

    def test_refuses_data_before_the_last_recebimento_of_any_cobranca(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        quitada = new_cobranca_chave(conta_chave, "2026-08", today + timedelta(days=5), ALUGUEL_DE_2000)
        new_cobranca_chave(conta_chave, "2026-09", today + timedelta(days=5), ALUGUEL_DE_2000)
        ObjectGenerator.create_recebimento(quitada, 200000, today.isoformat())

        status, response = RequestGenerator.GET_conta_devido(conta_chave, {"data": (today - timedelta(days=1)).isoformat()})
        assert status == 422
        assert response["code"] == "QIT001027"

        status, _response = RequestGenerator.GET_conta_devido(conta_chave, {"data": today.isoformat()})
        assert status == 200

    def test_refuses_data_that_does_not_exist_in_the_calendar(self):
        status, response = RequestGenerator.GET_conta_devido(new_conta_chave(), {"data": "2026-02-30"})
        assert status == 422
        assert response["code"] == "QIT001025"

    def test_schema_refuses_data_out_of_format_and_unknown_parameter(self):
        conta_chave = new_conta_chave()

        for params in [{"data": "30/09/2026"}, {"data": ""}, {"data": "2026-9-5"}, {"dia": "2026-09-05"}, {"limite": "10"}]:
            status, response = RequestGenerator.GET_conta_devido(conta_chave, params)
            assert status == 400, params
            assert response["code"] == "QIT000001"

    def test_checks_the_parameters_before_the_conta(self):
        status, response = RequestGenerator.GET_conta_devido(UNKNOWN_CHAVE, {"data": "30/09/2026"})
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_not_found(self):
        for conta_chave in [UNKNOWN_CHAVE, "nao-e-uma-chave", UNKNOWN_CHAVE.upper()]:
            status, response = RequestGenerator.GET_conta_devido(conta_chave)
            assert status == 404, conta_chave
            assert response["code"] == "QIT001011"

    def test_does_not_show_cobrancas_of_another_conta(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        outra_conta_chave = new_conta_chave()
        new_cobranca_chave(outra_conta_chave, "2026-09", today - timedelta(days=10), ALUGUEL_DE_2000)

        response = devido(conta_chave, today)

        assert response["cobrancas"] == []
        assert response["total_devido_na_data_centavos"] == 0

    def test_is_not_changed_by_encargo_pagamento_nor_by_repasse(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave, "2026-09", today + timedelta(days=5))
        ObjectGenerator.create_recebimento(cobranca_chave, 180000, today.isoformat())
        antes = devido(conta_chave, today)

        ObjectGenerator.create_encargo_pagamento(conta_chave, "condominio", 35000)
        ObjectGenerator.create_repasse(conta_chave, 130000)

        assert devido(conta_chave, today) == antes
        assert antes["total_em_aberto_centavos"] == 20000
        assert antes["total_pago_centavos"] == 180000

    def test_only_reads(self):
        today = today_in_sao_paulo()
        conta_chave = new_conta_chave()
        cobranca_chave = new_cobranca_chave(conta_chave, "2026-09", today + timedelta(days=5))
        ObjectGenerator.create_recebimento(cobranca_chave, 180000, today.isoformat())
        _status, saldo_antes = RequestGenerator.GET_conta_saldo(conta_chave)
        _status, extrato_antes = RequestGenerator.GET_conta_extrato(conta_chave)

        devido(conta_chave, today)
        devido(conta_chave, today + timedelta(days=30))

        _status, saldo_depois = RequestGenerator.GET_conta_saldo(conta_chave)
        _status, extrato_depois = RequestGenerator.GET_conta_extrato(conta_chave)
        assert saldo_depois == saldo_antes
        assert extrato_depois == extrato_antes

    def test_refuses_request_without_token(self):
        response = ClientRequisition.send("GET", f"/contas/{new_conta_chave()}/devido")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        response = ClientRequisition.send(
            "POST", f"/contas/{new_conta_chave()}/devido", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}
        )
        assert response.response_status == 405
        assert response.response_json["code"] == "QIT000405"
