from models import Transacao


class TransacaoDTO:
    @staticmethod
    def recebimento_to_dict(transacao: Transacao, imputacao: dict) -> dict:
        rateio = []
        for parcela in imputacao["rateio"]:
            rateio.append({"natureza": parcela["natureza"], "valor_centavos": parcela["valor_centavos"]})

        dto = dict()
        dto["transacao_chave"] = transacao.chave
        dto["rateio"] = rateio
        dto["em_aberto"] = imputacao["em_aberto"]

        return dto

    @staticmethod
    def encargo_to_dict(transacao: Transacao, natureza: str, valor_centavos: int) -> dict:
        dto = dict()
        dto["transacao_chave"] = transacao.chave
        dto["natureza"] = natureza
        dto["valor_centavos"] = valor_centavos

        return dto

    @staticmethod
    def repasse_to_dict(transacao: Transacao, valor_bruto_centavos: int, taxa_centavos: int) -> dict:
        dto = dict()
        dto["transacao_chave"] = transacao.chave
        dto["valor_bruto_centavos"] = valor_bruto_centavos
        dto["taxa_centavos"] = taxa_centavos
        dto["liquido_centavos"] = valor_bruto_centavos - taxa_centavos

        return dto
