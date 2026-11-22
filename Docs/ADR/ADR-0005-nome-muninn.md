> **Nota:** a equipe voltou atrás nesta decisão e o produto se chama Adito de novo (ver [ADR-0008](./ADR-0008-volta-ao-nome-adito.md)). O texto abaixo não foi reescrito; os caminhos `Muninn/` citados hoje são `Adito/`.

# ADR 0005: Nome do produto passa a ser Muninn

**Status:** Substituído pelo [ADR-0008](./ADR-0008-volta-ao-nome-adito.md)  
**Data:** 18/11/2026  

## Contexto/Problema  
O programa nasceu como adaptação do Oraculo-ESX, sistema web de BI com agentes. Para separá-lo do original, a equipe passou a chamá-lo de **Adito**, nome provisório. O código, os prompts dos agentes, o identifier do Tauri, as variáveis de ambiente e a documentação ficaram com uma mistura de Oraculo-ESX e Adito. Os agentes ainda se apresentavam como assistente de vendas.

## Decisão Tomada  
A equipe escolheu o nome **Muninn**. Na mitologia nórdica, Muninn é um dos dois corvos de Odin: voa pelo mundo e volta trazendo informações. Todo o código vivo passa a usar o nome:

- pasta `Muninn/` no lugar de `Adito/`; pacote `muninn_etl` e CLI `muninn-etl`; crate `muninn`, sidecar `muninn-backend`;
- identifier `br.edu.ifes.leds.muninn`, com migração automática da pasta de dados e da chave do cofre do SO que usavam `br.edu.ifes.leds.oraculo-esx`;
- variáveis `MUNINN_*` no lugar de `ORACULO_*` e `ADITO_*`, sem fallback (corte deliberadamente brusco);
- prompts dos agentes se apresentam como Muninn, assistente de pesquisa e extensão do IFES;
- arquivos de logo `muninn-*` (a arte do corvo substitui as imagens atuais depois).

Detalhes em [`Muninn/docs/specs/especificacao_identidade_muninn.md`](../../Muninn/docs/specs/especificacao_identidade_muninn.md).

## Justificativa  
1. **Decisão da equipe:** o nome foi escolhido em conjunto pela equipe do projeto.
2. **Significado:** o produto reúne dados de várias fontes (SRC, SigPesq, CNPq/DGP, Lattes) e os entrega ao usuário em linguagem natural, como o corvo que traz informações do mundo.
3. **Identidade própria:** "Adito" era provisório, e "Oraculo-ESX" confunde com o projeto web original.

## Alternativas Consideradas  
* **Manter Adito:** descartado; era nome provisório, sem identidade própria.
* **Voltar a Oraculo-ESX:** descartado; confunde com o sistema web de origem.

## Consequências  
* **Positivas:** um nome só no código, na interface e nos prompts; agentes deixam de citar vendas.
* **Negativas:** quem tem `.env` ou scripts locais com `ORACULO_*`/`ADITO_*` precisa trocar para `MUNINN_*`; branches abertas sobre `Adito/` terão conflito de caminho.
* **Riscos:** perda aparente de dados ou da chave de API no primeiro start (mitigado pela migração automática, testada em Rust e em Python). O repositório no GitHub é renomeado à parte, pela equipe.

## Referências  
* Documentos históricos (stories, discovery, ADRs 0001–0004) não foram reescritos; ganharam uma nota com o nome da época.
