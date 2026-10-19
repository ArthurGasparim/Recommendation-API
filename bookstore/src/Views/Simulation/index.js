import { useEffect, useMemo, useState } from 'react'
import {
    FaBolt,
    FaChartLine,
    FaCheckCircle,
    FaClock,
    FaDatabase,
    FaDownload,
    FaExclamationTriangle,
    FaFileExcel,
    FaFlask,
    FaPlay,
    FaPlus,
    FaSync,
    FaShieldAlt,
    FaTrash,
} from 'react-icons/fa'
import Header from '../../Components/Header'
import Footer from '../../Components/Footer'
import SimulationChart, { formatMetric } from '../../Components/SimulationChart'
import api from '../../Services/service'
import * as Style from './style'

const PRESETS = {
    coordinated: {
        label: 'Campanha coordenada',
        attacks: [
            ['push_attack', 0.18, 0.25, 0.68],
            ['nuke_attack', 0.34, 0.22, 0.58],
            ['distribution_drift', 0.62, 0.24, 0.52],
        ],
    },
    data: {
        label: 'Dados + drift',
        attacks: [
            ['data_corruption', 0.18, 0.24, 0.64],
            ['distribution_drift', 0.50, 0.30, 0.58],
        ],
    },
    infrastructure: {
        label: 'Infraestrutura',
        attacks: [
            ['latency_degradation', 0.20, 0.28, 0.70],
            ['dependency_outage', 0.62, 0.15, 0.78],
        ],
    },
}

const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))

function formatMeasured(value, digits = 3) {
    if (!Number.isFinite(Number(value))) return '—'
    return Number(value).toFixed(digits)
}

function buildPreset(preset, duration) {
    return preset.attacks.map(([type, startRatio, durationRatio, intensity], index) => {
        const start = Math.max(1, Math.round(duration * startRatio))
        const attackDuration = Math.max(2, Math.min(
            Math.round(duration * durationRatio),
            duration - start,
        ))
        return {
            attack_id: `${type}-${index + 1}`,
            attack_type: type,
            start_minute: start,
            duration_minutes: attackDuration,
            intensity,
        }
    })
}

function clampAttacks(attacks, duration) {
    return attacks.map(attack => {
        const start = Math.min(Math.max(1, Number(attack.start_minute)), duration - 1)
        return {
            ...attack,
            start_minute: start,
            duration_minutes: Math.min(
                Math.max(1, Number(attack.duration_minutes)),
                duration - start,
            ),
            intensity: Number(attack.intensity),
        }
    })
}

function Timeline({attacks, duration}) {
    return (
        <Style.Timeline aria-label="Linha do tempo dos ataques">
            <div className="scale"><span>0 min</span><span>{duration} min</span></div>
            <div className="track">
                {attacks.map(attack => (
                    <div
                        className="attack"
                        key={attack.attack_id}
                        title={`${attack.label}: minuto ${attack.start_minute} ao ${attack.start_minute + attack.duration_minutes}`}
                        style={{
                            left: `${attack.start_minute / duration * 100}%`,
                            width: `${attack.duration_minutes / duration * 100}%`,
                            backgroundColor: attack.color,
                        }}
                    >
                        <span>{attack.label}</span>
                    </div>
                ))}
            </div>
        </Style.Timeline>
    )
}

