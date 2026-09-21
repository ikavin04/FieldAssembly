import { useEffect, useMemo, useState } from 'react'
import VoiceTestPanel from './components/VoiceTestPanel'
import { getInspectionReport, getMaintenanceTickets, getSafetyAlerts } from './services/api'

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

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
    const onPopState = () => {
      setPath(currentLocation())
      setMobileMenuOpen(false)
    }
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
    setMobileMenuOpen(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const page = getPage(path)
  const activeHref = path === '/' ? '/' : `/${path.split('/')[1]}`

  return (
    <div className="app-shell">
      {page !== 'landing' && (
        <>
          <div
            className={`mobile-backdrop ${mobileMenuOpen ? 'open' : ''}`}
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          <aside className={`sidebar ${mobileMenuOpen ? 'mobile-open' : ''}`}>
            <div className="sidebar-header">
              <button className="brand-mark" onClick={() => navigate('/')} aria-label="FieldVoice home">
                <span className="brand-dot" />
                <span>fieldvoice</span>
              </button>
              <button
                className="mobile-sidebar-close"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close navigation menu"
              >
                ✕
              </button>
            </div>
            <button className="primary-cta sidebar-cta" onClick={() => navigate('/equipment')}>+ <span>Start inspection</span></button>
            <nav className="main-nav" aria-label="Main navigation">
              {navItems.map((item) => (
                <button
                  className={`nav-link ${activeHref === item.href || (item.href === '/reports/preview' && activeHref === '/reports') ? 'active' : ''}`}
                  key={item.href}
                  onClick={() => navigate(item.href)}
                >
                  <span>{item.index}</span>{item.label}
                </button>
              ))}
            </nav>
            <div className="sidebar-footer">
              <div className="user-avatar">JM</div>
              <div><strong>Jordan Mills</strong><small>Field technician</small></div>
              <button className="icon-button" aria-label="Open account menu">•••</button>
            </div>
          </aside>
        </>
      )}
      <main className={page === 'landing' ? 'landing-main' : 'main-content'}>
        {page !== 'landing' && (
          <AppHeader
            path={path}
            backendState={backendState}
            mobileMenuOpen={mobileMenuOpen}
            onToggleMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
          />
        )}
        {page === 'landing' && <LandingPage navigate={navigate} />}
        {page === 'dashboard' && <DashboardPage navigate={navigate} equipment={equipment} state={equipmentState} />}
        {page === 'equipment' && <EquipmentPage navigate={navigate} equipment={equipment} state={equipmentState} />}
        {page === 'inspection' && <InspectionPage navigate={navigate} equipment={equipment} path={path} />}
        {page === 'result' && <ResultPage navigate={navigate} path={path} equipment={equipment} />}
        {page === 'tickets' && <TicketsPage navigate={navigate} />}
        {page === 'alerts' && <AlertsPage navigate={navigate} />}
        {page === 'report' && <ReportPage navigate={navigate} path={path} />}
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
  if (path === '/reports' || path.startsWith('/reports/')) return 'report'
  return 'dashboard'
}

function AppHeader({ path, backendState, mobileMenuOpen, onToggleMenu }) {
  const labels = { dashboard: 'Dashboard', equipment: 'Equipment', inspection: 'Inspection', result: 'Inspection result', tickets: 'Tickets', alerts: 'Safety alerts', reports: 'Report' }
  const key = path.split('/')[1] || 'dashboard'
  const statusText = backendState === 'connected' ? 'Backend connected' : backendState === 'unavailable' ? 'Backend unavailable' : 'Checking backend'
  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          className="mobile-menu-toggle"
          onClick={onToggleMenu}
          aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? '✕' : '☰'}
        </button>
        <div>
          <p className="eyebrow">Field operations / {labels[key] || 'FieldVoice'}</p>
          <h1>{labels[key] || 'FieldVoice'}</h1>
        </div>
      </div>
      <div className="topbar-actions">
        <span className={`system-status ${backendState}`}><i /> {statusText}</span>
        <button className="round-button" aria-label="Notifications">!</button>
      </div>
    </header>
  )
}

