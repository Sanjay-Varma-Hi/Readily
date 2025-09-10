import React from 'react';
import styled from 'styled-components';

const HeaderContainer = styled.header`
  background: white;
  color: #1e293b;
  padding: 12px 0;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 10;
  border-bottom: 1px solid #e2e8f0;
`;

const HeaderContent = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
`;

const Logo = styled.h1`
  font-size: 2rem;
  font-weight: 700;
  margin: 0;
  text-shadow: none;
  letter-spacing: -0.01em;
  color: #1e293b;
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f1f5f9;
  padding: 6px 16px;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  position: absolute;
  right: 20px;
`;

const StatusDot = styled.div`
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
`;

const StatusText = styled.span`
  font-size: 0.85rem;
  font-weight: 500;
  color: #64748b;
`;

const pulseAnimation = `
  @keyframes pulse {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.7;
      transform: scale(1.1);
    }
  }
`;

function Header() {
  return (
    <HeaderContainer>
      <HeaderContent>
        <Logo>READILY</Logo>
        <StatusIndicator>
          <StatusDot />
          <StatusText>System Online</StatusText>
        </StatusIndicator>
      </HeaderContent>
    </HeaderContainer>
  );
}

export default Header;
