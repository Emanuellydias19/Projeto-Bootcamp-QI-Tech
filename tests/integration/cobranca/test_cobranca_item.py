from datetime import timedelta

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator, today_in_sao_paulo
from tests.utils.requisition import ClientRequisition


UNKNOWN_CHAVE = "00000000-0000-0000-0000-000000000000"
MAXIMUM_CENTAVOS = 9007199254740991


def new_cobranca_chave() -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]
    conta_chave = ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]

    return ObjectGenerator.create_cobranca(conta_chave)["cobranca_chave"]


class TestCobrancaItem:
    def test_adds_despesa_extra(self):
        cobranca_chave = new_cobranca_chave()

        status, response = RequestGenerator.POST_cobranca_itens(cobranca_chave, PayloadGenerator.create_item_payload())
        assert status == 201
        assert response == {
            "cobranca_chave": cobranca_chave,
            "itens": [
                {"natureza": "aluguel", "valor_devido_centavos": 150000},
                {"natureza": "condominio", "valor_devido_centavos": 35000},
                {"natureza": "iptu", "valor_devido_centavos": 15000},
                {"natureza": "despesa_extra", "valor_devido_centavos": 8000},
            ],
        }

    def test_adds_more_than_one_despesa_extra(self):
        cobranca_chave = new_cobranca_chave()

        for valor in [8000, 12000]:
            status, response = RequestGenerator.POST_cobranca_itens(
                cobranca_chave, PayloadGenerator.create_item_payload(valor_centavos=valor)
            )
            assert status == 201

        assert response["itens"][3:] == [
            {"natureza": "despesa_extra", "valor_devido_centavos": 8000},
            {"natureza": "despesa_extra", "valor_devido_centavos": 12000},
        ]

    def test_accepts_valor_at_the_maximum(self):
        status, _response = RequestGenerator.POST_cobranca_itens(
            new_cobranca_chave(), PayloadGenerator.create_item_payload(valor_centavos=MAXIMUM_CENTAVOS)
        )
        assert status == 201

    def test_refuses_cobranca_that_does_not_exist(self):
        cobranca_chave_real = new_cobranca_chave()

        for cobranca_chave in [UNKNOWN_CHAVE, "abc", cobranca_chave_real + " ", cobranca_chave_real.upper()]:
            status, response = RequestGenerator.POST_cobranca_itens(cobranca_chave, PayloadGenerator.create_item_payload())
            assert status == 404, repr(cobranca_chave)
            assert response["code"] == "QIT001015"

        status, response = RequestGenerator.GET_cobranca(cobranca_chave_real, {"data": "2026-10-05"})
        assert status == 200
        assert len(response["itens"]) == 3

    def test_schema_refuses_valor_with_decimal_places_or_above_the_maximum(self):
        cobranca_chave = new_cobranca_chave()

        for valor in [8000.0, MAXIMUM_CENTAVOS + 1]:
            status, response = RequestGenerator.POST_cobranca_itens(
                cobranca_chave, PayloadGenerator.create_item_payload(valor_centavos=valor)
            )
            assert status == 400, valor
            assert response["code"] == "QIT000001"

    def test_accepts_item_on_a_parcial_cobranca(self):
        proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]
        conta_chave = ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]
        vencimento = today_in_sao_paulo() + timedelta(days=5)
        cobranca_chave = ObjectGenerator.create_cobranca(conta_chave, vencimento=vencimento.isoformat())["cobranca_chave"]

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, PayloadGenerator.create_recebimento_payload(1000, today_in_sao_paulo().isoformat())
        )
        assert status == 201

        status, response = RequestGenerator.POST_cobranca_itens(cobranca_chave, PayloadGenerator.create_item_payload())
        assert status == 201
        assert response["itens"][3] == {"natureza": "despesa_extra", "valor_devido_centavos": 8000}

        status, response = RequestGenerator.GET_cobranca(cobranca_chave)
        assert status == 200
        assert response["status"] == "parcial"
        assert response["total_em_aberto_centavos"] == 207000

    def test_refuses_item_on_a_quitada_cobranca(self):
        proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]
        conta_chave = ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]
        vencimento = today_in_sao_paulo() + timedelta(days=5)
        cobranca_chave = ObjectGenerator.create_cobranca(conta_chave, vencimento=vencimento.isoformat())["cobranca_chave"]

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, PayloadGenerator.create_recebimento_payload(200000, today_in_sao_paulo().isoformat())
        )
        assert status == 201

        status, response = RequestGenerator.POST_cobranca_itens(cobranca_chave, PayloadGenerator.create_item_payload())
        assert status == 409
        assert response["code"] == "QIT001017"

    def test_refuses_valor_not_positive(self):
        cobranca_chave = new_cobranca_chave()

        for valor in [0, -1]:
            status, response = RequestGenerator.POST_cobranca_itens(
                cobranca_chave, PayloadGenerator.create_item_payload(valor_centavos=valor)
            )
            assert status == 422, valor
            assert response["code"] == "QIT001018"

    def test_schema_refuses_natureza_other_than_despesa_extra(self):
        cobranca_chave = new_cobranca_chave()

        for natureza in ["aluguel", "condominio", "iptu", "multa", "juros"]:
            status, response = RequestGenerator.POST_cobranca_itens(
                cobranca_chave, PayloadGenerator.create_item_payload(natureza=natureza)
            )
            assert status == 400, natureza
            assert response["code"] == "QIT000001"

    def test_schema_refuses_missing_or_unknown_field(self):
        cobranca_chave = new_cobranca_chave()

        for field in ["natureza", "valor_centavos"]:
            payload = PayloadGenerator.create_item_payload()
            del payload[field]

            status, response = RequestGenerator.POST_cobranca_itens(cobranca_chave, payload)
            assert status == 400, field
            assert response["code"] == "QIT000001"

        payload = PayloadGenerator.create_item_payload()
        payload["cobranca_id"] = 1

        status, response = RequestGenerator.POST_cobranca_itens(cobranca_chave, payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_request_without_token_and_records_nothing(self):
        cobranca_chave = new_cobranca_chave()

        response = ClientRequisition.send(
            "POST", f"/cobrancas/{cobranca_chave}/itens", payload=PayloadGenerator.create_item_payload()
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        status, response = RequestGenerator.GET_cobranca(cobranca_chave, {"data": "2026-10-05"})
        assert status == 200
        assert len(response["itens"]) == 3
