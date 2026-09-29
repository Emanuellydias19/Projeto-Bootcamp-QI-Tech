import re

CHAVE_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def is_valid_chave(chave: str) -> bool:
    return CHAVE_PATTERN.fullmatch(chave) is not None
