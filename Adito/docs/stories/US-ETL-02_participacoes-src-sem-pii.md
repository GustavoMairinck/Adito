# User Story: [US-ETL-02] Participações do SRC sem CPF nem e-mail

**Epic:** EPIC-07 — ETL do Adito  
**Prioridade:** Alta (primeiro vertical slice)  
**Story Points:** 5  
**Sprint:** —  
**Status:** In Progress (implementado; falta rodar com a credencial)  
**Requisitos:** FR02, FR03, BR01, NFR02, NFR04, NFR06 (filtro de PII) (`docs/requirements/adito-etl.md`)  
**Nível ScrumAIDev:** 1

---

## 📖 História

**Como** membro da equipe de dados  
**Eu quero** baixar as atividades de cada ação do SRC com o público-alvo e a equipe de execução, guardando só o nome e campos não pessoais  
**Para que** os extensionistas e alunos atendidos possam ser cruzados com as outras fontes sem que CPF ou e-mail fiquem guardados em lugar nenhum

### Contexto Adicional
O `gerenciar.py` do SRCEtl entra logado, pesquisa cada processo e lê o HTML de `gerenciar-publico-alvo.xhtml` e `gerenciar-equipe-execucao.xhtml` de cada atividade. Hoje ele guarda cada pessoa como dict com todas as colunas da tabela (Nome, CPF, E-mail, Situação…). Esta story copia esse fluxo e acrescenta o filtro por lista de colunas permitidas na coleta.

---

## ✅ Critérios de Aceitação

- [ ] **CA1:** Um comando (ex.: `adito-etl src-participacoes`) lê os processos de `etl/brutos/src/acoes/_index.json` e grava `etl/brutos/src/participacoes/participacoes_<processo>.json` com atividades, público-alvo e equipe de execução.
- [ ] **CA2:** A credencial vem do Infisical (segredos `src-user`/`src-password`, nomes configuráveis) ou do `etl/.env`, conforme `ADITO_CREDENCIAIS`, e não aparece em log nem em arquivo gerado. *(Revisto em 2026-11-11.)*
- [x] **CA3:** Cada pessoa guarda só as colunas da lista de permitidas de público-alvo e de equipe. A lista sai das colunas reais da página e é **aprovada pelo usuário** antes do merge. *(Aprovada em 2026-11-10: Nome, Função, Vínculo, Situação, Início, Término, C.H, Certificado; conferir avisos de coluna nova na primeira rodada real.)*
- [ ] **CA4:** Coluna da página que não está na lista é descartada, e o comando avisa o nome dela uma vez por execução.
- [ ] **CA5:** Processos já gravados são pulados (retomada), e cada processo é gravado assim que termina.
- [ ] **CA6:** Credencial errada ou sessão expirada para o comando com mensagem clara, sem gravar arquivo parcial do processo em curso.
- [ ] **CA7:** Um teste automatizado varre `etl/brutos/` e falha se encontrar algo com formato de CPF ou de e-mail, ou chave chamada CPF/e-mail.
- [ ] **CA8:** O comando atualiza `etl/brutos/src/_extracao.json` com totais de atividades, público-alvo, equipe e falhas.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `etl/` subpacote `fontes/src/` (participações), filtro de colunas comum, teste de PII.
- **Origem do código:** `src_etl/etl/gerenciar.py`, `models.py` (`AtividadeParticipacoes`, `AcaoParticipacoes`), `run_participacoes` em `pipeline.py`, `cli_part.py`.
- **APIs necessárias:** área autenticada do SRC.
- **Database changes:** nenhuma.

### Dependências
- [ ] US-ETL-01 (estrutura do `etl/` e `_index.json`).
- [ ] Credencial do SRC da equipe.

### Considerações de Performance
- O SRC aceita uma sessão por usuário: coleta sequencial numa sessão; `workers` só como abas da mesma sessão, como o SRCEtl já faz.

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Filtro de colunas: mantém as permitidas, descarta e avisa as outras.
- [ ] Detector de PII: acha CPF com e sem máscara e e-mail; não acusa nome comum.

### Testes de Integração
- [ ] Rodada com `--processo <um processo>` contra o SRC real grava o arquivo sem CPF/e-mail.

### Testes Manuais
- [ ] Interromper no meio e rodar de novo: retoma sem duplicar.
- [ ] Senha errada: mensagem clara e nenhum arquivo parcial.

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Copiar fluxo autenticado e modelos do SRCEtl
- [ ] **[TASK-002]** Levantar colunas reais e submeter a lista de permitidas ao usuário
- [ ] **[TASK-003]** Filtro de colunas na coleta + aviso
- [ ] **[TASK-004]** Teste de PII sobre `etl/brutos/`
- [ ] **[TASK-005]** Comando com retomada e `_extracao.json`

---

## 🤖 IA Insights

### Sugestões de Implementação
Aplicar o filtro dentro de `_scrape_participacoes`, antes de montar o modelo, para que CPF/e-mail nunca cheguem a um objeto Python que possa ser serializado.

### Riscos Identificados
- Matrícula, telefone ou data de nascimento podem aparecer em colunas; a lista de permitidas (e não uma lista de proibidas) evita que passem.
- Sem CPF, a mesma pessoa em ações diferentes só se reconhece pelo nome (risco aceito, BR03).

### Alternativas Consideradas
- Guardar o bruto completo e filtrar depois: rejeitado no Discovery rev. 4 (CPF/e-mail descartados na coleta).

---

## 📝 Notas e Comentários

- **Spec governada:** US não exige Spec.
- **Contract governado:** US não exige Contract.

---

## ✓ Definition of Done Checklist

- [ ] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [ ] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [ ] Documentação atualizada
- [ ] Aprovação do Product Owner
