# RFC 0001: Modelagem da conta do proprietário

| | |
|---|---|
| **Status** | Em discussão |
| **Autoras** | _o time_ |
| **Criada em** | 22/09/2026 |

## Contexto

O projeto é a conta corrente do proprietário dentro da administradora de imóveis: cinco peças (Cliente, Conta, Transação, Tarifa, Extrato) e três regras que o sistema barra (repasse acima do saldo disponível, baixa sem política de imputação, lançamento genérico). A descrição completa está no [README](../../README.md).

Antes da primeira linha de código, quatro decisões precisam estar escritas aqui. Cada uma segue o formato:

> **Decisão:** o que escolhemos.
> **Alternativa descartada:** o que consideramos e não escolhemos.
> **Por quê:** o motivo da escolha e o custo que aceitamos.

As perguntas em cada seção existem para guiar a discussão. Não precisam de resposta uma a uma.

---

## Decisão 1: Onde o saldo mora

**As opções:**
- **(a) Campo na conta:** a tabela da conta guarda o saldo, atualizado a cada lançamento.
- **(b) Soma dos lançamentos:** o saldo não é guardado. Ele é calculado a partir dos lançamentos sempre que alguém pergunta.

**Perguntas para a discussão:**
- Duas requisições de repasse chegam ao mesmo tempo. Como a Regra 1 (sem repasse acima do saldo disponível) continua valendo?
- Como saldo **disponível** e saldo **provisionado** aparecem em cada opção?
- O extrato e o saldo sempre precisam bater. Em qual opção é mais fácil provar isso?

**Decisão:** _a definir_
**Alternativa descartada:** _a definir_
**Por quê:** _a definir_

---

## Decisão 2: Centavos e arredondamento

Dinheiro é guardado em **inteiro de centavos**. Falta decidir **quem fica com o arredondamento** quando um valor é repartido.

**Perguntas para a discussão:**
- Ao dividir R$ 100,00 em três partes, sobra 1 centavo. Quem fica com ele?
- A taxa de administração é um percentual. Quando o resultado não é um número inteiro de centavos, ele é arredondado para cima, para baixo ou para o mais próximo?
- Onde essa regra fica escrita no código, para que ela exista num lugar só?

**Decisão:** _a definir_
**Alternativa descartada:** _a definir_
**Por quê:** _a definir_

---

## Decisão 3: Tarifa por dentro ou por fora do repasse

**As opções:**
- **Por dentro:** a taxa é descontada do valor repassado.
- **Por fora:** o repasse sai cheio, e a taxa é cobrada à parte.

E, nos dois casos: **a tarifa vira um lançamento próprio** ou não?

**Perguntas para a discussão:**
- A Regra 3 proíbe lançamento genérico. Como a tarifa aparece no extrato do proprietário?
- Se o saldo disponível não cobrir o repasse **mais** a tarifa, o que acontece?

**Decisão:** _a definir_
**Alternativa descartada:** _a definir_
**Por quê:** _a definir_

---

## Decisão 4: Chave pública da conta × id interno

**As opções:**
- Expor o **id interno** (o número que o banco gera).
- Expor uma **chave pública** (por exemplo, um UUID) e manter o id interno só dentro do sistema. É o que o projeto base já faz com o `sample_entity_key`.

**Perguntas para a discussão:**
- Alguém que conhece a conta 41 consegue adivinhar a 42? O que isso significa para a segurança (IDOR)?
- Qual chave aparece nas URLs, no extrato e nos logs?

**Decisão:** _a definir_
**Alternativa descartada:** _a definir_
**Por quê:** _a definir_

---

## Também a declarar: a política de imputação

A Regra 2 recusa uma baixa sem **política de imputação declarada**. O Código Civil define parte da ordem, e o time define e defende o resto. Confiram o texto dos artigos antes de citar:

- **Art. 354:** havendo capital e juros, o pagamento é imputado primeiro nos juros vencidos e depois no capital.
- **Art. 355:** se ninguém indicar a dívida, a imputação vai primeiro para as dívidas líquidas e vencidas; se forem todas iguais nisso, para a mais onerosa.

**A política do time:** _a definir_. Por exemplo: em que ordem entram aluguel, condomínio, IPTU, multa e taxa quando o valor pago não cobre tudo?

---

## Alternativa de domínio considerada

O mesmo desenho serve para **leiloeiros**, em que a comissão e o prazo de repasse vêm de um decreto de 1932 em vez de uma política própria. Registrem aqui se o time considerou essa troca e por que ficou com as administradoras de imóveis.

_a definir_
