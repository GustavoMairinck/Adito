# Porte do Oráculo-ESX para desktop: decisões e pendências

Compilado em 2026-11-03 a partir da conversa de planejamento e atualizado durante a implementação, até 2026-11-04. Os caminhos de arquivo são relativos a [`../app/`](../app/). As user stories em [`stories/`](stories/) resumem cada decisão.

Objetivo: gerar o Oráculo-ESX como aplicativo desktop (Windows e Linux). O app não depende de nenhuma fonte de dados específica: os dados e as views serão fornecidos depois pelo usuário e não têm relação com SigPesq nem Horizon. Ordem de grandeza a suportar: cerca de 50 mil registros de alunos. (Versão anterior deste documento amarrava várias decisões ao SigPesq/Horizon; isso foi removido em 2026-11-03.)

## 1. Decidido

| Tema | Decisão |
|---|---|
| Casca | Tauri, front Vue existente e backend Python como sidecar |
| Sistemas | Windows e Linux (sem macOS) |
| Banco | SQLite para tudo (metadados Django, dados analíticos fornecidos pelo usuário, vetores) |
| Vetores | sqlite-vec ou numpy; decidir após contar os `KnowledgeItem` |
| Redis | Removido. O estado da conversa do LangGraph vai para `langgraph-checkpoint-sqlite` |
| Onde gravar | Pasta de dados do usuário: XDG data / `~/.cache` no Linux, `%LOCALAPPDATA%` no Windows. Nunca `/var` nem `%APPDATA%` (Roaming) |
| Cache de consultas | Se existir, guarda pergunta → SQL gerado, não as linhas (LGPD). Chave: pergunta normalizada + tenant + identificador da carga de dados atual (por exemplo hash ou data de modificação do arquivo de dados) |
| Tenant | Fixo: uma linha criada no primeiro start, um par de arquivos (`app.db` e `dados.db`) por tenant. Saem só `db_schema_name`, `SET search_path` e o prefixo de schema no SQL. FKs de tenant e `thread_id` ficam |
| Autenticação | **Sem login local** (decidido em 2026-11-03). Um usuário local único é criado no primeiro start e o app abre direto. Saem Acesso Cidadão, gateway C#, `JWT_SECRET` e as telas de login |
| Chave do LLM | **O usuário informa a própria chave** (decidido em 2026-11-03), guardada no cofre do sistema operacional. Nenhuma chave vai embutida no instalador. Hoje só a chave da Mistral é usada |
| Dados enviados ao LLM | **Mascarar e limitar** (decidido em 2026-11-03): views por contexto sem colunas sensíveis, limite de linhas no prompt, embeddings só de campos não pessoais (nomes de pessoas por busca local) e aviso ao usuário. Detalhes na seção "Política de dados enviados ao LLM" |
| Arquivos de banco | **Separados** (decidido em 2026-11-03): `app.db` (Django, conversas, dashboards, checkpoints, cache, índices derivados) e `dados.db` (dados do usuário, aberto só para leitura, nunca escrito pelo app) |
| Processos | **Servidor MCP no mesmo processo** (decidido em 2026-11-03): a ferramenta `bi_agent` vira função local, some a porta 8005. Backend ASGI (`daphne`) em `127.0.0.1`, porta livre, com token efêmero do Tauri (consequência de "sem login") |
| Criptografia | **Só criptografia de disco do SO na primeira versão** (decidido em 2026-11-03): BitLocker no Windows e LUKS no Linux. Sem SQLCipher por ora. O app avisa no primeiro uso e a documentação diz que a proteção é a conta do SO mais a criptografia de disco. Revisar se a política da instituição exigir cifra no próprio arquivo |
| Histórico do chat | **Guarda só o SQL** (decidido em 2026-11-03): as linhas de resultado não são gravadas; ao abrir a conversa o app reexecuta o SQL no `dados.db` (só leitura), sob demanda |
| Entrada de dados | **Arquivo SQLite pronto** (decidido em 2026-11-03): o usuário aponta um `.db` que já tem as views, junto com o `views.json` de cada contexto. Importar CSV/XLSX fica para depois. O app **copia** o arquivo para a pasta de dados do usuário (decidido em 2026-11-03); a cópia vira o `dados.db`, identificada por hash |
| Views | **Só views do arquivo** (decidido em 2026-11-03): views de views funcionam nativamente; o app não cria views. Só as views expostas entram no `views.json` |
| Contextos | **Modelo `Contexto` novo** (decidido em 2026-11-03), com o tenant fixo. Um contexto é um pacote de views, RAG, regras, filtros e colunas sensíveis. Detalhes na seção 2 |

