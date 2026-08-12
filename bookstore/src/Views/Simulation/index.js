import { useEffect, useMemo, useState } from 'react'
import {
    FaBolt,
    FaChartLine,
    FaCheckCircle,
    FaClock,
    FaExclamationTriangle,
    FaFlask,
    FaPlay,
    FaPlus,
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

    useEffect(() => {
        if (!isAdmin) return undefined
        let active = true
        async function initialize() {
            try {
                setLoading(true)
                const response = await api.get('/admin/experiments/catalog')
                if (!active) return
                setCatalog(response.data)
                setForm(response.data.default_request)
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

    if (!catalog || !form) {
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

    return (
        <Style.Page>
            <Header admin/>
            <Style.Hero>
                <div className="eyebrow"><FaFlask/> SIMULAÇÃO EXPLORATÓRIA</div>
                <div className="hero-grid">
                    <div>
                        <h1>Laboratório de Resiliência</h1>
                        <p>Programe ataques no tempo, compare recomendadores e observe a diferença entre operar sem defesa e responder com sinais de observabilidade.</p>
                    </div>
                    <div className="hero-status">
                        <span><FaCheckCircle/> Motor determinístico</span>
                        <span><FaShieldAlt/> Comparação pareada</span>
                        <span><FaChartLine/> Sete métricas temporais</span>
                    </div>
                </div>
                <div className="disclaimer"><FaExclamationTriangle/> {catalog.disclaimer}</div>
            </Style.Hero>

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

