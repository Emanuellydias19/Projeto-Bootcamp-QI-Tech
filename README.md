# Projeto-Bootcamp-QI-Tech

> **Uma API que é a conta corrente do proprietário dentro da administradora.** Todo dinheiro que entra vira lançamento, toda saída passa por regra, e o extrato é a prestação de contas: não um relatório, uma obrigação.

> 🚧 **Em construção.** A base técnica está pronta: API, banco, Docker, testes, autenticação e erros padronizados. As funcionalidades financeiras estão sendo modeladas e ainda não foram implementadas. O código em `src/` hoje traz a entidade de exemplo do projeto base (`sample_entity`), que será substituída aos poucos.

**Sumário:** [A dor](#a-dor) · [A ideia](#a-ideia) · [As cinco peças](#as-cinco-peças) · [As três regras](#as-três-regras-que-o-sistema-barra) · [Um mês na conta](#um-mês-na-conta-do-proprietário) · [Funcionalidades](#funcionalidades) · [Benefícios](#benefícios) · [Tecnologias](#tecnologias) · [Começando](#começando) · [Documentação](#documentação) · [Estrutura](#estrutura) · [Como contribuir](#como-contribuir) · [Licença](#licença)

---

## A dor

Uma administradora de imóveis guarda dinheiro que **não é dela**. O inquilino paga um boleto único (aluguel + condomínio + IPTU) numa conta da administradora. Ela precisa:

- pagar o síndico e a prefeitura nos vencimentos deles;
- reter a taxa de administração;
- repassar o resto ao proprietário, lá pelo dia 10.

Cada proprietário tem uma **posição própria** dentro desse caixa comum.

### O problema

O problema aparece quando entra um valor **diferente do boleto**: pagamento parcial, atraso com multa e juros, ou uma despesa lançada depois da emissão. O rateio pré-calculado deixa de valer, e alguém decide na mão como dividir aquele dinheiro entre aluguel, encargos e taxa.

Essa decisão muda quanto o proprietário recebe, e a lei ainda proíbe quitação genérica: a **Lei 8.245/1991 (Lei do Inquilinato), art. 22, VI** exige recibo discriminado. Hoje, tudo isso vive numa planilha ao lado do ERP.

## A ideia

Uma API que funciona como a **conta corrente do proprietário dentro da administradora**:

- todo dinheiro que entra vira **lançamento**;
- toda saída passa por **regra**;
- o **extrato** é a prestação de contas. Ele não é um relatório: é uma obrigação.

## As cinco peças

| Peça | O que é |
|---|---|
| **Cliente** | O proprietário, com CPF/CNPJ validado. |
| **Conta** | Uma por proprietário, com o **saldo disponível** separado do **provisionado**. |
| **Transação** | O aluguel entra; condomínio, IPTU e repasse saem. Nenhuma fura o saldo. |
| **Tarifa** | A taxa de administração, retida no momento do repasse. |
| **Extrato** | Paginado e discriminado por natureza, porque a lei manda. |

## As três regras que o sistema barra

| # | O sistema recusa… | Base |
|---|---|---|
| 1 | **Repasse acima do saldo disponível** do proprietário. | Regra de negócio |
| 2 | **Baixa de pagamento sem política de imputação declarada.** O Código Civil manda imputar primeiro nos juros e depois no capital. O resto da ordem é política do time, e é ela que o time defende. | Código Civil, arts. 354 e 355 |
| 3 | **Lançamento genérico no extrato.** Todo crédito e todo débito carrega uma natureza, ou a operação é recusada. | Lei 8.245/1991, art. 22, VI |

## Um mês na conta do proprietário

```
boleto pago pelo inquilino (aluguel + condomínio + IPTU)
        ↓  entra como lançamentos, cada um com sua natureza
conta do proprietário
        ↓  condomínio sai para o síndico, no vencimento
        ↓  IPTU sai para a prefeitura, no vencimento
        ↓  no repasse, a taxa de administração é retida
        ↓  o resto vai para o proprietário (lá pelo dia 10), nunca acima do saldo disponível
extrato discriminado: a prestação de contas do mês
```

Se o valor pago for diferente do boleto, a **política de imputação** declarada decide como ele se divide, e não uma planilha.

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
