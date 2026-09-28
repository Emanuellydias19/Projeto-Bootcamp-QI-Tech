from models import Conta


class ContaDTO:
    @staticmethod
    def only_obj_key(conta: Conta) -> dict:
        dto = dict()
        dto["conta_chave"] = conta.chave

        return dto

    @staticmethod
    def saldo_to_dict(conta: Conta) -> dict:
        dto = dict()
        dto["conta_chave"] = conta.chave
        dto["saldo_disponivel_centavos"] = conta.saldo_disponivel
        dto["saldo_reservado_centavos"] = conta.saldo_reservado
        dto["ultimo_lancamento_em"] = None

        return dto
