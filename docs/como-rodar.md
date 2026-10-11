# Como rodar o projeto

A API e o banco sobem no **Docker**. Os testes rodam no **Python** da sua máquina, contra a API que está no Docker.

**Sumário:** [Pré-requisitos](#pré-requisitos) · [1. Clonar](#1-clonar) · [2. Configurar o .env](#2-configurar-o-env) · [3. Subir](#3-subir-a-api-e-o-banco) · [4. Testes](#4-rodar-os-testes) · [5. Desligar e resetar](#5-desligar-e-resetar) · [6. Passeio pelas rotas](#6-um-passeio-pelas-rotas-da-orca) · [Problemas comuns](#problemas-comuns)

---

## Pré-requisitos

| Programa | Para quê | Como conferir |
| --- | --- | --- |
| **Docker Desktop** | roda a API e o banco | `docker compose version` |
| **Git** (no Windows, traz o **Git Bash**) | clonar o repositório e rodar os comandos | `git --version` |
| **Python 3.12 ou mais novo** | rodar os testes | `py --version` (Mac/Linux: `python3 --version`) |

> A suíte foi conferida no Python 3.12 e no 3.13. A API não depende do Python da sua máquina: ela roda dentro do Docker, com o Python 3.11 da imagem.

No Windows, rode os comandos no **Git Bash**. O `curl` e a ativação do `.venv` deste guia não funcionam do mesmo jeito no PowerShell.

## 1. Clonar

```bash
git clone https://github.com/Emanuellydias19/Projeto-Bootcamp-QI-Tech.git
cd Projeto-Bootcamp-QI-Tech
git switch develop
```

## 2. Configurar o `.env`

```bash
cp .env.example .env
```

**No Windows**, abra o `.env` e troque `SERVER_LOCALHOST=0.0.0.0` por `SERVER_LOCALHOST=localhost`. Sem essa troca, os testes não encontram a API, porque o Windows não aceita conexão para `0.0.0.0`.

O `.env` é só seu: ele está no `.gitignore` e nunca vai para o repositório.

## 3. Subir a API e o banco

Com o Docker Desktop aberto:

```bash
docker compose up --build
```

Espere aparecer `Application startup complete` e abra <http://localhost:3000>. Deve aparecer algo como `{"service":"bootcamp-api","id":"8"}`.

Esse terminal fica ocupado com a API. Para o resto, abra outro.

## 4. Rodar os testes

Na primeira vez:

```bash
py -m venv .venv
source .venv/Scripts/activate
pip install -r requirements-dev.txt
```

No Mac/Linux, troque as duas primeiras linhas por `python3 -m venv .venv` e `source .venv/bin/activate`.

Depois, sempre com a API de pé e `(healthy)` em `docker compose ps`:

```bash
pytest
```

O resultado esperado é `303 passed`, em 1 a 4 minutos, conforme a máquina. Para rodar um arquivo só: `pytest -v tests/integration/test_healthcheck.py`.

Para conferir o estilo do código com as regras do `.flake8`, rode `python -m flake8 .`. O resultado esperado é nenhuma linha de saída.

> Alguns testes **apagam e recriam o banco**. O que você criou na mão some depois do `pytest`, e isso é esperado.

## 5. Desligar e resetar

| Quero… | Comando |
| --- | --- |
| Desligar | `Ctrl+C` no terminal da API e depois `docker compose down` |
| Ligar de novo | `docker compose up` |
| Recriar o banco do zero (necessário depois de mudar `database/database.sql`) | `docker compose down -v` e depois `docker compose up --build`. O `--build` é obrigatório: o `database.sql` é copiado para dentro da imagem do banco, e sem ele o banco nasce com o arquivo antigo |
| Ver o log da API | `docker compose logs -f api`. Cada linha é um JSON; para seguir uma requisição, filtre pelo `X-Request-ID` que ela devolveu: `docker compose logs api \| grep <X-Request-ID>` |

## 6. Um passeio pelas rotas da ORCA

Com a API de pé, este passeio conta um mês na conta de um proprietário: cadastro, conta, cobrança, recebimento, pagamento do condomínio, repasse com a taxa, extrato e estorno. Os números são os dos exemplos do [documento de decisões](rfc/RFC.md#72-para-cada-rota).

Cada resposta traz uma chave (UUID). Guarde as chaves nas variáveis indicadas para usar nos passos seguintes. O token é o `INTERNAL_TOKEN` do seu `.env` (no exemplo, `default_token`).

```bash
API=http://localhost:3000
TOKEN=default_token
```

1. Cadastre o proprietário. O documento pode ser CPF ou CNPJ, inclusive o alfanumérico; se ele já estiver cadastrado, a resposta é `409`, e basta usar outro documento válido.

   ```bash
   curl -s -X POST $API/proprietarios -H "INTERNAL-TOKEN: $TOKEN" -H "Content-Type: application/json" \
     -d '{"documento": "12.ABC.345/01DE-35", "nome": "Maria da Silva"}'
   ```

   Guarde a `proprietario_chave` em `PROPRIETARIO=...`.

2. Abra a conta do imóvel, com a política de imputação padrão, taxa de 10%, multa de 2% e juros de 1% ao mês. Guarde a `conta_chave` em `CONTA=...`.

   ```bash
   curl -s -X POST $API/contas -H "INTERNAL-TOKEN: $TOKEN" -H "Content-Type: application/json" \
     -d "{\"proprietario_chave\": \"$PROPRIETARIO\", \"imovel_referencia\": \"Rua das Flores, 120, apto 34\", \"politica_imputacao_chave\": \"7d2e9b41-3c5a-4f8e-a1b6-9c0d2e4f6a18\", \"taxa_administracao_bps\": 1000, \"multa_bps\": 200, \"juros_mensal_bps\": 100}"
   ```

3. Lance a cobrança de setembro: aluguel de R$ 1.500,00, condomínio de R$ 350,00 e IPTU de R$ 150,00. Guarde a `cobranca_chave` em `COBRANCA=...`.

   ```bash
   curl -s -X POST $API/contas/$CONTA/cobrancas -H "INTERNAL-TOKEN: $TOKEN" -H "Content-Type: application/json" \
     -d '{"competencia": "2026-09", "vencimento": "2026-09-05", "itens": [{"natureza": "aluguel", "valor_centavos": 150000}, {"natureza": "condominio", "valor_centavos": 35000}, {"natureza": "iptu", "valor_centavos": 15000}]}'
   ```

4. Registre o pagamento de R$ 1.800,00 do inquilino. A resposta mostra o rateio pela política: condomínio, IPTU e R$ 1.300,00 de aluguel, com R$ 200,00 ainda em aberto.

   ```bash
   curl -s -X POST $API/cobrancas/$COBRANCA/recebimentos -H "INTERNAL-TOKEN: $TOKEN" -H "Content-Type: application/json" \
     -H "Idempotency-Key: passeio-recebimento" -d '{"valor_centavos": 180000, "pago_em": "2026-09-05"}'
   ```

5. Consulte a posição da cobrança: `parcial`, com o total devido na data.

   ```bash
   curl -s "$API/cobrancas/$COBRANCA?data=2026-09-05" -H "INTERNAL-TOKEN: $TOKEN"
   ```

6. Pague o condomínio com o dinheiro reservado para ele.

   ```bash
   curl -s -X POST $API/contas/$CONTA/encargos/pagamentos -H "INTERNAL-TOKEN: $TOKEN" -H "Content-Type: application/json" \
     -H "Idempotency-Key: passeio-condominio" -d '{"natureza": "condominio", "valor_centavos": 35000}'
   ```

7. Repasse todo o disponível ao proprietário. A taxa é retida sobre o aluguel quitado: R$ 130,00 de taxa e R$ 1.170,00 de líquido. Guarde a `transacao_chave` em `REPASSE=...`. Repetir o mesmo comando, com a mesma `Idempotency-Key`, devolve `200` com a mesma resposta e não repassa de novo.

   ```bash
   curl -s -X POST $API/contas/$CONTA/repasses -H "INTERNAL-TOKEN: $TOKEN" -H "Content-Type: application/json" \
     -H "Idempotency-Key: passeio-repasse" -d '{"valor_centavos": 130000}'
   ```

8. Confira o saldo (disponível 0 e reservado R$ 150,00, o IPTU) e o extrato, do lançamento mais recente para o mais antigo.

   ```bash
   curl -s $API/contas/$CONTA/saldo -H "INTERNAL-TOKEN: $TOKEN"
   curl -s "$API/contas/$CONTA/extrato?limite=2" -H "INTERNAL-TOKEN: $TOKEN"
   ```

9. Tente repassar R$ 0,01 a mais: a API recusa com `409` e o código `QIT001020`, porque não há disponível.

   ```bash
   curl -s -X POST $API/contas/$CONTA/repasses -H "INTERNAL-TOKEN: $TOKEN" -H "Content-Type: application/json" \
     -H "Idempotency-Key: passeio-repasse-extra" -d '{"valor_centavos": 1}'
   ```

10. Estorne o repasse: a API cria lançamentos de sinal invertido, e o disponível volta a R$ 1.300,00.

    ```bash
    curl -s -X POST $API/transacoes/$REPASSE/estornos -H "INTERNAL-TOKEN: $TOKEN" -H "Idempotency-Key: passeio-estorno"
    ```

## Problemas comuns

| A mensagem diz… | O que fazer |
| --- | --- |
| `failed to connect to the docker API` | Abra o Docker Desktop e espere ele ficar pronto. |
| `port is already allocated` | No `.env`, descomente `API_PORT=3001` e/ou `DB_PORT=5433`. Se mudou o `DB_PORT`, troque a porta também na `DATABASE_URL`. |
| `Não consegui falar com a API em http://0.0.0.0:3000` | Faltou a troca `SERVER_LOCALHOST=localhost` no `.env` (passo 2). |
| `AssertionError ... TypingOnly` | O `.venv` tem uma versão antiga do SQLAlchemy. Com o `.venv` ativo, rode `pip install -r requirements-dev.txt` de novo. |
| `relation "..." does not exist` | O `database.sql` mudou e o banco é antigo. Rode `docker compose down -v` e `docker compose up --build`. |
| `No module named 'prometheus_client'` no log da API | A imagem da API é anterior à dependência nova. Rode `docker compose up --build`. |

O contrato completo de cada rota, com os códigos de erro, está no [documento de decisões](rfc/RFC.md#7-contrato-da-api). Logs, métricas, saúde e os limites de produção estão em [producao.md](producao.md). O [guia da API base](guia-da-api-base.md) mostra as rotas de exemplo do projeto base (`sample_entity`), que continuam no código como referência.
