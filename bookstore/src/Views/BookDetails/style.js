import styled from "styled-components";

export const Container = styled.div`
    width: 100%;
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 40px 20px;
    background-color: #f4f6f8;
`

export const FormCard = styled.div`
    background: white;
    width: 100%;
    max-width: 400px;
    padding: 40px;
    border-radius: 15px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    display: flex;
    flex-direction: column;
    gap: 20px;

    h2 {
        text-align: center;
        color: #004299;
        margin-bottom: 10px;
    }

    button {
        background-color: #004299;
        color: white;
        padding: 15px;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        font-weight: 600;
        margin-top: 10px;
        transition: background 0.2s;

        &:hover {
            background-color: #003375;
        }
    }
`

export const InputGroup = styled.div`
    display: flex;
    flex-direction: column;
    gap: 8px;

    label {
        font-size: 0.9rem;
        font-weight: bold;
        color: #555;
    }

    input {
        padding: 12px;
        border: 1px solid #ddd;
        border-radius: 8px;
        font-size: 1rem;
        transition: border-color 0.2s;

        &:focus {
            outline: none;
            border-color: #004299;
        }
    }
`