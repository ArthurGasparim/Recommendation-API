import styled from 'styled-components'

export const Page = styled.div`
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background:
        radial-gradient(circle at 80% 10%, rgba(14, 165, 233, 0.08), transparent 28%),
        #f3f7fa;
    color: #0f172a;
`

export const Hero = styled.section`
    position: relative;
    overflow: hidden;
    padding: 48px max(24px, calc((100vw - 1440px) / 2));
    color: #fff;
    background:
        radial-gradient(circle at 78% 20%, rgba(56, 189, 248, 0.24), transparent 25%),
        radial-gradient(circle at 18% 110%, rgba(16, 185, 129, 0.18), transparent 30%),
        linear-gradient(125deg, #071426 0%, #0a2440 55%, #0b3d52 100%);

    &::after {
        content: '';
        position: absolute;
        inset: 0;
        opacity: 0.12;
        background-image: linear-gradient(rgba(255,255,255,.12) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.12) 1px, transparent 1px);
        background-size: 42px 42px;
        pointer-events: none;
    }

    > * { position: relative; z-index: 1; }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 11px;
        border: 1px solid rgba(125, 211, 252, .35);
        border-radius: 999px;
        background: rgba(14, 165, 233, .12);
        color: #7dd3fc;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .12em;
    }

    .hero-grid {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 40px;
        align-items: end;
        margin-top: 18px;
    }

    h1 { font-size: clamp(2.2rem, 4vw, 4rem); letter-spacing: -.045em; line-height: 1; margin: 0; }
    p { max-width: 760px; margin-top: 18px; color: #bfd1e2; font-size: 1.04rem; line-height: 1.65; }

    .hero-status {
        display: grid;
        gap: 8px;
        min-width: 245px;
        padding: 15px;
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 16px;
        background: rgba(6, 17, 32, .45);
        backdrop-filter: blur(10px);

        span { display: flex; align-items: center; gap: 9px; color: #dbeafe; font-size: .8rem; }
        svg { color: #34d399; }
    }

    .disclaimer {
        display: flex;
        align-items: center;
        gap: 9px;
        margin-top: 30px;
        padding-top: 18px;
        border-top: 1px solid rgba(255,255,255,.1);
        color: #fcd34d;
        font-size: .78rem;
    }

    @media (max-width: 800px) {
        .hero-grid { grid-template-columns: 1fr; }
        .hero-status { display: none; }
    }
`

export const RealLab = styled.section`
    width: min(1500px, calc(100% - 48px));
    margin: 28px auto 0;
    padding: 26px;
    border: 1px solid #cbdfe9;
    border-radius: 22px;
    background: rgba(255,255,255,.98);
    box-shadow: 0 18px 42px rgba(15,35,55,.07);
    @media (max-width: 600px) { width: calc(100% - 24px); padding: 16px; }
`

export const RealHeader = styled.div`
    display: flex; align-items: start; justify-content: space-between; gap: 24px;
    padding-bottom: 20px; border-bottom: 1px solid #e2e8f0;
    span { color: #047857; font-size: .68rem; font-weight: 900; letter-spacing: .12em; }
    h2 { margin: 5px 0 5px; color: #0f172a; font-size: clamp(1.4rem, 2.4vw, 2rem); }
    p { color: #64748b; font-size: .78rem; line-height: 1.5; }
    > button { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; padding: 11px 14px; border: 1px solid #a7f3d0; border-radius: 10px; background: #ecfdf5; color: #047857; font-weight: 800; }
    > button:disabled { opacity: .6; }
    @media (max-width: 700px) { flex-direction: column; }
`

export const RealActions = styled.div`
    display: grid; grid-template-columns: .82fr 1.55fr 1fr; gap: 14px; margin-top: 20px;
    @media (max-width: 1050px) { grid-template-columns: 1fr 1fr; }
    @media (max-width: 680px) { grid-template-columns: 1fr; }
`

