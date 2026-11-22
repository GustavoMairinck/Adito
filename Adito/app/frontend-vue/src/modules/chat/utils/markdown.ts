function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function renderInlineMarkdown(value: string) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
}

export function renderMarkdown(value: string) {
  const lines = value.split(/\r?\n/)
  const html: string[] = []
  let activeList: 'ul' | 'ol' | null = null

  const closeList = (type?: 'ul' | 'ol') => {
    if (activeList && (!type || type !== activeList)) {
      html.push(`</${activeList}>`)
      activeList = null
    }
  }

  const openList = (type: 'ul' | 'ol') => {
    if (activeList === type) return
    closeList()
    html.push(`<${type}>`)
    activeList = type
  }

  for (const line of lines) {
    const trimmed = line.trim()

    if (!trimmed) {
      closeList()
      continue
    }

    if (/^---+$/.test(trimmed)) {
      closeList()
      html.push('<hr>')
      continue
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      closeList()
      const level = heading[1].length
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`)
      continue
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/)
    if (bullet) {
      openList('ul')
      html.push(`<li>${renderInlineMarkdown(bullet[1])}</li>`)
      continue
    }

    const numbered = trimmed.match(/^\d+\.\s+(.+)$/)
    if (numbered) {
      openList('ol')
      html.push(`<li>${renderInlineMarkdown(numbered[1])}</li>`)
      continue
    }

    closeList()
    html.push(`<p>${renderInlineMarkdown(trimmed)}</p>`)
  }

  closeList()
  return html.join('')
}
