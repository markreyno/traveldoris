import type { ChatMessage, DorisParserResult, TripRequest } from '../types/trip'
import type { TripSession } from '../types/session'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(payload?.detail ?? 'Doris could not complete that request.')
  }
  return response.json() as Promise<T>
}

export function createTripSession(): Promise<TripSession> {
  return request('/api/trips', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
}

export function getTripSession(sessionId: string): Promise<TripSession> {
  return request(`/api/trips/${sessionId}`)
}

export function addTripMessage(sessionId: string, message: string): Promise<TripSession> {
  return request(`/api/trips/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
}

export function startTripResearch(sessionId: string, acceptDeferredFields: boolean): Promise<TripSession> {
  return request(`/api/trips/${sessionId}/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmed: true, accept_deferred_fields: acceptDeferredFields }),
  })
}

export async function sendMessageToDoris(
  messages: ChatMessage[],
  currentTrip: TripRequest | null,
): Promise<DorisParserResult> {
  const response = await fetch('/api/trip/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, current_trip: currentTrip }),
  })

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(payload?.detail ?? 'Doris could not understand that request.')
  }

  return response.json() as Promise<DorisParserResult>
}
