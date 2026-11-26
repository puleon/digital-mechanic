import { useEffect, useMemo, useRef, useState } from 'react'
import { getFleet, getVehicleCard, getVehicles, sendMessage } from './api'
import { FleetDashboard } from './components/FleetDashboard'
import { HistoryChart } from './components/HistoryChart'
import { TicketCard } from './components/TicketCard'
import { ToolTrace } from './components/ToolTrace'
import { VehiclePicker } from './components/VehiclePicker'
import { VerdictCard } from './components/VerdictCard'
import { MarkdownLite } from './MarkdownLite'
import type { Diagnosis, Fleet, Ticket, ToolCall, Vehicle, VehicleCard } from './types'
import { formatDateTime, statusInfo } from './util'

type Tab = 'mechanic' | 'fleet'

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  trace?: ToolCall[]
}

let messageCounter = 0
const nextId = () => `m-${++messageCounter}`

function findDiagnosis(trace: ToolCall[]): Diagnosis | null {
  for (const call of trace) {
    if (call.tool === 'get_diagnosis' && !call.error) {
      const result = call.result as { diagnosis?: Diagnosis } | null
      if (result?.diagnosis) return result.diagnosis
    }
  }
  return null
}

function findTickets(trace: ToolCall[], vehicleId: string): Ticket[] {
  const created: Ticket[] = []
  for (const call of trace) {
    if (call.tool !== 'create_ticket' || call.error) continue
    const result = call.result as { ticket_id?: string; payload?: Omit<Ticket, 'ticket_id' | 'created_at'> }
    if (!result?.ticket_id || !result.payload) continue
    created.push({
      ...result.payload,
      vehicle_id: vehicleId,
      ticket_id: result.ticket_id,
      created_at: new Date().toISOString(),
    })
  }
  return created
}

