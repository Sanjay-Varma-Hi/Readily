import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { getPolicyFolders, uploadPolicy } from '../services/api';

const Container = styled.div`
  padding: 32px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 32px;
  background: linear-gradient(135deg, #fafbfc 0%, #f8fafc 100%);
`;

const AddPolicySection = styled.div`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 20px;
  padding: 48px 32px;
  text-align: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
    pointer-events: none;
  }

  &:hover {
    transform: translateY(-4px) scale(1.02);
    box-shadow: 0 16px 48px rgba(102, 126, 234, 0.4);
  }
`;

const AddButton = styled.button`
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  padding: 18px 36px;
  border-radius: 16px;
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
  letter-spacing: -0.025em;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.3);
    border-color: rgba(255, 255, 255, 0.5);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
`;

const FoldersSection = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
`;

const SectionTitle = styled.h3`
  font-size: 1.4rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  padding-bottom: 16px;
  border-bottom: 3px solid #e2e8f0;
  letter-spacing: -0.025em;
`;

const FoldersList = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  padding: 16px 0;
  
  @media (max-width: 768px) {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
  }
`;

const FolderItem = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px 12px;
  background: white;
  border: 1px solid ${props => props.selected ? '#667eea' : 'rgba(102, 126, 234, 0.1)'};
  border-radius: 12px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  box-shadow: ${props => props.selected ? '0 6px 24px rgba(102, 126, 234, 0.3)' : '0 2px 8px rgba(0, 0, 0, 0.08)'};
  opacity: ${props => props.dimmed ? '0.5' : '1'};
  transform: ${props => props.selected ? 'translateY(-2px) scale(1.02)' : 'translateY(0)'};
  min-height: 100px;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: ${props => props.selected ? 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)' : 'transparent'};
    pointer-events: none;
  }

  &:hover {
    border-color: #667eea;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
    transform: translateY(-3px) scale(1.02);
    opacity: 1;
  }
`;

const FolderInfo = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
  width: 100%;
  position: relative;
  z-index: 1;
`;

const FolderIcon = styled.div`
  font-size: 2rem;
  color: #667eea;
  filter: drop-shadow(0 2px 4px rgba(102, 126, 234, 0.3));
`;

const FolderDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
`;

const FolderName = styled.h4`
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.025em;
  word-break: break-word;
  line-height: 1.3;
`;

const DocumentCount = styled.span`
  font-size: 0.9rem;
  color: #64748b;
  font-weight: 600;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  padding: 6px 12px;
  border-radius: 16px;
  display: inline-block;
  border: 1px solid rgba(102, 126, 234, 0.1);
`;

const FolderActions = styled.div`
  display: flex;
  gap: 12px;
  margin-top: 12px;
`;

const ActionButton = styled.button`
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.2);
  color: #667eea;
  cursor: pointer;
  padding: 8px;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 1rem;
  min-width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);

  &:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
  }
`;

const LoadingMessage = styled.div`
  text-align: center;
  color: #6b7280;
  font-style: italic;
  padding: 40px 20px;
  font-size: 1.1rem;
`;

const ErrorMessage = styled.div`
  background: #fef2f2;
  color: #dc2626;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #fecaca;
  margin: 10px 0;
  font-weight: 500;
`;

const EmptyState = styled.div`
  text-align: center;
  color: #6b7280;
  padding: 40px 20px;
  font-size: 1rem;
`;

// Modal components
const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 12px;
  padding: 32px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
`;

const ModalTitle = styled.h3`
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 16px 0;
  text-align: center;
`;

const ModalInput = styled.input`
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 1rem;
  margin-bottom: 24px;
  transition: border-color 0.3s ease;

  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const ModalButtons = styled.div`
  display: flex;
  gap: 12px;
  justify-content: flex-end;
`;

const ModalButton = styled.button`
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;

  ${props => props.primary ? `
    background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
    color: white;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
  ` : `
    background: #f3f4f6;
    color: #374151;
    
    &:hover {
      background: #e5e7eb;
    }
  `}
