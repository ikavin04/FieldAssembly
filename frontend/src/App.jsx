import { useEffect, useMemo, useState } from 'react'
import VoiceTestPanel from './components/VoiceTestPanel'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', index: '01' },
  { href: '/equipment', label: 'Equipment', index: '02' },
  { href: '/tickets', label: 'Tickets', index: '03' },
  { href: '/alerts', label: 'Alerts', index: '04' },
  { href: '/reports/preview', label: 'Reports', index: '05' },
]

function App() {
  const currentLocation = () => `${window.location.pathname}${window.location.search}`
  const [path, setPath] = useState(currentLocation)
  const [equipment, setEquipment] = useState([])
  const [equipmentState, setEquipmentState] = useState('loading')
  const [backendState, setBackendState] = useState('checking')

  useEffect(() => {
    if (path === '/') return undefined
    fetch('/api/health')
      .then((response) => {
        if (!response.ok) throw new Error('Health request failed')
        setBackendState('connected')
      })
      .catch(() => setBackendState('unavailable'))
  }, [path])

  useEffect(() => {
    const onPopState = () => setPath(currentLocation())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    if (path === '/') return undefined
    fetch('/api/equipment')
      .then((response) => {
        if (!response.ok) throw new Error('Equipment request failed')
        return response.json()
      })
      .then((items) => {
        setEquipment(Array.isArray(items) ? items : [])
        setEquipmentState('ready')
      })
      .catch(() => setEquipmentState('unavailable'))
  }, [path])

  const navigate = (href) => {
    window.history.pushState({}, '', href)
    setPath(href)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const page = getPage(path)
  const activeHref = path === '/' ? '/' : `/${path.split('/')[1]}`

  return (
    <div className="app-shell">
      {page !== 'landing' && (
        <aside className="sidebar">
          <button className="brand-mark" onClick={() => navigate('/')} aria-label="FieldVoice home">
            <span className="brand-dot" />
            <span>fieldvoice</span>
          </button>
          <button className="primary-cta sidebar-cta" onClick={() => navigate('/equipment')}>+ <span>Start inspection</span></button>
          <nav className="main-nav" aria-label="Main navigation">
            {navItems.map((item) => (
              <button className={`nav-link ${activeHref === item.href || (item.href === '/reports/preview' && activeHref === '/reports') ? 'active' : ''}`} key={item.href} onClick={() => navigate(item.href)}>
                <span>{item.index}</span>{item.label}
              </button>
            ))}
          </nav>
          <div className="sidebar-footer"><div className="user-avatar">JM</div><div><strong>Jordan Mills</strong><small>Field technician</small></div><button className="icon-button" aria-label="Open account menu">•••</button></div>
        </aside>
      )}
      <main className={page === 'landing' ? 'landing-main' : 'main-content'}>
        {page !== 'landing' && <AppHeader path={path} backendState={backendState} />}
        {page === 'landing' && <LandingPage navigate={navigate} />}
        {page === 'dashboard' && <DashboardPage navigate={navigate} equipment={equipment} state={equipmentState} />}
        {page === 'equipment' && <EquipmentPage navigate={navigate} equipment={equipment} state={equipmentState} />}
        {page === 'inspection' && <InspectionPage navigate={navigate} equipment={equipment} path={path} />}
        {page === 'result' && <ResultPage navigate={navigate} path={path} equipment={equipment} />}
        {page === 'tickets' && <EmptyDataPage type="tickets" />}
        {page === 'alerts' && <EmptyDataPage type="alerts" />}
        {page === 'report' && <ReportPage navigate={navigate} />}
      </main>
    </div>
  )
}

function getPage(path) {
  if (path === '/') return 'landing'
  if (path === '/dashboard') return 'dashboard'
  if (path === '/equipment') return 'equipment'
  if (path.startsWith('/inspection/') && path.endsWith('/result')) return 'result'
  if (path.startsWith('/inspection/')) return 'inspection'
  if (path === '/tickets') return 'tickets'
  if (path === '/alerts') return 'alerts'
  if (path.startsWith('/reports/')) return 'report'
  return 'dashboard'
}

function AppHeader({ path, backendState }) {
  const labels = { dashboard: 'Dashboard', equipment: 'Equipment', inspection: 'Inspection', result: 'Inspection result', tickets: 'Tickets', alerts: 'Safety alerts', reports: 'Report' }
  const key = path.split('/')[1] || 'dashboard'
  const statusText = backendState === 'connected' ? 'Backend connected' : backendState === 'unavailable' ? 'Backend unavailable' : 'Checking backend'
  return <header className="topbar"><div><p className="eyebrow">Field operations / {labels[key] || 'FieldVoice'}</p><h1>{labels[key] || 'FieldVoice'}</h1></div><div className="topbar-actions"><span className={`system-status ${backendState}`}><i /> {statusText}</span><button className="round-button" aria-label="Notifications">!</button></div></header>
}

function LandingPage({ navigate }) {
  return <div className="landing-page">
    <header className="landing-nav"><button className="brand-mark" onClick={() => navigate('/')}><span className="brand-wave">∿</span><span>FieldVoice</span></button><nav><button onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}>How it works</button><button onClick={() => document.getElementById('for-technicians')?.scrollIntoView({ behavior: 'smooth' })}>For technicians</button><button onClick={() => navigate('/dashboard')}>Open workspace</button><button className="landing-login" onClick={() => navigate('/equipment')}>Start inspection <span>→</span></button></nav></header>
    <section className="hero-section"><div className="hero-copy"><p className="eyebrow lime">Hands-free inspection</p><h1>Equipment<br /><em>listens now.</em></h1><p className="hero-text">Hands-free AI inspection assistance for industrial technicians. Speak naturally about what you see and leave with a verified record.</p><div className="hero-actions"><button className="primary-cta" onClick={() => navigate('/equipment')}>Start inspection <span>→</span></button><button className="secondary-cta" onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}>See how it works</button></div><div className="hero-signoff">REAL WORK.<br />REAL VOICE.<br />REAL RESULTS.</div></div><div className="hero-photo"><div className="photo-wash" /><div className="inspection-card"><div className="inspection-card-header"><div><strong>Live inspection</strong><small>Air handler / field preview</small></div><span><i /> Listening</span></div><div className="mini-voice"><div className="mini-rings ring-one" /><div className="mini-rings ring-two" /><span>♩</span></div><p className="speak-label">Speak naturally...</p><div className="mini-checks"><div><b>✓</b><span>Temperature</span><small>—</small></div><div><b>○</b><span>Pressure</span><small>—</small></div><div><b>○</b><span>Vibration</span><small>—</small></div><div><b>○</b><span>Leakage</span><small>—</small></div></div></div></div></section>
    <section className="workflow-section" id="how-it-works"><div><p className="eyebrow">How it works</p><h2>One clear loop<br /><span>from machine to record.</span></h2></div><div className="workflow-steps">{['Select', 'Speak', 'Capture', 'Done'].map((step, index) => <div className="workflow-step" key={step}><span>0{index + 1}</span><strong>{step}</strong><small>{['Choose equipment', 'Describe what you see', 'AI structures the observation', 'Get a verified record'][index]}</small></div>)}</div></section>
    <section className="value-section" id="for-technicians"><div className="value-photo" /><div className="value-copy"><p className="eyebrow">FieldVoice</p><h2>Less typing.<br /><span>More doing.</span></h2><div className="benefits"><div><b>01</b><strong>Simple workflow</strong><p>Stay focused on the equipment, not a form.</p></div><div><b>02</b><strong>Safer field work</strong><p>Keep your hands where the work is.</p></div><div><b>03</b><strong>More time in the field</strong><p>Capture the record while it is fresh.</p></div></div><button className="text-link" onClick={() => navigate('/equipment')}>See how it works <span>→</span></button></div></section>
    <section className="final-cta"><p className="eyebrow">The next inspection starts here</p><h2>Ready to inspect?</h2><button className="primary-cta" onClick={() => navigate('/equipment')}>Start inspection <span>→</span></button></section>
    <footer className="landing-footer"><span>FieldVoice</span><span>Talk while you work.</span><span>© 2026</span></footer>
  </div>
}

