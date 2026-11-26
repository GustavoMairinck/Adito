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
  llmProvider?: string
  llmSupportsEmbeddings?: boolean
  embeddingsNeedsRetrain?: boolean
  chatError503?: boolean
  /** Atraso em ms antes de finalizar o stream do chat (útil para testar botão Parar / Esc / segundo plano). */
  chatStreamDelayMs?: number
  role?: 'admin' | 'user'
  /** Há uma versão nova dos dados publicada (acende o aviso do canto). */
  dadosNovos?: boolean
  /** Primeiro uso: ainda não há dados.db baixado. */
  semDados?: boolean
  /** Versão nova do executável publicada (ex.: '0.2.0'). */
  appNovaVersao?: string
  /** Pré-ativa o modo opt-in de atualização automática no localStorage antes do boot. */
  autoUpdateEnabled?: boolean
  /** Linhas devolvidas na resposta do chat (padrão: projetos por grande área, 2 linhas). */
  chatData?: Array<Record<string, unknown>>
  /** Tipo de gráfico sugerido pelo agente de painéis na resposta do chat (padrão: nenhum). */
  chatChartType?: string
  /** Linhas por palavra da pergunta (a primeira palavra encontrada vence); senão vale `chatData`. */
  chatDataByQuestion?: Record<string, Array<Record<string, unknown>>>
  /** Pasta simulada escolhida no diálogo "Salvar como..." durante a exportação. */
  exportDir?: string
  /** Simula o usuário cancelando o diálogo "Salvar como..." na exportação. */
  exportCancel?: boolean
}

/**
 * Injeta `window.__TAURI_INTERNALS__` compatível com `@tauri-apps/api/core` v2
 * (incluindo `invoke`, `Channel`, `transformCallback` e `unregisterCallback`)
 * via `page.addInitScript()`, sem qualquer código condicional na aplicação de produção.
 */
