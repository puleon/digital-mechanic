import { useMemo, useState } from 'react'
import type { Vehicle } from '../types'
import { statusInfo } from '../util'

interface Props {
  vehicles: Vehicle[]
  selected: Vehicle | null
  onSelect: (vehicleId: string) => void
}

export function VehiclePicker({ vehicles, selected, onSelect }: Props) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return vehicles
    return vehicles.filter((v) =>
      [v.vehicle_id, v.garage_no, v.make, v.model, v.engine_model]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(q),
    )
  }, [vehicles, query])

  if (!selected) return null

  return (
    <>
      <button className="vehicle-current" onClick={() => setOpen(true)}>
        <span className="plate">{selected.vehicle_id}</span>
        <span className="vehicle-meta">
          {selected.make} {selected.model ?? ''} · {selected.engine_model}
        </span>
        <span className="chevron">▾</span>
      </button>

      {open && (
        <div className="sheet-backdrop" onClick={() => setOpen(false)}>
          <div className="sheet" onClick={(event) => event.stopPropagation()}>
            <div className="sheet-head">
              <strong>Выбор ТС</strong>
              <button className="icon" onClick={() => setOpen(false)} aria-label="Закрыть">
                ✕
              </button>
            </div>
            <input
              autoFocus
              className="search"
              placeholder="Госномер, гаражный, марка или двигатель"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <div className="vehicle-list">
              {filtered.map((vehicle) => {
                const info = statusInfo(vehicle.status)
                return (
                  <button
                    key={vehicle.vehicle_id}
                    className={`vehicle-row ${vehicle.vehicle_id === selected.vehicle_id ? 'active' : ''}`}
                    onClick={() => {
                      onSelect(vehicle.vehicle_id)
                      setOpen(false)
                      setQuery('')
                    }}
                  >
                    <span className="vehicle-row-main">
                      <span className="plate">{vehicle.vehicle_id}</span>
                      <span className="muted small">{vehicle.garage_no}</span>
                      <span className="vehicle-row-model">
                        {vehicle.make} {vehicle.model ?? ''} · {vehicle.engine_model}
                      </span>
                    </span>
                    <span className={`dot tone-${info.tone}`} title={info.text} />
                  </button>
                )
              })}
              {!filtered.length && <p className="muted pad">Ничего не найдено</p>}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