### Consequências de não ter login

- O Django continua precisando de um `User` (conversas, dashboards e auditoria têm FK de usuário). Ele passa a ser uma linha fixa criada no primeiro start, sem senha usada.
- A API deixa de depender de JWT do gateway. Como o backend ouve só em `127.0.0.1`, o Tauri gera um token efêmero a cada execução e o front o envia; assim outro processo da máquina não chama a API. Detalhes a confirmar em `backend/api/core/authentication.py`.
- No front, saem a rota de login, o `useAuth` e o token em `sessionStorage`.
- Some a separação entre usuários: quem abre a conta do sistema operacional vê tudo. A proteção passa a ser a conta do SO e a criptografia de disco (ver a decisão de criptografia).
- Sem superusuário padrão (`admin`).

### Consequências de o usuário informar a chave

- Todos os LLMs do orquestrador e do servidor MCP usam Mistral (router, conversational, reflection, report e o agente BI), e os embeddings também. Gemini aparece só em `backend/api/agents/config.py:6-8`, sem uso encontrado. O app precisa de **uma** chave, a da Mistral.
- Guardar no cofre do SO: Credential Manager no Windows e Secret Service no Linux. Distros mínimas podem não ter Secret Service; precisa de plano B (não verificado), por exemplo arquivo cifrado com senha do usuário.
- Entregar ao sidecar por variável de ambiente no momento de subir o processo, sem gravar em disco e sem `.env`.
- Primeiro uso: tela de configuração que pede a chave e valida com uma chamada de teste. Sem chave, chave inválida, cota esgotada ou sem internet: o app abre, o chat fica desativado e mostra o motivo.
- Langfuse (telemetria externa) fica desligado por padrão.

### Política de dados enviados ao LLM (mascarar e limitar)

Três caminhos levam dados do banco para a Mistral:

| Caminho | Onde está | Controle |
|---|---|---|
| Linhas de resultado no histórico da conversa | Corrigido em 2026-11-03: `reflection.py` e `report.py` não estão ligados a nenhum grafo (código morto). O caminho vivo é a prévia de 5 linhas que `oraculo_mcp_server.py` põe no `final_content`; ela entra nas mensagens da conversa e volta ao LLM nas próximas perguntas | Views do contexto sem colunas sensíveis; prévia limitada; preferir agregados |
| Valores únicos embedados para resolver nomes | `analytics_index/services.py:104` e `analytics_index/config.py` | Embedar só campos não pessoais; nomes de pessoas resolvidos localmente no SQLite (FTS5 ou busca por prefixo) |
| Pergunta do usuário, DDL e exemplos no prompt de geração de SQL | agente BI | Inevitável: avisar que nomes digitados na pergunta são enviados |

Regras:
- **Colunas:** as views do contexto deixam as sensíveis de fora (por exemplo CPF, e-mail, telefone, data de nascimento, nome completo de aluno). Defesa extra: `set_authorizer` do SQLite nega a leitura de qualquer coluna fora da lista do contexto, mesmo que o SQL gerado tente.
- **Limite de linhas: só no prompt do LLM.** Dashboards, gráficos e tabelas usam todas as linhas: o SQL roda localmente no `dados.db` e o resultado completo vai para a tela, sem passar pelo LLM. O limite vale apenas para as linhas copiadas para o prompt de reflexão e de relatório. Para agregações o resultado já é pequeno; para listagens o LLM só precisa de uma amostra para descrever. **Padrão: 20 linhas** (decidido em 2026-11-03; hoje 50, via `REACT_MAX_ROWS`). Cada contexto pode sobrescrever com `llm_row_limit`.
- **Execução sem corte para exibição** (decidido em 2026-11-03): hoje `execute_query` corta em 100 linhas (`backend/api/agents/bi_agent/agent.py:31`, `LIMIT {max_rows}`). No desktop esse corte sai do caminho de exibição; a tabela da interface pagina, sem perder linhas.
- **Aviso:** tela no primeiro uso explicando o que sai da máquina (pergunta, esquema, resultados limitados, valores não pessoais) e indicador na interface quando uma resposta usou dados enviados.
- **Modo só agregados (opcional):** nenhuma linha individual vai ao LLM.
- **Langfuse:** desligado por padrão.
- **Fora do escopo por ora:** pseudonimização com re-substituição (trocar nomes por tokens antes de enviar e voltar depois). Fica como melhoria futura.

