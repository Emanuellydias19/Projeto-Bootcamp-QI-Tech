from controllers.base_controller import BaseController
from dtos import ContaDTO
from errors import DuplicatedConta, InvalidBps, NotFoundConta, NotFoundPoliticaImputacao, NotFoundProprietario
from models import Conta
from repositories import ContaRepository, PoliticaImputacaoRepository, ProprietarioRepository
from utils.chave import is_valid_chave

BPS_FIELDS = ["taxa_administracao_bps", "multa_bps", "juros_mensal_bps"]
MINIMUM_BPS = 0
MAXIMUM_BPS = 10000


class ContaController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.conta_repository = ContaRepository(self.context)
        self.proprietario_repository = ProprietarioRepository(self.context)
        self.politica_imputacao_repository = PoliticaImputacaoRepository(self.context)

    def create(self, conta_data: dict) -> dict:
        self.logger.debug("Abrindo uma nova conta")

        proprietario = self.proprietario_repository.get_by_chave(conta_data["proprietario_chave"])

        if proprietario is None:
            raise NotFoundProprietario(conta_data["proprietario_chave"])

        politica = self.politica_imputacao_repository.get_by_chave(conta_data["politica_imputacao_chave"])

        if politica is None:
            raise NotFoundPoliticaImputacao(conta_data["politica_imputacao_chave"])

        for field in BPS_FIELDS:
            if conta_data[field] < MINIMUM_BPS or conta_data[field] > MAXIMUM_BPS:
                raise InvalidBps(field, MINIMUM_BPS, MAXIMUM_BPS)

        conta = self.conta_repository.create(proprietario, politica, conta_data)

        self._flush_or_raise({Conta.PROPRIETARIO_IMOVEL_UNIQUE_CONSTRAINT: DuplicatedConta})

        conta_dto = ContaDTO.only_obj_key(conta)

        self.session.commit()

        return conta_dto

    def get_saldo(self, conta_chave: str) -> dict:
        conta = self._get_conta(conta_chave)

        return ContaDTO.saldo_to_dict(conta)

    def _get_conta(self, conta_chave: str) -> Conta:
        if not is_valid_chave(conta_chave):
            raise NotFoundConta(conta_chave)

        conta = self.conta_repository.get_by_chave(conta_chave)

        if conta is None:
            raise NotFoundConta(conta_chave)

        return conta
