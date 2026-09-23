# Projeto-Bootcamp-QI-Tech

Uma API financeira para administradoras de imóveis que automatiza o rateio e a gestão do dinheiro de cada proprietário. Cada pagamento é identificado, classificado e distribuído por regras, mantendo saldo, taxas, repasses e extratos rastreáveis.

> 🚧 **Em construção.** A base técnica está pronta: API, banco, Docker, testes, autenticação e erros padronizados. As funcionalidades de rateio estão sendo modeladas e ainda não foram implementadas. O código em `src/` hoje traz a entidade de exemplo do projeto base (`sample_entity`), que será substituída aos poucos.

**Sumário:** [Como funciona](#como-funciona) · [Funcionalidades](#funcionalidades) · [Tecnologias](#tecnologias) · [Começando](#começando) · [Documentação](#documentação) · [Estrutura](#estrutura) · [Como contribuir](#como-contribuir) · [Licença](#licença)

---

## Como funciona

O caminho de cada pagamento, do momento em que entra até virar extrato:

```
pagamento recebido
      ↓
identificado      → de qual imóvel e de qual contrato ele é
      ↓
classificado      → que tipo de pagamento ele é
      ↓
rateado           → dividido entre os proprietários, pelas regras cadastradas
      ↓
saldo e taxas     → o saldo de cada proprietário é atualizado e as taxas são descontadas
      ↓
repasse           → o dinheiro é enviado a cada proprietário
      ↓
extrato           → tudo fica registrado e rastreável
```

## Funcionalidades

| Funcionalidade | Status |
|---|---|
| Identificação do pagamento | 📝 planejada |
| Classificação do pagamento | 📝 planejada |
| Rateio entre proprietários, por regras | 📝 planejada |
| Saldo por proprietário | 📝 planejada |
| Cálculo e desconto de taxas | 📝 planejada |
| Repasses | 📝 planejada |
| Extrato rastreável | 📝 planejada |
| Base técnica (API, banco, Docker, testes, token, erros padronizados) | ✅ pronta |

## Tecnologias

| Camada | Ferramenta | Versão |
|---|---|---|
| Linguagem | Python | 3.11 (na imagem Docker) |
| API | FastAPI + Uvicorn | 0.141.1 / 0.52.3 |
| Validação da entrada | jsonschema | 4.17.3 |
| Banco de dados | PostgreSQL | 16 |
| Acesso ao banco | SQLAlchemy + psycopg2 | 2.0.23 / 2.9.10 |
| Chamadas a outros serviços | requests | 2.32.3 |
| Ambiente | Docker + Docker Compose | — |
| Testes | pytest | 7.4.4 |

## Começando

Você precisa de **Docker Desktop**, **Git** e **Python 3.12**. Com eles instalados:

```bash
git clone https://github.com/Emanuellydias19/Projeto-Bootcamp-QI-Tech.git
cd Projeto-Bootcamp-QI-Tech
cp .env.example .env
docker compose up --build
```

Abra http://localhost:3000: se aparecer `{"service":"bootcamp-api",...}`, está funcionando.

O passo a passo completo está em **[docs/como-rodar.md](docs/como-rodar.md)**, com os testes, as particularidades do Windows e as soluções para os erros mais comuns.

## Documentação

| Documento | O que tem |
|---|---|
| [docs/como-rodar.md](docs/como-rodar.md) | Instalação, execução, testes e problemas comuns. |
| [docs/como-o-projeto-e-organizado.md](docs/como-o-projeto-e-organizado.md) | A arquitetura: o caminho de uma requisição, o que cada pasta pode e não pode fazer e onde mexer para cada tipo de mudança. |
| [docs/guia-da-api-base.md](docs/guia-da-api-base.md) | O guia original do projeto base: as rotas atuais com exemplos de `curl` e o catálogo de códigos de erro (`QIT…`). |
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
docs/             ← a documentação do projeto
```

Toda requisição segue o mesmo caminho, sempre nesse sentido: `resources → controllers → repositories → models`.

## Como contribuir

Crie uma branch a partir de `develop`, faça commits no padrão `tipo: descrição` e abra um pull request para `develop`. O passo a passo completo está no [CONTRIBUTING.md](CONTRIBUTING.md).

## Licença

Este projeto é distribuído sob a licença **Apache 2.0** (veja [LICENSE](LICENSE)).

Ele foi construído a partir do projeto base do Bootcamp (`bootcamp-base-api`), © 2026 QI Tech, distribuído sob a licença **MIT**. O aviso original está preservado em [LICENSE-bootcamp-base](LICENSE-bootcamp-base), como a licença MIT exige.
