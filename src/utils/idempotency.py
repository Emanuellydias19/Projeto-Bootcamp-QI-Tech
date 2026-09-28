import json
from hashlib import sha256

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
MAXIMUM_IDEMPOTENCY_KEY_LENGTH = 255


def hash_requisicao(operacao: str, chave: str, corpo: dict) -> str:
    corpo_canonico = json.dumps(corpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    return sha256(f"{operacao}|{chave}|{corpo_canonico}".encode("utf-8")).hexdigest()
