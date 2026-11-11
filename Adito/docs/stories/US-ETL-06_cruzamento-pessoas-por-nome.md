# User Story: [US-ETL-06] Cruzamento de pessoas por nome normalizado

**Epic:** EPIC-07 — ETL do Adito  
**Prioridade:** Alta (segundo slice)  
**Story Points:** 5  
**Sprint:** —  
**Status:** Review (implementado na branch feat/etl-slices-1-2)  
**Requisitos:** FR10, FR11, FR13, BR02, BR03, BR05, NFR05, NFR06 (`docs/requirements/adito-etl.md`)  
**Nível ScrumAIDev:** 1

---

## 📖 História

**Como** membro da equipe de dados  
**Eu quero** rodar um script que liga as pessoas entre as fontes pelo nome normalizado e me mostra o que ligou, o que ficou sem par e o que ficou ambíguo  
**Para que** o oráculo responda perguntas que atravessam as bases e eu consiga ver e corrigir os casos duvidosos

### Contexto Adicional
Sem CPF e e-mail, o nome normalizado é a única chave de pessoa entre fontes. O script lê os brutos que existirem (no mínimo SRC + uma outra fonte), então pode começar com SRC e SigPesq e ganhar CNPq e Lattes depois.

---

## ✅ Critérios de Aceitação

- [ ] **CA1:** Um comando (ex.: `adito-etl cruzar`) lê os brutos presentes em `etl/brutos/` e diz quais fontes entraram.
- [ ] **CA2:** Para cada fonte, extrai as pessoas com nome, papel (aluno atendido, membro da equipe, coordenador, orientador, orientando, membro de grupo, dono do currículo) e referência ao registro de origem.
- [ ] **CA3:** Normaliza os nomes conforme BR02 (sem acento, minúsculo, sem pontuação, espaços únicos, partículas mantidas).
- [ ] **CA4:** A mesma forma normalizada é uma pessoa só; se uma fonte com id próprio (Lattes, CNPq) tiver dois ids com a mesma forma, o nome é marcado ambíguo e não é ligado (BR03).
- [ ] **CA5:** Grava `etl/trabalho/pessoas.json` com id opaco, nome e ocorrências por fonte. O id não carrega CPF, e-mail nem hash deles.
- [ ] **CA6:** Grava `etl/trabalho/relatorio_cruzamento.md` com: pessoas por fonte, pares ligados por par de fontes, nomes sem par por fonte e ambíguos com suas ocorrências.
- [ ] **CA7:** Rodar duas vezes sobre os mesmos brutos gera arquivos idênticos.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `etl/` módulo `cruzamento/` (normalização, leitores por fonte, ligação, relatório).
- **Referência:** `horizon_etl/src/core/logic/person_identity.py` (`normalize_participant_name`, `is_junk_name`) e `person_matcher.py`. Desde 2026-11-10 a inferência é a mesma do horizon com `strict_match=True` (BR02 rev.): forma normalizada, forma sem partículas/"Jr" e mesmas palavras em outra ordem, por igualdade exata; o fuzzy (semelhança ≥ 90) continua fora, como no horizon.

### Dependências
- [ ] US-ETL-02 e pelo menos mais uma fonte (US-ETL-03 no segundo slice).
- [ ] Sem dependência externa nova (biblioteca padrão: `unicodedata`, `json`).

### Considerações de Performance
- Dezenas de milhares de ocorrências; dicionário em memória basta.

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Normalização: acentos, maiúsculas, pontuação, espaços duplos, "D'Ávila", partículas.
- [ ] Ambíguos: dois ids Lattes com a mesma forma → ambíguo; dois alunos SRC iguais → uma pessoa.
- [ ] Determinismo: mesma entrada, mesmo `pessoas.json`.

### Testes de Integração
- [ ] Brutos pequenos de SRC + SigPesq geram pessoas e relatório coerentes.

### Testes Manuais
- [ ] Ler o relatório sobre os brutos reais e conferir uma amostra de 20 ligações.

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Normalizador de nomes + testes
- [ ] **[TASK-002]** Leitores de pessoas por fonte (SRC e SigPesq primeiro)
- [ ] **[TASK-003]** Ligação, ids opacos e regra de ambíguos
- [ ] **[TASK-004]** Relatório do cruzamento

---

## 🤖 IA Insights

### Riscos Identificados
- Homônimos no SRC e no SigPesq viram uma pessoa (risco aceito); grafias diferentes ficam sem par. O relatório é a defesa.

---

## 📝 Notas e Comentários

- **Pontos de esclarecimento:**
  - ~~[PRECISA CLARIFICAR: o id opaco de pessoa deve ser estável entre execuções?]~~ Resolvido na implementação (2026-11-10, a confirmar pelo usuário): estável, `p_` + 16 caracteres base32 do SHA-256 do nome normalizado. Não carrega CPF/e-mail; como o nome já vai em claro no pacote, o hash não expõe nada novo.
- **Spec governada:** US não exige Spec.
- **Contract governado:** US não exige Contract (o formato de `pessoas.json` vira contrato quando a montagem do pacote for especificada).

---

## ✓ Definition of Done Checklist

- [ ] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [ ] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [ ] Documentação atualizada
- [ ] Aprovação do Product Owner
