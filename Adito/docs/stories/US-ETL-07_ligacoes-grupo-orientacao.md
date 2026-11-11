# User Story: [US-ETL-07] Ligações de grupo e de orientação

**Epic:** EPIC-07 — ETL do Adito  
**Prioridade:** Média  
**Story Points:** 3  
**Sprint:** —  
**Status:** Backlog  
**Requisitos:** FR12, FR13, BR02, NFR05 (`docs/requirements/adito-etl.md`)  
**Nível ScrumAIDev:** 1

---

## 📖 História

**Como** membro da equipe de dados  
**Eu quero** que o cruzamento também ligue os grupos do SigPesq aos do CNPq e as orientações do SigPesq às do Lattes  
**Para que** o oráculo responda perguntas como "quais orientações do grupo X têm currículo Lattes com o mesmo título"

### Contexto Adicional
São as chaves que não são de pessoa e que o Discovery manteve: grupo pelo id de 16 dígitos do espelho e orientação por título normalizado + orientador normalizado.

---

## ✅ Critérios de Aceitação

- [ ] **CA1:** O cruzamento grava `etl/trabalho/ligacoes_grupos.json` (grupo SigPesq ↔ grupo CNPq) pelo id de 16 dígitos do espelho.
- [ ] **CA2:** Grava `etl/trabalho/ligacoes_orientacoes.json` (orientação SigPesq ↔ orientação Lattes) quando título normalizado e orientador normalizado coincidem.
- [ ] **CA3:** O título é normalizado com a mesma regra do nome (BR02).
- [ ] **CA4:** O relatório do cruzamento ganha as seções de grupos e orientações: ligados, sem par de cada lado e casos com mais de um par possível (não ligados).
- [ ] **CA5:** Se faltar o bruto do CNPq ou do Lattes, a ligação correspondente é pulada com aviso, sem erro.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `etl/` módulo `cruzamento/` (leitores de grupos e orientações, ligação, relatório).

### Dependências
- [ ] US-ETL-03, US-ETL-04, US-ETL-05 e US-ETL-06.

### Considerações de Performance
- Volume pequeno; dicionários em memória.

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Ligação de grupo por id de espelho (URL com e sem barras duplas).
- [ ] Orientação com título que só difere em acento/pontuação liga; com orientador diferente não liga.

### Testes de Integração
- [ ] Brutos pequenos das quatro fontes geram os dois arquivos de ligação e o relatório.

### Testes Manuais
- [ ] Conferir uma amostra de 10 orientações ligadas.

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Ligação de grupos pelo espelho
- [ ] **[TASK-002]** Ligação de orientações por título + orientador
- [ ] **[TASK-003]** Seções novas no relatório

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
