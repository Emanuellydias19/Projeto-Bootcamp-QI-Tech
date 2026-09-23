# Projeto-Bootcamp-QI-Tech

Uma API financeira para administradoras de imóveis que automatiza o rateio e a gestão do dinheiro de cada proprietário. Cada pagamento é identificado, classificado e distribuído por regras, mantendo saldo, taxas, repasses e extratos rastreáveis.

> **Status: em construção.** O código em `src/` ainda é o do projeto base do Bootcamp, com a entidade de exemplo `sample_entity`. O domínio de rateio vai substituí-lo aos poucos, seguindo a mesma arquitetura.

**Sumário:** [Como rodar](#como-rodar) · [Problemas comuns](#problemas-comuns) · [Documentação](#documentação) · [Estrutura](#estrutura) · [Como contribuir](#como-contribuir) · [Licença](#licença)

---

## Como rodar

A API e o banco sobem no **Docker**. Os testes rodam no **Python** da sua máquina, contra a API que está no Docker.

### Pré-requisitos

| Programa | Para quê | Como conferir |
|---|---|---|
| **Docker Desktop** | roda a API e o banco | `docker compose version` |
| **Git** (no Windows, traz o **Git Bash**) | clonar o repositório e rodar os comandos | `git --version` |
| **Python 3.12** | rodar os testes | `py -3.12 --version` (Mac/Linux: `python3.12 --version`) |

> ⚠️ **Tem que ser o Python 3.12.** O `SQLAlchemy==2.0.23` fixado no projeto não funciona no Python 3.13: os testes quebram com `AssertionError ... TypingOnly`. Se você já tem o 3.13, instale o 3.12 junto; os dois convivem.

No Windows, rode os comandos no **Git Bash**. O `curl` e a ativação do `.venv` deste guia não funcionam do mesmo jeito no PowerShell.

### 1. Clonar

```bash
git clone https://github.com/Emanuellydias19/Projeto-Bootcamp-QI-Tech.git
cd Projeto-Bootcamp-QI-Tech
git switch develop
```

### 2. Configurar o `.env`

```bash
cp .env.example .env
```

**No Windows**, abra o `.env` e troque `SERVER_LOCALHOST=0.0.0.0` por `SERVER_LOCALHOST=localhost`. Sem essa troca, os testes não encontram a API, porque o Windows não aceita conexão para `0.0.0.0`.

O `.env` é só seu: ele está no `.gitignore` e nunca vai para o repositório.

### 3. Subir a API e o banco

Com o Docker Desktop aberto:

```bash
docker compose up --build
```

Espere aparecer `Application startup complete` e abra http://localhost:3000. Deve aparecer algo como `{"service":"bootcamp-api","id":"8"}`.

Esse terminal fica ocupado com a API. Para o resto, abra outro.

### 4. Rodar os testes

Na primeira vez:

```bash
py -3.12 -m venv .venv
source .venv/Scripts/activate
pip install -r requirements-dev.txt
```

No Mac/Linux, troque as duas primeiras linhas por `python3.12 -m venv .venv` e `source .venv/bin/activate`.

Depois, sempre com a API de pé e `(healthy)` em `docker compose ps`:

```bash
pytest
```

O resultado esperado é `35 passed`. Para rodar um arquivo só: `pytest -v tests/integration/test_healthcheck.py`.

> Alguns testes **apagam e recriam o banco**. O que você criou na mão some depois do `pytest`, e isso é esperado.

### 5. Desligar e resetar

| Quero… | Comando |
|---|---|
| Desligar | `Ctrl+C` no terminal da API e depois `docker compose down` |
| Ligar de novo | `docker compose up` |
| Recriar o banco do zero (necessário depois de mudar `database/database.sql`) | `docker compose down -v` e depois `docker compose up` |
| Ver o log da API | `docker compose logs -f api` |

## Problemas comuns

| A mensagem diz… | O que fazer |
|---|---|
| `failed to connect to the docker API` | Abra o Docker Desktop e espere ele ficar pronto. |
| `port is already allocated` | No `.env`, descomente `API_PORT=3001` e/ou `DB_PORT=5433`. Se mudou o `DB_PORT`, troque a porta também na `DATABASE_URL`. |
| `Não consegui falar com a API em http://0.0.0.0:3000` | Faltou a troca `SERVER_LOCALHOST=localhost` no `.env` (passo 2). |
| `AssertionError ... TypingOnly` | O `.venv` foi criado com o Python 3.13. Apague a pasta `.venv` e refaça com `py -3.12`. |
| `relation "..." does not exist` | O `database.sql` mudou e o banco é antigo. Rode `docker compose down -v` e `docker compose up`. |

## Documentação

| Documento | O que tem |
|---|---|
| [docs/como-o-projeto-e-organizado.md](docs/como-o-projeto-e-organizado.md) | A arquitetura: o caminho de uma requisição, o que cada pasta pode e não pode fazer e onde mexer para cada tipo de mudança. |
| [docs/guia-da-api-base.md](docs/guia-da-api-base.md) | O guia original do projeto base: todas as rotas com exemplos de `curl`, o catálogo de códigos de erro (`QIT…`) e o que fazer quando dá errado. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Como o time trabalha: branches, commits e pull requests. |

## Estrutura

```
src/
  app.py          ← registra as rotas, os middlewares e o tratamento de erro
  resources/      ← recebe a requisição HTTP e devolve a resposta
  schemas/        ← o formato do que ENTRA (JSON Schema)
  controllers/    ← as regras de negócio e o commit
  repositories/   ← as consultas ao banco
  models/         ← as tabelas, descritas em Python
  dtos/           ← o formato do que SAI
  errors/         ← os erros da API, cada um com seu código
  middlewares/    ← o que acontece em toda requisição
  connectors/     ← chamadas a outros serviços
database/
  database.sql    ← as tabelas, em SQL (rodam quando o banco nasce)
tests/            ← testes de integração, que chamam a API por HTTP
```

A regra que organiza tudo: `resources → controllers → repositories → models`, sempre nesse sentido. Os detalhes estão em [docs/como-o-projeto-e-organizado.md](docs/como-o-projeto-e-organizado.md).

## Como contribuir

Resumo: crie uma branch a partir de `develop`, faça commits no padrão `tipo: descrição` e abra um pull request para `develop`. O passo a passo completo está no [CONTRIBUTING.md](CONTRIBUTING.md).

## Licença

Este projeto é distribuído sob a licença **Apache 2.0**. Veja o arquivo [LICENSE](LICENSE).

Ele foi construído a partir do projeto base do Bootcamp (`bootcamp-base-api`), © 2026 QI Tech, distribuído sob a licença **MIT**. O aviso original está preservado em [LICENSE-bootcamp-base](LICENSE-bootcamp-base), como a licença MIT exige.
