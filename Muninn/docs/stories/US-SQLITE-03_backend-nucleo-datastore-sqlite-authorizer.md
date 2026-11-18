# User Story: [US-SQLITE-03] Adaptação do Backend Núcleo para SQLite (Datastore Somente-Leitura, Authorizer, Custom LIKE e Transpilação)

**Epic:** EPIC-08: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)  
**GitHub Epic Issue:** -  
**GitHub US Issue:** -  
**Prioridade:** Alta (Slice 2)  
**Story Points:** 5  
**Sprint:** Sprint 01  
**Status:** Completed  
**Behavior Change Esperado:** YES  

---

## Historia

**Como** Usuário e Agente de BI do Adito  
**Eu quero** que o backend núcleo (`core/datastore.py`, handlers RPC e contextos) execute sobre `dados.db` via SQLite com conexão somente-leitura, autorizador de segurança, função customizada de busca sem acento e transpilação de queries com `sqlglot`  
**Para que** as análises respondam em menos de 10 ms com máxima segurança contra injeções/mutações e com total resiliência linguística a termos com ou sem acentuação em português.

### Contexto Adicional

O backend núcleo (`Adito/app/backend/nucleo/`) foi desacoplado de HTTP pós-PR #62 e opera via stdio RPC no Tauri. O componente `datastore.py` conectava anteriormente no `dados.duckdb`. Com a migração para `dados.db`, o datastore deve ser adaptado para `sqlite3`. Para garantir segurança absoluta, configuraremos `conn.set_authorizer` restringindo acessos exclusivamente a `SELECT` nas 6 tabelas `vfact_*_resolved`. Para resolver limitações nativas do SQLite com caracteres latinos acentuados, registraremos uma função Python customizada `LIKE` com normalização Unicode NFD. Adicionalmente, consultas formuladas pelo LLM serão transpiladas via `sqlglot` (`duckdb` → `sqlite`) para absorver eventuais operadores analíticos legados.

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Conexão Somente-Leitura Segura):** `core/datastore.py` abre `dados.db` usando URI estrita `file:dados.db?mode=ro` e executa `PRAGMA query_only = ON`. Tentativas de escrita falham em nível de driver.
- [x] **Criterio 2 (Autorizador de Segurança em Nível de Conexão):** `conn.set_authorizer` autoriza exclusivamente `SQLITE_SELECT` e `SQLITE_READ` restritos às 6 tabelas fato (`vfact_*_resolved`), bloqueando imediatamente comandos de modificação (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`) e tentativas de consulta direta às 42 tabelas base.
- [x] **Criterio 3 (Busca Textual Acentuada e Case-Insensitive):** Função customizada `LIKE` registrada via `conn.create_function("like", 2, ...)` normaliza caracteres com `unicodedata.normalize('NFD')`, garantindo que filtros como `campus LIKE '%Vitoria%'` e `campus LIKE '%Vitória%'` retornem os mesmos registros.
- [x] **Criterio 4 (Transpilação de Queries com sqlglot):** Queries recebidas pelo datastore são transpiladas automaticamente (`sqlglot.transpile(sql, read="duckdb", write="sqlite")`), assegurando conversão transparente de cláusulas como `ILIKE`, `::INTEGER` ou `EXTRACT`.
- [x] **Criterio 5 (Introspecção de Schema e RPC):** `core/contexts.py` utiliza `PRAGMA table_info(...)` para introspecção de schema em substituição ao `DESCRIBE` do DuckDB; endpoints RPC (`dashboard.py`, `explorer.py`) operam com sucesso sobre o novo datastore.
- [x] **Criterio 6 (Metadados do Contexto Acadêmico):** Os arquivos `views.json`, `rules.md` e `examples.json` em `Adito/app/contexts/pesquisa-extensao-ifes/` são atualizados para dialeto SQLite e documentam os novos campos da especificação v2.0 (`qtd_autorias`, `flag_obra_unica`, `flag_software_sem_patente`, `instituicao_vinculo`, `parceiros_demandantes`, `flag_projeto_completo`, `duracao_meses_efetiva`).

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 2
- **Justificativa do nivel:** Modificação de contrato interno de consulta analítica e schema compartilhado entre datastore, RPC e agente de BI.
- **US exige Spec governada?** Nao
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Contract previsto:** N/A (RPC interno via stdio JSON-RPC)
- **Touch List preliminar:**
  - `Adito/app/backend/nucleo/core/datastore.py`
  - `Adito/app/backend/nucleo/core/contexts.py`
  - `Adito/app/backend/nucleo/rpc/dashboard.py`
  - `Adito/app/backend/nucleo/rpc/explorer.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/sql_security.py`
  - `Adito/app/contexts/pesquisa-extensao-ifes/views.json`
  - `Adito/app/contexts/pesquisa-extensao-ifes/rules.md`
  - `Adito/app/contexts/pesquisa-extensao-ifes/examples.json`
- **Requisitos Cobertos:** `FR13`, `FR14`, `FR15`, `FR16`, `FR17`, `FR18`, `NFR02`, `NFR03`.

---

## Notas Tecnicas

### Implementação do Authorizer
```python
def authorizer(action, arg1, arg2, db_name, trigger_name):
    allowed_tables = {
        "vfact_extensao_acao_resolved",
        "vfact_extensao_participacao_resolved",
        "vfact_projeto_pesquisa_resolved",
        "vfact_orientacao_bolsa_resolved",
        "vfact_producao_cientifica_resolved",
        "vfact_grupo_pesquisa_membro_resolved",
    }
    if action == sqlite3.SQLITE_READ and arg1 in allowed_tables:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY
```

### Implementação do Custom LIKE
```python
import unicodedata

def normalize_text(text: str) -> str:
    if text is None:
        return ""
    nfkd = unicodedata.normalize('NFD', str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).casefold()

def custom_like(pattern: str, text: str) -> bool:
    # Implementação de correspondência pattern com wildcard % e _ normalizados
    ...
```

---

## Plano de Testes

### Testes Unitarios e Integracao
- [ ] Testar tentativa de escrita (`INSERT`/`UPDATE`/`DROP`) no datastore, verificando bloqueio por `mode=ro` e `authorizer`.
- [ ] Testar consulta direta em tabela base (`SELECT * FROM pessoa`), verificando negação de acesso pelo autorizador.
- [ ] Testar consulta `SELECT * FROM vfact_producao_cientifica_resolved WHERE campus LIKE '%Vitoria%'` e confirmar que retorna registros de `'Vitória'`.
- [ ] Testar query com `ILIKE` e verificar que `sqlglot` converte para `LIKE` compatível.
- [ ] Testar rotas RPC do explorer e dashboard via stdio.

---

## Tasks (Breakdown)

- [ ] **[TASK-001]** Refatorar `core/datastore.py` para usar `sqlite3` com URI `mode=ro` e `conn.set_authorizer`.
- [ ] **[TASK-002]** Implementar função customizada `LIKE` com normalização de acentos (Unicode NFD) e registrá-la na conexão.
- [ ] **[TASK-003]** Implementar camada de transpilação com `sqlglot` em tempo de execução no datastore.
- [ ] **[TASK-004]** Atualizar `contexts.py` (usando `PRAGMA table_info`), `rpc/dashboard.py` e `rpc/explorer.py`.
- [ ] **[TASK-005]** Atualizar metadados do contexto `pesquisa-extensao-ifes` (`views.json`, `rules.md`, `examples.json`).

---

## Definition of Done Checklist

- [ ] Código do backend adaptado e funcional
- [ ] Latência de consultas inferior a 10 ms
- [ ] Blindagem de segurança com `set_authorizer` validada
- [ ] Suporte a consultas sem acento validado
- [ ] Code review aprovado
- [ ] Rastreabilidade para requisitos `FR13..FR18, NFR02, NFR03` confirmada
