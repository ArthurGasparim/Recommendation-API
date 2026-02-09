import styled from "styled-components"

export const Container = styled.div`
    width: 100%;
    max-width: 1000px;
    margin: 40px auto;
    padding: 0 20px;
    flex: 1;
`

export const ContentWrapper = styled.div`
    display: flex;
    gap: 40px;
    background: white;
    padding: 40px;
    border-radius: 15px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.05);

    @media (max-width: 768px) {
        flex-direction: column;
        align-items: center;
    }
`

export const ImageWrapper = styled.div`
    flex: 1;
    max-width: 300px;

    img {
        width: 100%;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
`

export const Details = styled.div`
    flex: 2;
    display: flex;
    flex-direction: column;
`

export const Title = styled.h1`
    font-size: 2.2rem;
    color: #1a1a1a;
    margin-bottom: 10px;
`

export const Meta = styled.div`
    margin-bottom: 30px;
    display: flex;
    flex-direction: column;
    gap: 10px;

    p {
        color: #666;
        font-size: 1.1rem;
    }

    .rating-badge {
        display: inline-flex;
        align-items: center;
        background-color: #FFF9C4;
        color: #FBC02D;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: bold;
        width: fit-content;
    }
`

export const ActionSection = styled.div`
    display: flex;
    flex-direction: column;
    gap: 15px;

    .buy-btn {
        margin-top: 10px;
        padding: 15px;
        background-color: #27ae60;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 1.1rem;
        font-weight: bold;
        width: 100%;
        transition: background 0.2s;

        &:hover {
            background-color: #219150;
        }
    }
`

export const Card = styled.div`
    background: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #e9ecef;

    h4 {
        margin-bottom: 10px;
        font-size: 0.9rem;
        color: #555;
    }

    .input-row {
        display: flex;
        gap: 10px;
        
        input {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        button {
            padding: 8px 15px;
            background-color: #004299;
            color: white;
            border: none;
            border-radius: 4px;
        }
    }

    .checkbox-container {
        display: flex;
        align-items: center;
        gap: 10px;
        cursor: pointer;
        
        input {
            width: 18px;
            height: 18px;
        }
    }
`