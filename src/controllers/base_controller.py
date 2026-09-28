from abc import ABCMeta
from datetime import date

from sqlalchemy.exc import IntegrityError

from database import get_context
from errors import InvalidDate, InvalidValor
from models.base import Base
from utils.chave import is_valid_chave
from utils.dates import parse_date
from utils.logger import get_logger


class BaseController(metaclass=ABCMeta):
    """O que todo controller tem em comum: a conexão com o banco e o log.

    Nada chega por parâmetro: o controller pega o CONTEXTO da requisição
    em que está rodando. Quem preparou esse contexto foi o middleware.

    Guardar o `self.context`, e não só a sessão, é o que permite o
    repository receber `context` em vez de `db`: o contexto é a coisa que
    viaja entre as camadas, e a sessão é só o que ele carrega hoje.

    É aqui que a sessão nasce, no `get_or_create_session` — construir um
    controller é a mesma coisa que dizer "eu uso banco".
    """

    def __init__(self, class_name: str) -> None:
        self.context = get_context()
        self.session = self.context.get_or_create_session()
        self.logger = get_logger(class_name)

    def _flush_or_raise(self, errors_by_constraint: dict) -> None:
        try:
            self.session.flush()
        except IntegrityError as error:
            constraint_name = error.orig.diag.constraint_name

            if constraint_name in errors_by_constraint:
                raise errors_by_constraint[constraint_name]()

            raise

    def _get_or_raise(self, repository, chave: str, not_found_error: type) -> Base:
        return self._find_or_raise(repository.get_by_chave, chave, not_found_error)

    def _get_for_update_or_raise(self, repository, chave: str, not_found_error: type) -> Base:
        return self._find_or_raise(repository.get_by_chave_for_update, chave, not_found_error)

    def _find_or_raise(self, find, chave: str, not_found_error: type) -> Base:
        if not is_valid_chave(chave):
            raise not_found_error(chave)

        entity = find(chave)

        if entity is None:
            raise not_found_error(chave)

        return entity

    def _parse_date_or_raise(self, field: str, text: str) -> date:
        parsed_date = parse_date(text)

        if parsed_date is None:
            raise InvalidDate(field, text)

        return parsed_date

    def _check_valor(self, valor_centavos: int) -> None:
        if valor_centavos <= 0:
            raise InvalidValor(valor_centavos)