### Consequências de separar `app.db` e `dados.db`

- **`app.db`** (na pasta de dados do usuário): Django, conversas, dashboards, checkpoints do LangGraph, cache, embeddings do RAG e índice de busca local (FTS5). Backup antes de cada migração.
- **`dados.db`:** fornecido pelo usuário e nunca escrito pelo app. O agente o abre com `sqlite3` em modo só leitura (`file:...?mode=ro` com `uri=True`), mais `PRAGMA query_only=ON` e o `set_authorizer` do contexto. Isso substitui o `psycopg2` de `agents/bi_agent/agent.py:39` e `agents/bi_agent/nodes/sql_validator.py:45`.
- O Django gerencia só o `app.db`; não há models para o `dados.db`.
- Índices derivados (embeddings, FTS5, cache de SQL) ficam no `app.db` e são reconstruídos a cada nova carga, identificados por hash ou data de modificação do `dados.db`.
- Ao trocar os dados, o app compara o esquema das views (nomes e tipos de colunas). Se mudou, avisa, reindexa e marca os widgets como desatualizados para revalidar o `sql_validated` (o `Widget` já tem o campo `status`).
- Risco: streaming do chat, checkpointer e ORM escrevendo ao mesmo tempo no `app.db` podem gerar `database is locked`. O modo WAL com `busy_timeout` costuma bastar; se não, os checkpoints vão para um arquivo próprio. Não verificado.

### Consequências do MCP no mesmo processo

- Só existe uma ferramenta MCP, a `bi_agent` (`backend/api/agents/oraculo_mcp_server.py:40`). Hoje o servidor escuta em `0.0.0.0:8005` sem autenticação; no desktop isso deixa de existir.
- Extrair o corpo da ferramenta para uma função ou `StructuredTool` local com o mesmo nome e descrição. O router (`agents/orchestrator/router.py:15`) e o nó de ferramenta (`agents/orchestrator/graph.py:37`) continuam funcionando sem mudar o contrato (retorno em JSON dentro de string).
- O `.ask()` do agente é síncrono e hoje roda em outro processo. No mesmo processo bloquearia o loop assíncrono do streaming SSE; envolver com `asyncio.to_thread`.
- Carregar a lista de ferramentas uma vez na inicialização. Hoje cada requisição abre um cliente MCP com timeout de 30 s e troca as globais `mcp_tools` (`backend/api/chat/stream_views.py:203-216`).
- Remover: `fastmcp`, `mcp`, `langchain-mcp-adapters`, a porta 8005, o serviço `oraculo_esx_mcp`, `ORACULO_MCP_URL` e a duplicata de `mcp_client.py` (existe em `agents/orchestrator/` e em `agents/orchestrator/tools/`).
- O `CallbackHandler` do Langfuse criado dentro da ferramenta vira opcional, desligado por padrão.
- Backend ASGI: `daphne` já está no `requirements.txt` e em `INSTALLED_APPS`. Subir em `127.0.0.1`, porta livre, com o token efêmero do Tauri. Tratado como decidido por ser consequência de "sem login".

### Consequências de o histórico guardar só o SQL

