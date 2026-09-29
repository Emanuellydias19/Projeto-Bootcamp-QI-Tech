from models import Cobranca


class CobrancaDTO:
    @staticmethod
    def only_obj_key(cobranca: Cobranca) -> dict:
        dto = dict()
        dto["cobranca_chave"] = cobranca.chave

        return dto

    @staticmethod
    def itens_to_dict(cobranca: Cobranca) -> dict:
        itens = []
        for item in cobranca.itens:
            itens.append({"natureza": item.natureza, "valor_devido_centavos": item.valor_devido_centavos})

        dto = dict()
        dto["cobranca_chave"] = cobranca.chave
        dto["itens"] = itens

        return dto

    @staticmethod
    def obj_to_dict(cobranca: Cobranca, posicao: dict) -> dict:
        itens = []
        for linha in posicao["itens"]:
            itens.append(
                {
                    "natureza": linha["item"].natureza,
                    "valor_devido_centavos": linha["item"].valor_devido_centavos,
                    "valor_pago_centavos": linha["valor_pago_centavos"],
                    "valor_em_aberto_centavos": linha["valor_em_aberto_centavos"],
                }
            )

        dto = dict()
        dto["cobranca_chave"] = cobranca.chave
        dto["conta_chave"] = cobranca.conta.chave
        dto["competencia"] = cobranca.competencia
        dto["vencimento"] = cobranca.vencimento.isoformat()
        dto["status"] = posicao["status"]
        dto["itens"] = itens
        dto["total_em_aberto_centavos"] = posicao["total_em_aberto_centavos"]
        dto["data"] = posicao["data"].isoformat()
        dto["multa_centavos"] = posicao["multa_centavos"]
        dto["juros_centavos"] = posicao["juros_centavos"]
        dto["total_devido_na_data_centavos"] = posicao["total_devido_na_data_centavos"]

        return dto
