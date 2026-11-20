# User Story: [US-DEVEX-04] Compatibilidade de `rodar_desktop.sh` com VS Code Snap (`/snap/`) e GNOME Wayland

**Epic:** EPIC-09 — Produtividade de Desenvolvimento & Automação Local (DevEx)  
**GitHub Epic Issue:** [#87](https://github.com/SmartIdea-ifes-serra/Adito/issues/87)  
**GitHub US Issue:** [#87](https://github.com/SmartIdea-ifes-serra/Adito/issues/87)  
**Prioridade:** Alta (Slice 1)  
**Story Points:** 2  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** YES (`rodar_desktop.sh` higieniza variáveis `/snap/` e define `GDK_BACKEND=x11` sob Wayland antes do `cargo run`)

---

## Historia

**Como** desenvolvedor usando Linux GNOME sob Wayland (Ubuntu 24.04+) ou o terminal integrado do VS Code instalado via Snap,  
**Eu quero** que `rodar_desktop.sh` limpe variáveis contaminadas pelo Snap e configure `GDK_BACKEND=x11` em Wayland automaticamente,  
**Para que** a janela desktop do Tauri abra normalmente sem abortar com `GLib-GIO-ERROR` (Error 134) nem conflitos de `glibc`/`libpthread`.

### Contexto Adicional
No Ubuntu com GNOME Wayland, o GTK3 usado pelo Tauri/WebKitGTK aborta com `Settings schema 'org.gnome.settings-daemon.plugins.xsettings' does not contain a key named 'antialiasing'` (Error 134). Além disso, o terminal integrado do VS Code Snap injeta variáveis apontando para `/snap/...` (`GTK_PATH`, `GIO_MODULE_DIR`, `GSETTINGS_SCHEMA_DIR`, `LD_LIBRARY_PATH`, `GTK_EXE_PREFIX`, `GTK_IM_MODULE_FILE`), causando conflito de bibliotecas e schemas com o GTK/WebKit nativo do sistema.

### Pontos de Esclarecimento
Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **CA01 (Sanitização seletiva de variáveis `/snap/`):** Antes de executar `cargo run`, `rodar_desktop.sh` filtra **apenas as entradas** contendo `/snap/` em variáveis de lista separadas por `:` (`GTK_PATH`, `GIO_MODULE_DIR`, `GSETTINGS_SCHEMA_DIR`, `LD_LIBRARY_PATH`), preservando caminhos legítimos em valores mistos (ex.: `/opt/custom/lib:/snap/...:/usr/local/lib` → `/opt/custom/lib:/usr/local/lib`), e remove `GTK_EXE_PREFIX`/`GTK_IM_MODULE_FILE` quando apontam para `/snap/`.
- [x] **CA02 (Fallback `GDK_BACKEND=x11` restrito ao cenário Snap / opt-in):** Dentro do bloco `[ "${XDG_SESSION_TYPE:-}" = "wayland" ]`, mantém `WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"` e aplica `GDK_BACKEND="${GDK_BACKEND:-x11}"` **somente** quando detectado ambiente Snap (`$SNAP` ou sanitização de `/snap/`) ou quando o usuário ativa explicitamente `MUNINN_FORCE_X11=1` (preservando Wayland nativo, escala fracionária e ambientes sem XWayland).
- [x] **CA03 (Respeito a override manual):** Se o usuário exportar `GDK_BACKEND` ou `WEBKIT_DISABLE_DMABUF_RENDERER` manualmente antes de invocar o script, seus valores são preservados (`BR05`).
- [x] **CA04 (Sem impacto fora de Wayland/Snap):** Em sessões X11/macOS/WSL sem variáveis `/snap/`, `GDK_BACKEND` não é forçado e variáveis do sistema permanecem intactas.
- [x] **CA05 (Testes automatizados offline):** Testes executando a rotina de preparação de ambiente do `rodar_desktop.sh` (com stub de `cargo` e `curl`) validando limpeza de `/snap/`, preservação de `LD_LIBRARY_PATH` customizado, export de `GDK_BACKEND=x11` em Wayland e respeito a override manual.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; ajuste de variáveis de ambiente no launcher local `rodar_desktop.sh`.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Não altera regras de negócio nem contratos de interface/API.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Sem contrato externo.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Requisitos rastreados:** `FR05`, `FR09`, `BR05`, `NFR01`, `NFR02`, `NFR05`, `A04`
- **Touch List preliminar:**
  - `rodar_desktop.sh`
  - `Muninn/etl/tests/test_onboarding_makefile.py`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura
- **Componentes afetados:** `rodar_desktop.sh` (bloco de preparação antes de `cargo run`).
- **APIs necessarias:** Nenhuma.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A.
- **Erros observaveis esperados:** Evita `GLib-GIO-ERROR` / `SIGABRT` (Error 134) e conflitos de carregamento de bibliotecas do Snap.

### Dependencias
- [x] `US-DEVEX-03` concluída (commit anterior no mesmo arquivo `rodar_desktop.sh`).
- [x] Zero novas dependências externas.

### Consideracoes de Performance
- Impacto nulo (< 5 ms no startup do script).

---

## Plano de Testes

### Testes Unitarios / Integracao Local
- [x] Simulação com variáveis apontando para `/snap/code/...` verifica que todas foram removidas antes do `cargo run`.
- [x] Simulação com `LD_LIBRARY_PATH=/opt/custom/lib` (sem `/snap/`) verifica preservação intacta.
- [x] Simulação com `XDG_SESSION_TYPE=wayland` exporta `GDK_BACKEND=x11` e `WEBKIT_DISABLE_DMABUF_RENDERER=1`.
- [x] Simulação com `XDG_SESSION_TYPE=wayland GDK_BACKEND=wayland` preserva `GDK_BACKEND=wayland`.