- Parar de gravar `data` em `Message.metadata` nos dois pontos de persistência: `backend/api/chat/stream_views.py:84` e `backend/api/chat/views.py:279`.
- Novo endpoint que reexecuta o `metadata.sql` de uma mensagem no `dados.db` (só leitura), com o mesmo limite de linhas, timeout e authorizer do contexto.
- Front: `frontend-vue/src/modules/chat/composables/useChatHistory.ts:30` monta a tabela a partir de `metadata.data`. Passa a carregar as linhas sob demanda, por mensagem visível ou expandida (não todas ao abrir a conversa), com indicador de carregamento.
- Se o esquema mudou e o SQL falha: mostrar "os dados mudaram, refaça a pergunta" em vez de erro técnico.
- Os resultados passam a refletir os dados atuais, não os do momento da pergunta. Os widgets do dashboard já funcionam assim (guardam `sql_validated`).
- O `app.db` é novo no desktop, então não há conversas antigas para migrar.
- Resíduo aceito: o texto da resposta (`Message.content`) e a `explanation` continuam gravados e podem citar valores.

### Por que SQLite e não Postgres

- Volume é pequeno: 50 mil alunos são dezenas de MB. Qualquer opção responde em milissegundos.
- Docker Postgres: inviável para usuário final.
- Postgres embutido: viável, mas exige pgvector compilado por sistema (sem binário oficial para Windows), assinatura dos executáveis, ciclo de vida `initdb`/porta/desligamento e fixar a versão major. Custo recorrente de manutenção.
- DuckDB: plano B só para leitura, caso uma consulta analítica fique lenta. Pode abrir o mesmo arquivo com `ATTACH`.

### Por que manter o tenant (fixo)

- Cerca de 150 referências em 30 arquivos (RAG, conversas, dashboards, auditoria, `thread_id`).
- Manter o modelo preserva compatibilidade com a versão web (`oraculo.agentes.leds.dev.br`) e deixa um caminho barato para multi-instituição (um arquivo por tenant).
- A única parte que não existe em SQLite é o schema; essa sai.

## 2. Decidido: vários contextos e várias views (modelo `Contexto` novo)

Hoje só existe uma view. Para ter vários contextos em chats e dashboards:

- Criar um modelo `Contexto` (o tenant continua fixo). Alternativa descartada: reusar linhas de `Tenant` como contextos (mais barato, mas mistura organização com assunto e amarra o usuário a um tenant só).
- Um contexto é um pacote: views permitidas, DDL/doc/exemplos do RAG, regras de métrica do prompt e lista de filtros do dashboard. Sugestão de estrutura: `contexts/<slug>/ddl.sql`, `rules.md`, `examples.json`, `filters.json`, `views.json`.
- Um contexto por grupo de views de mesma granularidade (por exemplo, uma view de eventos e outra de entidades que não casam linha a linha ficam em contextos separados, para o agente não somar coisas incompatíveis). Perguntas que cruzam contextos exigem uma view de junção feita por quem fornece os dados, não JOIN pedido ao LLM. As views vêm prontas do usuário; o app só as lê.
- Validador de SQL passa de `tabelas == {view fixa}` para `tabelas ⊆ views do contexto`. Atenção: o nome de um CTE aparece como tabela no parse do sqlglot.
- Defesa no banco: `set_authorizer` do SQLite permitindo `SELECT` só nas views do contexto. Como o agente vê só views, colunas sensíveis (CPF, nome completo) podem ficar de fora.
- Chat: contexto escolhido ao criar a conversa e fixo nela (seletor explícito; o orquestrador pode só sugerir).
- Dashboard: contexto por widget; filtros globais só valem para widgets cujo contexto declara o filtro.
- Riscos: cada contexto exige DDL, regras e exemplos mantidos e testados; o prompt cresce se juntar contextos; mais uma FK em cerca de 5 modelos e uma migration.

Rascunho do `views.json` de um contexto (a validar):

```json
{
  "contexto": "nome-do-contexto",
  "views": [
    {
      "name": "nome_da_view",
      "description": "o que cada linha representa",
      "sensitive_columns": ["cpf", "email"],
      "embed_columns": ["categoria", "status"],
      "local_search_columns": ["nome_pessoa"]
    }
  ],
  "llm_row_limit": 20
}
```

- `sensitive_columns`: o agente não enxerga (authorizer) e nunca vão ao LLM.
- `embed_columns`: campos não pessoais cujos valores únicos são embedados.
- `local_search_columns`: nomes de pessoas resolvidos por busca local (FTS5), sem embedding.
- `llm_row_limit`: limite de linhas enviadas ao LLM neste contexto; sobrescreve o padrão.

### Views de views (testado em SQLite 3.46.1, 2026-11-03)

