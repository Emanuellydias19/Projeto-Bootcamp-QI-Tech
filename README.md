<p align="center">
  <img src="assets/readme/titulo.png" alt="ORCA" width="100%">
</p>

<p align="center">
  <img src="assets/readme/logos.png" alt="Bootcamp | QI Tech" width="100%">
</p>

<p align="center">
  <img src="assets/readme/integrantes.png" alt="Integrantes" width="100%">
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/emanuelly-dias-2a0480305/"><img src="assets/readme/emanuelly.png" alt="Emanuelly Dias" title="Emanuelly Dias no LinkedIn" width="200"></a>
  &nbsp;&nbsp;
  <a href="https://www.linkedin.com/in/julia-g-perri/"><img src="assets/readme/julia.png" alt="Julia Perri" title="Julia Perri no LinkedIn" width="200"></a>
  &nbsp;&nbsp;
  <a href="https://www.linkedin.com/in/maya-giron-almeida"><img src="assets/readme/maya.png" alt="Maya Giron" title="Maya Giron no LinkedIn" width="200"></a>
</p>

<p align="center">
  <img src="assets/readme/instrutores.png" alt="Instrutores" width="100%">
</p>

<div align="center">

| Instrutor | Função |
| --- | --- |
| Gilberto Oliveira | Tech Lead · DTVM |
| Gabriel Orsi | Tech Lead · Financeiro Tech |
| João Bebber | Tech Lead · LaaS |
| Pedro Calil | Head · DTVM |
| Gustavo Guanabara | Professor |

</div>

---

> **A ORCA é o livro-caixa interno da administradora que mantém a posição financeira de cada proprietário, por imóvel.** É o núcleo de um banco dentro da administradora: contas, saldo, transações, tarifa e extrato. Ela registra e controla de quem é cada valor, para que ele está reservado e quanto pode ser repassado. Ela não executa PIX nem boleto: liquidar o dinheiro no sistema bancário não faz parte de um protótipo.
>
> **Implementada.** As 11 rotas do contrato estão no ar, cobertas por testes que falam só por HTTP, inclusive os de concorrência: cadastro, conta, saldo, cobrança (com inclusão de item e consulta), recebimento, pagamento de encargo, repasse com a taxa, estorno e extrato. O desenho está no [RFC da ORCA](docs/rfc/rfc-orca.md), e cada decisão, com a alternativa descartada, está no [documento de decisões](docs/rfc/RFC.md). A entidade de exemplo do projeto base (`sample_entity`) continua no código como referência didática da base, fora do escopo da ORCA.
>
> **Preparada para produção.** Logs em JSON com o `request_id`, métricas de tráfego, erro e duração em `/metrics`, prontidão separada da vida do processo, limites de tempo no banco e de tamanho no corpo, e recusa de subir em produção com o token padrão. Tudo explicado em [docs/producao.md](docs/producao.md), com as respostas às 9 perguntas da Aula 4 e os limites que ainda ficam, como a autorização por perfil.

