from sqlalchemy.exc import SQLAlchemyError

from controllers.base_controller import BaseController
from repositories import HealthCheckRepository


class HealthCheckController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.health_check_repository = HealthCheckRepository(self.context)

    def is_database_ready(self) -> bool:
        try:
            self.health_check_repository.ping()
        except SQLAlchemyError:
            self.logger.warning("O banco nao respondeu a verificacao de prontidao")
            return False

        return True