- **Funciona nativamente no arquivo fornecido.** Testado com três níveis (`v_resumo` → `v_cursos` → `v_base` → tabela).
- **Só as views expostas entram no `views.json`.** O authorizer recebe o nome da view mais interna responsável por cada leitura. Regra testada: no nível de cima, só views expostas e colunas não sensíveis; leituras feitas de dentro de uma view são liberadas. Resultado: view exposta funciona, view intermediária e tabela base são negadas se o SQL gerado tentar acessá-las direto, e subconsulta e CTE sobre views expostas funcionam.
- **Coluna sensível:** declarar na view exposta. Se a view de cima não seleciona a coluna, ela não aparece; se seleciona algo derivado (por exemplo parte do CPF), declarar como sensível também.
- **Decidido em 2026-11-03: só views do arquivo.** O app não cria views; todas vêm prontas no `.db` fornecido. O parágrafo abaixo fica como referência caso isso mude.
- **Views criadas dentro do app** (fora do escopo): uma view persistente no `app.db` não pode referenciar o `dados.db` (erro "cannot reference objects in database"). Alternativa testada: guardar as definições no `app.db` e criá-las como `TEMP VIEW` na conexão só leitura do `dados.db` a cada abertura, **antes** de ligar `PRAGMA query_only`. Depois do `query_only`, nem o SQL gerado consegue criar views.
- **Desempenho:** views não são materializadas; o SQLite expande ou roda como subconsulta. Na ordem de 50 mil linhas não deve pesar; se pesar, quem fornece os dados materializa em tabela antes de entregar.

## 3. Em aberto

1. **Como declarar colunas sensíveis e o limite de linhas.** A política (mascarar e limitar) está decidida. Como as views vêm do usuário, quem fornece os dados declara as colunas sensíveis por contexto (por exemplo `sensitive_columns` em `views.json`). O app aplica a lista (authorizer e prompts) e, ao carregar os dados, sugere candidatas pelo nome da coluna (cpf, email, telefone, nascimento, nome). O rascunho do `views.json` está na seção 2; falta validar o formato. O limite padrão no prompt do LLM já está decidido (20 linhas).
2. **Como o usuário traz os dados** (definir quando você fornecê-los). A separação `app.db` / `dados.db`, o formato (arquivo SQLite pronto) e a cópia para a pasta de dados do app estão decididos. Falta só validar o `views.json` quando os dados chegarem. Ao copiar, usar a API de backup do SQLite (`sqlite3.Connection.backup`) em vez de copiar bytes, para não pegar o arquivo no meio de uma escrita; manter só a carga atual e apagar a anterior depois que a nova estiver indexada. Na carga, o app valida: é SQLite íntegro (`PRAGMA quick_check`), as views do `views.json` existem, e as colunas declaradas (sensíveis, embedadas, de busca local) existem nas views. Ao carregar dados novos, o app precisa indexar (embeddings do RAG e índice de valores) usando a chave do usuário, com barra de progresso.

## 4. O que aproveitar, adaptar ou descartar

