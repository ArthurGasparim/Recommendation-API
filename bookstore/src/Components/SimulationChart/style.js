import styled from 'styled-components'

export const ChartFrame = styled.div`
    border: 1px solid #dbe5ef;
    border-radius: 20px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbfd 100%);
    padding: 18px 18px 8px;
`

export const Legend = styled.div`
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    justify-content: flex-end;
    color: #475569;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 0 8px 8px;

    span { display: inline-flex; align-items: center; gap: 7px; }
    i { width: 20px; height: 3px; border-radius: 2px; display: inline-block; }
    i.with { background: #10b981; }
    i.without { background: repeating-linear-gradient(90deg, #f43f5e 0 7px, transparent 7px 10px); }
    i.detection { height: 12px; width: 2px; background: #059669; border-left: 1px dashed #059669; }
`

export const SvgWrap = styled.div`
    position: relative;
    width: 100%;

    svg { width: 100%; height: auto; display: block; overflow: visible; }
`

export const Tooltip = styled.div`
    position: absolute;
    top: 42px;
    transform: translateX(-50%);
    z-index: 5;
    min-width: 190px;
    padding: 12px 14px;
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.94);
    color: #fff;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.25);
    pointer-events: none;

    strong { display: block; margin-bottom: 8px; font-size: 0.78rem; color: #cbd5e1; }
    span { display: flex; align-items: center; gap: 7px; font-size: 0.76rem; margin-top: 5px; }
    b { margin-left: auto; }
    i { width: 8px; height: 8px; border-radius: 50%; }
    i.with { background: #10b981; }
    i.without { background: #f43f5e; }
`
