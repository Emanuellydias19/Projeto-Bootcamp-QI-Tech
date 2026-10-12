from sqlalchemy import text

from database import Context


class HealthCheckRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def ping(self) -> None:
        self.session.execute(text("SELECT 1"))
