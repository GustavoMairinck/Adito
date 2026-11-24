# User Story: [US-LLM-03] Cofre do SO por provedor, persistência local, retrocompatibilidade v0.1.0 e PyInstaller

**Epic:** EPIC-11: Suporte Multi-Provedor de IA (BYOK)
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (Vertical Slice 2)
**Story Points:** 5
**Sprint:** A definir
**Status:** Done
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário do aplicativo desktop Adito,
**Eu quero** que minhas chaves de API fiquem isoladas por provedor no cofre do sistema operacional, que a troca de provedor preserve chaves já salvas sem nunca expor segredos ao frontend e que minha chave Gemini da v0.1.0 continue funcionando automaticamente,
**Para que** eu alterne provedores com segurança, atualize o app sem reconfiguração e receba um instalador desktop funcional.

### Contexto Adicional

Origem: `Adito/docs/discovery/suporte-multi-provedor-llm.md` (`PROBLEM_READY`) e `Adito/docs/requirements/suporte-multi-provedor-llm.md` (`REQUIREMENTS_READY`).

Atualmente `Adito/app/src-tauri/src/lib.rs` gerencia uma única entrada no `keyring` (`KEYRING_USER = "gemini-api-key"`) e repassa apenas `GEMINI_API_KEY` ao sidecar Python. Além disso, `Adito/app/backend/adito-backend.spec` empacota explicitamente apenas `langchain_google_genai` e `google.genai`. Esta story evolui o cofre e os comandos Tauri para múltiplos provedores com isolamento de segredos (`A03`), retrocompatibilidade absoluta com v0.1.0 e suporte ao empacotamento PyInstaller.

**Requisitos rastreados:** `FR03`, `FR10` (Tauri), `BR01`, `BR02`, `BR03`, `BR06`, `NFR02`, `NFR05` (`cargo test`), `A03`.

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [ ] **Criterio 1 (Cofre isolado por provedor + metadados não-sensíveis — FR03, BR03, BR06):** `src-tauri/src/lib.rs` armazena chaves separadamente no `keyring` sob `llm-key-<provider>` (no serviço `br.edu.ifes.leds.adito`) e persiste apenas `{provider, model, base_url}` em `llm_config.json` dentro de `data_dir`, garantindo que nenhuma chave de API seja gravada em arquivo texto nem logada.
- [ ] **Criterio 2 (Retrocompatibilidade v0.1.0 — BR01, BR03):** Se `llm_config.json` não existir e houver uma chave em `gemini-api-key` no `keyring`, o Tauri ativa automaticamente `provider = "gemini"` com modelo padrão sem exigir reconfiguração. Ao salvar nova chave para `gemini`, grava em `llm-key-gemini`; ao remover `gemini`, remove tanto `llm-key-gemini` quanto `gemini-api-key` legado.
- [ ] **Criterio 3 (Preservação de chaves e remoção seletiva — BR03):** Alternar o provedor ativo no Adito nunca apaga chaves já salvas de outros provedores no cofre; o comando de remoção apaga somente a chave do provedor selecionado (e reverte/limpa a configuração ativa apenas se o provedor removido for o ativo).
- [ ] **Criterio 4 (Reuso seguro de chave salva sem expor segredo ao frontend — A03, BR06, FR10, BR02):** Comandos Tauri permitem: (a) consultar provedor ativo, modelo, `base_url` e mapa booleano `has_key_by_provider` (nunca retornando a chave ao frontend); (b) testar e salvar configuração reutilizando a chave já salva no cofre do lado Rust → núcleo Python quando o usuário não digita nova chave (ex.: ao alternar para provedor já salvo ou mudar só o modelo); (c) aceitar chave vazia exclusivamente quando `base_url` apontar para host loopback (`localhost`, `127.0.0.1`, `::1`).
- [ ] **Criterio 5 (Injeção de variáveis no núcleo — FR03, BR01):** Ao iniciar ou reiniciar o sidecar Python, o Tauri injeta `ADITO_LLM_PROVIDER`, `ADITO_LLM_MODEL`, `ADITO_LLM_BASE_URL` e `ADITO_LLM_API_KEY` (e também `GEMINI_API_KEY` quando `provider == "gemini"`), removendo variáveis obsoletas ao trocar de provedor para evitar vazamento de estado entre reinícios.
- [ ] **Criterio 6 (PyInstaller e `cargo test` — NFR02, NFR05):** `Adito/app/backend/adito-backend.spec` inclui coleta de `langchain_openai` (e submódulos necessários de runtime); `cargo test` em `Adito/app/src-tauri` cobre leitura/escrita de `llm_config.json`, retrocompatibilidade de `gemini-api-key`, isolamento por provedor, política de loopback e ausência de segredo em disco.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 2
- **Justificativa do nivel:** Altera o boundary IPC Tauri ↔ Frontend, o modelo de persistência de credenciais no cofre do SO (LGPD/segurança) e o empacotamento desktop (`adito-backend.spec`).
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** O contrato de persistência, retrocompatibilidade e segurança está consolidado em `Adito/docs/requirements/suporte-multi-provedor-llm.md` (`FR03`, `BR01`–`BR03`, `BR06`, `A03`).
- **Spec prevista:** N/A
- **US exige Contract governado?** Sim (IPC Tauri documentado)
- **Justificativa do Contract:** Define assinaturas dos comandos Tauri consumidos por `src/common/api/llmKey.ts` e simulados em `tests/e2e/helpers/tauriMock.ts` (`US-LLM-04`).
- **Contract previsto:** Comandos Tauri em `Adito/app/src-tauri/src/lib.rs` espelhados em `src/common/api/llmKey.ts` e `tauriMock.ts`
- **Padrao de erro aplicavel:** Erros legíveis em português retornados por `Result<..., String>` nos comandos Tauri
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** `cargo test` + `cargo check` em `Adito/app/src-tauri`
- **Touch List preliminar:**
  - `Adito/app/src-tauri/src/lib.rs`
  - `Adito/app/backend/adito-backend.spec`
