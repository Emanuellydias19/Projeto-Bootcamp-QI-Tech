from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import CobrancaController
from utils.schema_handler import SchemaHandler


class CobrancaResource:
    @SchemaHandler.validate("post_conta_cobranca.json")
    def on_post(self, conta_chave: str, payload: dict) -> JSONResponse:
        controller = CobrancaController()
        cobranca = controller.create(conta_chave, payload)

        return JSONResponse(
            content=jsonable_encoder(cobranca),
            status_code=http_status.HTTP_201_CREATED,
        )

    @SchemaHandler.validate("post_cobranca_item.json")
    def on_post_item(self, cobranca_chave: str, payload: dict) -> JSONResponse:
        controller = CobrancaController()
        cobranca = controller.add_item(cobranca_chave, payload)

        return JSONResponse(
            content=jsonable_encoder(cobranca),
            status_code=http_status.HTTP_201_CREATED,
        )

    @SchemaHandler.validate_query_params("get_cobranca.json")
    def on_get_by_chave(self, cobranca_chave: str, request: Request) -> JSONResponse:
        controller = CobrancaController()
        cobranca = controller.get_by_chave(cobranca_chave, request.query_params.get("data"))

        return JSONResponse(
            content=jsonable_encoder(cobranca),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate_query_params("get_conta_devido.json")
    def on_get_devido(self, conta_chave: str, request: Request) -> JSONResponse:
        controller = CobrancaController()
        devido = controller.get_devido_da_conta(conta_chave, request.query_params.get("data"))

        return JSONResponse(
            content=jsonable_encoder(devido),
            status_code=http_status.HTTP_200_OK,
        )
