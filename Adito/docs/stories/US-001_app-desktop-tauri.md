# User Story: [US-001] Rodar o Oráculo como aplicativo desktop

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** Done

---

## 📖 História

**Como** gestor que usa o Oráculo
**Eu quero** abrir o Oráculo como um programa no meu computador, no Windows ou no Linux
**Para que** usar o assistente sem servidor, sem Docker e sem depender da infraestrutura da versão web

### Contexto Adicional
A versão web roda em Docker (Django, Vue/nginx, servidor MCP, Postgres/pgvector e Redis). Para o usuário final isso é inviável. Decidido em 2026-11-03: casca **Tauri** com o front Vue existente e o backend Python como processo filho; alvos **Windows e Linux** (sem macOS).

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** O app abre uma janela nativa e carrega o front Vue dentro dela.
- [x] **Critério 2:** Ao abrir, o app inicia o backend Python numa porta livre de `127.0.0.1`, com um token aleatório por execução.
- [x] **Critério 3:** O front recebe URL e token do Tauri (`invoke('backend_info')`), que espera o `/health` responder antes de liberar a tela.
- [x] **Critério 4:** Fechar a janela encerra o backend.
- [x] **Critério 5:** Dados e log ficam na pasta de dados do usuário (`~/.local/share/br.edu.ifes.leds.oraculo-esx/` no Linux, `%LOCALAPPDATA%\br.edu.ifes.leds.oraculo-esx\` no Windows).
- [ ] **Critério 6:** O mesmo fluxo foi verificado no Windows (até agora só no Linux).

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `src-tauri/` (novo), `backend/api/desktop_server.py` (novo), `frontend-vue/src/common/api/config.ts`, `frontend-vue/vite.config.ts`, `bi_agent_api/settings.py` (CORS, `ALLOWED_HOSTS`)
- **APIs necessárias:** Comando Tauri `backend_info`; `GET /health`
- **Database changes:** Nenhuma

### Dependências
- [x] Rust estável e Tauri 2
- [x] Bibliotecas do WebView (`libwebkit2gtk-4.1` no Linux, WebView2 no Windows)

### Considerações de Performance
- O backend leva alguns segundos para subir; o front espera até 90 s pelo `/health` e mostra o caminho do log se falhar.

---

## 🧪 Plano de Testes

### Testes Unitários
- N/A

### Testes de Integração
- [x] No Linux: `cargo run` abre a janela, o backend responde e `/api/me`, `/api/contextos` e `/api/chat/conversations` devolvem 200.

### Testes Manuais
- [x] Fechar a janela e confirmar que o processo do backend terminou.
- [ ] Repetir no Windows 10/11.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Criar `src-tauri/` com porta livre, token e `backend_info`
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Criar `desktop_server.py` (migrate, usuário local, daphne em `127.0.0.1`)
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-003]** Ajustar CORS/CSP para a origem do webview
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-004]** Front lê URL e token do Tauri; hash router
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-005]** Testar no Windows
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
Se o app for morto à força (sinal, gerenciador de tarefas), o backend fica órfão (ver US-013). O CSP só foi exercitado no modo dev.

### Alternativas Consideradas
Electron (mais pesado, embute Chromium) e manter a versão web com Docker (inviável para usuário final).

---

## 📝 Notas e Comentários

- 2026-11-03: decidido Tauri + Vue + backend Python como processo filho; Windows e Linux.
- 2026-11-04: casca compilada e rodando no Linux (Rust 1.99.1, tauri-cli 2.12.4).
- Em desenvolvimento o Tauri usa o Python de `.venv/`; o binário empacotado é a US-011.

Registro completo: [PORTE_DESKTOP_DECISOES.md](../PORTE_DESKTOP_DECISOES.md).

---

## ✓ Definition of Done Checklist

- [x] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [ ] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [x] Documentação atualizada
- [ ] Build/CI passando
- [ ] Deploy em staging
- [ ] Aprovação do Product Owner