export async function installTauriMock(page: Page, options: TauriMockOptions = {}): Promise<void> {
  const config = {
    llmConfigured: options.llmConfigured ?? true,
    llmProvider: options.llmProvider ?? 'gemini',
    llmSupportsEmbeddings: options.llmSupportsEmbeddings,
    embeddingsNeedsRetrain: options.embeddingsNeedsRetrain ?? false,
    chatError503: options.chatError503 ?? false,
    chatStreamDelayMs: options.chatStreamDelayMs ?? 0,
    role: options.role ?? 'admin',
    dadosNovos: options.dadosNovos ?? false,
    semDados: options.semDados ?? false,
    appNovaVersao: options.appNovaVersao ?? null,
    autoUpdateEnabled: options.autoUpdateEnabled ?? false,
    chatData: options.chatData ?? null,
    chatChartType: options.chatChartType ?? null,
    chatDataByQuestion: options.chatDataByQuestion ?? null,
    exportDir: options.exportDir ?? '/mock/Documentos',
    exportCancel: options.exportCancel ?? false,
  }

  await page.addInitScript((cfg) => {
    if (cfg.autoUpdateEnabled) {
      localStorage.setItem('adito:auto_update', 'true')
    }
    const callbacks = new Map<number, (raw: unknown) => void>()
    let nextCbId = 1
    let llmConfigured = cfg.llmConfigured
    let activeProvider = cfg.llmProvider || 'gemini'
    let activeModel: string | null = null
    let activeBaseUrl: string | null = null
    let dadosInstalados = !cfg.semDados
    let dadosVersaoAtual = cfg.semDados ? null : '2026-11-01'
    let dadosNovosPendentes = cfg.dadosNovos
    const updaterTelemetry = {
      checks: 0,
      downloads: 0,
      installs: 0,
      relaunches: 0,
      dadosInstalls: 0,
    }
    ;(window as unknown as Record<string, unknown>).__TAURI_MOCK_UPDATER__ = updaterTelemetry
    const exportedFiles: Array<{ nome: string; bytes: number[] }> = []
    ;(window as unknown as Record<string, unknown>).__TAURI_MOCK_EXPORTS__ = exportedFiles

    const PROVIDERS = [
      { id: 'gemini', label: 'Gemini', protocol: 'gemini', base_url: 'https://generativelanguage.googleapis.com/v1beta', default_model: 'gemini-3.5-flash-lite', supports_embeddings: true, default_embedding_model: 'gemini-embedding-2', requires_key: true, allow_custom_base_url: false },
      { id: 'openai', label: 'OpenAI', protocol: 'openai_compatible', base_url: 'https://api.openai.com/v1', default_model: 'gpt-4o-mini', supports_embeddings: true, default_embedding_model: 'text-embedding-3-small', requires_key: true, allow_custom_base_url: false },
      { id: 'openrouter', label: 'OpenRouter', protocol: 'openai_compatible', base_url: 'https://openrouter.ai/api/v1', default_model: 'google/gemini-2.5-flash', supports_embeddings: true, default_embedding_model: 'openai/text-embedding-3-small', requires_key: true, allow_custom_base_url: false },
      { id: 'mistral', label: 'Mistral AI', protocol: 'openai_compatible', base_url: 'https://api.mistral.ai/v1', default_model: 'ministral-8b-latest', supports_embeddings: true, default_embedding_model: 'mistral-embed', requires_key: true, allow_custom_base_url: false },
      { id: 'zai', label: 'Z.AI (GLM)', protocol: 'openai_compatible', base_url: 'https://api.z.ai/api/paas/v4', default_model: 'glm-4.5-flash', supports_embeddings: true, default_embedding_model: 'embedding-3', requires_key: true, allow_custom_base_url: true },
      { id: 'together', label: 'Together AI', protocol: 'openai_compatible', base_url: 'https://api.together.xyz/v1', default_model: 'meta-llama/Llama-3.3-70B-Instruct-Turbo', supports_embeddings: true, default_embedding_model: 'intfloat/multilingual-e5-large-instruct', requires_key: true, allow_custom_base_url: false },
      { id: 'fireworks', label: 'Fireworks AI', protocol: 'openai_compatible', base_url: 'https://api.fireworks.ai/inference/v1', default_model: 'accounts/fireworks/models/llama-v3p3-70b-instruct', supports_embeddings: true, default_embedding_model: 'nomic-ai/nomic-embed-text-v1.5', requires_key: true, allow_custom_base_url: false },
      { id: 'ollama', label: 'Ollama (Local)', protocol: 'openai_compatible', base_url: 'http://localhost:11434/v1', default_model: 'qwen2.5:7b', supports_embeddings: true, default_embedding_model: 'nomic-embed-text', requires_key: false, allow_custom_base_url: true },
    ]
    const hasKeyByProvider: Record<string, boolean> = Object.fromEntries(
      PROVIDERS.map((p) => [p.id, p.id === activeProvider && llmConfigured && p.id !== 'ollama'])
    )
    const activeSpec = () => PROVIDERS.find((p) => p.id === activeProvider) || PROVIDERS[0]

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

    // Exposto para os testes conferirem o que foi fixado no painel.
    ;(window as unknown as Record<string, unknown>).__TAURI_MOCK_WIDGETS__ = widgets

    const widgetRows: Record<string, Array<Record<string, unknown>>> = {
      'w-1': [
        { ano: 2023, total: 85 },
        { ano: 2024, total: 120 },
      ],
    }

    // Explorar dados: projetos sintéticos (sem nomes de pessoas) para catálogo, busca, filtro e gráfico.
    const AREAS = ['Engenharias', 'Ciências Exatas e da Terra', 'Ciências Humanas', 'Ciências Biológicas']
    const explorerRows: Record<string, Array<Record<string, unknown>>> = {
      vfact_projeto_pesquisa_resolved: Array.from({ length: 33 }, (_, i) => ({
        id_projeto: i + 1,
        titulo_projeto: i === 0 ? 'Robótica educacional 100%' : `Projeto ${String(i + 1).padStart(2, '0')}`,
        grande_area: AREAS[i % AREAS.length],
        ano: 2023 + (i % 2),
      })),
      vfact_orientacao_bolsa_resolved: [
        { id_orientacao: 1, modalidade: 'PIBIC', ano: 2024 },
        { id_orientacao: 2, modalidade: 'PIBITI', ano: 2024 },
      ],
      vfact_extensao_acao_resolved: [],
    }
    const explorerColumns = (name: string) => {
      const sample = explorerRows[name]?.[0]
      if (!sample) return []
      return Object.entries(sample).map(([column, value]) => ({ name: column, type: typeof value === 'number' ? 'INTEGER' : 'TEXT' }))
    }
    function explorerQuery(params: Record<string, unknown>) {
      const all = explorerRows[String(params.table)] || []
      const search = String(params.search || '').toLowerCase()
      const filterColumn = String(params.filter_column || '')
      const filterValue = String(params.filter_value || '')
      let rows = all.filter((row) => (
        (!search || Object.values(row).some((value) => String(value).toLowerCase().includes(search)))
        && (!filterColumn || !filterValue || String(row[filterColumn]) === filterValue)
      ))
      const sort = String(params.sort || Object.keys(all[0] || {})[0] || '')
      const desc = params.direction === 'desc'
      rows = [...rows].sort((a, b) => {
        const x = a[sort] as string | number
        const y = b[sort] as string | number
        return (x < y ? -1 : x > y ? 1 : 0) * (desc ? -1 : 1)
      })
      const pageSize = Number(params.page_size || 25)
      const page = Math.min(Number(params.page || 1), Math.max(1, Math.ceil(rows.length / pageSize)))
      const groupBy = String(params.group_by || '')
      const counts = new Map<unknown, number>()
      if (groupBy) for (const row of rows) counts.set(row[groupBy], (counts.get(row[groupBy]) || 0) + 1)
      return {
        rows: rows.slice((page - 1) * pageSize, page * pageSize),
        total: rows.length,
        page,
        page_size: pageSize,
        distribution: [...counts.entries()]
          .map(([value, count]) => ({ value, count }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 12),
      }
    }
    // Relatórios (EPIC-14): linhas e SQL de cada resposta do stream, para o relatório reexecutar.
    const chatRowsByMessage: Record<string, Array<Record<string, unknown>>> = {}
    const chatSqlByMessage: Record<string, string> = {}
    const reports: Record<string, { metadata: Record<string, unknown> } & Record<string, unknown>> = {}
    let reportSeq = 1
    let chatAnswerSeq = 0

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

    const activeStreams = new Map<number, {
      timers: Array<ReturnType<typeof setTimeout>>
      cb: (raw: unknown) => void
      nextIndex: number
      canceled: boolean
    }>()
    const canceledStreamIds: number[] = []
    ;(window as unknown as Record<string, unknown>).__TAURI_MOCK_CANCELED_IDS__ = canceledStreamIds
    let liveConversationSeq = 1

    function resolveChannelCallback(channelArg: unknown) {
      const serialized =
        channelArg && typeof channelArg === 'object' && 'id' in channelArg
          ? (channelArg as { id: number }).id
          : typeof channelArg === 'string' && channelArg.startsWith('__CHANNEL__:')
            ? Number(channelArg.split(':')[1])
            : null
      if (serialized === null) return null
      return callbacks.get(serialized) || null
    }

    function sendChannel(
      channelArg: unknown,
      messages: Array<{ msg: unknown; delayMs: number }>,
      streamId?: number,
    ) {
      const cb = resolveChannelCallback(channelArg)
      if (!cb) return
      const state = {
        timers: [] as Array<ReturnType<typeof setTimeout>>,
        cb,
        nextIndex: 0,
        canceled: false,
      }
      if (typeof streamId === 'number') {
        activeStreams.set(streamId, state)
      }
      let maxDelay = 0
      for (const item of messages) {
        maxDelay = Math.max(maxDelay, item.delayMs)
        const timer = setTimeout(() => {
          if (state.canceled) return
          const currentIndex = state.nextIndex++
          cb({ index: currentIndex, message: item.msg })
        }, item.delayMs)
        state.timers.push(timer)
      }
      const endTimer = setTimeout(() => {
        if (state.canceled) return
        if (typeof streamId === 'number') activeStreams.delete(streamId)
        cb({ index: state.nextIndex++, end: true })
      }, maxDelay + 10)
      state.timers.push(endTimer)
    }

    function handleRpc(method: string, params: Record<string, unknown>) {
      switch (method) {
        case 'health':
          return { status: 'ok' }
        case 'me': {
          const spec = activeSpec()
          const supportsEmb = cfg.llmSupportsEmbeddings ?? spec.supports_embeddings
          return {
            id: 'user-local',
            username: 'Pesquisador IFES',
            email: 'local@adito.ifes.edu.br',
            role: cfg.role,
            tenant_id: 'tenant-local',
            llm_configured: llmConfigured,
            llm_provider: spec.id,
            llm_provider_label: spec.label,
            llm_model: activeModel || spec.default_model,
            llm_supports_embeddings: supportsEmb,
            llm_is_local: spec.id === 'ollama',
          }
        }
        case 'config.llm_providers':
          return PROVIDERS
        case 'contextos.list':
          return CONTEXTOS
        case 'dashboard.kpis': {
          const ano = String(params.ano || '')
          const atualizado = dadosVersaoAtual === '2026-11-22'
          return {
            total_investido: ano === '2023' ? 'R$ 84.000,00' : atualizado ? 'R$ 410.000,00' : 'R$ 320.000,00',
            projetos_ativos: ano === '2023' ? 48 : atualizado ? 310 : 236,
            pagamentos_ano_vigente: 'R$ 95.000,00',
            equipe_alocada: ano === '2023' ? 24 : atualizado ? 105 : 89,
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
          return {
            tables: CONTEXTOS[0].views.map((view) => ({
              name: view.name,
              label: view.description,
              description: view.description,
              kind: 'fact',
              columns: explorerColumns(view.name),
              available: explorerColumns(view.name).length > 0,
            })),
          }
        case 'explorer.rows':
          return explorerQuery(params)
        case 'chat.reports.create': {
          const sections = (params.sections as Array<Record<string, unknown>>) || []
          const report = {
            id: `rep-${reportSeq++}`,
            role: 'assistant',
            content: String(params.title || ''),
            created_at: '2026-11-25T14:30:00Z',
            metadata: {
              type: 'report',
              title: String(params.title || ''),
              contexto_nome: CONTEXTOS[0].name,
              sections: sections.map((section) => ({
                source_message_id: section.message_id,
                title: section.title,
                sql: chatSqlByMessage[String(section.message_id)] || 'SELECT 1',
                field_formats: { total: 'integer' },
                chart_type: section.chart_type ?? null,
              })),
            },
          }
          reports[report.id] = report
          ;(window as unknown as Record<string, unknown>).__TAURI_MOCK_LAST_REPORT__ = { params, report }
          return report
        }
        case 'chat.report_rows': {
          const report = reports[String(params.id)]
          const sections = (report?.metadata.sections || []) as Array<Record<string, unknown>>
          return {
            sections: sections.map((section) => {
              const sql = String(section.sql || '')
              if (sql.includes('quebrado')) return { data: [], error: 'os dados mudaram desde a pergunta' }
              return { data: chatRowsByMessage[String(section.source_message_id)] || [], error: null }
            }),
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
        case 'admin.system_status': {
          const spec = activeSpec()
          const supportsEmb = cfg.llmSupportsEmbeddings ?? spec.supports_embeddings
          return {
            services: [
              { name: 'app.db', status: 'online', latency_ms: 1, url: 'app.db' },
              { name: 'dados.db', status: 'online', latency_ms: 1, url: 'dados.db' },
            ],
            systemStats: {
              version: '0.1.0',
              uptime: '0h 5m',
              vectorRows: 420,
              trainedDdl: 1,
              trainedDoc: 1,
              trainedExamples: 16,
              lastTraining: '2026-11-19T12:00:00Z',
            },
            embeddings: {
              supports_embeddings: supportsEmb,
              provider: spec.id,
              provider_label: spec.label,
              embedding_model: supportsEmb ? spec.default_embedding_model : null,
              expected_dim: spec.id === 'gemini' ? 1024 : spec.id === 'openai' ? 1536 : null,
              stored_dims: [1024],
              needs_retrain: cfg.embeddingsNeedsRetrain,
              incompatible_vectors: cfg.embeddingsNeedsRetrain ? 18 : 0,
            },
          }
        }
        case 'admin.contextos':
          return [
            {
              id: CONTEXTOS[0].id,
              slug: 'pesquisa-extensao-ifes',
              nome: 'Pesquisa, Extensão e Produção Científica (Ifes)',
              descricao: CONTEXTOS[0].description,
              ativo: true,
              tabelas: CONTEXTOS[0].views.map((v) => v.name),
              rag_itens: 18,
              valores: 420,
              atualizado_em: '2026-11-19T12:00:00Z',
              erros: [],
            },
          ]
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
        if (cmd === 'core_cancel') {
          const streamId = Number(args.id)
          if (Number.isFinite(streamId)) {
            canceledStreamIds.push(streamId)
            const active = activeStreams.get(streamId)
            if (active && !active.canceled) {
              active.canceled = true
              for (const t of active.timers) clearTimeout(t)
              activeStreams.delete(streamId)
              active.cb({
                index: active.nextIndex++,
                message: { event: '$end', ok: false, error: { status: 499, data: { detail: 'Cancelado.' } } },
              })
              active.cb({ index: active.nextIndex++, end: true })
            }
          }
          return undefined
        }
        if (cmd === 'llm_key_status') {
          return { configured: llmConfigured, store_available: true, error: null }
        }
        if (cmd === 'llm_config_status') {
          return {
            provider: activeProvider,
            model: activeModel,
            base_url: activeBaseUrl,
            configured: llmConfigured,
            store_available: true,
            has_key_by_provider: { ...hasKeyByProvider },
            error: null,
          }
        }
        if (cmd === 'test_llm_config') {
          return args.key === 'chave-invalida'
            ? { ok: false, reason: 'Chave inválida' }
            : { ok: true }
        }
        if (cmd === 'set_llm_config') {
          activeProvider = String(args.provider || 'gemini')
          activeModel = args.model ? String(args.model) : null
          activeBaseUrl = args.baseUrl ? String(args.baseUrl) : null
          if (args.key) hasKeyByProvider[activeProvider] = true
          llmConfigured = true
          return undefined
        }
        if (cmd === 'set_llm_key') {
          activeProvider = 'gemini'
          hasKeyByProvider.gemini = true
          llmConfigured = true
          return undefined
        }
        if (cmd === 'clear_llm_key') {
          const target = String(args.provider || activeProvider)
          hasKeyByProvider[target] = false
          if (target === activeProvider) llmConfigured = false
          return undefined
        }
        // Distribuição: por padrão os dados já estão instalados e nada novo foi publicado.
        if (cmd === 'dados_status') {
          return dadosInstalados
            ? { instalado: true, versao: dadosVersaoAtual || '2026-11-01', desenvolvimento: false, chave_configurada: true }
            : { instalado: false, versao: null, desenvolvimento: false, chave_configurada: false }
        }
        if (cmd === 'dados_verificar') {
          const novos = dadosNovosPendentes || !dadosInstalados
          return { versao: novos ? '2026-11-22' : (dadosVersaoAtual || '2026-11-01'), tamanho: 8000000, atualizacao: novos, precisa_chave: !dadosInstalados }
        }
        if (cmd === 'dados_instalar') {
          if (!dadosInstalados && args.chave !== 'a'.repeat(64)) {
            throw 'Essa chave não abre esta versão dos dados.'
          }
          dadosInstalados = true
          dadosVersaoAtual = '2026-11-22'
          dadosNovosPendentes = false
          updaterTelemetry.dadosInstalls += 1
          return '2026-11-22'
        }
        // Plugins oficiais de atualização (tauri-plugin-updater e tauri-plugin-process).
        if (cmd === 'plugin:updater|check') {
          updaterTelemetry.checks += 1
          if (!cfg.appNovaVersao) return null
          return {
            rid: 1001,
            currentVersion: '0.1.0',
            version: cfg.appNovaVersao,
            date: '2026-11-25T15:00:00Z',
            body: 'Nova versão do Adito',
            rawJson: {},
          }
        }
        if (cmd === 'plugin:updater|download') {
          updaterTelemetry.downloads += 1
          sendChannel(args.onEvent, [
            { msg: { event: 'Started', data: { contentLength: 100 } }, delayMs: 0 },
            { msg: { event: 'Progress', data: { chunkLength: 100 } }, delayMs: 5 },
            { msg: { event: 'Finished' }, delayMs: 10 },
          ])
          return 2001
        }
        if (cmd === 'plugin:updater|install') {
          updaterTelemetry.installs += 1
          return undefined
        }
        if (cmd === 'plugin:updater|download_and_install') {
          updaterTelemetry.downloads += 1
          updaterTelemetry.installs += 1
          sendChannel(args.onEvent, [
            { msg: { event: 'Started', data: { contentLength: 100 } }, delayMs: 0 },
            { msg: { event: 'Finished' }, delayMs: 5 },
          ])
          return undefined
        }
        if (cmd === 'plugin:resources|close') {
          return undefined
        }
        if (cmd === 'plugin:process|restart') {
          updaterTelemetry.relaunches += 1
          return undefined
        }
        if (cmd === 'exportar_arquivo') {
          if (cfg.exportCancel) {
            return { nome: '', caminho: '', cancelado: true }
          }
          const nome = String(args.nome || 'adito-dados.csv')
          const bytes = Array.isArray(args.bytes) ? (args.bytes as number[]) : []
          exportedFiles.push({ nome, bytes })
          return { nome, caminho: `${cfg.exportDir}/${nome}`, cancelado: false }
        }
        if (cmd === 'core_call') {
          return handleRpc(String(args.method), (args.params as Record<string, unknown>) || {})
        }
        if (cmd === 'core_stream') {
          const streamId = Number(args.id)
          const params = (args.params as Record<string, unknown>) || {}
          if (cfg.chatError503 || !llmConfigured) {
            sendChannel(args.onEvent, [
              {
                msg: { event: '$end', ok: false, error: { status: 503, data: { detail: 'Chave do Gemini não configurada.' } } },
                delayMs: 0,
              },
            ], streamId)
            return undefined
          }
          const question = String(params.question || '')
          const rawConvId = params.conversation_id ? String(params.conversation_id) : ''
          const resolvedConvId = rawConvId && !rawConvId.startsWith('local-')
            ? rawConvId
            : `conv-live-${liveConversationSeq++}`
          const delay = Number(cfg.chatStreamDelayMs || 0)
          const finalDelay = delay > 0 ? delay : 15
          const byQuestion = Object.entries(cfg.chatDataByQuestion || {})
            .find(([word]) => question.toLowerCase().includes(word.toLowerCase()))
          const answerRows = byQuestion?.[1] || cfg.chatData || [
            { grande_area: 'Engenharias', total: 120 },
            { grande_area: 'Ciências Exatas', total: 116 },
          ]
          const answerId = `msg-live-${streamId}`
          const answerSql = byQuestion || cfg.chatData
            ? `SELECT … /* resposta ${++chatAnswerSeq}: ${question.replace(/\*\//g, '')} */`
            : 'SELECT grande_area, COUNT(*) AS total FROM vfact_projeto_pesquisa_resolved GROUP BY grande_area'
          chatRowsByMessage[answerId] = answerRows
          chatSqlByMessage[answerId] = answerSql
          sendChannel(args.onEvent, [
            {
              msg: { event: 'status', data: { message: 'Consultando dados acadêmicos...', conversation_id: resolvedConvId } },
              delayMs: 5,
            },
            {
              msg: { event: 'token', data: { text: `Parcial para "${question}": ` } },
              delayMs: 15,
            },
            {
              msg: {
                event: 'result',
                data: {
                  message_id: answerId,
                  conversation_id: resolvedConvId,
                  type: 'analysis',
                  text: `Resposta para "${question}": existem **236 projetos** de pesquisa ativos no Campus Serra.`,
                  sql: answerSql,
                  data: answerRows,
                  chart_type: cfg.chatChartType,
                },
              },
              delayMs: finalDelay,
            },
            {
              msg: { event: '$end', ok: true, result: { ok: true } },
              delayMs: finalDelay + 5,
            },
          ], streamId)
          return undefined
        }
        return undefined
      },
    }
  }, config)
}

/**
 * Modo Live: conecta `window.__TAURI_INTERNALS__` à ponte HTTP local (`e2e_bridge.py`)
 * que fala com o processo real `desktop_server.py` sobre `Adito/app/data/dados.db`.
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
        if (cmd === 'llm_config_status') {
          return {
            provider: 'gemini',
            model: null,
            base_url: null,
            configured: false,
            store_available: true,
            has_key_by_provider: {},
            error: null,
          }
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
