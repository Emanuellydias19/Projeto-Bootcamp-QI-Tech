from datetime import datetime

from models import Conta
from utils.dates import format_moment


class ContaDTO:
    @staticmethod
    def only_obj_key(conta: Conta) -> dict:
        dto = dict()
        dto["conta_chave"] = conta.chave

        return dto

    @staticmethod
    def saldo_to_dict(conta: Conta, ultimo_lancamento_em: datetime) -> dict:
        dto = dict()
        dto["conta_chave"] = conta.chave
        dto["saldo_disponivel_centavos"] = conta.saldo_disponivel
        dto["saldo_reservado_centavos"] = conta.saldo_reservado
        dto["ultimo_lancamento_em"] = None

        if ultimo_lancamento_em is not None:
            dto["ultimo_lancamento_em"] = format_moment(ultimo_lancamento_em)

        return dto
