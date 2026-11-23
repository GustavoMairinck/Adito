# Núcleo local sem HTTP

Registrado em 2026-11-17 ([US-016](stories/US-016_nucleo-local-sem-http.md)). Esta decisão substitui a de 2026-11-03, "backend ASGI (daphne) em `127.0.0.1` com token", registrada em [PORTE_DESKTOP_DECISOES.md](PORTE_DESKTOP_DECISOES.md).

## Resumo

- **O que saiu:** o servidor web local. Isso inclui Django, Django REST Framework, daphne, CORS, whitenoise, a porta em `127.0.0.1` e o token `X-Adito-Token`.
- **O que entrou:** o Python (agente, contextos, DuckDB, `app.db`) continua, agora como um processo filho que conversa com a janela por stdin/stdout. O Adito é um app desktop; não precisa de servidor.
- **O que não mudou:** as telas recebem exatamente as mesmas respostas. O teste de contrato prova isso em 51 chamadas. O `app.db` de instalações antigas abre sem migração de dados.

## Lista de mudanças

| Área | Antes | Depois |
|---|---|---|
| Tauri (`src-tauri/src/lib.rs`) | Escolhia uma porta livre, gerava um token, subia o daphne e esperava o `/health` | Sobe o núcleo com stdin e stdout em pipe e entrega as respostas a quem espera cada pedido |
| Comandos Tauri | `backend_info` | `core_ready`, `core_call`, `core_stream`, `core_cancel` (os da chave continuam iguais) |
| Front: cliente | axios (`httpClient.ts`) e `fetch` com SSE no chat | `common/api/core.ts`: `call()`, `stream()`, `coreReady()` |
| Front: telas | Uma chamada HTTP por ação | A mesma ação, uma linha trocada (`call('widgets.list')` em vez de `GET /api/dashboard/widgets`) |
| Python: entrada | `desktop_server.py` rodava `migrate` e subia o daphne | `desktop_server.py` sobe `rpc/server.py` (stdin/stdout) |
| Python: rotas e views | `bi_agent_api/urls.py` e views do DRF em `chat/`, `dashboard/`, `knowledge/`, `core/` | Métodos em `rpc/` (`core_methods`, `dashboard`, `chat`, `admin`) |
| Python: banco | ORM do Django, models e migrations | `core/db.py` (sqlite3), `core/records.py` (tabelas), `core/schema.sql` + `core/schema.py` (`PRAGMA user_version`) |
| Python: validação | Serializers do DRF | `rpc/params.py`, com as mesmas mensagens de erro |
| Python: DuckDB | Abria o `dados.duckdb` a cada consulta (~12 ms) | Abre uma vez; cada chamada usa um cursor próprio (`core/datastore.py`) |
| Comandos de manutenção | `python manage.py load_context` etc. | `python -m core.cli load-context` etc. |
| Dependências Python | `django`, `djangorestframework`, `django-cors-headers`, `daphne`, `whitenoise`, `python-jose`, `bcrypt` | Removidas |
| Dependências do front | `axios` | Removida |
| Dependências Rust | `uuid` | `serde_json`, `tokio` (só `sync`); as duas já estavam na árvore do Tauri |
| Web e scripts | `Dockerfile`, `nginx.conf`, `.dockerignore` do front, `rodar_backend.sh` | Removidos |
| CSP | `connect-src` liberava `http://127.0.0.1:*` | Só `ipc:` |
| Testes | `teste_nucleo_sqlite.py` (já quebrado desde a troca para o DuckDB) e `core/tests.py` com Django | `teste_contrato.py`, `teste_stdio.py` e `core/tests.py` em `unittest` |

## Como funciona o stdin/stdout

```
Vue ──invoke('core_call')──▶ Rust (Tauri) ──linha JSON no stdin──▶ Python (núcleo)
Vue ◀──Promise / Channel──── Rust ◀───────linha JSON no stdout──── Python
                                            stderr ──▶ logs/backend.log
```

Cada mensagem é um objeto JSON numa linha. O `id` é gerado pelo front e casa cada pedido com a sua resposta. Por isso vários pedidos podem estar em andamento ao mesmo tempo, e as respostas podem voltar em qualquer ordem.

| Mensagem | Sentido | Exemplo |
|---|---|---|
| Pronto | núcleo → Rust, uma vez ao subir | `{"event":"ready","data":{"schema":1,"methods":22,"startup_ms":504}}` |
| Pedido | Rust → núcleo | `{"id":42,"method":"dashboard.kpis","params":{"ano":"2025"}}` |
| Resposta | núcleo → Rust | `{"id":42,"ok":true,"result":{"rows":[…],"total":310}}` |
| Erro | núcleo → Rust | `{"id":42,"ok":false,"error":{"status":404,"data":{"detail":"Tabela indisponível neste contexto."}}}` |
| Evento de stream | núcleo → Rust, antes da resposta | `{"id":7,"event":"token","data":{"text":"O total"}}` |
| Cancelar | Rust → núcleo | `{"method":"$cancel","params":{"id":42}}` |
| Falha ao subir | núcleo → Rust | `{"event":"fatal","data":{"message":"…"}}` |