function DashboardPage({ navigate, equipment, state }) {
  return <div className="page-body"><section className="welcome-row"><div><p className="eyebrow">Tuesday, September 18, 2026</p><h2>Good morning, Jordan.</h2><p className="muted">Your field workspace, ready when you are.</p></div><button className="primary-cta" onClick={() => navigate('/equipment')}>Start voice inspection ↗</button></section><section className="stats-grid"><Stat label="Registered equipment" value={state === 'ready' ? equipment.length : '—'} note={state === 'unavailable' ? 'Backend unavailable' : 'From live equipment data'} color="blue" /><Stat label="Inspections" value="—" note="No inspection endpoint yet" color="amber" /><Stat label="Open tickets" value="—" note="No ticket records yet" color="green" /><Stat label="Safety alerts" value="—" note="No alert records yet" color="red" /></section><section className="dashboard-grid"><div className="section-block"><div className="section-heading"><div><p className="eyebrow">Next action</p><h2>Choose your equipment</h2></div><button className="text-button" onClick={() => navigate('/equipment')}>View catalog →</button></div><div className="dashboard-action"><div className="action-icon">◌</div><div><h3>Begin a hands-free inspection</h3><p>Select an asset from the live catalog, then let FieldVoice guide the conversation.</p></div><button className="round-button light" onClick={() => navigate('/equipment')} aria-label="Open equipment catalog">→</button></div></div><div className="section-block"><div className="section-heading"><div><p className="eyebrow">Activity</p><h2>Recent inspections</h2></div></div><EmptyState title="No inspections yet" text="Completed inspections will appear here once the backend is connected." /></div></section></div>
}

