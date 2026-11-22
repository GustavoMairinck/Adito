> **Nota:** documento histórico. O projeto se chamava Adito (e, antes, Oraculo-ESX) na época; depois o nome passou a Adito e voltou a Adito (ver `Docs/ADR/ADR-0008-volta-ao-nome-adito.md`). O texto abaixo não foi reescrito.

# User Story: [US-011] Instalar o app sem ferramentas de desenvolvimento

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** Em revisão

---

## 📖 História

**Como** usuário final
**Eu quero** baixar um instalador e rodar o app
**Para que** não precisar de Python, Node, Rust nem Visual Studio Build Tools

### Contexto Adicional
Hoje o app roda só a partir do código (README de desenvolvimento). O Tauri gera `.msi`/`.exe` no Windows e `.deb`/`.AppImage` no Linux, mas embute só o binário Rust e o front; o backend Python precisa virar executável. Nem o Tauri nem o PyInstaller compilam para outro sistema.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** O backend vira o executável `oraculo-backend` (PyInstaller ou Nuitka), declarado como `externalBin` no `tauri.conf.json`. Desde 2026-11-17 (US-016) ele não recebe argumentos e usa stdin/stdout: empacotar como aplicativo de console, sem `--port`, e sem Django/daphne no bundle.
- [ ] **Critério 2:** `tauri build` gera `.exe` (NSIS) e `.msi` no Windows e `.deb`/`.AppImage` no Linux.
- [ ] **Critério 3:** Um workflow do GitHub Actions com matriz Windows e Linux gera os instaladores a cada tag.
- [ ] **Critério 4:** O app instalado roda num PC limpo, sem nenhuma ferramenta de desenvolvimento.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `src-tauri/tauri.conf.json`, `src-tauri/src/lib.rs` (já procura `oraculo-backend` fora do modo dev), novo spec do PyInstaller, novo workflow de CI
- **APIs necessárias:** Nenhuma
- **Database changes:** Backup do `app.db` antes de cada migração

### Dependências
- [ ] PyInstaller ou Nuitka
- [ ] Runners Windows e Linux no GitHub Actions

### Considerações de Performance
- Tamanho do instalador depende das dependências Python (LangChain, numpy, pandas); medir.

---

## 🧪 Plano de Testes

### Testes Unitários
- N/A

### Testes de Integração
- N/A

### Testes Manuais
- [ ] Instalar num Windows 10/11 e num Ubuntu limpos e fazer uma pergunta no chat.

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Empacotar o backend
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-002]** Registrar o sidecar no Tauri
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-003]** Workflow de CI com matriz
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-004]** Testar em máquinas limpas
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
Assinatura de código no Windows tem custo; sem ela o SmartScreen avisa ao instalar. `cargo-xwin` gera o `.exe` a partir do Linux, mas é experimental e não resolve o backend Python.

### Alternativas Consideradas
N/A

---

## 📝 Notas e Comentários

- 2026-11-04: o README deixa claro que o Build Tools é só para desenvolvimento no Windows.
- 2026-11-22: núcleo empacotado com PyInstaller como `adito-backend` (executável único, ~79 MB no Linux, sobe em ~1 s). Spec em `backend/adito-backend.spec`, build e conferência em `scripts/empacotar_nucleo.py`, `make instalador` local e o workflow `.github/workflows/release-app.yml` (matriz Windows e Linux, junto com o atualizador do ADR-0006). O `externalBin` entra só no build de instalador, para o modo dev seguir usando o `.venv`. Os critérios 2 e 3 dependem da primeira execução do workflow (o Windows só sai do CI) e o 4 de teste manual num Windows e num Ubuntu limpos. Detalhes em `docs/DISTRIBUICAO.md`.

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
