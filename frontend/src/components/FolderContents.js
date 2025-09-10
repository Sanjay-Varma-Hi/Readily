import React, { useState, useEffect } from 'react';
import styled from 'styled-components';

const Container = styled.div`
  padding: 32px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 32px;
  background: linear-gradient(135deg, #fafbfc 0%, #f8fafc 100%);
`;


const UploadSection = styled.div`
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border: none;
  border-radius: 20px;
  padding: 48px 32px;
  text-align: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(240, 147, 251, 0.3);

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
    box-shadow: 0 16px 48px rgba(240, 147, 251, 0.4);
  }
`;

const UploadButton = styled.button`
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

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
`;

const DocumentsSection = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
`;

const SectionTitle = styled.h3`
  font-size: 1.2rem;
  font-weight: 600;
  color: #374151;
  margin: 0;
`;

const SectionHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 2px solid #e5e7eb;
`;

const RefreshButton = styled.button`
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #475569;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;

  &:hover:not(:disabled) {
    background: #e2e8f0;
    border-color: #cbd5e1;
    color: #334155;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const DocumentsList = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  padding: 16px 0;
`;

const DocumentItem = styled.div`
  background: white;
  border: 1px solid rgba(240, 147, 251, 0.1);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(240, 147, 251, 0.02) 0%, rgba(245, 87, 108, 0.02) 100%);
    pointer-events: none;
  }

  &:hover {
    border-color: #f093fb;
    box-shadow: 0 8px 24px rgba(240, 147, 251, 0.2);
    transform: translateY(-3px) scale(1.02);
  }
`;

const DeleteButton = styled.button`
  position: absolute;
  top: 8px;
  right: 8px;
  background: #ef4444;
  border: none;
  color: white;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  z-index: 10;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);

  &:hover {
    background: #dc2626;
    transform: scale(1.1);
    box-shadow: 0 4px 8px rgba(239, 68, 68, 0.4);
  }

  &:active {
    transform: scale(0.95);
  }
`;

const DocumentIcon = styled.div`
  font-size: 1.8rem;
  color: #f093fb;
  margin-bottom: 8px;
  text-align: center;
  filter: drop-shadow(0 2px 4px rgba(240, 147, 251, 0.3));
  position: relative;
  z-index: 1;
`;

const DocumentName = styled.h4`
  margin: 0 0 8px 0;
  font-size: 0.9rem;
  font-weight: 700;
  color: #1e293b;
  text-align: center;
  word-break: break-word;
  line-height: 1.3;
  letter-spacing: -0.025em;
  position: relative;
  z-index: 1;
`;

const DocumentMeta = styled.div`
  font-size: 0.75rem;
  color: #64748b;
  display: flex;
  flex-direction: column;
  gap: 3px;
  position: relative;
  z-index: 1;
  font-weight: 500;
`;

const EmptyState = styled.div`
  text-align: center;
  color: #6b7280;
  font-style: italic;
  padding: 40px 20px;
  background: #f9fafb;
  border-radius: 12px;
  border: 2px dashed #d1d5db;
`;

const LoadingMessage = styled.div`
  text-align: center;
  color: #6b7280;
  font-style: italic;
  padding: 40px 20px;
`;

const UploadProgressContainer = styled.div`
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-top: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
`;

const UploadProgressTitle = styled.h4`
  margin: 0 0 16px 0;
  color: #374151;
  font-size: 1.1rem;
  font-weight: 600;
`;

const UploadItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
  
  &:last-child {
    border-bottom: none;
  }
`;

const UploadItemInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
`;

const UploadItemName = styled.span`
  font-weight: 500;
  color: #374151;
  font-size: 0.9rem;
`;

const UploadStatus = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  
  &.pending {
    color: #6b7280;
  }
  
  &.uploading {
    color: #f59e0b;
  }
  
  &.completed {
    color: #10b981;
  }
  
  &.error {
    color: #ef4444;
  }
