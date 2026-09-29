import re
from datetime import datetime, timedelta, timezone

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator, today_in_sao_paulo
from tests.utils.requisition import ClientRequisition


def new_conta_chave() -> str:
    proprietario_chave = ObjectGenerator.create_proprietario()["proprietario_chave"]

    return ObjectGenerator.create_conta(proprietario_chave)["conta_chave"]


class TestContaSaldo:
    def test_returns_zero_saldos_for_a_new_conta(self):
        conta_chave = new_conta_chave()

        status, response = RequestGenerator.GET_conta_saldo(conta_chave)
        assert status == 200
        assert response == {
            "conta_chave": conta_chave,
            "saldo_disponivel_centavos": 0,
            "saldo_reservado_centavos": 0,
            "ultimo_lancamento_em": None,
        }

    def test_shows_the_date_of_the_last_lancamento(self):
        conta_chave = new_conta_chave()
        vencimento = today_in_sao_paulo() + timedelta(days=5)
        cobranca_chave = ObjectGenerator.create_cobranca(conta_chave, vencimento=vencimento.isoformat())["cobranca_chave"]

        status, _response = RequestGenerator.POST_cobranca_recebimentos(
            cobranca_chave, PayloadGenerator.create_recebimento_payload(1000, today_in_sao_paulo().isoformat())
        )
        assert status == 201

        status, response = RequestGenerator.GET_conta_saldo(conta_chave)
        assert status == 200
        assert re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", response["ultimo_lancamento_em"])

        ultimo_lancamento_em = datetime.strptime(response["ultimo_lancamento_em"], "%Y-%m-%dT%H:%M:%SZ")
        assert abs(datetime.now(timezone.utc) - ultimo_lancamento_em.replace(tzinfo=timezone.utc)) < timedelta(hours=1)

    def test_not_found(self):
        status, response = RequestGenerator.GET_conta_saldo("00000000-0000-0000-0000-000000000000")
        assert status == 404
        assert response["code"] == "QIT001011"

    def test_treats_chave_out_of_format_as_not_found(self):
        conta_chave = new_conta_chave()

        for chave in ["abc", conta_chave + " ", conta_chave.upper(), conta_chave[:-1] + "\x00"]:
            status, response = RequestGenerator.GET_conta_saldo(chave)
            assert status == 404, repr(chave)
            assert response["code"] == "QIT001011"

    def test_refuses_request_without_token(self):
        response = ClientRequisition.send("GET", f"/contas/{new_conta_chave()}/saldo")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
