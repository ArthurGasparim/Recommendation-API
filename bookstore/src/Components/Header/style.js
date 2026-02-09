import styled from 'styled-components'

export const Container = styled.header`
    width: 100%;
    height: 70px;
    background-color: #004299;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    position: sticky;
    top: 0;
    z-index: 1000;
    display: flex;
    justify-content: center;
`

export const Wrapper = styled.div`
    width: 100%;
    max-width: 1200px;
    height: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;

    .logo-area {
        display: flex;
        align-items: center;
        gap: 10px;
        color: white;
        font-size: 1.5rem;
        font-weight: bold;

        img {
            height: 40px;
            border-radius: 5px;
        }
    }
`

export const Nav = styled.nav`
    display: flex;
    gap: 20px;

    a {
        color: rgba(255,255,255,0.8);
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.2s ease;

        &:hover {
            color: #ffffff;
            transform: translateY(-2px);
        }
    }
`