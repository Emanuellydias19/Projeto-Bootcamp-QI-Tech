# Documento de Decisões da API

> Documento de apoio à implementação.
> Reúne as decisões de domínio, regras, fluxos e contrato que devem estar definidos antes do início da codificação.

**Fontes:**

* **(RFC):** RFC "Conta corrente do proprietário na administração de locação", versão 1, de 20/09/2026. É a fonte de verdade do desenho.
* **(Pitch):** documento "Conta corrente do proprietário ORCA: dor e solução", preparado para a reunião com a banca.
* **(Time):** decisões de modelagem e de contrato fechadas pelo time em 23 e 24/09/2026. Quando uma decisão do time ajusta o RFC, ela está registrada em [14. Decisões tomadas](#14-decisões-tomadas).

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

* [ ] Cadastro de cliente
* [ ] Criação de conta vinculada ao cliente
* [ ] Registro de transação
* [ ] Controle de saldo
* [ ] Transferência
* [ ] Aplicação de tarifa
* [ ] Consulta de extrato paginado

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

Também ficam fora **(RFC)**: contrato de locação e reajuste, obrigações acessórias fiscais e controle de acesso por perfil. Nenhum deles disputa saldo, e manter todos deixaria o núcleo raso.

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
| Transação | Um movimento de dinheiro: recebimento, encargo, repasse ou estorno | chave pública, conta, tipo, chave de idempotência, resultado guardado, cobrança paga (só no recebimento), transação estornada (só no estorno) |
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
                   │              └── tem ──> Itens (um por natureza)
                   │
                   └── movimenta ──> Transação (recebimento, encargo, repasse, estorno)
                                        │
                                        └── compõe ──> Lançamentos (um por natureza)
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
* **Quantas transações um repasse gera?** Uma transação do tipo `repasse`, com dois lançamentos: a taxa e o repasse (RFC e Time, T16).
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
| RN01 | O saldo disponível e o saldo reservado de uma conta nunca ficam negativos | Saldo negativo significa gastar dinheiro de outro proprietário (RFC) | Pagamento de encargo, repasse |
| RN02 | A soma dos dois saldos é sempre igual à soma dos lançamentos da conta | Divergir significa repassar dinheiro alheio (RFC). Invariante: `saldo_disponivel + saldo_reservado = SUM(lancamento.valor_centavos)` | Todas as operações de movimento |
| RN03 | Uma operação reenviada não produz o mesmo efeito duas vezes | Timeout leva o operador a reenviar, e o mesmo dinheiro não pode entrar ou sair duas vezes (RFC) | Recebimento, pagamento de encargo, repasse |
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
> * **Base e cálculo (Time, T17, T27 e T38):** a taxa incide **só sobre o aluguel efetivamente quitado**, e não sobre multa, juros ou o valor do repasse pedido. Ela é derivada dos lançamentos, sem estado novo: `taxa pendente = ⌊SUM(aluguel recebido) × taxa_administracao_bps ÷ 10000⌋ − SUM(taxa já retida)`, truncada para baixo; a sobra fica sempre com o proprietário. O repasse retém a taxa pendente e, como ela sai de dentro do valor bruto pedido (T16), o líquido é `valor_bruto − taxa`. Assim a taxa não muda com a quantidade nem com o tamanho dos repasses: num repasse parcial, a taxa do aluguel já quitado é retida uma vez só, e os repasses seguintes não pagam de novo sobre o mesmo aluguel.
> * **Aparece no extrato:** sim, como linha própria, de natureza `taxa` (RFC).
> * **Transação própria:** não; é um lançamento dentro da transação de repasse (RFC).
> * **Pode deixar a conta negativa:** não. O valor bruto inteiro precisa caber no disponível, e a taxa sai de dentro dele (RN01 e T16).
> * **Repasse menor que a taxa pendente (Time, T40):** é recusado com **422** (`QIT001026`), sem nenhum lançamento. A taxa não é retida em parte nem dividida entre repasses, e a API não executa um repasse cujo líquido seria zero ou negativo.

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
* **Valor máximo:** no recebimento, o devido na data do pagamento, que é o aberto da cobrança mais a multa e os juros daquela data (RN12 e T35). No repasse e no pagamento de encargo, o saldo correspondente (RN11). Fora isso, o limite técnico é o de `bigint`.
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
* **Formato:** `chave` é **UUID**; `id` é `bigserial`.
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
| POST | `/cobrancas/{chave}/recebimentos` | Registrar o pagamento do inquilino e imputar o valor sobre a cobrança | `valor_centavos`, `pago_em`; header `Idempotency-Key` | 201 com o rateio aplicado; 200 na repetição idêntica | 409 mesma chave com corpo diferente; 404 cobrança; 422 valor menor ou igual a zero; 422 valor acima do devido na data do pagamento |
| POST | `/contas/{chave}/encargos/pagamentos` | Pagar condomínio ou IPTU com o reservado daquela natureza | `natureza`, `valor_centavos`; header `Idempotency-Key` | 201; 200 na repetição idêntica | 409 reservado insuficiente; 409 chave repetida com corpo diferente; 404 conta |
| POST | `/contas/{chave}/repasses` | Reter a taxa e transferir o líquido ao proprietário | `valor_centavos` (bruto); header `Idempotency-Key` | 201 com a taxa e o líquido; 200 na repetição idêntica | 409 disponível insuficiente; 409 chave repetida com corpo diferente; 404 conta |
| GET | `/contas/{chave}/extrato` | Listar os lançamentos, do mais recente para o mais antigo | query `cursor`, `limite`, `natureza` | 200 com a página e o `proximo_cursor` | 404 conta; 400 limite acima de 50 |
| GET | `/contas/{chave}/saldo` | Devolver os saldos e a data do último lançamento | a chave no caminho | 200 | 404 conta |
| POST | `/transacoes/{chave}/estornos` | Estornar uma transação, com lançamentos de sinal invertido | header `Idempotency-Key` | 201; 200 na repetição idêntica | 404 transação; 409 transação já estornada ou que é um estorno; 409 saldo insuficiente para desfazer; 409 chave repetida com outra transação |

Todas as rotas acima também exigem o header `INTERNAL-TOKEN` do projeto base (sem ele, **403**).

As rotas da **cobrança** (T25 e T28) estão detalhadas em 7.2.8, 7.2.9 e 7.2.10, e a do estorno (T37 e DD04) em 7.2.11. Os campos `multa_bps` e `juros_mensal_bps` na abertura de conta vêm da decisão T18.

### Convenções do contrato

Valem para todas as rotas.

#### Autenticação

Todo pedido leva o header `INTERNAL-TOKEN`. Sem ele, ou com o valor errado, a resposta é **403**. As únicas exceções são `GET /` e `GET /health_check`, que vêm do projeto base.

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
| Mesma chave, mesmo corpo (reenvio após timeout) | **200**, com o resultado original e sem novo efeito |
| Mesma chave, corpo diferente | **409**, chave reutilizada |

Sem o header, ou com ele vazio, a resposta é **400** (`QIT000001`), como qualquer pedido fora do formato na base (Time, T32).

#### Valores e formatos

| Tipo | Formato | Exemplo |
| --- | --- | --- |
| Dinheiro | inteiro em centavos, campos com o sufixo `_centavos` | `150000` (R$ 1.500,00) |
| Percentual | inteiro em pontos-base, sufixo `_bps` (10000 = 100%) | `1000` (10%) |
| Identificador | a `chave` pública, UUID; o id interno nunca aparece | `"3fbf83e9-e5fc-4e0f-8427-db6a1a50f964"` |
| Data | `AAAA-MM-DD` | `"2026-10-05"` |
| Competência | `AAAA-MM` | `"2026-10"` |
| Documento | CPF `000.000.000-00` ou CNPJ `00.000.000/0000-00`, com a máscara, como na base | `"529.982.247-25"` |
| Lançamento | valor sinalizado: entrada positiva, saída negativa | `-35000` |

#### Formato dos erros

Todo erro segue o formato do projeto base:

```json
{
  "title": "Saldo disponível insuficiente",
  "description": "O saldo disponível da conta não cobre o valor pedido.",
  "translation": "Saldo disponível insuficiente.",
  "code": "QIT001020"
}
```

Toda resposta traz o header `X-Request-ID`, o número de protocolo da requisição (projeto base).

Uma `{chave}` fora do formato UUID no caminho é tratada como inexistente: **404**, como a base faz com a chave no caminho.

#### Catálogo de erros

Um catálogo único, no padrão `QIT` da base (Time, T31). Cada erro tem um código, uma mensagem e um status HTTP, e nenhuma rota inventa a própria representação de erro. Os códigos do projeto começam em `QIT001008`, o próximo livre da base (DD01); os `QIT001001` a `QIT001007` são da entidade de exemplo e saem com ela.

| Código | HTTP | Quando acontece |
| --- | ---: | --- |
| `QIT000001` | 400 | corpo, query ou header fora do formato: campo faltando, tipo errado, natureza fora da lista, `limite` acima de 50 ou `Idempotency-Key` ausente (projeto base) |
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
| `QIT001025` | 422 | data com o formato certo que não existe no calendário (por exemplo, `2026-02-30`) |
| `QIT001026` | 422 | repasse com valor bruto menor que a taxa pendente (T40) |

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
| `documento` | texto | sim | CPF ou CNPJ, com dígitos verificadores válidos |
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

> Registra o pagamento do inquilino sobre a cobrança indicada no caminho e imputa o valor nas naturezas, na ordem da política vigente: juros, multa, encargos, aluguel e despesa extra (RFC e T39). Multa e juros são calculados pela fórmula da conta (RN14). O encargo que não fica completo continua reservado (RN13), e o que não foi pago fica em aberto na cobrança para o pagamento seguinte (T14). Cada lançamento que quita um item aponta para ele (T25).

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
| `pago_em` | data | sim | quando o inquilino pagou; base da multa e dos juros |

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

**Exemplo de resposta 201:** o rateio aplicado, na ordem da política (juros, multa, encargos, aluguel, despesa extra), e o que ficou em aberto na cobrança.

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

> Cobrança inexistente; valor menor ou igual a zero; valor acima do devido na data do pagamento; mesma chave de idempotência com corpo diferente.

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
| `Idempotency-Key` ausente ou vazia | 400 | `QIT000001` (projeto base) |

> **Sobre o 422 do excedente (Time, T19):** ele recusa o **registro** de um recebimento acima do devido na data do pagamento (o aberto mais a multa e os juros, T35). Não é uma afirmação sobre o dinheiro: a administradora pode ter recebido R$ 2.100 na conta bancária dela. A ORCA não controla o dinheiro físico, controla o registro da posição. Na Fase 1, o excedente fica fora do sistema e é tratado pelo operador.

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

> RN01, RN02, RN03, RN04, RN06, RN07, RN11 e RN16. Com a conta travada, a API soma os lançamentos daquela natureza para saber se o reservado cobre o valor.

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

> Retém a taxa de administração e transfere o líquido ao proprietário, a partir do saldo disponível.

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

> RN01, RN02, RN03, RN04, RN06, RN11 e RN16, com a taxa calculada sobre o aluguel efetivamente quitado (T17, T27 e T38) e lançada à parte (T05 e T16).

**Quais situações bloqueiam a operação?**

> Conta inexistente; valor bruto maior que o disponível; valor bruto menor que a taxa pendente (T40); mesma chave com corpo diferente.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Corpo fora do formato | 400 | `QIT000001` (projeto base) |
| Repetição idêntica (não é erro) | 200 | não se aplica |
| Disponível insuficiente | 409 | `QIT001020` |
| Valor bruto menor que a taxa pendente (T40) | 422 | `QIT001026` |
| Mesma `Idempotency-Key` com corpo diferente | 409 | `QIT001022` |
| Conta inexistente | 404 | `QIT001011` |
| Valor menor ou igual a zero | 422 | `QIT001018` |

> **Repasse menor que a taxa pendente (Time, T40):**
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

> **200** com a página de lançamentos e o `proximo_cursor`. Cada lançamento traz a chave dele, a chave e o tipo da transação, a natureza, o valor sinalizado e a data (T32).

**Headers:** `INTERNAL-TOKEN`.

**Caminho:** `{chave}` é a `conta_chave`.

**Parâmetros de query (todos opcionais):**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `cursor` | texto | o `proximo_cursor` da página anterior |
| `limite` | inteiro | quantos lançamentos por página: de 1 a 50 (T32), padrão 10, como na base (DD03) |
| `natureza` | texto | filtra por natureza; com filtro, o extrato não reconstrói o saldo total |

Qualquer outro parâmetro é recusado com 400, como no projeto base.

**Exemplo de requisição:**

```http
GET /contas/3fbf83e9-e5fc-4e0f-8427-db6a1a50f964/extrato?limite=20
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
      "criado_em": "2026-10-10T14:02:11Z"
    },
    {
      "lancamento_chave": "1b2c3d4e-5f6a-4b7c-9d8e-0f1a2b3c4d5e",
      "transacao_chave": "f2b8d4a6-1c3e-4d5f-a7b9-0e2c4a6f8d13",
      "tipo": "repasse",
      "natureza": "taxa",
      "valor_centavos": -15000,
      "criado_em": "2026-10-10T14:02:11Z"
    }
  ],
  "limite": 20,
  "proximo_cursor": "eyJpZCI6IDQyfQ"
}
```

Quando não há mais páginas, `proximo_cursor` vem `null`.

**Quais regras de negócio são executadas?**

> RN04 (toda linha tem natureza). A soma dos lançamentos, de baixo para cima, reconstrói os saldos (RN02).

**Quais situações bloqueiam a operação?**

> Conta inexistente; limite acima de 50.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Parâmetro desconhecido ou fora do formato | 400 | `QIT000001` (projeto base) |
| Conta inexistente (ou não é sua conta) | 404 | `QIT001011` |
| Limite acima de 50 | 400 | `QIT000001` (projeto base) |

> **Observação:** com o filtro `natureza`, o extrato mostra só aquela natureza e, sozinho, não reconstrói o saldo total. O `limite` vai até 50 (T32).

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

### 7.2.10 GET /cobrancas/{chave}

**O que a operação faz?**

> Mostra a cobrança como ela está agora: quanto é devido, quanto já foi pago e quanto está em aberto em cada item. É por aqui que o operador sabe o valor máximo aceito num recebimento antes de registrá-lo, já que o recebimento acima do aberto é recusado com 422 (RN12). Rota incluída pela decisão T28.

**O que recebe?**

> A `chave` da cobrança no caminho e, na query, a `data` (opcional, `AAAA-MM-DD`; se não vier, vale a data de hoje) (DD05).

**O que devolve?**

> **200** com os dados da cobrança; para cada item, o valor devido, o valor pago e o valor em aberto; o total em aberto; a multa e os juros calculados para a `data`; e o **total devido na data**, que é o máximo aceito num recebimento pago nesse dia (RN12 e T35).

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
  "quitada": false,
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

> Nenhuma escrita. O que está em aberto não é guardado: é calculado como o valor devido de cada item menos a soma dos lançamentos que apontam para ele (12.7). A cobrança está quitada quando nenhum item tem valor em aberto.

**Quais situações bloqueiam a operação?**

> Cobrança inexistente.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Cobrança inexistente (ou não é sua cobrança) | 404 | `QIT001015` |
| `data` fora do formato | 400 | `QIT000001` (projeto base) |
| `data` inexistente no calendário | 422 | `QIT001025` |

> **Multa e juros:** não entram no valor em aberto dos itens, porque dependem da data do pagamento (RN14). Por isso a rota os calcula para a `data` pedida, e o total devido na data é o limite do recebimento (T35). No exemplo, o pagamento é em dia, então os dois são zero.

### 7.2.11 POST /transacoes/{chave}/estornos

**O que a operação faz?**

> Desfaz uma transação registrada por engano sem apagar nada: cria uma transação nova, do tipo `estorno`, com um lançamento de sinal invertido para cada lançamento da original, apontando para o mesmo item da cobrança quando houver (T22, T37 e DD04). Segue o mesmo fluxo idempotente das outras transações: `Idempotency-Key`, resultado guardado e trava na conta.

**O que recebe?**

> A `chave` da transação no caminho e o header `Idempotency-Key`. Não tem corpo: o estorno é sempre da transação inteira, porque inverte todos os lançamentos dela (DD04).

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

> RN01, RN02, RN03, RN04 e RN16, e T10: a transação original não muda. Como os lançamentos invertidos apontam para os mesmos itens, estornar um recebimento devolve o valor ao "em aberto" da cobrança. O estorno também não pode deixar um saldo negativo: estornar um recebimento cujo dinheiro já foi repassado ou pago ao credor é recusado com 409.

**Quais situações bloqueiam a operação?**

> Transação inexistente; transação já estornada; transação que é ela mesma um estorno; saldo insuficiente para desfazer; mesma chave de idempotência usada para outra transação.

**Quais erros podem acontecer?**

| Situação | HTTP | Código de erro |
| --- | ---: | --- |
| Repetição idêntica (não é erro) | 200 | não se aplica |
| `Idempotency-Key` ausente ou vazia | 400 | `QIT000001` (projeto base) |
| Transação inexistente (ou não é sua) | 404 | `QIT001023` |
| Transação já estornada, ou que é ela mesma um estorno | 409 | `QIT001024` |
| Desfazer deixaria o saldo disponível negativo | 409 | `QIT001020` |
| Desfazer deixaria o saldo reservado negativo | 409 | `QIT001021` |
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
Proprietário existe? ─── não ──> 404
    ↓ sim
Taxa entre 0 e 10000 bps? ─── não ──> 422
    ↓ sim
INSERT conta (UNIQUE proprietário + imóvel) ─── violou ──> 409
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
4. SELECT conta da cobrança FOR UPDATE (a linha da conta fica travada)
    ↓
5. INSERT transacao (chave_idempotencia UNIQUE; cobranca_id da cobrança paga)
    ↓
6. calcula o que está em aberto na cobrança
    ↓
7. calcula multa e juros sobre o aberto, na data do pagamento (RN14)
   (valor acima de aberto + multa + juros ──> 422)
    ↓
8. imputa o valor pela política vigente: juros, multa, encargos, aluguel, despesa extra
    ↓
9. INSERT lancamentos (um por natureza)
    ↓
10. UPDATE saldo_disponivel e saldo_reservado
    ↓
11. COMMIT (a trava é liberada)
    ↓
201 com o rateio aplicado
```

### Decisões sobre o fluxo de transação

> Os passos 2 a 11 vivem numa única transação de banco: lançamentos e saldos nascem juntos ou não nascem (RFC). A ordem de imputação é dado, não código: vem da política versionada apontada pela conta, e o rateio produzido fica gravado nos lançamentos. Diferente do RFC original, a taxa de administração **não** é lançada aqui: ela é retida no repasse (T15).

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
INSERT transacao com a mesma Idempotency-Key
    ├── não violou o UNIQUE ──> opera normalmente ──> 201
    └── violou o UNIQUE
            ├── corpo igual ao guardado ──> 200 com o resultado original, sem novo efeito
            └── corpo diferente ──> 409 chave reutilizada
```

### Decisões sobre o fluxo de transferência

> * **A trava vem antes da verificação de saldo:** o `SELECT ... FOR UPDATE` é tomado antes da validação e mantido até o commit. Sem ele, as duas requisições leriam o mesmo saldo antes de qualquer uma escrever, e as duas passariam. A trava serializa aquela conta, não o sistema (RFC).
> * **"Verificar saldo":** o valor bruto precisa caber no **saldo disponível** (RN11).
> * **"Calcular tarifa":** a taxa pendente sobre o aluguel efetivamente quitado (T27 e T38): `⌊SUM(aluguel recebido) × taxa_administracao_bps ÷ 10000⌋ − SUM(taxa já retida)`; líquido = `valor_bruto − taxa` (T17).
> * **"Registrar movimentações":** dois lançamentos, `taxa` e `repasse`, que somados dão o valor bruto (RN16).
> * **Idempotência no banco:** a violação da restrição UNIQUE é capturada pela aplicação e traduzida em 200 ou 409, nunca em 500. Quem decide é o banco, não um `if` que consultou antes e correu o risco de outra requisição entrar no meio (RFC).

---

## 8.5 Fluxo de extrato

```text
GET /contas/{chave}/extrato?cursor=...&limite=...&natureza=...
    ↓
Validação da query (limite acima de 50 ──> 400)
    ↓
Conta existe? ─── não ──> 404
    ↓ sim
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
| Transação (recebimento) | Reenvio da mesma operação após timeout | O UNIQUE da chave de idempotência barra o INSERT; com o corpo igual, 200 com o resultado original, sem novo lançamento; com o corpo diferente, 409 |
| Transação (recebimento) | Valor acima do devido na data do pagamento (aberto + multa + juros) | 422 (`QIT001019`); nada é registrado, e o excedente é tratado pelo operador fora do sistema (T19) |
| Transferência (repasse) | Duas requisições concorrentes e disponível insuficiente para a segunda | A segunda espera a trava, lê o saldo atualizado, falha na validação e sofre ROLLBACK; 409 `QIT001020`, nenhum lançamento órfão |
| Extrato | Limite acima de 50 | 400 (`QIT000001`), sem ler nada do banco |
| Estorno | Transação já estornada | 409 (`QIT001024`); nada é criado, e a original continua como estava |
| Transferência (repasse) | Valor bruto menor que a taxa pendente | 422 (`QIT001026`); nenhum lançamento de repasse (T40) |

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
| `documento` | obrigatório; CPF `000.000.000-00` ou CNPJ `00.000.000/0000-00`, com a máscara, como na base |
| `nome` | obrigatório; texto não vazio |
| `proprietario_chave` | obrigatório; UUID |
| `{chave}` (caminho) | UUID da conta, da cobrança ou da transação, conforme a rota (T28); fora do formato, é tratada como inexistente: 404, como na base |
| `imovel_referencia` | obrigatório; texto não vazio |
| `politica_imputacao_chave` | obrigatório; UUID (DD08) |
| `taxa_administracao_bps`, `multa_bps`, `juros_mensal_bps` | obrigatórios; inteiros (a faixa de 0 a 10000 é regra de negócio, RN10) |
| `valor_centavos` | obrigatório; inteiro (no repasse, é o valor bruto) |
| `competencia` | obrigatório na cobrança; `AAAA-MM` |
| `vencimento` | obrigatório na cobrança; data no formato `AAAA-MM-DD` |
| `itens` | obrigatório na cobrança; lista não vazia de `natureza` (`aluguel`, `condominio`, `iptu` ou `despesa_extra`, T36) e `valor_centavos` inteiro |
| `pago_em` | obrigatório no recebimento; data no formato `AAAA-MM-DD` |
| `natureza` (encargo) | obrigatório; `condominio` ou `iptu` |
| `natureza` (item incluído depois) | obrigatório; `despesa_extra` (T36) |
| `data` (consulta da cobrança) | opcional; `AAAA-MM-DD` |
| `Idempotency-Key` (header) | obrigatório e não vazio nas quatro rotas de movimento (recebimento, encargo, repasse e estorno); sem ele, 400 (T32) |
| `cursor`, `limite`, `natureza` (extrato) | opcionais; `limite` inteiro de 1 a 50; nenhum outro parâmetro aceito |

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
| Multa uma vez e juros pro rata die (RN14) | Controller, no recebimento |
| Encargo que não fica completo continua reservado (RN13) | Controller, na imputação |
| Disponível suficiente para o repasse (RN01 e RN11) | Controller, depois do `SELECT ... FOR UPDATE`, dentro da transação de banco |
| Reservado da natureza suficiente para o encargo (RN11) | Controller, somando os lançamentos da natureza com a conta travada |
| Item novo só em cobrança não quitada (RN15) | Controller, na inclusão de item (`POST /cobrancas/{chave}/itens`) |
| Estorno só de transação não estornada e que não é um estorno (DD04) | Controller, com a conta travada, e o banco, com a restrição UNIQUE em `transacao_estornada_id` |
| Unicidade de documento, de conta por imóvel e de chave de idempotência (RN08, RN09, RN03) | Banco, com restrições UNIQUE; o controller só traduz a violação em 409 ou 200 |
| Ordem de imputação (RN05) | Controller, lendo a política versionada da conta |
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

Modelo do RFC com as decisões do time. Em todas as tabelas, `id` é a chave interna (`bigserial`) e nunca sai na resposta. O diagrama está em `docs/rfc/orca-modelo-dados.erd.json` (abre no ERD Editor).

## 12.1 Cliente

Na ORCA, o cliente é o **proprietário**.

```text
Proprietario
- id           bigserial    PK interna
- chave        uuid         UNIQUE, identificador público
- documento    char         UNIQUE, unicidade do cadastro
- nome         text
- criado_em    timestamptz
```

## 12.2 Conta

```text
Conta
- id                      bigserial    PK interna
- chave                   uuid         UNIQUE, identificador público
- proprietario_id         bigint       FK para Proprietario
- imovel_referencia       text         UNIQUE junto com o proprietário: uma conta por imóvel e proprietário
- saldo_disponivel        bigint       o que pode ser repassado; trava e validação do repasse (T13)
- saldo_reservado         bigint       o que está guardado para encargos; trava e validação do pagamento de encargo (T13)
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
- chave               uuid         UNIQUE, identificador público
- conta_id            bigint       FK para Conta
- tipo                text         recebimento, encargo, repasse ou estorno (T22)
- transacao_estornada_id  bigint  FK para Transacao; preenchida só no estorno; UNIQUE, então uma transação é estornada no máximo uma vez (DD04)
- cobranca_id         bigint       FK para Cobranca; a cobrança que o recebimento pagou, preenchida só no recebimento (T29)
- chave_idempotencia  text         UNIQUE por conta; barra o reenvio
- resultado           jsonb        resposta guardada para a repetição idêntica
- criado_em           timestamptz  quando aconteceu
```

O `cobranca_id` liga o recebimento inteiro à cobrança, inclusive os lançamentos de multa e juros, que não quitam nenhum item e por isso não têm `item_cobranca_id`. É por ele que a API sabe se a multa daquela cobrança já foi cobrada (RN14).

## 12.4 Transferência

Não existe uma tabela de transferência. O repasse é uma **Transação** do tipo `repasse`, e os valores ficam nos **Lançamentos** dela (a taxa e o repasse).

## 12.5 Lançamento

```text
Lancamento
- id              bigserial    PK interna
- chave           uuid         UNIQUE
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
- chave            uuid         UNIQUE, identificador público (DD08)
- nome             text
- versao           int          UNIQUE; versionada, nunca editada no lugar
- ordem_naturezas  jsonb        a ordem em que o valor recebido quita as naturezas
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

Campos decididos pelo time (T14 e T25). O que está em aberto numa cobrança não é guardado: é o valor devido de cada item menos a soma dos lançamentos que apontam para ele. A cobrança está quitada quando nenhum item tem valor em aberto.

```text
Cobranca
- id               bigserial    PK interna
- chave            uuid         UNIQUE, identificador público
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

As questões D01 a D26 estão fechadas (seção 14). Os detalhes derivados do padrão da base (DD01 a DD10, no fim da seção 14) só aguardam a revisão do time.

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
| T40 (D25) | **Repasse com valor bruto menor que a taxa pendente é recusado com 422** (`QIT001026`), sem nenhum lançamento: não há retenção parcial da taxa, e ela não é dividida entre repasses | A taxa continua retida uma vez só (T38), e a API não executa um repasse cujo líquido para o proprietário seria zero ou negativo | 24/09/2026 |
| T41 (D26) | A **política de imputação padrão é criada no `database.sql`**, pelo mecanismo de inicialização do banco da base, com versão 1 e uma chave UUID fixa; a abertura de conta usa essa política como referência | Evita criar uma rota só para administrar uma entidade que não precisa ser configurável na Fase 1, e garante que toda conta tenha uma política válida | 24/09/2026 |

### Detalhes derivados do padrão da base

Os itens abaixo **não são decisões novas de modelagem**. São detalhes de contrato que completam as decisões acima seguindo o padrão que a base já adota, ou uma decisão já tomada. O time só revisa e confirma se estão coerentes com o contrato da base.

| ID | Detalhe | Derivado de |
| --- | --- | --- |
| DD01 | Os códigos do projeto são numerados a partir de `QIT001008` (de `QIT001008` a `QIT001026`), e os dois 409 de saldo têm códigos diferentes (disponível e reservado) | Guia da base: "o próximo livre é o `QIT001008`"; T31 |
| DD02 | Documento com o formato certo e os dígitos verificadores errados responde **422** (`QIT001008`), e não 400 | Base: o `InvalidDocumentNumber` responde 422 ("li, entendi, e esse valor não pode existir") |
| DD03 | `limite` do extrato acima de 50 responde **400** (`QIT000001`), porque é barrado no schema; sem o parâmetro, o padrão é 10 | Base: o schema de listagem barra o `limit` pelo `pattern`, e o padrão é 10; T32 |
| DD04 | Estorno em `POST /transacoes/{chave}/estornos`, sem corpo e sempre da transação inteira (inverte todos os lançamentos); uma transação é estornada no máximo uma vez (UNIQUE em `transacao_estornada_id`), e um estorno não é estornado | T28 (o estorno pertence à transação), T22 e T37 (lançamentos invertidos), T10 (a original não muda) |
| DD05 | `GET /cobrancas/{chave}` aceita `?data=AAAA-MM-DD` (padrão: hoje) e devolve a multa, os juros e o total devido naquela data | T35: sem isso, o operador não saberia o limite do recebimento antes de registrá-lo |
| DD06 | Valor menor ou igual a zero responde **422** (`QIT001018`) em toda operação com valor, não só no recebimento | RFC: 422 no recebimento; mesma regra nas outras operações |
| DD07 | `multa_bps` e `juros_mensal_bps` aceitam de 0 a 10000, a mesma faixa da taxa (RN10) | RN10 |
| DD08 | Na API, a política é identificada pela `chave` pública dela (`politica_imputacao_chave`); a política inexistente responde 404 (`QIT001014`) | T08: nenhuma rota aceita o id interno; T30 |
| DD09 | Uma `{chave}` fora do formato UUID no caminho é tratada como inexistente: **404** | Base: a chave no caminho não é validada no schema, e a entidade não encontrada responde 404 |
| DD10 | Data com o formato certo que não existe no calendário responde **422** (`QIT001025`); documento com a máscara de CPF ou CNPJ | Base: `InvalidBirthdate` (422) e o `pattern` do documento |

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
* [x] Nenhuma decisão importante ficou implícita no código (os detalhes derivados DD01 a DD10 aguardam só a revisão do time)

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