**Sumário:** [A dor](#a-dor) · [A ideia](#a-ideia) · [As cinco peças](#as-cinco-peças) · [As três regras](#as-três-regras-que-o-sistema-barra) · [Um mês na conta](#um-mês-na-conta-do-proprietário) · [Decisões de modelagem](#decisões-de-modelagem) · [Status](#status) · [Tecnologias](#tecnologias) · [Começando](#começando) · [Documentação](#documentação) · [Estrutura](#estrutura) · [Como contribuir](#como-contribuir) · [Licença](#licença)

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

Um **livro-caixa interno** que mantém, dentro da administradora, a posição de cada proprietário:

- todo dinheiro que entra vira **lançamento**;
- toda saída passa por **regra**;
- o **extrato** é a prestação de contas. Ele não é um relatório: é uma obrigação.

## As cinco peças

| Peça | O que é |
| --- | --- |
| **Cliente** | O proprietário, com CPF/CNPJ validado. |
| **Conta** | Uma por proprietário e imóvel, com o **saldo disponível** separado do **reservado** para condomínio e IPTU. |
| **Transação** | O aluguel entra; condomínio, IPTU e repasse saem. Nenhuma fura o saldo. |
| **Tarifa** | A taxa de administração, retida no momento do repasse. |
| **Extrato** | Paginado e discriminado por natureza, porque a lei manda. |

## As três regras que o sistema barra

| # | O sistema recusa… | Base |
| --- | --- | --- |
| 1 | **Repasse acima do saldo disponível** do proprietário. | Regra de negócio |
| 2 | **Baixa de pagamento sem política de imputação declarada.** O Código Civil manda imputar primeiro nos juros e depois no capital. O resto da ordem é política do time, e é ela que o time defende. | Código Civil, arts. 354 e 355 |
| 3 | **Lançamento genérico no extrato.** Todo crédito e todo débito carrega uma natureza, ou a operação é recusada. | Lei 8.245/1991, art. 22, VI |

## Um mês na conta do proprietário

```text
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

## Decisões de modelagem

As quatro decisões pedidas pela banca estão fechadas e registradas no **[documento de decisões](docs/rfc/RFC.md#14-decisões-tomadas)**, no formato *decisão → alternativa descartada → por quê*:

1. **Onde o saldo mora:** em dois campos na conta, `saldo_disponivel` e `saldo_reservado`, que servem para controle e trava. Os lançamentos explicam a composição.
2. **Dinheiro em inteiro de centavos.** A taxa é truncada para baixo, e a sobra do arredondamento fica sempre com o proprietário.
3. **Tarifa por dentro, retida no repasse,** como lançamento próprio: o operador pede o valor bruto, e a API devolve a taxa e o líquido.
4. **Chave pública (UUID)** em todas as rotas; o id interno nunca sai da API.

O diagrama do banco está em [docs/rfc/orca-modelo-dados.erd.json](docs/rfc/orca-modelo-dados.erd.json) e abre no ERD Editor do VS Code.

## Status

| Item | Status |
| --- | --- |
| Cliente (proprietário com CPF ou CNPJ, inclusive o alfanumérico, validado) | Pronto |
| Conta (saldo disponível × reservado) | Pronta |
| Transação (cobrança, recebimento imputado pela política, pagamento de encargo e estorno) | Pronta |
| Tarifa (taxa de administração retida no repasse) | Pronta |
| Extrato (paginado por cursor e discriminado por natureza) | Pronto |
| Regra 1: sem repasse acima do saldo disponível | Pronta |
| Regra 2: sem baixa sem política de imputação | Pronta |
| Regra 3: sem lançamento genérico | Pronta |
| Concorrência (trava da conta) e idempotência nas quatro operações de dinheiro | Prontas |
| Decisões de modelagem e de contrato | Fechadas |
| Produção (logs, métricas, saúde, timeouts e limites) | Pronta |
| Decisões de implementação | Registradas (DD11 a DD40); as derivadas aguardam a revisão do time |

## Tecnologias

| Camada | Ferramenta | Versão |
| --- | --- | --- |
| Linguagem | Python | 3.11 (na imagem Docker) |
| API | FastAPI + Uvicorn | 0.141.1 / 0.52.3 |
| Validação da entrada | jsonschema | 4.17.3 |
| Banco de dados | PostgreSQL | 16 |
| Acesso ao banco | SQLAlchemy + psycopg2 | 2.0.23 / 2.9.10 |
| Chamadas a outros serviços | requests | 2.32.3 |
| Ambiente | Docker + Docker Compose | Compose Specification |
| Testes | pytest | 7.4.4 |

## Começando

Você precisa de **Docker Desktop**, **Git** e **Python 3.12 ou mais novo** (só para os testes). Com eles instalados:

```bash
git clone https://github.com/Emanuellydias19/Projeto-Bootcamp-QI-Tech.git
cd Projeto-Bootcamp-QI-Tech
cp .env.example .env
docker compose up --build
```

Abra <http://localhost:3000>: se aparecer `{"service":"bootcamp-api",...}`, está funcionando.

O passo a passo completo está em **[docs/como-rodar.md](docs/como-rodar.md)**, com os testes, as particularidades do Windows, as soluções para os erros mais comuns e um [passeio pelas rotas da ORCA](docs/como-rodar.md#6-um-passeio-pelas-rotas-da-orca) com `curl`.

## Documentação

| Documento | O que tem |
| --- | --- |
| [docs/como-rodar.md](docs/como-rodar.md) | Instalação, execução, testes e problemas comuns. |
| [docs/producao.md](docs/producao.md) | A ORCA em produção: logs, métricas, saúde, timeouts, idempotência, configuração e segurança, com as respostas às 9 perguntas da Aula 4. |
| [docs/rfc/rfc-orca.md](docs/rfc/rfc-orca.md) | O RFC da ORCA no formato oficial do Bootcamp: o problema, a solução, as rotas, o diagrama do banco, os fluxos e o principal desafio. |
| [docs/rfc/RFC.md](docs/rfc/RFC.md) | O documento de decisões da API: domínio, regras de negócio, rotas, fluxos, modelo de dados e as decisões tomadas e em aberto. |
| [docs/rfc/orca-modelo-dados.erd.json](docs/rfc/orca-modelo-dados.erd.json) | O diagrama do banco de dados, para abrir no ERD Editor do VS Code. |
| [docs/como-o-projeto-e-organizado.md](docs/como-o-projeto-e-organizado.md) | A arquitetura: o caminho de uma requisição, o que cada pasta pode e não pode fazer e onde mexer para cada tipo de mudança. |
| [docs/guia-da-api-base.md](docs/guia-da-api-base.md) | O guia original do projeto base: as rotas atuais com exemplos de `curl` e o catálogo de códigos de erro (`QIT…`). |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Como o time trabalha: branches, commits e pull requests. |

## Estrutura

```text
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
