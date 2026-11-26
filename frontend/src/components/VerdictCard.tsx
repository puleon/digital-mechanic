import type { Diagnosis } from '../types'
import { formatConfidence, formatScore, statusInfo } from '../util'

export function VerdictCard({ diagnosis }: { diagnosis: Diagnosis }) {
  const info = statusInfo(diagnosis.status)
  const title =
    diagnosis.status === 'anomaly'
      ? diagnosis.anomaly_title ?? 'Отклонение'
      : diagnosis.status === 'normal'
        ? 'Отклонений не выявлено'
        : 'Запись непригодна'

  return (
    <section className={`verdict tone-${info.tone}`}>
      <div className="verdict-top">
        <span className={`badge tone-${info.tone}`}>{info.text}</span>
        {diagnosis.anomaly_type && <span className="badge ghost">{diagnosis.anomaly_type}</span>}
        <span className="verdict-session">проверка {diagnosis.session_id}</span>
      </div>
      <h2>{title}</h2>
      <p className="verdict-desc">{diagnosis.description}</p>
      <div className="verdict-stats">
        {diagnosis.status !== 'check_failed' && (
          <>
            <span>
              уверенность <b>{formatConfidence(diagnosis.confidence)}</b>
            </span>
            <span>
              score <b>{formatScore(diagnosis.anomaly_score)}</b>
            </span>
          </>
        )}
        <span>
          запись <b>{diagnosis.signal_quality}</b>
        </span>
      </div>
    </section>
  )
}
