from utils.dates import format_moment


class LancamentoDTO:
    @staticmethod
    def extrato_to_dict(linhas: list, limite: int, proximo_cursor: str) -> dict:
        data = []
        for lancamento, transacao_chave, tipo, transacao_estornada_chave in linhas:
            data.append(
                {
                    "lancamento_chave": lancamento.chave,
                    "transacao_chave": transacao_chave,
                    "tipo": tipo,
                    "natureza": lancamento.natureza,
                    "valor_centavos": lancamento.valor_centavos,
                    "criado_em": format_moment(lancamento.criado_em),
                    "transacao_estornada_chave": transacao_estornada_chave,
                }
            )

        dto = dict()
        dto["data"] = data
        dto["limite"] = limite
        dto["proximo_cursor"] = proximo_cursor

        return dto
