import styled from "styled-components"
export const Container =  styled.div`
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    img{
    width: 15%;
    height: 30%;
    object-fit: cover;
    }
`
export const Line =  styled.div`
    display: flex;
    align-items: center;
    justify-content:space-between;
`

export const FormContainer = styled.div`
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-evenly; 
    flex-wrap: wrap; 
    gap: 10px;
    margin-top: 20px;
`

export const Form = styled.div`
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
`