# Projeto-Bootcamp-QI-Tech

> **Uma infraestrutura financeira que transforma o dinheiro administrado para cada proprietário em uma posição financeira individual, rastreável e governada por regras.**

Uma API de gestão financeira para administradoras de imóveis, que funciona como uma **conta corrente interna de cada proprietário**.

> 🚧 **Em construção.** A base técnica está pronta: API, banco, Docker, testes, autenticação e erros padronizados. As funcionalidades financeiras estão sendo modeladas e ainda não foram implementadas. O código em `src/` hoje traz a entidade de exemplo do projeto base (`sample_entity`), que será substituída aos poucos.

**Sumário:** [A dor](#a-dor) · [A solução](#a-solução) · [Como funciona](#como-funciona) · [Funcionalidades](#funcionalidades) · [Benefícios](#benefícios) · [Tecnologias](#tecnologias) · [Começando](#começando) · [Documentação](#documentação) · [Estrutura](#estrutura) · [Como contribuir](#como-contribuir) · [Licença](#licença)

---

## A dor

Administradoras de imóveis movimentam dinheiro que **pertence aos proprietários**. Elas precisam dividir corretamente cada pagamento entre aluguel, condomínio, IPTU, multas, juros, taxas e repasses.

### O problema

Quando o pagamento vem diferente do previsto, o rateio deixa de ser automático e a decisão passa para **planilhas e processos manuais**. Isso aumenta o risco de:

- erro no saldo do proprietário;
- repasse incorreto;
- extratos sem discriminação adequada.

## A solução

Uma API que dá a cada proprietário uma **conta individual**, onde cada crédito e cada débito fica registrado. Em vez de decidir manualmente *"para onde foi esse dinheiro?"*, a administradora trabalha com **regras definidas previamente**.

Assim, cada real movimentado fica vinculado a uma **origem**, uma **natureza** e um **destino**. Isso reduz a dependência de planilhas e de decisões manuais.

## Como funciona

O caminho de cada pagamento:

```
pagamento → identificação → imputação → atualização do saldo → taxa → repasse → extrato
```

| Etapa | O que acontece |
|---|---|
| **Identificação** | A natureza de cada lançamento é identificada. |
| **Imputação** | As regras definem a que cada parte do pagamento se destina: aluguel, condomínio, IPTU, multas, juros… |
| **Atualização do saldo** | O crédito ou débito é registrado na conta do proprietário, separando o saldo disponível do provisionado. |
| **Taxa** | A taxa da administradora é calculada e registrada. |
| **Repasse** | O dinheiro vai para o proprietário, e nunca acima do saldo disponível. |
| **Extrato** | Tudo aparece num extrato financeiro discriminado e paginado. |

## Funcionalidades

| Funcionalidade | Status |
|---|---|
| Conta individual para cada proprietário | 📝 planejada |
| Registro de todos os créditos e débitos | 📝 planejada |
| Identificação da natureza de cada lançamento | 📝 planejada |
| Regras para distribuir pagamentos | 📝 planejada |
| Controle de saldo disponível e provisionado | 📝 planejada |
| Cálculo e registro da taxa da administradora | 📝 planejada |
| Bloqueio de repasses acima do saldo disponível | 📝 planejada |
| Extrato financeiro discriminado e paginado | 📝 planejada |
| Base técnica (API, banco, Docker, testes, token, erros padronizados) | ✅ pronta |

## Benefícios

- **Menos erros** no rateio e nos repasses.
- **Rastreabilidade** de cada movimentação.
- **Automação** das regras financeiras.
- **Prestação de contas mais clara** para o proprietário.
- **Controle de saldo** antes de qualquer repasse.
- **Auditoria facilitada:** cada operação gera um registro.
- **Escalabilidade:** administrar muitos proprietários sem aumentar o trabalho manual na mesma proporção.

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
