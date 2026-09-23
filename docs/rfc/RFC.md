# Documento de Decisões da API

> Documento de apoio à implementação.
> Reúne as decisões de domínio, regras, fluxos e contrato que devem estar definidos antes do início da codificação.

---

## 1. Objetivo

### 1.1 Problema

Descrever de forma objetiva qual problema a API resolve.

**Pergunta que precisamos responder:**

> Qual problema da administradora de imóveis estamos resolvendo e por que ele exige uma API?

---

### 1.2 Objetivo da solução

Descrever o que a API permitirá fazer para resolver o problema.

**Pergunta:**

> Ao final da implementação, o que o sistema será capaz de realizar?

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

---

# 2. Entendimento do domínio

Antes de definir as rotas, precisamos definir os conceitos que existem no sistema.

## 2.1 Entidades

| Entidade      | O que representa? | Dados principais |
| ------------- | ----------------- | ---------------- |
| Cliente       |                   |                  |
| Conta         |                   |                  |
| Transação     |                   |                  |
| Transferência |                   |                  |

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

Perguntas a decidir:

* Um cliente pode possuir mais de uma conta?
* Uma conta pertence a apenas um cliente?
* Uma transferência gera uma ou mais transações?
* O saldo é armazenado ou calculado?
* Uma tarifa é uma transação?
* Uma transação pode ser alterada depois de criada?

---

# 3. Regras de negócio

> **Objetivo:** definir o que o sistema permite, o que bloqueia e por quê.

Não adicionar regras apenas porque parecem uma boa prática. Cada regra deve possuir uma justificativa no domínio ou nos requisitos do projeto.

## 3.1 Regras obrigatórias

| ID   | Regra | Motivo | Operação afetada |
| ---- | ----- | ------ | ---------------- |
| RN01 |       |        |                  |
| RN02 |       |        |                  |
| RN03 |       |        |                  |

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

### Decisão

> ...

---

## 3.3 Regras de transferência

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

### Decisão

> ...

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

### Decisão

> ...

---

# 4. Dinheiro e valores monetários

Definir como valores financeiros serão representados.

## 4.1 Unidade

Decidir entre:

* [ ] Centavos como inteiro
* [ ] `NUMERIC/DECIMAL`
* [ ] Outro

### Decisão

> ...

### Justificativa

> ...

---

## 4.2 Precisão

Definir:

* número de casas decimais;
* arredondamento;
* valor mínimo;
* valor máximo;
* representação nas requisições;
* representação nas respostas.

---

# 5. Integridade e histórico

Definir o que acontece com os dados depois que uma operação ocorre.

## 5.1 Transações

Precisamos decidir:

* Uma transação pode ser editada?
* Uma transação pode ser excluída?
* Como corrigir uma operação incorreta?
* O histórico precisa permanecer íntegro?
* O saldo pode ser reconstruído a partir das transações?

### Decisão

> ...

---

## 5.2 Identificadores

Definir:

* identificador público;
* identificador interno do banco;
* formato do identificador;
* se o ID interno pode ser exposto.

> O identificador retornado pela API não deve ser automaticamente tratado como o ID do banco sem uma decisão explícita.

---

# 6. Segurança e acesso aos recursos

Definir como a API diferencia recursos pertencentes ao solicitante e recursos de terceiros.

## 6.1 Acesso

Precisamos decidir:

* Quem pode consultar uma conta?
* Quem pode realizar uma transferência?
* Quem pode consultar o extrato?
* Como identificamos o proprietário do recurso?
* O que acontece quando alguém tenta acessar um recurso que não lhe pertence?

### Decisão

> ...

---

# 7. Contrato da API

Somente depois das decisões anteriores devemos fechar as rotas.

## 7.1 Mapa de rotas

| Método | Endpoint               | Objetivo | Entrada | Resposta | Erros |
| ------ | ---------------------- | -------- | ------- | -------- | ----- |
| POST   | `/clientes`            |          |         |          |       |
| POST   | `/contas`              |          |         |          |       |
| POST   | `/transacoes`          |          |         |          |       |
| GET    | `/contas/{id}/saldo`   |          |         |          |       |
| POST   | `/transferencias`      |          |         |          |       |
| GET    | `/contas/{id}/extrato` |          |         |          |       |

---

## 7.2 Para cada rota

Antes de implementar cada endpoint, responder:

### O que a operação faz?

> ...

### O que recebe?

> ...

### O que devolve?

> ...

### Quais regras de negócio são executadas?

> ...

