import styled from "styled-components";

export const Container =  styled.div`
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
`

export const ScrollBar = styled.div`
  display: flex; 
  overflow-x: auto;
  white-space: nowrap;      
  width: 100%;
  height: 350px;
  gap: 10px;
`

export const Item = styled.div`
  
`

export const Line = styled.div`
  display: flex;
`


/*flex-shrink: 0;
  width: 100px;
  height: 100px;
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  display: inline-block; */