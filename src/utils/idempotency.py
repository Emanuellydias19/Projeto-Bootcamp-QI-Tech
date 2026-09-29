import json
from hashlib import sha256

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
MAXIMUM_IDEMPOTENCY_KEY_LENGTH = 255
OPTIONAL_WHITESPACE = " \t"


def read_idempotency_key(headers) -> str:
    idempotency_key = headers.get(IDEMPOTENCY_KEY_HEADER)

    if idempotency_key is None:
        return None

    return idempotency_key.strip(OPTIONAL_WHITESPACE)


def hash_requisicao(operacao: str, chave: str, corpo: dict) -> str:
    corpo_canonico = json.dumps(corpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    return sha256(f"{operacao}|{chave}|{corpo_canonico}".encode("utf-8")).hexdigest()