- **Task Issues previstas:** N/A

---

## Mockups/Wireframes

N/A (camada Rust/Tauri e empacotamento; UI está em `US-LLM-04`).

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `Adito/app/src-tauri/src/lib.rs` (comandos Tauri, gerenciamento do `keyring`, `llm_config.json`, spawn/restart do sidecar Python) e `Adito/app/backend/adito-backend.spec`.
- **APIs necessarias:** Comandos Tauri (mantendo wrappers retrocompatíveis se necessário ou migrando coordenadamente com `US-LLM-04`):
  - `llm_config_status` (retorna `{provider, model, base_url, configured, has_key_by_provider, key_source}`)
  - `test_llm_config` (recebe `{provider, model, base_url, api_key?, use_saved_key?}`, resolve segredo no `keyring` quando `use_saved_key` e chama `config.test_llm_key` no núcleo via STDIO sem expor a chave à WebView)
  - `set_llm_config` (grava chave no `keyring` se informada, persiste `llm_config.json` e reinicia o núcleo)
  - `clear_llm_key` (recebe `{provider}`, remove apenas `llm-key-<provider>` e legado `gemini-api-key` se `gemini`, reiniciando o núcleo se era o ativo)
- **Database changes:** Nenhuma alteração em `app.db` ou `dados.db`; apenas arquivo `llm_config.json` em `data_dir`.
- **Referencias do modelo de dados:** N/A
- **Erros observaveis esperados:**
  - Falha ao acessar cofre do SO (ex.: Secret Service indisponível no Linux) com orientação clara.
  - Chave ausente ao tentar ativar provedor remoto sem chave digitada nem salva no cofre.
  - Caracteres inválidos na chave ou URL inválida.

### Dependencias

- [ ] `US-LLM-01` (variáveis `ADITO_LLM_*` e método RPC `config.test_llm_key` aceitando `{provider, key, model, base_url}`).

### Consideracoes de Performance

- Leitura do mapa `has_key_by_provider` no `keyring` deve consultar apenas os IDs conhecidos do catálogo (8 provedores) e evitar chamadas repetidas dentro de loops de chat.

---

## Plano de Testes

### Testes Unitarios

- [ ] `cargo test` em `src-tauri`: serialização/deserialização de `llm_config.json` verificando ausência de campo de segredo.
- [ ] `cargo test`: fallback de leitura de `gemini-api-key` legado quando `llm_config.json` não existe.
- [ ] `cargo test`: validação de host loopback (`localhost`, `127.0.0.1`, `::1`, rejeitando `localhost.evil.com` ou hosts remotos).
- [ ] `cargo test`: limpeza de variáveis de ambiente antigas ao trocar provedor (ex.: `GEMINI_API_KEY` não vaza ao mudar para `openai`).

