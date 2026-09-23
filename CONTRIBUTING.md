# Como contribuir

Este guia é o combinado do time: como criar branches, escrever commits e abrir pull requests. Siga-o do começo ao fim até virar hábito.

## As branches

| Branch | Para que serve | Quem escreve nela |
|---|---|---|
| `main` | Versão estável, a que é entregue. | Ninguém escreve direto. Só recebe merge de `develop`, quando o time decide que está pronto. |
| `develop` | Onde o trabalho de todo mundo se junta. É a base de toda branch nova. | Ninguém escreve direto. Só recebe pull requests. |
| `tipo/descricao-curta` | O seu trabalho do momento. | Você. |

O nome da sua branch começa pelo tipo de trabalho:

| Prefixo | Quando usar | Exemplo |
|---|---|---|
| `feat/` | funcionalidade nova | `feat/cadastro-de-proprietario` |
| `fix/` | correção de bug | `fix/rateio-arredondamento` |
| `docs/` | só documentação | `docs/modelagem-do-dominio` |
| `test/` | só testes | `test/extrato-por-periodo` |
| `refactor/` | reorganizar código sem mudar o comportamento | `refactor/repository-de-pagamento` |
| `chore/` | configuração, dependências, Docker | `chore/atualiza-compose` |

Use letras minúsculas, palavras separadas por hífen e nada de acento ou espaço.

## O passo a passo de uma tarefa

**1. Comece sempre de um `develop` atualizado:**

```bash
git switch develop
git pull
git switch -c feat/nome-da-tarefa
```

**2. Trabalhe e faça commits pequenos,** cada um com uma ideia só:

```bash
git add caminho/do/arquivo.py
git commit -m "feat: cria tabela de proprietarios"
```

Prefira `git add` com o caminho do arquivo em vez de `git add .`: assim nada entra por acidente (um `.env`, uma planilha, um arquivo de teste solto).

**3. Antes de abrir o PR,** traga o que os outros já juntaram em `develop` e confira os testes:

```bash
git pull origin develop
pytest
```

Se o `git pull` avisar de conflito, abra os arquivos marcados, escolha o que fica, e finalize com `git add` + `git commit`. Travou? Peça ajuda no canal antes de apagar qualquer coisa.

**4. Envie a branch:**

```bash
git push -u origin feat/nome-da-tarefa
```

**5. Abra o pull request no GitHub,** com **base: `develop`**. Não use `main`! O modelo de descrição aparece sozinho: preencha.

**6. Revisão:** pelo menos **uma pessoa do time** aprova antes do merge. Quem revisa roda o projeto na própria máquina quando a mudança mexe em comportamento.

**7. Depois do merge,** apague a branch no GitHub (botão *Delete branch*) e volte ao passo 1 para a próxima tarefa.

## Mensagens de commit

O formato é `tipo: o que mudou`, no presente e em português. Os tipos são os mesmos dos prefixos de branch:

```
feat: adiciona rota de cadastro de proprietario
fix: corrige arredondamento do rateio em centavos
docs: explica a maquina de estados do pagamento
test: cobre repasse com taxa de administracao
refactor: separa calculo de taxa do controller
chore: fixa versao do postgres no compose
```

Um bom teste: a mensagem completa a frase *"se aplicado, este commit…"*.

## Antes de pedir revisão

- [ ] `pytest` passa inteiro na sua máquina.
- [ ] Nenhum `.env`, senha, token ou dado real entrou no commit.
- [ ] Mudou o `database/database.sql`? Então rodou `docker compose down -v` e testou com o banco recriado.
- [ ] Criou um erro novo? Ele tem código próprio em `src/errors/custom_errors.py` (sem repetir número).
- [ ] Mudou como algo se usa? Atualizou o README ou a pasta `docs/`.

## Regras do projeto que valem para todo PR

Elas vêm da arquitetura da base. O motivo de cada uma está em [docs/como-o-projeto-e-organizado.md](docs/como-o-projeto-e-organizado.md).

- **A seta anda num sentido só:** `resources → controllers → repositories → models`.
- **Nenhum `raise` em `resources/`:** quem recusa é o schema (formato) ou o controller (regra).
- **Só o `repository` escreve consulta.** Só o `controller` dá `commit`.
- **Dinheiro é inteiro em centavos,** nunca `float`.
