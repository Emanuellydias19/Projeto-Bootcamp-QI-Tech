from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import TransacaoController
from utils.idempotency import IDEMPOTENCY_KEY_HEADER
from utils.schema_handler import SchemaHandler


class TransacaoResource:
    @SchemaHandler.validate("post_cobranca_recebimento.json")
    @SchemaHandler.validate_idempotency_key
    def on_post_recebimento(self, cobranca_chave: str, payload: dict, request: Request) -> JSONResponse:
        controller = TransacaoController()
        recebimento, created = controller.receber(
            cobranca_chave, payload, request.headers.get(IDEMPOTENCY_KEY_HEADER)
        )

        if created:
            status_code = http_status.HTTP_201_CREATED
        else:
            status_code = http_status.HTTP_200_OK

        return JSONResponse(
            content=jsonable_encoder(recebimento),
            status_code=status_code,
        )
