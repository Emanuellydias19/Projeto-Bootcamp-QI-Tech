CREATE TABLE sample_entity_status(
    id		                        SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO sample_entity_status (enumerator) VALUES
('created'),
('pending'),
('success'),
('failed');

CREATE TABLE sample_entity(
    id                              SERIAL PRIMARY KEY,
    sample_entity_key               CHAR(36) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    sample_entity_data              JSONB NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    birthdate                       DATE NOT NULL,
    counter                         INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(sample_entity_key),
    UNIQUE(document_number),
    UNIQUE(email)
);

CREATE TABLE sample_entity_status_event(
    id                              SERIAL PRIMARY KEY,
    sample_entity_id                INTEGER NOT NULL REFERENCES sample_entity(id),
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE proprietario(
    id                              BIGSERIAL PRIMARY KEY,
    chave                           CHAR(36) NOT NULL,
    documento                       VARCHAR(18) NOT NULL,
    nome                            TEXT NOT NULL,
    criado_em                       TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    CONSTRAINT uq_proprietario_chave UNIQUE(chave),
    CONSTRAINT uq_proprietario_documento UNIQUE(documento)
);

CREATE TABLE politica_imputacao(
    id                              BIGSERIAL PRIMARY KEY,
    chave                           CHAR(36) NOT NULL,
    nome                            TEXT NOT NULL,
    versao                          INTEGER NOT NULL,
    ordem_naturezas                 JSONB NOT NULL,
    vigente_desde                   TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    CONSTRAINT uq_politica_imputacao_chave UNIQUE(chave),
    CONSTRAINT uq_politica_imputacao_nome_versao UNIQUE(nome, versao)
);

INSERT INTO politica_imputacao (chave, nome, versao, ordem_naturezas) VALUES
('7d2e9b41-3c5a-4f8e-a1b6-9c0d2e4f6a18', 'Politica padrao', 1, '["juros", "multa", "condominio", "iptu", "aluguel", "despesa_extra"]');

CREATE TABLE conta(
    id                              BIGSERIAL PRIMARY KEY,
    chave                           CHAR(36) NOT NULL,
    proprietario_id                 BIGINT NOT NULL,
    imovel_referencia               TEXT NOT NULL,
    saldo_disponivel                BIGINT NOT NULL DEFAULT(0),
    saldo_reservado                 BIGINT NOT NULL DEFAULT(0),
    taxa_administracao_bps          INTEGER NOT NULL,
    multa_bps                       INTEGER NOT NULL,
    juros_mensal_bps                INTEGER NOT NULL,
    politica_id                     BIGINT NOT NULL,
    criado_em                       TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    CONSTRAINT fk_conta_proprietario FOREIGN KEY (proprietario_id) REFERENCES proprietario(id),
    CONSTRAINT fk_conta_politica_imputacao FOREIGN KEY (politica_id) REFERENCES politica_imputacao(id),
    CONSTRAINT uq_conta_chave UNIQUE(chave),
    CONSTRAINT uq_conta_proprietario_imovel UNIQUE(proprietario_id, imovel_referencia),
    CONSTRAINT ck_conta_saldo_disponivel CHECK (saldo_disponivel >= 0),
    CONSTRAINT ck_conta_saldo_reservado CHECK (saldo_reservado >= 0),
    CONSTRAINT ck_conta_taxa_administracao_bps CHECK (taxa_administracao_bps BETWEEN 0 AND 10000),
    CONSTRAINT ck_conta_multa_bps CHECK (multa_bps BETWEEN 0 AND 10000),
    CONSTRAINT ck_conta_juros_mensal_bps CHECK (juros_mensal_bps BETWEEN 0 AND 10000)
);