`;

function PolicyPanel({ selectedFolder, onFolderSelect }) {
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [policyName, setPolicyName] = useState('');

  useEffect(() => {
    loadFolders();
  }, []);

  const loadFolders = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔄 Loading policy folders...');
      const data = await getPolicyFolders();
      console.log('✅ Policy folders loaded:', data);
      setFolders(data || []);
    } catch (err) {
      console.error('❌ Error loading folders:', err);
      setError('Failed to load policy folders. Please check your connection.');
      setFolders([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPolicy = () => {
    setShowModal(true);
    setPolicyName('');
  };

  const handleCreatePolicy = async () => {
    if (!policyName.trim()) {
      alert('Please enter a policy name');
      return;
    }

    try {
      console.log('🔄 Creating policy folder:', policyName);
      setUploading(true);
      setError(null);

      // Create a new policy folder in the database
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'https://readily-mgtk.onrender.com'}/api/policies/folders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: policyName.trim(),
          policy_type: 'custom'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create policy folder');
      }

      const result = await response.json();
      console.log('✅ Policy folder created:', result);
      
      // Reload folders to show the new policy
      await loadFolders();
      setShowModal(false);
      setPolicyName('');
      alert('Policy folder created successfully!');
    } catch (err) {
      console.error('❌ Create error:', err);
      setError('Failed to create policy folder. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleCancelModal = () => {
    setShowModal(false);
    setPolicyName('');
  };

  const handleRefresh = (e) => {
    e.stopPropagation();
    loadFolders();
  };

  const handleFolderClick = (folder) => {
    if (onFolderSelect) {
      onFolderSelect(folder);
    }
  };

  const handleUploadToFolder = (e, folder) => {
    e.stopPropagation();
    // TODO: Implement file upload to specific folder
    console.log('Upload to folder:', folder.name);
  };

  if (loading) {
    return (
      <Container>
        <LoadingMessage>Loading policy folders...</LoadingMessage>
      </Container>
    );
  }

  return (
    <Container>
      <AddPolicySection onClick={handleAddPolicy}>
        <AddButton disabled={uploading}>
          <span>{uploading ? '⏳' : '+'}</span>
          <span>{uploading ? 'Uploading...' : 'Add New Policy'}</span>
        </AddButton>
      </AddPolicySection>

      {error && <ErrorMessage>{error}</ErrorMessage>}

      <FoldersSection>
        <SectionTitle>Policy Categories</SectionTitle>
        {folders.length === 0 ? (
          <EmptyState>No policy categories found. Add your first policy to get started.</EmptyState>
        ) : (
          <FoldersList>
            {folders.map((folder) => (
              <FolderItem 
                key={folder._id || folder.id}
                selected={selectedFolder && selectedFolder._id === folder._id}
                dimmed={selectedFolder && selectedFolder._id !== folder._id}
                onClick={() => handleFolderClick(folder)}
              >
                <FolderInfo>
                  <FolderIcon>📁</FolderIcon>
                  <FolderDetails>
                    <FolderName>{folder.name}</FolderName>
                    <DocumentCount>{folder.document_count || 0} documents</DocumentCount>
                  </FolderDetails>
                </FolderInfo>
                <FolderActions>
                  <ActionButton 
                    onClick={(e) => handleUploadToFolder(e, folder)} 
                    title="Upload files to this folder"
                  >
                    📤
                  </ActionButton>
                  <ActionButton 
                    onClick={handleRefresh} 
                    title="Refresh folder"
                  >
                    🔄
                  </ActionButton>
                </FolderActions>
              </FolderItem>
            ))}
          </FoldersList>
        )}
      </FoldersSection>

      {/* Modal for adding new policy */}
      {showModal && (
        <ModalOverlay onClick={handleCancelModal}>
          <ModalContent onClick={(e) => e.stopPropagation()}>
            <ModalTitle>Add New Policy</ModalTitle>
            <ModalInput
              type="text"
              placeholder="Enter policy name..."
              value={policyName}
              onChange={(e) => setPolicyName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleCreatePolicy()}
              autoFocus
            />
            <ModalButtons>
              <ModalButton onClick={handleCancelModal}>
                Cancel
              </ModalButton>
              <ModalButton primary onClick={handleCreatePolicy} disabled={uploading}>
                {uploading ? 'Creating...' : 'Create Policy'}
              </ModalButton>
            </ModalButtons>
          </ModalContent>
        </ModalOverlay>
      )}
    </Container>
  );
}

export default PolicyPanel;