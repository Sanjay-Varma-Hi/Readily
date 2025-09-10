import React from 'react';
import styled from 'styled-components';
import Header from './components/Header';
import MainLayout from './components/MainLayout';

const AppContainer = styled.div`
  min-height: 100vh;
  background-color: #f5f5f5;
`;

function App() {
  return (
    <AppContainer>
      <Header />
      <MainLayout />
    </AppContainer>
  );
}

export default App;

