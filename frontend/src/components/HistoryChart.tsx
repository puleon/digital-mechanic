import type { Session } from '../types'
import { formatDateTime, plural, statusInfo } from '../util'

const W = 320
const H = 74
const PAD = 12

export function HistoryChart({ sessions }: { sessions: Session[] }) {
  const last = sessions.slice(-6)
  if (last.length < 2) return null

  const x = (index: number) => PAD + (index * (W - PAD * 2)) / Math.max(1, last.length - 1)
  const y = (score: number) => H - PAD - score * (H - PAD * 2)
  const points = last
    .map((session, index) => ({ session, index }))
    .filter((point) => point.session.anomaly_score !== null)

  const line = points.map((point) => `${x(point.index)},${y(point.session.anomaly_score!)}`).join(' ')

  return (
    <details className="chart-card">
      <summary>
        Динамика за {last.length} {plural(last.length, ['проверку', 'проверки', 'проверок'])}
        <span className="muted small">
          {' '}
          {last[last.length - 1].anomaly_score !== null
            ? `score ${last[last.length - 1].anomaly_score!.toFixed(2)}`
            : statusInfo(last[last.length - 1].status).text}
        </span>
      </summary>
      <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Динамика anomaly_score">
        <line x1={PAD} y1={y(0.5)} x2={W - PAD} y2={y(0.5)} className="grid" />
        {points.length > 1 && <polyline points={line} className="chart-line" />}
        {points.map((point) => (
          <circle
            key={point.session.session_id}
            cx={x(point.index)}
            cy={y(point.session.anomaly_score!)}
            r={4}
            className={`chart-dot tone-${statusInfo(point.session.status).tone}`}
          >
            <title>
              {formatDateTime(point.session.checked_at)} · {point.session.anomaly_score!.toFixed(2)}
            </title>
          </circle>
        ))}
        {last.map((session, index) =>
          session.anomaly_score === null ? (
            <g key={session.session_id}>
              <line
                x1={x(index)}
                y1={PAD}
                x2={x(index)}
                y2={H - PAD}
                className="chart-gap"
              />
              <title>Сбой записи · {formatDateTime(session.checked_at)}</title>
            </g>
          ) : null,
        )}
        <text x={PAD} y={H - 2} className="chart-label">
          0
        </text>
        <text x={W - PAD} y={H - 2} className="chart-label" textAnchor="end">
          1
        </text>
      </svg>
    </details>
  )
}
