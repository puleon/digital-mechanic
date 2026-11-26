export type SessionStatus = 'normal' | 'anomaly' | 'check_failed'

export interface Session {
  session_id: string
  vehicle_id: string
  checked_at: string
  status: SessionStatus
  anomaly_type: string | null
  anomaly_title: string | null
  anomaly_score: number | null
  confidence: number | null
  signal_quality: 'good' | 'warning' | 'bad'
  description: string
  model_version: string
}

export interface Vehicle {
  vehicle_id: string
  garage_no: string
  make: string
  model: string | null
  vehicle_type: string
  engine_model: string
  fuel: string
  session_id?: string | null
  checked_at?: string | null
  status?: SessionStatus | null
  anomaly_type?: string | null
  anomaly_score?: number | null
}

export interface Diagnosis {
  vehicle_id: string
  session_id: string
  status: SessionStatus
  anomaly_type: string | null
  anomaly_title: string | null
  anomaly_score: number | null
  confidence: number | null
  signal_quality: 'good' | 'warning' | 'bad'
  description: string
  model_version: string
}

export interface ToolCall {
  tool: string
  arguments: Record<string, unknown>
  result: unknown
  error: boolean
}

export interface ChatResponse {
  reply: string
  tool_calls: ToolCall[]
  vehicle_id: string
  session_id: string
  conversation_id: string
}

export interface Ticket {
  ticket_id: string
  vehicle_id: string
  session_id: string
  anomaly_type: string | null
  conclusion: string
  urgency: string
  operations: string[]
  spare_parts: string[]
  references: { manual: string; pdf_page: number }[]
  created_at: string
}

export interface VehicleCard {
  vehicle: Vehicle
  sessions: Session[]
  tickets: Ticket[]
}

export interface Fleet {
  total: number
  counts: { ok: number; attention: number; quarantine: number }
  buckets: {
    ok: Vehicle[]
    attention: Vehicle[]
    quarantine: Vehicle[]
  }
}
