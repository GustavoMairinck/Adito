# ADR 0008: Nome do produto volta a ser Adito

**Status:** Aceito  
**Data:** 21/11/2026  
**Substitui:** [ADR 0005: Nome do produto passa a ser Muninn](./ADR-0005-nome-muninn.md)

## Contexto/Problema  
No [ADR-0005](./ADR-0005-nome-muninn.md) a equipe trocou o nome provisório Adito por Muninn, e o código, os prompts, o identifier do Tauri, as variáveis de ambiente e a documentação passaram a usar Muninn. Depois a equipe voltou atrás na decisão.

## Decisão Tomada  
O produto volta a se chamar **Adito**, agora como nome definitivo. Todo o código vivo troca Muninn por Adito:

- pasta `Adito/` no lugar de `Muninn/`; pacote `adito_etl` e CLI `adito-etl`; crate `adito`, sidecar `adito-backend`;
- identifier `br.edu.ifes.leds.adito`, com migração automática da pasta de dados e da chave do cofre do SO que usavam `br.edu.ifes.leds.muninn` ou, antes dele, `br.edu.ifes.leds.oraculo-esx`;
- variáveis `ADITO_*` no lugar de `MUNINN_*`, sem fallback;
- prompts dos agentes se apresentam como Adito, assistente de pesquisa e extensão do IFES;
- arquivos de logo `adito-*`.

Detalhes em [`Adito/docs/specs/especificacao_identidade_adito.md`](../../Adito/docs/specs/especificacao_identidade_adito.md).

## Justificativa  
1. **Decisão da equipe:** a equipe preferiu manter Adito como nome do produto.
2. **Continuidade:** Adito já era o nome usado no repositório, nas issues e nas conversas com o campus.

## Alternativas Consideradas  
* **Manter Muninn:** descartado pela equipe.
* **Voltar a Oraculo-ESX:** descartado; confunde com o sistema web de origem.

## Consequências  
* **Positivas:** o nome do produto volta a coincidir com o do repositório.
* **Negativas:** quem tem `.env` ou scripts locais com `MUNINN_*` precisa trocar para `ADITO_*`; branches abertas sobre `Muninn/` terão conflito de caminho.
* **Riscos:** perda aparente de dados ou da chave de API no primeiro start (mitigado pela migração automática, testada em Rust e em Python, que aceita as pastas do Muninn e do Oraculo-ESX).

## Referências  
* Documentos históricos e o ADR-0005 não foram reescritos; as notas dos históricos passam a apontar para este ADR.
