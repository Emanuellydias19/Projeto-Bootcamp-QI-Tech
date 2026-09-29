# Documento de Decisões da API

> Documento de apoio à implementação.
> Reúne as decisões de domínio, regras, fluxos e contrato que devem estar definidos antes do início da codificação.

**Fontes:**

* **(RFC):** RFC "Conta corrente do proprietário na administração de locação", versão 1, de 20/09/2026. É a fonte de verdade do desenho.
* **(Pitch):** documento "Conta corrente do proprietário ORCA: dor e solução", preparado para a reunião com a banca.
* **(Time):** decisões de modelagem e de contrato fechadas pelo time em 23 e 24/09/2026, e decisões de implementação aprovadas em 28/09/2026. Quando uma decisão do time ajusta o RFC, ela está registrada em [14. Decisões tomadas](#14-decisões-tomadas).

O que ainda não foi decidido aparece como **em aberto**, com o ID da seção [13. Decisões em aberto](#13-decisões-em-aberto), e não deve ser resolvido dentro do código.

---

## 1. Objetivo

### 1.1 Problema

Descrever de forma objetiva qual problema a API resolve.

**Pergunta que precisamos responder:**

> Qual problema da administradora de imóveis estamos resolvendo e por que ele exige uma API?

**Resposta (RFC).** Uma administradora de imóveis recebe do inquilino um valor único que cobre aluguel, condomínio e IPTU, paga os encargos aos credores de cada um, retém a taxa de administração e repassa o líquido ao proprietário. Entre o recebimento e o repasse, o dinheiro fica parado no caixa da administradora, e ele não é dela: cada proprietário tem uma posição própria dentro desse caixa comum.

O boleto único tem donos diferentes, e cada parte sai num dia diferente **(Pitch)**:

| O que entra | De quem é | Quando sai | Para quem |
| --- | --- | --- | --- |
| Aluguel | Proprietário | No repasse, por volta do dia 10 | Proprietário |
| Condomínio | Condomínio | No vencimento do condomínio | Síndico |
| IPTU | Município | No vencimento da parcela | Prefeitura |
| Taxa de administração | Administradora | Retida no repasse | Administradora |

Todo esse dinheiro fica na mesma conta bancária da administradora. Por isso, o que está guardado para condomínio e IPTU não pode ser repassado ao proprietário, e um erro de conta de um proprietário acaba pago com o dinheiro de outro, sem ninguém ver **(Pitch)**.

O problema aparece quando entra um valor **diferente do boleto** **(Pitch)**:

* **Pagamento parcial:** entrou menos do que o devido. Quem recebe primeiro, o condomínio ou o proprietário?
* **Atraso:** entraram multa e juros, que não estavam no rateio original. De quem é esse dinheiro?
* **Despesa lançada depois da emissão:** um reparo ou uma taxa extra, quando o boleto já tinha saído com outro rateio.

Nos três casos, o rateio pré-calculado deixa de valer e alguém decide na mão como dividir o dinheiro. Essa decisão muda quanto o proprietário recebe, não fica registrada em lugar nenhum e hoje vive numa planilha ao lado do ERP. E a Lei 8.245/1991, art. 22, VI exige recibo discriminado e veda a quitação genérica.

A garantia é sobre **dinheiro de terceiro**, em três frentes:

* o saldo de um proprietário nunca pode ficar negativo nem divergir da soma dos lançamentos, porque divergir significa repassar dinheiro de outro proprietário;
* uma operação reenviada por timeout não pode produzir o mesmo efeito financeiro duas vezes;
* o extrato precisa reconstruir o saldo lançamento a lançamento, discriminado por natureza.

Isso exige uma API porque as regras precisam valer em todo lançamento, para qualquer operador, com concorrência e reenvio de requisições: exatamente o que uma planilha não garante.

---

### 1.2 Objetivo da solução

Descrever o que a API permitirá fazer para resolver o problema.

**Pergunta:**

> Ao final da implementação, o que o sistema será capaz de realizar?

**Resposta (Time).**

> **A ORCA é o livro-caixa interno da administradora que mantém a posição financeira de cada proprietário, por imóvel. Ela não movimenta dinheiro: registra de quem é cada valor, para que ele está reservado e quanto pode ser repassado.**

O título do RFC continua "Conta corrente do proprietário", porque o enunciado da QI Tech fala em "conta" e o título ecoa o enunciado de propósito. Na apresentação, a primeira frase é a do livro-caixa: ela evita a pergunta "então vocês estão fazendo um banco?".

Ao final da Fase 1, o sistema será capaz de:

* cadastrar o proprietário e abrir uma conta para cada imóvel dele;
* registrar o que o inquilino deve em cada competência (a cobrança) e o que ele pagou, dividindo o valor entre as naturezas por uma política de imputação declarada;
* lembrar o que ficou em aberto quando o pagamento não cobre tudo, para o pagamento seguinte continuar dali;
* separar o que pode ser repassado (disponível) do que está guardado para condomínio e IPTU (reservado);
* pagar condomínio e IPTU com o dinheiro reservado daquele proprietário;
* reter a taxa de administração e repassar o líquido ao proprietário, nunca acima do disponível;
* devolver um extrato paginado e discriminado por natureza, que reconstrói o saldo.

Quem usa: um **operador da administradora** faz as operações; o **proprietário** consulta o extrato da conta dele.

---

### 1.3 Escopo da Fase 1

Listar somente o que será implementado nesta entrega.

* [x] Cadastro de cliente
* [x] Criação de conta vinculada ao cliente
* [x] Registro de transação
* [x] Controle de saldo
* [x] Transferência
* [x] Aplicação de tarifa
* [x] Consulta de extrato paginado

> Esta seção deve ser confrontada com o escopo oficial do QI Tech.

**Confronto com o escopo da QI Tech.** Os itens acima usam o vocabulário genérico do escopo oficial. Na ORCA, cada um corresponde a:

| Item do escopo QI Tech | Na ORCA | Rota |
| --- | --- | --- |
| Cadastro de cliente | Cadastro do proprietário | `POST /proprietarios` |
| Criação de conta vinculada ao cliente | Conta do proprietário para um imóvel | `POST /contas` |
| Registro de transação | Cobrança da competência, recebimento do inquilino (entrada) e pagamento de encargo (saída) | `POST /contas/{chave}/cobrancas`, `POST /cobrancas/{chave}/itens`, `GET /cobrancas/{chave}`, `POST /cobrancas/{chave}/recebimentos` e `POST /contas/{chave}/encargos/pagamentos` |
| Controle de saldo | Saldo disponível e saldo reservado na conta, protegidos por trava | todas as rotas de movimento e `GET /contas/{chave}/saldo` |
| Transferência | Repasse do líquido ao proprietário | `POST /contas/{chave}/repasses` |
| Aplicação de tarifa | Taxa de administração retida no repasse, lançada à parte | dentro de `POST /contas/{chave}/repasses` |
| Consulta de extrato paginado | Extrato discriminado por natureza, paginado por cursor | `GET /contas/{chave}/extrato` |

Os itens ficam desmarcados até serem implementados.

**O recorte da Fase 1 (Time).** Declarar o que fica de fora não enfraquece o desenho: é uma pergunta obrigatória desta seção.

| A ORCA resolve na Fase 1 | A ORCA não resolve agora |
| --- | --- |
| Recebimento e imputação | Adiantamento e crédito ao proprietário |
| Pagamento parcial com dívida viva | Correção manual de lançamento |
| Reservado por natureza | Copropriedade (dois donos por imóvel) |
| Pagamento de encargo | Política de retry do conector |
| Tarifa e repasse | Emissão de boleto e régua de cobrança |
| Extrato discriminado e rastreável | Conciliação com extrato bancário |
| Registro do repasse, travado no disponível | Execução da transferência bancária (PIX, TED ou boleto) |

Também ficam fora **(RFC)**: contrato de locação e reajuste, obrigações acessórias fiscais e controle de acesso por perfil. Nenhum deles disputa saldo, e manter todos deixaria o núcleo raso.

**Nível de controle da Fase 1: nível 1, só registro (Time, DD11).** É uma decisão de escopo, e não uma limitação esquecida. A ORCA não executa a transferência bancária. Ela registra a obrigação, calcula o valor disponível para repasse, aplica as regras de negócio e registra o repasse realizado. Ela não controla o dinheiro fisicamente: controla a posição financeira e a decisão operacional dentro do sistema.

```text
O banco movimenta o dinheiro
        ↓
A ORCA governa o registro e a posição financeira
        ↓
A administradora executa o pagamento
```

**Pergunta esperada da banca:** "Se a administradora pode ignorar o que a ORCA registra, qual é o controle que a API realmente exerce?" A resposta separa controle financeiro de movimentação bancária. A ORCA não controla a transferência bancária: controla a posição financeira que fundamenta o repasse. Para cada proprietário, ela mantém os lançamentos, o saldo disponível, os valores reservados, as despesas, as taxas e os repasses, e, antes de registrar um repasse, valida as regras e impede o registro de um valor acima do disponível. A transferência bancária continua sendo executada pelo sistema financeiro que a administradora já usa.

---

## 2. Entendimento do domínio

Antes de definir as rotas, precisamos definir os conceitos que existem no sistema.

## 2.1 Entidades

| Entidade | O que representa? | Dados principais |
| --- | --- | --- |
| Proprietário (o "Cliente") | O dono do imóvel, a quem o dinheiro pertence | chave pública, documento (único), nome |
| Conta | A posição do proprietário para um imóvel dentro do caixa da administradora | chave pública, proprietário, imóvel, saldo disponível, saldo reservado, taxa de administração, multa e juros (em bps), política de imputação |
| Cobrança | O que o inquilino deve numa competência (Time, T14 e T25) | chave pública, conta, competência (única por conta), vencimento |
| Item da cobrança | Quanto é devido de uma natureza naquela competência (Time, T14 e T25) | cobrança, natureza, valor devido |
| Transação | Um movimento de dinheiro: recebimento, encargo, repasse ou estorno | chave pública, conta, tipo, chave de idempotência, hash da requisição (DD18), resultado guardado, cobrança paga e data do pagamento (só no recebimento, DD19), transação estornada (só no estorno) |
| Lançamento | Uma parte da transação, com uma única natureza (aluguel, condomínio, IPTU, despesa extra, multa, juros, taxa, repasse) | chave pública, transação, conta, natureza, valor em centavos (sinalizado, nunca alterado), item da cobrança que quitou (quando houver) |
| Política de imputação | A ordem em que um valor recebido quita as naturezas | chave pública, nome, versão (nunca editada no lugar), ordem das naturezas, vigente desde |
| Transferência | Não é uma entidade própria na ORCA: o repasse é uma **Transação** do tipo `repasse` | ver Transação |

---

## 2.2 Relações

Definir como as entidades se relacionam.

Exemplo:

```text
Cliente
   │
   └── possui ──> Conta
                     │
                     ├── possui saldo
                     │
                     └── possui ──> Transações
```

**Na ORCA:**

```text
Proprietário
   │
   └── detém ──> Conta (uma por imóvel)
                   │
                   ├── saldo_disponivel e saldo_reservado
                   ├── é regida por ──> Política de imputação (versionada)
                   │
                   ├── tem ──> Cobrança (uma por competência)
                   │              └── tem ──> Itens (aluguel, condomínio, IPTU, despesa extra)
                   │
                   └── movimenta ──> Transação (recebimento, encargo, repasse, estorno)
                                        │
                                        └── compõe ──> Lançamentos (cada um com uma natureza)
```

Perguntas a decidir:

* Um cliente pode possuir mais de uma conta?
* Uma conta pertence a apenas um cliente?
* Uma transferência gera uma ou mais transações?
* O saldo é armazenado ou calculado?
* Uma tarifa é uma transação?
* Uma transação pode ser alterada depois de criada?

**Respostas:**

* **Mais de uma conta por proprietário?** Sim: uma conta por imóvel. A combinação proprietário e imóvel é única (RFC). Copropriedade, com dois donos no mesmo imóvel, fica fora da Fase 1 (Time).
* **Conta de um só proprietário?** Sim. A conta aponta para um único proprietário (RFC).
* **Quantas transações um repasse gera?** Uma transação do tipo `repasse`, com dois lançamentos: a taxa e o repasse (RFC e Time, T16). Quando não há taxa pendente, o lançamento da taxa não existe, e o repasse tem um lançamento só (DD34).
* **Saldo armazenado ou calculado?** Armazenado, em **dois campos** na conta: `saldo_disponivel` e `saldo_reservado`. Eles servem para controle e trava; a composição de cada um é explicada pelos lançamentos (Time, T13).
* **A tarifa é uma transação?** Não. A tarifa é um **lançamento próprio**, de natureza `taxa`, dentro da transação de repasse (RFC e Time, T05 e T15).
* **Uma transação pode ser alterada?** Não. Os lançamentos são imutáveis; uma correção é uma nova transação de estorno (RFC e Time, T22).

---

## 3. Regras de negócio

> **Objetivo:** definir o que o sistema permite, o que bloqueia e por quê.

Não adicionar regras apenas porque parecem uma boa prática. Cada regra deve possuir uma justificativa no domínio ou nos requisitos do projeto.

## 3.1 Regras obrigatórias

| ID | Regra | Motivo | Operação afetada |
| --- | --- | --- | --- |
| RN01 | O saldo disponível e o saldo reservado de uma conta nunca ficam negativos | Saldo negativo significa gastar dinheiro de outro proprietário (RFC) | Pagamento de encargo, repasse, estorno |
| RN02 | A soma dos dois saldos é sempre igual à soma dos lançamentos da conta | Divergir significa repassar dinheiro alheio (RFC). Invariante: `saldo_disponivel + saldo_reservado = SUM(lancamento.valor_centavos)` | Todas as operações de movimento |
| RN03 | Uma operação reenviada não produz o mesmo efeito duas vezes | Timeout leva o operador a reenviar, e o mesmo dinheiro não pode entrar ou sair duas vezes (RFC) | Recebimento, pagamento de encargo, repasse, estorno |
| RN04 | Todo lançamento tem uma natureza; lançamento genérico é recusado | Lei 8.245/1991, art. 22, VI: recibo discriminado, quitação genérica vedada (RFC) | Todas as operações de movimento, extrato |
| RN05 | A baixa de um pagamento só acontece com uma política de imputação declarada | Código Civil, art. 354: juros antes do capital. O resto da ordem é política do time, declarada e com a versão guardada (RFC e Pitch) | Recebimento |
| RN06 | O dinheiro de um proprietário nunca paga obrigação ou repasse de outro | É a garantia central do sistema: cada dono tem sua posição (RFC) | Pagamento de encargo, repasse |
| RN07 | Condomínio e IPTU só são pagos ao credor integralmente | Nenhum dos dois credores aceita fração; o rateio proporcional foi descartado (RFC) | Pagamento de encargo |
| RN08 | Um cadastro por documento | Evita dois proprietários para a mesma pessoa (RFC: 409) | Cadastro do proprietário |
| RN09 | Uma conta por proprietário e imóvel | Uma posição única por imóvel (RFC: 409) | Abertura de conta |
| RN10 | A taxa de administração, a multa e os juros ficam entre 0 e 10000 bps (0% a 100%) | Percentual fora dessa faixa não tem sentido (RFC: 422; a multa e os juros seguem a mesma faixa da taxa, DD07) | Abertura de conta |
| RN11 | O repasse só consome o **saldo disponível**; o pagamento de encargo só consome o **reservado** daquela natureza | O dinheiro guardado para condomínio e IPTU não pode ser repassado, mesmo estando na mesma conta (Pitch e Time, T13) | Repasse, pagamento de encargo |
| RN12 | Recebimento acima do devido na data do pagamento é recusado; o devido é o que está em aberto na cobrança mais a multa e os juros calculados para aquela data | Na Fase 1, o excedente não é registrado; ele fica fora do sistema e é tratado pelo operador (Time, T19 e T35) | Recebimento |
| RN13 | O valor recebido para um encargo que não fica completo continua reservado até completar; a imputação não pula para a próxima natureza | Pular deixaria o condomínio descoberto enquanto o aluguel é pago (Time, T20) | Recebimento |
| RN14 | A multa incide uma vez sobre o que estava em aberto no vencimento; os juros correm pro rata die sobre o aberto; um segundo pagamento não gera multa nova | A multa é uma por dívida, não uma por pagamento, e nada é recalculado sobre valor já quitado (Time, T18) | Recebimento |
| RN15 | Um item novo só entra numa cobrança ainda não quitada; numa cobrança quitada, a inclusão é recusada e o item vai para a competência seguinte | Evita dois tipos de cobrança e a imputação escolhendo entre duas abertas (Time, T21) | Inclusão de item na cobrança |
| RN16 | Toda transação tem pelo menos um lançamento, e a soma dos lançamentos da transação é igual ao valor dela | Corrige a frase do RFC ("dois ou mais"), porque o pagamento de encargo gera um lançamento só (Time, T24) | Todas as operações de movimento |

As regras que o sistema **recusa**, com código de erro próprio e motivo legível, são as três pedidas pela banca **(Pitch)**: RN05 (baixa sem política de imputação), RN04 (lançamento genérico) e RN11 (repasse acima do saldo disponível). As três têm a mesma forma: o sistema não deixa o operador tomar sozinho uma decisão que muda o dinheiro de outra pessoa.

---

## 3.2 Regras de saldo

Precisamos decidir:

* O que significa "saldo"?
* Quando o saldo aumenta?
* Quando o saldo diminui?
* Uma operação pode deixar o saldo negativo?
* O saldo considera tarifas?
* Em qual momento uma transferência altera o saldo?
* O que acontece se não houver saldo suficiente?

### Decisão das regras de saldo

> **(Time, T13).** A conta tem **dois saldos**:
>
> ```text
> Conta
> ├── saldo_disponivel      trava e validação do repasse
> └── saldo_reservado       trava e validação do pagamento de encargo
>
> Lançamentos (a fonte de verdade da composição)
> ├── condomínio    → reservado
> ├── IPTU          → reservado
> ├── aluguel       → disponível
> ├── multa         → disponível
> ├── juros         → disponível
> └── despesa extra → disponível (T39)
> ```
>
> **Os saldos servem para controle e trava. Os lançamentos explicam a composição.** O `saldo_reservado` não sabe quanto dele é condomínio e quanto é IPTU, e não precisa saber. Quando o pagamento de encargo pergunta "tem 350 de condomínio?", a resposta sai da soma dos lançamentos daquela natureza, lida com a conta já travada.
>
> * **Aumenta:** no recebimento. Aluguel, multa, juros e despesa extra entram no disponível; condomínio e IPTU entram no reservado (T39).
> * **Diminui:** o pagamento de encargo sai do reservado; a taxa e o repasse saem do disponível.
> * **Negativo:** nunca (RN01).
> * **Tarifas:** sim, a taxa é um lançamento e sai do disponível.
> * **Quando o repasse altera o saldo:** na mesma transação de banco que grava os lançamentos, com trava pessimista na linha da conta. Lançamentos e saldos nascem juntos ou não nascem (RFC).
> * **Saldo insuficiente:** a operação é desfeita (ROLLBACK) e a API responde **409**, com `QIT001020` (disponível insuficiente) ou `QIT001021` (reservado insuficiente), sem nenhum lançamento órfão (RFC e T31).
>
> **Descartadas:** uma coluna de saldo por natureza, porque cada natureza nova viraria uma migração; e lançamentos de "reserva" movendo valor entre os dois saldos, porque dobrariam os lançamentos sem informação nova, já que o destino é decidido na imputação.

---

## 3.3 Regras de transferência

Na ORCA, a "transferência" do escopo é o **repasse**: a administradora retém a taxa e transfere o líquido ao proprietário.

Precisamos decidir:

* Quem pode iniciar uma transferência?
* A conta de origem precisa existir?
* A conta de destino precisa existir?
* A conta de origem pode transferir para ela mesma?
* O valor precisa ser positivo?
* O saldo precisa ser suficiente?
* A tarifa é descontada da origem?
* A tarifa faz parte do valor transferido ou é cobrada separadamente?
* O que acontece se alguma etapa da transferência falhar?

### Decisão das regras de transferência

> * **Quem inicia:** o operador da administradora (RFC).
> * **Conta de origem:** precisa existir; se não existir, **404** (RFC).
> * **Conta de destino:** não existe no sistema. O destino do repasse é o próprio proprietário da conta, fora da API (RFC).
> * **Para ela mesma:** não se aplica, porque não há conta de destino.
> * **Valor positivo:** sim; valor menor ou igual a zero é recusado com **422** (`QIT001018`), como no recebimento (DD06).
> * **Saldo suficiente:** o valor pedido precisa caber no **saldo disponível**; senão, **409** `QIT001020` (RFC, RN11 e T31).
> * **Tarifa descontada da origem:** sim, sai do disponível da conta do proprietário.
> * **Tarifa por dentro (Time, T16):** o operador pede o valor **bruto**; a API separa a taxa e o líquido e devolve os dois. O saldo disponível cai exatamente o valor pedido. A taxa é um **lançamento próprio** (RFC, T05). **Descartada:** tarifa por fora, porque o débito real passaria do valor pedido e a validação de saldo seria feita sobre um número que o cliente não mandou.
> * **Falha em alguma etapa:** tudo acontece numa única transação de banco. Qualquer falha desfaz a operação inteira: nenhum lançamento órfão e nenhum saldo alterado (RFC).

---

## 3.4 Regras de tarifa

Precisamos decidir:

* Existe uma tarifa fixa ou percentual?
* Quem paga a tarifa?
* Quando ela é calculada?
* Quando ela é descontada?
* A tarifa aparece no extrato?
* A tarifa possui uma transação própria?
* O valor da tarifa pode deixar a conta negativa?

### Decisão das regras de tarifa

> * **Fixa ou percentual:** percentual, em pontos-base (`taxa_administracao_bps`, de 0 a 10000), definido por conta na abertura (RFC).
> * **Quem paga:** o proprietário; a taxa sai do disponível da conta dele.
> * **Quando é calculada e descontada (Time, T15):** **no repasse**. **Descartada:** tarifa no recebimento, porque cobraria taxa sobre o dinheiro do síndico e da prefeitura, que só está de passagem. Esta decisão substitui o trecho do fluxo de recebimento do RFC que lançava a taxa no recebimento.
> * **Base e cálculo (Time, T17, T27 e T38):** a taxa incide **só sobre o aluguel efetivamente quitado**, e não sobre multa, juros ou o valor do repasse pedido. Ela é derivada dos lançamentos, sem estado novo: `taxa pendente = max(0, ⌊SUM(aluguel recebido) × taxa_administracao_bps ÷ 10000⌋ − SUM(taxa já retida))`, truncada para baixo e nunca negativa (DD26); a sobra fica sempre com o proprietário. O repasse retém a taxa pendente e, como ela sai de dentro do valor bruto pedido (T16), o líquido é `valor_bruto − taxa`. Assim a taxa não muda com a quantidade nem com o tamanho dos repasses: num repasse parcial, a taxa do aluguel já quitado é retida uma vez só, e os repasses seguintes não pagam de novo sobre o mesmo aluguel.
> * **Aparece no extrato:** sim, como linha própria, de natureza `taxa` (RFC).
> * **Transação própria:** não; é um lançamento dentro da transação de repasse (RFC).
> * **Pode deixar a conta negativa:** não. O valor bruto inteiro precisa caber no disponível, e a taxa sai de dentro dele (RN01 e T16).
> * **Repasse menor ou igual à taxa pendente (Time, T40 e DD25):** é recusado com **422** (`QIT001026`), sem nenhum lançamento. A taxa não é retida em parte nem dividida entre repasses, e a API não registra um repasse cujo líquido seria zero ou negativo.
> * **Taxa pendente depois de um estorno (Time, DD26):** nunca fica negativa. Estornar um recebimento cujo aluguel já teve a taxa retida não gera devolução automática da taxa; essa taxa é descontada da taxa dos aluguéis que entrarem depois (compensação aprovada pelo time em 28/09/2026).

---

## 4. Dinheiro e valores monetários

Definir como valores financeiros serão representados.

## 4.1 Unidade

Decidir entre:

* [x] Centavos como inteiro
* [ ] `NUMERIC/DECIMAL`
* [ ] Outro

### Decisão da unidade de medida

> **(RFC)** Todo valor é um **inteiro em centavos** (`bigint`, campos com o sufixo `_centavos`). Taxa, multa e juros são **inteiros em pontos-base** (`int`, 10000 bps = 100%).

### Justificativa da unidade

> Float não representa centavos com exatidão (0,1 + 0,2 não dá 0,3), e o erro se acumula em sistema financeiro. Inteiro é exato: o centavo não some nem duplica, e a soma dos lançamentos bate com o saldo sem tolerância. Pontos-base mantêm os percentuais também como inteiros. O conector de boletos do projeto base já segue a mesma regra ("dinheiro nunca viaja como float").

---

## 4.2 Precisão

Definir:

* número de casas decimais;
* arredondamento;
* valor mínimo;
* valor máximo;
* representação nas requisições;
* representação nas respostas.

**Decisões:**

* **Casas decimais:** nenhuma na API (o valor já está em centavos). Em reais, equivale a duas casas.
* **Arredondamento (Time, T17):** todo cálculo em bps é **truncado para baixo** (`⌊ ⌋`), e a sobra fica sempre com o proprietário. **Descartada:** arredondar para o mais próximo, porque a sobra mudaria de dono conforme o valor.
* **Valor mínimo:** maior que zero em toda operação com valor; zero ou negativo é recusado com **422** (`QIT001018`) (RFC e DD06).
* **Valor máximo:** no recebimento, o devido na data do pagamento, que é o aberto da cobrança mais a multa e os juros daquela data (RN12 e T35). No repasse e no pagamento de encargo, o saldo correspondente (RN11). Fora isso, o limite é 9007199254740991, o maior inteiro que um cliente JSON lê sem perder precisão e bem abaixo do limite do `bigint`, barrado no schema com 400 (DD28).
* **Teto do saldo (Time, DD37):** o mesmo 9007199254740991 vale para cada saldo da conta. A operação que levaria o disponível ou o reservado acima dele é recusada com **422** (`QIT001029`), sem nada gravado, e o banco confere o mesmo teto numa restrição.
* **Nas requisições:** inteiro em centavos, no campo `valor_centavos`.
* **Nas respostas:** inteiro em centavos. Os lançamentos são **sinalizados** (RFC): entrada positiva e saída negativa.

---

## 5. Integridade e histórico

Definir o que acontece com os dados depois que uma operação ocorre.

## 5.1 Transações

Precisamos decidir:

* Uma transação pode ser editada?
* Uma transação pode ser excluída?
* Como corrigir uma operação incorreta?
* O histórico precisa permanecer íntegro?
* O saldo pode ser reconstruído a partir das transações?

### Decisão sobre as Transações

> * **Editar:** não. Os lançamentos são imutáveis: "sinalizado, nunca alterado" (RFC).
> * **Excluir:** não. Apagar um lançamento quebraria a igualdade entre saldos e soma dos lançamentos (RN02).
> * **Corrigir uma operação incorreta (Time, T22):** por uma **transação de estorno**, pelo mesmo fluxo idempotente das outras transações: `Idempotency-Key`, resultado guardado, trava na conta e lançamentos com o sinal invertido, apontando para a transação original. A correção manual de lançamento fica fora da Fase 1. A rota é `POST /transacoes/{chave}/estornos` (7.2.11, T37).
> * **Histórico íntegro:** sim. A política de imputação é versionada e o rateio aplicado fica gravado nos lançamentos, então um extrato antigo continua explicável mesmo depois de a política mudar (RFC).
> * **Reconstruir o saldo:** sim. O extrato "reconstrói o saldo somando de baixo para cima" (RFC).

---

## 5.2 Identificadores

Definir:

* identificador público;
* identificador interno do banco;
* formato do identificador;
* se o ID interno pode ser exposto.

> O identificador retornado pela API não deve ser automaticamente tratado como o ID do banco sem uma decisão explícita.

**Decisões (RFC):**

* **Identificador público:** o campo `chave`, em todas as entidades expostas (proprietário, conta, cobrança, transação, lançamento e política de imputação).
* **Identificador interno:** o campo `id`, usado só para chaves estrangeiras dentro do banco.
* **Formato:** `chave` é **UUID**, gerado na aplicação (`uuid4`) e guardado em `CHAR(36)`, como na base (DD13); `id` é `bigserial`.
* **Expor o id interno:** nunca. "Nenhuma rota aceita ou devolve o id interno, só a chave pública." A chave pública esconde o volume de registros e não quebra se a base for migrada (Pitch).

**Política de imputação (Time, T30 e T41):** a conta aponta para a política pelo `politica_id`, que é interno. Na API, a política é identificada pela `chave` pública dela, como as outras entidades (T08 e DD08): a abertura de conta recebe `politica_imputacao_chave`. Na Fase 1 existe uma política só, a padrão, criada no `database.sql` com versão 1 e chave fixa (T41).

---

## 6. Segurança e acesso aos recursos

Definir como a API diferencia recursos pertencentes ao solicitante e recursos de terceiros.

## 6.1 Acesso

Precisamos decidir:

* Quem pode consultar uma conta?
* Quem pode realizar uma transferência?
* Quem pode consultar o extrato?
* Como identificamos o proprietário do recurso?
* O que acontece quando alguém tenta acessar um recurso que não lhe pertence?

### Decisão sobre o acesso

> * **Consultar uma conta:** o operador da administradora (RFC).
> * **Realizar um repasse:** o operador da administradora (RFC).
> * **Consultar o extrato:** o operador e o proprietário da conta (RFC).
> * **Como identificamos o dono do recurso:** o **controle de acesso por perfil está fora do escopo** (RFC). A autenticação disponível hoje é a do projeto base: o header `INTERNAL-TOKEN`, igual para todos os chamadores e exigido em todas as rotas, exceto `/` e `/health_check`.
> * **Recurso que não lhe pertence:** "404 e 'não é sua conta' respondem igual, para não confirmar a existência de conta alheia" (RFC).
>
> **Decisão (Time, T33):** o recurso de outro dono responde **404**, igual ao inexistente, sem revelar que ele existe. Na Fase 1, o `INTERNAL-TOKEN` é o mesmo para todos, então a API não sabe quem é o dono de quem chama: na prática, só acontece o 404 de recurso inexistente. Quando o controle de acesso por perfil entrar, a regra já está escrita e continua 404.

---

## 7. Contrato da API

Somente depois das decisões anteriores devemos fechar as rotas.

## 7.1 Mapa de rotas

As rotas genéricas do escopo (`/clientes`, `/transacoes`, `/transferencias`) foram substituídas pelas rotas do RFC, que usam a chave pública (`{chave}`) no lugar do `{id}`.

**Como os caminhos são organizados (Time, T28):** o que pertence à conta fica dentro de `/contas/{chave}`, e o que pertence à cobrança fica dentro de `/cobrancas/{chave}`. A chave do recurso dono vai sempre no caminho, nunca no corpo.

| Método | Endpoint | Objetivo | Entrada | Resposta | Erros |
| --- | --- | --- | --- | --- | --- |
| POST | `/proprietarios` | Cadastrar o dono do imóvel | `documento`, `nome` | 201 | 422 documento com dígito inválido; 409 documento já cadastrado |
| POST | `/contas` | Abrir a conta do proprietário para um imóvel | `proprietario_chave`, `imovel_referencia`, `politica_imputacao_chave`, `taxa_administracao_bps`, `multa_bps`, `juros_mensal_bps` | 201 | 404 proprietário ou política inexistente; 409 conta já aberta para o imóvel; 422 taxa, multa ou juros fora de 0 a 10000 bps |
| POST | `/contas/{chave}/cobrancas` | Registrar o que o inquilino deve numa competência | `competencia`, `vencimento`, `itens` (natureza e valor) | 201 com a chave da cobrança | 404 conta; 409 já existe cobrança para essa competência |
| POST | `/cobrancas/{chave}/itens` | Incluir um item (despesa lançada depois) numa cobrança ainda não quitada | `natureza`, `valor_centavos` | 201 | 404 cobrança; 409 cobrança já quitada |
| GET | `/cobrancas/{chave}` | Consultar a cobrança: o devido, o pago e o aberto de cada item, e o total devido numa data, com multa e juros | a chave no caminho; query `data` (opcional, DD05) | 200 | 404 cobrança |
| POST | `/cobrancas/{chave}/recebimentos` | Registrar o pagamento do inquilino e imputar o valor sobre a cobrança | `valor_centavos`, `pago_em`; header `Idempotency-Key` | 201 com o rateio aplicado; 200 na repetição idêntica | 409 mesma chave com corpo diferente; 404 cobrança; 422 valor menor ou igual a zero; 422 valor acima do devido na data do pagamento; 422 `pago_em` no futuro ou anterior a um recebimento já registrado |
| POST | `/contas/{chave}/encargos/pagamentos` | Pagar condomínio ou IPTU com o reservado daquela natureza | `natureza`, `valor_centavos`; header `Idempotency-Key` | 201; 200 na repetição idêntica | 409 reservado da natureza insuficiente; 409 chave repetida com corpo diferente; 404 conta; 422 valor menor ou igual a zero |
| POST | `/contas/{chave}/repasses` | Reter a taxa e registrar o repasse do líquido ao proprietário (DD11) | `valor_centavos` (bruto); header `Idempotency-Key` | 201 com a taxa e o líquido; 200 na repetição idêntica | 409 disponível insuficiente; 409 chave repetida com corpo diferente; 404 conta; 422 valor menor ou igual a zero; 422 valor bruto menor ou igual à taxa pendente |
| GET | `/contas/{chave}/extrato` | Listar os lançamentos, do mais recente para o mais antigo | query `cursor`, `limite`, `natureza` | 200 com a página e o `proximo_cursor` | 404 conta; 400 limite fora de 1 a 50, natureza fora da lista, parâmetro desconhecido ou `cursor` que não é o último lançamento da sua transação dentro do filtro pedido (DD27) |
| GET | `/contas/{chave}/saldo` | Devolver os saldos e a data do último lançamento | a chave no caminho | 200 | 404 conta |
| POST | `/transacoes/{chave}/estornos` | Estornar uma transação, com lançamentos de sinal invertido | header `Idempotency-Key` | 201; 200 na repetição idêntica | 404 transação; 409 transação já estornada ou que é um estorno; 409 recebimento com outro posterior não estornado na cobrança; 409 saldo insuficiente para desfazer; 409 chave repetida com outra transação |

Todas as rotas acima também exigem o header `INTERNAL-TOKEN` do projeto base (sem ele, **403**).

As rotas da **cobrança** (T25 e T28) estão detalhadas em 7.2.8, 7.2.9 e 7.2.10, e a do estorno (T37 e DD04) em 7.2.11. Os campos `multa_bps` e `juros_mensal_bps` na abertura de conta vêm da decisão T18.

### Convenções do contrato

Valem para todas as rotas.

#### Autenticação

Todo pedido leva o header `INTERNAL-TOKEN`. Sem ele, ou com o valor errado, a resposta é **403**. As únicas exceções são `GET /` e `GET /health_check`, que vêm do projeto base. O método `OPTIONS` também exige o token (DD38).

```http
INTERNAL-TOKEN: default_token
Content-Type: application/json
```

#### Idempotência

As rotas que movem dinheiro (recebimento, pagamento de encargo, repasse e estorno) exigem o header `Idempotency-Key`, um identificador único gerado por quem chama para cada operação.

```http
Idempotency-Key: 7f3c2a9e-2c1d-4b8e-9a51-0e6d3f1b2c44
```

| Situação | Resposta |
| --- | --- |
| Primeira vez com essa chave | **201**, a operação acontece |
| Mesma chave e mesma requisição: rota, chave do caminho e corpo (reenvio após timeout) | **200**, com o resultado original e sem novo efeito |
| Mesma chave na mesma conta, requisição diferente: outra rota, outra chave no caminho ou outro corpo (DD18) | **409**, chave reutilizada |
| Mesma chave em outra conta | **201**, é outra operação (a chave é única por conta, T03) |

Sem o header, com ele vazio ou com mais de 255 caracteres, a resposta é **400** (`QIT000001`), como qualquer pedido fora do formato na base (Time, T32 e DD32). Espaços e tabulações nas pontas do valor não fazem parte da chave, como define o HTTP: `abc`, `abc` seguido de espaço e `abc` seguido de tabulação são a mesma chave, e os 255 caracteres são contados sem eles (DD38).

#### Valores e formatos

| Tipo | Formato | Exemplo |
| --- | --- | --- |
| Dinheiro | inteiro em centavos, campos com o sufixo `_centavos` | `150000` (R$ 1.500,00) |
| Percentual | inteiro em pontos-base, sufixo `_bps` (10000 = 100%) | `1000` (10%) |
| Identificador | a `chave` pública, UUID; o id interno nunca aparece | `"3fbf83e9-e5fc-4e0f-8427-db6a1a50f964"` |
| Data | `AAAA-MM-DD` | `"2026-10-05"` |
| Competência | `AAAA-MM` | `"2026-10"` |
| Documento | CPF `000.000.000-00` ou CNPJ `00.000.000/0000-00`, com a máscara, como na base; o CNPJ aceita também o formato alfanumérico da Receita, com letras maiúsculas nas 12 primeiras posições (DD37) | `"529.982.247-25"`, `"12.ABC.345/01DE-35"` |
| Lançamento | valor sinalizado: entrada positiva, saída negativa | `-35000` |

#### Formato dos erros

Todo erro segue o formato do projeto base:

```json
{
  "title": "Insufficient available balance",
  "description": "The amount 150001 is above the 150000 available in the account.",
  "translation": "O saldo disponível da conta não cobre o valor pedido.",
  "code": "QIT001020"
}
```

Como nos erros da base, o `title` e a `description` saem em inglês, e a `translation`, em português.

Toda resposta traz o header `X-Request-ID`, o número de protocolo da requisição (projeto base).

Uma `{chave}` fora do formato UUID no caminho é tratada como inexistente: **404**, como a base faz com a chave no caminho.

#### Catálogo de erros

Um catálogo único, no padrão `QIT` da base (Time, T31). Cada erro tem um código, uma mensagem e um status HTTP, e nenhuma rota inventa a própria representação de erro. Os códigos do projeto começam em `QIT001008`, o próximo livre da base (DD01); os `QIT001001` a `QIT001007` são da entidade de exemplo e saem com ela.

| Código | HTTP | Quando acontece |
| --- | ---: | --- |
| `QIT000001` | 400 | corpo, query ou header fora do formato: campo faltando, tipo errado, texto vazio, só com espaços, com caractere de controle ou com mais de 255 caracteres (DD37), corpo que não é UTF-8 ou JSON legível (DD38), valor em centavos ou em pontos-base com casa decimal, valor acima de 9007199254740991 (DD28), natureza fora da lista, `limite` fora de 1 a 50, `cursor` que não é um lançamento da conta ou que partiria uma transação (DD27) ou `Idempotency-Key` ausente, vazia ou com mais de 255 caracteres (DD32) (projeto base) |
| `QIT000002` | 403 | sem o `INTERNAL-TOKEN`, ou com o valor errado (projeto base) |
| `QIT001008` | 422 | documento com o formato certo e os dígitos verificadores errados |
| `QIT001009` | 409 | documento já cadastrado |
| `QIT001010` | 404 | proprietário não encontrado |
| `QIT001011` | 404 | conta não encontrada (ou não é sua conta, T33) |
| `QIT001012` | 409 | já existe conta para esse proprietário e imóvel |
| `QIT001013` | 422 | taxa, multa ou juros fora de 0 a 10000 bps |
| `QIT001014` | 404 | política de imputação não encontrada |
| `QIT001015` | 404 | cobrança não encontrada |
| `QIT001016` | 409 | já existe cobrança para essa competência |
| `QIT001017` | 409 | cobrança já quitada |
| `QIT001018` | 422 | valor menor ou igual a zero |
| `QIT001019` | 422 | recebimento acima do devido na data do pagamento (aberto + multa + juros) |
| `QIT001020` | 409 | saldo disponível insuficiente |
| `QIT001021` | 409 | saldo reservado da natureza insuficiente |
| `QIT001022` | 409 | `Idempotency-Key` já usada com outro corpo, ou para outra transação |
| `QIT001023` | 404 | transação não encontrada |
| `QIT001024` | 409 | transação já estornada, ou que é ela mesma um estorno |
| `QIT001025` | 422 | data ou competência com o formato certo que não existe no calendário (por exemplo, `2026-02-30` ou `2026-13`, DD31) |
| `QIT001026` | 422 | repasse com valor bruto maior que zero e menor ou igual à taxa pendente (T40 e DD25) |
| `QIT001027` | 422 | `pago_em` no futuro, ou anterior a um recebimento não estornado da cobrança; ou, na consulta da cobrança, `data` anterior a esse recebimento (DD21) |
| `QIT001028` | 409 | estorno de um recebimento quando a cobrança tem um recebimento posterior não estornado (DD35) |
| `QIT001029` | 422 | operação que levaria o saldo disponível ou o reservado acima de 9007199254740991 (DD37) |

Os demais erros gerais (`QIT000404`, `QIT000405` e `QIT000500`) seguem o projeto base.

As três regras que o sistema barra **(Pitch)** chegam ao cliente assim: RN11 (repasse acima do disponível) com `QIT001020`; RN05 (baixa sem política declarada) com `QIT001014`, porque a conta não abre sem uma política existente e todo recebimento usa a política da conta; e RN04 (lançamento genérico) no schema, com `QIT000001` e o campo `natureza` na descrição do erro.

#### Exemplo usado nos contratos

Um imóvel com aluguel de R$ 1.500,00, condomínio de R$ 350,00 e IPTU de R$ 150,00, taxa de administração de 10% (`1000` bps), multa de 2% (`200` bps) e juros de 1% ao mês (`100` bps).

#### Idempotência e sucesso por rota

| Método | Rota | Idempotency-Key | Sucesso |
| --- | --- | --- | --- |
| POST | `/proprietarios` | não (a restrição UNIQUE do documento barra o reenvio) | 201 |
| POST | `/contas` | não (a restrição UNIQUE de proprietário e imóvel barra o reenvio) | 201 |
| POST | `/contas/{chave}/cobrancas` | não (a restrição UNIQUE de conta e competência barra o reenvio) | 201 |
| POST | `/cobrancas/{chave}/itens` | não | 201 |
| GET | `/cobrancas/{chave}` | não | 200 |
| POST | `/cobrancas/{chave}/recebimentos` | sim | 201; 200 na repetição |
| POST | `/contas/{chave}/encargos/pagamentos` | sim | 201; 200 na repetição |
| POST | `/contas/{chave}/repasses` | sim | 201; 200 na repetição |
| GET | `/contas/{chave}/extrato` | não | 200 |
| GET | `/contas/{chave}/saldo` | não | 200 |
| POST | `/transacoes/{chave}/estornos` | sim (T22) | 201; 200 na repetição |

---

## 7.2 Para cada rota

Antes de implementar cada endpoint, responder:

### 7.2.1 POST /proprietarios

**O que a operação faz?**

> Cadastra o proprietário: a raiz de quem é cada posição dentro do caixa.

**O que recebe?**

> `documento` e `nome`.

**O que devolve?**

> **201.** Pela regra da chave pública, a resposta traz a `chave` do proprietário, usada depois na abertura da conta.

**Headers:** `INTERNAL-TOKEN`, `Content-Type: application/json`.

**Campos do corpo:**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `documento` | texto | sim | CPF ou CNPJ, numérico ou alfanumérico (DD37), com dígitos verificadores válidos |
| `nome` | texto | sim | nome do proprietário |

**Exemplo de requisição:**

```json
{
  "documento": "529.982.247-25",
  "nome": "Maria da Silva"
}
```

**Exemplo de resposta 201:**

```json
{
  "proprietario_chave": "b1f0c2d4-8a3e-4c6b-9d2f-1e5a7c9b3d10"
}
```

**Quais regras de negócio são executadas?**

> RN08 (um cadastro por documento) e a validação dos dígitos verificadores do documento.

**Quais situações bloqueiam a operação?**

> Documento com dígito inválido; documento já cadastrado.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Corpo fora do formato | 400 | `QIT000001` (projeto base) |
| Documento com dígito inválido | 422 | `QIT001008` (DD02) |
| Documento já cadastrado | 409 | `QIT001009` |

### 7.2.2 POST /contas

**O que a operação faz?**

> Abre a conta do proprietário para um imóvel e fixa as regras daquele dinheiro: a política de imputação, a taxa de administração e os percentuais de multa e juros do contrato de locação.

**O que recebe?**

> `proprietario_chave`, `imovel_referencia`, `politica_imputacao_chave`, `taxa_administracao_bps`, `multa_bps` e `juros_mensal_bps`.

**O que devolve?**

> **201.** A resposta traz a `chave` da conta, usada em todas as rotas seguintes. A conta nasce com os dois saldos em zero.

**Headers:** `INTERNAL-TOKEN`, `Content-Type: application/json`.

**Campos do corpo:**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `proprietario_chave` | UUID | sim | o dono da conta |
| `imovel_referencia` | texto | sim | o imóvel; uma conta por proprietário e imóvel |
| `politica_imputacao_chave` | UUID | sim | a política que decide a ordem de quitação (T30 e DD08); na Fase 1, a chave fixa da política padrão (T41) |
| `taxa_administracao_bps` | inteiro | sim | de 0 a 10000 |
| `multa_bps` | inteiro | sim | de 0 a 10000; multa do contrato de locação |
| `juros_mensal_bps` | inteiro | sim | de 0 a 10000; juros mensais do contrato de locação |

**Exemplo de requisição:**

```json
{
  "proprietario_chave": "b1f0c2d4-8a3e-4c6b-9d2f-1e5a7c9b3d10",
  "imovel_referencia": "Rua das Flores, 120, apto 34",
  "politica_imputacao_chave": "7d2e9b41-3c5a-4f8e-a1b6-9c0d2e4f6a18",
  "taxa_administracao_bps": 1000,
  "multa_bps": 200,
  "juros_mensal_bps": 100
}
```

**Exemplo de resposta 201:**

```json
{
  "conta_chave": "3fbf83e9-e5fc-4e0f-8427-db6a1a50f964"
}
```

**Quais regras de negócio são executadas?**

> RN09 (uma conta por proprietário e imóvel) e RN10 (taxa, multa e juros entre 0 e 10000 bps). A conta passa a apontar para a política de imputação (base da RN05).

**Quais situações bloqueiam a operação?**

> Proprietário inexistente; política inexistente; conta já aberta para o imóvel; taxa, multa ou juros fora da faixa.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Corpo fora do formato | 400 | `QIT000001` (projeto base) |
| Proprietário inexistente | 404 | `QIT001010` |
| Conta já aberta para esse imóvel | 409 | `QIT001012` |
| Taxa, multa ou juros fora de 0 a 10000 bps | 422 | `QIT001013` |
| Política de imputação inexistente | 404 | `QIT001014` |

### 7.2.3 POST /cobrancas/{chave}/recebimentos

**O que a operação faz?**

> Registra o pagamento do inquilino sobre a cobrança indicada no caminho e imputa o valor nas naturezas, na ordem da política vigente: juros, multa, encargos (condomínio antes do IPTU), aluguel e despesa extra (RFC, T39 e DD24). Multa e juros são calculados pela fórmula da conta (RN14 e DD20). O encargo que não fica completo continua reservado (RN13), e o que não foi pago fica em aberto na cobrança para o pagamento seguinte (T14). Cada lançamento que quita um item aponta para ele (T25).

**O que recebe?**

> A `chave` da cobrança no caminho; `valor_centavos` e `pago_em` no corpo; e o header `Idempotency-Key`. A conta não vai no pedido: ela vem da cobrança (T28).

**O que devolve?**

> **201 com o rateio aplicado**: como o valor foi dividido entre as naturezas. O resultado fica guardado na transação e é devolvido igual numa repetição (**200**).

**Headers:** `INTERNAL-TOKEN`, `Content-Type: application/json`, `Idempotency-Key`.

**Caminho:** `{chave}` é a `cobranca_chave`. Antes de registrar, o operador consulta quanto é devido na data em `GET /cobrancas/{chave}?data=AAAA-MM-DD` (7.2.10).

**Campos do corpo:**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `valor_centavos` | inteiro | sim | quanto o inquilino pagou; maior que zero e até o devido na data do pagamento (aberto + multa + juros, T35) |
| `pago_em` | data | sim | quando o inquilino pagou; base da multa e dos juros; guardado em `transacao.pago_em`, separado do `criado_em` (DD19) |

Exemplo: o inquilino pagou R$ 1.800,00 em dia, abaixo dos R$ 2.000,00 devidos na cobrança de outubro.

**Exemplo de requisição:**

```http
POST /cobrancas/c4a2e8f1-5b3d-4e7a-8c9f-2d1b6a0e4f37/recebimentos
```

```json
{
  "valor_centavos": 180000,
  "pago_em": "2026-10-05"
}
```

**Exemplo de resposta 201:** o rateio aplicado, na ordem da política (juros, multa, encargos, aluguel, despesa extra), com uma linha por lançamento (DD32), e o que ficou em aberto na cobrança.

```json
{
  "transacao_chave": "e9d1a3b5-7c2f-4a8e-b6d0-3f5c1e9a7b22",
  "rateio": [
    { "natureza": "condominio", "valor_centavos": 35000 },
    { "natureza": "iptu", "valor_centavos": 15000 },
    { "natureza": "aluguel", "valor_centavos": 130000 }
  ],
  "em_aberto": [
    { "natureza": "aluguel", "valor_centavos": 20000 }
  ]
}
```

**Resposta 200:** o mesmo corpo da primeira resposta, numa repetição idêntica.

**Quais regras de negócio são executadas?**

> RN02, RN03, RN04, RN05, RN12, RN13, RN14 e RN16.

**Quais situações bloqueiam a operação?**

> Cobrança inexistente; valor menor ou igual a zero; valor acima do devido na data do pagamento; `pago_em` no futuro ou anterior a um recebimento não estornado da cobrança; mesma chave de idempotência com corpo diferente.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Corpo fora do formato | 400 | `QIT000001` (projeto base) |
| Repetição idêntica (não é erro: devolve o resultado original) | 200 | não se aplica |
| Mesma `Idempotency-Key` com corpo diferente | 409 | `QIT001022` |
| Cobrança inexistente | 404 | `QIT001015` |
| Valor menor ou igual a zero | 422 | `QIT001018` |
| Valor acima do devido na data do pagamento (aberto + multa + juros) | 422 | `QIT001019` |
| `pago_em` inexistente no calendário | 422 | `QIT001025` |
| `pago_em` no futuro (data de São Paulo), ou anterior a um recebimento não estornado da cobrança (DD21 e DD22) | 422 | `QIT001027` |
| `Idempotency-Key` ausente, vazia ou com mais de 255 caracteres (DD32) | 400 | `QIT000001` (projeto base) |

> **Sobre o 422 do excedente (Time, T19):** ele recusa o **registro** de um recebimento acima do devido na data do pagamento (o aberto mais a multa e os juros, T35). Não é uma afirmação sobre o dinheiro: a administradora pode ter recebido R$ 2.100 na conta bancária dela. A ORCA não controla o dinheiro físico, controla o registro da posição. Na Fase 1, o excedente fica fora do sistema e é tratado pelo operador.
>
> **Multa e juros não cobertos (Time, T43):** o que um recebimento não cobre de multa e juros continua devido e entra na imputação do recebimento seguinte, na ordem da política. Multa e juros não viram principal, então não geram juros.

### 7.2.4 POST /contas/{chave}/encargos/pagamentos

**O que a operação faz?**

> Paga condomínio ou IPTU ao credor com o dinheiro **reservado** daquela natureza, na conta do proprietário.

**O que recebe?**

> A `chave` da conta no caminho; `natureza` (condomínio ou IPTU) e `valor_centavos` no corpo; e o header `Idempotency-Key`.

**O que devolve?**

> **201** no pagamento; **200** com o resultado original na repetição idêntica.

**Headers:** `INTERNAL-TOKEN`, `Content-Type: application/json`, `Idempotency-Key`.

**Caminho:** `{chave}` é a `conta_chave`.

**Campos do corpo:**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `natureza` | texto | sim | `condominio` ou `iptu` |
| `valor_centavos` | inteiro | sim | o valor do encargo, pago integralmente ao credor |

**Exemplo de requisição:**

```http
POST /contas/3fbf83e9-e5fc-4e0f-8427-db6a1a50f964/encargos/pagamentos
```

```json
{
  "natureza": "condominio",
  "valor_centavos": 35000
}
```

**Exemplo de resposta 201:**

```json
{
  "transacao_chave": "a7c3e1f9-2b4d-4f6a-9e8c-5d1b3a7f9c01",
  "natureza": "condominio",
  "valor_centavos": 35000
}
```

**Resposta 200:** o mesmo corpo da primeira resposta, numa repetição idêntica.

**Quais regras de negócio são executadas?**

> RN01, RN02, RN03, RN04, RN06, RN07, RN11 e RN16. Com a conta travada, a API soma os lançamentos daquela natureza para saber se o reservado cobre o valor. O valor é pago inteiro ou recusado (DD33).

**Quais situações bloqueiam a operação?**

> Conta inexistente; reservado insuficiente para a natureza; mesma chave com corpo diferente.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Corpo fora do formato | 400 | `QIT000001` (projeto base) |
| Repetição idêntica (não é erro) | 200 | não se aplica |
| Reservado da natureza insuficiente | 409 | `QIT001021` |
| Mesma `Idempotency-Key` com corpo diferente | 409 | `QIT001022` |
| Conta inexistente | 404 | `QIT001011` |
| Natureza diferente de condomínio ou IPTU | 400 | `QIT000001` (projeto base) |
| Valor menor ou igual a zero | 422 | `QIT001018` |

> **Credor (Time, T23):** o credor não é guardado; a natureza já diz para quem é o pagamento.

### 7.2.5 POST /contas/{chave}/repasses

**O que a operação faz?**

> Registra o repasse: retém a taxa de administração e registra o líquido repassado ao proprietário, a partir do saldo disponível. A transferência bancária é feita pela administradora, fora da ORCA (DD11).

**O que recebe?**

> A `chave` da conta no caminho; `valor_centavos` (o valor **bruto**) no corpo; e o header `Idempotency-Key`.

**O que devolve?**

> **201** com a **taxa** e o **líquido** separados; **200** com o resultado original na repetição idêntica.

**Headers:** `INTERNAL-TOKEN`, `Content-Type: application/json`, `Idempotency-Key`.

**Caminho:** `{chave}` é a `conta_chave`.

**Campos do corpo:**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `valor_centavos` | inteiro | sim | o valor **bruto**; a taxa sai de dentro dele |

Exemplo: repasse do aluguel de R$ 1.500,00, com taxa de 10% sobre o aluguel.

**Exemplo de requisição:**

```http
POST /contas/3fbf83e9-e5fc-4e0f-8427-db6a1a50f964/repasses
```

```json
{
  "valor_centavos": 150000
}
```

**Exemplo de resposta 201:** a taxa e o líquido separados. A taxa pendente é `⌊aluguel quitado × 1000 ÷ 10000⌋ − taxa já retida` = 15000 − 0 = 15000 (T38).

```json
{
  "transacao_chave": "f2b8d4a6-1c3e-4d5f-a7b9-0e2c4a6f8d13",
  "valor_bruto_centavos": 150000,
  "taxa_centavos": 15000,
  "liquido_centavos": 135000
}
```

**Resposta 200:** o mesmo corpo da primeira resposta, numa repetição idêntica.

**Quais regras de negócio são executadas?**

> RN01, RN02, RN03, RN04, RN06, RN11 e RN16, com a taxa calculada sobre o aluguel efetivamente quitado (T17, T27 e T38) e lançada à parte (T05 e T16). Sem taxa pendente, o repasse tem um lançamento só, e a resposta traz `taxa_centavos` zero (DD34).

**Quais situações bloqueiam a operação?**

> Conta inexistente; valor bruto maior que o disponível; valor bruto menor ou igual à taxa pendente (T40 e DD25); mesma chave com corpo diferente.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Corpo fora do formato | 400 | `QIT000001` (projeto base) |
| Repetição idêntica (não é erro) | 200 | não se aplica |
| Disponível insuficiente | 409 | `QIT001020` |
| Valor bruto menor ou igual à taxa pendente (T40 e DD25) | 422 | `QIT001026` |
| Mesma `Idempotency-Key` com corpo diferente | 409 | `QIT001022` |
| Conta inexistente | 404 | `QIT001011` |
| Valor menor ou igual a zero | 422 | `QIT001018` |

> **Repasse menor ou igual à taxa pendente (Time, T40 e DD25):**
>
> ```text
> Taxa pendente:      R$ 150,00
> Repasse solicitado: R$ 100,00
> Líquido:            R$ 100,00 − R$ 150,00 = −R$ 50,00
>                     ──> 422 QIT001026, nenhum lançamento de repasse
> ```

### 7.2.6 GET /contas/{chave}/extrato

**O que a operação faz?**

> Lista os lançamentos da conta, do mais recente para o mais antigo, sem cortar uma transação entre páginas. É a prestação de contas exigida por lei.

**O que recebe?**

> A `chave` da conta no caminho e, na query, `cursor`, `limite` e `natureza`.

**O que devolve?**

> **200** com a página de lançamentos e o `proximo_cursor`. Cada lançamento traz a chave dele, a chave e o tipo da transação, a natureza, o valor sinalizado e a data (T32), e a `transacao_estornada_chave`: nas linhas de um estorno, a chave da transação que ele desfaz; nas outras, `null` (DD36).

**Headers:** `INTERNAL-TOKEN`.

**Caminho:** `{chave}` é a `conta_chave`.

**Parâmetros de query (todos opcionais):**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `cursor` | texto | o `proximo_cursor` da página anterior, que é a chave do último lançamento dela (DD27) |
| `limite` | inteiro | quantos lançamentos por página: de 1 a 50 (T32), padrão 10, como na base (DD03); a página pode passar dele para não cortar a última transação (DD36) |
| `natureza` | texto | filtra por natureza; com filtro, o extrato não reconstrói o saldo total |

Qualquer outro parâmetro é recusado com 400, como no projeto base.

**Exemplo de requisição:**

```http
GET /contas/3fbf83e9-e5fc-4e0f-8427-db6a1a50f964/extrato?limite=2
```

**Exemplo de resposta 200:**

```json
{
  "data": [
    {
      "lancamento_chave": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
      "transacao_chave": "f2b8d4a6-1c3e-4d5f-a7b9-0e2c4a6f8d13",
      "tipo": "repasse",
      "natureza": "repasse",
      "valor_centavos": -135000,
      "criado_em": "2026-10-10T14:02:11Z",
      "transacao_estornada_chave": null
    },
    {
      "lancamento_chave": "1b2c3d4e-5f6a-4b7c-9d8e-0f1a2b3c4d5e",
      "transacao_chave": "f2b8d4a6-1c3e-4d5f-a7b9-0e2c4a6f8d13",
      "tipo": "repasse",
      "natureza": "taxa",
      "valor_centavos": -15000,
      "criado_em": "2026-10-10T14:02:11Z",
      "transacao_estornada_chave": null
    }
  ],
  "limite": 2,
  "proximo_cursor": "1b2c3d4e-5f6a-4b7c-9d8e-0f1a2b3c4d5e"
}
```

O `proximo_cursor` é a chave do último lançamento da página, e não o id interno (T08 e DD27). Quando não há mais páginas, ele vem `null`.

**Quais regras de negócio são executadas?**

> RN04 (toda linha tem natureza). A soma dos lançamentos, de baixo para cima, reconstrói os saldos (RN02).

**Quais situações bloqueiam a operação?**

> Conta inexistente; limite fora de 1 a 50; `cursor` que não é um lançamento desta conta, que é de outra natureza que a filtrada, ou que não é o último lançamento da sua transação dentro do filtro pedido (DD27).

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Parâmetro desconhecido ou fora do formato | 400 | `QIT000001` (projeto base) |
| Conta inexistente (ou não é sua conta) | 404 | `QIT001011` |
| Limite fora de 1 a 50 | 400 | `QIT000001` (projeto base) |
| `cursor` que não é um lançamento desta conta, ou que parte uma transação (DD27) | 400 | `QIT000001` (projeto base) |

> **Observação:** com o filtro `natureza`, o extrato mostra só aquela natureza e, sozinho, não reconstrói o saldo total. O `limite` vai até 50 (T32), e é o teto do parâmetro: a página termina no fim da última transação e pode passar dele (DD36).

### 7.2.7 GET /contas/{chave}/saldo

**O que a operação faz?**

> Devolve os saldos atuais da conta e a data do último lançamento, sem somar o histórico.

**O que recebe?**

> A `chave` da conta no caminho.

**O que devolve?**

> **200** com o saldo disponível e o saldo reservado, em centavos, e a data do último lançamento.

**Headers:** `INTERNAL-TOKEN`.

**Caminho:** `{chave}` é a `conta_chave`.

**Exemplo de requisição:**

```http
GET /contas/3fbf83e9-e5fc-4e0f-8427-db6a1a50f964/saldo
```

**Exemplo de resposta 200:**

```json
{
  "conta_chave": "3fbf83e9-e5fc-4e0f-8427-db6a1a50f964",
  "saldo_disponivel_centavos": 0,
  "saldo_reservado_centavos": 15000,
  "ultimo_lancamento_em": "2026-10-10T14:02:11Z"
}
```

**Quais regras de negócio são executadas?**

> Nenhuma escrita. Os saldos lidos são os materializados, que por RN02 somam o mesmo que o extrato.

**Quais situações bloqueiam a operação?**

> Conta inexistente.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Conta inexistente (ou não é sua conta) | 404 | `QIT001011` |

### 7.2.8 POST /contas/{chave}/cobrancas

**O que a operação faz?**

> Registra o que o inquilino deve numa competência, com um item por natureza. É o que o recebimento quita (T14 e T25).

**O que recebe?**

> A `chave` da conta no caminho; `competencia`, `vencimento` e `itens` (cada um com `natureza` e `valor_centavos`) no corpo.

**O que devolve?**

> **201** com a `chave` da cobrança, usada para consultar a cobrança, incluir itens e registrar recebimentos.

**Headers:** `INTERNAL-TOKEN`, `Content-Type: application/json`.

**Caminho:** `{chave}` é a `conta_chave`.

**Campos do corpo:**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `competencia` | texto | sim | o mês de referência; uma cobrança por conta e competência |
| `vencimento` | data | sim | a base da multa e dos juros |
| `itens` | lista | sim | pelo menos um item |
| `itens[].natureza` | texto | sim | `aluguel`, `condominio`, `iptu` ou `despesa_extra` (T36) |
| `itens[].valor_centavos` | inteiro | sim | quanto é devido dessa natureza |

**Exemplo de requisição:**

```http
POST /contas/3fbf83e9-e5fc-4e0f-8427-db6a1a50f964/cobrancas
```

```json
{
  "competencia": "2026-10",
  "vencimento": "2026-10-05",
  "itens": [
    { "natureza": "aluguel", "valor_centavos": 150000 },
    { "natureza": "condominio", "valor_centavos": 35000 },
    { "natureza": "iptu", "valor_centavos": 15000 }
  ]
}
```

**Exemplo de resposta 201:**

```json
{
  "cobranca_chave": "c4a2e8f1-5b3d-4e7a-8c9f-2d1b6a0e4f37"
}
```

**Quais regras de negócio são executadas?**

> Uma cobrança por conta e competência (UNIQUE no banco). O vencimento é a base da multa e dos juros (RN14).

**Quais situações bloqueiam a operação?**

> Conta inexistente; já existe cobrança para essa competência.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Corpo fora do formato | 400 | `QIT000001` (projeto base) |
| Conta inexistente | 404 | `QIT001011` |
| Já existe cobrança para essa competência | 409 | `QIT001016` |
| Item com valor menor ou igual a zero | 422 | `QIT001018` |
| `vencimento` inexistente no calendário | 422 | `QIT001025` |
| `competencia` com mês inexistente (por exemplo, `2026-13`) | 422 | `QIT001025` (DD31) |

### 7.2.9 POST /cobrancas/{chave}/itens

**O que a operação faz?**

> Inclui um item numa cobrança ainda não quitada: é por aqui que entra a despesa lançada depois da emissão do boleto (T21).

**O que recebe?**

> A `chave` da cobrança no caminho, e `natureza` e `valor_centavos` no corpo.

**O que devolve?**

> **201.**

**Headers:** `INTERNAL-TOKEN`, `Content-Type: application/json`.

**Caminho:** `{chave}` é a `cobranca_chave`.

**Campos do corpo:**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `natureza` | texto | sim | `despesa_extra`, a natureza da despesa lançada depois da emissão (T36) |
| `valor_centavos` | inteiro | sim | quanto é devido |

**Exemplo de requisição:**

```json
{
  "natureza": "despesa_extra",
  "valor_centavos": 8000
}
```

**Exemplo de resposta 201:**

```json
{
  "cobranca_chave": "c4a2e8f1-5b3d-4e7a-8c9f-2d1b6a0e4f37",
  "itens": [
    { "natureza": "aluguel", "valor_devido_centavos": 150000 },
    { "natureza": "condominio", "valor_devido_centavos": 35000 },
    { "natureza": "iptu", "valor_devido_centavos": 15000 },
    { "natureza": "despesa_extra", "valor_devido_centavos": 8000 }
  ]
}
```

**Quais regras de negócio são executadas?**

> RN15: o item só entra numa cobrança ainda não quitada; se ela já foi quitada, o item vai para a competência seguinte.

**Quais situações bloqueiam a operação?**

> Cobrança inexistente; cobrança já quitada.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Corpo fora do formato | 400 | `QIT000001` (projeto base) |
| Cobrança inexistente | 404 | `QIT001015` |
| Cobrança já quitada | 409 | `QIT001017` |
| Natureza diferente de `despesa_extra` | 400 | `QIT000001` (projeto base) |
| Valor menor ou igual a zero | 422 | `QIT001018` (DD06) |

> **Item incluído depois do vencimento (Time, T42):** entra na multa e nos juros a partir da data de inclusão, sem encargos retroativos pelo período entre o vencimento e a inclusão.

### 7.2.10 GET /cobrancas/{chave}

**O que a operação faz?**

> Mostra a cobrança como ela está agora: quanto é devido, quanto já foi pago e quanto está em aberto em cada item. É por aqui que o operador sabe o valor máximo aceito num recebimento antes de registrá-lo, já que o recebimento acima do devido na data (aberto + multa + juros) é recusado com 422 (RN12 e T35). Rota incluída pela decisão T28.

**O que recebe?**

> A `chave` da cobrança no caminho e, na query, a `data` (opcional, `AAAA-MM-DD`; se não vier, vale a data de hoje em São Paulo) (DD05 e DD22).

**O que devolve?**

> **200** com os dados da cobrança; o `status` calculado (DD23); para cada item, o valor devido, o valor pago e o valor em aberto; o total em aberto; a multa e os juros devidos na `data`, já descontado o que foi pago deles (DD20 e T43); e o **total devido na data**, que é o máximo aceito num recebimento pago nesse dia (RN12 e T35).

**Headers:** `INTERNAL-TOKEN`.

**Caminho:** `{chave}` é a `cobranca_chave`.

Exemplo: a cobrança de outubro depois do recebimento de R$ 1.800,00 do exemplo da 7.2.3.

**Exemplo de requisição:**

```http
GET /cobrancas/c4a2e8f1-5b3d-4e7a-8c9f-2d1b6a0e4f37?data=2026-10-05
```

**Exemplo de resposta 200:**

```json
{
  "cobranca_chave": "c4a2e8f1-5b3d-4e7a-8c9f-2d1b6a0e4f37",
  "conta_chave": "3fbf83e9-e5fc-4e0f-8427-db6a1a50f964",
  "competencia": "2026-10",
  "vencimento": "2026-10-05",
  "status": "parcial",
  "itens": [
    { "natureza": "aluguel", "valor_devido_centavos": 150000, "valor_pago_centavos": 130000, "valor_em_aberto_centavos": 20000 },
    { "natureza": "condominio", "valor_devido_centavos": 35000, "valor_pago_centavos": 35000, "valor_em_aberto_centavos": 0 },
    { "natureza": "iptu", "valor_devido_centavos": 15000, "valor_pago_centavos": 15000, "valor_em_aberto_centavos": 0 }
  ],
  "total_em_aberto_centavos": 20000,
  "data": "2026-10-05",
  "multa_centavos": 0,
  "juros_centavos": 0,
  "total_devido_na_data_centavos": 20000
}
```

**Quais regras de negócio são executadas?**

> Nenhuma escrita. O que está em aberto não é guardado: é calculado como o valor devido de cada item menos a soma dos lançamentos que apontam para ele, contando só os recebimentos não estornados (12.7 e DD35). O `status` também é calculado, sem coluna no banco (DD23): `aberta` quando nada foi pago na cobrança, `parcial` quando algo foi pago e ainda há valor devido, e `quitada` só quando nada mais é devido: itens, multa e juros (T43).

**Quais situações bloqueiam a operação?**

> Cobrança inexistente, ou `data` anterior a um recebimento não estornado da cobrança (DD21): a posição antes de um pagamento já lançado não é reconstruída.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Cobrança inexistente (ou não é sua cobrança) | 404 | `QIT001015` |
| `data` fora do formato | 400 | `QIT000001` (projeto base) |
| `data` inexistente no calendário | 422 | `QIT001025` |
| `data` anterior a um recebimento não estornado da cobrança (DD21) | 422 | `QIT001027` |

> **Multa e juros:** não entram no valor em aberto dos itens, porque dependem da data do pagamento (RN14). Por isso a rota os calcula para a `data` pedida, pela fórmula da DD20, e o total devido na data é o limite do recebimento (T35). No exemplo, o pagamento é em dia, então os dois são zero.

### 7.2.11 POST /transacoes/{chave}/estornos

**O que a operação faz?**

> Desfaz uma transação registrada por engano sem apagar nada: cria uma transação nova, do tipo `estorno`, com um lançamento de sinal invertido para cada lançamento da original, apontando para o mesmo item da cobrança quando houver (T22, T37 e DD04). Os lançamentos invertidos são gravados na ordem da original, e a resposta os lista na ordem do extrato, do mais recente para o mais antigo (DD35). Segue o mesmo fluxo idempotente das outras transações: `Idempotency-Key`, resultado guardado e trava na conta.

**O que recebe?**

> A `chave` da transação no caminho e o header `Idempotency-Key`. Não tem corpo: o estorno é sempre da transação inteira, porque inverte todos os lançamentos dela (DD04). Um corpo enviado é ignorado e não entra no hash da idempotência (DD35).

**O que devolve?**

> **201** com a chave do estorno e os lançamentos criados; **200** com o resultado original na repetição idêntica.

**Headers:** `INTERNAL-TOKEN`, `Idempotency-Key`.

**Caminho:** `{chave}` é a `transacao_chave`, que aparece na resposta de cada operação e no extrato.

Exemplo: o repasse da 7.2.5 foi registrado por engano.

**Exemplo de requisição:**

```http
POST /transacoes/f2b8d4a6-1c3e-4d5f-a7b9-0e2c4a6f8d13/estornos
```

**Exemplo de resposta 201:**

```json
{
  "transacao_chave": "9b7e5c3a-1d2f-4e6a-8b0c-2d4f6a8c0e35",
  "transacao_estornada_chave": "f2b8d4a6-1c3e-4d5f-a7b9-0e2c4a6f8d13",
  "lancamentos": [
    { "natureza": "repasse", "valor_centavos": 135000 },
    { "natureza": "taxa", "valor_centavos": 15000 }
  ]
}
```

**Resposta 200:** o mesmo corpo da primeira resposta, numa repetição idêntica.

**Quais regras de negócio são executadas?**

> RN01, RN02, RN03, RN04 e RN16, e T10: a transação original não muda. Estornar um recebimento devolve a cobrança à posição que ela teria sem ele: o valor volta ao "em aberto" dos itens, e a multa e os juros que ele pagou voltam a ser devidos (DD35). Só o último recebimento não estornado da cobrança pode ser estornado (DD35). O estorno também não deixa negativo o disponível nem o reservado de nenhuma natureza (DD33): ele é recusado com 409 quando o saldo atual não cobre o desfazer, por exemplo quando o dinheiro do recebimento já foi repassado ou pago ao credor e nenhum outro valor da conta o cobre. A API não rastreia qual dinheiro foi repassado.

**Quais situações bloqueiam a operação?**

> Transação inexistente; transação já estornada; transação que é ela mesma um estorno; recebimento que não é o último não estornado da cobrança; saldo insuficiente para desfazer; mesma chave de idempotência usada para outra transação.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Repetição idêntica (não é erro) | 200 | não se aplica |
| `Idempotency-Key` ausente, vazia ou com mais de 255 caracteres (DD32) | 400 | `QIT000001` (projeto base) |
| Transação inexistente (ou não é sua) | 404 | `QIT001023` |
| Transação já estornada, ou que é ela mesma um estorno | 409 | `QIT001024` |
| Recebimento com outro posterior não estornado na mesma cobrança (DD35) | 409 | `QIT001028` |
| Desfazer deixaria o saldo disponível negativo | 409 | `QIT001020` |
| Desfazer deixaria negativo o reservado de alguma natureza (DD33) | 409 | `QIT001021` |
| Mesma `Idempotency-Key` usada para outra transação | 409 | `QIT001022` |

---

## 8. Fluxos

Depois de fechar as rotas, devemos desenhar os fluxos das principais operações.

## 8.1 Fluxo de cadastro

```text
Requisição
    ↓
Validação de formato
    ↓
Verificação das regras
    ↓
Persistência
    ↓
Resposta
```

### Decisões sobre o fluxo de cadastro

> * **Validação de formato:** o schema confere que `documento` e `nome` vieram e têm o formato certo.
> * **Verificação das regras:** os dígitos verificadores do documento.
> * **Persistência:** o INSERT no proprietário. A unicidade do documento fica numa restrição UNIQUE no banco, e é ela que produz o 409, não uma consulta prévia.
> * **Resposta:** 201 com a chave pública.

---

## 8.2 Fluxo de criação de conta

```text
Requisição
    ↓
Validação de formato (schema)
    ↓
Proprietário existe? ─── não ──> 404 (QIT001010)
    ↓ sim
Política de imputação existe? ─── não ──> 404 (QIT001014)
    ↓ sim
Taxa, multa e juros entre 0 e 10000 bps? ─── não ──> 422 (QIT001013)
    ↓ sim
INSERT conta (UNIQUE proprietário + imóvel) ─── violou ──> 409 (QIT001012)
    ↓
201 com a chave da conta
```

### Decisões sobre o fluxo de conta

> A conta nasce apontando para a política de imputação, com a taxa, a multa e os juros fixados, e com os dois saldos em zero. Esse fluxo não está desenhado no RFC; ele segue as rotas e os status da seção 7.

---

## 8.3 Fluxo de transação

Na ORCA, o fluxo de transação central é o **recebimento** (RFC, "Recebimento parcial: caminho feliz", com as decisões do time).

```text
Operador ──> POST /cobrancas/{chave}/recebimentos
    ↓
1. o schema valida o formato
    ↓
2. BEGIN
    ↓
3. localiza a cobrança pela chave do caminho (não existe ──> 404)
    ↓
4. SELECT conta da cobrança FOR UPDATE: a primeira leitura da conta, que fica travada (DD16)
    ↓
5. procura, nessa conta, a transação com a mesma Idempotency-Key (DD18)
   (hash da requisição igual ──> 200 com o resultado guardado; hash diferente ──> 409)
    ↓
6. confere o valor (menor ou igual a zero ──> 422) e o pago_em
   (no futuro ou antes de um recebimento não estornado da cobrança ──> 422, DD21)
    ↓
7. calcula o que está em aberto na cobrança
    ↓
8. calcula multa e juros sobre o aberto, na data do pagamento (RN14 e DD20)
   (valor acima de aberto + multa + juros ──> 422)
    ↓
9. imputa o valor pela política vigente: juros, multa, condomínio, IPTU, aluguel, despesa extra (DD24)
    ↓
10. INSERT transacao (chave_idempotencia UNIQUE por conta, hash_requisicao, pago_em, cobranca_id) e INSERT lancamentos (juros, multa e um por item que recebeu valor, DD32)
    ↓
11. UPDATE saldo_disponivel e saldo_reservado
    ↓
12. COMMIT (a trava é liberada)
    ↓
201 com o rateio aplicado
```

### Decisões sobre o fluxo de transação

> Os passos 2 a 12 vivem numa única transação de banco: lançamentos e saldos nascem juntos ou não nascem (RFC). Nenhuma escrita acontece antes das regras: a transação e os lançamentos só são gravados depois das validações dos passos 5 a 9. A consulta pela `Idempotency-Key` acontece com a conta travada, então uma repetição concorrente espera a trava e depois encontra a transação já confirmada; a restrição UNIQUE continua como rede (DD15 e DD18). A ordem de imputação é dado, não código: vem da política versionada apontada pela conta, e o rateio produzido fica gravado nos lançamentos. Diferente do RFC original, a taxa de administração **não** é lançada aqui: ela é retida no repasse (T15).

---

## 8.4 Fluxo de transferência

Na ORCA, a transferência é o **repasse**.

```text
Requisição
    ↓
Validação
    ↓
Verificar contas
    ↓
Verificar saldo
    ↓
Calcular tarifa
    ↓
Registrar movimentações
    ↓
Atualizar saldo
    ↓
Confirmar operação
    ↓
Resposta
```

**Duas requisições concorrentes sobre o mesmo saldo (RFC):**

```text
Repasse A: BEGIN, SELECT conta FOR UPDATE ──> lê disponível 100000 centavos
Repasse B: BEGIN, SELECT conta FOR UPDATE ──> espera na trava (não lê saldo velho)
Repasse A: INSERT lançamentos, UPDATE saldo, COMMIT ──> disponível 20000 centavos
Repasse B: lê 20000, a validação falha, ROLLBACK
           ──> 409 QIT001020, nenhum lançamento órfão
```

**Reenvio por timeout (RFC):**

```text
Com a conta travada, procura a transação com a mesma Idempotency-Key
    ├── não existe ──> opera normalmente ──> 201
    └── existe
            ├── hash da requisição igual ao guardado ──> 200 com o resultado original, sem novo efeito
            └── hash diferente ──> 409 chave reutilizada (DD18)
```

### Decisões sobre o fluxo de transferência

> * **A trava vem antes da verificação de saldo:** o `SELECT ... FOR UPDATE` é a primeira leitura da conta na transação (DD16), é tomado antes da validação e é mantido até o commit. Sem ele, as duas requisições leriam o mesmo saldo antes de qualquer uma escrever, e as duas passariam. A trava serializa aquela conta, não o sistema (RFC).
> * **"Verificar saldo":** o valor bruto precisa caber no **saldo disponível** (RN11).
> * **"Calcular tarifa":** a taxa pendente sobre o aluguel efetivamente quitado (T27 e T38): `max(0, ⌊SUM(aluguel recebido) × taxa_administracao_bps ÷ 10000⌋ − SUM(taxa já retida))` (DD26); líquido = `valor_bruto − taxa` (T17).
> * **"Registrar movimentações":** o lançamento `repasse`, com o líquido, e o lançamento `taxa`, quando a taxa pendente é maior que zero; somados, dão o valor bruto (RN16 e DD34).
> * **Idempotência:** a consulta pela chave acontece com a conta travada (DD17), então nenhuma outra requisição da mesma conta entra no meio. A restrição UNIQUE continua como rede: se ainda assim o INSERT a violar, a violação é capturada e traduzida em 409 (`QIT001022`), nunca em 500 (RFC, T03, DD15 e DD18).

---

## 8.5 Fluxo de extrato

```text
GET /contas/{chave}/extrato?cursor=...&limite=...&natureza=...
    ↓
Validação da query (limite fora de 1 a 50, natureza fora da lista ou parâmetro desconhecido ──> 400)
    ↓
Conta existe? ─── não ──> 404
    ↓ sim
Cursor é um lançamento desta conta, da natureza filtrada
e o último da sua transação dentro do filtro? ─── não ──> 400 (DD27)
    ↓ sim, ou sem cursor
Lê os lançamentos a partir do cursor, do mais recente para o mais antigo
    ↓
Completa a última transação da página, sem cortá-la ao meio
    ↓
200 com a página e o proximo_cursor
```

### Decisões sobre o extrato

> * **Paginação por cursor**, e não por número de página (RFC). O cursor não se desloca quando entram lançamentos novos no topo, então uma página nunca repete nem pula linhas.
> * **Uma transação nunca fica partida entre páginas**, para que o rateio de um recebimento apareça inteiro. Por isso uma página pode ter mais linhas que o `limite` (T32).

---

## 9. Tratamento de falhas

Para cada operação principal, precisamos definir pelo menos um caminho de falha.

| Operação | Falha | Comportamento esperado |
| --- | --- | --- |
| Cadastro | Documento já cadastrado | A restrição UNIQUE barra o INSERT; a API responde 409, e nada é criado |
| Criação de conta | Já existe conta para esse proprietário e imóvel | A restrição UNIQUE barra o INSERT; a API responde 409 |
| Transação (recebimento) | Reenvio da mesma operação após timeout | Com a conta travada, a API encontra a transação com a mesma chave de idempotência; com o mesmo hash da requisição, 200 com o resultado original, sem novo lançamento; com outro hash, 409 (DD18). O UNIQUE da chave continua como rede |
| Transação (recebimento) | Valor acima do devido na data do pagamento (aberto + multa + juros) | 422 (`QIT001019`); nada é registrado, e o excedente é tratado pelo operador fora do sistema (T19) |
| Transferência (repasse) | Duas requisições concorrentes e disponível insuficiente para a segunda | A segunda espera a trava, lê o saldo atualizado, falha na validação e sofre ROLLBACK; 409 `QIT001020`, nenhum lançamento órfão |
| Extrato | Limite acima de 50 | 400 (`QIT000001`), sem ler nada do banco |
| Estorno | Transação já estornada | 409 (`QIT001024`); nada é criado, e a original continua como estava |
| Transferência (repasse) | Valor bruto menor ou igual à taxa pendente | 422 (`QIT001026`); nenhum lançamento de repasse (T40 e DD25) |

---

## 10. Validações

Separar explicitamente **validação de formato** de **regra de negócio**.

## 10.1 Schema

Validações relacionadas ao formato dos dados recebidos.

Exemplos:

* campo obrigatório;
* tipo do campo;
* formato;
* tamanho;
* estrutura da requisição.

No projeto base, o schema é um arquivo JSON Schema em `src/schemas/`, conferido antes da primeira linha da rota. Formato errado responde 400.

| Campo | Validação |
| --- | --- |
| `documento` | obrigatório; CPF `000.000.000-00` ou CNPJ `00.000.000/0000-00`, com a máscara, como na base, e dígitos só de `0` a `9` (DD28); no CNPJ, as 12 primeiras posições aceitam também letras de `A` a `Z`, e os dígitos verificadores continuam numéricos (DD37) |
| `nome` | obrigatório; de 1 a 255 caracteres, com pelo menos um que não seja espaço e sem caractere de controle ou Unicode inválido; os espaços das pontas são removidos antes de gravar (DD37) |
| `proprietario_chave` | obrigatório; UUID na forma canônica em minúsculo, como a API emite (fora disso, 400) |
| `{chave}` (caminho) | UUID da conta, da cobrança ou da transação, conforme a rota (T28); fora do formato canônico em minúsculo (inclusive com espaço no fim, que o `CHAR(36)` ignoraria na comparação), é tratada como inexistente: 404, conferido antes de consultar o banco (DD09) |
| `imovel_referencia` | obrigatório; as mesmas regras do `nome`, e a unicidade por proprietário (RN09) vale depois de tirar os espaços das pontas (DD37) |
| `politica_imputacao_chave` | obrigatório; UUID (DD08) |
| `taxa_administracao_bps`, `multa_bps`, `juros_mensal_bps` | obrigatórios; inteiros sem casa decimal (`1000.0` é recusado, DD28); a faixa de 0 a 10000 é regra de negócio (RN10) |
| `valor_centavos` | obrigatório; inteiro sem casa decimal (`150000.0` é recusado) e no máximo 9007199254740991 (DD28); no repasse, é o valor bruto. O valor menor ou igual a zero é regra de negócio (422, DD06) |
| `competencia` | obrigatório na cobrança; `AAAA-MM` |
| `vencimento` | obrigatório na cobrança; data no formato `AAAA-MM-DD` |
| `itens` | obrigatório na cobrança; lista não vazia de `natureza` (`aluguel`, `condominio`, `iptu` ou `despesa_extra`, T36) e `valor_centavos` inteiro |
| `pago_em` | obrigatório no recebimento; data no formato `AAAA-MM-DD` |
| `natureza` (encargo) | obrigatório; `condominio` ou `iptu` |
| `natureza` (item incluído depois) | obrigatório; `despesa_extra` (T36) |
| `data` (consulta da cobrança) | opcional; `AAAA-MM-DD` |
| `Idempotency-Key` (header) | obrigatório e não vazio nas quatro rotas de movimento (recebimento, encargo, repasse e estorno); sem ele, 400 (T32) |
| `cursor`, `limite`, `natureza` (extrato) | opcionais; `cursor` no formato UUID canônico, em minúsculas (DD27); `limite` inteiro de 1 a 50; `natureza` entre as oito da 12.5; nenhum outro parâmetro aceito |

---

## 10.2 Regra de negócio

Validações que dependem do estado ou das relações do sistema.

Exemplos:

* conta existe;
* saldo disponível;
* conta pertence ao cliente;
* transferência permitida;
* recurso pertence ao solicitante.

| Regra | Onde será aplicada? |
| --- | --- |
| Dígitos verificadores do documento | Controller, no cadastro |
| Proprietário e política de imputação existem | Controller, na abertura de conta |
| Taxa, multa e juros entre 0 e 10000 bps (RN10) | Controller, na abertura de conta |
| Conta existe | Controller, em todas as rotas com `/contas/{chave}` no caminho |
| Cobrança existe | Controller, em todas as rotas com `/cobrancas/{chave}` no caminho; no recebimento, a conta travada é a da cobrança |
| Valor maior que zero em toda operação com valor | Controller (422, então é regra de negócio e não de formato; DD06) |
| Valor dentro do devido na data do pagamento: aberto + multa + juros (RN12 e T35) | Controller, com a conta travada |
| Multa uma vez e juros pro rata die (RN14), pela fórmula da DD20 | Controller, no recebimento e na consulta da cobrança |
| `pago_em` nem no futuro nem antes de um recebimento não estornado da cobrança (DD21) | Controller, no recebimento, com a conta travada |
| Encargo que não fica completo continua reservado (RN13) | Controller, na imputação |
| Disponível suficiente para o repasse (RN01 e RN11) | Controller, depois do `SELECT ... FOR UPDATE`, dentro da transação de banco |
| Reservado da natureza suficiente para o encargo (RN11) | Controller, somando os lançamentos da natureza com a conta travada |
| Item novo só em cobrança não quitada (RN15) | Controller, na inclusão de item (`POST /cobrancas/{chave}/itens`) |
| Estorno só de transação não estornada e que não é um estorno (DD04) | Controller, com a conta travada, e o banco, com a restrição UNIQUE em `transacao_estornada_id` |
| Estorno de recebimento só do último não estornado da cobrança (DD35) | Controller, com a conta travada |
| Estorno não deixa negativo o disponível nem o reservado de nenhuma natureza (RN01 e DD33) | Controller, com a conta travada |
| Unicidade de documento, de conta por imóvel e de chave de idempotência (RN08, RN09, RN03) | Banco, com restrições UNIQUE; o controller só traduz a violação em 409. A repetição da mesma requisição é respondida antes, com 200, pela consulta com a conta travada (DD18) |
| Ordem de imputação (RN05) | Controller, lendo a política versionada da conta |
| Cursor do extrato é um lançamento da conta, da natureza filtrada e o último da sua transação dentro do filtro (DD27) | Controller, no extrato; senão, 400 (`QIT000001`) |
| Recurso pertence ao solicitante | Controller; recurso de outro dono responde 404, igual ao inexistente (T33). Na Fase 1, com o `INTERNAL-TOKEN` único, não há dono de quem chama |

---

## 11. Decisões de arquitetura

Registrar decisões que afetarão a implementação.

## 11.1 Camadas

```text
API
 ↓
Controller
 ↓
Repository
 ↓
Database
```

Ou, caso exista outra camada:

```text
API
 ↓
Controller
 ↓
Service
 ↓
Repository
 ↓
Database
```

### Decisão a respeito das camadas

> **Decisão (Time, T34):** seguir as camadas do projeto base, sem camada de Service. Os middlewares cuidam do que vale para toda requisição (identificador da requisição, log, `INTERNAL-TOKEN` e o ciclo de vida da sessão de banco).
>
> ```text
> Requisição ──> middlewares ──> resource (o schema valida o formato) ──> controller ──> repository ──> models ──> PostgreSQL
> ```
>
> Os controllers concentram as regras de negócio e as validações que dependem do banco; os repositories só acessam o banco e nunca guardam regra financeira; os resources e os schemas cuidam da representação HTTP; e os middlewares, do ciclo da requisição e da sessão de banco. O commit continua no controller, como na base.

### Justificativa das camadas utilizadas

> É a arquitetura que o projeto base já traz e documenta (`docs/como-o-projeto-e-organizado.md`), e é o padrão dos serviços da QI Tech. Cada camada tem um trabalho só, e a seta anda num sentido. O controller já concentra as regras de negócio e o commit, então um Service seria uma camada a mais sem trabalho próprio nesta fase.

---

## 11.2 Responsabilidade de cada camada

| Camada | Responsabilidade | O que NÃO deve fazer |
| --- | --- | --- |
| Schema | Definir o formato do que entra (JSON Schema) e recusar o que está fora dele, com 400 | Consultar o banco; decidir regra de negócio |
| Controller | Aplicar as regras de negócio, tomar a trava, chamar os repositories e decidir o `commit` | Escrever consulta SQL; conhecer HTTP |
| Resource | Receber a requisição, chamar um controller e devolver a resposta com o status HTTP | Ter regra de negócio ou SQL; levantar erro (quem recusa é o schema ou o controller) |
| Repository | Buscar, inserir e atualizar no banco, incluindo o `SELECT ... FOR UPDATE` | Decidir se a operação era permitida |
| Model | Descrever as tabelas em Python | Conter regra de negócio |

---

## 12. Modelo de dados

Somente após fechar o domínio e as regras, definir as estruturas persistidas.

Modelo do RFC com as decisões do time. Em todas as tabelas, `id` é a chave interna (`bigserial`) e nunca sai na resposta, e a `chave` pública é um UUID gerado na aplicação e guardado em `char(36)` (DD13). O diagrama está em `docs/rfc/orca-modelo-dados.erd.json` (abre no ERD Editor).

## 12.1 Cliente

Na ORCA, o cliente é o **proprietário**.

```text
Proprietario
- id           bigserial    PK interna
- chave        char(36)     UNIQUE, identificador público
- documento    varchar(18)  UNIQUE, unicidade do cadastro; CPF ou CNPJ, numérico ou alfanumérico, com a máscara (DD13 e DD37)
- nome         text
- criado_em    timestamptz
```

## 12.2 Conta

```text
Conta
- id                      bigserial    PK interna
- chave                   char(36)     UNIQUE, identificador público
- proprietario_id         bigint       FK para Proprietario
- imovel_referencia       text         UNIQUE junto com o proprietário: uma conta por imóvel e proprietário
- saldo_disponivel        bigint       o que pode ser repassado; trava e validação do repasse (T13); de 0 a 9007199254740991 (DD37)
- saldo_reservado         bigint       o que está guardado para encargos; trava e validação do pagamento de encargo (T13); de 0 a 9007199254740991 (DD37)
- taxa_administracao_bps  int          taxa de administração em pontos-base
- multa_bps               int          multa do contrato de locação, em pontos-base (T18)
- juros_mensal_bps        int          juros mensais do contrato de locação, em pontos-base (T18)
- politica_id             bigint       FK para Politica_imputacao
- criado_em               timestamptz
```

O `saldo_centavos` único do RFC foi substituído por `saldo_disponivel` e `saldo_reservado` (T13).

## 12.3 Transação

```text
Transacao
- id                  bigserial    PK interna
- chave               char(36)     UNIQUE, identificador público
- conta_id            bigint       FK para Conta
- tipo                text         recebimento, encargo, repasse ou estorno (T22)
- transacao_estornada_id  bigint  FK para Transacao; preenchida só no estorno; UNIQUE, então uma transação é estornada no máximo uma vez (DD04)
- cobranca_id         bigint       FK para Cobranca; a cobrança que o recebimento pagou, preenchida só no recebimento (T29)
- chave_idempotencia  text         UNIQUE por conta; barra o reenvio
- hash_requisicao     char(64)     SHA-256 da rota, da chave do caminho e do corpo; separa a repetição idêntica da chave reutilizada (DD18)
- resultado           jsonb        resposta guardada para a repetição idêntica
- pago_em             date         data efetiva do pagamento; obrigatória no recebimento e vazia nos outros tipos (DD19)
- criado_em           timestamptz  quando foi registrada
```

O `cobranca_id` liga o recebimento inteiro à cobrança, inclusive os lançamentos de multa e juros, que não quitam nenhum item e por isso não têm `item_cobranca_id`. É por ele que a API sabe se a multa daquela cobrança já foi cobrada (RN14).

## 12.4 Transferência

Não existe uma tabela de transferência. O repasse é uma **Transação** do tipo `repasse`, e os valores ficam nos **Lançamentos** dela: o repasse, com o líquido, e a taxa, quando a taxa pendente é maior que zero (DD34).

## 12.5 Lançamento

```text
Lancamento
- id              bigserial    PK interna
- chave           char(36)     UNIQUE; é também o cursor do extrato (DD27)
- transacao_id    bigint       FK para Transacao
- conta_id        bigint       FK para Conta
- natureza        text         aluguel, condominio, iptu, despesa_extra, multa, juros, taxa ou repasse
- valor_centavos  bigint       sinalizado, nunca alterado
- item_cobranca_id  bigint     FK para Item_cobranca; o item que o lançamento quitou, quando houver (T25)
- criado_em       timestamptz
```

A natureza decide em qual saldo o lançamento conta: condomínio e IPTU no reservado; aluguel, multa, juros, `despesa_extra`, taxa e repasse no disponível (T13 e T39).

## 12.6 Política de imputação

```text
Politica_imputacao
- id               bigserial    PK
- chave            char(36)     UNIQUE, identificador público (DD08)
- nome             text
- versao           int          UNIQUE junto com o nome (nome, versao), para que cada política tenha a sua v1; versionada, nunca editada no lugar (derivado, aguarda revisão)
- ordem_naturezas  jsonb        a ordem em que o valor recebido quita as naturezas; na v1: juros, multa, condominio, iptu, aluguel, despesa_extra (T39 e DD24)
- vigente_desde    timestamptz
```

A política padrão nasce no `database.sql`, com versão 1 e chave fixa, e não tem rota de criação na Fase 1 (T41):

```text
database.sql
     ↓
Política padrão v1
     ↓
POST /contas
     ↓
conta.politica_id
     ↓
política usada na imputação
```

## 12.7 Cobrança e itens

Campos decididos pelo time (T14 e T25). O que está em aberto numa cobrança não é guardado: é o valor devido de cada item menos a soma dos lançamentos que apontam para ele, contando só os recebimentos não estornados (DD35). A cobrança está quitada só quando nada mais é devido: nenhum item em aberto e nenhuma multa ou juros pendentes (T43).

```text
Cobranca
- id               bigserial    PK interna
- chave            char(36)     UNIQUE, identificador público
- conta_id         bigint       FK para Conta
- competencia      text         o mês de referência (por exemplo, AAAA-MM); UNIQUE junto com a conta
- vencimento       date         base da multa e dos juros (RN14)
- criado_em        timestamptz

Item_cobranca
- id                     bigserial    PK interna
- cobranca_id            bigint       FK para Cobranca
- natureza               text         aluguel, condominio, iptu ou despesa_extra (T36)
- valor_devido_centavos  bigint       quanto é devido dessa natureza na competência
- criado_em              timestamptz
```

---

## 13. Decisões em aberto

Tudo que ainda não foi decidido deve ficar explícito.

| ID | Questão | Responsável | Status |
| --- | --- | --- | --- |
| | Nenhuma decisão em aberto. | | |

As questões D01 a D28 estão fechadas (seção 14). Os detalhes derivados DD01 a DD10 aguardam a revisão do time. Os DD11 a DD30 foram aprovados pelo time em 28/09/2026, menos os complementos marcados como *derivado, aguarda revisão*. As DD31 a DD36 e a DD38 foram derivadas na implementação e também aguardam revisão, menos a DD35 (a) e a compensação da DD26, aprovadas pelo time em 28/09/2026. A DD37 reúne decisões do time de 29/09/2026 (fim da seção 14).

> **Regra:** uma decisão em aberto não deve ser escondida dentro do código.

---

## 14. Decisões tomadas

Registrar decisões importantes para evitar que sejam revistas acidentalmente.

Os IDs começam com **T**. Entre parênteses, o ID da questão em aberto que a decisão fechou.

| ID | Decisão | Motivo | Data |
| --- | --- | --- | --- |
| T01 | O saldo é **materializado** na conta e só muda na mesma transação de banco que grava os lançamentos | Descartada: saldo como soma dos lançamentos, sem campo, porque não elimina a trava (em READ COMMITTED, dois SUM concorrentes leem o mesmo snapshot e ambos aprovam) e faz cada débito custar o histórico inteiro | 20/09/2026 |
| T02 | **Trava pessimista** (`SELECT ... FOR UPDATE`) na linha da conta, tomada antes da validação e mantida até o commit | Impede que duas requisições leiam o mesmo saldo e as duas passem; serializa a conta, não o sistema | 20/09/2026 |
| T03 | **Idempotência** pela `Idempotency-Key`, numa coluna com restrição UNIQUE por conta, com o resultado original guardado | O banco decide, e não um `if` com janela de corrida; a repetição idêntica devolve o mesmo resultado sem novo efeito | 20/09/2026 |
| T04 | **Política de imputação versionada**, como dado apontado pela conta, e não como código | A lei só resolve parte da ordem (juros antes do capital); o rateio aplicado fica nos lançamentos, e extratos antigos continuam explicáveis | 20/09/2026 |
| T05 | A **taxa de administração é um lançamento próprio** | Descartada: tarifa embutida no valor do repasse, porque o extrato mostraria um líquido que ele mesmo não explica, e a lei exige discriminação | 20/09/2026 |
| T06 | **Uma conta por proprietário e imóvel** | Descartada: uma conta única da administradora com a posição calculada no relatório, porque nada impediria um repasse de consumir dinheiro alheio | 20/09/2026 |
| T07 | Encargos pagos ao credor **integralmente** | Descartado: rateio proporcional do pagamento parcial, porque condomínio e IPTU ficariam pagos pela metade, e nenhum credor aceita fração | 20/09/2026 |
| T08 | **Chave pública (UUID)** em todas as rotas; o id interno nunca é aceito nem devolvido | Descartado: expor o id serial, porque revela o volume de registros e quebra se a base for migrada | 20/09/2026 |
| T09 | Dinheiro em **inteiro de centavos** e percentuais em **pontos-base** | Descartado: decimal flutuante, porque acumula erro; com inteiro, o centavo não some nem duplica | 20/09/2026 |
| T10 | **Lançamentos imutáveis** | O histórico precisa reconstruir o saldo; alterar um lançamento quebraria a invariante | 20/09/2026 |
| T11 | Extrato **paginado por cursor**, do mais recente para o mais antigo, sem cortar uma transação entre páginas | Páginas estáveis mesmo com lançamentos novos entrando, e o rateio de cada transação sempre inteiro | 20/09/2026 |
| T12 (D17) | O domínio é a **administradora de aluguel** | É onde está o rateio entre aluguel, condomínio e IPTU, o pedaço do problema que resiste | 23/09/2026 |
| T13 (D05) | **Dois saldos na conta**, `saldo_disponivel` e `saldo_reservado`, para controle e trava; a composição do reservado vive nos lançamentos | Descartadas: uma coluna por natureza, porque cada natureza nova vira migração; e lançamentos de reserva movendo valor entre os saldos, porque dobram os lançamentos sem informação nova | 23/09/2026 |
| T14 (D01) | **Entidade cobrança**, com itens por natureza | Descartado: valores informados no próprio recebimento, que ganharia se todo pagamento fosse integral e no prazo; o sistema não lembraria do que sobrou, e o pagamento seguinte não teria onde continuar | 23/09/2026 |
| T15 (D02) | A **tarifa é retida no repasse** | Descartada: tarifa no recebimento, porque cobraria taxa sobre o dinheiro do síndico e da prefeitura, que só está de passagem | 23/09/2026 |
| T16 (D03) | **Tarifa por dentro:** o operador pede o bruto, e a API devolve a taxa e o líquido | Descartada: tarifa por fora, porque o débito real ultrapassaria o valor pedido, e a validação de saldo seria sobre um número que o cliente não mandou | 23/09/2026 |
| T17 (D04) | `taxa = ⌊valor × taxa_bps ÷ 10000⌋`, **truncada para baixo**, com a sobra sempre com o proprietário | Descartado: arredondar para o mais próximo, porque a sobra mudaria de dono conforme o valor | 23/09/2026 |
| T18 (D16) | **Multa e juros por fórmula parametrizada na conta** (`multa_bps`, `juros_mensal_bps`), definida pelo contrato de locação: a multa incide uma vez sobre o aberto no vencimento, e os juros correm pro rata die sobre o aberto; um segundo pagamento não gera multa nova | Justificativa de engenharia: a multa é uma por dívida, não uma por pagamento; os juros são proporcionais ao período; nenhum dos dois é recalculado sobre valor já quitado. A única referência legal é o Código Civil, art. 354, que trata da ordem de imputação e não da fórmula | 23/09/2026 |
| T19 (D06) | **Recebimento acima do aberto é recusado com 422** na Fase 1 (o aberto inclui a multa e os juros da data do pagamento, T35); o excedente fica fora do sistema e é tratado pelo operador | Descartado: excedente como crédito para a competência seguinte, que ganharia se adiantamento fosse prática comum, mas exigiria natureza de crédito, regra de consumo em competências futuras e um estado novo | 23/09/2026 |
| T20 (D07) | O **encargo aceita valor parcial**, que fica reservado até completar; a imputação não pula para a próxima natureza | Descartado: pular para a próxima natureza, porque o condomínio ficaria descoberto enquanto o aluguel é pago | 23/09/2026 |
| T21 (D18) | A **despesa lançada depois da emissão** entra como item novo na cobrança enquanto ela não está quitada; numa cobrança quitada, a inclusão é recusada com 409, e o item vai para a competência seguinte | Descartada: cobrança avulsa, porque criaria dois tipos de cobrança e a imputação teria de escolher entre duas abertas | 23/09/2026 |
| T22 (D08) | A correção de uma operação é uma **transação de estorno**, pelo mesmo fluxo idempotente das outras transações (`Idempotency-Key`, resultado guardado, trava na conta), com lançamentos de sinal invertido que apontam para a transação original; a correção manual fica fora da Fase 1 | Mantém os lançamentos imutáveis (T10) e reaproveita a garantia contra reenvio (T03) | 23/09/2026 |
| T23 (D13) | O **credor do encargo não é guardado** | A natureza já diz para quem é o pagamento | 23/09/2026 |
| T24 (D14) | **Corrigir a frase do RFC, não o modelo:** toda transação tem pelo menos um lançamento, e a soma dos lançamentos da transação é igual ao valor dela | O pagamento de encargo gera um lançamento só, e o modelo já comporta isso | 23/09/2026 |
| T25 (D19) | A cobrança entra por **duas rotas**: `POST /cobrancas` (hoje `POST /contas/{chave}/cobrancas`, T28) cria a cobrança da competência com os itens, e `POST /cobrancas/{chave}/itens` inclui um item depois; o lançamento aponta para o item que quitou (`item_cobranca_id`) | Descartadas: cobrança automática a partir de valores fixos na conta, porque o reajuste fica de fora e a despesa extra ainda precisaria de uma rota; e uma rota só, porque a despesa lançada depois viraria cobrança avulsa, contra T21 | 23/09/2026 |
| T26 (D20) | Política de retry do conector **fora da Fase 1**: nenhuma chamada ao conector é reenviada automaticamente | Já está no quadro do que a ORCA não resolve agora, e não disputa saldo | 23/09/2026 |
| T27 | A taxa de administração incide **só sobre o aluguel**, e não sobre multa e juros | Descartado: incidir sobre todo o valor repassado, que seria mais simples, mas faria a administradora ganhar também sobre multa e juros. Mantém o que o RFC já dizia ("sobre o aluguel efetivamente quitado") | 23/09/2026 |
| T28 | **Rotas organizadas pelo recurso dono:** o que pertence à conta fica em `/contas/{chave}/...` (cobranças, pagamento de encargo e repasse), e o que pertence à cobrança fica em `/cobrancas/{chave}/...` (itens e recebimentos); o recebimento passa a ser `POST /cobrancas/{chave}/recebimentos`, sem `conta_chave` nem `competencia` no corpo; e entra a rota `GET /cobrancas/{chave}`, com o devido, o pago e o aberto de cada item | Descartado: as rotas soltas do RFC, com a `conta_chave` no corpo, porque misturavam dois padrões (leituras dentro da conta, escritas fora dela), e o operador não tinha como consultar o que está em aberto antes de um recebimento que responde 422 acima dele. Com a chave no caminho, o "404 conta inexistente" fica igual em todas as rotas, e a verificação de acesso (T33) acontece num lugar só | 24/09/2026 |
| T29 | A **transação de recebimento aponta para a cobrança** que pagou (`transacao.cobranca_id`, preenchida só no recebimento) | Descartado: chegar à cobrança só pelos lançamentos (`item_cobranca_id`), porque os lançamentos de multa e juros não quitam item e ficariam sem ligação com a cobrança; sem ela, a API não teria como saber se a multa daquela cobrança já foi cobrada (RN14: um segundo pagamento não gera multa nova) | 24/09/2026 |
| T30 (D09) | Cada conta tem uma **política de imputação associada** por `politica_id`, que decide a ordem e as regras da distribuição dos recebimentos; a abertura de conta referencia a política aplicável | Mantém a política explícita no modelo e permite políticas diferentes no futuro sem mudar a estrutura da conta | 24/09/2026 |
| T31 (D10) | **Catálogo único de erros no padrão `QIT` da base**: cada erro com código, mensagem e status HTTP (seção 7.1) | Evita que cada rota invente a própria representação de erro; o cliente programa em cima do código | 24/09/2026 |
| T32 (D11) | **Contrato das respostas pelo padrão da base**: extrato paginado com **limite máximo de 50** lançamentos por página; `Idempotency-Key` ausente é erro de requisição, pelo padrão de validação da base; os campos das respostas são definidos explicitamente no contrato, e não como proposta | Segue a validação que a base já adota | 24/09/2026 |
| T33 (D12) | **Recurso de outro dono responde 404**, igual ao inexistente, sem revelar que ele existe; na Fase 1, com o `INTERNAL-TOKEN` único, não há dono de quem chama | Compatível com a autorização da base, e a regra já vale quando o controle por perfil entrar | 24/09/2026 |
| T34 (D15) | **Camadas da base, sem Service**: controllers com as regras e as validações, repositories só com o acesso ao banco, resources e schemas com o HTTP, e middlewares com o ciclo da requisição | Nenhuma regra financeira dentro dos repositories; o controller já concentra as regras e o commit | 24/09/2026 |
| T35 (D16) | **O limite do recebimento é o devido na data do pagamento**: o aberto da cobrança mais a multa e os juros calculados para aquela data | Descartado: limitar ao aberto sem multa e juros, porque recusaria o pagamento correto de quem pagou atrasado | 24/09/2026 |
| T36 (D21) | A despesa lançada depois da emissão tem a **natureza `despesa_extra`**, no item e no lançamento; a taxa de administração não incide sobre ela (T27) | Descartado: uma natureza para cada tipo de despesa (reparo, taxa extraordinária), porque cada tipo novo viraria mudança de estrutura | 24/09/2026 |
| T37 (D22) | O **estorno segue o fluxo idempotente** das demais operações: nova transação, `Idempotency-Key`, resultado guardado, conta travada e lançamentos vinculados à transação original (T22) | Uma mesma solicitação de estorno nunca é processada duas vezes | 24/09/2026 |
| T38 (D23) | A **taxa incide sobre o aluguel efetivamente quitado**, e não sobre o valor do repasse pedido: `taxa pendente = ⌊SUM(aluguel recebido) × bps ÷ 10000⌋ − SUM(taxa já retida)`, derivada dos lançamentos e retida no repasse | Descartado: taxa sobre o valor de cada repasse, porque ela variaria com a quantidade e o tamanho dos repasses | 24/09/2026 |
| T39 (D24) | A **`despesa_extra` conta no `saldo_disponivel`** e ocupa a **última posição da ordem de imputação**: juros, multa, encargos, aluguel, despesa extra. Ela é tratada como uma dedução da posição disponível do proprietário, e não como valor provisionado para uma rota de encargos; condomínio e IPTU continuam no reservado | Descartado: o reservado, porque a Fase 1 não tem rota que pague despesa extra pelo fluxo de encargos, e o valor ficaria preso | 24/09/2026 |
| T40 (D25) | **Repasse com valor bruto menor que a taxa pendente é recusado com 422** (`QIT001026`), e na igualdade também (DD25), sem nenhum lançamento: não há retenção parcial da taxa, e ela não é dividida entre repasses | A taxa continua retida uma vez só (T38), e a API não executa um repasse cujo líquido para o proprietário seria zero ou negativo | 24/09/2026 |
| T41 (D26) | A **política de imputação padrão é criada no `database.sql`**, pelo mecanismo de inicialização do banco da base, com versão 1 e uma chave UUID fixa; a abertura de conta usa essa política como referência | Evita criar uma rota só para administrar uma entidade que não precisa ser configurável na Fase 1, e garante que toda conta tenha uma política válida | 24/09/2026 |
| T42 (D27) | Um **item incluído depois do vencimento** (a despesa extra da T21) entra na multa e nos juros, desde que já faça parte da cobrança no momento do pagamento, **sem encargos retroativos**: a data de referência dos encargos dele é a da inclusão, e os juros correm a partir dela. Exemplo: vencimento em 10/09, aluguel de R$ 2.000,00 já na cobrança, despesa extra de R$ 300,00 incluída em 20/09 e pagamento em 25/09. O aluguel tem multa e juros desde 10/09; a despesa extra não recebe encargos de 10/09 a 20/09 | Descartado: tratar o item como se existisse desde o vencimento, porque a administradora poderia criar uma despesa hoje e o sistema cobraria juros de um período em que ela não existia | 28/09/2026 |
| T43 (D28) | **Multa e juros que um recebimento não cobre continuam devidos** e permanecem no saldo da cobrança. O recebimento é imputado na ordem da política; o que sobra de multa e juros entra na imputação do recebimento seguinte. Multa e juros **não viram principal**, então não geram juros. A cobrança só está **quitada** quando todos os valores devidos (itens, multa e juros) foram cobertos. Exemplo: principal de R$ 2.000,00, multa de R$ 40,00 e juros de R$ 6,66 somam R$ 2.046,66; um pagamento de R$ 2.020,00 deixa valor devido, e a cobrança não fica quitada | Descartado: perdoar o que o pagamento não cobre, porque um pagamento pequeno apagaria a multa; e somar multa e juros ao principal, porque criaria juros sobre juros | 28/09/2026 |

### Detalhes derivados e decisões de implementação

Os itens DD01 a DD10 **não são decisões novas de modelagem**: são detalhes de contrato que completam as decisões acima seguindo o padrão que a base já adota, ou uma decisão já tomada, e aguardam a revisão do time.

Os itens DD11 a DD30 são decisões de escopo (DD11), de modelo (DD13, DD18 e DD19), de regra (DD20 a DD26) e de implementação, aprovadas pelo time em 28/09/2026, antes do início da implementação. Elas seguem a base, a implementação de referência da QI Tech (`bootcamp-biblioteca-api`) ou uma decisão já tomada. Onde um item vai além do que foi aprovado, o complemento aparece marcado como *derivado, aguarda revisão*.

| ID | Detalhe | Derivado de |
| --- | --- | --- |
| DD01 | Os códigos do projeto são numerados a partir de `QIT001008` (de `QIT001008` a `QIT001029`), e os dois 409 de saldo têm códigos diferentes (disponível e reservado) | Guia da base: "o próximo livre é o `QIT001008`"; T31 |
| DD02 | Documento com o formato certo e os dígitos verificadores errados responde **422** (`QIT001008`), e não 400 | Base: o `InvalidDocumentNumber` responde 422 ("li, entendi, e esse valor não pode existir") |
| DD03 | `limite` do extrato acima de 50 responde **400** (`QIT000001`), porque é barrado no schema; sem o parâmetro, o padrão é 10 | Base: o schema de listagem barra o `limit` pelo `pattern`, e o padrão é 10; T32 |
| DD04 | Estorno em `POST /transacoes/{chave}/estornos`, sem corpo e sempre da transação inteira (inverte todos os lançamentos); uma transação é estornada no máximo uma vez (UNIQUE em `transacao_estornada_id`), e um estorno não é estornado | T28 (o estorno pertence à transação), T22 e T37 (lançamentos invertidos), T10 (a original não muda) |
| DD05 | `GET /cobrancas/{chave}` aceita `?data=AAAA-MM-DD` (padrão: hoje) e devolve a multa, os juros e o total devido naquela data | T35: sem isso, o operador não saberia o limite do recebimento antes de registrá-lo |
| DD06 | Valor menor ou igual a zero responde **422** (`QIT001018`) em toda operação com valor, não só no recebimento | RFC: 422 no recebimento; mesma regra nas outras operações |
| DD07 | `multa_bps` e `juros_mensal_bps` aceitam de 0 a 10000, a mesma faixa da taxa (RN10) | RN10 |
| DD08 | Na API, a política é identificada pela `chave` pública dela (`politica_imputacao_chave`); a política inexistente responde 404 (`QIT001014`) | T08: nenhuma rota aceita o id interno; T30 |
| DD09 | Uma `{chave}` fora do formato UUID no caminho é tratada como inexistente: **404** | Base: a chave no caminho não é validada no schema, e a entidade não encontrada responde 404 |
| DD10 | Data com o formato certo que não existe no calendário responde **422** (`QIT001025`); documento com a máscara de CPF ou CNPJ | Base: `InvalidBirthdate` (422) e o `pattern` do documento |
| DD11 | **Nível de controle da Fase 1: nível 1, só registro.** A ORCA não executa a transferência bancária: registra a obrigação, calcula o disponível para repasse, aplica as regras e registra o repasse realizado. Controla a posição financeira e a decisão operacional, não o dinheiro físico. É decisão de escopo, explicada em 1.3 | Decisão do time em 28/09/2026, para a defesa na banca (1.3); a execução de PIX, TED e boleto fica fora da Fase 1 (1.2) |
| DD12 | **Arquitetura e testes da implementação de referência da QI Tech:** rotas com `add_api_route` no `app.py`; pastas `resources`, `schemas`, `controllers`, `repositories`, `models`, `dtos`, `errors` e `utils`, além dos `middlewares` da base; sem camada de domínio, service, repository genérico ou factory. Desenvolvimento em TDD, com testes de integração por HTTP que não importam `src/` | T34; regra R1 da Aula 3 (teste de caixa-preta); `bootcamp-biblioteca-api` |
| DD13 | **Tipos no banco:** a `chave` em `CHAR(36)`, com UUID v4 gerado na aplicação (menos a da política padrão, fixa no `database.sql`, T41); `BIGSERIAL` nos ids; `BIGINT` nos centavos; `TIMESTAMPTZ` nos instantes (`criado_em`, `vigente_desde`) e `DATE` nas datas de calendário (`vencimento`, `pago_em`); o `documento` em `VARCHAR(18)`, o tamanho do CNPJ com máscara | Base: `CHAR(36)` e `uuid4` no repository. Com o tipo `UUID` do Postgres, uma chave malformada no caminho daria 500, e não o 404 da DD09; T08 e T09 |
| DD14 | **Nomes no código:** o domínio em português, igual ao contrato (`Conta`, `saldo_reservado`, `receber`, `repassar`); os nomes técnicos no estilo da base (`on_post`, `create`, `get_by_chave_for_update`, `obj_to_dict`) | Seção 7 (contrato em português); padrão de nomes da base |
| DD15 | **A unicidade é decidida pelo banco:** cada restrição UNIQUE tem nome, e a violação (`IntegrityError`) é traduzida para o erro do catálogo (409), com `flush` antes do commit quando é preciso vê-la antes; a consulta prévia só serve para responder mais cedo. A UNIQUE da `Idempotency-Key` fica como rede: com a conta travada, a repetição é respondida antes pela DD18, e a violação, se ainda assim acontecer, responde 409 (`QIT001022`) | T03 ("o banco decide") e 8.4; na base, duas requisições iguais ao mesmo tempo terminam em 500 |
| DD16 | **A trava da conta é a primeira leitura dela na transação** (`SELECT ... FOR UPDATE`); cada operação trava uma conta só, e toda regra que depende do saldo é conferida depois da trava | T02; 3.3 (o repasse não tem conta de destino); na base, um objeto lido antes da trava volta com o valor antigo |
| DD17 | **As quatro operações que movem dinheiro** (recebimento, pagamento de encargo, repasse e estorno) ficam no `transacao_controller.py` e seguem o mesmo roteiro: conta travada, idempotência conferida com a conta travada, regras de negócio, lançamentos e saldos, e o commit como última operação. Nenhuma escrita acontece antes das regras, e qualquer falha desfaz tudo | T22, T24 e T37 (toda operação de dinheiro é uma transação); T34; a idempotência vem depois da trava para que uma repetição concorrente espere a primeira e receba o resultado dela (DD29) |
| DD18 | **Idempotência com o hash da requisição:** `transacao.hash_requisicao` (`CHAR(64)`) guarda o SHA-256 da rota, da chave do caminho e do corpo em JSON canônico. Mesma chave com hash igual devolve o resultado guardado (200); com hash diferente, 409 (`QIT001022`). Uma operação que falha é desfeita inteira, inclusive a linha de idempotência, e um reenvio com a mesma chave executa de novo | T03 e 8.4 (comparar a requisição); a rota e a chave do caminho entram no hash porque o estorno não tem corpo e a mesma chave, na mesma conta, pode chegar por outra rota; atomicidade (3.3 e 8.3) |
| DD19 | **`transacao.pago_em` (`DATE`)**: a data efetiva do pagamento, separada do `criado_em`, que é a data do registro; obrigatória no recebimento e vazia nos outros tipos | T18 e RN14: os juros dependem da data de cada pagamento |
| DD20 | **Fórmula da multa e dos juros.** A multa é o percentual `multa_bps` sobre o valor em aberto dos itens no vencimento, uma vez só. Os juros correm por dias corridos, com divisor de 30 dias, a partir da data mais recente entre o vencimento (ou a inclusão do item, T42) e o `pago_em` do último recebimento não estornado da cobrança, até o `pago_em` (na consulta da cobrança, até a `data`), sobre o valor em aberto dos itens (12.7), sem juros sobre juros nem sobre a multa. O arredondamento trunca uma vez. Exemplo: R$ 2.000,00 pagos 10 dias depois do vencimento, com multa de 2% e juros de 1% ao mês: multa `⌊200000 × 200 ÷ 10000⌋` = 4000 (R$ 40,00); juros `⌊200000 × 100 × 10 ÷ (10000 × 30)⌋` = 666 (R$ 6,66). Para um item incluído depois do vencimento, a data de referência dos encargos é a da inclusão (T42). A multa e os juros que um recebimento não cobre continuam devidos (T43) | T18, T35, T42, T43 e T17 (truncar para baixo) |
| DD21 | **`pago_em` no futuro, ou anterior a um recebimento não estornado já registrado na cobrança, responde 422** (`QIT001027`). *Derivado, aguarda revisão:* na consulta da cobrança, uma `data` anterior a esse recebimento responde o mesmo 422, e uma `data` no futuro é aceita, para o operador simular o devido | DD20: os juros por período dependem da ordem das datas |
| DD22 | **"Hoje" é a data de São Paulo** (`America/Sao_Paulo`): vale para o `GET /cobrancas/{chave}` sem `data` e para a checagem de `pago_em` no futuro | DD05; o servidor roda em UTC e viraria o dia às 21h |
| DD23 | **Status da cobrança calculado, sem coluna:** `aberta` (nada pago na cobrança), `parcial` (algo pago e ainda há valor devido) e `quitada` (nada mais devido: itens, multa e juros), no campo `status` do `GET /cobrancas/{chave}` | 12.7 (o aberto é calculado, não guardado); T14; T43 |
| DD24 | **Ordem dentro dos encargos: condomínio antes do IPTU.** A política v1 imputa juros, multa, condominio, iptu, aluguel e despesa_extra | T39 e T41; a ordem do exemplo da 7.2.3 |
| DD25 | **T40 na igualdade:** o repasse com valor bruto maior que zero e menor ou igual à taxa pendente responde 422 (`QIT001026`), porque o líquido seria zero ou negativo. O valor menor ou igual a zero é conferido antes e responde `QIT001018` (DD06) | T40 ("líquido zero ou negativo") |
| DD26 | **A taxa pendente nunca é negativa** (`max(0, ...)` sobre a fórmula da T38); o estorno de um recebimento cujo aluguel já teve a taxa retida não gera devolução automática da taxa. **Compensação (Time, 28/09/2026):** como a fórmula não guarda sobre qual aluguel cada taxa foi retida, a taxa retida sobre um aluguel estornado é descontada da taxa dos aluguéis que entrarem depois | T38 e T22 |
| DD27 | **O cursor do extrato é a chave do último lançamento da página.** *Derivado, aguarda revisão:* um cursor que não é um lançamento da conta responde 400 (`QIT000001`), porque o cursor é opaco para o cliente e um valor que a API não emitiu é tratado como parâmetro fora do formato, como o `limite` acima de 50 (DD03). O mesmo 400 vale para um lançamento da conta que não é o último da sua transação dentro do filtro pedido, porque começar dele partiria a transação (T11), e, quando há filtro de natureza, para um cursor de outra natureza. Todo cursor que a API emite passa nessas regras. Sem filtro, a API não distingue um cursor emitido com outro filtro que seja o último da sua transação, e o aceita como ponto de partida. Um cursor na linha mais antiga devolve a página vazia, com `proximo_cursor` nulo | T08 (o id interno não sai) e T11 |
| DD28 | **Validação de valores e documentos mais rígida que a da base:** centavos e pontos-base só como inteiro, sem casa decimal (`150000.0` e `1000.0` respondem 400); documentos e datas com `[0-9]` no padrão, e não `\d`. *Derivado, aguarda revisão:* o teto dos valores em centavos é 9007199254740991, o maior inteiro que um cliente JSON lê sem perder precisão. O valor menor ou igual a zero continua respondendo 422 (DD06) | T09; o `integer` do jsonschema aceita `150000.0`, e o `\d` aceita dígitos que não são de `0` a `9` |
| DD29 | **Testes de concorrência nas operações de dinheiro:** requisições em paralelo por HTTP provam que repasses simultâneos não deixam saldo negativo nem divergência entre saldo e extrato, e que duas requisições com a mesma `Idempotency-Key` produzem um efeito só | T01, T02 e T03; a base e a referência não têm teste de concorrência |
| DD30 | **Código sem comentários:** a intenção fica nos nomes, na estrutura e nos testes, e as decisões ficam neste documento e na descrição dos pull requests | Decisão de estilo do time para a implementação |
| DD31 | *Derivado, aguarda revisão:* **datas de referência dos encargos e competência.** Os itens enviados na criação da cobrança usam o vencimento como data de referência da multa e dos juros, mesmo que a cobrança seja registrada depois dele. Só o item incluído depois, pela 7.2.9, usa a data da inclusão (T42), que é a data de São Paulo do `criado_em` do item (DD22): a multa incide se o pagamento for depois dessa data, e os juros correm a partir dela. A competência com mês fora de 01 a 12 responde 422 (`QIT001025`), como uma data que não existe (DD10) | T42, DD10, DD20 e DD22 |
| DD32 | *Derivado, aguarda revisão:* **detalhes do recebimento.** (a) A `Idempotency-Key` tem de 1 a 255 caracteres; ausente, vazia ou maior responde 400 (`QIT000001`), conferida na camada de schema. (b) O `rateio` da resposta tem uma linha por lançamento, na ordem da imputação: juros, multa e uma linha por item que recebeu valor, de modo que duas despesas extras aparecem separadas; entre itens da mesma natureza, o incluído primeiro é pago primeiro. (c) O `em_aberto` inclui a multa e os juros que o recebimento não cobriu (T43), na ordem da política. (d) Os juros acumulam por trechos entre as datas dos recebimentos, sobre o aberto de cada trecho, e truncam uma vez sobre o total (DD20). (e) Data e hora nas respostas, como `ultimo_lancamento_em`, saem em UTC no formato `AAAA-MM-DDTHH:MM:SSZ`, como nos exemplos. (f) A inclusão de item (7.2.9) também trava a conta, porque decide pela posição da cobrança se ela está quitada (RN15). Com a conta travada, o recebimento e a inclusão releem os itens da cobrança, para enxergar um item incluído enquanto esperavam a trava. (g) Um item incluído depois da data do pagamento não entra na posição dessa data (T42): um recebimento com `pago_em` anterior à inclusão não é imputado nele, e a consulta da 7.2.10 com essa `data` não o mostra. (h) "Mesmo corpo" é o mesmo objeto JSON: a ordem das chaves pode mudar sem virar outra requisição. A restrição UNIQUE da chave de idempotência não é alcançada com a conta travada; se ainda assim disparar, responde 409 (`QIT001022`), nunca 500 | T03, T42, T43, DD16, DD18, DD20 e exemplos da seção 7 |
| DD33 | *Derivado, aguarda revisão:* **pagamento de encargo.** (a) O reservado de uma natureza é a soma dos lançamentos daquela natureza na conta, lida com a conta travada; um encargo acima dele responde 409 (`QIT001021`) mesmo que o `saldo_reservado` total cubra o valor (RN11). (b) A RN07 é garantida pela recusa inteira: o valor pedido é pago todo ou recusado, nunca em parte. A API não compara o valor com os itens da cobrança nem exige que o reservado da competência esteja completo, porque o valor cobrado pelo credor é informado pelo operador (T23). (c) O encargo gera um lançamento negativo da natureza paga, sem item, e não muda a posição da cobrança (7.2.10), que conta só os recebimentos. (d) O estorno (7.2.11) confere o reservado de cada natureza, e não só o `saldo_reservado` total, com o mesmo `QIT001021`: assim nenhuma natureza fica negativa, e a conferência do encargo pela natureza basta. (e) A soma dos lançamentos de uma transação é o valor pedido com o sinal do movimento: positiva no recebimento, negativa no encargo e no repasse, e a da original com o sinal trocado no estorno (RN16) | RN07, RN11, RN13, RN16, T07, T23 e 7.2.11 |
| DD34 | *Derivado, aguarda revisão:* **repasse.** (a) O repasse gera o lançamento `taxa`, negativo, só quando a taxa pendente é maior que zero, e o lançamento `repasse`, negativo, com o líquido. Sem taxa pendente (`taxa_administracao_bps` zero, ou taxa já retida), há um lançamento só, e a soma continua igual ao valor bruto (RN16); a restrição `valor_centavos <> 0` não admite lançamento zerado. (b) A taxa já retida é a soma dos lançamentos `taxa` da conta com o sinal trocado, então o estorno de um repasse, com o lançamento `taxa` positivo, a devolve à taxa pendente. (c) A taxa é calculada em inteiro, sem ponto flutuante, e fora do SQL: com valores perto do teto da DD28, o produto pelos pontos-base passa do `BIGINT`. (d) Ordem das conferências: valor menor ou igual a zero (422 `QIT001018`), disponível insuficiente (409 `QIT001020`) e valor menor ou igual à taxa pendente (422 `QIT001026`), como no 8.4, que verifica o saldo antes de calcular a tarifa. Sem estorno, a taxa pendente nunca passa do disponível, e os dois últimos não coincidem. Depois de um estorno, ela pode passar: nesse caso, o disponível menor ou igual à taxa pendente fica na conta até entrar mais dinheiro (T40). (e) Com taxa de 10000 bps, um disponível feito só de aluguel não sai da conta, porque todo repasse até ele fica menor ou igual à taxa pendente (T40); a taxa de 100% só é retida junto com dinheiro que não é aluguel. É efeito aceito da T40, sem mudar a RN10. (f) A mesma `Idempotency-Key` usada em outra operação da mesma conta (recebimento, encargo ou repasse) responde 409 (`QIT001022`), porque a operação entra no hash (DD18); em outra conta, é outra operação | RN10, RN16, T16, T38, T40, DD18, DD25, DD26 e DD28 |
| DD35 | **Estorno.** (a) *Aprovado pelo time em 28/09/2026:* só o último recebimento não estornado da cobrança, na ordem do `pago_em` e do registro, pode ser estornado; estornar um anterior responde 409 (`QIT001028`). Estornar um anterior deixaria os posteriores imputados fora da ordem da política (RN05, RN13 e T20) e moveria dinheiro dos encargos para o disponível. O operador estorna do mais recente para o mais antigo e registra de novo, com outra chave, os recebimentos que valem. *Derivado, aguarda revisão, de (b) a (f):* (b) A posição da cobrança ignora por inteiro o recebimento estornado e o estorno dele: o valor pago por item, a multa e os juros pagos, os trechos da DD20, a ordem da DD21, o status da DD23 e a RN15. A cobrança volta à posição que teria sem ele. (c) A conferência olha o saldo atual: o disponível travado mais a soma invertida, e o reservado de cada natureza (DD33). Ordem: 400 do header, 404 (`QIT001023`), trava, 200 ou 409 (`QIT001022`), 409 (`QIT001024`), 409 (`QIT001028`), 409 (`QIT001020`) e 409 (`QIT001021`), com o condomínio antes do IPTU. (d) Os lançamentos invertidos são gravados na ordem de criação da original, e a resposta os lista na ordem do extrato, como no exemplo da 7.2.11. O `item_cobranca_id` copiado serve à rastreabilidade (T22 e T25), e não ao cálculo; nenhuma rota o mostra. (e) Um corpo enviado ao estorno é ignorado e não entra no hash, que é da operação e da chave da transação (DD18). (f) O estorno de um repasse devolve a taxa dele à taxa pendente (DD34), e o de um encargo devolve o valor ao reservado da natureza | T10, T20, T22, T25, T37, RN05, RN13, DD04, DD18, DD20, DD21, DD23, DD26, DD33 e DD34 |
| DD36 | *Derivado, aguarda revisão:* **extrato.** (a) A ordem do extrato é a ordem de registro na conta (o id), serializada pela trava da DD16. O `criado_em` é o instante em que a operação começou, com precisão de segundos, e pode não acompanhar essa ordem entre operações concorrentes; por isso o `ultimo_lancamento_em` da 7.2.7, que é o maior `criado_em`, pode diferir do `criado_em` da primeira linha. (b) O `limite` de 1 a 50 é o teto do parâmetro, e não das linhas: a página tem até `limite` linhas mais o resto da última transação, e uma transação grande (por exemplo, um recebimento com muitos itens) pode passar de 50. (c) O filtro `natureza` vale também para completar a transação, e o `proximo_cursor` vem nulo quando não resta linha daquela natureza. (d) Cada linha traz a `transacao_estornada_chave`: nas linhas de um estorno, a chave da transação que ele desfaz; nas outras, `null`. Aguarda a confirmação do time. (e) Parâmetro repetido na query segue a base: vale o último valor. (f) O extrato só lê, sem trava e sem commit | T11, T32, DD03, DD16, DD27, DD35 e 7.2.7 |
| DD37 | **Endurecimento, decisões do time (29/09/2026).** (a) O CNPJ alfanumérico da Receita (IN RFB 2.229/2024) é aceito: as 12 primeiras posições aceitam letras maiúsculas de `A` a `Z` e dígitos, e os dígitos verificadores continuam numéricos, calculados pelo módulo 11 com o valor de cada caractere igual ao código ASCII menos 48. Letra minúscula responde 400. (b) `nome` e `imovel_referencia` têm de 1 a 255 caracteres, com pelo menos um que não seja espaço; os espaços das pontas são removidos antes de gravar, então o mesmo imóvel com um espaço a mais responde 409 (RN09). Caractere de controle e Unicode inválido (surrogate isolado) respondem 400, porque o PostgreSQL não grava esses valores. (c) A política de imputação é única por nome e versão (`UNIQUE(nome, versao)`, 12.6). (d) Nenhum saldo passa de 9007199254740991: a operação que levaria o disponível ou o reservado acima dele responde 422 (`QIT001029`), sem nada gravado; vale para o recebimento e para o estorno, as duas operações que aumentam saldo, e o banco confere o mesmo teto nas restrições `ck_conta_saldo_*` | Decisão do time de 29/09/2026; DD13, DD28, RN09 e 12.6 |
| DD38 | *Derivado, aguarda revisão:* **endurecimento das entradas e dos erros.** (a) Um corpo que o FastAPI não consegue ler (bytes que não são UTF-8, inteiro com mais de 4300 dígitos, JSON aninhado demais) responde 400 (`QIT000001`), e não 500. (b) Espaços e tabulações nas pontas da `Idempotency-Key` não fazem parte dela (HTTP, RFC 9110), para que um reenvio com um espaço a mais não movimente o dinheiro de novo; os 255 caracteres são contados depois disso. (c) `OPTIONS` também exige o `INTERNAL-TOKEN`, para que quem não tem o token não descubra as rotas pela diferença entre 404 e 405. (d) A resposta 500 também traz o `X-Request-ID`, e o log registra o erro com o traceback. Como nenhuma entrada de cliente produz mais um 500, não há teste HTTP permanente desse caso; ele foi provado reproduzindo um 500 antes da correção dos textos. (e) O engine do SQLAlchemy usa `hide_parameters`, para que o log de um erro de banco não grave os valores enviados. (f) O índice `ix_lancamento_conta_id` passa a ser `(conta_id, id)`, a ordem do extrato | RFC 7.1 (X-Request-ID e QIT000001), RFC 9110, DD18, DD36 |

---

## 15. Checklist pré-código

Antes de começar a implementação:

### Domínio

* [x] Problema definido
* [x] Escopo definido
* [x] Entidades identificadas
* [x] Relações definidas

### Regras

* [x] Regras de saldo definidas
* [x] Regras de transferência definidas
* [x] Regras de tarifa definidas
* [x] Regras de acesso definidas
* [x] Tratamento das transações definido
* [x] Representação do dinheiro definida

### API

* [x] Rotas definidas
* [x] Entradas definidas
* [x] Respostas definidas
* [x] Códigos de erro definidos
* [x] Caminhos de falha definidos

### Arquitetura

* [x] Responsabilidade de cada camada definida
* [x] Modelo de dados definido
* [x] Identificadores definidos
* [x] Persistência definida

### Fluxos

* [x] Cadastro
* [x] Conta
* [x] Transação
* [x] Transferência
* [x] Extrato

### Validação

* [x] Validações de schema separadas das regras de negócio
* [x] Regras de negócio associadas às operações
* [x] Nenhuma decisão importante ficou implícita no código (DD01 a DD10 e os complementos marcados em DD11 a DD30 aguardam a revisão do time; D27 e D28 foram fechadas como T42 e T43)

---

## 16. Critério para começar a implementação

A implementação começa quando conseguimos responder, para cada operação:

> **O que entra?**
> **O que acontece?**
> **O que pode impedir a operação?**
> **O que muda no sistema?**
> **O que fica registrado?**
> **O que sai?**
> **Como o erro é comunicado?**

Se alguma dessas respostas ainda estiver indefinida, a decisão deve ser registrada em **Decisões em aberto** antes da implementação.
