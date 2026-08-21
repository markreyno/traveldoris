import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { addTripMessage, createTripSession, getTripSession, startTripResearch } from './api/doris'
import type { ResearchOption, TripSession } from './types/session'
import './App.css'

const starter = 'I want to plan a trip next month to Japan and visit Disneyland. My budget is around $3,000.'
const SESSION_KEY = 'traveldoris.sessionId'

function OptionGroup({ title, options }: { title: string; options: ResearchOption[] }) {
  if (!options.length) return null
  return (
    <section className="option-group">
      <h3>{title}</h3>
      <div className="option-grid">
        {options.map((option) => (
          <article className="option-card" key={option.id}>
            <div><span>{option.provider}</span><strong>{option.score} match</strong></div>
            <h4>{option.title}</h4>
            <p>{option.details.join(' · ')}</p>
            <b>{option.currency} {option.price.toLocaleString()}</b>
          </article>
        ))}
      </div>
    </section>
  )
}

function App() {
  const [draft, setDraft] = useState(starter)
  const [session, setSession] = useState<TripSession | null>(null)
  const [acceptDeferred, setAcceptDeferred] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const sessionId = localStorage.getItem(SESSION_KEY)
    if (!sessionId) return
    getTripSession(sessionId)
      .then(setSession)
      .catch(() => localStorage.removeItem(SESSION_KEY))
  }, [])

  async function ensureSession(): Promise<TripSession> {
    if (session) return session
    const created = await createTripSession()
    localStorage.setItem(SESSION_KEY, created.id)
    setSession(created)
    return created
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || loading) return
    setLoading(true)
    setError('')
    try {
      const active = await ensureSession()
      const updated = await addTripMessage(active.id, content)
      setSession(updated)
      setDraft('')
      setAcceptDeferred(false)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  async function research() {
    if (!session || loading) return
    setLoading(true)
    setError('')
    try {
      setSession(await startTripResearch(session.id, acceptDeferred))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Research could not start.')
    } finally {
      setLoading(false)
    }
  }

  function newTrip() {
    localStorage.removeItem(SESSION_KEY)
    setSession(null)
    setDraft(starter)
    setAcceptDeferred(false)
    setError('')
  }

  const trip = session?.trip
  const intake = session?.intake
  const researchResult = session?.research
  const deferred = intake?.deferred_fields ?? []
  const ready = trip?.ready_to_search === true

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="TravelDoris home"><span className="brand-mark">D</span><span>TravelDoris</span></a>
        <div className="header-actions"><span className="phase">Trip planning · MVP</span><button className="quiet-button" onClick={newTrip}>New trip</button></div>
      </header>

      <section className="workspace">
        <div className="conversation">
          <div className="intro">
            <p className="eyebrow">Your thoughtful travel planner</p>
            <h1>{researchResult ? 'Your first trip options' : 'Where would you like to go?'}</h1>
            <p>{researchResult ? 'These are mock results for validating the planning flow before live providers are connected.' : 'Tell Doris what matters. She’ll organize the details and ask only what she needs.'}</p>
          </div>

          <div className="messages" aria-live="polite">
            {(session?.messages ?? []).map((message, index) => (
              <div className={`message ${message.role}`} key={`${message.role}-${index}`}><span>{message.role === 'assistant' ? 'Doris' : 'You'}</span><p>{message.content}</p></div>
            ))}
          </div>

          {!researchResult ? (
            <form className="composer" onSubmit={submit}>
              <textarea aria-label="Describe your trip" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="I’d like to visit…" rows={4} />
              <div className="composer-footer"><span>{error || 'Your session is saved automatically.'}</span><button type="submit" disabled={loading || !draft.trim()}>{loading ? 'Thinking…' : 'Ask Doris'}</button></div>
            </form>
          ) : null}

          {ready && !researchResult ? (
            <section className="confirmation-card">
              <p className="eyebrow">Ready for your approval</p>
              <h2>Research this trip brief?</h2>
              <p>Doris will use mock providers to compare flights, stays, and activities. No booking or external purchase will occur.</p>
              {deferred.length ? (
                <label><input type="checkbox" checked={acceptDeferred} onChange={(event) => setAcceptDeferred(event.target.checked)} />Use Doris’s flexible assumptions for {deferred.map((field) => field.replaceAll('.', ' ')).join(', ')}.</label>
              ) : null}
              <button onClick={research} disabled={loading || (deferred.length > 0 && !acceptDeferred)}>{loading ? 'Researching…' : 'Confirm and research'}</button>
              {error ? <p className="form-error">{error}</p> : null}
            </section>
          ) : null}

          {researchResult ? (
            <section className="research-results">
              <div className="research-summary"><div><span>Estimated package</span><strong>{researchResult.currency} {researchResult.estimated_total.toLocaleString()}</strong></div><p>{researchResult.summary}</p><em>{researchResult.budget_assessment.replaceAll('_', ' ')}</em></div>
              <OptionGroup title="Flights" options={researchResult.flights} />
              <OptionGroup title="Places to stay" options={researchResult.lodging} />
              <OptionGroup title="Things to do" options={researchResult.activities} />
            </section>
          ) : null}
        </div>

        <aside className="trip-card">
          <p className="eyebrow">Trip brief</p>
          <h2>{trip?.destinations.join(' → ') || 'Your trip takes shape here'}</h2>
          {!trip ? <p className="empty">Share your plans and Doris will turn them into a clear, searchable brief.</p> : (
            <>
              <div className="progress-label"><span>Planning details</span><strong>{intake?.completion_percentage ?? 0}%</strong></div>
              <div className="progress-track"><span style={{ width: `${intake?.completion_percentage ?? 0}%` }} /></div>
              <dl>
                <div><dt>From</dt><dd>{trip.origin || 'Flexible'}</dd></div>
                <div><dt>When</dt><dd>{trip.date.description || trip.date.start || 'Flexible'}</dd></div>
                <div><dt>Length</dt><dd>{trip.duration_days ? `${trip.duration_days} days` : 'Flexible'}</dd></div>
                <div><dt>Travelers</dt><dd>{trip.travelers.adults ?? 'Flexible'}</dd></div>
                <div><dt>Budget</dt><dd>{trip.budget.amount ? `${trip.budget.currency} ${trip.budget.amount.toLocaleString()}` : 'Flexible'}</dd></div>
                <div><dt>Status</dt><dd className={ready ? 'ready' : ''}>{researchResult ? 'Research complete' : ready ? 'Awaiting confirmation' : 'Gathering details'}</dd></div>
              </dl>
              {intake?.missing_fields.length ? <div className="missing-list"><h3>Still to confirm</h3>{intake.missing_fields.slice(0, 5).map((item) => <p key={item.field}><span className={item.priority} />{item.field.replaceAll('.', ' ')}</p>)}</div> : null}
              {deferred.length ? <div className="deferred-list"><h3>Doris will keep flexible</h3><p>{deferred.map((field) => field.replaceAll('.', ' ')).join(', ')}</p></div> : null}
            </>
          )}
          {trip?.must_visit.length ? <div className="tags">{trip.must_visit.map((item) => <span key={item}>{item}</span>)}</div> : null}
        </aside>
      </section>
    </main>
  )
}

export default App
