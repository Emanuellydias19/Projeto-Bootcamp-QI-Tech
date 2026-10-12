from datetime import date

from models import Cobranca, Conta
from utils.dates import format_moment


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

    @staticmethod
    def devido_to_dict(conta: Conta, data: date, linhas: list) -> dict:
        cobrancas = []
        total_em_aberto = 0
        multa = 0
        juros = 0
        total_pago = 0
        total_devido = 0
        for linha in linhas:
            cobranca = linha["cobranca"]
            posicao = linha["posicao"]

            recebimentos = []
            for recebimento, transacao_chave, estorno_id in linha["recebimentos"]:
                recebimentos.append(
                    {
                        "recebimento_chave": recebimento.chave,
                        "transacao_chave": transacao_chave,
                        "pago_em": recebimento.pago_em.isoformat(),
                        "criado_em": format_moment(recebimento.criado_em),
                        "valor_centavos": recebimento.valor_centavos,
                        "estornado": estorno_id is not None,
                    }
                )

            cobrancas.append(
                {
                    "cobranca_chave": cobranca.chave,
                    "competencia": cobranca.competencia,
                    "vencimento": cobranca.vencimento.isoformat(),
                    "status": posicao["status"],
                    "total_em_aberto_centavos": posicao["total_em_aberto_centavos"],
                    "multa_centavos": posicao["multa_centavos"],
                    "juros_centavos": posicao["juros_centavos"],
                    "total_pago_centavos": posicao["total_pago_centavos"],
                    "total_devido_na_data_centavos": posicao["total_devido_na_data_centavos"],
                    "recebimentos": recebimentos,
                }
            )

            total_em_aberto = total_em_aberto + posicao["total_em_aberto_centavos"]
            multa = multa + posicao["multa_centavos"]
            juros = juros + posicao["juros_centavos"]
            total_pago = total_pago + posicao["total_pago_centavos"]
            total_devido = total_devido + posicao["total_devido_na_data_centavos"]

        dto = dict()
        dto["conta_chave"] = conta.chave
        dto["data"] = data.isoformat()
        dto["multa_bps"] = conta.multa_bps
        dto["juros_mensal_bps"] = conta.juros_mensal_bps
        dto["total_em_aberto_centavos"] = total_em_aberto
        dto["multa_centavos"] = multa
        dto["juros_centavos"] = juros
        dto["total_pago_centavos"] = total_pago
        dto["total_devido_na_data_centavos"] = total_devido
        dto["cobrancas"] = cobrancas

        return dto