export const SuitePanel = styled.div`
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto auto;
    align-items: center;
    gap: 18px;
    margin-top: 16px;
    padding: 18px;
    border: 1px solid #bbf7d0;
    border-radius: 15px;
    background: linear-gradient(110deg, #f0fdf4, #f8fafc 58%, #eff6ff);

    .suite-icon {
        display: grid;
        place-items: center;
        width: 46px;
        height: 46px;
        border-radius: 12px;
        background: #047857;
        color: #fff;
        font-size: 1.2rem;
        box-shadow: 0 8px 18px rgba(4,120,87,.2);
    }
    .suite-copy { min-width: 0; }
    .suite-copy > span { color: #047857; font-size: .58rem; font-weight: 900; letter-spacing: .12em; }
    .suite-copy h3 { margin: 4px 0; color: #0f172a; font-size: .9rem; }
    .suite-copy p { max-width: 720px; color: #64748b; font-size: .65rem; line-height: 1.5; }
    .suite-stats {
        display: grid;
        grid-template-columns: auto auto;
        align-items: baseline;
        gap: 2px 7px;
        padding: 9px 13px;
        border-left: 1px solid #dbe6df;
    }
    .suite-stats b { color: #065f46; font-size: 1rem; text-align: right; }
    .suite-stats span { color: #64748b; font-size: .57rem; }
    .suite-actions { display: grid; gap: 7px; min-width: 210px; }
    .suite-actions button {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        min-height: 38px;
        padding: 8px 12px;
        border-radius: 9px;
        font-size: .65rem;
        font-weight: 800;
    }
    .run-suite { border: 0; background: linear-gradient(135deg, #047857, #0369a1); color: #fff; }
    .download-suite { border: 1px solid #86efac; background: #fff; color: #047857; }
    .suite-actions button:disabled { opacity: .55; cursor: not-allowed; }

    @media (max-width: 1050px) { grid-template-columns: auto 1fr auto; .suite-actions { grid-column: 2 / -1; } }
    @media (max-width: 680px) {
        grid-template-columns: auto 1fr;
        .suite-stats { grid-column: 1 / -1; border-left: 0; border-top: 1px solid #dbe6df; }
        .suite-actions { grid-column: 1 / -1; }
    }
`

export const RealCard = styled.div`
    display: flex; flex-direction: column; min-width: 0; padding: 17px;
    border: 1px solid #e2e8f0; border-radius: 15px; background: #f8fafc;
    .card-title { display: flex; align-items: start; gap: 10px; color: #0369a1; }
    .card-title > svg { margin-top: 2px; font-size: 1rem; }
    .card-title div { display: grid; gap: 3px; }
    .card-title b { color: #0f172a; font-size: .82rem; }
    .card-title small { color: #64748b; font-size: .62rem; line-height: 1.35; }
    .dataset-counts { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 19px 0; }
    .dataset-counts span { padding: 10px; border-radius: 9px; background: #fff; color: #64748b; font-size: .61rem; }
    .dataset-counts b { display: block; color: #0f172a; font-size: 1rem; }
    > button { display: flex; align-items: center; justify-content: center; gap: 7px; min-height: 39px; margin-top: auto; border: 1px solid #cbd5e1; border-radius: 9px; background: #fff; color: #334155; font-size: .7rem; font-weight: 800; }
    > button.primary { border: 0; background: linear-gradient(135deg, #0369a1, #047857); color: #fff; }
    > button.attack { margin-top: 13px; }
    > button:disabled { opacity: .55; cursor: not-allowed; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 14px; }
    .form-grid label { display: grid; gap: 4px; color: #64748b; font-size: .59rem; font-weight: 800; }
    select, input[type='number'] { min-width: 0; width: 100%; padding: 8px; border: 1px solid #d8e2e9; border-radius: 8px; background: #fff; color: #0f172a; font-size: .67rem; }
    .real-intensity { display: grid; gap: 5px; margin-top: 11px; color: #64748b; font-size: .62rem; font-weight: 800; }
    .real-intensity span { display: flex; justify-content: space-between; }
    .real-intensity b { color: #0369a1; }
    .real-intensity input { width: 100%; accent-color: #0369a1; }
`