| Peça | Destino |
|---|---|
| Agente BI, LangGraph, sqlglot, prompts | Aproveitar, com `dialect="sqlite"` |
| Conexão do agente ao banco (`psycopg2` em `agent.py` e `sql_validator.py`) | Adaptar: `sqlite3` só leitura no `dados.db` |
| Servidor MCP separado (`oraculo_mcp_server.py`, porta 8005, `fastmcp`, `mcp`, `langchain-mcp-adapters`) | Descartar no desktop; a ferramenta `bi_agent` vira função local |
| Models e views Django | Adaptar: sem `VectorField`, SQL cru reescrito |
| Front Vue | Aproveitar |
| URL da API no front | Adaptar: `VITE_API_URL` é fixada no build; a porta agora é dinâmica |
| CORS, CSRF e CSP | Adaptar: só aceitam o domínio de produção e `localhost:5173`; o webview do Tauri tem outra origem (confirmar qual) |
| nginx, whitenoise | Descartar (o Tauri serve o `dist`), salvo se o admin do Django ficar |
| Redis, Airflow, Spark, MinIO | Descartar |
| Login (Acesso Cidadão, gateway C#, `JWT_SECRET`, telas de login, `useAuth`) | Descartar; usuário local fixo criado no primeiro start |
| Dados e bootstrap de vendas | Descartar; dados e views serão fornecidos depois pelo usuário |
| `docker-entrypoint.sh` | Substituir por rotina de startup (migrate, tenant padrão, bootstrap) |
| Dependências | Enxugar: `psycopg2-binary`, `pgvector`, `redis` saem; `langchain-google-genai` provavelmente sai (Gemini sem uso encontrado); `pandas` sem import encontrado; conferir `sqlalchemy` |

## 5. Ordem sugerida

1. Fechar os pontos em aberto (declaração de colunas sensíveis com limite de linhas, entrada de dados). Já decididos: autenticação (sem login), chave do LLM (usuário informa), política de dados do LLM (mascarar e limitar), arquivos separados, MCP no mesmo processo, criptografia (só disco do SO) e histórico só com SQL.
2. Portar o núcleo para SQLite: `ENGINE` sqlite3 apontando para o `app.db`, conexão só leitura separada para o `dados.db`, regenerar migrations, vetores, checkpointer SQLite, `dialect` sqlite, reescrever SQL cru do dashboard e prompts, remover schema.
   - **Status em 2026-11-03 (pasta `Oraculo-ESX-desktop`, não commitado):** feito e testado com `scripts/teste_nucleo_sqlite.py` (28 verificações, sem LLM). Django no `app.db` com migrations regeneradas; vetores em BLOB float32 com busca numpy (`core/vectors.py`); `dados.db` só leitura com authorizer e política por variável de ambiente até os contextos existirem (`core/datastore.py`); validador com CTE e lista de views; `execute_query` sem corte; checkpointer `AsyncSqliteSaver`; SQL cru do dashboard e prompts em dialeto SQLite; limite de 20 linhas no prompt.
   - **Ficou para depois:** campo `db_schema_name` ainda existe (sem uso de `search_path`); `core/services/sales_bootstrap.py` ainda é Postgres (dados de demonstração, será descartado); login, MCP separado e front intocados; caminho com LLM real não testado.
3. Implementar contextos (modelo `Contexto`).
   - **Status em 2026-11-03 (commitado):** feito e testado (`scripts/teste_nucleo_sqlite.py`, 48 verificações sem LLM). Modelo `Contexto` com FK em conversa, widget, RAG, auditoria e índice de valores; carga e validação de `views.json`/`rules.md`/`examples.json` (`core/contexts.py`, comando `load_context`); política, prompt, RAG e índice de valores por contexto; conversa nova exige contexto (ou usa o único ativo); `GET /api/contextos`; `db_schema_name`, a view fixa no agente e o bootstrap de vendas foram removidos. Contexto de exemplo em `contexts/exemplo-vendas/`.
   - **Ficou para depois:** os endpoints fixos do painel (`kpis`, `charts`, `projects`) continuam presos à view de vendas de demonstração e precisam do `filters.json` por contexto; `train.py` e `backend/training/` ficaram obsoletos (o RAG agora sai do contexto); `local_search_columns` (busca local com FTS5) ainda não existe; histórico ainda grava `data`; caminho com LLM real não testado.
4. Casca Tauri e sidecar Python (PyInstaller ou Nuitka), porta dinâmica, CORS/CSP, loopback com token.
   - **Status em 2026-11-03:** backend e front feitos e testados (`scripts/teste_nucleo_sqlite.py`, 58 verificações sem LLM, mais o front rodando no navegador contra o backend local até a chamada da Mistral). Casca Tauri em `src-tauri/` **compilada e rodando no Linux** (Rust 1.99.1, tauri-cli 2.12.4 via npm): o app sobe o backend numa porta livre, o front recebe URL e token por `backend_info`, o CORS do webview passa e `/api/me`, `/api/contextos` e `/api/chat/conversations` respondem 200. Dados do app em `~/.local/share/br.edu.ifes.leds.oraculo-esx/`, log do backend em `logs/backend.log`.
     - Sem login: `core/local_auth.py` (usuário local fixo e token efêmero no header `X-Oraculo-Token`), `GET /api/me`; saíram JWT, cookie login, `simplejwt` e a tela de login. `SECRET_KEY` gerada por instalação, `DEBUG` desligado por padrão, `ALLOWED_HOSTS` só `127.0.0.1`/`localhost`.
     - MCP no mesmo processo: `agents/bi_agent/tool.py` (`StructuredTool` `bi_agent` com `asyncio.to_thread`); saíram o servidor MCP, o cliente MCP, `fastmcp`, `mcp` e `langchain-mcp-adapters`. Langfuse só liga se as chaves existirem.
     - Histórico guarda só o SQL; `GET /api/chat/messages/<id>/rows` reexecuta no `dados.db` (409 se o esquema mudou). O front carrega as linhas ao abrir a conversa.
     - Front: URL e token vêm do Tauri (`invoke('backend_info')`) ou do `.env` do Vite; hash router; seletor de contexto na conversa nova e contexto travado na existente; o widget fixado leva o contexto da conversa.
     - `backend/api/desktop_server.py` é o ponto de entrada que o Tauri sobe (migra, cria o usuário local, daphne em `127.0.0.1`).
   - **Para compilar (Ubuntu; nomes de pacotes da documentação do Tauri v2, não testados no 26.04):**
     `sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev`,
     instalar o Rust com o rustup, a CLI do Tauri já está em `frontend-vue` (`npx tauri`),
     `cargo tauri icon src-tauri/icons/icon.png` (gera os ícones), e para desenvolver: `npm --prefix frontend-vue run dev` num terminal e `cargo run` em `src-tauri/` noutro.
   - **Ficou para depois:** chave da Mistral no cofre do SO e tela de configuração (hoje vem do ambiente); sidecar empacotado (`oraculo-backend` via PyInstaller ou Nuitka) no lugar do `.venv`; perguntas iniciais do chat ainda são de vendas; o CSP só foi exercitado no modo dev (front servido pelo Vite); falta testar com o front embutido (`tauri build`).
5. Empacotamento: NSIS/MSI no Windows e `.deb`/AppImage no Linux, assinatura de código no Windows (tem custo), updater do Tauri, backup do `.db` antes de cada migração, logs na pasta de logs do usuário, CI com matriz Windows e Linux.

Também falta: gerar `DJANGO_SECRET_KEY` por instalação, forçar `DEBUG=false`, não criar superusuário padrão (o `.env.example` traz `admin`), trocar o card de status do Postgres/Redis por uma tela de diagnóstico e gerar o RAG (DDL, exemplos e índice de valores) quando o usuário carrega os dados, com a chave dele, e não no build, porque as views só chegam depois. Os exemplos atuais de vendas (cerca de 20 KB) são descartados.

## 6. Achados no código (verificados em 2026-11-01)

- Postgres faz três papéis: metadados Django (`backend/api/bi_agent_api/settings.py:114`), vetores pgvector de 1024 dimensões (`backend/api/knowledge/models.py:18`, `backend/api/analytics_index/models.py:16`) e dados analíticos por schema via `SET search_path` (`backend/api/agents/bi_agent/agent.py:39`, `backend/api/agents/bi_agent/nodes/sql_validator.py:45`).
- O SQL gerado e validado usa dialeto `postgres`. O SQL cru do dashboard usa `ILIKE`, `::text`, `json_agg ... FILTER` e `EXTRACT` (`backend/api/dashboard/views.py`).
- Redis só serve de checkpointer do LangGraph (`backend/api/agents/orchestrator/graph.py:23`, `backend/api/agents/config.py:16`), com limpeza em `backend/api/core/management/commands/flush_data.py:107` e ping em `backend/api/dashboard/views.py:331`. Não existe cache de resultados; o campo `cache_ttl_hours` do `Widget` não é usado.
- A view `vfactvendasresolved` está fixa em: `backend/api/agents/bi_agent/config.py:6`, `backend/api/agents/bi_agent/sql_security.py:37`, `backend/api/agents/config.py:35`, `backend/api/dashboard/views.py:17`, `backend/api/core/services/sales_bootstrap.py:39`. O `backend/api/analytics_index/config.py:5` já é um dicionário por view.
- Backend sobe com `runserver 0.0.0.0:8001`; servidor MCP separado em `:8005`; `VITE_API_URL` é fixada no build (`frontend-vue/src/common/api/config.ts:7`); CORS lista só o domínio de produção e `localhost:5173` (`backend/api/bi_agent_api/settings.py:199`).
- Todas as chamadas de LLM usam `ChatMistralAI` (`backend/api/agents/orchestrator/` e `oraculo_mcp_server.py`). As linhas de resultado (`data_rows`) vão no prompt de reflexão e de relatório (`orchestrator/nodes/reflection.py:48`, `orchestrator/nodes/report.py:38`).
- O índice de valores faz `SELECT DISTINCT` dos campos de texto configurados (`backend/api/analytics_index/services.py:104`) e manda cada valor ao embedder da Mistral (`embed_texts`, linha 123). Se campos com nomes de pessoas forem configurados, esses nomes saem para a nuvem.
- O cliente MCP é aberto por requisição em `backend/api/chat/stream_views.py:203` (timeout de 30 s para listar ferramentas), que grava as ferramentas nas globais `router.mcp_tools` e `graph_module.mcp_tools`. O servidor MCP expõe uma única ferramenta (`bi_agent`).
- O histórico do chat grava as linhas de resultado completas em `Message.metadata["data"]` (`backend/api/chat/stream_views.py:84-102`), junto com o SQL, a explicação e as sugestões.
- Essa gravação existe em dois lugares (`backend/api/chat/stream_views.py:84` e `backend/api/chat/views.py:279`). O serializer devolve `metadata` inteiro (`backend/api/chat/serializers.py:7`) e o front monta a tabela do histórico a partir de `metadata.data` (`frontend-vue/src/modules/chat/composables/useChatHistory.ts:30`).
- `execute_query` envolve todo SQL em `SELECT * FROM (...) LIMIT 100` (`backend/api/agents/bi_agent/agent.py:31-39`), então hoje o chat nunca mostra mais de 100 linhas. O `Widget` tem `limit_rows` com padrão 0 (sem limite).

## 7. Não verificado

- Quantidade de `KnowledgeItem` (define sqlite-vec ou numpy).
- Versão atual do sqlite-vec.
- Origem do webview do Tauri para CORS (a documentação do Tauri v2 não foi consultada sobre isso).
- Termos de tratamento de dados da Mistral (retenção, uso para treino).
- Se o Secret Service existe nas distros Linux alvo.
- Tamanhos de instalador citados (estimativas).
- Fontes de binários de Postgres embutido (EDB, zonky, crate `postgresql_embedded`) e se este último inclui pgvector.
- Se o `sqlalchemy` do `requirements.txt` ainda é usado.
- Se `chat/views.py` (rota sem streaming) também usa o cliente MCP; só confirmei em `stream_views.py`.
- O que `backend/api/chat/views.py:180` grava em `metadata` (outra criação de mensagem do assistente); só li as outras duas.

## 8. Demonstração de vendas (2026-11-04)

- `scripts/gerar_dados_demo.py <dados.db>` gera o `dados.db` com a mesma demo que o Oráculo web carregava (`backend/training/ddl/schema.sql` + `mudanças/mudanca/03` e `02`): 1.200 vendas de 2023 a 2026 e a view `vfactvendasresolved`, mais `v_receita_produto` (view sobre view).
- `contexts/exemplo-vendas/` usa essa demo: regras e métricas originais (com o nome da view corrigido; as regras antigas citavam `vfact_vendas_resolved`) e os 68 exemplos originais, todos testados contra a demo (um usava `INTERVAL` do Postgres e foi trocado por `date('now', '-3 months')`).
- O botão do Admin ("Carregar Contextos") valida os contextos e, com a chave da Mistral configurada, gera o RAG e o índice de valores.

## 9. Telas herdadas da web (2026-11-04)

- **Validação de Dados removida** (tela, componentes, `GET /api/admin/data-validation` e `/analytics`): comparava OLTP com OLAP do ETL da web; no desktop não há ETL e ela comparava o `dados.db` com ele mesmo. A validação útil é a de "Carregar Contextos".
- **Explorar Dados fora do menu**: lista fixa da view de vendas (`/api/projects`), sem contextos. A rota `/explorar` e o endpoint continuam no código até a tela ser refeita por contexto com o `filters.json`.