function LandingPage({ navigate }) {
  const [landingMenuOpen, setLandingMenuOpen] = useState(false)

  const handleNav = (href) => {
    setLandingMenuOpen(false)
    navigate(href)
  }

  const handleScrollTo = (id) => {
    setLandingMenuOpen(false)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="landing-page">
      <header className="landing-nav">
        <button className="brand-mark" onClick={() => handleNav('/')}>
          <span className="brand-wave">∿</span>
          <span>FieldVoice</span>
        </button>
        <button
          className="mobile-menu-toggle landing-toggle"
          onClick={() => setLandingMenuOpen(!landingMenuOpen)}
          aria-label={landingMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={landingMenuOpen}
        >
          {landingMenuOpen ? '✕' : '☰'}
        </button>
        <nav className={`landing-nav-links ${landingMenuOpen ? 'mobile-open' : ''}`}>
          <button onClick={() => handleScrollTo('how-it-works')}>How it works</button>
          <button onClick={() => handleScrollTo('for-technicians')}>For technicians</button>
          <button onClick={() => handleNav('/dashboard')}>Open workspace</button>
          <button className="landing-login" onClick={() => handleNav('/equipment')}>Start inspection <span>→</span></button>
        </nav>
      </header>
      <section className="hero-section">
        <div className="hero-copy">
          <p className="eyebrow lime">Hands-free inspection</p>
          <h1>Equipment<br /><em>listens now.</em></h1>
          <p className="hero-text">
            Hands-free AI inspection assistance for industrial technicians. Speak naturally about what you see and leave with a verified record.
          </p>
          <div className="hero-actions">
            <button className="primary-cta" onClick={() => handleNav('/equipment')}>
              Start inspection <span>→</span>
            </button>
            <button className="secondary-cta" onClick={() => handleScrollTo('how-it-works')}>
              See how it works
            </button>
          </div>
          <div className="hero-signoff">
            REAL WORK.<br />REAL VOICE.<br />REAL RESULTS.
          </div>
        </div>
        <div className="hero-photo">
          <div className="photo-wash" />
          <div className="inspection-card">
            <div className="inspection-card-header">
              <div>
                <strong>Live inspection</strong>
                <small>Air handler / field preview</small>
              </div>
              <span><i /> Listening</span>
            </div>
            <div className="mini-voice">
              <div className="mini-rings ring-one" />
              <div className="mini-rings ring-two" />
              <span>♩</span>
            </div>
            <p className="speak-label">Speak naturally...</p>
            <div className="mini-checks">
              <div><b>✓</b><span>Temperature</span><small>—</small></div>
              <div><b>○</b><span>Pressure</span><small>—</small></div>
              <div><b>○</b><span>Vibration</span><small>—</small></div>
              <div><b>○</b><span>Leakage</span><small>—</small></div>
            </div>
          </div>
        </div>
      </section>

      <section className="workflow-section" id="how-it-works">
        <div>
          <p className="eyebrow">How it works</p>
          <h2>One clear loop<br /><span>from machine to record.</span></h2>
        </div>
        <div className="workflow-steps">
          {['Select', 'Speak', 'Capture', 'Done'].map((step, index) => (
            <div className="workflow-step" key={step}>
              <span>0{index + 1}</span>
              <strong>{step}</strong>
              <small>
                {[
                  'Choose equipment',
                  'Describe what you see',
                  'AI structures the observation',
                  'Get a verified record',
                ][index]}
              </small>
            </div>
          ))}
        </div>
      </section>

      <section className="value-section" id="for-technicians">
        <div className="value-photo" />
        <div className="value-copy">
          <p className="eyebrow">FieldVoice</p>
          <h2>Less typing.<br /><span>More doing.</span></h2>
          <div className="benefits">
            <div>
              <b>01</b>
              <strong>Simple workflow</strong>
              <p>Stay focused on the equipment, not a form.</p>
            </div>
            <div>
              <b>02</b>
              <strong>Safer field work</strong>
              <p>Keep your hands where the work is.</p>
            </div>
            <div>
              <b>03</b>
              <strong>More time in the field</strong>
              <p>Capture the record while it is fresh.</p>
            </div>
          </div>
          <button className="text-link" onClick={() => handleNav('/equipment')}>
            See how it works <span>→</span>
          </button>
        </div>
      </section>

      <section className="final-cta">
        <p className="eyebrow">The next inspection starts here</p>
        <h2>Ready to inspect?</h2>
        <button className="primary-cta" onClick={() => handleNav('/equipment')}>
          Start inspection <span>→</span>
        </button>
      </section>

      <footer className="landing-footer">
        <span>FieldVoice</span>
        <span>Talk while you work.</span>
        <span>© 2026</span>
      </footer>
    </div>
  )
}

function DashboardPage({ navigate, equipment, state }) {
  const [openTicketCount, setOpenTicketCount] = useState(null)
  const [openAlertCount, setOpenAlertCount] = useState(null)

  useEffect(() => {
    getMaintenanceTickets({ status: 'open' })
      .then((tix) => setOpenTicketCount(Array.isArray(tix) ? tix.length : 0))
      .catch(() => setOpenTicketCount('—'))
    getSafetyAlerts({ status: 'open' })
      .then((alr) => setOpenAlertCount(Array.isArray(alr) ? alr.length : 0))
      .catch(() => setOpenAlertCount('—'))
  }, [])

  return (
    <div className="page-body">
      <section className="welcome-row">
        <div>
          <p className="eyebrow">Tuesday, September 18, 2026</p>
          <h2>Good morning, Jordan.</h2>
          <p className="muted">Your field workspace, ready when you are.</p>
        </div>
        <button className="primary-cta" onClick={() => navigate('/equipment')}>Start voice inspection ↗</button>
      </section>
      <section className="stats-grid">
        <Stat label="Registered equipment" value={state === 'ready' ? equipment.length : '—'} note={state === 'unavailable' ? 'Backend unavailable' : 'From live equipment data'} color="blue" />
        <Stat label="Inspections" value="—" note="From live inspection sessions" color="amber" />
        <Stat label="Open tickets" value={openTicketCount !== null ? openTicketCount : '...'} note="From live ticket records" color="green" />
        <Stat label="Safety alerts" value={openAlertCount !== null ? openAlertCount : '...'} note="From live alert records" color="red" />
      </section>
      <section className="dashboard-grid">
        <div className="section-block">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Next action</p>
              <h2>Choose your equipment</h2>
            </div>
            <button className="text-button" onClick={() => navigate('/equipment')}>View catalog →</button>
          </div>
          <div className="dashboard-action">
            <div className="action-icon">◌</div>
            <div>
              <h3>Begin a hands-free inspection</h3>
              <p>Select an asset from the live catalog, then let FieldVoice guide the conversation.</p>
            </div>
            <button className="round-button light" onClick={() => navigate('/equipment')} aria-label="Open equipment catalog">→</button>
          </div>
        </div>
        <div className="section-block">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Activity</p>
              <h2>Recent inspections</h2>
            </div>
          </div>
          <EmptyState title="No inspections yet" text="Completed inspections will appear here once the backend is connected." />
        </div>
      </section>
    </div>
  )
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
  const [tickets, setTickets] = useState([])
  const [alerts, setAlerts] = useState([])
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
      fetch(`/api/inspections/${inspectionId}/tickets`).then((r) => {
        if (!r.ok) return []
        return r.json()
      }),
      fetch(`/api/inspections/${inspectionId}/alerts`).then((r) => {
        if (!r.ok) return []
        return r.json()
      }),
    ])
      .then(([insData, obsData, tixData, alrData]) => {
        if (!isMounted) return
        setInspection(insData)
        setObservations(Array.isArray(obsData) ? obsData : [])
        setTickets(Array.isArray(tixData) ? tixData : [])
        setAlerts(Array.isArray(alrData) ? alrData : [])
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
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="secondary-cta" onClick={() => navigate(`/reports/${inspection.id}`)}>
            View full report →
          </button>
          <button className="primary-cta" onClick={() => navigate('/equipment')}>
            Start another inspection ↗
          </button>
        </div>
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

        {/* Maintenance Tickets */}
        <div className="section-block">
          <div className="section-heading">
            <h2>Maintenance Tickets</h2>
            <span className={`status-badge ${tickets.length > 0 ? '' : 'neutral'}`}>
              {tickets.length} {tickets.length === 1 ? 'ticket' : 'tickets'}
            </span>
          </div>
          {tickets.length > 0 ? (
            <div style={{ display: 'grid', gap: '12px' }}>
              {tickets.map((t) => (
                <div
                  key={`ticket-${t.id}`}
                  style={{
                    padding: '16px',
                    border: '1px solid #e4e1d9',
                    borderRadius: '12px',
                    background: '#fff',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontSize: '11px', fontFamily: "'DM Mono', monospace", color: '#7a8490' }}>
                      TICKET #{t.id}
                    </span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: t.priority === 'critical' ? '#fee2e2' : t.priority === 'high' ? '#ffedd5' : '#f0fdf4',
                        color: t.priority === 'critical' ? '#991b1b' : t.priority === 'high' ? '#9a3412' : '#166534',
                      }}
                    >
                      {t.priority}
                    </span>
                  </div>
                  <strong style={{ fontSize: '13px', color: '#111827' }}>{t.issue}</strong>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '11px', color: '#7a8490' }}>
                    <span>Status: <strong style={{ color: '#111827', textTransform: 'capitalize' }}>{t.status}</strong></span>
                    {t.created_at && <span>{new Date(t.created_at).toLocaleTimeString()}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No maintenance tickets"
              text="No tickets were generated during this inspection."
            />
          )}
        </div>

        {/* Safety Alerts */}
        <div className="section-block">
          <div className="section-heading">
            <h2>Safety Alerts</h2>
            <span className={`status-badge ${alerts.length > 0 ? '' : 'neutral'}`}>
              {alerts.length} {alerts.length === 1 ? 'alert' : 'alerts'}
            </span>
          </div>
          {alerts.length > 0 ? (
            <div style={{ display: 'grid', gap: '12px' }}>
              {alerts.map((a) => (
                <div
                  key={`alert-${a.id}`}
                  style={{
                    padding: '16px',
                    border: '1px solid #fca5a5',
                    borderRadius: '12px',
                    background: '#fff5f5',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontSize: '11px', fontFamily: "'DM Mono', monospace", color: '#991b1b' }}>
                      ALERT #{a.id}
                    </span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: '#fee2e2',
                        color: '#991b1b',
                      }}
                    >
                      {a.severity}
                    </span>
                  </div>
                  <strong style={{ fontSize: '13px', color: '#991b1b' }}>⚠ {a.hazard}</strong>
                  {a.evidence_text && (
                    <p style={{ margin: '6px 0 0', fontSize: '11px', color: '#7a8490', fontStyle: 'italic' }}>
                      Evidence: &quot;{a.evidence_text}&quot;
                    </p>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '11px', color: '#7a8490' }}>
                    <span>Status: <strong style={{ color: '#111827', textTransform: 'capitalize' }}>{a.status}</strong></span>
                    {a.created_at && <span>{new Date(a.created_at).toLocaleTimeString()}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No safety alerts"
              text="No safety conditions detected during this inspection."
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

function TicketsPage() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    let isMounted = true
    setLoading(true)
    setError(null)
    getMaintenanceTickets()
      .then((data) => {
        if (!isMounted) return
        setTickets(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        if (!isMounted) return
        setError(err.message || 'Unable to load tickets')
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })
    return () => { isMounted = false }
  }, [])

  const filteredTickets = useMemo(() => {
    if (filter === 'open') return tickets.filter((t) => t.status === 'open')
    if (filter === 'resolved') return tickets.filter((t) => t.status === 'resolved' || t.status === 'closed')
    return tickets
  }, [tickets, filter])

  return (
    <div className="page-body">
      <section className="page-intro">
        <div>
          <p className="eyebrow">Maintenance actions</p>
          <h2>Maintenance tickets</h2>
          <p className="muted">Actions created from inspection findings and out-of-range observations.</p>
        </div>
        <span className="record-count">{loading ? '...' : `${filteredTickets.length} records`}</span>
      </section>
      <div className="filter-row">
        <button className={`filter-chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
        <button className={`filter-chip ${filter === 'open' ? 'active' : ''}`} onClick={() => setFilter('open')}>Open</button>
        <button className={`filter-chip ${filter === 'resolved' ? 'active' : ''}`} onClick={() => setFilter('resolved')}>Resolved</button>
      </div>
      {loading ? (
        <LoadingState text="Loading maintenance tickets from PostgreSQL..." />
      ) : error ? (
        <EmptyState title="Unable to load tickets" text={error} />
      ) : filteredTickets.length === 0 ? (
        <EmptyState
          title="No maintenance tickets yet"
          text="Records created by the backend will appear here. The frontend does not manufacture operational data."
        />
      ) : (
        <div style={{ display: 'grid', gap: '16px', marginTop: '20px' }}>
          {filteredTickets.map((t) => (
            <div
              key={t.id}
              style={{
                background: '#fff',
                border: '1px solid #e4e1d9',
                borderRadius: '14px',
                padding: '20px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div>
                  <span style={{ fontSize: '11px', fontFamily: "'DM Mono', monospace", color: '#7a8490' }}>
                    TICKET #{t.id} {t.inspection_id ? `• Inspection #${t.inspection_id}` : ''}
                  </span>
                  <h3 style={{ margin: '4px 0 0', fontSize: '15px', color: '#111827' }}>{t.issue}</h3>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      background: t.priority === 'critical' ? '#fee2e2' : t.priority === 'high' ? '#ffedd5' : '#f0fdf4',
                      color: t.priority === 'critical' ? '#991b1b' : t.priority === 'high' ? '#9a3412' : '#166534',
                    }}
                  >
                    {t.priority}
                  </span>
                  <span className="status-badge" style={{ textTransform: 'capitalize' }}>
                    {t.status}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#7a8490', marginTop: '12px' }}>
                {t.equipment_asset_code && (
                  <span>
                    Asset: <strong style={{ color: '#111827' }}>{t.equipment_asset_code}</strong> {t.equipment_name ? `(${t.equipment_name})` : ''}
                  </span>
                )}
                {t.created_at && <span>Created: {new Date(t.created_at).toLocaleString()}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AlertsPage() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    let isMounted = true
    setLoading(true)
    setError(null)
    getSafetyAlerts()
      .then((data) => {
        if (!isMounted) return
        setAlerts(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        if (!isMounted) return
        setError(err.message || 'Unable to load safety alerts')
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })
    return () => { isMounted = false }
  }, [])

  const filteredAlerts = useMemo(() => {
    if (filter === 'open') return alerts.filter((a) => a.status === 'open')
    if (filter === 'resolved') return alerts.filter((a) => a.status === 'resolved' || a.status === 'closed')
    return alerts
  }, [alerts, filter])

  return (
    <div className="page-body">
      <section className="page-intro">
        <div>
          <p className="eyebrow">Safety events</p>
          <h2>Safety alerts</h2>
          <p className="muted">Conditions detected during inspections, with evidence attached.</p>
        </div>
        <span className="record-count">{loading ? '...' : `${filteredAlerts.length} records`}</span>
      </section>
      <div className="filter-row">
        <button className={`filter-chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
        <button className={`filter-chip ${filter === 'open' ? 'active' : ''}`} onClick={() => setFilter('open')}>Open</button>
        <button className={`filter-chip ${filter === 'resolved' ? 'active' : ''}`} onClick={() => setFilter('resolved')}>Resolved</button>
      </div>
      {loading ? (
        <LoadingState text="Loading safety alerts from PostgreSQL..." />
      ) : error ? (
        <EmptyState title="Unable to load safety alerts" text={error} />
      ) : filteredAlerts.length === 0 ? (
        <EmptyState
          title="No safety alerts yet"
          text="Records created by the backend will appear here. The frontend does not manufacture operational data."
        />
      ) : (
        <div style={{ display: 'grid', gap: '16px', marginTop: '20px' }}>
          {filteredAlerts.map((a) => (
            <div
              key={a.id}
              style={{
                background: a.severity === 'critical' ? '#fff5f5' : '#fff',
                border: a.severity === 'critical' ? '1px solid #fca5a5' : '1px solid #e4e1d9',
                borderRadius: '14px',
                padding: '20px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div>
                  <span style={{ fontSize: '11px', fontFamily: "'DM Mono', monospace", color: '#7a8490' }}>
                    ALERT #{a.id} {a.inspection_id ? `• Inspection #${a.inspection_id}` : ''}
                  </span>
                  <h3 style={{ margin: '4px 0 0', fontSize: '15px', color: '#991b1b' }}>⚠ {a.hazard}</h3>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      background: a.severity === 'critical' ? '#fee2e2' : '#ffedd5',
                      color: a.severity === 'critical' ? '#991b1b' : '#9a3412',
                    }}
                  >
                    {a.severity}
                  </span>
                  <span className="status-badge" style={{ textTransform: 'capitalize' }}>
                    {a.status}
                  </span>
                </div>
              </div>
              {a.evidence_text && (
                <div style={{ background: '#f9fafb', borderLeft: '3px solid #991b1b', padding: '8px 12px', margin: '10px 0', borderRadius: '4px' }}>
                  <p style={{ margin: 0, fontSize: '12px', color: '#374151', fontStyle: 'italic' }}>
                    Spoken evidence: &quot;{a.evidence_text}&quot;
                  </p>
                </div>
              )}
              <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#7a8490', marginTop: '10px' }}>
                {a.equipment_asset_code && (
                  <span>
                    Asset: <strong style={{ color: '#111827' }}>{a.equipment_asset_code}</strong> {a.equipment_name ? `(${a.equipment_name})` : ''}
                  </span>
                )}
                {a.created_at && <span>Created: {new Date(a.created_at).toLocaleString()}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ReportPage({ navigate, path }) {
  const routeParam = path.split('/')[2]?.split('?')[0]
  const inspectionId = routeParam && routeParam !== 'preview' ? Number(routeParam) : null
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!inspectionId) {
      setLoading(false)
      return
    }

    let isMounted = true
    setLoading(true)
    setError(null)

    getInspectionReport(inspectionId)
      .then((data) => {
        if (!isMounted) return
        setReport(data)
      })
      .catch((err) => {
        if (!isMounted) return
        setError(err.message || 'Unable to load report')
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => { isMounted = false }
  }, [inspectionId])

  if (loading) {
    return (
      <div className="page-body report-page">
        <LoadingState text="Loading inspection report from PostgreSQL..." />
      </div>
    )
  }

  if (error || (!inspectionId && !report)) {
    return (
      <div className="page-body report-page">
        <div className="report-actions">
          <span className="status-badge neutral">{error ? 'Error loading report' : 'Preview / no report loaded'}</span>
          <div>
            <button className="primary-cta" onClick={() => navigate('/equipment')}>
              New inspection ↗
            </button>
          </div>
        </div>
        <article className="report-sheet" style={{ background: '#fff', border: '1px solid #e4e1d9', borderRadius: '16px', padding: '40px' }}>
          <p className="eyebrow">FieldVoice inspection report</p>
          <h2>{error ? 'Unable to load report' : 'No report selected'}</h2>
          <p className="muted">
            {error || 'Select an inspection from the catalog or completed session to view its authoritative report.'}
          </p>
          <div className="report-rule" />
          <div className="report-placeholder">
            <span>◌</span>
            <strong>{error ? error : 'Navigate to a completed inspection to generate its report.'}</strong>
          </div>
        </article>
      </div>
    )
  }

  const { inspection, equipment, checklist, observations, maintenance_tickets, safety_alerts, summary } = report
  const isCompleted = inspection?.status === 'completed'

  return (
    <div className="page-body report-page">
      <div className="report-actions">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="text-button" style={{ fontSize: '12px', color: '#56616f' }} onClick={() => navigate(`/inspection/${inspection.id}/result`)}>
            ← Back to result
          </button>
          <span className={`status-badge ${isCompleted ? '' : 'neutral'}`}>
            {isCompleted ? 'Verified & Completed Report' : 'In-Progress Inspection Report'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="secondary-cta" onClick={() => window.print()}>
            Print report
          </button>
          <button className="primary-cta" onClick={() => navigate('/equipment')}>
            New inspection ↗
          </button>
        </div>
      </div>

      <article className="report-sheet" style={{ background: '#fff', border: '1px solid #e4e1d9', borderRadius: '16px', padding: '40px' }}>
        {/* Document Header */}
        <header style={{ borderBottom: '2px solid #111827', paddingBottom: '20px', marginBottom: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <p className="eyebrow" style={{ color: '#2f6558', fontWeight: 700, margin: '0 0 6px' }}>
                FIELDVOICE • INDUSTRIAL INSPECTION REPORT
              </p>
              <h1 style={{ margin: 0, fontSize: '28px', color: '#111827', letterSpacing: '-0.02em' }}>
                Inspection #{inspection.id}
              </h1>
              <p style={{ margin: '6px 0 0', color: '#56616f', fontSize: '13px' }}>
                Asset: <strong>{equipment.asset_code}</strong> — {equipment.name} ({equipment.equipment_type || 'General'})
              </p>
            </div>
            <div style={{ textAlign: 'right', fontFamily: "'DM Mono', monospace", fontSize: '11px', color: '#7a8490' }}>
              <div>Generated: {new Date(report.generated_at).toLocaleString()}</div>
              <div style={{ marginTop: '4px' }}>Status: <strong style={{ color: isCompleted ? '#2f6558' : '#b45309', textTransform: 'uppercase' }}>{inspection.status}</strong></div>
              {inspection.duration && <div style={{ marginTop: '4px' }}>Duration: {inspection.duration}</div>}
            </div>
          </div>
        </header>

        {/* Executive Summary Card */}
        <section style={{ background: '#f8faf9', border: '1px solid #dce8e2', borderRadius: '12px', padding: '18px 22px', marginBottom: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#2f6558' }}>
              Executive Summary
            </span>
            <span style={{ fontSize: '11px', fontFamily: "'DM Mono', monospace", color: '#7a8490' }}>
              {summary.completed_count}/{summary.required_count} Checkpoints Recorded
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.6, color: '#1f2937' }}>
            {summary.overview}
          </p>
          {inspection.summary && (
            <p style={{ margin: '10px 0 0', fontSize: '12px', fontStyle: 'italic', color: '#56616f', borderTop: '1px dashed #dce8e2', paddingTop: '8px' }}>
              Technician note: &quot;{inspection.summary}&quot;
            </p>
          )}
        </section>

        {/* Two-Column Metadata: Equipment & Lifecycle */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '32px' }}>
          <div style={{ padding: '18px', border: '1px solid #e4e1d9', borderRadius: '12px' }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.04em', color: '#56616f' }}>
              Equipment Profile
            </h3>
            <div style={{ display: 'grid', gap: '8px', fontSize: '12px' }}>
              <div><span style={{ color: '#7a8490' }}>Asset Code:</span> <strong>{equipment.asset_code}</strong></div>
              <div><span style={{ color: '#7a8490' }}>Name:</span> <strong>{equipment.name}</strong></div>
              <div><span style={{ color: '#7a8490' }}>Type:</span> <span>{equipment.equipment_type || '—'}</span></div>
              <div><span style={{ color: '#7a8490' }}>Location:</span> <span>{equipment.location || '—'}</span></div>
              {equipment.description && (
                <div style={{ color: '#56616f', fontSize: '11px', marginTop: '4px' }}>
                  {equipment.description}
                </div>
              )}
            </div>
          </div>

          <div style={{ padding: '18px', border: '1px solid #e4e1d9', borderRadius: '12px' }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.04em', color: '#56616f' }}>
              Inspection Execution
            </h3>
            <div style={{ display: 'grid', gap: '8px', fontSize: '12px' }}>
              <div><span style={{ color: '#7a8490' }}>Inspection ID:</span> <strong>#{inspection.id}</strong></div>
              <div><span style={{ color: '#7a8490' }}>Type:</span> <span style={{ textTransform: 'capitalize' }}>{inspection.inspection_type || 'Routine'}</span></div>
              <div><span style={{ color: '#7a8490' }}>Started:</span> <span>{inspection.started_at ? new Date(inspection.started_at).toLocaleString() : '—'}</span></div>
              <div><span style={{ color: '#7a8490' }}>Completed:</span> <span>{inspection.completed_at ? new Date(inspection.completed_at).toLocaleString() : 'In progress'}</span></div>
              <div><span style={{ color: '#7a8490' }}>Duration:</span> <strong>{inspection.duration || (isCompleted ? '—' : 'In progress')}</strong></div>
            </div>
          </div>
        </div>

        {/* Checklist Progress */}
        <section style={{ marginBottom: '32px' }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '14px', color: '#111827' }}>
            Checklist Status ({checklist.completed_fields.length}/{checklist.required_fields.length})
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {checklist.required_fields.map((f) => {
              const done = checklist.completed_fields.includes(f)
              return (
                <span
                  key={f}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: done ? '1px solid #c6ddd3' : '1px dashed #d4d5cc',
                    background: done ? '#eef5f1' : '#f9fafb',
                    color: done ? '#2f6558' : '#7a8490',
                    fontSize: '12px',
                    fontWeight: done ? 600 : 400,
                  }}
                >
                  <span>{done ? '✓' : '○'}</span>
                  <span style={{ textTransform: 'capitalize' }}>{f}</span>
                </span>
              )
            })}
          </div>
        </section>

        {/* Recorded Observations Table */}
        <section style={{ marginBottom: '36px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', color: '#111827' }}>
              Recorded Observations ({observations.length})
            </h3>
            <span style={{ fontSize: '11px', color: '#7a8490' }}>
              Deterministic Validation & Spoken Quotes
            </span>
          </div>

          {observations.length > 0 ? (
            <div style={{ overflowX: 'auto', border: '1px solid #e4e1d9', borderRadius: '12px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f9fafb', borderBottom: '1px solid #e4e1d9', color: '#56616f', textTransform: 'uppercase', fontSize: '10px', letterSpacing: '0.04em' }}>
                    <th style={{ padding: '12px 14px' }}>Field</th>
                    <th style={{ padding: '12px 14px' }}>Value</th>
                    <th style={{ padding: '12px 14px' }}>Unit</th>
                    <th style={{ padding: '12px 14px' }}>Validation</th>
                    <th style={{ padding: '12px 14px' }}>Operating Limit</th>
                    <th style={{ padding: '12px 14px' }}>Evidence</th>
                    <th style={{ padding: '12px 14px' }}>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {observations.map((obs, idx) => {
                    const val = obs.validation || {}
                    const isOOR = val.status === 'out_of_range'
                    return (
                      <tr
                        key={obs.id}
                        style={{
                          borderBottom: idx === observations.length - 1 ? 'none' : '1px solid #e4e1d9',
                          background: isOOR ? '#fffbeb' : '#fff',
                        }}
                      >
                        <td style={{ padding: '12px 14px', fontWeight: 600, color: '#111827', textTransform: 'capitalize' }}>
                          {obs.field_name}
                        </td>
                        <td style={{ padding: '12px 14px', fontFamily: "'DM Mono', monospace", fontWeight: 600, color: '#2f6558' }}>
                          {obs.value}
                        </td>
                        <td style={{ padding: '12px 14px', fontFamily: "'DM Mono', monospace", color: '#56616f' }}>
                          {obs.unit || '—'}
                        </td>
                        <td style={{ padding: '12px 14px' }}>
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 600,
                              color: val.status === 'normal' ? '#2f6558' : isOOR ? '#b45309' : '#7a8490',
                            }}
                          >
                            {isOOR ? '⚠ Out of range' : val.status === 'normal' ? '✓ Normal' : 'Unknown'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', fontFamily: "'DM Mono', monospace", color: '#56616f', fontSize: '11px' }}>
                          {val.limit ? `${val.limit.min}–${val.limit.max}` : '—'}
                        </td>
                        <td style={{ padding: '12px 14px', maxWidth: '260px', color: '#374151', fontStyle: 'italic', fontSize: '11px' }}>
                          {obs.evidence_text ? `"${obs.evidence_text}"` : '—'}
                        </td>
                        <td style={{ padding: '12px 14px', fontFamily: "'DM Mono', monospace", color: '#7a8490', fontSize: '11px' }}>
                          {obs.confidence != null ? `${Math.round(obs.confidence * 100)}%` : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No observations recorded" text="No observations were found for this inspection in PostgreSQL." />
          )}
        </section>

        {/* Maintenance Tickets Section */}
        <section style={{ marginBottom: '36px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', color: '#111827' }}>
              Maintenance Tickets ({maintenance_tickets.length})
            </h3>
            <span style={{ fontSize: '11px', color: '#7a8490' }}>
              Generated from out-of-range observations & technician reports
            </span>
          </div>

          {maintenance_tickets.length > 0 ? (
            <div style={{ display: 'grid', gap: '10px' }}>
              {maintenance_tickets.map((t) => (
                <div
                  key={t.id}
                  style={{
                    padding: '14px 18px',
                    border: '1px solid #e4e1d9',
                    borderRadius: '10px',
                    background: '#fff',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '10px', fontFamily: "'DM Mono', monospace", color: '#7a8490', marginBottom: '4px' }}>
                      TICKET #{t.id} • Created: {t.created_at ? new Date(t.created_at).toLocaleString() : '—'}
                    </div>
                    <strong style={{ fontSize: '13px', color: '#111827' }}>{t.issue}</strong>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '3px 8px',
                        borderRadius: '6px',
                        background: t.priority === 'critical' ? '#fee2e2' : t.priority === 'high' ? '#ffedd5' : '#f0fdf4',
                        color: t.priority === 'critical' ? '#991b1b' : t.priority === 'high' ? '#9a3412' : '#166534',
                      }}
                    >
                      {t.priority}
                    </span>
                    <span className="status-badge" style={{ textTransform: 'capitalize' }}>
                      {t.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ margin: 0, fontSize: '12px', color: '#7a8490', fontStyle: 'italic' }}>
              No maintenance tickets were generated during this inspection.
            </p>
          )}
        </section>

        {/* Safety Alerts Section */}
        <section style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', color: '#991b1b' }}>
              Safety Alerts ({safety_alerts.length})
            </h3>
            <span style={{ fontSize: '11px', color: '#7a8490' }}>
              Critical hazard conditions & evidence
            </span>
          </div>

          {safety_alerts.length > 0 ? (
            <div style={{ display: 'grid', gap: '10px' }}>
              {safety_alerts.map((a) => (
                <div
                  key={a.id}
                  style={{
                    padding: '14px 18px',
                    border: '1px solid #fca5a5',
                    borderRadius: '10px',
                    background: '#fff5f5',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontSize: '10px', fontFamily: "'DM Mono', monospace", color: '#991b1b' }}>
                      ALERT #{a.id} • Created: {a.created_at ? new Date(a.created_at).toLocaleString() : '—'}
                    </span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '3px 8px',
                        borderRadius: '6px',
                        background: '#fee2e2',
                        color: '#991b1b',
                      }}
                    >
                      {a.severity}
                    </span>
                  </div>
                  <strong style={{ fontSize: '13px', color: '#991b1b' }}>⚠ {a.hazard}</strong>
                  {a.evidence_text && (
                    <p style={{ margin: '6px 0 0', fontSize: '11px', color: '#374151', fontStyle: 'italic' }}>
                      Evidence: &quot;{a.evidence_text}&quot;
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p style={{ margin: 0, fontSize: '12px', color: '#7a8490', fontStyle: 'italic' }}>
              No safety alerts were recorded during this inspection.
            </p>
          )}
        </section>

        {/* Footer Signoff */}
        <footer style={{ borderTop: '1px solid #e4e1d9', paddingTop: '20px', marginTop: '40px', display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#7a8490' }}>
          <div>
            FieldVoice Autonomous Hands-Free Inspection Copilot
          </div>
          <div>
            Document Hash / Timestamp: {report.generated_at}
          </div>
        </footer>
      </article>
    </div>
  )
}

function EmptyState({ title, text }) { return <div className="empty-state"><span className="empty-icon">○</span><h3>{title}</h3><p>{text}</p></div> }
function LoadingState({ text }) { return <div className="empty-state"><span className="loading-line" /><h3>Loading</h3><p>{text}</p></div> }

export default App
