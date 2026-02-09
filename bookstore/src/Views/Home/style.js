import styled from "styled-components";

export const Container = styled.main`
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 20px;
    flex: 1;
`

export const Section = styled.section`
    margin-bottom: 50px;
`

export const SectionTitle = styled.h2`
    font-size: 1.5rem;
    color: #004299;
    margin-bottom: 20px;
    border-left: 5px solid #004299;
    padding-left: 15px;
`

export const ScrollBar = styled.div`
    display: flex; 
    overflow-x: auto;
    gap: 20px;
    padding: 10px 5px 30px 5px;
    
    /* Custom Scrollbar */
    &::-webkit-scrollbar {
        height: 8px;
    }
    &::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    &::-webkit-scrollbar-thumb {
        background: #ccc; 
        border-radius: 4px;
    }
    &::-webkit-scrollbar-thumb:hover {
        background: #004299; 
    }
`

export const InputGroup = styled.div`
    display: flex;
    gap: 10px;
    margin-bottom: 20px;

    input {
        padding: 10px 15px;
        border: 1px solid #ccc;
        border-radius: 5px;
        font-size: 1rem;
        width: 200px;
        &:focus {
            outline: none;
            border-color: #004299;
        }
    }

    button {
        padding: 10px 20px;
        background-color: #004299;
        color: white;
        border: none;
        border-radius: 5px;
        font-weight: bold;
        transition: background 0.2s;

        &:hover {
            background-color: #003375;
        }
    }
`