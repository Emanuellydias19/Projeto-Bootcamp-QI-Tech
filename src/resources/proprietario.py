from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ProprietarioController
from utils.schema_handler import SchemaHandler


class ProprietarioResource:
    @SchemaHandler.validate("post_proprietario.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = ProprietarioController()
        proprietario = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(proprietario),
            status_code=http_status.HTTP_201_CREATED,
        )
