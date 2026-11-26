import type { Ticket } from '../types'

export function TicketCard({ ticket }: { ticket: Ticket }) {
  return (
    <section className="ticket-card">
      <div className="ticket-head">
        <span className="ticket-id">{ticket.ticket_id}</span>
        <span className="muted small">срочность: {ticket.urgency}</span>
      </div>
      <p className="ticket-conclusion">{ticket.conclusion}</p>
      <div className="ticket-grid">
        <div>
          <span className="muted small">Работы</span>
          <b>{ticket.operations.length}</b>
        </div>
        <div>
          <span className="muted small">Запчасти</span>
          <b>{ticket.spare_parts.length}</b>
        </div>
        <div>
          <span className="muted small">Источники</span>
          <b>{ticket.references.length}</b>
        </div>
      </div>
      <div className="ticket-refs">
        {ticket.references.slice(0, 3).map((ref, index) => (
          <span key={index} className="chip">
            {ref.manual}, стр. {ref.pdf_page}
          </span>
        ))}
        {ticket.references.length > 3 && (
          <span className="chip">ещё {ticket.references.length - 3}</span>
        )}
      </div>
    </section>
  )
}
