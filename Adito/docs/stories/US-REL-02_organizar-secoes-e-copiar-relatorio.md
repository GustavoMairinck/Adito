# User Story: [US-REL-02] Organizar as seções e copiar o relatório

**Epic:** EPIC-14 — Relatórios a partir das respostas do chat
**Prioridade:** Alta (slice 2)
**Story Points:** 3
**Sprint:** —
**Status:** Review

**Origem:** [`docs/discovery/relatorios-chat.md`](../discovery/relatorios-chat.md) · [`docs/requirements/relatorios-chat.md`](../requirements/relatorios-chat.md)
**Requisitos:** FR02 (título de seção editável), FR03, FR11; BR04, BR06; NFR06, NFR07

---

## 📖 História

**Como** gestor que monta um relatório no chat
**Eu quero** escolher a ordem das seções, dar a cada uma um título claro e copiar o relatório em texto
**Para que** o relatório conte a análise na sequência que faz sentido e eu possa colar o conteúdo em outro documento

### Contexto Adicional
A US-REL-01 entrega o formulário com seleção e o relatório no chat, usando a pergunta como título e a ordem cronológica. Esta story acrescenta a organização das seções e o "Copiar", no mesmo padrão do "Copiar" das respostas.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1 — Ordem:** no formulário, cada seção tem os controles "Subir" e "Descer" (com rótulos acessíveis); a primeira não sobe e a última não desce; o relatório gerado segue a ordem da tela.
- [x] **Critério 2 — Títulos de seção:** o título de cada seção é editável no formulário, começa com a pergunta original e não pode ficar vazio (com título vazio, "Gerar relatório" fica desativado e o campo mostra o motivo).
- [x] **Critério 3 — Relatório imutável:** depois de gerado, o relatório não é editado; para mudar ordem ou títulos, o usuário gera outro relatório, que vira nova mensagem.
- [x] **Critério 4 — Copiar:** a mensagem de relatório tem "Copiar", que copia em Markdown o título, a data, o contexto, a versão dos dados e, para cada seção, o número e o título, o número principal e a tabela (até 20 linhas, com o total), sem o texto original das respostas.
- [x] **Critério 5 — Seções com problema no texto copiado:** seções com erro ou sem linhas aparecem no texto copiado com o mesmo aviso mostrado na tela.
- [ ] **Critério 6 — Teclado:** reordenar, editar títulos e copiar funcionam só com o teclado.

---

## 🎨 Mockups/Wireframes

Mesma referência visual da US-REL-01, com os controles de ordem e o campo de título em cada linha da lista de seções.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** formulário do relatório e mensagem de relatório (criados na US-REL-01).
- **APIs necessárias:** nenhuma nova; o método de criação da US-REL-01 já recebe a ordem e os títulos.
- **Database changes:** nenhuma.

### Dependências
- [x] US-REL-01

### Considerações de Performance
- Nenhuma relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] Vitest: subir/descer nas pontas, título vazio bloqueia a geração, montagem do Markdown copiado (incluindo seção com erro e seção vazia).

### Testes de Integração
- [x] Playwright com `tauriMock.ts`: reordenar, renomear, gerar e conferir a ordem e os títulos no relatório; copiar e conferir o texto.

### Testes Manuais
- [ ] Colar o texto copiado num editor de Markdown e conferir as tabelas.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Controles de ordem no formulário
- [x] **[TASK-002]** Título editável por seção, com validação
- [x] **[TASK-003]** "Copiar" da mensagem de relatório em Markdown
- [x] **[TASK-004]** Testes Vitest e Playwright

---

## 🤖 IA Insights

### Sugestões de Implementação
- Reaproveitar a montagem de tabela em Markdown que o "Copiar" das respostas já faz.

### Riscos Identificados
- Arrastar e soltar seria mais natural, mas exigiria biblioteca nova ou mais código de acessibilidade; "Subir/Descer" atende sem dependência.

### Alternativas Consideradas
- Editar um relatório já gerado: descartado (BR06).

---

## 📝 Notas e Comentários

- 2026-11-25: implementada na branch `feat/relatorios-chat`, junto com as outras stories do EPIC-14, a pedido do usuário (sem sprint planning). Nota do spike de PDF: [`docs/resultados/spike-pdf-relatorio-2026-11-25.md`](../resultados/spike-pdf-relatorio-2026-11-25.md).

---

## ✓ Definition of Done Checklist

- [ ] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [x] Testes unitários com cobertura adequada
- [x] Testes de integração passando
- [x] Documentação atualizada
- [ ] Build/CI passando
- [ ] Deploy em staging
- [ ] Aprovação do Product Owner
