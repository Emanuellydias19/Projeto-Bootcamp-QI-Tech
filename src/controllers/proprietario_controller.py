from controllers.base_controller import BaseController
from dtos import ProprietarioDTO
from errors import DuplicatedDocumento, InvalidDocumento
from models import Proprietario
from repositories import ProprietarioRepository
from utils.document_number import is_valid_cnpj, is_valid_cpf


class ProprietarioController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.proprietario_repository = ProprietarioRepository(self.context)

    def create(self, proprietario_data: dict) -> dict:
        self.logger.debug("Cadastrando um novo proprietario")

        documento = proprietario_data["documento"]

        if not is_valid_cpf(documento) and not is_valid_cnpj(documento):
            raise InvalidDocumento()

        proprietario = self.proprietario_repository.create({**proprietario_data, "nome": proprietario_data["nome"].strip()})

        self._flush_or_raise({Proprietario.DOCUMENTO_UNIQUE_CONSTRAINT: DuplicatedDocumento})

        proprietario_dto = ProprietarioDTO.only_obj_key(proprietario)

        self.session.commit()

        return proprietario_dto
