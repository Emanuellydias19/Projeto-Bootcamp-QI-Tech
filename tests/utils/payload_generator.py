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

    @staticmethod
    def create_cobranca_payload(competencia: str = None, vencimento: str = None, itens: list = None) -> dict:
        if competencia is None:
            competencia = "2026-10"

        if vencimento is None:
            vencimento = "2026-10-05"

        if itens is None:
            itens = [
                {"natureza": "aluguel", "valor_centavos": 150000},
                {"natureza": "condominio", "valor_centavos": 35000},
                {"natureza": "iptu", "valor_centavos": 15000},
            ]

        payload = {
            "competencia": competencia,
            "vencimento": vencimento,
            "itens": itens,
        }
        return payload

    @staticmethod
    def create_recebimento_payload(valor_centavos: int, pago_em: str) -> dict:
        payload = {
            "valor_centavos": valor_centavos,
            "pago_em": pago_em,
        }
        return payload

    @staticmethod
    def create_item_payload(natureza: str = None, valor_centavos: int = None) -> dict:
        if natureza is None:
            natureza = "despesa_extra"

        if valor_centavos is None:
            valor_centavos = 8000

        payload = {
            "natureza": natureza,
            "valor_centavos": valor_centavos,
        }
        return payload
