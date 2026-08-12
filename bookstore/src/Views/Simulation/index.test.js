import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import api from '../../Services/service'
import Simulation from './index'

jest.mock('../../Services/service', () => ({
    __esModule: true,
    default: {get: jest.fn(), post: jest.fn()},
}))

const catalog = {
    kind: 'exploratory_simulation',
    disclaimer: 'Valores sintéticos. Não representam resultados medidos.',
    models: [{
        id: 'hybrid',
        label: 'Híbrido',
        short_label: 'Híbrido',
        description: 'Modelo híbrido',
        color: '#10b981',
    }],
    attacks: [{
        id: 'push_attack',
        label: 'Push attack',
        description: 'Promoção artificial',
        color: '#f97316',
    }],
    metrics: [{
        id: 'ndcg_at_10',
        label: 'NDCG@10',
        short_label: 'NDCG',
        description: 'Qualidade do ranking',
        unit: 'ratio',
        direction: 'higher',
    }, {
        id: 'latency_p95_ms',
        label: 'Latência p95',
        short_label: 'Latência',
        description: 'Tempo de resposta',
        unit: 'milliseconds',
        direction: 'lower',
    }],
    default_request: {
        duration_minutes: 20,
        step_minutes: 1,
        seed: 42,
        models: ['hybrid'],
        compare_defense: true,
        attacks: [{
            attack_id: 'push-1',
            attack_type: 'push_attack',
            start_minute: 5,
            duration_minutes: 8,
            intensity: 0.6,
        }],
    },
}

const summaryWithout = {
    average_ndcg_at_10: 0.62,
    minimum_ndcg_at_10: 0.40,
    average_precision_at_10: 0.45,
    average_recall_at_10: 0.41,
    average_catalog_coverage: 0.70,
    average_latency_p95_ms: 44,
    minimum_availability_percent: 99.2,
    accumulated_quality_loss: 2.4,
    minutes_below_quality_slo: 8,
    quality_slo: 0.71,
    detections: 0,
    mean_detection_minutes: null,
    instrumentation_latency_overhead_percent: 0,
}

const summaryWith = {
    ...summaryWithout,
    average_ndcg_at_10: 0.72,
    minimum_ndcg_at_10: 0.61,
    average_latency_p95_ms: 45.8,
    accumulated_quality_loss: 0.8,
    minutes_below_quality_slo: 2,
    detections: 1,
    mean_detection_minutes: 4,
    instrumentation_latency_overhead_percent: 4,
}

const pointsWithout = [
    {time: 0, ndcg_at_10: 0.79, latency_p95_ms: 44},
    {time: 20, ndcg_at_10: 0.40, latency_p95_ms: 60},
]
const pointsWith = [
    {time: 0, ndcg_at_10: 0.79, latency_p95_ms: 45.8},
    {time: 20, ndcg_at_10: 0.70, latency_p95_ms: 48},
]

const simulation = {
    kind: 'exploratory_simulation',
    disclaimer: catalog.disclaimer,
    duration_minutes: 20,
    step_minutes: 1,
    seed: 42,
    attacks: [{
        ...catalog.default_request.attacks[0],
        label: 'Push attack',
        color: '#f97316',
        detection_minute: 9,
    }],
    events: [
        {time: 5, kind: 'attack_start', attack_id: 'push-1', label: 'Início: Push attack', color: '#f97316'},
        {time: 9, kind: 'detection', attack_id: 'push-1', label: 'Detectado: Push attack', color: '#10b981'},
    ],
    series: [
        {model: 'hybrid', model_label: 'Híbrido', color: '#10b981', defended: false, points: pointsWithout, summary: summaryWithout},
        {model: 'hybrid', model_label: 'Híbrido', color: '#10b981', defended: true, points: pointsWith, summary: summaryWith},
    ],
    comparison: [{
        model: 'hybrid',
        model_label: 'Híbrido',
        color: '#10b981',
        without_defense: summaryWithout,
        with_defense: summaryWith,
        quality_loss_reduction_percent: 66.67,
    }],
}

beforeEach(() => {
    jest.clearAllMocks()
    sessionStorage.clear()
})

test('exibe restrição quando o usuário não é administrador', () => {
    render(<Simulation/>)
    expect(screen.getByRole('heading', {name: /Laboratório restrito/i})).toBeInTheDocument()
    expect(api.get).not.toHaveBeenCalled()
})

test('carrega o cenário, deixa claro que é sintético e executa nova comparação', async () => {
    sessionStorage.setItem('isAdmin', 'true')
    api.get.mockResolvedValue({data: catalog})
    api.post.mockResolvedValue({data: simulation})

    render(<Simulation/>)

    expect(await screen.findByRole('heading', {name: /Laboratório de Resiliência/i})).toBeInTheDocument()
    expect(screen.getByText(/Não representam resultados medidos/i)).toBeInTheDocument()
    expect(screen.getByRole('img', {name: /NDCG@10 ao longo da simulação/i})).toBeInTheDocument()
    expect(screen.getAllByText('66.7%')).toHaveLength(2)

    fireEvent.click(screen.getByRole('button', {name: /Executar comparação/i}))
    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2))
    expect(api.post.mock.calls[1][0]).toBe('/admin/experiments/simulate')
})
