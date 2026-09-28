from errors import QIException


class NotFoundSampleEntity(QIException):
    code = "QIT001001"

    def __init__(self, sample_entity_key) -> None:
        title = "Entity not Found"
        http_status = 404
        description = f"Entity with key {sample_entity_key} was not found."
        translation = f"A entidade com chave {sample_entity_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class SampleEntityFinalStatus(QIException):
    code = "QIT001002"

    def __init__(self, old_status, new_status) -> None:
        title = "Entity cannot change status"
        http_status = 409
        description = f"Entity with status {old_status} cannot update to {new_status}."
        translation = "Essa entidade não pode ser atualizada."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentNumber(QIException):
    """O CPF tem o formato certo e não existe.

    422, e não 400, de propósito: 400 quer dizer "não consegui ler o seu
    pedido". Aqui a API leu, entendeu, e o valor é que não pode existir —
    os dois últimos dígitos não batem com a conta. A diferença está
    explicada em src/utils/document_number.py.
    """

    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    """Já existe um cadastro com este CPF.

    409 Conflict: o pedido está correto em si, e o que impede é o que já
    está no banco. É a mesma família do SampleEntityFinalStatus aqui em
    cima — conflito com o que já existe, não erro de quem pediu.
    """

    code = "QIT001004"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already an entity with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT001005"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already an entity with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageSampleEntity(QIException):
    code = "QIT001006"

    def __init__(self, age, minimum_age) -> None:
        title = "Entity is underage"
        http_status = 422
        description = f"The entity is {age} years old, and the minimum is {minimum_age}."
        translation = f"É preciso ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBirthdate(QIException):
    """A data tem o formato certo e não existe no calendário.

    Existe porque o `pattern` do schema sabe contar dígitos, não dias:
    "2025-02-30" e "9999-99-99" passam pelo regex e morrem no
    `date.fromisoformat`. Sem esta classe, esse ValueError virava 500 —
    a API culpando a si mesma por um erro de quem chamou.
    """

    code = "QIT001007"

    def __init__(self, birthdate) -> None:
        title = "Invalid Birthdate"
        http_status = 422
        description = f"The birthdate {birthdate} is not a real date."
        translation = "A data de nascimento informada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumento(QIException):
    code = "QIT001008"

    def __init__(self) -> None:
        title = "Invalid document"
        http_status = 422
        description = "The document check digits do not match a valid CPF or CNPJ."
        translation = "O documento informado não é um CPF ou CNPJ válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumento(QIException):
    code = "QIT001009"

    def __init__(self) -> None:
        title = "Document already registered"
        http_status = 409
        description = "There is already an owner registered with this document."
        translation = "Já existe um proprietário cadastrado com este documento."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundProprietario(QIException):
    code = "QIT001010"

    def __init__(self, proprietario_chave) -> None:
        title = "Owner not found"
        http_status = 404
        description = f"Owner with key {proprietario_chave} was not found."
        translation = "O proprietário informado não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundConta(QIException):
    code = "QIT001011"

    def __init__(self, conta_chave) -> None:
        title = "Account not found"
        http_status = 404
        description = f"Account with key {conta_chave} was not found."
        translation = "A conta informada não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedConta(QIException):
    code = "QIT001012"

    def __init__(self) -> None:
        title = "Account already opened"
        http_status = 409
        description = "There is already an account for this owner and property."
        translation = "Já existe uma conta para este proprietário e imóvel."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBps(QIException):
    code = "QIT001013"

    def __init__(self, field, minimum_bps, maximum_bps) -> None:
        title = "Invalid basis points"
        http_status = 422
        description = f"The field {field} must be between {minimum_bps} and {maximum_bps} basis points."
        translation = f"Taxa, multa e juros precisam estar entre {minimum_bps} e {maximum_bps} pontos-base."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundPoliticaImputacao(QIException):
    code = "QIT001014"

    def __init__(self, politica_imputacao_chave) -> None:
        title = "Allocation policy not found"
        http_status = 404
        description = f"Allocation policy with key {politica_imputacao_chave} was not found."
        translation = "A política de imputação informada não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundCobranca(QIException):
    code = "QIT001015"

    def __init__(self, cobranca_chave) -> None:
        title = "Charge not found"
        http_status = 404
        description = f"Charge with key {cobranca_chave} was not found."
        translation = "A cobrança informada não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedCobranca(QIException):
    code = "QIT001016"

    def __init__(self) -> None:
        title = "Charge already registered"
        http_status = 409
        description = "There is already a charge for this account and reference month."
        translation = "Já existe uma cobrança para esta conta e competência."
        super().__init__(title, self.code, http_status, description, translation)


