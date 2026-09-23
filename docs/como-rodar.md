# Como rodar o projeto

A API e o banco sobem no **Docker**. Os testes rodam no **Python** da sua máquina, contra a API que está no Docker.

**Sumário:** [Pré-requisitos](#pré-requisitos) · [1. Clonar](#1-clonar) · [2. Configurar o .env](#2-configurar-o-env) · [3. Subir](#3-subir-a-api-e-o-banco) · [4. Testes](#4-rodar-os-testes) · [5. Desligar e resetar](#5-desligar-e-resetar) · [Problemas comuns](#problemas-comuns)

---

## Pré-requisitos

| Programa | Para quê | Como conferir |
| --- | --- | --- |
| **Docker Desktop** | roda a API e o banco | `docker compose version` |
| **Git** (no Windows, traz o **Git Bash**) | clonar o repositório e rodar os comandos | `git --version` |
| **Python 3.12** | rodar os testes | `py -3.12 --version` (Mac/Linux: `python3.12 --version`) |

> **Atenção: tem que ser o Python 3.12.** O `SQLAlchemy==2.0.23` fixado no projeto não funciona no Python 3.13: os testes quebram com `AssertionError ... TypingOnly`. Se você já tem o 3.13, instale o 3.12 junto; os dois convivem.

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

## 5. Desligar e resetar

| Quero… | Comando |
| --- | --- |
| Desligar | `Ctrl+C` no terminal da API e depois `docker compose down` |
| Ligar de novo | `docker compose up` |
| Recriar o banco do zero (necessário depois de mudar `database/database.sql`) | `docker compose down -v` e depois `docker compose up` |
| Ver o log da API | `docker compose logs -f api` |

## Problemas comuns

| A mensagem diz… | O que fazer |
| --- | --- |
| `failed to connect to the docker API` | Abra o Docker Desktop e espere ele ficar pronto. |
| `port is already allocated` | No `.env`, descomente `API_PORT=3001` e/ou `DB_PORT=5433`. Se mudou o `DB_PORT`, troque a porta também na `DATABASE_URL`. |
| `Não consegui falar com a API em http://0.0.0.0:3000` | Faltou a troca `SERVER_LOCALHOST=localhost` no `.env` (passo 2). |
| `AssertionError ... TypingOnly` | O `.venv` foi criado com o Python 3.13. Apague a pasta `.venv` e refaça com `py -3.12`. |
| `relation "..." does not exist` | O `database.sql` mudou e o banco é antigo. Rode `docker compose down -v` e `docker compose up`. |

Para ver as rotas que a API já tem, com exemplos de `curl`, abra o [guia da API base](guia-da-api-base.md).
