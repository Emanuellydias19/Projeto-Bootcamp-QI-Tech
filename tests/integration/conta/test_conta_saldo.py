from tests.utils import ObjectGenerator, RequestGenerator
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
