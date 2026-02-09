import styled from "styled-components";

export const Container = styled.div`
    width: 180px;
    height: 320px;
    background-color: white;
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    cursor: pointer;

    &:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
`

export const ImageContainer = styled.div`
    width: 100%;
    height: 200px;
    background-color: #eee;
    
    img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
`

export const Info = styled.div`
    padding: 15px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex: 1;

    h3 {
        font-size: 1rem;
        color: #2c3e50;
        margin-bottom: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .author {
        font-size: 0.85rem;
        color: #7f8c8d;
        margin-bottom: 8px;
    }

    .rating {
        display: flex;
        align-items: center;
        gap: 5px;
        font-weight: bold;
        color: #333;
        font-size: 0.9rem;
    }
`