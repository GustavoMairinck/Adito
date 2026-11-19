import type { Page } from '@playwright/test'

/**
 * Registra listener de `pageerror` para falhar o teste caso ocorra qualquer exceção JS
 * não tratada durante a renderização ou interação do usuário.
 */
export function trackPageErrors(page: Page): () => string[] {
  const errors: string[] = []
  page.on('pageerror', (err) => {
    errors.push(err.message || String(err))
  })
  return () => [...errors]
}

export interface TauriMockOptions {
  llmConfigured?: boolean
  chatError503?: boolean
  explorerError503?: boolean
  role?: 'admin' | 'user'
}

/**
 * Injeta `window.__TAURI_INTERNALS__` compatível com `@tauri-apps/api/core` v2
 * (incluindo `invoke`, `Channel`, `transformCallback` e `unregisterCallback`)
 * via `page.addInitScript()`, sem qualquer código condicional na aplicação de produção.
 */
export async function installTauriMock(page: Page, options: TauriMockOptions = {}): Promise<void> {
  const config = {
    llmConfigured: options.llmConfigured ?? true,
    chatError503: options.chatError503 ?? false,
    explorerError503: options.explorerError503 ?? false,
    role: options.role ?? 'admin',
  }

  await page.addInitScript((cfg) => {
    const callbacks = new Map<number, (raw: unknown) => void>()
    let nextCbId = 1
    let llmConfigured = cfg.llmConfigured

    const CONTEXTOS = [
      {
        id: '00000000-0000-0000-0000-000000000001',
        slug: 'pesquisa-extensao-ifes',
        name: 'Pesquisa e Extensão IFES',
        description: 'Base acadêmica consolidada (SRC, SigPesq, Lattes e CNPq DGP)',
        views: [
          { name: 'vfact_orientacao_bolsa_resolved', description: 'Orientações e Bolsas' },
          { name: 'vfact_projeto_pesquisa_resolved', description: 'Projetos de Pesquisa' },
          { name: 'vfact_extensao_acao_resolved', description: 'Ações de Extensão' },
        ],
      },
    ]

    const EXTRA_ORIENTACOES = Array.from({ length: 23 }, (_, idx) => ({
      ano: idx === 22 ? 2026 : 2025,
      titulo_projeto: idx === 22 ? 'Projeto Página 2 Exclusivo' : `Iniciação Científica Lote ${idx + 1}`,
      nome_orientador: `Docente Extra ${idx + 1}`,
      modalidade: idx % 2 === 0 ? 'BOLSISTA' : 'VOLUNTARIO',
      investimento_total_estimado: idx % 2 === 0 ? 4800 : 0,
    }))

    const ALL_ROWS: Record<string, Array<Record<string, unknown>>> = {
      vfact_orientacao_bolsa_resolved: [
        { ano: 2024, titulo_projeto: 'Monitoramento Inteligente de Redes', nome_orientador: 'Docente A', modalidade: 'BOLSISTA', investimento_total_estimado: 9600 },
        { ano: 2024, titulo_projeto: 'Plataforma de Dados Educacionais', nome_orientador: 'Docente B', modalidade: 'VOLUNTARIO', investimento_total_estimado: 0 },
        { ano: 2023, titulo_projeto: 'Robótica Aplicada à Indústria', nome_orientador: 'Docente C', modalidade: 'BOLSISTA', investimento_total_estimado: 8400 },
        ...EXTRA_ORIENTACOES,
      ],
      vfact_projeto_pesquisa_resolved: [
        { ano_inicio: 2024, titulo_projeto: 'Visão Computacional no Campus Serra', grande_area: 'Engenharias', parecer_diretoria: 'APROVADO' },
        { ano_inicio: 2023, titulo_projeto: 'Análise de Séries Temporais Acadêmicas', grande_area: 'Ciências Exatas', parecer_diretoria: 'APROVADO' },
      ],
      vfact_extensao_acao_resolved: [
        { ano_cadastro: 2024, titulo_acao: 'Oficina de Programação para Escolas Públicas', tipo_acao: 'CURSO', campus: 'Serra' },
      ],
    }

    const widgets: Array<Record<string, unknown>> = [
      {
        id: 'w-1',
        title: 'Bolsas por Ano',
        question_original: 'Quantas bolsas por ano?',
        sql_validated: 'SELECT ano, COUNT(*) AS total FROM vfact_orientacao_bolsa_resolved GROUP BY ano',
        chart_type: 'table',
        size: 'medium',
        sort_order: 'none',
        limit_rows: 10,
        status: 'OK',
        last_executed_at: '2026-11-18T12:00:00Z',
        grid_x: 0,
        grid_y: 0,
        grid_w: 6,
        grid_h: 8,
      },
    ]

    const widgetRows: Record<string, Array<Record<string, unknown>>> = {
      'w-1': [
        { ano: 2023, total: 85 },
        { ano: 2024, total: 120 },
      ],
    }

    const conversations: Array<Record<string, unknown>> = [
      {
        id: 'conv-1',
        title: 'Panorama de Projetos',
        contexto: CONTEXTOS[0].id,
        created_at: '2026-11-18T12:00:00Z',
        messages: [
          { id: 'm-1', role: 'user', content: 'Quantos projetos existem?', created_at: '2026-11-18T12:00:01Z' },
          {
            id: 'm-2',
            role: 'assistant',
            content: 'Existem **236 projetos** de pesquisa cadastrados.',
            created_at: '2026-11-18T12:00:02Z',
            metadata: { sql: 'SELECT COUNT(*) AS total FROM vfact_projeto_pesquisa_resolved', type: 'analysis' },
          },
        ],
      },
    ]

    function sendChannel(channelArg: unknown, messages: unknown[]) {
      const serialized =
        channelArg && typeof channelArg === 'object' && 'id' in channelArg
          ? (channelArg as { id: number }).id
          : typeof channelArg === 'string' && channelArg.startsWith('__CHANNEL__:')
            ? Number(channelArg.split(':')[1])
            : null
      if (serialized === null) return
      const cb = callbacks.get(serialized)
      if (!cb) return
      let idx = 0
      for (const msg of messages) {
        const currentIndex = idx++
        setTimeout(() => cb({ index: currentIndex, message: msg }), 5 * currentIndex)
      }
      const endIdx = idx
      setTimeout(() => cb({ index: endIdx, end: true }), 5 * endIdx + 10)
    }

    function handleRpc(method: string, params: Record<string, unknown>) {
      switch (method) {
        case 'health':
          return { status: 'ok' }
        case 'me':
          return {
            id: 'user-local',
            username: 'Pesquisador IFES',
            email: 'local@muninn.ifes.edu.br',
            role: cfg.role,
            tenant_id: 'tenant-local',
            llm_configured: llmConfigured,
          }
        case 'contextos.list':
          return CONTEXTOS
        case 'dashboard.kpis': {
          const ano = String(params.ano || '')
          return {
            total_investido: ano === '2023' ? 'R$ 84.000,00' : 'R$ 320.000,00',
            projetos_ativos: ano === '2023' ? 48 : 236,
            pagamentos_ano_vigente: 'R$ 95.000,00',
            equipe_alocada: ano === '2023' ? 24 : 89,
          }
        }
        case 'dashboard.top_projects':
          return [
            { nome: 'Monitoramento Inteligente de Redes', valor: 48000, valor_formatado: 'R$ 48.000,00', status: 'PIBIC' },
            { nome: 'Visão Computacional no Campus Serra', valor: 36000, valor_formatado: 'R$ 36.000,00', status: 'PIBITI' },
          ]
        case 'dashboard.charts':
          return {
            por_ano: [
              { year: 2023, value: 140000 },
              { year: 2024, value: 180000 },
            ],
            mensal: [
              { month: '1', value: 15000 },
              { month: '2', value: 18000 },
            ],
            ano_vigente: 2026,
            anos_disponiveis: [2024, 2023],
            areas_disponiveis: ['Engenharias', 'Ciências Exatas'],
            modalidades_disponiveis: ['PIBIC', 'PIBITI'],
            statuses_disponiveis: ['BOLSISTA', 'VOLUNTARIO'],
          }
        case 'widgets.list':
          return widgets
        case 'widgets.refresh': {
          const id = String(params.id || '')
          return {
            widget_status: 'OK',
            data: widgetRows[id] || [{ grande_area: 'Engenharias', total: 120 }],
          }
        }
        case 'widgets.create': {
          const created = {
            id: `w-${widgets.length + 1}`,
            title: String(params.title || 'Widget Novo'),
            question_original: String(params.question_original || ''),
            sql_validated: String(params.sql_validated || ''),
            chart_type: String(params.chart_type || 'table'),
            size: 'medium',
            sort_order: 'none',
            limit_rows: 10,
            status: 'OK',
            last_executed_at: '2026-11-19T12:00:00Z',
            grid_x: 0,
            grid_y: 8,
            grid_w: 6,
            grid_h: 8,
          }
          widgets.push(created)
          widgetRows[created.id] = [
            { grande_area: 'Engenharias', total: 120 },
            { grande_area: 'Ciências Exatas', total: 116 },
          ]
          return created
        }
        case 'widgets.update':
          return { ok: true }
        case 'widgets.delete': {
          const idx = widgets.findIndex((w) => w.id === params.id)
          if (idx >= 0) widgets.splice(idx, 1)
          return { ok: true }
        }
        case 'explorer.tables':
          if (cfg.explorerError503) {
            throw {
              status: 503,
              data: { detail: 'Não foi possível ler os dados. Verifique o dados.db e recarregue os contextos em Administração.' },
            }
          }
          return {
            tables: [
              {
                name: 'vfact_orientacao_bolsa_resolved',
                label: 'Orientações e Bolsas',
                description: 'Bolsas e orientações de pesquisa',
                kind: 'fact',
                available: true,
                columns: [
                  { name: 'ano', type: 'INTEGER' },
                  { name: 'titulo_projeto', type: 'TEXT' },
                  { name: 'nome_orientador', type: 'TEXT' },
                  { name: 'modalidade', type: 'TEXT' },
                  { name: 'investimento_total_estimado', type: 'REAL' },
                ],
              },
              {
                name: 'vfact_projeto_pesquisa_resolved',
                label: 'Projetos de Pesquisa',
                description: 'Projetos SigPesq',
                kind: 'fact',
                available: true,
                columns: [
                  { name: 'ano_inicio', type: 'INTEGER' },
                  { name: 'titulo_projeto', type: 'TEXT' },
                  { name: 'grande_area', type: 'TEXT' },
                  { name: 'parecer_diretoria', type: 'TEXT' },
                ],
              },
              {
                name: 'vfact_extensao_acao_resolved',
                label: 'Ações de Extensão',
                description: 'Ações SRC',
                kind: 'fact',
                available: true,
                columns: [
                  { name: 'ano_cadastro', type: 'INTEGER' },
                  { name: 'titulo_acao', type: 'TEXT' },
                  { name: 'tipo_acao', type: 'TEXT' },
                  { name: 'campus', type: 'TEXT' },
                ],
              },
            ],
          }
        case 'explorer.rows': {
          const table = String(params.table || 'vfact_orientacao_bolsa_resolved')
          const search = String(params.search || '').trim().toLowerCase()
          const sortCol = String(params.sort || '')
          const direction = String(params.direction || 'desc')
          const page = Math.max(1, Number(params.page || 1))
          const pageSize = Math.max(1, Number(params.page_size || 25))
          const source = ALL_ROWS[table] || []
          const filtered = search
            ? source.filter((row) => JSON.stringify(row).toLowerCase().includes(search))
            : [...source]
          if (sortCol) {
            filtered.sort((a, b) => {
              const av = a[sortCol]
              const bv = b[sortCol]
              if (av === bv) return 0
              const cmp = typeof av === 'number' && typeof bv === 'number'
                ? av - bv
                : String(av ?? '').localeCompare(String(bv ?? ''), 'pt-BR')
              return direction === 'asc' ? cmp : -cmp
            })
          }
          const start = (page - 1) * pageSize
          const paged = filtered.slice(start, start + pageSize)
          const columns = source.length > 0 ? Object.keys(source[0]) : []
          return {
            table,
            columns,
            rows: paged,
            total: filtered.length,
            page,
            page_size: pageSize,
          }
        }
        case 'chat.conversations.list':
          return conversations
        case 'chat.message_rows':
          return { data: [{ total: 236 }] }
        case 'chat.conversations.delete':
          return { ok: true }
        case 'config.test_llm_key':
          return params.key === 'chave-invalida'
            ? { ok: false, reason: 'Chave Gemini rejeitada' }
            : { ok: true }
        case 'admin.system_status':
          return {
            status: 'ok',
            database: { ok: true, path: 'dados.db', views: 6 },
            llm: { configured: llmConfigured, model: 'gemini-3.5-flash-lite' },
            embeddings: { total: 420 },
          }
        case 'admin.query_executions':
          return { results: [], count: 0 }
        case 'admin.trainings.list':
          return []
        default:
          return {}
      }
    }

    ;(window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {
      transformCallback(callback: (raw: unknown) => void) {
        const id = nextCbId++
        callbacks.set(id, callback)
        return id
      },
      unregisterCallback(id: number) {
        callbacks.delete(id)
      },
      async invoke(cmd: string, args: Record<string, unknown> = {}) {
        if (cmd === 'core_ready') return undefined
        if (cmd === 'core_cancel') return undefined
        if (cmd === 'llm_key_status') {
          return { configured: llmConfigured, store_available: true, error: null }
        }
        if (cmd === 'set_llm_key') {
          llmConfigured = true
          return undefined
        }
        if (cmd === 'clear_llm_key') {
          llmConfigured = false
          return undefined
        }
        if (cmd === 'core_call') {
          return handleRpc(String(args.method), (args.params as Record<string, unknown>) || {})
        }
        if (cmd === 'core_stream') {
          const params = (args.params as Record<string, unknown>) || {}
          if (cfg.chatError503 || !llmConfigured) {
            sendChannel(args.onEvent, [
              { event: '$end', ok: false, error: { status: 503, data: { detail: 'Chave do Gemini não configurada.' } } },
            ])
            return undefined
          }
          const question = String(params.question || '')
          sendChannel(args.onEvent, [
            { event: 'status', data: { message: 'Consultando dados acadêmicos...' } },
            { event: 'token', data: { text: 'Foram encontrados ' } },
            {
              event: 'result',
              data: {
                message_id: 'msg-live-1',
                conversation_id: 'conv-live-1',
                type: 'analysis',
                text: `Resposta para "${question}": existem **236 projetos** de pesquisa ativos no Campus Serra.`,
                sql: 'SELECT grande_area, COUNT(*) AS total FROM vfact_projeto_pesquisa_resolved GROUP BY grande_area',
                data: [
                  { grande_area: 'Engenharias', total: 120 },
                  { grande_area: 'Ciências Exatas', total: 116 },
                ],
              },
            },
            { event: '$end', ok: true, result: { ok: true } },
          ])
          return undefined
        }
        return undefined
      },
    }
  }, config)
}

/**
 * Modo Live: conecta `window.__TAURI_INTERNALS__` à ponte HTTP local (`e2e_bridge.py`)
 * que fala com o processo real `desktop_server.py` sobre `Muninn/app/data/dados.db`.
 */
export async function installLiveBridge(page: Page, bridgeUrl: string): Promise<void> {
  await page.addInitScript((url) => {
    const callbacks = new Map<number, (raw: unknown) => void>()
    let nextCbId = 1

    ;(window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {
      transformCallback(callback: (raw: unknown) => void) {
        const id = nextCbId++
        callbacks.set(id, callback)
        return id
      },
      unregisterCallback(id: number) {
        callbacks.delete(id)
      },
      async invoke(cmd: string, args: Record<string, unknown> = {}) {
        if (cmd === 'core_ready') {
          const res = await fetch(`${url}/health`)
          if (!res.ok) throw new Error('Bridge indisponível')
          return undefined
        }
        if (cmd === 'core_cancel') return undefined
        if (cmd === 'llm_key_status') {
          return { configured: false, store_available: true, error: null }
        }
        if (cmd === 'core_call') {
          const res = await fetch(`${url}/rpc`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ method: args.method, params: args.params || {} }),
          })
          const payload = await res.json()
          if (!payload.ok) {
            throw payload.error || { status: 500, data: { detail: 'Erro RPC live' } }
          }
          return payload.result
        }
        return undefined
      },
    }
  }, bridgeUrl)
}
