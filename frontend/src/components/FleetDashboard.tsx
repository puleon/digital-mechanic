import type { Fleet, Vehicle } from '../types'
import { formatDateTime, formatScore } from '../util'

interface Props {
  fleet: Fleet | null
  onPick: (vehicleId: string) => void
}

const SECTIONS: { key: 'quarantine' | 'attention' | 'ok'; title: string; hint: string }[] = [
  { key: 'quarantine', title: 'Карантин', hint: 'критическое отклонение' },
  { key: 'attention', title: 'Требует внимания', hint: 'плановый контроль' },
  { key: 'ok', title: 'Норма', hint: 'можно эксплуатировать' },
]

function VehicleRow({ vehicle, onPick }: { vehicle: Vehicle; onPick: (id: string) => void }) {
  return (
    <button className="fleet-row" onClick={() => onPick(vehicle.vehicle_id)}>
      <span className="plate">{vehicle.vehicle_id}</span>
      <span className="fleet-row-model">
        {vehicle.make} {vehicle.model ?? ''}
        <span className="muted small"> · {vehicle.engine_model}</span>
      </span>
      <span className="fleet-row-meta">
        <b>{formatScore(vehicle.anomaly_score)}</b>
        <span className="muted tiny">{formatDateTime(vehicle.checked_at)}</span>
      </span>
    </button>
  )
}

export function FleetDashboard({ fleet, onPick }: Props) {
  if (!fleet) return <div className="pad muted">Загрузка сводки…</div>

  return (
    <div className="fleet">
      <div className="tiles">
        <div className="tile tone-ok">
          <b>{fleet.counts.ok}</b>
          <span>в норме</span>
        </div>
        <div className="tile tone-warn">
          <b>{fleet.counts.attention}</b>
          <span>внимание</span>
        </div>
        <div className="tile tone-danger">
          <b>{fleet.counts.quarantine}</b>
          <span>карантин</span>
        </div>
      </div>

      {SECTIONS.map((section) => {
        const items = fleet.buckets[section.key]
        return (
          <section key={section.key} className="fleet-section">
            <h3>
              {section.title} <span className="muted small">{items.length}</span>
              <span className="muted tiny section-hint">{section.hint}</span>
            </h3>
            {items.length ? (
              items.map((vehicle) => (
                <VehicleRow key={vehicle.vehicle_id} vehicle={vehicle} onPick={onPick} />
              ))
            ) : (
              <p className="muted small pad">Пусто</p>
            )}
          </section>
        )
      })}
    </div>
  )
}
