import { useMemo, useState } from 'react'
import * as Style from './style'

const WIDTH = 960
const HEIGHT = 390
const MARGIN = { top: 28, right: 26, bottom: 52, left: 70 }

function formatMetric(value, metric) {
    if (!Number.isFinite(Number(value))) return '—'
    if (metric?.unit === 'milliseconds') return `${Number(value).toFixed(1)} ms`
    if (metric?.unit === 'percent') return `${Number(value).toFixed(2)}%`
    return Number(value).toFixed(3)
}

function makePath(points, metricId, xScale, yScale) {
    return points.map((point, index) => {
        const command = index === 0 ? 'M' : 'L'
        return `${command}${xScale(point.time).toFixed(2)},${yScale(point[metricId]).toFixed(2)}`
    }).join(' ')
}

function SimulationChart({
    withoutDefense,
    withDefense,
    metricId,
    metric,
    attacks,
    events,
    duration,
}) {
    const [hoverIndex, setHoverIndex] = useState(null)
    const allPoints = useMemo(() => [
        ...(withoutDefense?.points || []),
        ...(withDefense?.points || []),
    ], [withoutDefense, withDefense])

    if (!withoutDefense || !allPoints.length) return null

    const values = allPoints.map(point => Number(point[metricId])).filter(Number.isFinite)
    let minimum = Math.min(...values)
    let maximum = Math.max(...values)
    const spread = Math.max(maximum - minimum, metric?.unit === 'ratio' ? 0.08 : 1)

    if (metric?.unit === 'ratio') {
        minimum = Math.max(0, minimum - spread * 0.18)
        maximum = Math.min(1, maximum + spread * 0.18)
    } else if (metric?.unit === 'percent') {
        minimum = Math.max(0, minimum - spread * 0.12)
        maximum = Math.min(100, maximum + spread * 0.12)
    } else {
        minimum = Math.max(0, minimum - spread * 0.08)
        maximum += spread * 0.12
    }
    if (maximum === minimum) maximum = minimum + 1

    const chartWidth = WIDTH - MARGIN.left - MARGIN.right
    const chartHeight = HEIGHT - MARGIN.top - MARGIN.bottom
    const xScale = value => MARGIN.left + (Number(value) / duration) * chartWidth
    const yScale = value => MARGIN.top + (1 - (Number(value) - minimum) / (maximum - minimum)) * chartHeight
    const yTicks = Array.from({length: 5}, (_, index) => minimum + ((maximum - minimum) * index / 4))
    const xTicks = Array.from({length: 7}, (_, index) => Math.round(duration * index / 6))
    const withoutPath = makePath(withoutDefense.points, metricId, xScale, yScale)
    const withPath = withDefense ? makePath(withDefense.points, metricId, xScale, yScale) : null
    const points = withoutDefense.points
    const activeIndex = hoverIndex === null ? points.length - 1 : hoverIndex
    const activeWithout = points[activeIndex]
    const activeWith = withDefense?.points[activeIndex]
    const activeX = xScale(activeWithout.time)

    function handlePointer(event) {
        const bounds = event.currentTarget.getBoundingClientRect()
        const relativeX = (event.clientX - bounds.left) / bounds.width * WIDTH
        const time = Math.max(0, Math.min(duration, (relativeX - MARGIN.left) / chartWidth * duration))
        let nearest = 0
        let distance = Infinity
        points.forEach((point, index) => {
            const candidate = Math.abs(point.time - time)
            if (candidate < distance) {
                nearest = index
                distance = candidate
            }
        })
        setHoverIndex(nearest)
    }

    return (
        <Style.ChartFrame>
            <Style.Legend>
                <span><i className="without"/> Sem defesa</span>
                {withDefense && <span><i className="with"/> Com resposta observável</span>}
                <span><i className="detection"/> Detecção</span>
            </Style.Legend>
            <Style.SvgWrap>
                <svg
                    viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
                    role="img"
                    aria-label={`${metric?.label || metricId} ao longo da simulação`}
                    onMouseMove={handlePointer}
                    onMouseLeave={() => setHoverIndex(null)}
                >
                    <defs>
                        <linearGradient id="withGradient" x1="0" x2="0" y1="0" y2="1">
                            <stop offset="0%" stopColor="#34d399" stopOpacity="0.22"/>
                            <stop offset="100%" stopColor="#34d399" stopOpacity="0"/>
                        </linearGradient>
                        <filter id="lineGlow" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="2.2" result="blur"/>
                            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                        </filter>
                    </defs>

                    {attacks.map(attack => {
                        const start = xScale(attack.start_minute)
                        const end = xScale(attack.start_minute + attack.duration_minutes)
                        return (
                            <g key={attack.attack_id}>
                                <rect
                                    x={start}
                                    y={MARGIN.top}
                                    width={Math.max(2, end - start)}
                                    height={chartHeight}
                                    fill={attack.color}
                                    opacity="0.09"
                                />
                                <line x1={start} x2={start} y1={MARGIN.top} y2={MARGIN.top + chartHeight} stroke={attack.color} strokeWidth="1.5" opacity="0.7"/>
                                <text x={start + 6} y={MARGIN.top + 15} fill={attack.color} fontSize="11" fontWeight="700">
                                    {attack.label}
                                </text>
                            </g>
                        )
                    })}

                    {yTicks.map(tick => (
                        <g key={`y-${tick}`}>
                            <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={yScale(tick)} y2={yScale(tick)} stroke="#dbe5ef" strokeDasharray="4 6"/>
                            <text x={MARGIN.left - 12} y={yScale(tick) + 4} textAnchor="end" fill="#64748b" fontSize="11">
                                {formatMetric(tick, metric)}
                            </text>
                        </g>
                    ))}
                    {xTicks.map(tick => (
                        <g key={`x-${tick}`}>
                            <line x1={xScale(tick)} x2={xScale(tick)} y1={MARGIN.top} y2={MARGIN.top + chartHeight} stroke="#eef2f7"/>
                            <text x={xScale(tick)} y={HEIGHT - 20} textAnchor="middle" fill="#64748b" fontSize="11">{tick} min</text>
                        </g>
                    ))}

                    {withPath && (
                        <>
                            <path d={`${withPath} L${xScale(points[points.length - 1].time)},${MARGIN.top + chartHeight} L${xScale(points[0].time)},${MARGIN.top + chartHeight} Z`} fill="url(#withGradient)"/>
                            <path d={withPath} fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" filter="url(#lineGlow)"/>
                        </>
                    )}
                    <path d={withoutPath} fill="none" stroke="#f43f5e" strokeWidth="2.5" strokeDasharray="7 5" strokeLinecap="round" strokeLinejoin="round"/>

                    {events.filter(event => event.kind === 'detection').map(event => (
                        <g key={`${event.attack_id}-${event.time}`}>
                            <line x1={xScale(event.time)} x2={xScale(event.time)} y1={MARGIN.top} y2={MARGIN.top + chartHeight} stroke="#059669" strokeWidth="1.5" strokeDasharray="3 4"/>
                            <circle cx={xScale(event.time)} cy={MARGIN.top + chartHeight + 1} r="4" fill="#059669"/>
                        </g>
                    ))}

                    {hoverIndex !== null && (
                        <>
                            <line x1={activeX} x2={activeX} y1={MARGIN.top} y2={MARGIN.top + chartHeight} stroke="#0f172a" strokeWidth="1" opacity="0.25"/>
                            <circle cx={activeX} cy={yScale(activeWithout[metricId])} r="5" fill="#fff" stroke="#f43f5e" strokeWidth="3"/>
                            {activeWith && <circle cx={activeX} cy={yScale(activeWith[metricId])} r="5" fill="#fff" stroke="#10b981" strokeWidth="3"/>}
                        </>
                    )}
                    <rect x={MARGIN.left} y={MARGIN.top} width={chartWidth} height={chartHeight} fill="transparent"/>
                </svg>
                {hoverIndex !== null && (
                    <Style.Tooltip style={{left: `${Math.min(82, Math.max(8, activeX / WIDTH * 100))}%`}}>
                        <strong>Minuto {activeWithout.time}</strong>
                        <span><i className="without"/>Sem defesa <b>{formatMetric(activeWithout[metricId], metric)}</b></span>
                        {activeWith && <span><i className="with"/>Com defesa <b>{formatMetric(activeWith[metricId], metric)}</b></span>}
                    </Style.Tooltip>
                )}
            </Style.SvgWrap>
        </Style.ChartFrame>
    )
}

export { formatMetric }
export default SimulationChart

