import React, { useState, useRef, useCallback } from 'react';
import styled from 'styled-components';
import PolicyPanel from './PolicyPanel';
import QuestionnairePanel from './QuestionnairePanel';
import FolderContents from './FolderContents';

const MainContainer = styled.div`
  display: flex;
  height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
`;

const LeftPanel = styled.div`
  width: ${props => props.width}%;
  background: white;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 16px 16px 16px 0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  margin: 0 0 0 16px;
  border: 1px solid rgba(0, 0, 0, 0.05);
`;

const RightPanel = styled.div`
  width: ${props => props.width}%;
  background: white;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 16px 0 0 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  margin: 0 16px 0 0;
  border: 1px solid rgba(0, 0, 0, 0.05);
`;

const Resizer = styled.div`
  width: 2px;
  background: #d1d5db;
  cursor: col-resize;
  position: relative;
  min-width: 2px;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.1);
  
  &:hover {
    background: #9ca3af;
    width: 4px;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.2);
  }
  
  &:active {
    background: #6b7280;
    width: 4px;
    box-shadow: 0 0 6px rgba(0, 0, 0, 0.3);
  }
  
  &::after {
    content: 'Drag to resize • Double-click to reset';
    position: absolute;
    top: 50%;
    left: 8px;
    transform: translateY(-50%);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.1s ease;
    z-index: 1000;
  }
  
  &:hover::after {
    opacity: 1;
  }
`;

const PanelHeader = styled.div`
  background: white;
  color: #1e293b;
  padding: 20px 28px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 60px;
  position: relative;
  overflow: hidden;
`;

const LeftPanelHeader = styled(PanelHeader)`
  background: white;
  border-radius: 16px 16px 0 0;
`;

const RightPanelHeader = styled(PanelHeader)`
  background: white;
  border-radius: 16px 0 0 0;
  justify-content: space-between;
`;

const BackButton = styled.button`
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  color: #374151;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;

  &:hover {
    background: #e5e7eb;
    border-color: #9ca3af;
  }
`;

const PanelTitle = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  letter-spacing: -0.025em;
  position: relative;
  z-index: 1;
`;

const PanelContent = styled.div`
  flex: 1;
  padding: 0;
  overflow-y: auto;
  background: linear-gradient(135deg, #fafbfc 0%, #f8fafc 100%);
  border-radius: 0 0 16px 0;
  position: relative;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 3px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.2);
  }
`;

const QuestionsOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: white;
  z-index: 10;
  overflow-y: auto;
  border-radius: 0 0 16px 0;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 3px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.2);
  }
`;

function MainLayout() {
  const [leftWidth, setLeftWidth] = useState(50);
  const [isResizing, setIsResizing] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [showQuestions, setShowQuestions] = useState(false);
  const [selectedQuestionnaire, setSelectedQuestionnaire] = useState(null);
  const [questions, setQuestions] = useState([]);
  const containerRef = useRef(null);

  const handleMouseDown = useCallback((e) => {
    setIsResizing(true);
    e.preventDefault();
  }, []);

  const handleMouseMove = useCallback((e) => {
    if (!isResizing || !containerRef.current) return;
    
    requestAnimationFrame(() => {
      const containerRect = containerRef.current.getBoundingClientRect();
      const newLeftWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
      
      // Constrain between 20% and 80%
      const constrainedWidth = Math.min(Math.max(newLeftWidth, 20), 80);
      setLeftWidth(constrainedWidth);
    });
  }, [isResizing]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  const handleDoubleClick = useCallback(() => {
    setLeftWidth(50);
  }, []);

  const handleFolderSelect = useCallback((folder) => {
    setSelectedFolder(folder);
  }, []);

  const handleBackToFolders = useCallback(() => {
    setSelectedFolder(null);
  }, []);

  const handleViewQuestions = useCallback((questionnaire, questionsData) => {
    setSelectedQuestionnaire(questionnaire);
    setQuestions(questionsData);
    setShowQuestions(true);
    setSelectedFolder(null); // Clear folder selection when viewing questions
  }, []);

  const handleCloseQuestions = useCallback(() => {
    setShowQuestions(false);
    setSelectedQuestionnaire(null);
    setQuestions([]);
  }, []);

  // Add event listeners for mouse move and up
  React.useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  return (
    <MainContainer ref={containerRef}>
      <LeftPanel width={leftWidth}>
        <LeftPanelHeader>
          <div style={{ fontSize: '1.5rem' }}>
            {showQuestions ? '📋' : '📁'}
          </div>
          <PanelTitle>
            {showQuestions ? 'Questionnaire Analysis' : 'Policy Documents'}
          </PanelTitle>
          {showQuestions && (
            <BackButton onClick={handleCloseQuestions}>
              Close
            </BackButton>
          )}
        </LeftPanelHeader>
        <PanelContent>
          <PolicyPanel 
            selectedFolder={selectedFolder} 
            onFolderSelect={handleFolderSelect} 
          />
          {showQuestions && (
            <QuestionsOverlay>
              <QuestionnairePanel 
                selectedQuestionnaire={selectedQuestionnaire}
                questions={questions}
                onCloseQuestions={handleCloseQuestions}
              />
            </QuestionsOverlay>
          )}
        </PanelContent>
      </LeftPanel>

      <Resizer onMouseDown={handleMouseDown} onDoubleClick={handleDoubleClick} />

      <RightPanel width={100 - leftWidth}>
        <RightPanelHeader>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ fontSize: '1.5rem' }}>
              {selectedFolder ? '📁' : '📋'}
            </div>
            <PanelTitle>
              {selectedFolder ? `${selectedFolder.name} Contents` : 'Questionnaire Analysis'}
            </PanelTitle>
          </div>
          {selectedFolder && (
            <BackButton onClick={handleBackToFolders}>
              ← Back to Folders
            </BackButton>
          )}
        </RightPanelHeader>
        <PanelContent>
          {selectedFolder ? (
            <FolderContents 
              folder={selectedFolder} 
            />
          ) : (
            <QuestionnairePanel 
              onViewQuestions={handleViewQuestions}
            />
          )}
        </PanelContent>
      </RightPanel>
    </MainContainer>
  );
}

export default MainLayout;