- **Erros.** O `status` repete o código HTTP de antes (400, 403, 404, 409, 503) e `data` repete o corpo de antes. No front, o erro é um `CoreError` com `status`, `data` e `response = {status, data}`. Por isso o tratamento atual das telas (`error.response.data.detail`) não mudou.
- **Streaming do chat.** O Python emite `status`, `token`, `result` e `error`, com os mesmos nomes e campos do SSE de antes. O Rust repassa cada um por um `tauri::ipc::Channel` e manda o fim (`$end`) pelo mesmo canal. Assim, nenhum evento chega depois de a chamada terminar.
- **Concorrência.** No Python, cada pedido vira uma task do asyncio. Os métodos síncronos (sqlite3, DuckDB) rodam numa thread, cada uma com a sua conexão ao `app.db`. A escrita no stdout é serializada.
- **Cancelamento.** Um `AbortController` no front, como o do Dashboard, chama `core_cancel`. A Promise rejeita na hora com `name === 'CanceledError'`, e o núcleo cancela a task.
- **Por que os logs vão para o stderr.** O stdout é o canal do protocolo: qualquer texto solto ali quebraria a leitura. Ao subir, o núcleo guarda uma cópia do stdout só para o protocolo e aponta o descritor 1 para o stderr. Assim, um `print()` de qualquer biblioteca (LangGraph, rich) vai para o `backend.log`.
- **O núcleo morre junto com o app.** Quando o app fecha, ou é morto com `kill -9` ou pelo Gerenciador de Tarefas, o sistema fecha o pipe. O núcleo lê o fim do stdin e encerra. Não sobra processo órfão em Linux nem em Windows, o que resolve a [US-013](stories/US-013_backend-orfao.md). No fechamento normal, o Rust fecha o stdin e espera até 3 s antes de matar o processo.
- **Troca da chave do Gemini.** A chave continua indo do cofre do SO ao núcleo por variável de ambiente. Salvar ou apagar a chave reinicia o núcleo: os pedidos pendentes recebem 503 "O núcleo está reiniciando." e o front espera `core_ready` antes de seguir.
- **Abertura.** O front espera `core_ready` antes de montar a interface. Se o núcleo não subir, a janela mostra o motivo e o caminho do log, em vez de ficar em branco.

## Persistência sem ORM

- **Mesmas tabelas do Django** (`core/schema.sql`), no mesmo formato:
  - ids UUID gravados em hex de 32 caracteres (no código e na API, com hífens);
  - datas em texto UTC;
  - JSON em texto;
  - vetores em BLOB float32.

  Um `app.db` criado pela versão Django abre como está. As tabelas `auth_*` e `django_*` ficam intocadas.
- **Versão do esquema em `PRAGMA user_version`** (hoje 1). Mudanças futuras entram em `MIGRACOES` (`core/schema.py`), com backup automático em `app.db.bak-v<n>` antes de aplicar.
- **O que o ORM fazia sozinho agora está explícito em `core/records.py`:**
  - apagar uma conversa apaga as mensagens e solta a auditoria que apontava para elas;
  - `update()` sem campos renova o `updated_at`;
  - as ordenações (conversas por `updated_at` decrescente, mensagens por `created_at`).
- **Uma consulta só para as mensagens.** A lista de conversas busca as mensagens de uma vez; o serializer do DRF fazia uma consulta por conversa.

## Mapa de chamadas

| Antes (HTTP) | Agora (método) |
|---|---|
| `GET /health`, `GET /api/me` | `health`, `me` |
| `POST /api/config/test-llm-key` | `config.test_llm_key` |
| `GET /api/contextos` | `contextos.list` |
| `GET /api/explorer/tables`, `GET /api/explorer/rows` | `explorer.tables`, `explorer.rows` (removidos em 2026-11-19, com a tela Explorar dados) |
| `POST /api/chat/stream` | `chat.stream` (com eventos) |
| `GET /api/chat/conversations`, `DELETE /api/chat/conversations/{id}` | `chat.conversations.list`, `chat.conversations.delete` |
| `GET /api/chat/messages/{id}/rows` | `chat.message_rows` |
| `GET/POST/PUT/DELETE /api/dashboard/widgets[/{id}]`, `…/{id}/refresh` | `widgets.list`, `widgets.create`, `widgets.update`, `widgets.delete`, `widgets.refresh` |
| `GET /api/kpis`, `GET /api/projects/top`, `GET /api/charts` | `dashboard.kpis`, `dashboard.top_projects`, `dashboard.charts` |
| `POST /api/admin/data/bootstrap` | `admin.bootstrap` (sem o limite de 900 s) |
| `GET /api/admin/system-status` | `admin.system_status` |
| `GET /api/chat/query-executions` | `admin.query_executions` |
| `POST /api/admin/trainings` | `admin.trainings.create` |
| — (novos em 2026-11-23, aba Base de conhecimento) | `admin.trainings.list`, `admin.trainings.delete`, `admin.trainings.retrain` (refaz o RAG de um contexto pelos arquivos e mantém os itens manuais) |

