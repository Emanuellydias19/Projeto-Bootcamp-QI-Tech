from datetime import timedelta

from tests.utils import (
    ObjectGenerator,
    PayloadGenerator,
    RequestGenerator,
    adiantar_o_relogio_da_cobranca,
    today_in_sao_paulo,
)
from tests.utils.requisition import ClientRequisition


UNKNOWN_CHAVE = "00000000-0000-0000-0000-000000000000"


def new_conta_chave(multa_bps: int = 200, juros_mensal_bps: int = 100) -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave, multa_bps=multa_bps, juros_mensal_bps=juros_mensal_bps)[
        "conta_chave"
    ]


def encargos_on(cobranca_chave: str, data: str) -> dict:
    status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": data})
    assert status == 200

    return {
        "multa_centavos": response["multa_centavos"],
        "juros_centavos": response["juros_centavos"],
        "total_devido_na_data_centavos": response["total_devido_na_data_centavos"],
    }


class TestCobrancaGet:
    def test_has_no_encargos_up_to_the_vencimento(self):
        cobranca_chave = ObjectGenerator.create_cobranca(new_conta_chave())["cobranca_chave"]

        for data in ["2026-09-01", "2026-10-05"]:
            assert encargos_on(cobranca_chave, data) == {
                "multa_centavos": 0,
                "juros_centavos": 0,
                "total_devido_na_data_centavos": 200000,
            }

    def test_calculates_multa_and_juros_after_the_vencimento(self):
        cobranca_chave = ObjectGenerator.create_cobranca(
            new_conta_chave(), vencimento="2026-10-05", itens=[{"natureza": "aluguel", "valor_centavos": 200000}]
        )["cobranca_chave"]

        assert encargos_on(cobranca_chave, "2026-10-06") == {
            "multa_centavos": 4000,
            "juros_centavos": 66,
            "total_devido_na_data_centavos": 204066,
        }
        assert encargos_on(cobranca_chave, "2026-10-15") == {
            "multa_centavos": 4000,
            "juros_centavos": 666,
            "total_devido_na_data_centavos": 204666,
        }

    def test_truncates_multa_and_juros_once_over_all_the_itens(self):
        itens = [
            {"natureza": "aluguel", "valor_centavos": 10025},
            {"natureza": "condominio", "valor_centavos": 10025},
            {"natureza": "iptu", "valor_centavos": 10025},
        ]
        cobranca_chave = ObjectGenerator.create_cobranca(new_conta_chave(), vencimento="2026-10-05", itens=itens)[
            "cobranca_chave"
        ]

        assert encargos_on(cobranca_chave, "2026-10-06") == {
            "multa_centavos": 601,
            "juros_centavos": 10,
            "total_devido_na_data_centavos": 30686,
        }

    def test_uses_multa_and_juros_of_the_conta(self):
        cobranca_chave = ObjectGenerator.create_cobranca(
            new_conta_chave(multa_bps=1000, juros_mensal_bps=300),
            vencimento="2026-10-05",
            itens=[{"natureza": "aluguel", "valor_centavos": 100000}],
        )["cobranca_chave"]

        assert encargos_on(cobranca_chave, "2026-10-15") == {
            "multa_centavos": 10000,
            "juros_centavos": 1000,
            "total_devido_na_data_centavos": 111000,
        }

    def test_item_included_after_the_vencimento_has_no_retroactive_encargos(self):
        today = today_in_sao_paulo()
        vencimento = today - timedelta(days=10)
        cobranca_chave = ObjectGenerator.create_cobranca(
            new_conta_chave(),
            vencimento=vencimento.isoformat(),
            itens=[{"natureza": "aluguel", "valor_centavos": 200000}],
        )["cobranca_chave"]

        status, _response = RequestGenerator.POST_cobranca_itens(
            cobranca_chave, PayloadGenerator.create_item_payload(valor_centavos=30000)
        )
        assert status == 201

        status, response = RequestGenerator.GET_cobranca(cobranca_chave)
        assert response["data"] == today.isoformat(), "o dia virou em Sao Paulo durante o teste; rode de novo"

        assert encargos_on(cobranca_chave, today.isoformat()) == {
            "multa_centavos": 4000,
            "juros_centavos": 666,
            "total_devido_na_data_centavos": 234666,
        }
        assert encargos_on(cobranca_chave, (today + timedelta(days=5)).isoformat()) == {
            "multa_centavos": 4600,
            "juros_centavos": 1050,
            "total_devido_na_data_centavos": 235650,
        }

    def test_item_included_after_the_vencimento_has_no_retroactive_encargos_when_the_clock_went_back(self):
        today = today_in_sao_paulo()
        vencimento = today - timedelta(days=10)
        cobranca_chave = ObjectGenerator.create_cobranca(
            new_conta_chave(),
            vencimento=vencimento.isoformat(),
            itens=[{"natureza": "aluguel", "valor_centavos": 200000}],
        )["cobranca_chave"]
        adiantar_o_relogio_da_cobranca(cobranca_chave)

        status, _response = RequestGenerator.POST_cobranca_itens(
            cobranca_chave, PayloadGenerator.create_item_payload(valor_centavos=30000)
        )
        assert status == 201

        status, response = RequestGenerator.GET_cobranca(cobranca_chave)
        assert response["data"] == today.isoformat(), "o dia virou em Sao Paulo durante o teste; rode de novo"

        assert encargos_on(cobranca_chave, today.isoformat()) == {
            "multa_centavos": 4000,
            "juros_centavos": 666,
            "total_devido_na_data_centavos": 234666,
        }

    def test_item_included_before_the_vencimento_uses_the_vencimento(self):
        vencimento = today_in_sao_paulo() + timedelta(days=5)
        cobranca_chave = ObjectGenerator.create_cobranca(
            new_conta_chave(),
            vencimento=vencimento.isoformat(),
            itens=[{"natureza": "aluguel", "valor_centavos": 200000}],
        )["cobranca_chave"]

        status, _response = RequestGenerator.POST_cobranca_itens(
            cobranca_chave, PayloadGenerator.create_item_payload(valor_centavos=30000)
        )
        assert status == 201

        assert encargos_on(cobranca_chave, vencimento.isoformat()) == {
            "multa_centavos": 0,
            "juros_centavos": 0,
            "total_devido_na_data_centavos": 230000,
        }
        assert encargos_on(cobranca_chave, (vencimento + timedelta(days=10)).isoformat()) == {
            "multa_centavos": 4600,
            "juros_centavos": 766,
            "total_devido_na_data_centavos": 235366,
        }

    def test_uses_the_date_of_sao_paulo_when_data_is_missing(self):
        today = today_in_sao_paulo()
        cobranca_chave = ObjectGenerator.create_cobranca(
            new_conta_chave(), vencimento=(today + timedelta(days=5)).isoformat()
        )["cobranca_chave"]

        status, response = RequestGenerator.GET_cobranca(cobranca_chave)
        assert status == 200
        assert response["data"] in [today.isoformat(), today_in_sao_paulo().isoformat()]
        assert response["multa_centavos"] == 0
        assert response["juros_centavos"] == 0

    def test_refuses_data_out_of_format(self):
        cobranca_chave = ObjectGenerator.create_cobranca(new_conta_chave())["cobranca_chave"]

        for data in ["2026/10/05", "05-10-2026", "abc", "", "2026-10-05\n", "2026-10-0٥"]:
            status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": data})
            assert status == 400, data
            assert response["code"] == "QIT000001"

    def test_refuses_data_that_does_not_exist_in_the_calendar(self):
        cobranca_chave = ObjectGenerator.create_cobranca(new_conta_chave())["cobranca_chave"]

        status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": "2026-02-30"})
        assert status == 422
        assert response["code"] == "QIT001025"

    def test_refuses_data_before_the_last_recebimento(self):
        vencimento = today_in_sao_paulo() - timedelta(days=30)
        cobranca_chave = ObjectGenerator.create_cobranca(new_conta_chave(), vencimento=vencimento.isoformat())[
            "cobranca_chave"
        ]
        pago_em = vencimento + timedelta(days=10)

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, PayloadGenerator.create_recebimento_payload(1000, pago_em.isoformat())
        )
        assert status == 201

        status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": (pago_em - timedelta(days=1)).isoformat()})
        assert status == 422
        assert response["code"] == "QIT001027"

        status, _response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": pago_em.isoformat()})
        assert status == 200

    def test_schema_refuses_unknown_query_parameter(self):
        cobranca_chave = ObjectGenerator.create_cobranca(new_conta_chave())["cobranca_chave"]

        status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"outro": "x"})
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_not_found(self):
        cobranca_chave = ObjectGenerator.create_cobranca(new_conta_chave())["cobranca_chave"]

        for chave in [UNKNOWN_CHAVE, "abc", cobranca_chave + " ", cobranca_chave.upper()]:
            status, response = RequestGenerator.GET_cobranca(chave)
            assert status == 404, repr(chave)
            assert response["code"] == "QIT001015"

    def test_refuses_request_without_token(self):
        cobranca_chave = ObjectGenerator.create_cobranca(new_conta_chave())["cobranca_chave"]

        response = ClientRequisition.send("GET", f"/cobrancas/{cobranca_chave}")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
