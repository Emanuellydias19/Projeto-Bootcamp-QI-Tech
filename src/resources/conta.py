from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ContaController
from utils.schema_handler import SchemaHandler


class ContaResource:
    @SchemaHandler.validate("post_conta.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = ContaController()
        conta = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(conta),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_saldo(self, conta_chave: str) -> JSONResponse:
        controller = ContaController()
        saldo = controller.get_saldo(conta_chave)

        return JSONResponse(
            content=jsonable_encoder(saldo),
            status_code=http_status.HTTP_200_OK,
        )
