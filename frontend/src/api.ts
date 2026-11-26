import type { ChatResponse, Fleet, Vehicle, VehicleCard } from './types'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const text = await response.text()
    let detail = text
    try {
      const parsed = JSON.parse(text) as { detail?: unknown }
      if (typeof parsed.detail === 'string') detail = parsed.detail
    } catch {
      // не JSON — показываем как есть
    }
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function getVehicles(): Promise<Vehicle[]> {
  const data = await request<{ vehicles: Vehicle[] }>('/api/vehicles')
  return data.vehicles
}

export async function getVehicleCard(vehicleId: string): Promise<VehicleCard> {
  return request<VehicleCard>(`/api/vehicles/${vehicleId}`)
}

export async function getFleet(): Promise<Fleet> {
  return request<Fleet>('/api/fleet')
}

export async function sendMessage(payload: {
  vehicle_id: string
  session_id: string
  message: string
  conversation_id: string
}): Promise<ChatResponse> {
  return request<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