`;

const ProgressBar = styled.div`
  width: 100px;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
  margin-left: 8px;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: ${props => 
    props.status === 'completed' ? '#10b981' :
    props.status === 'error' ? '#ef4444' :
    props.status === 'uploading' ? '#f59e0b' : '#6b7280'
  };
  width: ${props => props.progress}%;
  transition: width 0.3s ease;
`;

// Modal styled components
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
  padding: 20px;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 16px;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
`;

const ModalHeader = styled.div`
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const ModalTitle = styled.h2`
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
`;

const CloseButton = styled.button`
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  color: #374151;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;

  &:hover {
    background: #e5e7eb;
    border-color: #9ca3af;
  }
`;

const ModalBody = styled.div`
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
`;

const PropertyRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;

  &:last-child {
    border-bottom: none;
  }
`;

const PropertyLabel = styled.span`
  font-weight: 600;
  color: #374151;
  font-size: 0.95rem;
`;

const PropertyValue = styled.span`
  color: #6b7280;
  font-size: 0.9rem;
  text-align: right;
  max-width: 60%;
  word-break: break-word;
`;

function FolderContents({ folder }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [documentStatuses, setDocumentStatuses] = useState({});
  const [statusCheckInProgress, setStatusCheckInProgress] = useState(new Set());
  const [lastRefreshTime, setLastRefreshTime] = useState(0);
  const [uploadQueue, setUploadQueue] = useState([]);
  const [currentUpload, setCurrentUpload] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [showDocumentModal, setShowDocumentModal] = useState(false);

  useEffect(() => {
    if (folder) {
      loadDocuments();
    }
  }, [folder]);

  // Auto-refresh disabled - only manual refresh via button

  const loadDocuments = async () => {
    if (!folder) return;
    
    setLoading(true);
    try {
      console.log('🔄 Loading documents for folder:', folder.name);
      
      const response = await fetch(`http://localhost:8000/api/policies/folders/${folder._id}/documents`);
      
      if (!response.ok) {
        throw new Error('Failed to load documents');
      }
      
      const data = await response.json();
      setDocuments(data || []);
      console.log('✅ Documents loaded for folder:', folder.name, data.length, 'documents');
      
      // No automatic status checking - only when refresh button is pressed
    } catch (err) {
      console.error('❌ Error loading documents:', err);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  const checkDocumentStatus = async (docId) => {
    // Prevent duplicate calls
    if (statusCheckInProgress.has(docId)) {
      return;
    }
    
    setStatusCheckInProgress(prev => new Set(prev).add(docId));
    
    try {
      const response = await fetch(`http://localhost:8000/api/policies/${docId}/status`);
      if (response.ok) {
        const status = await response.json();
        setDocumentStatuses(prev => ({
          ...prev,
          [docId]: status
        }));
      }
    } catch (err) {
      console.error('Error checking document status:', err);
    } finally {
      // Remove from in-progress set
      setStatusCheckInProgress(prev => {
        const newSet = new Set(prev);
        newSet.delete(docId);
        return newSet;
      });
    }
  };

  const handleRefresh = async () => {
    const now = Date.now();
    // Prevent rapid clicking (debounce for 1 second)
    if (now - lastRefreshTime < 1000) {
      console.log('⏳ Refresh too soon, please wait...');
      return;
    }
    
    setLastRefreshTime(now);
    
    // Reload documents and check status in one go
    if (!folder) return;
    
    setLoading(true);
    try {
      console.log('🔄 Refreshing documents for folder:', folder.name);
      
      const response = await fetch(`http://localhost:8000/api/policies/folders/${folder._id}/documents`);
      
      if (!response.ok) {
        throw new Error('Failed to load documents');
      }
      
      const data = await response.json();
      setDocuments(data || []);
      console.log('✅ Documents loaded for folder:', folder.name, data.length, 'documents');
      
      // Check status for all documents (only once)
      console.log('🔄 Checking status for all documents...');
      for (const doc of data || []) {
        if (!statusCheckInProgress.has(doc._id)) {
          checkDocumentStatus(doc._id);
        }
      }
    } catch (err) {
      console.error('❌ Error refreshing documents:', err);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (docId, docTitle) => {
    if (!window.confirm(`Are you sure you want to delete "${docTitle}"? This action cannot be undone.`)) {
      return;
    }

    try {
      console.log('🗑️ Deleting document:', docId);
      
      const response = await fetch(`http://localhost:8000/api/policies/${docId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete document');
      }
      
      console.log('✅ Document deleted successfully');
      
      // Remove document from local state
      setDocuments(prev => prev.filter(doc => doc._id !== docId));
      
      // Also remove from document statuses
      setDocumentStatuses(prev => {
        const newStatuses = { ...prev };
        delete newStatuses[docId];
        return newStatuses;
      });
      
    } catch (err) {
      console.error('❌ Error deleting document:', err);
      alert('Failed to delete document. Please try again.');
    }
  };

  const handleDocumentClick = (doc) => {
    setSelectedDocument(doc);
    setShowDocumentModal(true);
  };

  const handleCloseModal = () => {
    setShowDocumentModal(false);
    setSelectedDocument(null);
  };

  const handleFileUpload = () => {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf,.docx';
    fileInput.multiple = true; // Allow multiple file selection
    fileInput.onchange = (e) => {
      const files = Array.from(e.target.files);
      if (files.length > 0) {
        uploadMultipleFiles(files);
      }
    };
    fileInput.click();
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const uploadMultipleFiles = async (files) => {
    if (!folder) return;
    
    console.log(`📤 Starting upload of ${files.length} files`);
    
    // Create upload queue with file info
    const queue = files.map((file, index) => ({
      id: `upload_${Date.now()}_${index}`,
      file,
      status: 'pending', // pending, uploading, completed, error
      progress: 0,
      error: null
    }));
    
    setUploadQueue(queue);
    setUploading(true);
    
    // Process files one by one
    for (let i = 0; i < queue.length; i++) {
      const queueItem = queue[i];
      setCurrentUpload(queueItem);
      
      // Update status to uploading
      setUploadQueue(prev => prev.map(item => 
        item.id === queueItem.id 
          ? { ...item, status: 'uploading' }
          : item
      ));
      
      try {
        await uploadSingleFile(queueItem.file, queueItem.id);
        
        // Update status to completed
        setUploadQueue(prev => prev.map(item => 
          item.id === queueItem.id 
            ? { ...item, status: 'completed', progress: 100 }
            : item
        ));
        
      } catch (err) {
        console.error(`❌ Upload error for ${queueItem.file.name}:`, err);
        
        // Update status to error
        setUploadQueue(prev => prev.map(item => 
          item.id === queueItem.id 
            ? { ...item, status: 'error', error: err.message }
            : item
        ));
      }
      
      // Small delay between uploads
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    // Reload documents to show all new uploads
    await loadDocuments();
    
    // Clear upload queue after a delay
    setTimeout(() => {
      setUploadQueue([]);
      setCurrentUpload(null);
      setUploading(false);
    }, 2000);
  };

  const uploadSingleFile = async (file, queueId) => {
    console.log('📤 Uploading file:', file.name);
    
    const formData = new FormData();
    formData.append('file', file);
    // Extract title by removing only the file extension (last part after the last dot)
    const fileExtension = file.name.split('.').pop();
    const title = file.name.replace(`.${fileExtension}`, '');
    formData.append('title', title);
    formData.append('jurisdiction', 'Unknown');
    formData.append('version', '1.0');
    formData.append('effective_date', new Date().toISOString());
    
    const response = await fetch(`http://localhost:8000/api/policies/folders/${folder._id}/documents`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }
    
    const result = await response.json();
    console.log('✅ Upload successful:', result);
    return result;
  };

  const uploadFile = async (file) => {
    if (!folder) return;
    
    setUploading(true);
    try {
      console.log('🔄 Uploading file to folder:', folder.name, file.name);
      
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      // Extract title by removing only the file extension (last part after the last dot)
      const fileExtension = file.name.split('.').pop();
      const title = file.name.replace(`.${fileExtension}`, '');
      formData.append('title', title);
      formData.append('jurisdiction', 'Unknown');
      formData.append('version', '1.0');
      formData.append('effective_date', new Date().toISOString());
      
      // Upload file
      const response = await fetch(`http://localhost:8000/api/policies/folders/${folder._id}/documents`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }
      
      const result = await response.json();
      console.log('✅ File uploaded successfully:', result);
      
      // Reload documents
      await loadDocuments();
      
      alert('File uploaded successfully! Processing will begin in the background.');
      
    } catch (err) {
      console.error('❌ Upload error:', err);
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  if (!folder) {
    return (
      <Container>
        <EmptyState>Select a folder to view its contents</EmptyState>
      </Container>
    );
  }

  return (
    <Container>
      <UploadSection onClick={handleFileUpload}>
        <UploadButton disabled={uploading}>
          <span>{uploading ? '⏳' : '📤'}</span>
          <span>
            {uploading 
              ? `Uploading ${uploadQueue.length > 0 ? `${uploadQueue.filter(item => item.status === 'completed').length + 1}/${uploadQueue.length}` : ''}...` 
              : 'Upload Files to This Folder'
            }
          </span>
        </UploadButton>
      </UploadSection>

      {uploadQueue.length > 0 && (
        <UploadProgressContainer>
          <UploadProgressTitle>
            Upload Progress ({uploadQueue.filter(item => item.status === 'completed').length}/{uploadQueue.length} completed)
          </UploadProgressTitle>
          {uploadQueue.map((item) => (
            <UploadItem key={item.id}>
              <UploadItemInfo>
                <span>📄</span>
                <UploadItemName>{item.file.name}</UploadItemName>
              </UploadItemInfo>
              <UploadStatus className={item.status}>
                {item.status === 'pending' && '⏸️ Pending'}
                {item.status === 'uploading' && '⏳ Uploading...'}
                {item.status === 'completed' && '✅ Completed'}
                {item.status === 'error' && `❌ Error: ${item.error}`}
                <ProgressBar>
                  <ProgressFill 
                    status={item.status} 
                    progress={item.status === 'uploading' ? 50 : item.progress}
                  />
                </ProgressBar>
              </UploadStatus>
            </UploadItem>
          ))}
        </UploadProgressContainer>
      )}

      <DocumentsSection>
        <SectionHeader>
          <SectionTitle>Documents in this folder</SectionTitle>
          <RefreshButton onClick={handleRefresh} disabled={loading}>
            <span>{loading ? '⏳' : '🔄'}</span>
            <span>{loading ? 'Loading...' : 'Refresh'}</span>
          </RefreshButton>
        </SectionHeader>
        {loading ? (
          <LoadingMessage>Loading documents...</LoadingMessage>
        ) : documents.length === 0 ? (
          <EmptyState>
            No documents in this folder yet.<br />
            Upload some files to get started.
          </EmptyState>
        ) : (
          <DocumentsList>
            {documents.map((doc) => {
              const status = documentStatuses[doc._id];
              return (
                <DocumentItem key={doc._id} onClick={() => handleDocumentClick(doc)}>
                  <DeleteButton 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteDocument(doc._id, doc.title);
                    }}
                    title="Delete document"
                  >
                    ×
                  </DeleteButton>
                  <DocumentIcon>📄</DocumentIcon>
                  <DocumentName>{doc.title}</DocumentName>
                  <DocumentMeta>
                    <div>Status: {doc.status}</div>
                    <div>Type: {doc.file_type?.toUpperCase()}</div>
                    <div>Size: {formatFileSize(doc.file_size)}</div>
                    <div>Uploaded: {new Date(doc.uploaded_at).toLocaleDateString()}</div>
                    {status && (
                      <div style={{ 
                        color: status.status === 'completed' ? '#10b981' : 
                               status.status === 'error' ? '#ef4444' : 
                               status.status === 'processing' ? '#f59e0b' : '#6b7280',
                        fontWeight: 'bold',
                        marginTop: '4px'
                      }}>
                        {status.status === 'processing' && `⏳ Processing ${status.progress}% (${status.processed_chunks}/${status.total_chunks})`}
                        {status.status === 'completed' && '✅ Analysis Complete'}
                        {status.status === 'error' && `❌ Error: ${status.error}`}
                        {status.status === 'pending' && '⏸️ Pending Analysis'}
                      </div>
                    )}
                  </DocumentMeta>
                </DocumentItem>
              );
            })}
          </DocumentsList>
        )}
      </DocumentsSection>

      {/* Document Properties Modal */}
      {showDocumentModal && selectedDocument && (
        <ModalOverlay onClick={handleCloseModal}>
          <ModalContent onClick={(e) => e.stopPropagation()}>
            <ModalHeader>
              <ModalTitle>Document Properties</ModalTitle>
              <CloseButton onClick={handleCloseModal}>×</CloseButton>
            </ModalHeader>
            <ModalBody>
              <PropertyRow>
                <PropertyLabel>Title:</PropertyLabel>
                <PropertyValue>{selectedDocument.title}</PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>Version:</PropertyLabel>
                <PropertyValue>{selectedDocument.version || '1.0'}</PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>Checksum:</PropertyLabel>
                <PropertyValue style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                  {selectedDocument.checksum || 'N/A'}
                </PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>File Type:</PropertyLabel>
                <PropertyValue>{selectedDocument.file_type?.toUpperCase() || 'Unknown'}</PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>File Size:</PropertyLabel>
                <PropertyValue>{formatFileSize(selectedDocument.file_size)}</PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>Status:</PropertyLabel>
                <PropertyValue style={{ 
                  color: selectedDocument.status === 'completed' ? '#10b981' : 
                         selectedDocument.status === 'error' ? '#ef4444' : 
                         selectedDocument.status === 'processing' ? '#f59e0b' : '#6b7280',
                  fontWeight: '600'
                }}>
                  {selectedDocument.status}
                </PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>Jurisdiction:</PropertyLabel>
                <PropertyValue>{selectedDocument.jurisdiction || 'Unknown'}</PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>Policy Type:</PropertyLabel>
                <PropertyValue>{selectedDocument.policy_type || 'Unknown'}</PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>Effective Date:</PropertyLabel>
                <PropertyValue>
                  {selectedDocument.effective_date ? 
                    new Date(selectedDocument.effective_date).toLocaleDateString() : 
                    'Unknown'
                  }
                </PropertyValue>
              </PropertyRow>
              <PropertyRow>
                <PropertyLabel>Uploaded:</PropertyLabel>
                <PropertyValue>
                  {selectedDocument.uploaded_at ? 
                    new Date(selectedDocument.uploaded_at).toLocaleDateString() : 
                    'Unknown'
                  }
                </PropertyValue>
              </PropertyRow>
              <PropertyRow style={{ borderTop: '2px solid #e5e7eb', marginTop: '16px', paddingTop: '20px' }}>
                <PropertyLabel>Source:</PropertyLabel>
                <PropertyValue>
                  <a 
                    href="https://drive.google.com/drive/folders/1eHw6ybJh1ItDdsmLuYw1vPU4hRx43mA9" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ 
                      color: '#0ea5e9', 
                      textDecoration: 'none',
                      fontWeight: '500',
                      fontSize: '0.9rem'
                    }}
                    onMouseEnter={(e) => e.target.style.textDecoration = 'underline'}
                    onMouseLeave={(e) => e.target.style.textDecoration = 'none'}
                  >
                    📁 View in Google Drive
                  </a>
                </PropertyValue>
              </PropertyRow>
            </ModalBody>
          </ModalContent>
        </ModalOverlay>
      )}
    </Container>
  );
}

export default FolderContents;
