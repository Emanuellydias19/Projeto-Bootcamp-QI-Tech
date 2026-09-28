from uuid import uuid4

from tests.utils.random_generator import RandomGenerator


POLITICA_PADRAO_CHAVE = "7d2e9b41-3c5a-4f8e-a1b6-9c0d2e4f6a18"


class PayloadGenerator:
    @staticmethod
    def create_sample_entity_payload(
        hello: str = None,
        name: str = None,
        email: str = None,
        document_number: str = None,
        birthdate: str = None,
    ) -> dict:
        """Um cadastro valido, com qualquer campo trocado a pedido.

        Sem argumento nenhum o payload sai aleatorio no que precisa ser
        unico (e-mail e CPF), pra que dois cadastros seguidos nao batam
        na regra de duplicidade. Quem testa FILTRO precisa do contrario
        disso: um valor conhecido, pra poder procurar por ele depois.
        """
        if hello is None:
            hello = "world"

        if name is None:
            name = "Maria da Silva"

        if email is None:
            email = f"maria.silva.{uuid4()}@exemplo.com.br"

        if document_number is None:
            document_number = RandomGenerator.generate_cpf()

        if birthdate is None:
            birthdate = "1990-05-17"

        payload = {
            "hello": hello,
            "name": name,
            "email": email,
            "document_number": document_number,
            "birthdate": birthdate,
        }
        return payload

    @staticmethod
    def create_new_status_payload(new_status: str = None) -> dict:
        payload = {"status": new_status}
        return payload

    @staticmethod
    def create_proprietario_payload(documento: str = None, nome: str = None) -> dict:
        if documento is None:
            documento = RandomGenerator.generate_cpf()

        if nome is None:
            nome = "Maria da Silva"

        payload = {
            "documento": documento,
            "nome": nome,
        }
        return payload

    @staticmethod
    def create_conta_payload(
        proprietario_chave: str,
        imovel_referencia: str = None,
        politica_imputacao_chave: str = None,
        taxa_administracao_bps: int = None,
        multa_bps: int = None,
        juros_mensal_bps: int = None,
    ) -> dict:
        if imovel_referencia is None:
            imovel_referencia = "Rua das Flores, 120, apto 34"

        if politica_imputacao_chave is None:
            politica_imputacao_chave = POLITICA_PADRAO_CHAVE

        if taxa_administracao_bps is None:
            taxa_administracao_bps = 1000

        if multa_bps is None:
            multa_bps = 200

        if juros_mensal_bps is None:
            juros_mensal_bps = 100

        payload = {
            "proprietario_chave": proprietario_chave,
            "imovel_referencia": imovel_referencia,
            "politica_imputacao_chave": politica_imputacao_chave,
            "taxa_administracao_bps": taxa_administracao_bps,
            "multa_bps": multa_bps,
            "juros_mensal_bps": juros_mensal_bps,
        }
        return payload