function Simulation() {
    const isAdmin = sessionStorage.getItem('isAdmin') === 'true'
    const [catalog, setCatalog] = useState(null)
    const [form, setForm] = useState(null)
    const [result, setResult] = useState(null)
    const [selectedMetric, setSelectedMetric] = useState('ndcg_at_10')
    const [focusedModel, setFocusedModel] = useState('hybrid')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [realCatalog, setRealCatalog] = useState(null)
    const [realForm, setRealForm] = useState(null)
    const [realMetrics, setRealMetrics] = useState(null)
    const [activeJob, setActiveJob] = useState(null)
    const [realBusy, setRealBusy] = useState('')
    const [realError, setRealError] = useState('')

    useEffect(() => {
        if (!isAdmin) return undefined
        let active = true
        async function initialize() {
            try {
                setLoading(true)
                const [response, measuredCatalog, metrics] = await Promise.all([
                    api.get('/admin/experiments/catalog'),
                    api.get('/admin/experiments/real/catalog'),
                    api.get('/admin/experiments/real/metrics'),
                ])
                if (!active) return
                setCatalog(response.data)
                setForm(response.data.default_request)
                setRealCatalog(measuredCatalog.data)
                setRealForm(measuredCatalog.data.default_request)
                setRealMetrics(metrics.data)
                const simulation = await api.post(
                    '/admin/experiments/simulate',
                    response.data.default_request,
                )
                if (active) setResult(simulation.data)
            } catch (requestError) {
                if (active) setError(requestError.response?.data?.detail || 'Não foi possível iniciar o laboratório')
            } finally {
                if (active) setLoading(false)
            }
        }
        initialize()
        return () => { active = false }
    }, [isAdmin])

    async function refreshMeasuredMetrics() {
        try {
            setRealBusy('metrics')
            setRealError('')
            const response = await api.get('/admin/experiments/real/metrics')
            setRealMetrics(response.data)
            return response.data
        } catch (requestError) {
            setRealError(requestError.response?.data?.detail || 'Não foi possível obter as métricas medidas')
            return null
        } finally {
            setRealBusy('')
        }
    }

    async function pollJob(jobId) {
        let consecutiveFailures = 0
        for (let attempt = 0; attempt < 3600; attempt += 1) {
            try {
                const response = await api.get(`/admin/jobs/${jobId}`)
                consecutiveFailures = 0
                setActiveJob(response.data)
                if (response.data.status === 'completed') return response.data
                if (response.data.status === 'failed') {
                    throw new Error(response.data.error || response.data.message || 'A tarefa falhou')
                }
            } catch (requestError) {
                // Uma carga grande pode provocar uma falha transitória no
                // SQLite local; no EKS também podem ocorrer trocas de pod/ALB.
                // O job está persistido, portanto é seguro retomar a consulta.
                if (!requestError.response || requestError.response.status >= 500) {
                    consecutiveFailures += 1
                    if (consecutiveFailures < 10) {
                        await wait(Math.min(1000 * consecutiveFailures, 5000))
                        continue
                    }
                }
                throw requestError
            }
            await wait(1000)
        }
        throw new Error('A tarefa excedeu o tempo máximo de acompanhamento')
    }

    async function loadCsvData() {
        try {
            setRealBusy('load')
            setRealError('')
            const response = await api.post('/admin/data/load')
            setActiveJob(response.data)
            await pollJob(response.data.id)
            await refreshMeasuredMetrics()
        } catch (requestError) {
            const detail = requestError.response?.data?.detail
            setRealError(typeof detail === 'string' ? detail : requestError.message || 'Não foi possível carregar os CSVs')
        } finally {
            setRealBusy('')
        }
    }

    async function runMeasuredExperiment() {
        try {
            setRealBusy('experiment')
            setRealError('')
            const response = await api.post('/admin/experiments/real/run', realForm)
            setActiveJob(response.data)
            await pollJob(response.data.id)
            await refreshMeasuredMetrics()
        } catch (requestError) {
            const detail = requestError.response?.data?.detail
            const message = typeof detail === 'object' ? detail?.message : detail
            setRealError(message || requestError.message || 'Não foi possível executar o ataque controlado')
        } finally {
            setRealBusy('')
        }
    }

    async function downloadSuite(jobId) {
        try {
            setRealError('')
            const response = await api.get(
                `/admin/experiments/real/suite/${jobId}/xlsx`,
                {responseType: 'blob'},
            )
            const downloadUrl = window.URL.createObjectURL(response.data)
            const link = document.createElement('a')
            link.href = downloadUrl
            link.download = `comparacao-observabilidade-${jobId}.xlsx`
            document.body.appendChild(link)
            link.click()
            link.remove()
            window.URL.revokeObjectURL(downloadUrl)
        } catch (requestError) {
            const detail = requestError.response?.data?.detail
            setRealError(typeof detail === 'string' ? detail : 'Não foi possível baixar a planilha')
        }
    }

    async function runFullSuite() {
        try {
            setRealBusy('suite')
            setRealError('')
            const request = {
                intensity: realForm.intensity,
                seed: realForm.seed,
                sample_users: realForm.sample_users,
                top_k: realForm.top_k,
                target_book_id: realForm.target_book_id,
            }
            const response = await api.post('/admin/experiments/real/suite', request)
            setActiveJob(response.data)
            const completed = await pollJob(response.data.id)
            await refreshMeasuredMetrics()
            await downloadSuite(completed.id)
        } catch (requestError) {
            const detail = requestError.response?.data?.detail
            const message = typeof detail === 'object' ? detail?.message : detail
            setRealError(message || requestError.message || 'Não foi possível executar a bateria completa')
        } finally {
            setRealBusy('')
        }
    }

    const modelMap = useMemo(() => Object.fromEntries(
        (catalog?.models || []).map(model => [model.id, model]),
    ), [catalog])
    const attackMap = useMemo(() => Object.fromEntries(
        (catalog?.attacks || []).map(attack => [attack.id, attack]),
    ), [catalog])
    const metricMap = useMemo(() => Object.fromEntries(
        (catalog?.metrics || []).map(metric => [metric.id, metric]),
    ), [catalog])

    async function runSimulation(payload = form) {
        if (!payload || payload.models.length === 0) {
            setError('Selecione pelo menos um modelo')
            return
        }
        const normalized = {
            ...payload,
            attacks: clampAttacks(payload.attacks, payload.duration_minutes),
        }
        try {
            setLoading(true)
            setError('')
            setForm(normalized)
            const response = await api.post('/admin/experiments/simulate', normalized)
            setResult(response.data)
            if (!normalized.models.includes(focusedModel)) {
                setFocusedModel(normalized.models[0])
            }
        } catch (requestError) {
            const detail = requestError.response?.data?.detail
            setError(typeof detail === 'string' ? detail : 'A configuração da simulação é inválida')
        } finally {
            setLoading(false)
        }
    }

    function toggleModel(modelId) {
        setForm(current => {
            const selected = current.models.includes(modelId)
            if (selected && current.models.length === 1) return current
            return {
                ...current,
                models: selected
                    ? current.models.filter(id => id !== modelId)
                    : [...current.models, modelId],
            }
        })
    }

    function changeDuration(value) {
        const duration = Number(value)
        setForm(current => ({
            ...current,
            duration_minutes: duration,
            attacks: clampAttacks(current.attacks, duration),
        }))
    }

    function applyPreset(preset) {
        const attacks = buildPreset(preset, form.duration_minutes)
        setForm(current => ({...current, attacks}))
    }

    function addAttack() {
        const index = form.attacks.length + 1
        const start = Math.max(1, Math.round(form.duration_minutes * 0.3))
        setForm(current => ({
            ...current,
            attacks: [
                ...current.attacks,
                {
                    attack_id: `ataque-${Date.now()}-${index}`,
                    attack_type: catalog.attacks[0].id,
                    start_minute: start,
                    duration_minutes: Math.min(10, form.duration_minutes - start),
                    intensity: 0.5,
                },
            ],
        }))
    }

    function updateAttack(index, field, value) {
        setForm(current => ({
            ...current,
            attacks: current.attacks.map((attack, attackIndex) => attackIndex === index
                ? {...attack, [field]: field === 'attack_type' ? value : Number(value)}
                : attack),
        }))
    }

    function removeAttack(index) {
        setForm(current => ({
            ...current,
            attacks: current.attacks.filter((_, attackIndex) => attackIndex !== index),
        }))
    }

    if (!isAdmin) {
        return (
            <Style.Page>
                <Header/>
                <Style.AccessCard>
                    <FaShieldAlt/>
                    <h1>Laboratório restrito</h1>
                    <p>Entre com um usuário administrador para configurar e executar simulações.</p>
                    <a href="/">Voltar ao login</a>
                </Style.AccessCard>
                <Footer/>
            </Style.Page>
        )
    }

    if (!catalog || !form || !realCatalog || !realForm) {
        return (
            <Style.Page>
                <Header admin/>
                <Style.LoadingCard><span/><p>{error || 'Preparando o laboratório…'}</p></Style.LoadingCard>
                <Footer/>
            </Style.Page>
        )
    }

    const focusedWithout = result?.series.find(series => series.model === focusedModel && !series.defended)
    const focusedWith = result?.series.find(series => series.model === focusedModel && series.defended)
    const bestReduction = result?.comparison.reduce((best, item) => (
        Number(item.quality_loss_reduction_percent || 0) > Number(best?.quality_loss_reduction_percent || 0)
            ? item : best
    ), result.comparison[0])
    const metric = metricMap[selectedMetric]
    const measuredLatest = realMetrics?.latest
    const measuredDataset = realMetrics?.dataset || {}
    const latestSuite = realMetrics?.latest_suite
    const realAttack = realCatalog.attacks.find(option => option.id === realForm.attack_type)
    const realModel = realCatalog.models.find(option => option.id === realForm.model)

    return (
        <Style.Page>
            <Header admin/>
            <Style.Hero>
                <div className="eyebrow"><FaFlask/> EXPERIMENTO MEDIDO + SIMULAÇÃO EXPLORATÓRIA</div>
                <div className="hero-grid">
                    <div>
                        <h1>Laboratório de Resiliência</h1>
                        <p>Carregue o Goodbooks no PostgreSQL, execute um ataque seguro sobre uma cópia do snapshot e recupere métricas reais sem corromper o banco principal.</p>
                    </div>
                    <div className="hero-status">
                        <span><FaCheckCircle/> Resultados persistidos</span>
                        <span><FaShieldAlt/> Snapshot principal protegido</span>
                        <span><FaChartLine/> Métricas no Prometheus</span>
                    </div>
                </div>
                <div className="disclaimer"><FaExclamationTriangle/> {realCatalog.disclaimer} O painel temporal abaixo permanece exploratório: {catalog.disclaimer}</div>
            </Style.Hero>

            <Style.RealLab>
                <Style.RealHeader>
                    <div>
                        <span>FLUXO REAL NA AWS</span>
                        <h2>Carga, ataque controlado e métricas</h2>
                        <p>As tarefas são executadas em segundo plano e ficam registradas no PostgreSQL, inclusive quando a API possui mais de uma réplica.</p>
                    </div>
                    <button type="button" onClick={refreshMeasuredMetrics} disabled={Boolean(realBusy)}>
                        <FaDownload/> {realBusy === 'metrics' ? 'Atualizando…' : 'Obter métricas'}
                    </button>
                </Style.RealHeader>

                <Style.RealActions>
                    <Style.RealCard>
                        <div className="card-title"><FaDatabase/><div><b>1. Dados de teste</b><small>CSVs empacotados na API</small></div></div>
                        <div className="dataset-counts">
                            <span><b>{Number(measuredDataset.books || 0).toLocaleString('pt-BR')}</b> livros</span>
                            <span><b>{Number(measuredDataset.ratings || 0).toLocaleString('pt-BR')}</b> avaliações</span>
                        </div>
                        <button type="button" className="primary" onClick={loadCsvData} disabled={Boolean(realBusy)}>
                            <FaDatabase/> {realBusy === 'load' ? 'Carregando…' : 'Carregar dados dos CSVs'}
                        </button>
                    </Style.RealCard>

                    <Style.RealCard>
                        <div className="card-title"><FaBolt/><div><b>2. Ataque real controlado</b><small>{realAttack?.description}</small></div></div>
                        <div className="form-grid">
                            <label>Modelo
                                <select value={realForm.model} onChange={event => setRealForm(current => ({...current, model: event.target.value}))}>
                                    {realCatalog.models.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                                </select>
                            </label>
                            <label>Ataque
                                <select value={realForm.attack_type} onChange={event => setRealForm(current => ({...current, attack_type: event.target.value}))}>
                                    {realCatalog.attacks.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                                </select>
                            </label>
                            <label>Usuários avaliados
                                <input type="number" min="5" max="100" value={realForm.sample_users} onChange={event => setRealForm(current => ({...current, sample_users: Number(event.target.value)}))}/>
                            </label>
                            <label>Seed
                                <input type="number" min="0" value={realForm.seed} onChange={event => setRealForm(current => ({...current, seed: Number(event.target.value)}))}/>
                            </label>
                        </div>
                        <label className="real-intensity">
                            <span>Intensidade <b>{Math.round(realForm.intensity * 100)}%</b></span>
                            <input type="range" min="0.01" max="0.30" step="0.01" value={realForm.intensity} onChange={event => setRealForm(current => ({...current, intensity: Number(event.target.value)}))}/>
                        </label>
                        <Style.ModeToggle>
                            <button type="button" className={!realForm.with_observability ? 'active danger' : ''} onClick={() => setRealForm(current => ({...current, with_observability: false}))}>Sem observabilidade</button>
                            <button type="button" className={realForm.with_observability ? 'active safe' : ''} onClick={() => setRealForm(current => ({...current, with_observability: true}))}><FaShieldAlt/> Com observabilidade</button>
                        </Style.ModeToggle>
                        <button type="button" className="primary attack" onClick={runMeasuredExperiment} disabled={Boolean(realBusy) || !measuredDataset.ratings}>
                            <FaPlay/> {realBusy === 'experiment' ? 'Executando…' : 'Executar ataque'}
                        </button>
                    </Style.RealCard>

                    <Style.RealCard>
                        <div className="card-title"><FaChartLine/><div><b>3. Resultado medido</b><small>{realModel?.label}</small></div></div>
                        {measuredLatest ? (
                            <Style.MiniMetrics>
                                <span><small>NDCG@{measuredLatest.method.top_k}</small><b>{formatMeasured(measuredLatest.measured.ndcg_at_k)}</b></span>
                                <span><small>Latência p95</small><b>{formatMeasured(measuredLatest.measured.latency_p95_ms, 1)} ms</b></span>
                                <span><small>Disponibilidade</small><b>{formatMeasured(measuredLatest.measured.availability_percent, 1)}%</b></span>
                                <span><small>Qualidade dos dados</small><b>{formatMeasured(measuredLatest.data_quality.effective.quality_score * 100, 1)}%</b></span>
                            </Style.MiniMetrics>
                        ) : <Style.NoMetrics>Nenhuma execução medida. Carregue os dados e execute um ataque.</Style.NoMetrics>}
                        <button type="button" onClick={refreshMeasuredMetrics} disabled={Boolean(realBusy)}><FaSync/> Atualizar métricas</button>
                    </Style.RealCard>
                </Style.RealActions>

                <Style.SuitePanel>
                    <div className="suite-icon"><FaFileExcel/></div>
                    <div className="suite-copy">
                        <span>BATERIA COMPLETA</span>
                        <h3>Todos os modelos × todos os ataques</h3>
                        <p>
                            Executa em sequência {realCatalog.suite?.models || realCatalog.models.length} modelos ×{' '}
                            {realCatalog.suite?.attacks || realCatalog.attacks.length} ataques, sempre sem e com observabilidade,
                            e consolida qualidade inicial, qualidade atacada e qualidade protegida em um XLSX.
                        </p>
                    </div>
                    <div className="suite-stats">
                        <b>{realCatalog.suite?.comparisons || realCatalog.models.length * realCatalog.attacks.length}</b>
                        <span>comparações</span>
                        <b>{realCatalog.suite?.scenario_runs || realCatalog.models.length * realCatalog.attacks.length * 2}</b>
                        <span>execuções</span>
                    </div>
                    <div className="suite-actions">
                        <button
                            type="button"
                            className="run-suite"
                            onClick={runFullSuite}
                            disabled={Boolean(realBusy) || !measuredDataset.ratings}
                        >
                            <FaPlay/> {realBusy === 'suite' ? 'Executando bateria…' : 'Testar todos e gerar XLSX'}
                        </button>
                        {latestSuite && (
                            <button
                                type="button"
                                className="download-suite"
                                onClick={() => downloadSuite(latestSuite.id)}
                                disabled={realBusy === 'suite'}
                            >
                                <FaFileExcel/> Baixar último XLSX
                            </button>
                        )}
                    </div>
                </Style.SuitePanel>

                {activeJob && (
                    <Style.JobStatus className={activeJob.status}>
                        <div><b>{activeJob.message}</b><span>{activeJob.progress}% · tarefa {activeJob.id}</span></div>
                        <progress max="100" value={activeJob.progress}/>
                    </Style.JobStatus>
                )}
                {realError && <Style.Error role="alert">{realError}</Style.Error>}

                {measuredLatest && (
                    <Style.MeasuredDetails>
                        <Style.ResultHeader>
                            <div><span>ÚLTIMA EXECUÇÃO MEDIDA</span><h2>{measuredLatest.attack.type} · {measuredLatest.configuration.with_observability ? 'com observabilidade' : 'sem observabilidade'}</h2><p>Run ID: {measuredLatest.run_id}</p></div>
                            <div className="seed">SEED <b>{measuredLatest.method.seed}</b></div>
                        </Style.ResultHeader>
                        <Style.KpiGrid>
                            <Style.KpiCard><span>NDCG baseline</span><strong>{formatMeasured(measuredLatest.baseline.ndcg_at_k)}</strong><small>{measuredLatest.configuration.model}</small></Style.KpiCard>
                            <Style.KpiCard className={measuredLatest.deltas.ndcg_at_k >= 0 ? 'green' : ''}><span>NDCG após ataque/resposta</span><strong>{formatMeasured(measuredLatest.measured.ndcg_at_k)}</strong><small>Δ {formatMeasured(measuredLatest.deltas.ndcg_at_k)}</small></Style.KpiCard>
                            <Style.KpiCard><span>Detecção</span><strong>{measuredLatest.observability.detected ? 'SIM' : 'NÃO'}</strong><small>{measuredLatest.observability.detection_ms ? `${measuredLatest.observability.detection_ms} ms` : 'desativada'}</small></Style.KpiCard>
                            <Style.KpiCard><span>Tempo total</span><strong>{formatMeasured(measuredLatest.timing.total_seconds, 1)}<em> s</em></strong><small>{measuredLatest.dataset.evaluation_users} usuários</small></Style.KpiCard>
                        </Style.KpiGrid>
                        <Style.MeasurementTable>
                            <table><thead><tr><th>Métrica</th><th>Baseline</th><th>Medido</th><th>Variação</th></tr></thead><tbody>
                                <tr><td>NDCG@{measuredLatest.method.top_k}</td><td>{formatMeasured(measuredLatest.baseline.ndcg_at_k)}</td><td>{formatMeasured(measuredLatest.measured.ndcg_at_k)}</td><td>{formatMeasured(measuredLatest.deltas.ndcg_at_k)}</td></tr>
                                <tr><td>Precision@{measuredLatest.method.top_k}</td><td>{formatMeasured(measuredLatest.baseline.precision_at_k)}</td><td>{formatMeasured(measuredLatest.measured.precision_at_k)}</td><td>—</td></tr>
                                <tr><td>Recall@{measuredLatest.method.top_k}</td><td>{formatMeasured(measuredLatest.baseline.recall_at_k)}</td><td>{formatMeasured(measuredLatest.measured.recall_at_k)}</td><td>—</td></tr>
                                <tr><td>Hit rate@{measuredLatest.method.top_k}</td><td>{formatMeasured(measuredLatest.baseline.hit_rate_at_k)}</td><td>{formatMeasured(measuredLatest.measured.hit_rate_at_k)}</td><td>—</td></tr>
                                <tr><td>Cobertura do catálogo</td><td>{formatMeasured(measuredLatest.baseline.catalog_coverage)}</td><td>{formatMeasured(measuredLatest.measured.catalog_coverage)}</td><td>—</td></tr>
                                <tr><td>Latência p50</td><td>{formatMeasured(measuredLatest.baseline.latency_p50_ms, 1)} ms</td><td>{formatMeasured(measuredLatest.measured.latency_p50_ms, 1)} ms</td><td>—</td></tr>
                                <tr><td>Latência p95</td><td>{formatMeasured(measuredLatest.baseline.latency_p95_ms, 1)} ms</td><td>{formatMeasured(measuredLatest.measured.latency_p95_ms, 1)} ms</td><td>{formatMeasured(measuredLatest.deltas.latency_p95_overhead_percent, 1)}%</td></tr>
                                <tr><td>Latência p99</td><td>{formatMeasured(measuredLatest.baseline.latency_p99_ms, 1)} ms</td><td>{formatMeasured(measuredLatest.measured.latency_p99_ms, 1)} ms</td><td>—</td></tr>
                                <tr><td>Disponibilidade</td><td>{formatMeasured(measuredLatest.baseline.availability_percent, 1)}%</td><td>{formatMeasured(measuredLatest.measured.availability_percent, 1)}%</td><td>{formatMeasured(measuredLatest.deltas.availability_percentage_points, 1)} p.p.</td></tr>
                                <tr><td>Requisições com falha</td><td>{measuredLatest.baseline.failed_requests}</td><td>{measuredLatest.measured.failed_requests}</td><td>—</td></tr>
                                <tr><td>Qualidade dos dados</td><td>{formatMeasured(measuredLatest.data_quality.baseline.quality_score * 100, 1)}%</td><td>{formatMeasured(measuredLatest.data_quality.effective.quality_score * 100, 1)}%</td><td>—</td></tr>
                            </tbody></table>
                        </Style.MeasurementTable>
                        <Style.ObservationSummary className={measuredLatest.observability.response_applied ? 'applied' : ''}>
                            <FaShieldAlt/><div><b>{measuredLatest.observability.action}</b><span>{measuredLatest.observability.signal || 'Execução sem detector e sem resposta automática.'}</span></div>
                        </Style.ObservationSummary>
                    </Style.MeasuredDetails>
                )}
            </Style.RealLab>

            <Style.Workspace>
                <Style.ControlPanel>
                    <Style.PanelHeading>
                        <div><span>01</span><h2>Cenário</h2></div>
                        <small>Configure antes de executar</small>
                    </Style.PanelHeading>

                    <Style.Field>
                        <label htmlFor="duration">Janela de simulação</label>
                        <select id="duration" value={form.duration_minutes} onChange={event => changeDuration(event.target.value)}>
                            {[30, 60, 90, 120, 180].map(value => <option value={value} key={value}>{value} minutos</option>)}
                        </select>
                    </Style.Field>

                    <Style.Subtitle>Modelos comparados</Style.Subtitle>
                    <Style.ModelChoices>
                        {catalog.models.map(model => (
                            <button
                                type="button"
                                key={model.id}
                                className={form.models.includes(model.id) ? 'selected' : ''}
                                onClick={() => toggleModel(model.id)}
                                title={model.description}
                            >
                                <i style={{background: model.color}}/>
                                <span>{model.short_label}</span>
                                <b>{form.models.includes(model.id) ? '✓' : '+'}</b>
                            </button>
                        ))}
                    </Style.ModelChoices>

                    <Style.Subtitle>Presets</Style.Subtitle>
                    <Style.PresetGrid>
                        {Object.entries(PRESETS).map(([key, preset]) => (
                            <button type="button" key={key} onClick={() => applyPreset(preset)}>{preset.label}</button>
                        ))}
                    </Style.PresetGrid>

                    <Style.AttackHeader>
                        <Style.Subtitle>Ataques no tempo</Style.Subtitle>
                        <button type="button" onClick={addAttack}><FaPlus/> Adicionar</button>
                    </Style.AttackHeader>

                    <Style.AttackList>
                        {form.attacks.length === 0 && <Style.EmptyAttacks>Nenhum ataque: o cenário mede apenas o baseline e o overhead.</Style.EmptyAttacks>}
                        {form.attacks.map((attack, index) => {
                            const definition = attackMap[attack.attack_type]
                            return (
                                <Style.AttackCard key={attack.attack_id} style={{'--attack-color': definition?.color || '#ef4444'}}>
                                    <div className="attack-title">
                                        <FaBolt/>
                                        <select value={attack.attack_type} onChange={event => updateAttack(index, 'attack_type', event.target.value)} aria-label={`Tipo do ataque ${index + 1}`}>
                                            {catalog.attacks.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                                        </select>
                                        <button type="button" onClick={() => removeAttack(index)} aria-label={`Remover ataque ${index + 1}`}><FaTrash/></button>
                                    </div>
                                    <p>{definition?.description}</p>
                                    <div className="attack-fields">
                                        <label>Início<input type="number" min="1" max={form.duration_minutes - 1} value={attack.start_minute} onChange={event => updateAttack(index, 'start_minute', event.target.value)}/><small>min</small></label>
                                        <label>Duração<input type="number" min="1" max={form.duration_minutes - attack.start_minute} value={attack.duration_minutes} onChange={event => updateAttack(index, 'duration_minutes', event.target.value)}/><small>min</small></label>
                                    </div>
                                    <label className="intensity">
                                        <span>Intensidade <b>{Math.round(attack.intensity * 100)}%</b></span>
                                        <input type="range" min="0.05" max="1" step="0.05" value={attack.intensity} onChange={event => updateAttack(index, 'intensity', event.target.value)}/>
                                    </label>
                                </Style.AttackCard>
                            )
                        })}
                    </Style.AttackList>

                    {error && <Style.Error role="alert">{error}</Style.Error>}
                    <Style.RunButton type="button" disabled={loading} onClick={() => runSimulation()}>
                        {loading ? <span className="spinner"/> : <FaPlay/>}
                        {loading ? 'Simulando…' : 'Executar comparação'}
                    </Style.RunButton>
                </Style.ControlPanel>

                <Style.Results>
                    {result && (
                        <>
                            <Style.ResultHeader>
                                <div>
                                    <span>02 · RESULTADOS</span>
                                    <h2>Impacto ao longo do tempo</h2>
                                    <p>Selecione uma métrica e um modelo para inspecionar as duas condições.</p>
                                </div>
                                <div className="seed">SEED <b>{result.seed}</b></div>
                            </Style.ResultHeader>

                            <Style.KpiGrid>
                                <Style.KpiCard className="green">
                                    <span>Maior redução da perda</span>
                                    <strong>{bestReduction?.quality_loss_reduction_percent?.toFixed(1) || '0.0'}%</strong>
                                    <small>{bestReduction?.model_label}</small>
                                </Style.KpiCard>
                                <Style.KpiCard>
                                    <span>Ataques programados</span>
                                    <strong>{result.attacks.length}</strong>
                                    <small>{result.events.filter(event => event.kind === 'detection').length} detecções</small>
                                </Style.KpiCard>
                                <Style.KpiCard>
                                    <span>MTTD do modelo em foco</span>
                                    <strong>{focusedWith?.summary.mean_detection_minutes ?? '—'}<em> min</em></strong>
                                    <small>média sintética</small>
                                </Style.KpiCard>
                                <Style.KpiCard>
                                    <span>Overhead instrumentado</span>
                                    <strong>{focusedWith?.summary.instrumentation_latency_overhead_percent ?? 0}<em>%</em></strong>
                                    <small>latência base</small>
                                </Style.KpiCard>
                            </Style.KpiGrid>

                            <Timeline attacks={result.attacks} duration={result.duration_minutes}/>

                            <Style.SelectorRow>
                                <div>
                                    <label>Métrica visualizada</label>
                                    <Style.MetricTabs>
                                        {catalog.metrics.map(option => (
                                            <button type="button" key={option.id} className={selectedMetric === option.id ? 'active' : ''} onClick={() => setSelectedMetric(option.id)}>{option.short_label}</button>
                                        ))}
                                    </Style.MetricTabs>
                                </div>
                                <div>
                                    <label>Modelo em foco</label>
                                    <Style.FocusTabs>
                                        {result.comparison.map(item => (
                                            <button type="button" key={item.model} className={focusedModel === item.model ? 'active' : ''} onClick={() => setFocusedModel(item.model)}>
                                                <i style={{background: item.color}}/>{modelMap[item.model]?.short_label}
                                            </button>
                                        ))}
                                    </Style.FocusTabs>
                                </div>
                            </Style.SelectorRow>

                            <Style.ChartHeader>
                                <div>
                                    <h3>{metric?.label} · {modelMap[focusedModel]?.label}</h3>
                                    <p>{metric?.description}</p>
                                </div>
                                <div className="direction">Melhor resultado <b>{metric?.direction === 'lower' ? '↓' : '↑'}</b></div>
                            </Style.ChartHeader>
                            <SimulationChart
                                withoutDefense={focusedWithout}
                                withDefense={focusedWith}
                                metricId={selectedMetric}
                                metric={metric}
                                attacks={result.attacks}
                                events={result.events}
                                duration={result.duration_minutes}
                            />

                            <Style.SectionTitle>
                                <div><span>03</span><h2>Comparação entre modelos</h2></div>
                                <p>A perda acumulada integra a queda de NDCG ao longo do tempo.</p>
                            </Style.SectionTitle>
                            <Style.ComparisonGrid>
                                {result.comparison.map(item => {
                                    const reduction = Number(item.quality_loss_reduction_percent || 0)
                                    return (
                                        <Style.ComparisonCard key={item.model}>
                                            <div className="model-name"><i style={{background: item.color}}/><strong>{item.model_label}</strong><b>{reduction.toFixed(1)}%</b></div>
                                            <div className="bar"><span style={{width: `${Math.max(2, reduction)}%`}}/></div>
                                            <div className="values">
                                                <span>Sem defesa <b>{item.without_defense.accumulated_quality_loss.toFixed(3)}</b></span>
                                                <span>Com defesa <b>{item.with_defense?.accumulated_quality_loss.toFixed(3)}</b></span>
                                            </div>
                                        </Style.ComparisonCard>
                                    )
                                })}
                            </Style.ComparisonGrid>

                            <Style.TableWrap>
                                <table>
                                    <thead><tr><th>Modelo</th><th>NDCG médio sem defesa</th><th>NDCG médio com defesa</th><th>Mínimo com defesa</th><th>Tempo abaixo do SLO</th><th>Latência p95 média</th></tr></thead>
                                    <tbody>
                                        {result.comparison.map(item => (
                                            <tr key={item.model}>
                                                <td><i style={{background: item.color}}/>{item.model_label}</td>
                                                <td>{item.without_defense.average_ndcg_at_10.toFixed(3)}</td>
                                                <td className="positive">{item.with_defense?.average_ndcg_at_10.toFixed(3)}</td>
                                                <td>{item.with_defense?.minimum_ndcg_at_10.toFixed(3)}</td>
                                                <td>{item.with_defense?.minutes_below_quality_slo} min</td>
                                                <td>{formatMetric(item.with_defense?.average_latency_p95_ms, metricMap.latency_p95_ms)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </Style.TableWrap>

                            <Style.SectionTitle>
                                <div><span>04</span><h2>Eventos observados</h2></div>
                                <p>Os marcadores ligam o ataque ao momento de detecção e encerramento.</p>
                            </Style.SectionTitle>
                            <Style.EventGrid>
                                {result.events.map((event, index) => (
                                    <Style.EventCard key={`${event.attack_id}-${event.kind}-${index}`} className={event.kind}>
                                        <div className="time"><FaClock/><b>{event.time}</b><small>min</small></div>
                                        <i style={{background: event.color}}/>
                                        <div><strong>{event.label}</strong><span>{event.kind === 'detection' ? 'Sinal convertido em resposta' : 'Evento do cenário'}</span></div>
                                    </Style.EventCard>
                                ))}
                            </Style.EventGrid>
                        </>
                    )}
                </Style.Results>
            </Style.Workspace>
            <Footer/>
        </Style.Page>
    )
}

export default Simulation