export const ModeToggle = styled.div`
    display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 10px;
    button { display: flex; align-items: center; justify-content: center; gap: 5px; padding: 8px; border: 1px solid #dce4ea; border-radius: 8px; background: #fff; color: #64748b; font-size: .61rem; font-weight: 800; }
    button.active.danger { border-color: #fecdd3; background: #fff1f2; color: #be123c; }
    button.active.safe { border-color: #a7f3d0; background: #ecfdf5; color: #047857; }
`

export const MiniMetrics = styled.div`
    display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin: 15px 0;
    span { padding: 9px; border: 1px solid #e2e8f0; border-radius: 9px; background: #fff; }
    small { display: block; color: #64748b; font-size: .56rem; }
    b { display: block; margin-top: 4px; color: #0f172a; font-size: .82rem; }
`

export const NoMetrics = styled.div`
    margin: 16px 0; padding: 15px; border: 1px dashed #cbd5e1; border-radius: 10px;
    color: #64748b; font-size: .68rem; line-height: 1.5;
`

export const JobStatus = styled.div`
    display: grid; grid-template-columns: minmax(0,1fr) 220px; align-items: center; gap: 18px;
    margin-top: 16px; padding: 12px 14px; border: 1px solid #bae6fd; border-radius: 11px; background: #f0f9ff;
    div { display: grid; gap: 3px; }
    b { color: #0c4a6e; font-size: .7rem; }
    span { color: #64748b; font-size: .56rem; overflow-wrap: anywhere; }
    progress { width: 100%; accent-color: #0284c7; }
    &.completed { border-color: #a7f3d0; background: #ecfdf5; }
    &.failed { border-color: #fecdd3; background: #fff1f2; }
    @media (max-width: 700px) { grid-template-columns: 1fr; }
`

export const MeasuredDetails = styled.div`
    margin-top: 22px; padding-top: 22px; border-top: 1px solid #e2e8f0;
`

export const MeasurementTable = styled.div`
    overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 12px;
    table { width: 100%; border-collapse: collapse; min-width: 620px; }
    th { padding: 10px 12px; background: #f8fafc; color: #64748b; font-size: .58rem; text-transform: uppercase; text-align: left; }
    td { padding: 11px 12px; border-top: 1px solid #edf2f7; color: #334155; font-size: .68rem; }
    td:first-child { font-weight: 800; color: #0f172a; }
`

export const ObservationSummary = styled.div`
    display: flex; align-items: center; gap: 11px; margin-top: 13px; padding: 13px;
    border: 1px solid #e2e8f0; border-radius: 11px; background: #f8fafc; color: #64748b;
    > svg { font-size: 1.2rem; }
    div { display: grid; gap: 3px; }
    b { color: #334155; font-size: .72rem; }
    span { font-size: .62rem; }
    &.applied { border-color: #a7f3d0; background: #ecfdf5; color: #047857; }
    &.applied b { color: #065f46; }
`

export const Workspace = styled.main`
    width: min(1500px, 100%);
    margin: 0 auto;
    padding: 28px 24px 64px;
    display: grid;
    grid-template-columns: 350px minmax(0, 1fr);
    gap: 26px;
    align-items: start;
    flex: 1;

    @media (max-width: 1080px) { grid-template-columns: 1fr; }
    @media (max-width: 600px) { padding: 16px 12px 40px; }
`

export const ControlPanel = styled.aside`
    position: sticky;
    top: 88px;
    max-height: calc(100vh - 106px);
    overflow-y: auto;
    padding: 22px;
    border: 1px solid #dce6ee;
    border-radius: 22px;
    background: rgba(255,255,255,.96);
    box-shadow: 0 18px 42px rgba(15, 35, 55, .08);

    &::-webkit-scrollbar { width: 6px; }
    &::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }

    @media (max-width: 1080px) { position: static; max-height: none; }
`

export const PanelHeading = styled.div`
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 18px;
    border-bottom: 1px solid #e7edf3;

    div { display: flex; align-items: center; gap: 10px; }
    span { color: #0ea5e9; font-size: .68rem; font-weight: 900; letter-spacing: .12em; }
    h2 { margin: 0; font-size: 1.25rem; }
    small { color: #94a3b8; font-size: .66rem; text-align: right; }
`

