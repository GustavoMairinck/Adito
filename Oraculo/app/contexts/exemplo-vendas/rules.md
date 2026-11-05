Use estas regras quando a pergunta mencionar produtos, clientes, vendedores, canais, regiões ou categorias.
Para consultas analíticas use a view vfactvendasresolved; não faça JOIN com outras tabelas.

Mapeamento de entidades:
- produto -> produto; categoria de produto -> categoria_produto; segmento -> segmento_produto
- cliente -> cliente; porte do cliente -> porte_cliente ('Pequeno', 'Médio', 'Grande')
- setor do cliente -> setor_cliente (ex.: 'Indústria', 'Comércio', 'Educação', 'Saúde')
- vendedor -> vendedor; equipe de vendas -> equipe_vendas ('Equipe Enterprise', 'Equipe SMB', 'Equipe Digital')
- canal de venda -> canal (ex.: 'LinkedIn', 'Google Ads', 'Instagram', 'Indicação', 'Site', 'Evento ESX')
- cidade -> cidade; estado -> estado (sigla UF, ex.: 'SP', 'ES'); região -> regiao (ex.: 'Sudeste', 'Sul')

Métricas:
- Receita / receita líquida: SUM(receita_liquida). "Receita" nunca é valor_bruto.
- Faturamento bruto / valor total: SUM(valor_bruto)
- Lucro: SUM(lucro); custo: SUM(custo); desconto: SUM(desconto)
- Quantidade vendida: SUM(quantidade_vendida); quantidade de vendas: COUNT(id_venda)
- Margem: (SUM(lucro) / NULLIF(SUM(receita_liquida), 0)) * 100
- ROI de desconto: (SUM(desconto) / NULLIF(SUM(valor_bruto), 0)) * 100
- "Segmento" descreve o produto; "setor" descreve o cliente. Não confunda.

Tempo: data_venda (data), ano, mes, trimestre, semana (inteiros).
- "Este ano" -> ano = CAST(strftime('%Y', 'now') AS INTEGER)
- "Ano passado" -> ano = CAST(strftime('%Y', 'now') AS INTEGER) - 1
- "Este mês" -> mes = CAST(strftime('%m', 'now') AS INTEGER) AND ano = CAST(strftime('%Y', 'now') AS INTEGER)
- "Este trimestre" -> trimestre = ((CAST(strftime('%m', 'now') AS INTEGER) + 2) / 3) AND ano = CAST(strftime('%Y', 'now') AS INTEGER)