### Quais situações bloqueiam a operação?

> ...

### Quais erros podem acontecer?

| Situação | HTTP | Código de erro |
| -------- | ---: | -------------- |
|          |      |                |
|          |      |                |

---

# 8. Fluxos

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

### Decisões

> ...

---

## 8.2 Fluxo de criação de conta

```text
...
```

### Decisões

> ...

---

## 8.3 Fluxo de transação

```text
...
```

### Decisões

> ...

---

## 8.4 Fluxo de transferência

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

### Decisões

> ...

---

## 8.5 Fluxo de extrato

```text
...
```

### Decisões

> ...

---

# 9. Tratamento de falhas

Para cada operação principal, precisamos definir pelo menos um caminho de falha.

| Operação         | Falha | Comportamento esperado |
| ---------------- | ----- | ---------------------- |
| Cadastro         |       |                        |
| Criação de conta |       |                        |
| Transação        |       |                        |
| Transferência    |       |                        |
| Extrato          |       |                        |

---

# 10. Validações

Separar explicitamente **validação de formato** de **regra de negócio**.

## 10.1 Schema

Validações relacionadas ao formato dos dados recebidos.

Exemplos:

* campo obrigatório;
* tipo do campo;
* formato;
* tamanho;
* estrutura da requisição.

| Campo | Validação |
| ----- | --------- |
|       |           |

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
| ----- | ------------------- |
|       |                     |

---

# 11. Decisões de arquitetura

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

### Decisão

> ...

### Justificativa

> ...

---

## 11.2 Responsabilidade de cada camada

| Camada     | Responsabilidade | O que NÃO deve fazer |
| ---------- | ---------------- | -------------------- |
| Schema     |                  |                      |
| Controller |                  |                      |
| Resource   |                  |                      |
| Repository |                  |                      |
| Model      |                  |                      |

---

# 12. Modelo de dados

Somente após fechar o domínio e as regras, definir as estruturas persistidas.

## 12.1 Cliente

```text
Cliente
- ...
- ...
- ...
```

## 12.2 Conta

```text
Conta
- ...
- ...
- ...
```

## 12.3 Transação

```text
Transação
- ...
- ...
- ...
```

## 12.4 Transferência

```text
Transferência
- ...
- ...
- ...
```

---

# 13. Decisões em aberto

Tudo que ainda não foi decidido deve ficar explícito.

| ID  | Questão | Responsável | Status |
| --- | ------- | ----------- | ------ |
| D01 |         |             | Aberto |
| D02 |         |             | Aberto |
| D03 |         |             | Aberto |

> **Regra:** uma decisão em aberto não deve ser escondida dentro do código.

---

# 14. Decisões tomadas

Registrar decisões importantes para evitar que sejam revistas acidentalmente.

| ID  | Decisão | Motivo | Data |
| --- | ------- | ------ | ---- |
| D01 |         |        |      |
| D02 |         |        |      |
| D03 |         |        |      |

---

# 15. Checklist pré-código

Antes de começar a implementação:

### Domínio

* [ ] Problema definido
* [ ] Escopo definido
* [ ] Entidades identificadas
* [ ] Relações definidas

### Regras

* [ ] Regras de saldo definidas
* [ ] Regras de transferência definidas
* [ ] Regras de tarifa definidas
* [ ] Regras de acesso definidas
* [ ] Tratamento das transações definido
* [ ] Representação do dinheiro definida

### API

* [ ] Rotas definidas
* [ ] Entradas definidas
* [ ] Respostas definidas
* [ ] Códigos de erro definidos
* [ ] Caminhos de falha definidos

### Arquitetura

* [ ] Responsabilidade de cada camada definida
* [ ] Modelo de dados definido
* [ ] Identificadores definidos
* [ ] Persistência definida

### Fluxos

* [ ] Cadastro
* [ ] Conta
* [ ] Transação
* [ ] Transferência
* [ ] Extrato

### Validação

* [ ] Validações de schema separadas das regras de negócio
* [ ] Regras de negócio associadas às operações
* [ ] Nenhuma decisão importante ficou implícita no código

---

# 16. Critério para começar a implementação

A implementação começa quando conseguimos responder, para cada operação:

> **O que entra?**

> **O que acontece?**

> **O que pode impedir a operação?**

> **O que muda no sistema?**

> **O que fica registrado?**

> **O que sai?**

> **Como o erro é comunicado?**

Se alguma dessas respostas ainda estiver indefinida, a decisão deve ser registrada em **Decisões em aberto** antes da implementação.
