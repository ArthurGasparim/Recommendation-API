import styled from "styled-components";

export const Container = styled.div`
    flex-shrink: 0;
    background-color: #f0f0f0;
    border: 1px solid #ccc;
    width:200px;
    height:240px;
    display:flex;
    flex-direction:column;
     justify-content:space-between;
    img{
    width: 100%;
    height: 100%;
    object-fit: cover;
    }
`

export const Bottom = styled.div`
    bottom:0;
    display:flex;
    justify-content:space-between;
    flex-wrap: wrap;
`

