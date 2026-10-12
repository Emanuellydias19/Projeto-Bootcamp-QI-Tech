import os


SERVICE_ROOT = os.path.abspath(os.path.dirname(__file__))

# Onde moram os arquivos de schema — os .json que descrevem o formato
# que cada requisicao precisa ter. Quem le essa pasta e o
# src/utils/schema_handler.py.
SCHEMA_PATH = os.path.join(SERVICE_ROOT, "schemas")

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "bootcamp-api")

DATABASE_URL = os.environ.get("DATABASE_URL")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")

# A API de boletos: o serviço de fora que este projeto chama pra emitir
# uma cobrança (veja src/connectors/). O endereço vem do ambiente, como
# tudo aqui — na sua máquina ele aponta pro mock server do sábado 4; em
# produção, apontaria pro serviço de verdade. O código não sabe a
# diferença, e esse é o ponto.
BANKSLIP_API_URL = os.environ.get("BANKSLIP_API_URL", "http://localhost:8080")
BANKSLIP_API_INTERNAL_TOKEN = os.environ.get("BANKSLIP_API_INTERNAL_TOKEN", "default_token")

# Quantos segundos esperar pelo serviço de boletos antes de desistir.
# Todo connector TEM um timeout — o porquê está em
# src/connectors/rest_connector.py.
BANKSLIP_API_TIMEOUT = int(os.environ.get("BANKSLIP_API_TIMEOUT", "5"))

# Rotas públicas: não exigem o header INTERNAL-TOKEN. São as que
# precisam responder pra quem ainda não tem token nenhum: a raiz, que
# diz quem é este serviço, e os health checks, que o Docker consulta pra
# saber se a API já está de pé.
BYPASS_ENDPOINTS = [
    "/",
    "/health_check",
    "/health_check/ready",
]

MAXIMUM_BODY_BYTES = int(os.environ.get("MAXIMUM_BODY_BYTES", "65536"))
DB_LOCK_TIMEOUT_MS = int(os.environ.get("DB_LOCK_TIMEOUT_MS", "5000"))
DB_STATEMENT_TIMEOUT_MS = int(os.environ.get("DB_STATEMENT_TIMEOUT_MS", "15000"))
DB_CONNECT_TIMEOUT_SECONDS = int(os.environ.get("DB_CONNECT_TIMEOUT_SECONDS", "3"))
DEVELOPMENT_ENVIRONMENTS = ["local", "test"]
DEFAULT_INTERNAL_TOKEN = "default_token"
MINIMUM_PRODUCTION_TOKEN_LENGTH = 32

REQUIRED_VARIABLES = ["DATABASE_URL", "INTERNAL_TOKEN"]


def check_variables():
    missing = []
    for name in REQUIRED_VARIABLES:
        if not globals().get(name):
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Faltam variáveis de ambiente: {', '.join(missing)}. "
            "Rodando com 'docker compose up' elas já vêm preenchidas. "
            "Fora do Docker, copie o .env.example para .env."
        )


def check_production_token():
    if APP_ENV.lower() in DEVELOPMENT_ENVIRONMENTS:
        return

    token = INTERNAL_TOKEN.strip()

    if token == DEFAULT_INTERNAL_TOKEN or len(token) < MINIMUM_PRODUCTION_TOKEN_LENGTH:
        raise EnvironmentError(
            f"Fora dos ambientes {' e '.join(DEVELOPMENT_ENVIRONMENTS)}, o INTERNAL_TOKEN precisa ser um segredo "
            f"proprio, com pelo menos {MINIMUM_PRODUCTION_TOKEN_LENGTH} caracteres, e nao o valor padrao do docker-compose."
        )
