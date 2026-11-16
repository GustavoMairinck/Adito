# Oráculo ESX — Desktop

Assistente de BI: você pergunta em português, o agente gera o SQL, executa nos seus dados e devolve resposta, tabela e gráfico. Esta é a versão desktop (Tauri) do Oráculo-ESX web: roda inteira na máquina, sem Docker, Postgres ou Redis.

- **Janela:** Tauri (Rust) carregando o front Vue.
- **Backend:** Django + LangGraph, iniciado pelo próprio app numa porta livre de `127.0.0.1`.
- **Dados:** dois arquivos SQLite na pasta do usuário — `app.db` (conversas, dashboards, contextos) e `dados.db` (seus dados, aberto só para leitura).
- **LLM:** Gemini; cada usuário informa a própria chave, guardada no cofre do sistema.

As decisões do porte estão em [../docs/](../docs/): as user stories em [../docs/stories/](../docs/stories/) e o registro completo em [../docs/PORTE_DESKTOP_DECISOES.md](../docs/PORTE_DESKTOP_DECISOES.md).

> **Este guia é para desenvolvimento.** Por enquanto o app roda só a partir do código, por isso pede Python, Node e Rust (e, no Windows, o Visual Studio Build Tools). Quando o projeto estiver completo, haverá instaladores (`.exe` no Windows; `.deb`/`.AppImage` no Linux) que rodam sem nenhuma dessas ferramentas. Antes disso é preciso empacotar o backend Python com PyInstaller.

---

