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
