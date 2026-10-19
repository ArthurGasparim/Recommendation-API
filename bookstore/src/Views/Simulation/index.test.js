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

const measuredCatalog = {
    kind: 'measured_experiment',
    disclaimer: 'Métricas medidas sobre uma cópia controlada do snapshot real.',
    models: [{id: 'item_item', label: 'Colaborativo item-item', description: 'Modelo real'}],
    attacks: [{id: 'push_attack', label: 'Push attack', description: 'Ataque controlado'}],
    default_request: {
        model: 'item_item',
        attack_type: 'push_attack',
        with_observability: true,
        intensity: 0.05,
        seed: 42,
        sample_users: 20,
        top_k: 10,
        target_book_id: null,
    },
    suite: {
        models: 3,
        attacks: 6,
        comparisons: 18,
        scenario_runs: 36,
        default_request: {
            intensity: 0.05,
            seed: 42,
            sample_users: 20,
            top_k: 10,
            target_book_id: null,
        },
    },
}

const measuredMetrics = {
    kind: 'measured_metrics',
    dataset: {books: 10000, ratings: 979478, tags: 34252, book_tags: 999904, to_read: 912705},
    latest: null,
    latest_suite: null,
    runs: [],
}

const completedJob = {
    id: 'job-1',
    kind: 'real_experiment',
    status: 'completed',
    progress: 100,
    message: 'Experimento medido concluído',
    result: {kind: 'measured_experiment'},
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
    api.get.mockImplementation(path => {
        if (path === '/admin/experiments/catalog') return Promise.resolve({data: catalog})
        if (path === '/admin/experiments/real/catalog') return Promise.resolve({data: measuredCatalog})
        if (path === '/admin/experiments/real/metrics') return Promise.resolve({data: measuredMetrics})
        return Promise.resolve({data: completedJob})
    })
    api.post.mockImplementation(path => {
        if (path === '/admin/experiments/simulate') return Promise.resolve({data: simulation})
        return Promise.resolve({data: {...completedJob, status: 'queued', progress: 0}})
    })

    render(<Simulation/>)

    expect(await screen.findByRole('heading', {name: /Laboratório de Resiliência/i})).toBeInTheDocument()
    expect(screen.getByText(/Não representam resultados medidos/i)).toBeInTheDocument()
    expect(screen.getByRole('button', {name: /Carregar dados dos CSVs/i})).toBeInTheDocument()
    expect(screen.getByRole('button', {name: /Executar ataque/i})).toBeEnabled()
    expect(screen.getByRole('img', {name: /NDCG@10 ao longo da simulação/i})).toBeInTheDocument()
    expect(screen.getAllByText('66.7%')).toHaveLength(2)

    fireEvent.click(screen.getByRole('button', {name: /Executar comparação/i}))
    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2))
    expect(api.post.mock.calls[1][0]).toBe('/admin/experiments/simulate')
})

test('executa ataque medido e acompanha a tarefa persistida', async () => {
    sessionStorage.setItem('isAdmin', 'true')
    let jobPolls = 0
    api.get.mockImplementation(path => {
        if (path === '/admin/experiments/catalog') return Promise.resolve({data: catalog})
        if (path === '/admin/experiments/real/catalog') return Promise.resolve({data: measuredCatalog})
        if (path === '/admin/experiments/real/metrics') return Promise.resolve({data: measuredMetrics})
        if (path === '/admin/jobs/job-1') {
            jobPolls += 1
            if (jobPolls === 1) return Promise.reject({response: {status: 503}})
            return Promise.resolve({data: completedJob})
        }
        return Promise.reject(new Error(`GET inesperado: ${path}`))
    })
    api.post.mockImplementation(path => {
        if (path === '/admin/experiments/simulate') return Promise.resolve({data: simulation})
        if (path === '/admin/experiments/real/run') {
            return Promise.resolve({data: {...completedJob, status: 'queued', progress: 0}})
        }
        return Promise.reject(new Error(`POST inesperado: ${path}`))
    })

    render(<Simulation/>)

    const button = await screen.findByRole('button', {name: /Executar ataque/i})
    fireEvent.click(button)

    await waitFor(() => expect(api.post).toHaveBeenCalledWith(
        '/admin/experiments/real/run',
        measuredCatalog.default_request,
    ))
    await waitFor(() => expect(jobPolls).toBe(2), {timeout: 3000})
    expect(await screen.findByText(/Experimento medido concluído/i, {}, {timeout: 3000})).toBeInTheDocument()
})

test('executa a bateria completa e baixa a planilha XLSX', async () => {
    sessionStorage.setItem('isAdmin', 'true')
    const suiteJob = {
        id: 'suite-1',
        kind: 'real_experiment_suite',
        status: 'completed',
        progress: 100,
        message: 'Bateria completa concluída; planilha disponível',
        result: {kind: 'measured_experiment_suite'},
    }
    const createObjectURL = jest.fn(() => 'blob:planilha')
    const revokeObjectURL = jest.fn()
    Object.defineProperty(window.URL, 'createObjectURL', {value: createObjectURL, configurable: true})
    Object.defineProperty(window.URL, 'revokeObjectURL', {value: revokeObjectURL, configurable: true})
    const clickSpy = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    api.get.mockImplementation((path, config) => {
        if (path === '/admin/experiments/catalog') return Promise.resolve({data: catalog})
        if (path === '/admin/experiments/real/catalog') return Promise.resolve({data: measuredCatalog})
        if (path === '/admin/experiments/real/metrics') return Promise.resolve({data: measuredMetrics})
        if (path === '/admin/jobs/suite-1') return Promise.resolve({data: suiteJob})
        if (path === '/admin/experiments/real/suite/suite-1/xlsx') {
            expect(config).toEqual({responseType: 'blob'})
            return Promise.resolve({data: new Blob(['xlsx'])})
        }
        return Promise.reject(new Error(`GET inesperado: ${path}`))
    })
    api.post.mockImplementation(path => {
        if (path === '/admin/experiments/simulate') return Promise.resolve({data: simulation})
        if (path === '/admin/experiments/real/suite') {
            return Promise.resolve({data: {...suiteJob, status: 'queued', progress: 0}})
        }
        return Promise.reject(new Error(`POST inesperado: ${path}`))
    })

    render(<Simulation/>)
    const button = await screen.findByRole('button', {name: /Testar todos e gerar XLSX/i})
    fireEvent.click(button)

    await waitFor(() => expect(api.post).toHaveBeenCalledWith(
        '/admin/experiments/real/suite',
        measuredCatalog.suite.default_request,
    ))
    await waitFor(() => expect(createObjectURL).toHaveBeenCalledTimes(1))
    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:planilha')
    expect(await screen.findByText(/Bateria completa concluída/i)).toBeInTheDocument()
    clickSpy.mockRestore()
})