## 1. Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| Python | 3.11 ou mais nova (testado na 3.14) | backend |
| Node.js | 20 ou mais nova (testado na 22) | front |
| Rust | estável, via [rustup](https://rustup.rs) | janela Tauri |
| Chave do Gemini | — | chat ([Google AI Studio](https://aistudio.google.com/apikey)) |

### Linux (Ubuntu/Debian)

Bibliotecas do Tauri:

```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev python3-venv
```

Rust:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Depois abra um terminal novo (ou rode `source ~/.cargo/env`) e confirme com `cargo --version`.

A chave do Gemini fica no **Secret Service** (GNOME Keyring ou KWallet), que já vem nos desktops comuns.

### Windows 10/11

> **Só para desenvolvimento.** O Build Tools abaixo é exigido apenas de quem compila o projeto no Windows, porque o Rust usa o linker da Microsoft. Quando o projeto estiver completo, haverá um instalador `.exe` que roda sem Visual Studio, Rust, Node ou Python.

1. Instale o [Python](https://www.python.org/downloads/) marcando **"Add python.exe to PATH"**.
2. Instale o [Node.js LTS](https://nodejs.org).
3. Instale o Visual Studio Build Tools. Basta o compilador e o SDK (2 a 3 GB, em vez da carga completa de 6 a 8 GB):
   ```powershell
   winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621"
   ```
   Sem `winget`, use o [instalador](https://visualstudio.microsoft.com/visual-cpp-build-tools/) e marque a carga **"Desenvolvimento para desktop com C++"**.
4. Instale o Rust com o [rustup-init.exe](https://rustup.rs).
5. O WebView2 já vem no Windows 10/11 atualizado.

A chave do Gemini fica no **Gerenciador de Credenciais** do Windows.

---

## 2. Instalar as dependências (uma vez)

Todos os comandos partem desta pasta (`Adito/app`).

### Backend Python

O app procura o Python em `.venv/` dentro de `Adito/app` — o nome e o lugar importam.

Linux:

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r backend/requirements.txt
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
```

> Para usar outro Python, defina `ORACULO_PYTHON` com o caminho do executável antes de abrir o app.

### Front

```bash
cd frontend-vue && npm install
```

A primeira compilação do Rust baixa as dependências e leva de 3 a 10 minutos; as seguintes levam segundos.

---

## 3. Colocar dados no app

O app lê tudo da pasta de dados do usuário:

| Sistema | Pasta |
|---|---|
| Linux | `~/.local/share/br.edu.ifes.leds.oraculo-esx/` |
| Windows | `%LOCALAPPDATA%\br.edu.ifes.leds.oraculo-esx\` |

Ela é criada na primeira abertura. Dentro dela o app espera:

```text
dados.db               seus dados (SQLite, com as views que o agente pode consultar)
contexts/<nome>/       um contexto por pasta: views.json, rules.md, examples.json
```

### Usar a demonstração de vendas

Esta pasta traz a mesma demo de vendas do Oráculo web (1.200 vendas) e um contexto pronto para ela.

Linux:

```bash
D=~/.local/share/br.edu.ifes.leds.oraculo-esx; mkdir -p "$D/contexts" && .venv/bin/python scripts/gerar_dados_demo.py "$D/dados.db" && cp -r contexts/exemplo-vendas "$D/contexts/"
```

Windows (PowerShell):

```powershell
$D = "$env:LOCALAPPDATA\br.edu.ifes.leds.oraculo-esx"
New-Item -ItemType Directory -Force "$D\contexts" | Out-Null
.venv\Scripts\python scripts\gerar_dados_demo.py "$D\dados.db"
Copy-Item -Recurse contexts\exemplo-vendas "$D\contexts\"
```

### Usar os seus próprios dados

1. Gere um arquivo SQLite com as views que o agente pode ler e copie para `dados.db` na pasta acima. O app não cria views: tudo o que ele consulta precisa existir no arquivo.
2. Crie uma pasta em `contexts/` seguindo o modelo de [contexts/exemplo-vendas](contexts/exemplo-vendas):
   - `views.json` — views expostas, colunas sensíveis (nunca saem para a LLM), colunas indexadas para busca semântica e limite de linhas enviadas à LLM.
   - `rules.md` — regras de negócio e métricas, em texto livre.
   - `examples.json` — pares pergunta → SQL que o agente usa como referência.

---

## 4. Rodar

São dois terminais, ambos a partir de `Adito/app`.

**Terminal 1 — front (deixe aberto):**

```bash
cd frontend-vue && npm run dev
```

Ele precisa ficar na porta **5173**. Se acusar porta ocupada, feche o outro Vite que estiver rodando.

**Terminal 2 — app:**

```bash
cd src-tauri && cargo run
```

A janela abre em alguns segundos, e o backend sobe junto. Fechar a janela encerra o backend.

### Primeira vez no app

1. **Para usar o chat**, abra **Configurações** → cole a chave do Gemini → **Salvar**. O app testa a chave antes de guardar.
2. **Administração** → **Carregar Contextos**. Valida os contextos e, com a chave configurada, gera os embeddings. A exploração das tabelas funciona com os contextos validados.
3. **Chat** → escolha o contexto e pergunte, por exemplo: "qual a receita líquida por região?".

Mudou algo em `contexts/` ou trocou o `dados.db`? Repita o passo 2.

### Explorar os dados do Adito

Em **Explorar dados**, selecione um contexto e uma relação no catálogo. A tela oferece
busca textual, filtro por valor exato de uma coluna, ordenação pelos cabeçalhos e
paginação de 25, 50 ou 100 registros. Em **Estrutura e colunas visíveis**, consulte os
tipos e escolha as colunas da tabela. A visualização **Gráfico** conta os registros
por valor da coluna escolhida, considerando todos os resultados filtrados e exibindo
até 12 grupos.

O catálogo segue as relações já expostas em `views.json`, incluindo as entidades do
modelo UML unificado. Cada entrada aceita os campos opcionais `label` (nome exibido)
e `kind` (`fact`, `dimension` ou `entity`). Por exemplo, uma entrada de `iniciativa`
do modelo unificado pode ser declarada assim, quando essa relação existir no SQLite.

```json
{
  "name": "iniciativa",
  "label": "Iniciativas de pesquisa e extensão",
  "description": "Iniciativas institucionais do modelo unificado.",
  "kind": "entity"
}
```

Sem `kind`, os prefixos `fact`/`fato` e `dim_`/`dimensao_` identificam fatos e dimensões
(também após `v_`/`vw_`). As demais relações aparecem como entidades. Use `kind`
para classificar relações com outras convenções de nomes. Os contextos existentes
continuam compatíveis.

As consultas usam o `dados.db` SQLite do desktop, aberto para leitura, e respeitam
as colunas sensíveis declaradas no contexto. A exploração funciona com os contextos
carregados mesmo sem chave do Gemini. O DDL PostgreSQL em `../scripts/sql/` documenta
o modelo unificado. Para consultá-lo nesta versão, disponibilize suas relações no
`dados.db` e no contexto correspondente.

---

## 5. Problemas comuns

| Sintoma | Causa e solução |
|---|---|
| Janela branca ou "não abriu nada" | O Vite não está na porta 5173. Confira o terminal 1. |
| "O backend encerrou" / "não respondeu em 90 s" | Veja o log: `~/.local/share/br.edu.ifes.leds.oraculo-esx/logs/backend.log` (Linux) ou `%LOCALAPPDATA%\br.edu.ifes.leds.oraculo-esx\logs\backend.log` (Windows). Em geral falta o `.venv` ou alguma dependência do `pip`. |
| Chat desativado com aviso de chave | Salve a chave em **Configurações**. |
| Não salva a chave no Linux | O Secret Service não está rodando. Abra o "Senhas e chaves" (Seahorse) uma vez ou instale `gnome-keyring`. |
| Agente diz que não há contexto | Faltou `contexts/<nome>/views.json` na pasta de dados ou rodar **Carregar Contextos**. |
| `cargo: comando não encontrado` | Abra um terminal novo depois de instalar o Rust, ou rode `source ~/.cargo/env`. |

Se o app for morto à força (sem fechar a janela), o backend pode ficar rodando. No Linux, encerre com `pkill -f desktop_server.py`.

---

## 6. Testes do núcleo

Linux, a partir de `backend/api` (usa uma pasta de dados temporária, sem tocar na do app):

```bash
export ORACULO_DATA_DIR=/tmp/oraculo-teste JWT_SECRET=x GEMINI_API_KEY=x && mkdir -p $ORACULO_DATA_DIR && ../../.venv/bin/python manage.py migrate -v0 && ../../.venv/bin/python ../../scripts/teste_nucleo_sqlite.py "$PWD"
```

Não chama o Gemini: a chave `x` e os embeddings são falsos. Verifica leitura só-leitura do `dados.db`, bloqueio de colunas sensíveis, validação de SQL, contextos e a demo. Deve terminar em `0 falha(s)`.

Os testes da exploração ficam em `core/tests.py`. Após definir `ORACULO_DATA_DIR`
para uma pasta temporária, execute `python manage.py test core` em `backend/api`
com o Python do ambiente virtual. Eles cobrem catálogo, busca, filtros, paginação,
agrupamentos, isolamento de contextos e bloqueio de colunas sensíveis.

---

## Estrutura

```text
src-tauri/          janela Tauri: inicia o backend, guarda a chave no cofre do SO
frontend-vue/       front Vue/Vite
backend/api/        Django, agentes (LangGraph), chat, dashboard
contexts/           contexto de exemplo (demo de vendas)
scripts/            geração da demo e testes do núcleo
backend/training/   schema da demo de vendas (lido por scripts/gerar_dados_demo.py)
mudanças/mudanca/   dados da demo de vendas (lidos por scripts/gerar_dados_demo.py)
```

Ao atualizar da integração Mistral, execute as migrações do backend e carregue os contextos novamente para gerar os índices com Gemini. Use `GEMINI_API_KEY` no `.env` para desenvolvimento. O modelo padrão é `gemini-3.5-flash-lite`, ajustável com `GEMINI_MODEL`.
