import type { ReactNode } from 'react'

function inline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${keyPrefix}-${index}`}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={`${keyPrefix}-${index}`}>{part.slice(1, -1)}</code>
    }
    return <span key={`${keyPrefix}-${index}`}>{part}</span>
  })
}

/** Минимальный рендер markdown-подобного текста агента: заголовки, списки, жирный. */
export function MarkdownLite({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  let numbered: string[] = []

  const flushBullets = () => {
    if (!bullets.length) return
    const items = bullets
    blocks.push(
      <ul key={`ul-${blocks.length}`}>
        {items.map((item, index) => (
          <li key={index}>{inline(item, `b-${blocks.length}-${index}`)}</li>
        ))}
      </ul>,
    )
    bullets = []
  }
  const flushNumbered = () => {
    if (!numbered.length) return
    const items = numbered
    blocks.push(
      <ol key={`ol-${blocks.length}`}>
        {items.map((item, index) => (
          <li key={index}>{inline(item, `n-${blocks.length}-${index}`)}</li>
        ))}
      </ol>,
    )
    numbered = []
  }
  const flush = () => {
    flushBullets()
    flushNumbered()
  }

  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) {
      flush()
      continue
    }
    if (/^#{1,4}\s/.test(line)) {
      flush()
      blocks.push(<h3 key={`h-${blocks.length}`}>{inline(line.replace(/^#{1,4}\s/, ''), `h-${blocks.length}`)}</h3>)
      continue
    }
    if (/^[-•]\s+/.test(line)) {
      flushNumbered()
      bullets.push(line.replace(/^[-•]\s+/, ''))
      continue
    }
    if (/^\d+\.\s+/.test(line)) {
      flushBullets()
      numbered.push(line.replace(/^\d+\.\s+/, ''))
      continue
    }
    flush()
    blocks.push(<p key={`p-${blocks.length}`}>{inline(line, `p-${blocks.length}`)}</p>)
  }
  flush()
  return <div className="markdown">{blocks}</div>
}