Rotas que o front não usava saíram sem substituto:
- `POST /api/chat`;
- `conversations/ask`;
- `api/dashboard/dashboards`;
- `api/projects`;
- o resto do CRUD de trainings (listar e apagar voltaram em 2026-11-23 como métodos; editar continua de fora);
- o `/admin/` do Django.

## Como adicionar um método

1. Escreva a função num módulo de `backend/nucleo/rpc/`. Ela recebe `params` (dict) e devolve algo serializável em JSON.
2. Decore com `@rpc("area.acao")`. Um método com eventos usa `@rpc("…", stream=True)` e recebe também `emit(event, data)`.
3. Para erro, use `raise ApiError(status, corpo)` (`rpc/errors.py`). Para validar, use `validate(spec, params)` (`rpc/params.py`).
4. Se o módulo for novo, importe-o em `load_handlers()` (`rpc/registry.py`).
5. No front, chame `call('area.acao', {...})` de `@/common/api/core`.

## Como rodar e testar

- **App em desenvolvimento:** `./rodar_desktop.sh`, na raiz do repositório.
- **Testes**, a partir de `Adito/app`; nenhum usa rede nem chave:
  - `.venv/bin/python scripts/teste_contrato.py` compara as respostas com a referência gravada no Django;
  - `.venv/bin/python scripts/teste_stdio.py` testa o processo real e o protocolo;
  - `cd backend/nucleo && ../../.venv/bin/python -m unittest core.tests` roda os testes do núcleo.
- **Manutenção:** `cd backend/nucleo && ../../.venv/bin/python -m core.cli --help` mostra `load-context`, `sync-embeddings`, `rebuild-embeddings` e `flush-data`. O `flush-data` agora preserva o usuário local e os seus widgets; antes, ele apagava o usuário local.

### Desempenho medido

Linux, dados falsos e sem chamar o LLM:
- **DuckDB:** 200 mil linhas.
- **`app.db`:** 300 conversas com 6.000 mensagens, 5.000 auditorias de SQL, 60 widgets e 2.000 itens de RAG.

O cliente de teste fala com o núcleo por stdin/stdout, como o Tauri. Não está medida a ponte entre o Rust e o webview, que costuma custar menos de 1 ms por chamada.

| Medida | Resultado |
|---|---|
| Ida e volta sem banco (`health`) | 0,07 ms |
| Vazão com pedidos enviados de uma vez | ~24 mil pedidos/s |
| Abertura do núcleo até o evento ready | ~0,7 s |
| Lista de conversas (300 conversas, 6.000 mensagens, 2,4 MB) | 80 ms |
| `widgets.list` / salvar um widget | 1,3 ms / 0,4 ms |
| Explorar, página 1 / busca textual em todas as colunas | 4 ms / 42 ms |
| KPIs / gráficos do dashboard | 3,5 ms / 11 ms |
| Reexecutar o SQL de um widget ou do histórico | ~3 ms |
| Resposta de 13 MB (100 mil linhas) | 436 ms (~29 MB/s) |
| 8 consultas DuckDB ao mesmo tempo | 76 ms (367 ms uma de cada vez) |

Dois ganhos explicam esses tempos:
- **Conexão com o DuckDB.** Abrir o `dados.duckdb` a cada consulta custava ~12 ms. Com o arquivo aberto uma vez, as chamadas do Explorar e do Dashboard caíram de 15–55 ms para 3–11 ms.
- **Abertura e pedidos simples.** Comparado com o servidor Django (medido com dados menores), a abertura caiu de ~1,0 s para ~0,7 s, e o `me` de 3,9 ms para 0,07 ms.

Além disso, o grafo do orquestrador e o checkpointer são abertos uma vez por processo. Widgets e histórico reexecutam o SQL sem instanciar o LLM. O tempo até o primeiro token do chat não foi medido, porque exige a chave e a rede.

**O `dados.duckdb` fica aberto.** O núcleo mantém o arquivo aberto, só para leitura, com as mesmas travas de antes: sem acesso a arquivos externos e sem `SET`. O banco é reaberto quando o arquivo é trocado e solto depois de 60 s sem uso; o tempo é ajustável com `ADITO_DUCKDB_IDLE_CLOSE_S`.
- **Linux:** rodar o `gerar_duckdb.py` com o app aberto funciona; a consulta seguinte já lê o banco novo.
- **Windows:** um arquivo aberto não pode ser apagado. Feche o app ou espere 60 s sem usar o Explorar e o Dashboard antes de regerar o banco.
