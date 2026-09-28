from tests.utils.requisition import BaseConnectorResponse
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator


class ObjectGenerator:
    @staticmethod
    def create_sample_entity(hello: str = None) -> BaseConnectorResponse:

        sample_entity_payload = PayloadGenerator.create_sample_entity_payload(hello=hello)

        status, response = RequestGenerator.POST_sample_entity(sample_entity_payload)
        assert status == 201

        return response

    @staticmethod
    def update_sample_entity(sample_entity_key, new_status: str = None) -> BaseConnectorResponse:

        sample_entity_payload = PayloadGenerator.create_new_status_payload(new_status)

        status, response = RequestGenerator.PUT_sample_entity(sample_entity_key, sample_entity_payload)
        assert status == 202

        return response

    @staticmethod
    def create_proprietario() -> dict:
        proprietario_payload = PayloadGenerator.create_proprietario_payload()

        status, response = RequestGenerator.POST_proprietarios(proprietario_payload)
        assert status == 201

        return response

    @staticmethod
    def create_conta(
        proprietario_chave: str,
        multa_bps: int = None,
        juros_mensal_bps: int = None,
        taxa_administracao_bps: int = None,
    ) -> dict:
        conta_payload = PayloadGenerator.create_conta_payload(
            proprietario_chave,
            taxa_administracao_bps=taxa_administracao_bps,
            multa_bps=multa_bps,
            juros_mensal_bps=juros_mensal_bps,
        )

        status, response = RequestGenerator.POST_contas(conta_payload)
        assert status == 201

        return response

    @staticmethod
    def create_cobranca(conta_chave: str, vencimento: str = None, itens: list = None, competencia: str = None) -> dict:
        cobranca_payload = PayloadGenerator.create_cobranca_payload(
            competencia=competencia, vencimento=vencimento, itens=itens
        )

        status, response = RequestGenerator.POST_conta_cobrancas(conta_chave, cobranca_payload)
        assert status == 201

        return response

    @staticmethod
    def create_recebimento(cobranca_chave: str, valor_centavos: int, pago_em: str) -> dict:
        recebimento_payload = PayloadGenerator.create_recebimento_payload(valor_centavos, pago_em)

        status, response = RequestGenerator.POST_cobranca_recebimentos(cobranca_chave, recebimento_payload)
        assert status == 201

        return response