function Stat({ label, value, note, color }) { return <article className={`stat-card accent-${color}`}><span className="stat-label">{label}</span><strong>{value}</strong><span className="stat-note">{note}</span></article> }

function EquipmentPage({ navigate, equipment, state }) {
  const [query, setQuery] = useState('')
  const [type, setType] = useState('all')
  const types = [...new Set(equipment.map((item) => item.equipment_type).filter(Boolean))]
  const filtered = useMemo(() => equipment.filter((item) => `${item.asset_code} ${item.name} ${item.location}`.toLowerCase().includes(query.toLowerCase()) && (type === 'all' || item.equipment_type === type)), [equipment, query, type])
  return <div className="page-body"><section className="page-intro"><div><p className="eyebrow">Live asset catalog</p><h2>Find equipment to inspect.</h2><p className="muted">Choose an asset and FieldVoice will carry the conversation from there.</p></div><span className="record-count">{state === 'ready' ? `${equipment.length} assets` : '— assets'}</span></section><div className="catalog-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search asset code, name, or location" aria-label="Search equipment" /><select value={type} onChange={(event) => setType(event.target.value)} aria-label="Filter by equipment type"><option value="all">All equipment types</option>{types.map((item) => <option key={item} value={item}>{item}</option>)}</select></div>{state === 'loading' && <LoadingState text="Loading equipment from the backend..." />}{state === 'unavailable' && <EmptyState title="Equipment unavailable" text="The live equipment endpoint could not be reached. Check that the backend and database are running." />}{state === 'ready' && filtered.length === 0 && <EmptyState title={equipment.length ? 'No matching equipment' : 'No equipment registered'} text={equipment.length ? 'Try a different search or filter.' : 'Equipment added in the backend will appear here.'} />}{state === 'ready' && filtered.length > 0 && <div className="equipment-grid">{filtered.map((item) => <EquipmentCard key={item.id} item={item} navigate={navigate} />)}</div>}</div>
}

function EquipmentCard({ item, navigate }) { const checkpoints = Array.isArray(item.required_inspection_fields) ? item.required_inspection_fields.length : 0; return <article className="equipment-card"><div className="card-kicker"><span>{item.asset_code}</span><span className="type-tag">{item.equipment_type}</span></div><h3>{item.name}</h3><p className="muted">{item.location || 'Location not provided'}</p><div className="card-divider" /><div className="equipment-meta"><span>{checkpoints} required checkpoints</span><button className="text-button" onClick={() => navigate(`/inspection/new?equipment=${item.id}`)}>Inspect ↗</button></div><details><summary>View details</summary><div className="details-copy"><p>{item.description || 'No description provided.'}</p><strong>Operating limits</strong><code>{JSON.stringify(item.operating_limits || {})}</code></div></details></article> }