export const Field = styled.div`
    margin-top: 20px;
    display: grid;
    gap: 7px;

    label { color: #475569; font-size: .75rem; font-weight: 800; }
    select {
        width: 100%; padding: 11px 12px; border: 1px solid #d6e0e9; border-radius: 10px;
        background: #f8fafc; color: #0f172a; font-weight: 700; outline: none;
        &:focus { border-color: #0ea5e9; box-shadow: 0 0 0 3px rgba(14,165,233,.1); }
    }
`

export const Subtitle = styled.h3`
    margin: 22px 0 10px;
    color: #334155;
    font-size: .77rem;
    letter-spacing: .02em;
`

export const ModelChoices = styled.div`
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 7px;

    button {
        min-width: 0;
        display: flex;
        align-items: center;
        gap: 7px;
        padding: 9px;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        background: #fff;
        color: #64748b;
        font-size: .69rem;
        text-align: left;
        transition: .2s ease;

        i { width: 7px; height: 7px; flex: 0 0 auto; border-radius: 50%; opacity: .55; }
        span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        b { margin-left: auto; color: #94a3b8; }
        &:hover { border-color: #94a3b8; transform: translateY(-1px); }
        &.selected { border-color: #b9dff1; background: #f0f9ff; color: #0f172a; font-weight: 800; }
        &.selected i { opacity: 1; box-shadow: 0 0 0 3px rgba(14,165,233,.1); }
        &.selected b { color: #0284c7; }
    }
`

export const PresetGrid = styled.div`
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 7px;

    button {
        padding: 8px 9px;
        border: 1px solid #dce6ee;
        border-radius: 9px;
        background: #f8fafc;
        color: #475569;
        font-size: .67rem;
        font-weight: 700;
        &:hover { color: #0369a1; border-color: #7dd3fc; background: #f0f9ff; }
    }
`

export const AttackHeader = styled.div`
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
    ${Subtitle} { margin-bottom: 10px; }
    > button { display: flex; gap: 5px; align-items: center; border: 0; background: transparent; color: #0284c7; font-size: .68rem; font-weight: 800; }
`

export const AttackList = styled.div`
    display: grid;
    gap: 10px;
`

export const EmptyAttacks = styled.div`
    padding: 16px;
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    color: #64748b;
    font-size: .72rem;
    line-height: 1.5;
`

export const AttackCard = styled.div`
    padding: 12px;
    border: 1px solid #e2e8f0;
    border-left: 3px solid var(--attack-color);
    border-radius: 12px;
    background: #fbfdff;

    .attack-title { display: flex; align-items: center; gap: 7px; }
    .attack-title > svg { color: var(--attack-color); font-size: .82rem; }
    .attack-title select { min-width: 0; flex: 1; border: 0; background: transparent; color: #1e293b; font-size: .74rem; font-weight: 800; outline: none; }
    .attack-title button { border: 0; background: transparent; color: #94a3b8; padding: 4px; &:hover { color: #ef4444; } }
    > p { margin: 6px 0 10px 20px; color: #94a3b8; font-size: .62rem; line-height: 1.35; }
    .attack-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .attack-fields label { position: relative; color: #64748b; font-size: .59rem; font-weight: 700; }
    .attack-fields input { width: 100%; margin-top: 4px; padding: 7px 27px 7px 8px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; color: #0f172a; font-size: .72rem; }
    .attack-fields small { position: absolute; right: 8px; bottom: 8px; color: #94a3b8; font-size: .55rem; }
    .intensity { display: block; margin-top: 10px; color: #64748b; font-size: .61rem; font-weight: 700; }
    .intensity span { display: flex; justify-content: space-between; }
    .intensity b { color: var(--attack-color); }
    .intensity input { width: 100%; height: 4px; margin-top: 8px; accent-color: var(--attack-color); }
`

export const Error = styled.div`
    margin-top: 12px; padding: 10px 12px; border-radius: 10px; background: #fff1f2; color: #be123c; font-size: .72rem;
`

