# User Story: [US-005] Controlar quais dados saem para o LLM

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** In Progress

---

## 📖 História

**Como** responsável pelos dados da instituição
**Eu quero** que dados pessoais não sejam enviados à Mistral e que o envio do resto seja limitado
**Para que** usar o Oráculo de acordo com a LGPD

### Contexto Adicional
Três caminhos levam dados à Mistral: linhas de resultado que entram no histórico da conversa, valores únicos embedados para resolver nomes, e a própria pergunta com o esquema. Decidido em 2026-11-03: política **mascarar e limitar**, **histórico só com SQL** e **só criptografia de disco do SO**.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** Colunas declaradas em `sensitive_columns` não aparecem no prompt e o `set_authorizer` do SQLite nega a leitura delas, mesmo que o SQL gerado tente.
- [x] **Critério 2:** O `set_authorizer` nega tabelas e views que não estão expostas no contexto; leituras feitas de dentro de uma view exposta são liberadas.
- [x] **Critério 3:** Só campos não pessoais (`embed_columns`) são embedados; um campo não pode ser sensível e embedado ao mesmo tempo.
- [x] **Critério 4:** O histórico guarda só o SQL; as linhas são reexecutadas no `dados.db` ao abrir a conversa (409 se o esquema mudou).
- [x] **Critério 5:** Dashboards e tabelas usam todas as linhas; o SQL roda local e o resultado não passa pelo LLM.
- [ ] **Critério 6:** O limite de linhas enviado ao LLM respeita o `llm_row_limit` do contexto (padrão 20). Hoje a prévia está fixa em 5 linhas (US-012).
- [x] **Critério 7:** A tela Configurações explica o que sai do computador.
- [ ] **Critério 8:** Indicador na resposta quando ela usou dados enviados ao LLM; modo opcional só com agregados.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `core/datastore.py` (`ReadPolicy`), `core/contexts.py`, `agents/bi_agent/tool.py`, `agents/bi_agent/nodes/sql_validator.py`, `analytics_index/services.py`, `chat/stream_views.py`, `chat/views.py`, `useChatHistory.ts`
- **APIs necessárias:** `GET /api/chat/messages/<uuid>/rows`
- **Database changes:** `Message.metadata` deixa de guardar `data`

### Dependências
- N/A

### Considerações de Performance
- Sem impacto relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] `scripts/teste_nucleo_sqlite.py`: coluna sensível negada, view intermediária e tabela base negadas, CTE sobre view exposta aceita, prompt e DDL do RAG sem coluna sensível, histórico reexecuta o SQL e devolve 409 quando ele não roda mais.

### Testes de Integração
- N/A

### Testes Manuais
- N/A

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** `ReadPolicy` com `set_authorizer`
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Validador de SQL por lista de views (excluindo nomes de CTE)
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-003]** Histórico só com SQL e endpoint de linhas
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-004]** Aviso na tela Configurações
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-005]** Ligar `llm_row_limit` à prévia (US-012)
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-006]** Indicador por resposta e modo só agregados
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
A pergunta digitada vai inteira à Mistral: nomes escritos pelo usuário saem da máquina. O texto da resposta (`Message.content`) continua gravado e pode citar valores.

### Alternativas Consideradas
Pseudonimização com re-substituição (trocar nomes por tokens antes de enviar) e SQLCipher no próprio arquivo; ambos fora do escopo da primeira versão.

---

## 📝 Notas e Comentários

- 2026-11-03: mascarar e limitar; 20 linhas no prompt; histórico só com SQL; criptografia só a do disco do SO (BitLocker/LUKS).
- 2026-11-03: corrigido o mapeamento: `reflection.py` e `report.py` são código morto; o caminho vivo é a prévia da ferramenta `bi_agent`.

Registro completo: [PORTE_DESKTOP_DECISOES.md](../PORTE_DESKTOP_DECISOES.md).

---

## ✓ Definition of Done Checklist

- [ ] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [ ] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [ ] Documentação atualizada
- [ ] Build/CI passando
- [ ] Deploy em staging
- [ ] Aprovação do Product Owner
