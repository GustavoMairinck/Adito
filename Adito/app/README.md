# Adito — Desktop

Assistente de BI: você pergunta em português, o agente gera o SQL, executa nos seus dados e devolve resposta, tabela e gráfico. Esta é a versão desktop (Tauri) do Oraculo-ESX web: roda inteira na máquina, sem Docker, Postgres ou Redis.

- **Janela:** Tauri (Rust) carregando o front Vue.
- **Núcleo:** Python + LangGraph, iniciado pelo próprio app como processo filho. Não abre porta de rede: conversa com a janela por stdin/stdout ([../docs/NUCLEO_LOCAL_SEM_HTTP.md](../docs/NUCLEO_LOCAL_SEM_HTTP.md)).
- **Dados:** dois arquivos SQLite na pasta do usuário — `app.db` (conversas, dashboards, contextos) e `dados.db` (seus dados, aberto só para leitura).
- **LLM:** Gemini; cada usuário informa a própria chave, guardada no cofre do sistema.

As decisões do porte estão em [../docs/](../docs/): as user stories em [../docs/stories/](../docs/stories/) e o registro completo em [../docs/PORTE_DESKTOP_DECISOES.md](../docs/PORTE_DESKTOP_DECISOES.md).

> **Este guia é para desenvolvimento.** Por enquanto o app roda só a partir do código, por isso pede Python, Node e Rust (e, no Windows, o Visual Studio Build Tools). Quando o projeto estiver completo, haverá instaladores (`.exe` no Windows; `.deb`/`.AppImage` no Linux) que rodam sem nenhuma dessas ferramentas. Antes disso é preciso empacotar o núcleo Python com PyInstaller.

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

> Para usar outro Python, defina `ADITO_PYTHON` com o caminho do executável antes de abrir o app.

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
| Linux | `~/.local/share/br.edu.ifes.leds.adito/` |
| Windows | `%LOCALAPPDATA%\br.edu.ifes.leds.adito\` |

Ela é criada na primeira abertura. Dentro dela o app espera:

```text
dados.db               seus dados (SQLite, com as views que o agente pode consultar)
contexts/<nome>/       um contexto por pasta: views.json, rules.md, examples.json
```

### Usar os seus próprios dados

1. Gere um arquivo SQLite com as views que o agente pode ler e copie para `dados.db` na pasta acima. O app não cria views: tudo o que ele consulta precisa existir no arquivo.
2. Crie uma pasta em `contexts/` seguindo o modelo de [contexts/pesquisa-extensao-ifes](contexts/pesquisa-extensao-ifes):
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

A janela abre em alguns segundos, e o núcleo sobe junto. Fechar a janela (ou o app morrer) encerra o núcleo.

Atalho: `../../rodar_desktop.sh` (na raiz do repositório) sobe o Vite e a janela de uma vez.

### Primeira vez no app

1. **Para usar o chat**, abra **Configurações** → cole a chave do Gemini → **Salvar**. O app testa a chave antes de guardar.
2. **Administração** → **Carregar Contextos**. Valida os contextos e, com a chave configurada, gera os embeddings.
3. **Chat** → escolha o contexto e pergunte, por exemplo: "quantas ações de extensão foram cadastradas por ano?".

Mudou algo em `contexts/` ou trocou o `dados.db`? Repita o passo 2.

---

## 5. Problemas comuns

| Sintoma | Causa e solução |
|---|---|
| Janela branca ou "não abriu nada" | O Vite não está na porta 5173. Confira o terminal 1. |
| "O Adito não conseguiu iniciar" / "O núcleo do Adito encerrou" / "não respondeu em 90 s" | Veja o log: `~/.local/share/br.edu.ifes.leds.adito/logs/backend.log` (Linux) ou `%LOCALAPPDATA%\br.edu.ifes.leds.adito\logs\backend.log` (Windows). Em geral falta o `.venv` ou alguma dependência do `pip`. |
| Chat desativado com aviso de chave | Salve a chave em **Configurações**. |
| Não salva a chave no Linux | O Secret Service não está rodando. Abra o "Senhas e chaves" (Seahorse) uma vez ou instale `gnome-keyring`. |
| Agente diz que não há contexto | Faltou `contexts/<nome>/views.json` na pasta de dados ou rodar **Carregar Contextos**. |
| `cargo: comando não encontrado` | Abra um terminal novo depois de instalar o Rust, ou rode `source ~/.cargo/env`. |

---

## 6. Testes do núcleo

Nenhum chama o Gemini nem usa rede: os dados são sintéticos e o LLM é falso. Todos usam pastas temporárias, sem tocar na pasta de dados do app.

A partir de `Adito/app`:

```bash
.venv/bin/python scripts/teste_contrato.py
```

Compara cada chamada que as telas fazem (status e JSON) com a referência gravada quando o núcleo ainda era um servidor Django. Deve terminar em `50/50 chamadas iguais à referência.`

```bash
.venv/bin/python scripts/teste_stdio.py
```

Sobe o núcleo como o Tauri faz e testa o protocolo stdin/stdout: evento de pronto, pedidos simultâneos, erros, cancelamento e encerramento quando o stdin fecha.

A partir de `backend/nucleo`:

```bash
../../.venv/bin/python -m unittest core.tests
```

Cobre a segurança do SQL, os contextos, a chave do Gemini, os agentes e a persistência e a migração do `app.db`.

### Manutenção

A partir de `backend/nucleo`, com o mesmo `app.db` do app (ou outro, via `ADITO_DATA_DIR`):

```bash
../../.venv/bin/python -m core.cli --help
```

Comandos `load-context`, `sync-embeddings`, `rebuild-embeddings` e `flush-data` (substituem os antigos do `manage.py`).

---

## Estrutura

```text
src-tauri/          janela Tauri: inicia o núcleo e fala com ele por stdin/stdout; guarda a chave no cofre do SO
frontend-vue/       front Vue/Vite
backend/nucleo/     núcleo local: rpc/ (métodos e protocolo), core/ (app.db, contextos, SQLite), agentes (LangGraph)
contexts/           contexto de dados (pesquisa e extensão do IFES)
scripts/            testes do núcleo
```

Ao atualizar da integração Mistral, o núcleo zera os vetores antigos na primeira abertura; carregue os contextos novamente para gerar os índices com Gemini. Use `GEMINI_API_KEY` no `.env` para desenvolvimento. O modelo padrão é `gemini-3.5-flash-lite`, ajustável com `GEMINI_MODEL`.