### Testes de Integracao

- [ ] Fluxo `test_llm_config` com `use_saved_key=true` invocando `config.test_llm_key` no núcleo sem trafegar a chave pela WebView.

### Testes de Contract

- [ ] Alinhamento entre nomes/payloads dos comandos Tauri em `lib.rs` e mocks em `tests/e2e/helpers/tauriMock.ts` (`US-LLM-04`).

### Testes Manuais

- [ ] Simular instalação v0.1.0 com apenas `gemini-api-key` no cofre e confirmar boot transparente em `gemini`.
- [ ] Salvar chave Gemini, salvar chave OpenAI, voltar para Gemini sem redigitar a chave e confirmar que ambas permanecem no cofre.
- [ ] Validar empacotamento PyInstaller (`adito-backend.spec`) importando `langchain_openai` sem `ModuleNotFoundError`.

### BDD / Cenarios de Comportamento

- [ ] N/A.

---

## Tasks (Breakdown)

- [ ] **[TASK-001]** Implementar camada de configuração (`llm_config.json`) e abstração de cofre por provedor com retrocompatibilidade `gemini-api-key` em `src-tauri/src/lib.rs`
  - GitHub Task Issue: N/A
  - Estimativa: 3h
  - Assignee: A definir
- [ ] **[TASK-002]** Implementar comandos Tauri (`llm_config_status`, `test_llm_config`, `set_llm_config`, `clear_llm_key`) com reuso seguro de chave salva (`A03`) e injeção de `ADITO_LLM_*` no sidecar
  - GitHub Task Issue: N/A
  - Estimativa: 3h
  - Assignee: A definir
- [ ] **[TASK-003]** Atualizar `Adito/app/backend/adito-backend.spec` para coletar `langchain_openai` e dependências de runtime
  - GitHub Task Issue: N/A
  - Estimativa: 1h
  - Assignee: A definir
- [ ] **[TASK-004]** Escrever testes unitários Rust (`cargo test`) cobrindo migração v0.1.0, isolamento, loopback e limpeza de env vars
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: A definir

---

## IA Insights

### Sugestoes de Implementacao

- Abstrair o acesso ao `keyring` atrás de uma trait interna em `lib.rs` (com implementação real `keyring::Entry` e mock `HashMap` em `#[cfg(test)]`) para que `cargo test` rode 100% determinístico e offline mesmo em ambientes Linux headless sem Secret Service/D-Bus.
- No `adito-backend.spec`, verificar coleta de `langchain_openai`, `openai` e `tiktoken`/`tiktoken_ext` (caso usados em runtime pelo `ChatOpenAI`) para evitar falha silenciosa no binário congelado.

### Riscos Identificados

- `tiktoken` (dependência transitiva de `langchain-openai`) frequentemente exige `collect_submodules('tiktoken_ext')` e `collect_data_files('tiktoken')` no PyInstaller; validar explicitamente no spec.
- Em Linux headless/CI, chamadas diretas ao `keyring` real falham sem daemon — o uso de trait mockada em testes unitários elimina flakiness.

### Alternativas Consideradas

- Salvar um JSON com todas as chaves dentro de uma única entrada do `keyring`: descartada porque entradas isoladas por provedor (`llm-key-<provider>`) são mais simples, auditáveis e menos propensas a corrupção parcial.

---

## Notas e Comentarios

- Faz parte do **Vertical Slice 2** junto com `US-LLM-04`.

---

## Definition of Done Checklist

- [ ] Codigo implementado conforme criterios de aceitacao
- [ ] Decisao sobre Spec governada foi registrada
- [ ] Decisao sobre Contract governado foi registrada
- [ ] Nivel ScrumAIDev foi registrado
- [ ] Spec, Contract e BDD foram atualizados quando aplicavel
- [ ] Gates opcionais executados ou dispensados com justificativa
- [ ] Error handling observavel segue o padrao compartilhado quando aplicavel
- [ ] Code review aprovado
- [ ] Testes unitarios com cobertura adequada
- [ ] Testes de integracao e contract passando
- [ ] Documentacao atualizada
- [ ] Build/CI passando
- [ ] `Behavior change` documentado no PR
- [ ] Aprovacao do Product Owner
