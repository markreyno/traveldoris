export type PlanningStatus = 'collecting_basics' | 'collecting_logistics' | 'collecting_preferences' | 'ready_for_research' | 'ready_for_itinerary'

export interface DateRequirements {
  type: 'exact' | 'flexible' | 'unknown'
  start: string | null
  end: string | null
  description: string | null
}

export interface TripRequest {
  trip_type: string
  destinations: string[]
  origin: string | null
  date: DateRequirements
  duration_days: number | null
  budget: { amount: number | null; currency: string; scope: 'total' | 'per_person' | 'on_ground' | null; flexible: boolean | null; includes: string[] }
  travelers: { adults: number | null; children: number | null; child_ages: number[] }
  must_visit: string[]
  preferences: string[]
  pace: 'relaxed' | 'balanced' | 'busy' | null
  transportation: { flight: boolean | null; rental_car: boolean | null; public_transit: boolean | null; driving: boolean | null }
  lodging: { needed: boolean | null; type: string | null; rooms: number | null }
  constraints: { accessibility: string[]; dietary: string[]; mobility: string[]; max_driving_hours_per_day: number | null; notes: string[] }
  needs: Record<string, boolean | null>
  field_resolutions: Array<{
    field: string
    status: 'provided' | 'user_unsure' | 'declined' | 'not_applicable' | 'use_recommended_default'
    note: string | null
  }>
  planning_status: PlanningStatus
  ready_to_search: boolean
}

export interface MissingField {
  field: string
  section: 'basics' | 'logistics' | 'preferences'
  priority: 'required' | 'recommended'
  reason: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface DorisParserResult {
  trip: TripRequest
  status: PlanningStatus
  clarification_question: string | null
  next_questions: string[]
  missing_fields: MissingField[]
  deferred_fields: string[]
  completion_percentage: number
}