export const RunButton = styled.button`
    width: 100%;
    min-height: 48px;
    margin-top: 16px;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 9px;
    border: 0;
    border-radius: 12px;
    background: linear-gradient(135deg, #0284c7, #0f766e);
    color: #fff;
    font-size: .78rem;
    font-weight: 900;
    box-shadow: 0 9px 20px rgba(2, 132, 199, .2);
    transition: .2s ease;

    &:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 13px 26px rgba(2, 132, 199, .27); }
    &:disabled { opacity: .65; cursor: wait; }
    .spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.35); border-top-color: #fff; border-radius: 50%; animation: spin .8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
`

export const Results = styled.section`
    min-width: 0;
    padding: 26px;
    border: 1px solid #dce6ee;
    border-radius: 22px;
    background: rgba(255,255,255,.97);
    box-shadow: 0 18px 42px rgba(15, 35, 55, .06);

    @media (max-width: 600px) { padding: 16px 10px; }
`

export const ResultHeader = styled.div`
    display: flex; justify-content: space-between; align-items: start; gap: 18px;
    > div > span { color: #0ea5e9; font-size: .68rem; font-weight: 900; letter-spacing: .12em; }
    h2 { margin: 5px 0 4px; font-size: clamp(1.45rem, 2.4vw, 2rem); letter-spacing: -.025em; }
    p { color: #64748b; font-size: .8rem; }
    .seed { padding: 8px 10px; border-radius: 9px; background: #eff6ff; color: #64748b; font-size: .62rem; letter-spacing: .08em; }
    .seed b { color: #0369a1; }
`

export const KpiGrid = styled.div`
    display: grid;
    grid-template-columns: repeat(4, minmax(0,1fr));
    gap: 10px;
    margin: 24px 0 18px;
    @media (max-width: 760px) { grid-template-columns: 1fr 1fr; }
`

export const KpiCard = styled.div`
    min-width: 0;
    padding: 15px;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: linear-gradient(145deg, #fff, #f8fafc);
    span { display: block; color: #64748b; font-size: .64rem; font-weight: 700; }
    strong { display: block; margin-top: 7px; color: #0f172a; font-size: 1.55rem; letter-spacing: -.04em; }
    strong em { font-size: .68rem; font-style: normal; color: #64748b; letter-spacing: 0; }
    small { display: block; margin-top: 3px; color: #94a3b8; font-size: .61rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    &.green { border-color: #a7f3d0; background: linear-gradient(145deg, #ecfdf5, #fff); }
    &.green strong { color: #047857; }
`

export const Timeline = styled.div`
    padding: 15px 17px 18px;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #f8fafc;
    .scale { display: flex; justify-content: space-between; margin-bottom: 7px; color: #94a3b8; font-size: .58rem; }
    .track { position: relative; height: 26px; border-radius: 7px; background: #e8eef4; overflow: hidden; }
    .attack { position: absolute; top: 0; bottom: 0; min-width: 3px; display: flex; align-items: center; overflow: hidden; opacity: .82; }
    .attack span { padding: 0 7px; color: #fff; font-size: .55rem; font-weight: 800; white-space: nowrap; text-shadow: 0 1px 2px rgba(0,0,0,.25); }
`

export const SelectorRow = styled.div`
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin: 24px 0 18px;
    > div { min-width: 0; }
    label { display: block; margin-bottom: 8px; color: #64748b; font-size: .66rem; font-weight: 800; }
    @media (max-width: 820px) { grid-template-columns: 1fr; }
`

export const MetricTabs = styled.div`
    display: flex; flex-wrap: wrap; gap: 5px;
    button { padding: 7px 9px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; color: #64748b; font-size: .61rem; font-weight: 700; }
    button:hover { border-color: #7dd3fc; }
    button.active { border-color: #0284c7; background: #e0f2fe; color: #075985; }
`

export const FocusTabs = styled.div`
    display: flex; flex-wrap: wrap; gap: 5px;
    button { display: flex; align-items: center; gap: 6px; padding: 7px 9px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; color: #64748b; font-size: .61rem; font-weight: 700; }
    i { width: 6px; height: 6px; border-radius: 50%; }
    button.active { border-color: #334155; background: #0f172a; color: #fff; }
`

