# A ORCA em produção

O autoestudo da Aula 4 (Produção) termina com 9 perguntas, e cada uma reaparece como decisão de arquitetura no desafio. Este documento responde as 9 para a ORCA, sempre com a prova: o teste que garante o comportamento ou o comando que mostra o resultado.

As respostas valem para o que está no repositório. O que a ORCA ainda não faz aparece como limite conhecido, no fim de cada seção e em [O que fica para depois](#o-que-fica-para-depois).

**Sumário:** [Resumo](#resumo) · [1. Logs](#1-logs-estruturados-e-request-id) · [2. Métricas](#2-métricas-red) · [3. Saúde](#3-liveness-e-readiness) · [4. Sem estado](#4-sem-estado-balanceamento-e-autoscaling) · [5. Timeouts](#5-timeouts-retry-e-circuit-breaker) · [6. Idempotência](#6-idempotência) · [7. Configuração](#7-segredos-e-configuração) · [8. OWASP](#8-owasp-api-security-top-10) · [9. Autenticação](#9-autenticação-autorização-e-tls) · [Variáveis](#variáveis-de-produção) · [Como conferir](#como-conferir) · [Para depois](#o-que-fica-para-depois)

## Resumo

| Tema | O que a ORCA faz | Prova |
| --- | --- | --- |
| Logs | Uma linha JSON por evento, em stdout, com o `request_id` como campo | [Como conferir](#como-conferir), passo 3 |
| Correlação | `X-Request-ID` em toda resposta, inclusive no 500; o cliente pode mandar o seu | `test_returns_the_request_id_on_a_500` |
| Métricas | `GET /metrics` no formato do Prometheus: contagem e duração por método, rota e status | `tests/integration/test_producao.py` |
| Saúde | `/health_check` diz se o processo está vivo; `/health_check/ready` diz se o banco responde | `test_producao.py` e [Como conferir](#como-conferir), passo 4 |
| Sem estado | Saldo, trava e idempotência moram no PostgreSQL, não na memória do processo | os testes `test_processes_simultaneous_repetitions_only_once` |
| Timeouts | Espera pela trava limitada a 5 s, consulta a 15 s e conexão a 3 s; estourou, ou o banco caiu, `503` com `Retry-After` | `test_gives_up_waiting_for_the_conta_lock_with_503` |
| Idempotência | `Idempotency-Key` obrigatória nas 4 rotas de dinheiro, conferida com a conta travada | `test_recebimento_idempotencia.py` e os testes de repasse, encargo e estorno |
| Configuração | Tudo vem do ambiente; fora de `local` e `test`, a API não sobe com o token padrão | [Como conferir](#como-conferir), passo 6 |
| Consumo | Corpo de até 64 KiB (`413`), tamanho declarado (`411`), até 100 itens na criação da cobrança, extrato de 1 a 50 | `test_producao.py` |
| Autenticação | `INTERNAL-TOKEN` em toda rota de negócio, comparado em tempo constante | `test_refuses_metrics_without_token` e os testes de 403 da base |

## 1. Logs estruturados e request id

> **Pergunta:** se um cliente reportar um erro às 15h32, qual dado no seu sistema te permite achar exatamente aquela requisição, e não uma parecida?

**Resposta:** o `X-Request-ID`. Toda resposta da ORCA traz esse header, inclusive a de erro 500. Se quem chama manda o seu próprio `X-Request-ID` (letras, dígitos, `_` e `-`, até 64 caracteres), a ORCA usa o mesmo; se não manda, ela cria um UUID. O mesmo valor sai no campo `request_id` de todas as linhas de log daquela requisição, então um filtro devolve só ela:

```bash
docker compose logs api --no-log-prefix | grep 7b24c351-0933-4237-8abc-020f1ced3746
```

Cada linha é um objeto JSON escrito em stdout, como pede o fator XI do 12-factor: a aplicação não escolhe arquivo nem destino, só escreve o evento; quem guarda e indexa é o ambiente. Os dados da requisição vão como campos próprios, e não só dentro do texto da mensagem, para que a busca seja por campo e não por recorte de string. Esta é a saída real de um repasse que esperou a trava da conta e desistiu (o `ENTROU`, o aviso e o `SAIU` da mesma requisição):

```json
{"timestamp": "2026-10-01T00:20:26.473+00:00", "level": "INFO", "logger": "bootcamp-api.middlewares.request_logger", "request_id": "7b24c351-0933-4237-8abc-020f1ced3746", "message": "ENTROU POST /contas/11080148-a0c9-48ba-b10a-c70651cdd427/repasses", "method": "POST", "path": "/contas/11080148-a0c9-48ba-b10a-c70651cdd427/repasses"}
{"timestamp": "2026-10-01T00:20:31.503+00:00", "level": "WARNING", "logger": "bootcamp-api.errors.handlers", "request_id": "7b24c351-0933-4237-8abc-020f1ced3746", "message": "O banco nao respondeu a tempo em POST /contas/11080148-a0c9-48ba-b10a-c70651cdd427/repasses", "pgcode": "55P03"}
{"timestamp": "2026-10-01T00:20:31.504+00:00", "level": "INFO", "logger": "bootcamp-api.middlewares.request_logger", "request_id": "7b24c351-0933-4237-8abc-020f1ced3746", "message": "SAIU 503 POST /contas/11080148-a0c9-48ba-b10a-c70651cdd427/repasses - 5031.0 ms", "method": "POST", "path": "/contas/11080148-a0c9-48ba-b10a-c70651cdd427/repasses", "status": 503, "duration_ms": 5031.0}
```

O que o log **não** grava, de propósito:

* o corpo da requisição (documento, nome e valores ficam fora do log);
* os valores enviados ao banco quando uma consulta falha (`hide_parameters` no engine do SQLAlchemy, DD38);
* o `INTERNAL-TOKEN`.

A linha de acesso do uvicorn foi desligada (`--no-access-log` no `docker-compose.yml` e no `Dockerfile`): ela repetia o `SAIU` em texto livre e sem o `request_id`. As outras linhas do uvicorn (subida, desligamento e o aviso de um 500 inesperado) passam pelo mesmo formato JSON, com o `request_id` quando há uma requisição em andamento.

**Limite:** com o `--reload` do ambiente de desenvolvimento, o processo que vigia os arquivos e reinicia a API escreve as próprias linhas (`WatchFiles detected changes...`) em texto, porque roda fora da aplicação. A imagem de produção (o `CMD` do `Dockerfile`) não usa o `--reload`.

## 2. Métricas RED

> **Pergunta:** se você só pudesse olhar para 3 números num domingo à noite para saber se o sistema está bem, quais seriam, e por quê?

**Resposta:** os três números do método RED, que a ORCA expõe em `GET /metrics` (formato de texto do Prometheus, protegido pelo `INTERNAL-TOKEN`):

| Sinal | Métrica | O número do domingo | Consulta no Prometheus |
| --- | --- | --- | --- |
| **Rate** (tráfego) | `orca_http_requests_total{method, route, status}` | requisições por segundo | `sum(rate(orca_http_requests_total[5m]))` |
| **Errors** (erros) | o mesmo contador, com `status` 5xx | proporção de 5xx sobre o total | `sum(rate(orca_http_requests_total{status=~"5.."}[5m])) / sum(rate(orca_http_requests_total[5m]))` |
| **Duration** (latência) | `orca_http_request_duration_seconds{method, route}` (histograma) | p95 das rotas de dinheiro | `histogram_quantile(0.95, sum by (le, route) (rate(orca_http_request_duration_seconds_bucket{method="POST"}[5m])))` |

Por que esses três: o tráfego diz se o sistema está recebendo o que costuma receber (zero num dia útil é problema, mesmo sem erro); a proporção de 5xx diz se ele está falhando com quem chama; o p95 diz se ele está respondendo a tempo. Um 4xx não entra na conta de erro: é o cliente pedindo errado, e a ORCA respondendo certo.

O quarto sinal dourado, a **saturação**, aparece de forma indireta: o `503` de trava esgotada (seção 5) é a ORCA dizendo que uma conta tem mais operações na fila do que consegue atender, e ele já sai no contador com `status="503"`.

Cuidados que os testes garantem:

* **O rótulo `route` é o molde da rota, nunca o caminho com a chave.** Um repasse sai como `route="/contas/{conta_chave}/repasses"`. Se a chave entrasse no rótulo, cada conta criaria uma série nova, e o Prometheus cresceria sem limite. Pedidos que não chegam a uma rota (sem token, corpo grande demais, caminho inexistente) saem com `route="sem_rota"`. Testes: `test_counts_each_request_by_route_template_and_status` e `test_never_puts_a_chave_in_the_metric_labels`.
* **O rótulo `method` também é limitado.** GET, POST, PUT, PATCH, DELETE, HEAD e OPTIONS saem com o próprio nome; qualquer outro sai como `OUTRO`, para que um cliente não crie séries novas mandando métodos incomuns. Teste: `test_groups_the_unusual_methods_in_a_single_label`.
* **O 500 inesperado também conta** (`test_counts_the_unexpected_errors`), e a duração é medida por rota (`test_measures_the_duration_of_each_route`).

**Limite:** cada processo guarda os próprios contadores. Com várias cópias da API, o Prometheus coleta cada uma e soma. A ORCA roda um processo por contêiner; se um dia rodar o uvicorn com `--workers`, a biblioteca `prometheus-client` precisa do modo multiprocesso.

## 3. Liveness e readiness

> **Pergunta:** das duas perguntas, "o processo está vivo?" e "o processo está pronto para tráfego?", qual delas o endpoint de saúde do seu desafio responde hoje?

**Resposta:** as duas, em rotas separadas.

| Rota | Pergunta | Resposta | Toca no banco? |
| --- | --- | --- | --- |
| `GET /health_check` | O processo está vivo? (liveness) | `204`, sem corpo | não |
| `GET /health_check/ready` | Está pronto para tráfego? (readiness) | `200` com `{"status": "pronto", "banco": "ok"}`; `503` (`QIT000503`) se o banco não responde | sim, um `SELECT 1` |

A separação é de propósito. A liveness não consulta o banco: se consultasse, uma queda do banco faria o orquestrador reiniciar todas as cópias da API ao mesmo tempo (o reinício em cascata do material da aula), e reiniciar a API não conserta o banco. A readiness consulta, porque uma API sem banco não pode receber tráfego: o certo é sair da lista do balanceador até o banco voltar.

As duas rotas dispensam o token (quem consulta é o orquestrador, que não tem o segredo) e ficam fora do log de requisições, para que a consulta a cada 3 segundos não esconda o resto.

O `healthcheck` do `docker-compose.yml` usa a readiness: `docker compose up --wait` só libera quando a API alcança o banco. Num cluster, a liveness iria para `/health_check` e a readiness para `/health_check/ready`.

Prova com o banco parado ([Como conferir](#como-conferir), passo 4): `/health_check` continua `204`, `/health_check/ready` passa a `503` e volta a `200` quando o banco sobe.

**Limite:** não há tracing distribuído. A ORCA é um serviço só, e o `request_id` cumpre o papel de amarrar as linhas de uma requisição. Com mais serviços na cadeia, o próximo passo é propagar o `X-Request-ID` (ou um `trace_id` do OpenTelemetry) em cada chamada.

## 4. Sem estado, balanceamento e autoscaling

> **Pergunta:** se sua aplicação guarda alguma coisa na memória de um processo (um carrinho, um contador, uma sessão), o que acontece quando o autoscaling sobe uma segunda cópia?

**Resposta:** nada muda para quem chama, porque a ORCA não guarda estado de negócio na memória. Tudo o que decide o resultado de uma operação mora no PostgreSQL:

* os saldos e os lançamentos;
* a trava de cada conta, que é um `SELECT ... FOR UPDATE` no banco, e não um lock dentro do processo (DD16);
* a chave de idempotência e o resultado guardado de cada operação (DD18).

Duas cópias atrás de um balanceador (round robin, por exemplo) disputam a mesma trava no mesmo banco, e o resultado é o mesmo de uma cópia só. Os testes `test_processes_simultaneous_repetitions_only_once` (recebimento, repasse, encargo e estorno) e `test_matches_the_saldos_after_simultaneous_operations` (extrato) disparam requisições em paralelo e conferem que o dinheiro se move uma vez só.

O que fica na memória de cada processo não decide nada: o cache dos schemas JSON (só leitura, igual em todas as cópias) e os contadores de métricas (cada cópia expõe os seus, e o Prometheus soma).

**Limite:** escalar a API não escala o banco. Cada cópia abre até 15 conexões (`pool_size=5` mais o excedente padrão de 10 do SQLAlchemy), e o PostgreSQL atende 100 por padrão. Antes de subir a sétima cópia, é preciso aumentar o banco ou pôr um pooler (PgBouncer) no meio. Esta entrega não inclui o balanceador com réplicas.

## 5. Timeouts, retry e circuit breaker

> **Pergunta:** o conector do seu desafio para o serviço externo tem timeout? E o que o seu código faz quando ele estoura: tenta de novo, devolve erro, ou trava a requisição?

**Resposta:** nenhuma rota da ORCA chama um serviço externo. O conector de boletos do projeto base continua em `src/connectors`, com timeout de 5 segundos (`BANKSLIP_API_TIMEOUT`), mas a ORCA não o usa. A dependência que pode demorar é o banco, e ela tem dois limites, aplicados a toda conexão:

| Limite | Variável | Padrão | Quando estoura |
| --- | --- | --- | --- |
| Espera pela trava de uma conta | `DB_LOCK_TIMEOUT_MS` | 5000 ms | `503` (`QIT000503`) com `Retry-After: 1` |
| Duração de uma consulta | `DB_STATEMENT_TIMEOUT_MS` | 15000 ms | `503` (`QIT000503`) com `Retry-After: 1` |
| Abertura de uma conexão | `DB_CONNECT_TIMEOUT_SECONDS` | 3 s | `503` (`QIT000503`) com `Retry-After: 1` |

Sem esses limites, uma conta muito disputada (ou uma trava esquecida aberta) faria as requisições se acumularem sem fim, cada uma segurando uma conexão do pool. Com eles, a requisição desiste, a transação inteira é desfeita (nada gravado) e quem chama recebe um erro claro em poucos segundos. O banco fora do ar (conexão recusada ou sem resposta) também responde `503` com `Retry-After`; um erro de banco de outro tipo continua `500`, com o traceback no log.

Prova: o teste `test_gives_up_waiting_for_the_conta_lock_with_503` segura a trava de uma conta direto no banco, pede um repasse e confere o `503`, o `Retry-After: 1` e o saldo intacto; depois de soltar a trava, o reenvio com a mesma `Idempotency-Key` é aceito com `201`. Na prova manual ([Como conferir](#como-conferir), passo 5), a resposta chegou em 5,04 s. Com o banco parado, um cadastro respondeu `503` com `Retry-After: 1` em 5,3 s.

**Quem tenta de novo é o cliente, não a ORCA.** A API não repete nada sozinha: retries "são egoístas" (cada um pede mais do servidor que já está sofrendo), e repetir dentro da API multiplicaria a carga justamente na hora ruim. A política recomendada para quem chama:

* repetir só `503`, `500` e falha de rede sem resposta; nunca um `4xx`, que vai dar o mesmo resultado;
* esperar pelo menos o `Retry-After` e crescer a espera de forma exponencial, com jitter (por exemplo, um tempo aleatório entre 0 e `min(8 s, 1 s × 2^tentativa)`), para que os clientes não voltem todos no mesmo instante;
* parar depois de umas 4 tentativas;
* **repetir sempre com a mesma `Idempotency-Key`**, o que torna seguro repetir até um pedido que, na verdade, já tinha dado certo (seção 6).

Circuit breaker não se aplica dentro da ORCA, porque não há chamada externa a proteger. Para quem chama a ORCA, o padrão vale: se a proporção de `503` disparar, o cliente para de tentar por um tempo, em vez de insistir.

## 6. Idempotência

> **Pergunta:** qual operação do seu desafio seria perigosa de repetir sem querer, e o que te protegeria disso?

**Resposta:** as quatro que movem dinheiro: o recebimento, o pagamento de encargo, o repasse e o estorno. Repetir um repasse por causa de um timeout de rede pagaria o proprietário duas vezes.

O que protege (DD18 e DD32):

1. As quatro rotas exigem o header `Idempotency-Key`; sem ele, `400`.
2. Antes de decidir qualquer coisa, a operação trava a conta (`SELECT ... FOR UPDATE`). Com a conta travada, a ORCA procura a chave.
3. Se a chave já existe com o mesmo pedido (mesmo hash da rota, da chave do caminho e do corpo), a resposta é `200` com o resultado guardado da primeira vez, e nada se move de novo.
4. Se a chave já existe com outro pedido, `409` (`QIT001022`).
5. Uma restrição `UNIQUE` no banco é a rede de segurança, caso algo escape da trava.

Os cadastros (proprietário, conta e cobrança) não precisam da chave, porque o próprio dado é único: o mesmo documento, a mesma conta para o imóvel ou a mesma competência respondem `409`, e nada é criado duas vezes.

Esta é a pré-condição da seção 5: como o `503` acontece antes de gravar e o reenvio usa a mesma chave, o cliente pode repetir sem medo.

## 7. Segredos e configuração

> **Pergunta:** no seu repositório, onde mora o valor de uma credencial hoje, e o que aconteceria se esse arquivo fosse commitado por engano?

**Resposta:** a credencial mora no ambiente. O código só lê variáveis (`src/constants.py`), e nenhuma senha está escrita nele. Os valores que aparecem no repositório são de estudo e públicos de propósito: o `default_token` e o usuário `bootcamp` do banco, nos padrões do `docker-compose.yml` e no `.env.example`. O `.env` com valores de verdade fica fora do Git (`.gitignore`).

Se um `.env` com um token real fosse commitado, o token estaria vazado para sempre: apagar o commit não desfaz os clones e as cópias que já existem. A resposta certa é trocar o token na hora (rotação) e só depois limpar o histórico.

Duas proteções para o erro mais provável, que é subir em produção com o valor de estudo:

* fora dos ambientes `local` e `test` (em `production`, `staging` ou qualquer outro valor, inclusive um erro de digitação), a API **se recusa a subir** se o `INTERNAL_TOKEN` for o `default_token` ou tiver menos de 32 caracteres, sem contar os espaços das pontas. A regra nega por padrão: errar o nome do ambiente não libera o token de estudo. A recusa acontece na subida, e não na primeira requisição;
* a comparação do token é feita em tempo constante (`hmac.compare_digest`), para que o tempo da resposta não revele quantos caracteres do palpite estavam certos.

Prova ([Como conferir](#como-conferir), passo 6): com `APP_ENV` igual a `production`, `staging`, `prd` ou `production` com um espaço na frente, a subida com o token padrão falha, e também com um token de 40 espaços; com um token de 40 caracteres, ou com `APP_ENV=test`, sobe.

## 8. OWASP API Security Top 10

> **Pergunta:** existe alguma rota do seu desafio que devolve um recurso (conta, transação) só checando se o token é válido, sem checar se ele pertence ao dono daquele recurso?

**Resposta:** sim, e é uma decisão registrada, não um esquecimento. Na Fase 1 há um só ator, o operador da administradora, e o `INTERNAL-TOKEN` é o mesmo para todos os chamadores (RFC 6.1). A ORCA é o livro-caixa interno da administradora: quem chama é o sistema dela, que opera todas as contas. Por isso nenhuma rota confere dono, e quem tem o token vê qualquer conta.

O que reduz o risco hoje:

* as chaves públicas são UUID v4 aleatórios, então não dá para varrer contas trocando `1` por `2` como num id sequencial; o id interno do banco nunca sai numa resposta;
* a regra para quando houver perfis já está escrita (T33): recurso de outro dono responde `404`, igual ao inexistente, sem confirmar que ele existe.

O que falta para expor a ORCA fora da rede da administradora é o controle de acesso por perfil, fora do escopo desta fase.

Os outros itens do Top 10 que tocam a ORCA:

| Item (2023) | Situação na ORCA |
| --- | --- |
| API1 Broken Object Level Authorization | descrito acima: sem dono por recurso na Fase 1, chaves UUID, regra do `404` pronta |
| API2 Broken Authentication | token em header (nunca na URL), comparado em tempo constante; recusa do token padrão fora de `local` e `test`. Limite: token único e estático, sem expiração |
| API3 Broken Object Property Level Authorization | todo schema de entrada tem `additionalProperties: false`: o cliente não consegue mandar `saldo` nem `taxa_retida`, que só a ORCA calcula |
| API4 Unrestricted Resource Consumption | corpo de até 64 KiB (`413`), tamanho declarado obrigatório (`411`), até 100 itens na criação de uma cobrança (depois, a inclusão entra um item por requisição), textos de até 255 caracteres, extrato de 1 a 50 lançamentos por página, consulta de até 15 s. Limite: não há limite de requisições por cliente (rate limit), que fica no gateway |
| API5 Broken Function Level Authorization | todas as rotas são do mesmo nível (o operador); `/metrics` exige o token |
| API8 Security Misconfiguration | sem `/docs` e sem OpenAPI público, sem o header `Server`, sem stack trace na resposta de erro, `OPTIONS` também exige o token (DD38) |
| API9 Improper Inventory Management | toda rota está no mapa do RFC (7.1); as rotas de exemplo da base estão identificadas como tal |
| API10 Unsafe Consumption of APIs | a ORCA não consome API de terceiros |

## 9. Autenticação, autorização e TLS

> **Pergunta:** numa rota do seu desafio, o que garante que quem está entrando é quem diz ser (autenticação), e o que garante que, mesmo sendo quem diz ser, ele só vê a própria conta (autorização)?

**Resposta:**

* **Autenticação:** o header `INTERNAL-TOKEN`, exigido em toda rota exceto `/`, `/health_check` e `/health_check/ready`, e comparado em tempo constante. Sem ele, ou com o valor errado, `403` (`QIT000002`). Ele identifica "um sistema interno da administradora", e não uma pessoa.
* **Autorização:** na Fase 1, nenhuma por recurso, pelo motivo da seção 8. Quem passa na autenticação é o operador, e o operador pode ver todas as contas. A autorização por perfil (o proprietário vendo só a própria conta) é o próximo passo, com a resposta já definida (`404`).
* **TLS:** a ORCA fala HTTP simples dentro do compose. Em produção, o TLS termina no balanceador ou gateway na frente dela (HTTPS), e o trecho até a API fica na rede privada. Sem TLS, o `INTERNAL-TOKEN` viaja em texto puro, por isso a porta 3000 nunca deve ficar exposta direto na internet.

## Variáveis de produção

Todas têm padrão no `docker-compose.yml` e estão explicadas no `.env.example`.

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `APP_ENV` | `local` | Fora de `local` e `test`, o log sai de INFO para cima e a API exige um `INTERNAL_TOKEN` próprio com 32 caracteres ou mais |
| `INTERNAL_TOKEN` | `default_token` | O segredo das rotas internas; o padrão só vale fora de produção |
| `MAXIMUM_BODY_BYTES` | `65536` | Tamanho máximo do corpo de uma requisição (`413` acima disso) |
| `DB_LOCK_TIMEOUT_MS` | `5000` | Quanto uma operação espera pela trava da conta (`503` depois disso) |
| `DB_STATEMENT_TIMEOUT_MS` | `15000` | Quanto uma consulta pode durar no banco (`503` depois disso) |
| `DB_CONNECT_TIMEOUT_SECONDS` | `3` | Quanto esperar para abrir uma conexão com o banco (`503` depois disso) |

## Como conferir

Com a API de pé (`docker compose up -d --wait`):

1. **Saúde:**

   ```bash
   curl -i localhost:3000/health_check
   curl -s localhost:3000/health_check/ready
   ```

2. **Métricas:** depois de algumas chamadas, os contadores e o histograma:

   ```bash
   curl -s localhost:3000/metrics -H "INTERNAL-TOKEN: default_token" | grep orca_http
   ```

3. **Logs:** as linhas JSON de uma requisição, pelo `X-Request-ID` que ela devolveu:

   ```bash
   curl -s -D - localhost:3000/contas/00000000-0000-4000-8000-000000000000/saldo -H "INTERNAL-TOKEN: default_token" -H "X-Request-ID: protocolo-1532"
   docker compose logs api --no-log-prefix | grep protocolo-1532
   ```

4. **Readiness sem banco:** a liveness continua `204`, a readiness vai a `503` e volta.

   ```bash
   docker compose stop db
   curl -s -o /dev/null -w "%{http_code}\n" localhost:3000/health_check
   curl -s localhost:3000/health_check/ready
   docker compose start db
   ```

5. **Trava esgotada:** abra um `psql` e segure a trava de uma conta (troque `<CONTA>` pela `conta_chave` de uma conta sua):

   ```bash
   docker compose exec db psql -U bootcamp -d bootcamp
   ```

   ```sql
   BEGIN;
   SELECT id FROM conta WHERE chave = '<CONTA>' FOR UPDATE;
   ```

   Em outro terminal, peça um repasse para a mesma conta. A resposta chega em cerca de 5 segundos, com `503` e `Retry-After: 1`. Depois, rode `ROLLBACK;` no `psql`.

   ```bash
   curl -s -i -X POST localhost:3000/contas/<CONTA>/repasses -H "INTERNAL-TOKEN: default_token" -H "Content-Type: application/json" -H "Idempotency-Key: prova-trava" -d '{"valor_centavos": 1}'
   ```

6. **Recusa do token padrão em produção:**

   ```bash
   docker compose run --rm --no-deps -e APP_ENV=production api python -c "import app"
   ```

   A subida falha com `OSError: Fora dos ambientes local e test, o INTERNAL_TOKEN precisa ser um segredo proprio, com pelo menos 32 caracteres`.

Os comportamentos que dá para provar por HTTP estão em `tests/integration/test_producao.py`, inclusive a trava esgotada: o teste segura a trava direto no banco, como o `DbUtils` da base faz para preparar o banco, e confere tudo por HTTP. A readiness sem banco, o banco fora do ar e a recusa de subida dependem de parar o banco ou de mudar o ambiente, por isso ficaram como os passos 4 e 6.

## O que fica para depois

* Controle de acesso por perfil (autorização por recurso), com a regra do `404` já escrita.
* Limite de requisições por cliente (rate limit), no gateway.
* Tracing distribuído, quando houver mais de um serviço na cadeia.
* Balanceador com mais de uma cópia da API e um pooler de conexões na frente do banco.
* TLS de ponta a ponta, se a rede entre o gateway e a API não for privada.
* Rotação do `INTERNAL_TOKEN` sem derrubar a API (aceitar o token antigo e o novo por um período).