function InspectionPage({ navigate, equipment, path }) {
  const params = new URLSearchParams(path.split('?')[1] || '')
  const routeId = path.split('/')[2]?.split('?')[0]
  const selected = equipment.find((item) => String(item.id) === params.get('equipment'))
  const [activeInspectionId, setActiveInspectionId] = useState(routeId && routeId !== 'new' ? Number(routeId) : null)
  const [inspectionState, setInspectionState] = useState(routeId === 'new' ? 'creating' : 'ready')
  const [inspectionData, setInspectionData] = useState(null)
  const [isCompleting, setIsCompleting] = useState(false)
  const [completionError, setCompletionError] = useState(null)

  useEffect(() => {
    if (routeId !== 'new' || !selected || activeInspectionId) return
    let cancelled = false
    fetch('/api/inspections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ equipment_id: selected.id, inspection_type: 'routine' }),
    })
      .then((response) => {
        if (!response.ok) throw new Error('Unable to create inspection')
        return response.json()
      })
      .then((payload) => {
        if (cancelled) return
        setActiveInspectionId(payload.inspection_id)
        setInspectionState('ready')
        window.history.replaceState({}, '', `/inspection/${payload.inspection_id}?equipment=${selected.id}`)
      })
      .catch(() => {
        if (!cancelled) setInspectionState('error')
      })
    return () => { cancelled = true }
  }, [routeId, selected, activeInspectionId])

  // Poll GET /api/inspections/:id to keep checklist synchronized with PostgreSQL
  useEffect(() => {
    if (!activeInspectionId) return undefined
    let isMounted = true

    const fetchInspection = async () => {
      try {
        const res = await fetch(`/api/inspections/${activeInspectionId}`)
        if (!res.ok) return
        const data = await res.json()
        if (isMounted) {
          setInspectionData(data)
        }
      } catch {
        // network error handled gracefully
      }
    }

    fetchInspection()
    const interval = setInterval(() => {
      if (inspectionData?.status !== 'completed') {
        fetchInspection()
      }
    }, 3000)

    return () => {
      isMounted = false
      clearInterval(interval)
    }
  }, [activeInspectionId, inspectionData?.status])

  const handleCompleteInspection = async () => {
    if (!activeInspectionId || isCompleting) return
    setIsCompleting(true)
    setCompletionError(null)
    try {
      const res = await fetch(`/api/inspections/${activeInspectionId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || `Completion failed (${res.status})`)
      }
      const payload = await res.json()
      setInspectionData(payload.inspection)
      navigate(`/inspection/${activeInspectionId}/result`)
    } catch (err) {
      setCompletionError(err.message)
    } finally {
      setIsCompleting(false)
    }
  }

  // Derive checklist items: prefer inspectionData.required_fields from backend, fallback to equipment fields
  const checklistFields = inspectionData?.required_fields || selected?.required_inspection_fields || []
  const completedFields = inspectionData?.completed_fields || []

  const statusText = inspectionState === 'creating' ? 'Creating inspection' : inspectionState === 'error' ? 'Inspection unavailable' : activeInspectionId ? `Inspection #${activeInspectionId}` : 'Select an equipment asset'

  return (
    <div className="page-body inspection-page">
      <div className="inspection-context">
        <div>
          <p className="eyebrow">Inspection workspace / {selected?.asset_code || 'new session'}</p>
          <h2>{selected?.name || 'Select an equipment asset'}</h2>
          <p className="muted">{selected?.location || 'Equipment context will be attached when you start from the catalog.'}</p>
        </div>
        <span className="status-badge">{statusText}</span>
      </div>
      <div className="inspection-layout">
        <div>
          <VoiceTestPanel inspectionId={activeInspectionId} equipment={selected} />
          <button
            className="complete-button"
            disabled={isCompleting || !activeInspectionId}
            onClick={handleCompleteInspection}
          >
            {isCompleting ? 'Completing inspection...' : 'Complete inspection →'}
          </button>
          {completionError && (
            <p style={{ color: '#e48670', fontSize: '11px', marginTop: '6px', fontFamily: "'DM Mono', monospace" }}>
              {completionError}
            </p>
          )}
        </div>
        <aside className="checklist-panel">
          <p className="eyebrow">Required fields</p>
          <h3>Inspection checklist</h3>
          {checklistFields.map((field) => {
            const fieldName = typeof field === 'string' ? field : field.name || field.field_name || 'Required observation'
            const isCompleted = completedFields.includes(fieldName)
            const fieldValidation = inspectionData?.validation?.[fieldName]
            const validationStatus = fieldValidation?.status
            return (
              <div className="checklist-item" key={fieldName}>
                <span style={{ color: isCompleted ? '#2f6558' : '#738071', fontWeight: isCompleted ? 700 : 400 }}>
                  {isCompleted ? '✓' : '○'}
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <span style={{ color: isCompleted ? '#111827' : '#738071', fontWeight: isCompleted ? 600 : 400 }}>
                    {fieldName}
                  </span>
                  {isCompleted && fieldValidation && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {fieldValidation.value != null && (
                        <span style={{ fontFamily: "'DM Mono', monospace", fontSize: '10px', color: '#7a8490' }}>
                          {fieldValidation.value}{fieldValidation.unit ? ` ${fieldValidation.unit}` : ''}
                        </span>
                      )}
                      <span style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        color: validationStatus === 'normal' ? '#2f6558'
                          : validationStatus === 'out_of_range' ? '#b45309'
                          : '#7a8490',
                        textTransform: 'capitalize',
                      }}>
                        {validationStatus === 'out_of_range' ? '⚠ Out of range' : validationStatus === 'normal' ? 'Normal' : 'Unknown'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
          {!selected && !activeInspectionId && (
            <EmptyState title="Waiting for equipment" text="Start from Equipment to load the backend-defined checkpoints." />
          )}
        </aside>
      </div>
    </div>
  )
}

function ResultPage({ navigate, path, equipment }) {
  const routeId = path.split('/')[2]?.split('?')[0]
  const inspectionId = routeId && routeId !== 'new' ? Number(routeId) : null
  const [inspection, setInspection] = useState(null)
  const [observations, setObservations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!inspectionId) {
      setLoading(false)
      setError('No inspection ID provided')
      return
    }

    let isMounted = true
    setLoading(true)
    setError(null)

    Promise.all([
      fetch(`/api/inspections/${inspectionId}`).then((r) => {
        if (!r.ok) throw new Error(`Inspection #${inspectionId} not found`)
        return r.json()
      }),
      fetch(`/api/inspections/${inspectionId}/observations`).then((r) => {
        if (!r.ok) return []
        return r.json()
      }),
    ])
      .then(([insData, obsData]) => {
        if (!isMounted) return
        setInspection(insData)
        setObservations(Array.isArray(obsData) ? obsData : [])
      })
      .catch((err) => {
        if (!isMounted) return
        setError(err.message)
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => { isMounted = false }
  }, [inspectionId])

  const selectedEquipment = equipment.find((e) => e.id === inspection?.equipment_id)

  if (loading) {
    return (
      <div className="page-body">
        <LoadingState text="Loading inspection record..." />
      </div>
    )
  }

  if (error || !inspection) {
    return (
      <div className="page-body">
        <EmptyState title="Inspection not found" text={error || `Could not load inspection #${inspectionId}`} />
        <button className="secondary-cta" style={{ marginTop: '20px' }} onClick={() => navigate('/equipment')}>
          Return to equipment catalog
        </button>
      </div>
    )
  }

  const isCompleted = inspection.status === 'completed'
  const validationSummary = inspection.validation || {}

  return (
    <div className="page-body">
      <section className="result-banner">
        <div>
          <span className="success-mark">✓</span>
          <div>
            <p className="eyebrow">Inspection {isCompleted ? 'Complete' : 'In Progress'} / #{inspection.id}</p>
            <h2>{isCompleted ? 'Your record is verified and saved.' : 'Active inspection session.'}</h2>
            <p className="muted">
              {selectedEquipment ? `${selectedEquipment.asset_code} — ${selectedEquipment.name}` : `Asset #${inspection.equipment_id}`}
              {selectedEquipment?.location ? ` • ${selectedEquipment.location}` : ''}
              {inspection.completed_at ? ` • Completed: ${new Date(inspection.completed_at).toLocaleString()}` : ''}
            </p>
          </div>
        </div>
        <button className="primary-cta" onClick={() => navigate('/equipment')}>
          Start another inspection ↗
        </button>
      </section>

      {inspection.summary && (
        <section style={{ margin: '20px 0', padding: '16px 20px', background: '#fff', border: '1px solid #e4e1d9', borderRadius: '14px' }}>
          <p className="eyebrow">Summary</p>
          <p style={{ margin: 0, color: '#111827', fontSize: '13px', lineHeight: 1.6 }}>{inspection.summary}</p>
        </section>
      )}

      <div className="result-grid" style={{ marginTop: '24px' }}>
        {/* Observations Block */}
        <div className="section-block">
          <div className="section-heading">
            <h2>Recorded Observations</h2>
            <span className={`status-badge ${isCompleted ? '' : 'neutral'}`}>
              {observations.length} {observations.length === 1 ? 'record' : 'records'}
            </span>
          </div>
          {observations.length > 0 ? (
            <div style={{ display: 'grid', gap: '12px' }}>
              {observations.map((obs) => {
                const vResult = validationSummary[obs.field_name]
                const vStatus = vResult?.status
                return (
                  <div
                    key={obs.id}
                    style={{
                      padding: '16px',
                      border: vStatus === 'out_of_range' ? '1px solid #d97706' : '1px solid #e4e1d9',
                      borderRadius: '12px',
                      background: vStatus === 'out_of_range' ? '#fffbeb' : '#fff',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <strong style={{ fontSize: '13px', color: '#111827', textTransform: 'capitalize' }}>
                        {obs.field_name}
                      </strong>
                      <span style={{ fontFamily: "'DM Mono', monospace", fontSize: '12px', color: '#2f6558', fontWeight: 600 }}>
                        {obs.value} {obs.unit || ''}
                      </span>
                    </div>
                    {vResult && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          color: vStatus === 'normal' ? '#2f6558' : vStatus === 'out_of_range' ? '#b45309' : '#7a8490',
                        }}>
                          {vStatus === 'out_of_range' ? '⚠ Out of range' : vStatus === 'normal' ? '✓ Normal' : 'Unknown'}
                        </span>
                        {vResult.limit && (
                          <span style={{ fontSize: '10px', color: '#7a8490', fontFamily: "'DM Mono', monospace" }}>
                            Range: {vResult.limit.min}–{vResult.limit.max}
                          </span>
                        )}
                      </div>
                    )}
                    {obs.evidence_text && (
                      <p style={{ margin: '6px 0 0', fontSize: '11px', color: '#7a8490', fontStyle: 'italic' }}>
                        Spoken evidence: &quot;{obs.evidence_text}&quot;
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <EmptyState
              title="No observations captured"
              text="No observations were recorded for this inspection in PostgreSQL."
            />
          )}
        </div>

        {/* Evidence Timeline */}
        <div className="section-block">
          <div className="section-heading">
            <h2>Evidence Timeline</h2>
            <span className="status-badge">
              Spoken Quotes
            </span>
          </div>
          {observations.filter((o) => o.evidence_text).length > 0 ? (
            <div style={{ display: 'grid', gap: '12px' }}>
              {observations.filter((o) => o.evidence_text).map((obs) => (
                <div
                  key={`evidence-${obs.id}`}
                  style={{
                    padding: '14px',
                    border: '1px solid #e4e1d9',
                    borderRadius: '12px',
                    background: '#fff',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#7a8490', fontFamily: "'DM Mono', monospace", marginBottom: '4px' }}>
                    <span style={{ textTransform: 'uppercase' }}>{obs.field_name}</span>
                    <span>Observation #{obs.id}</span>
                  </div>
                  <blockquote style={{ margin: 0, color: '#111827', fontSize: '12px', lineHeight: 1.5 }}>
                    "{obs.evidence_text}"
                  </blockquote>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No evidence yet"
              text="Spoken statements stored in PostgreSQL will appear here."
            />
          )}
        </div>
      </div>

      <div style={{ marginTop: '32px' }}>
        <button className="secondary-cta" onClick={() => navigate('/equipment')}>
          ← Back to equipment catalog
        </button>
      </div>
    </div>
  )
}

function EmptyDataPage({ type }) { const isAlert = type === 'alerts'; return <div className="page-body"><section className="page-intro"><div><p className="eyebrow">{isAlert ? 'Safety events' : 'Maintenance actions'}</p><h2>{isAlert ? 'Safety alerts' : 'Maintenance tickets'}</h2><p className="muted">{isAlert ? 'Conditions detected during inspections, with evidence attached.' : 'Actions created from inspection findings.'}</p></div><span className="record-count">— records</span></section><div className="filter-row"><button className="filter-chip active">All</button><button className="filter-chip">Open</button><button className="filter-chip">Resolved</button></div><EmptyState title={isAlert ? 'No safety alerts yet.' : 'No maintenance tickets yet.'} text="Records created by the backend will appear here. The frontend does not manufacture operational data." /></div> }

function ReportPage({ navigate }) { return <div className="page-body report-page"><div className="report-actions"><span className="status-badge neutral">Preview / no report loaded</span><div><button className="secondary-cta" onClick={() => window.print()}>Print / Save as PDF</button><button className="primary-cta" onClick={() => navigate('/equipment')}>New inspection ↗</button></div></div><article className="report-sheet"><p className="eyebrow">FieldVoice inspection report</p><h2>No report selected</h2><p className="muted">A formal report will appear here once an inspection has been completed and the report endpoint is available.</p><div className="report-rule" /><div className="report-placeholder"><span>◌</span><strong>Report content is waiting for backend data</strong></div></article></div> }

function EmptyState({ title, text }) { return <div className="empty-state"><span className="empty-icon">○</span><h3>{title}</h3><p>{text}</p></div> }
function LoadingState({ text }) { return <div className="empty-state"><span className="loading-line" /><h3>Loading</h3><p>{text}</p></div> }

export default App
