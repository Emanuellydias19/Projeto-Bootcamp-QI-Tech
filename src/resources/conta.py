from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ContaController
from utils.schema_handler import SchemaHandler

DEFAULT_LIMITE = 10


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

    @SchemaHandler.validate_query_params("get_conta_extrato.json")
    def on_get_extrato(self, conta_chave: str, request: Request) -> JSONResponse:
        controller = ContaController()
        query_params = request.query_params
        extrato = controller.get_extrato(
            conta_chave,
            query_params.get("cursor"),
            int(query_params.get("limite", DEFAULT_LIMITE)),
            query_params.get("natureza"),
        )

        return JSONResponse(
            content=jsonable_encoder(extrato),
            status_code=http_status.HTTP_200_OK,
        )
