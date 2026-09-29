from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import TransacaoController
from utils.idempotency import read_idempotency_key
from utils.schema_handler import SchemaHandler


class TransacaoResource:
    @SchemaHandler.validate("post_cobranca_recebimento.json")
    @SchemaHandler.validate_idempotency_key
    def on_post_recebimento(self, cobranca_chave: str, payload: dict, request: Request) -> JSONResponse:
        controller = TransacaoController()
        recebimento, created = controller.receber(
            cobranca_chave, payload, read_idempotency_key(request.headers)
        )

        return self._response(recebimento, created)

    @SchemaHandler.validate("post_conta_encargo_pagamento.json")
    @SchemaHandler.validate_idempotency_key
    def on_post_encargo_pagamento(self, conta_chave: str, payload: dict, request: Request) -> JSONResponse:
        controller = TransacaoController()
        encargo, created = controller.pagar_encargo(conta_chave, payload, read_idempotency_key(request.headers))

        return self._response(encargo, created)

    @SchemaHandler.validate("post_conta_repasse.json")
    @SchemaHandler.validate_idempotency_key
    def on_post_repasse(self, conta_chave: str, payload: dict, request: Request) -> JSONResponse:
        controller = TransacaoController()
        repasse, created = controller.repassar(conta_chave, payload, read_idempotency_key(request.headers))

        return self._response(repasse, created)

    @SchemaHandler.validate_idempotency_key
    def on_post_estorno(self, transacao_chave: str, request: Request) -> JSONResponse:
        controller = TransacaoController()
        estorno, created = controller.estornar(transacao_chave, read_idempotency_key(request.headers))

        return self._response(estorno, created)

    def _response(self, resultado: dict, created: bool) -> JSONResponse:
        if created:
            status_code = http_status.HTTP_201_CREATED
        else:
            status_code = http_status.HTTP_200_OK

        return JSONResponse(
            content=jsonable_encoder(resultado),
            status_code=status_code,
        )