export const ChartHeader = styled.div`
    display: flex; justify-content: space-between; align-items: end; gap: 14px; margin-bottom: 11px;
    h3 { margin: 0; font-size: 1rem; }
    p { margin-top: 4px; color: #64748b; font-size: .68rem; }
    .direction { color: #94a3b8; font-size: .61rem; white-space: nowrap; }
    .direction b { color: #059669; font-size: .9rem; }
`

export const SectionTitle = styled.div`
    display: flex; align-items: end; justify-content: space-between; gap: 20px;
    margin: 34px 0 14px; padding-top: 28px; border-top: 1px solid #e7edf3;
    > div { display: flex; align-items: center; gap: 10px; }
    span { color: #0ea5e9; font-size: .68rem; font-weight: 900; letter-spacing: .12em; }
    h2 { margin: 0; font-size: 1.15rem; }
    p { color: #94a3b8; font-size: .65rem; text-align: right; }
`

export const ComparisonGrid = styled.div`
    display: grid; grid-template-columns: repeat(auto-fit, minmax(205px, 1fr)); gap: 9px;
`

export const ComparisonCard = styled.div`
    padding: 13px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fbfdff;
    .model-name { display: flex; align-items: center; gap: 7px; }
    .model-name i { width: 7px; height: 7px; border-radius: 50%; }
    .model-name strong { font-size: .7rem; }
    .model-name b { margin-left: auto; color: #059669; font-size: .76rem; }
    .bar { height: 5px; margin: 10px 0; border-radius: 5px; background: #e2e8f0; overflow: hidden; }
    .bar span { display: block; height: 100%; border-radius: 5px; background: linear-gradient(90deg, #0ea5e9, #10b981); }
    .values { display: flex; justify-content: space-between; color: #94a3b8; font-size: .56rem; }
    .values span { display: grid; gap: 2px; }
    .values span:last-child { text-align: right; }
    .values b { color: #475569; }
`

export const TableWrap = styled.div`
    margin-top: 14px; overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 13px;
    table { width: 100%; border-collapse: collapse; min-width: 760px; }
    th { padding: 11px 12px; background: #f8fafc; color: #64748b; font-size: .57rem; text-transform: uppercase; letter-spacing: .04em; text-align: left; }
    td { padding: 12px; border-top: 1px solid #edf2f7; color: #475569; font-size: .68rem; }
    td:first-child { display: flex; align-items: center; gap: 7px; color: #0f172a; font-weight: 800; }
    td i { width: 7px; height: 7px; border-radius: 50%; }
    td.positive { color: #047857; font-weight: 900; }
`

export const EventGrid = styled.div`
    display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 8px;
`

export const EventCard = styled.div`
    display: grid; grid-template-columns: 42px 7px 1fr; align-items: center; gap: 9px;
    padding: 11px; border: 1px solid #e2e8f0; border-radius: 11px; background: #fff;
    .time { display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 4px; color: #64748b; }
    .time svg { font-size: .58rem; }
    .time b { color: #0f172a; font-size: .8rem; }
    .time small { grid-column: 2; margin-top: -4px; font-size: .52rem; }
    > i { width: 7px; height: 28px; border-radius: 5px; }
    strong { display: block; color: #334155; font-size: .66rem; }
    span { display: block; margin-top: 3px; color: #94a3b8; font-size: .56rem; }
    &.detection { border-color: #a7f3d0; background: #f0fdf4; }
`

export const AccessCard = styled.main`
    width: min(460px, calc(100% - 32px)); margin: 80px auto; padding: 42px; text-align: center;
    border: 1px solid #dce6ee; border-radius: 22px; background: #fff; box-shadow: 0 18px 42px rgba(15,35,55,.08);
    > svg { font-size: 2.5rem; color: #0284c7; }
    h1 { margin: 15px 0 8px; }
    p { color: #64748b; line-height: 1.6; }
    a { display: inline-block; margin-top: 20px; padding: 11px 18px; border-radius: 10px; background: #004299; color: #fff; font-weight: 800; }
`

export const LoadingCard = styled.main`
    flex: 1; display: grid; place-content: center; justify-items: center; gap: 12px; color: #64748b;
    span { width: 32px; height: 32px; border: 3px solid #dbeafe; border-top-color: #0284c7; border-radius: 50%; animation: spin .8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
`
