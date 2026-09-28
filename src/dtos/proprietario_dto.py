from models import Proprietario


class ProprietarioDTO:
    @staticmethod
    def only_obj_key(proprietario: Proprietario) -> dict:
        dto = dict()
        dto["proprietario_chave"] = proprietario.chave

        return dto