class CobrancaQuitada(QIException):
    code = "QIT001017"

    def __init__(self, cobranca_chave) -> None:
        title = "Charge already settled"
        http_status = 409
        description = f"The charge {cobranca_chave} is already settled and does not accept new items."
        translation = "A cobrança já está quitada e não aceita novos itens; lance o item na competência seguinte."
        super().__init__(title, self.code, http_status, description, translation)


class ValorAboveDevido(QIException):
    code = "QIT001019"

    def __init__(self, valor_centavos, total_devido_centavos) -> None:
        title = "Amount above what is owed"
        http_status = 422
        description = f"The amount {valor_centavos} is above the {total_devido_centavos} owed on the payment date."
        translation = "O valor recebido é maior que o devido na data do pagamento."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientSaldoDisponivel(QIException):
    code = "QIT001020"

    def __init__(self, valor_centavos, saldo_disponivel_centavos) -> None:
        title = "Insufficient available balance"
        http_status = 409
        description = f"The amount {valor_centavos} is above the {saldo_disponivel_centavos} available in the account."
        translation = "O saldo disponível da conta não cobre o valor pedido."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientSaldoReservado(QIException):
    code = "QIT001021"

    def __init__(self, natureza, valor_centavos, reservado_centavos) -> None:
        title = "Insufficient reserved balance"
        http_status = 409
        description = f"The amount {valor_centavos} is above the {reservado_centavos} reserved for {natureza}."
        translation = "O saldo reservado dessa natureza não cobre o valor pedido."
        super().__init__(title, self.code, http_status, description, translation)


class ReusedIdempotencyKey(QIException):
    code = "QIT001022"

    def __init__(self) -> None:
        title = "Idempotency key already used"
        http_status = 409
        description = "The Idempotency-Key was already used with another request."
        translation = "A chave de idempotência já foi usada em outra requisição."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidPagoEm(QIException):
    code = "QIT001027"

    def __init__(self, field, text) -> None:
        title = "Payment date out of order"
        http_status = 422
        description = f"The {field} {text} is in the future or before the last payment of the charge."
        translation = "A data está no futuro ou é anterior a um recebimento já registrado na cobrança."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidValor(QIException):
    code = "QIT001018"

    def __init__(self, valor_centavos) -> None:
        title = "Invalid amount"
        http_status = 422
        description = f"The amount {valor_centavos} must be greater than zero."
        translation = "O valor precisa ser maior que zero."
        super().__init__(title, self.code, http_status, description, translation)


class ValorNotAboveTaxa(QIException):
    code = "QIT001026"

    def __init__(self, valor_centavos, taxa_centavos) -> None:
        title = "Amount not above the fee"
        http_status = 422
        description = f"The gross amount {valor_centavos} must be above the pending fee of {taxa_centavos}."
        translation = "O valor bruto do repasse precisa ser maior que a taxa de administração pendente."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDate(QIException):
    code = "QIT001025"

    def __init__(self, field, text) -> None:
        title = "Invalid date"
        http_status = 422
        description = f"The {field} {text} does not exist in the calendar."
        translation = "A data informada não existe no calendário."
        super().__init__(title, self.code, http_status, description, translation)
