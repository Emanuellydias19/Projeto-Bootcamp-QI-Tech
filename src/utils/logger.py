import json
import logging
import sys
from datetime import datetime, timezone

from constants import APP_ENV, SERVICE_NAME
from utils.request_context import get_request_id

STANDARD_RECORD_FIELDS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime", "request_id", "color_message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", None),
            "message": record.getMessage(),
        }

        for field, value in vars(record).items():
            if field not in STANDARD_RECORD_FIELDS and field not in line:
                line[field] = value

        if record.exc_info:
            line["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            line["stack"] = self.formatStack(record.stack_info)

        return json.dumps(line, ensure_ascii=False, default=str)


class RequestIdFilter(logging.Filter):
    """Carimba toda linha de log com o identificador da requisição.

    "Filter" é um nome infeliz do Python: esta classe não descarta nada
    — ela devolve True para tudo. O que ela faz é acrescentar um campo à
    linha antes de a formatação acontecer. É o gancho oficial do módulo
    de log para isso.

    A alternativa seria lembrar de escrever o identificador em cada
    chamada de logger.info do projeto. Uma hora alguém esquece, e é
    justamente na linha que você iria precisar.

    Quando não há requisição em andamento — a API subindo, por
    exemplo — o campo sai como "-", e nada quebra.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def setup_logging() -> None:
    """Liga o log da aplicação. Chamada uma vez, quando a API sobe."""
    level = logging.INFO
    if APP_ENV.upper() in ("LOCAL", "TEST"):
        level = logging.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    # O filtro fica no HANDLER, não num logger específico: assim toda
    # linha que passar por aqui ganha o campo, venha ela do nosso código
    # ou de qualquer biblioteca. Se ficasse num logger só, a primeira
    # linha vinda de outro lugar derrubaria a formatação.
    handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    server_logger = logging.getLogger("uvicorn")
    server_logger.handlers = []
    server_logger.propagate = True

    # O urllib3 fala MUITO em modo debug, e nada disso e nosso: sao
    # detalhes de conexao HTTP das bibliotecas que usamos.
    for biblioteca_falante in ["urllib3"]:
        logging.getLogger(biblioteca_falante).setLevel(logging.CRITICAL)


def get_logger(class_name: str) -> logging.Logger:
    """Devolve o log com o nome de quem está escrevendo.

    Assim, olhando a linha do log, você sabe de qual arquivo ela veio.
    """
    return logging.getLogger(f"{SERVICE_NAME}.{class_name}")