export default function App() {
  const [tab, setTab] = useState<Tab>('mechanic')
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [card, setCard] = useState<VehicleCard | null>(null)
  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string>(() => crypto.randomUUID())
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [fleet, setFleet] = useState<Fleet | null>(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  function resizeInput() {
    const field = inputRef.current
    if (!field) return
    field.style.height = '42px'
    field.style.height = `${Math.min(field.scrollHeight, 120)}px`
  }

  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const [list, fleetData] = await Promise.all([getVehicles(), getFleet()])
        if (!alive) return
        setVehicles(list)
        setFleet(fleetData)
        const preferred =
          list.find((vehicle) => vehicle.vehicle_id === 'B418HK98') ??
          list.find((vehicle) => vehicle.status === 'anomaly') ??
          list[0]
        if (preferred) setSelectedId(preferred.vehicle_id)
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : String(cause))
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (!selectedId) return
    let alive = true
    void (async () => {
      try {
        const data = await getVehicleCard(selectedId)
        if (!alive) return
        setCard(data)
        setTickets(data.tickets)
        setMessages([])
        setDiagnosis(null)
        setError('')
        setConversationId(crypto.randomUUID())
        setSessionId(data.sessions[data.sessions.length - 1]?.session_id ?? '')
      } catch (cause) {
        if (alive) setError(cause instanceof Error ? cause.message : String(cause))
      }
    })()
    return () => {
      alive = false
    }
  }, [selectedId])

  useEffect(() => {
    if (tab !== 'fleet') return
    void getFleet().then(setFleet).catch(() => undefined)
  }, [tab])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  const selected = useMemo(
    () => vehicles.find((vehicle) => vehicle.vehicle_id === selectedId) ?? null,
    [vehicles, selectedId],
  )

  const quickActions = useMemo(() => {
    const actions = ['Что проверить по руководству?', 'Почему это опасно?']
    if (diagnosis?.status === 'anomaly') actions.push('Создай заявку на дефектовку')
    return actions
  }, [diagnosis])

  function changeSession(nextSessionId: string) {
    setSessionId(nextSessionId)
    setMessages([])
    setDiagnosis(null)
    setConversationId(crypto.randomUUID())
  }

  async function send(text: string) {
    const message = text.trim()
    if (!message || !selected || !sessionId || loading) return
    setInput('')
    if (inputRef.current) inputRef.current.style.height = '42px'
    setError('')
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', text: message }])
    setLoading(true)
    try {
      const response = await sendMessage({
        vehicle_id: selected.vehicle_id,
        session_id: sessionId,
        message,
        conversation_id: conversationId,
      })
      const trace = response.tool_calls ?? []
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: response.reply, trace },
      ])
      const found = findDiagnosis(trace)
      if (found) setDiagnosis(found)
      const created = findTickets(trace, selected.vehicle_id)
      if (created.length) setTickets((prev) => [...created, ...prev])
      setConversationId(response.conversation_id)
    } catch (cause) {
      const textError = cause instanceof Error ? cause.message : String(cause)
      setError(textError.slice(0, 400))
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'assistant',
          text: 'Не удалось получить ответ. Проверьте, что Mock ML, Mock ТОиР и LLM доступны, и попробуйте ещё раз.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const latestTicket = tickets.find((ticket) => ticket.session_id === sessionId) ?? null

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">⚙</span>
          <span className="brand-text">
            <b>Цифровой механик</b>
            <span className="muted tiny">PoC · НейроДВС</span>
          </span>
        </div>
        <nav className="tabs">
          <button className={tab === 'mechanic' ? 'active' : ''} onClick={() => setTab('mechanic')}>
            Механик
          </button>
          <button className={tab === 'fleet' ? 'active' : ''} onClick={() => setTab('fleet')}>
            Парк
          </button>
        </nav>
      </header>

      {error && <div className="error">{error}</div>}

      {tab === 'mechanic' ? (
        <main className="mechanic">
          <div className="vehicle-panel">
            <VehiclePicker vehicles={vehicles} selected={selected} onSelect={setSelectedId} />
            {card && card.sessions.length > 0 && (
              <label className="session-picker">
                <span className="muted tiny">Проверка</span>
                <select value={sessionId} onChange={(event) => changeSession(event.target.value)}>
                  {[...card.sessions].reverse().map((session) => (
                    <option key={session.session_id} value={session.session_id}>
                      {formatDateTime(session.checked_at)} · {statusInfo(session.status).text} ·{' '}
                      {session.session_id}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <button
              className="primary"
              disabled={loading || !sessionId}
              onClick={() => void send('Получить результат диагностики')}
            >
              Получить результат диагностики
            </button>
          </div>

          {diagnosis && <VerdictCard diagnosis={diagnosis} />}
          {card && <HistoryChart sessions={card.sessions} />}

          <section className="chat">
            <div className="messages">
              {!messages.length && (
                <div className="hint">
                  <b>Проверка на посту ТО</b>
                  <span>
                    Выберите проверку и нажмите «Получить результат диагностики». Агент объяснит
                    отклонение по руководству, ответит на вопросы и оформит заявку на дефектовку.
                  </span>
                </div>
              )}
              {messages.map((message) => (
                <div key={message.id} className={`msg ${message.role}`}>
                  {message.role === 'assistant' ? (
                    <>
                      <MarkdownLite text={message.text} />
                      <ToolTrace calls={message.trace} />
                    </>
                  ) : (
                    <p>{message.text}</p>
                  )}
                </div>
              ))}
              {loading && (
                <div className="msg assistant typing" aria-label="Агент печатает">
                  <span />
                  <span />
                  <span />
                </div>
              )}
              <div ref={endRef} />
            </div>

            {latestTicket && (
              <details className="ticket-panel">
                <summary>
                  Заявка <b>{latestTicket.ticket_id}</b> создана
                </summary>
                <TicketCard ticket={latestTicket} />
              </details>
            )}

            <div className="composer">
              <div className="chips">
                {quickActions.map((action) => (
                  <button
                    key={action}
                    className="chip"
                    disabled={loading || !sessionId}
                    onClick={() => void send(action)}
                  >
                    {action}
                  </button>
                ))}
              </div>
              <div className="input-row">
                <textarea
                  ref={inputRef}
                  value={input}
                  rows={1}
                  placeholder="Спросите про неисправность…"
                  onChange={(event) => {
                    setInput(event.target.value)
                    resizeInput()
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault()
                      void send(input)
                    }
                  }}
                />
                <button
                  className="send"
                  aria-label="Отправить"
                  disabled={loading || !input.trim()}
                  onClick={() => void send(input)}
                >
                  →
                </button>
              </div>
            </div>
          </section>
        </main>
      ) : (
        <main className="fleet-main">
          <FleetDashboard
            fleet={fleet}
            onPick={(vehicleId) => {
              setSelectedId(vehicleId)
              setTab('mechanic')
            }}
          />
        </main>
      )}
    </div>
  )
}
