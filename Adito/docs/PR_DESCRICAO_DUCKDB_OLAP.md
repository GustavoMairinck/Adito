# PR: feat(adito): banco analítico DuckDB OLAP com 6 tabelas fato e suporte a Gemini

**Branch de Origem (Head):** `andrefsa16:Adito:feat/adito-duckdb-olap`  
**Branch de Destino (Base):** `SmartIdea-ifes-serra/Adito:development`  
**Story Relacionada:** `US-ADITO-DUCKDB-01` (`EPIC-07`)  

---

## Descrição

Migra a camada de dados analítica do **Adito (Oráculo ESX)** de SQLite para **DuckDB OLAP** em formato colunar nativo e adapta todo o backend, contexto e orquestrador para o modelo **Google Gemini**.

### O que foi feito:
1. **Geração do Banco DuckDB Analítico (`Adito/scripts/gerar_duckdb.py`):**
   - Importa os 41 JSONs do pipeline de ETL em `unificado.<tabela>` em ~2,5s via leitura colunar nativa (`read_json`).
   - Materializa as **6 tabelas fato** no schema `main` (`vfact_*_resolved`) com contagens conferidas e formato de armazenamento estável `v1.2.0` (compatível com VS Code, DBeaver e CLI):
     - `vfact_extensao_acao_resolved` (207)
     - `vfact_extensao_participacao_resolved` (6.741)
     - `vfact_projeto_pesquisa_resolved` (236)
     - `vfact_orientacao_bolsa_resolved` (1.203)
     - `vfact_producao_cientifica_resolved` (1.232)
     - `vfact_grupo_pesquisa_membro_resolved` (553)
2. **Adaptação do Backend Django (`Adito/app/backend/api/`):**
   - **`core/datastore.py`:** conexão `read_only=True` ao `dados.duckdb` via wrappers compatíveis com o Django (`DadosConnection`, `DadosCursor`, `DadosRow`).
   - **`agents/bi_agent/sql_security.py`:** parser AST `sqlglot` no dialeto `duckdb`, whitelist restrita às 6 tabelas fato, bloqueio de comandos de sistema/escrita (`COPY`, `ATTACH`, `LOAD`, `PRAGMA`) e de funções de arquivo (`read_*`), além de bloqueio de colunas sensíveis (LGPD).
   - **`core/contexts.py`:** introspecção via `DESCRIBE`, regras base de prompt para DuckDB OLAP e sincronização de contextos com desativação automática de modelos legados.
   - **`agent.py`, `sql_validator.py`, `sql_generator.py`, `sql_corrector.py`, `analytics_index` e `dashboard`:** adequação ao dialeto e metadados DuckDB.
3. **Contexto Oficial `pesquisa-extensao-ifes`:**
   - Criado em `Adito/app/contexts/pesquisa-extensao-ifes/` com `views.json`, `rules.md` e `examples.json` (16 perguntas e consultas SQL analíticas cobrindo SRC, SigPesq, Lattes e CNPq isoladamente e em cruzamentos unificados).
   - Desativação do contexto demonstrativo `exemplo-vendas` com `"ativo": false`.
4. **Migração para Google Gemini:**
   - Adoção de `langchain-google-genai` e `google-genai` com `gemini-3.5-flash` e `models/gemini-embedding-001`.
   - Chave do Gemini gerenciada no cofre do SO (Keyring do Tauri) via `gemini-api-key`.
   - Atualização das telas de Configurações e Administração no frontend Vue 3.
5. **Ferramentas de Desenvolvedor e Execução:**
   - `Adito/scripts/ver_dados.py`: utilitário para listar tabelas, inspecionar colunas e abrir shell SQL interativo.
   - `.vscode/settings.json`: auto-anexo do `dados.duckdb` em modo leitura na extensão DuckDB do VS Code.
   - `rodar_backend.sh` e `rodar_desktop.sh`: scripts locais de subida do ambiente.
   - `Adito/docs/ADAPTACAO_DUCKDB_VIEWS.md`: relatório técnico completo da iniciativa.

---

## Issue relacionada

Closes US-ADITO-DUCKDB-01

---

## Tipo de mudança

- [x] `feat` — nova funcionalidade
- [ ] `fix` — correção de bug
- [x] `docs` — apenas documentação
- [ ] `style` — formatação, sem mudança de lógica
- [x] `refactor` — refatoração sem alterar comportamento externo
- [x] `perf` — melhoria de performance (DuckDB colunar)
- [x] `test` — adição ou correção de testes
- [ ] `build` / `ci` — build, dependências ou pipeline de CI
- [ ] `chore` — tarefas de manutenção

---

## Como testar

1. **Rodar os testes automatizados do núcleo:**
   ```bash
   python Adito/app/backend/api/manage.py test core
   ```
2. **Gerar ou verificar o banco DuckDB analítico:**
   ```bash
   python Adito/scripts/gerar_duckdb.py
   ```
3. **Inspecionar as 6 tabelas fato pelo terminal:**
   ```bash
   python Adito/scripts/ver_dados.py
   python Adito/scripts/ver_dados.py vfact_projeto_pesquisa_resolved
   ```
4. **Executar a aplicação desktop completa:**
   ```bash
   bash ./rodar_desktop.sh
   ```

---

## Uso de Inteligência Artificial (AI Attribution)

- [ ] Nenhum trecho deste PR foi gerado com auxílio de IA.
- [x] Partes deste PR foram geradas/assistidas por IA. Se marcado, preencha abaixo:

- **Modelo:** Antigravity (Google Gemini, supervisionado)
- **Trailer:** `Assisted-by: Antigravity (model: Gemini, supervised)`

---

## Checklist geral

- [x] O título do PR segue o padrão Conventional Commits (`feat(adito): ...`)
- [x] Fiz um self-review do próprio código
- [x] Testei localmente e os testes existentes continuam passando (8/8 no core)
- [x] Adicionei/atualizei testes quando necessário
- [x] Atualizei a documentação relevante (`ADAPTACAO_DUCKDB_VIEWS.md`, `README.md`, `US-ADITO-DUCKDB-01`)
- [x] Não deixei código de debug, comentários temporários ou prints esquecidos
- [x] A branch está baseada em `development`
