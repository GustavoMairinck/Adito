Métricas oficiais:
- Receita / receita líquida: SUM(receita_liquida)
- Quantidade de vendas: COUNT(id_venda)

Mapeamento de termos:
- produto -> produto
- categoria de produto -> categoria_produto
- canal de venda -> canal
- vendedor -> vendedor
- porte do cliente -> porte_cliente ('Pequeno', 'Médio', 'Grande')

Campos de tempo: ano (int), mes (int), trimestre (int).
"Este ano" -> ano = CAST(strftime('%Y', 'now') AS INTEGER)
