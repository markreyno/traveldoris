import type { ChatMessage, DorisParserResult, TripRequest } from './trip'

export interface ResearchOption {
  id: string
  category: 'flight' | 'lodging' | 'activity'
  title: string
  provider: string
  price: number
  currency: string
  score: number
  details: string[]
  is_mock: boolean
}

export interface ResearchResult {
  summary: string
  estimated_total: number
  currency: string
  budget_assessment: 'within_budget' | 'near_budget' | 'over_budget' | 'unknown'
  flights: ResearchOption[]
  lodging: ResearchOption[]
  activities: ResearchOption[]
  assumptions: string[]
  generated_at: string
  uses_mock_data: boolean
}

export interface TripSession {
  id: string
  created_at: string
  updated_at: string
  messages: ChatMessage[]
  trip: TripRequest | null
  intake: DorisParserResult | null
  research_confirmed: boolean
  deferred_fields_accepted: boolean
  research: ResearchResult | null
}
