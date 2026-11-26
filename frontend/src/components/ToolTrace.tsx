import type { ToolCall } from '../types'

function summarize(calls: ToolCall[]): string {
  const counts = new Map<string, number>()
  for (const call of calls) counts.set(call.tool, (counts.get(call.tool) ?? 0) + 1)
  return [...counts.entries()]
    .map(([name, count]) => (count > 1 ? `${name} ×${count}` : name))
    .join(', ')
}

function preview(result: unknown): string {
  if (result && typeof result === 'object' && 'error' in result) {
    return String((result as { error: unknown }).error)
  }
  try {
    return JSON.stringify(result).slice(0, 420)
  } catch {
    return String(result)
  }
}

export function ToolTrace({ calls }: { calls?: ToolCall[] }) {
  if (!calls?.length) return null
  return (
    <details className="trace">
      <summary>Как агент пришёл к ответу · {summarize(calls)}</summary>
      <ul>
        {calls.map((call, index) => (
          <li key={index} className={call.error ? 'trace-error' : ''}>
            <code>{call.tool}</code>
            <span className="trace-args">{JSON.stringify(call.arguments)}</span>
            <pre>{preview(call.result)}</pre>
          </li>
        ))}
      </ul>
    </details>
  )
}
