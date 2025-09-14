import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { getQuestionnaires, uploadQuestionnaire, getQuestionnaireQuestionsFormatted, answerAuditQuestion, findEvidenceForQuestion, getAuditAnswer, getAuditAnswers, getAnswerDetails } from '../services/api';

const Container = styled.div`
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const UploadSection = styled.div`
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 2px dashed #7dd3fc;
  border-radius: 12px;
  padding: 40px 24px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;

  &:hover {
    border-color: #0ea5e9;
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(14, 165, 233, 0.15);
  }

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
    transform: rotate(45deg);
    transition: all 0.6s;
    opacity: 0;
  }

  &:hover::before {
    opacity: 1;
    animation: shimmer 1.5s ease-in-out;
  }

  @keyframes shimmer {
    0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
    100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
  }
`;

const UploadIcon = styled.div`
  font-size: 3rem;
  color: #0ea5e9;
  margin-bottom: 16px;
  display: block;
`;

const UploadTitle = styled.h3`
  font-size: 1.5rem;
  font-weight: 700;
  color: #0c4a6e;
  margin: 0 0 8px 0;
`;

const UploadSubtitle = styled.p`
  font-size: 1rem;
  color: #0369a1;
  margin: 0 0 20px 0;
  font-weight: 500;
`;

const UploadButton = styled.button`
  background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%);
  color: white;
  border: none;
  padding: 16px 32px;
  border-radius: 10px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 auto;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(14, 165, 233, 0.4);
  }

  &:active {
    transform: translateY(0);
  }
`;

const FileInput = styled.input`
  display: none;
`;

const PreviousUploadsSection = styled.div`
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
  padding-bottom: 8px;
  border-bottom: 2px solid #e5e7eb;
`;

const UploadsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const UploadItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  background: white;
  border: 1px solid #e0f2fe;
  border-radius: 12px;
  transition: all 0.3s ease;
  box-shadow: 0 1px 3px rgba(14, 165, 233, 0.1);

  &:hover {
    border-color: #0ea5e9;
    box-shadow: 0 4px 12px rgba(14, 165, 233, 0.15);
    transform: translateY(-2px);
  }
`;

const UploadInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
`;

const UploadIconSmall = styled.div`
  font-size: 1.5rem;
  color: #0ea5e9;
`;

const UploadDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const UploadName = styled.h4`
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
`;

const UploadMeta = styled.span`
  font-size: 0.9rem;
  color: #6b7280;
  font-weight: 500;
`;

const StatusBadge = styled.span`
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  background: ${props => {
    switch (props.status) {
      case 'ready': return '#dbeafe';
      case 'processing': return '#fef3c7';
      case 'error': return '#fecaca';
      default: return '#f0f9ff';
    }
  }};
  color: ${props => {
    switch (props.status) {
      case 'ready': return '#1e40af';
      case 'processing': return '#92400e';
      case 'error': return '#dc2626';
      default: return '#6b7280';
    }
  }};
`;

const ActionButton = styled.button`
  background: #f0f9ff;
  border: 1px solid #e0f2fe;
  color: #0ea5e9;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.3s ease;
  font-size: 1rem;

  &:hover {
    background: #0ea5e9;
    color: white;
    border-color: #0ea5e9;
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
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 8px;
  margin: 16px 0;
  font-size: 0.9rem;
  text-align: center;
`;

const EmptyState = styled.div`
  text-align: center;
  color: #6b7280;
  padding: 40px 20px;
  font-size: 1rem;
`;

const QuestionsSection = styled.div`
  margin-top: 24px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e0f2fe;
  overflow: hidden;
`;

const QuestionsHeader = styled.div`
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  padding: 20px;
  border-bottom: 1px solid #e0f2fe;
`;

const QuestionsTitle = styled.h3`
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: #0c4a6e;
`;

const QuestionsList = styled.div`
  max-height: 800px;
  overflow-y: auto;
  padding-bottom: 40px;
`;

const QuestionItem = styled.div`
  padding: 20px;
  border-bottom: 1px solid #f1f5f9;
  
  &:last-child {
    border-bottom: none;
  }
`;

const QuestionFooter = styled.div`
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
`;

const AnswerButton = styled.button`
  background: #f0f9ff;
  border: 1px solid #e0f2fe;
  color: #0ea5e9;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
  font-size: 0.9rem;
  font-weight: 500;

  &:hover {
    background: #0ea5e9;
    color: white;
    border-color: #0ea5e9;
  }
`;

const QuestionHeader = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
`;

const QuestionId = styled.span`
  background: #0ea5e9;
  color: white;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  min-width: 30px;
  text-align: center;
`;

const QuestionText = styled.p`
  margin: 0;
  font-size: 1rem;
  color: #111827;
  line-height: 1.5;
  flex: 1;
`;

const QuestionReference = styled.div`
  margin-top: 8px;
  padding: 8px 12px;
  background: #f8fafc;
  border-left: 3px solid #0ea5e9;
  border-radius: 0 6px 6px 0;
  font-size: 0.9rem;
  color: #475569;
  font-style: italic;
`;

const NoReference = styled.div`
  margin-top: 8px;
  padding: 8px 12px;
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
  border-radius: 0 6px 6px 0;
  font-size: 0.9rem;
  color: #92400e;
  font-style: italic;
`;

const ViewQuestionsButton = styled.button`
  background: #f0f9ff;
  border: 1px solid #e0f2fe;
  color: #0ea5e9;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
  font-size: 0.9rem;
  font-weight: 500;

  &:hover {
    background: #0ea5e9;
    color: white;
    border-color: #0ea5e9;
  }
`;

const CloseQuestionsButton = styled.button`
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
  font-size: 0.9rem;
  font-weight: 500;
  margin-left: 8px;

  &:hover {
    background: #dc2626;
    color: white;
    border-color: #dc2626;
  }
`;

const ThinkingState = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 1px solid #f59e0b;
  border-radius: 8px;
  margin: 12px 0;
  animation: pulse 2s infinite;
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }
`;

const ThinkingIcon = styled.div`
  font-size: 1.2rem;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const ThinkingText = styled.span`
  color: #92400e;
  font-weight: 600;
  font-size: 1rem;
`;

const AnswerContainer = styled.div`
  margin-top: 16px;
  padding: 20px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
`;

const AnswerHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f3f4f6;
`;

const AnswerStatus = styled.span`
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
  text-transform: uppercase;
  background: ${props => props.answer === 'YES' ? '#dbeafe' : '#fecaca'};
  color: ${props => props.answer === 'YES' ? '#1e40af' : '#dc2626'};
`;

const AnswerContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const AnswerSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const AnswerLabel = styled.span`
  font-weight: 600;
  color: #374151;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const AnswerText = styled.div`
  color: #111827;
  line-height: 1.6;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  border-left: 4px solid #3b82f6;
`;

const EvidenceText = styled.div`
  color: #6b7280;
  font-style: italic;
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 6px;
  border-left: 3px solid #9ca3af;
`;

const QuoteText = styled.div`
  color: #1f2937;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 8px;
  border-left: 4px solid #0ea5e9;
  font-family: 'Courier New', monospace;
  font-size: 0.95rem;
  line-height: 1.5;
`;

const DetailedAnswerModal = styled.div`
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

const DetailedAnswerContent = styled.div`
  background: white;
  border-radius: 12px;
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
`;

const DetailedAnswerHeader = styled.div`
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const DetailedAnswerTitle = styled.h2`
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

const DetailedAnswerBody = styled.div`
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const DetailSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const DetailLabel = styled.h3`
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const DetailValue = styled.div`
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border-left: 4px solid #3b82f6;
  color: #111827;
  line-height: 1.6;
`;

const SourceInfo = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 8px;
`;

const SourceItem = styled.div`
  padding: 12px;
  background: #f0f9ff;
  border-radius: 6px;
  border: 1px solid #e0f2fe;
`;

const SourceLabel = styled.span`
  font-weight: 600;
  color: #0c4a6e;
  font-size: 0.9rem;
`;

const SourceValue = styled.span`
  color: #0369a1;
  margin-left: 8px;
`;

const RelatedChunks = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
`;

const RelatedChunk = styled.div`
  padding: 12px;
  background: #f8fafc;
  border-radius: 6px;
  border-left: 3px solid #94a3b8;
  font-size: 0.9rem;
  color: #475569;
`;

const ChunkPage = styled.span`
  font-weight: 600;
  color: #0ea5e9;
  margin-right: 8px;
`;

const LoadingSpinner = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #6b7280;
  font-size: 1.1rem;
`;


function QuestionnairePanel({ selectedQuestionnaire, questions, onCloseQuestions, onViewQuestions }) {
  const [questionnaires, setQuestionnaires] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [internalSelectedQuestionnaire, setInternalSelectedQuestionnaire] = useState(null);
  const [internalQuestions, setInternalQuestions] = useState([]);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [answeringQuestions, setAnsweringQuestions] = useState(new Set());
  const [questionAnswers, setQuestionAnswers] = useState({});
  const [detailedAnswer, setDetailedAnswer] = useState(null);
  const [showDetailedAnswer, setShowDetailedAnswer] = useState(false);
  const [loadingDetailedAnswer, setLoadingDetailedAnswer] = useState(false);

  useEffect(() => {
    loadQuestionnaires();
  }, []);

  const loadQuestionnaires = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔄 Loading questionnaires...');
      const data = await getQuestionnaires();
      console.log('✅ Questionnaires loaded:', data);
      setQuestionnaires(data || []);
    } catch (err) {
      console.error('❌ Error loading questionnaires:', err);
      setError('Failed to load questionnaires. Please check your connection.');
      setQuestionnaires([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      alert('Please upload a PDF file');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      console.log('🔄 Uploading questionnaire:', file.name);
      
      const result = await uploadQuestionnaire(file);
      console.log('✅ Upload result:', result);
      
      // Reload questionnaires
      await loadQuestionnaires();
      alert('Questionnaire uploaded successfully!');
    } catch (err) {
      console.error('❌ Upload error:', err);
      setError('Failed to upload questionnaire. Please try again.');
    } finally {
      setUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const handleRefresh = () => {
    loadQuestionnaires();
  };

  const handleViewQuestions = async (questionnaire) => {
    try {
      setLoadingQuestions(true);
      setError(null);
      console.log('🔄 Loading questions for questionnaire:', questionnaire._id || questionnaire.id);
      
      const data = await getQuestionnaireQuestionsFormatted(questionnaire._id || questionnaire.id);
      console.log('✅ Questions loaded:', data);
      
      // Load existing answers for this questionnaire
      const existingAnswers = await getAuditAnswers(null, questionnaire._id || questionnaire.id);
      console.log('✅ Existing answers loaded:', existingAnswers);
      
      // Create a map of question_id to answer
      const answerMap = {};
      existingAnswers.forEach(answer => {
        answerMap[answer.question_id] = answer;
      });
      
      // Update questions with answered status and existing answers
      const questionsWithAnswers = data.questions.map(question => ({
        ...question,
        answered: answerMap[question.question_id] ? true : question.answered || false,
        existingAnswer: answerMap[question.question_id] || null
      }));
      
      if (onViewQuestions) {
        // If callback provided, use it to communicate with parent
        onViewQuestions(questionnaire, questionsWithAnswers);
      } else {
        // Internal state management for standalone mode
        setInternalSelectedQuestionnaire(questionnaire);
        setInternalQuestions(questionsWithAnswers);
      }
    } catch (err) {
      console.error('❌ Error loading questions:', err);
      setError('Failed to load questions. Please try again.');
    } finally {
      setLoadingQuestions(false);
    }
  };

  const handleCloseQuestions = () => {
    if (onCloseQuestions) {
      onCloseQuestions();
    } else {
      setInternalSelectedQuestionnaire(null);
      setInternalQuestions([]);
    }
  };

  const handleAnswerQuestion = async (question) => {
    const questionId = question.question_id;
    
    try {
      // First, fetch and print the question details to console
      console.log('🔍 FETCHING QUESTION DETAILS:');
      console.log('Question ID:', questionId);
      console.log('Question Object:', question);
      console.log('Question Text:', question.text || question.requirement);
      console.log('Question Number:', question.question_number);
      console.log('Question Type:', question.question_type);
      console.log('All Question Properties:', Object.keys(question));
      console.log('QID:', question.qid);
      console.log('Reference:', question.reference);
      console.log('Tags:', question.tags);
      console.log('--- END QUESTION DETAILS ---');
      
      // Check if answer already exists in local state
      const existingAnswer = questionAnswers[questionId];
      if (existingAnswer) {
        console.log('✅ Answer already exists in local state for question:', questionId);
        return;
      }

      // Check if answer exists in question data (from database)
      if (question.existingAnswer) {
        console.log('✅ Answer already exists in database for question:', questionId);
        setQuestionAnswers(prev => ({
          ...prev,
          [questionId]: question.existingAnswer
        }));
        return;
      }

      // Always make API call - the API will return cached answer if it exists

      // Set thinking state
      setAnsweringQuestions(prev => new Set([...prev, questionId]));
      setError(null);

      // Call both APIs in parallel
      let result, evidenceResult;
      try {
        [result, evidenceResult] = await Promise.all([
          answerAuditQuestion(questionId),
          findEvidenceForQuestion(questionId)
        ]);
      } catch (error) {
        // Try individual calls to see which one fails
        try {
          result = await answerAuditQuestion(questionId);
        } catch (deepseekError) {
          console.error('DeepSeek API failed:', deepseekError);
        }
        
        try {
          evidenceResult = await findEvidenceForQuestion(questionId);
        } catch (evidenceError) {
          console.error('Evidence API failed:', evidenceError);
        }
        
        // Even if there's an error, try to store what we have
        if (result && result.success && result.answer) {
          const answerWithEvidence = {
            ...result.answer,
            evidence_data: evidenceResult?.evidence || null
          };
          
          setQuestionAnswers(prev => ({
            ...prev,
            [questionId]: answerWithEvidence
          }));
        }
        
        throw error;
      }
      
      if (result && result.success && result.answer) {
        // Store the answer with evidence data
        const answerWithEvidence = {
          ...result.answer,
          evidence_data: evidenceResult?.evidence || null
        };
        
        setQuestionAnswers(prev => ({
          ...prev,
          [questionId]: answerWithEvidence
        }));
        
        // If this was a new answer (not from cache), update the question's answered status
        if (!result.from_cache) {
          // Update the question in the current questions list
          const updatedQuestions = (questions || internalQuestions).map(q => 
            q.question_id === questionId ? { ...q, answered: true, existingAnswer: result.answer } : q
          );
          
          if (onViewQuestions) {
            // Update parent state if callback provided
            onViewQuestions(selectedQuestionnaire, updatedQuestions);
          } else {
            // Update internal state
            setInternalQuestions(updatedQuestions);
          }
        }
      } else {
        throw new Error('Failed to get answer from API');
      }
      
    } catch (err) {
      console.error('❌ Error answering question:', err);
      setError(`Failed to answer question: ${err.message}`);
    } finally {
      // Remove thinking state
      setAnsweringQuestions(prev => {
        const newSet = new Set(prev);
        newSet.delete(questionId);
        return newSet;
      });
    }
  };

  const handleViewDetailedAnswer = async (question) => {
    const questionId = question.question_id;
    
    try {
      setLoadingDetailedAnswer(true);
      setError(null);
      
      console.log('🔍 Loading detailed answer for question:', questionId);
      
      // Get detailed answer information
      const detailedAnswerData = await getAnswerDetails(questionId);
      
      setDetailedAnswer(detailedAnswerData);
      setShowDetailedAnswer(true);
      
      console.log('✅ Detailed answer loaded:', detailedAnswerData);
      
    } catch (err) {
      console.error('❌ Error loading detailed answer:', err);
      setError(`Failed to load detailed answer: ${err.message}`);
    } finally {
      setLoadingDetailedAnswer(false);
    }
  };

  const handleCloseDetailedAnswer = () => {
    setShowDetailedAnswer(false);
    setDetailedAnswer(null);
  };

  const renderAnswer = (question) => {
    const questionId = question.question_id;
    const answer = questionAnswers[questionId] || question.existingAnswer;
    const isThinking = answeringQuestions.has(questionId);

    if (isThinking) {
      return (
        <ThinkingState>
          <ThinkingIcon>🤔</ThinkingIcon>
          <ThinkingText>Thinking...</ThinkingText>
        </ThinkingState>
      );
    }

    if (!answer) {
      return null;
    }

    return (
      <AnswerContainer>
        <AnswerHeader>
          <AnswerStatus answer={answer.answer}>
            {answer.answer}
          </AnswerStatus>
          <span style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            Confidence: {Math.round((answer.confidence || 0) * 100)}%
          </span>
          {question.answered && (
            <span style={{ 
              color: '#059669', 
              fontSize: '0.8rem', 
              fontWeight: '600',
              marginLeft: '12px',
              padding: '2px 8px',
              backgroundColor: '#d1fae5',
              borderRadius: '12px'
            }}>
              ✓ Answered
            </span>
          )}
        </AnswerHeader>
        
        <AnswerContent>
          {answer.answer === 'YES' && (
            <AnswerSection>
              <AnswerLabel>Evidence</AnswerLabel>
              <EvidenceText>
                {answer.evidence_data ? 
                  `${answer.evidence_data.most_relevant_document} (Page ${answer.evidence_data.page_number || 1})` : 
                  answer.evidence ? 
                    `${answer.evidence.filename} (Page ${answer.evidence.page || answer.page_number || 1})` : 
                    'None found'
                }
              </EvidenceText>
            </AnswerSection>
          )}
          
          
          {answer.answer === 'YES' && (answer.key_evidence || (answer.evidence && answer.evidence.key_evidence)) && (
            <AnswerSection>
              <AnswerLabel>Key Evidence</AnswerLabel>
              <QuoteText style={{ fontStyle: 'italic', backgroundColor: '#f8fafc', padding: '12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                "{answer.key_evidence || answer.evidence.key_evidence}"
              </QuoteText>
            </AnswerSection>
          )}
        </AnswerContent>
      </AnswerContainer>
    );
  };

  // If we have questions passed as props, show them directly as an overlay
  if (selectedQuestionnaire && questions) {
    return (
      <Container style={{ padding: '0', height: '100%' }}>
        <QuestionsSection style={{ margin: '0', borderRadius: '0', border: 'none', height: '100%' }}>
          <QuestionsHeader>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <QuestionsTitle>
                Questions from {selectedQuestionnaire.filename}
              </QuestionsTitle>
              <CloseQuestionsButton onClick={handleCloseQuestions}>
                Close
              </CloseQuestionsButton>
            </div>
          </QuestionsHeader>
          
          <QuestionsList style={{ maxHeight: 'none', height: 'calc(100% - 80px)' }}>
            {questions.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center' }}>
                <EmptyState>No questions found in this questionnaire.</EmptyState>
              </div>
            ) : (
              questions.map((question, index) => (
                <QuestionItem key={index}>
                  <QuestionHeader>
                    <QuestionText>{question.text || question.requirement}</QuestionText>
                  </QuestionHeader>
                  {question.reference ? (
                    <QuestionReference>
                      <strong>Reference:</strong> {question.reference}
                    </QuestionReference>
                  ) : (
                    <NoReference>
                      No reference information available
                    </NoReference>
                  )}
                  <QuestionFooter>
                    {question.answered || questionAnswers[question.question_id] || question.existingAnswer ? (
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <AnswerButton 
                          onClick={() => handleAnswerQuestion(question)}
                          disabled={answeringQuestions.has(question.question_id)}
                          style={{
                            backgroundColor: '#f0f9ff',
                            color: '#0ea5e9',
                            borderColor: '#e0f2fe'
                          }}
                        >
                          {answeringQuestions.has(question.question_id) ? 'Thinking...' : 'Answer'}
                        </AnswerButton>
                      </div>
                    ) : (
                      <AnswerButton 
                        onClick={() => handleAnswerQuestion(question)}
                        disabled={answeringQuestions.has(question.question_id)}
                        style={{
                          backgroundColor: '#f0f9ff',
                          color: '#0ea5e9',
                          borderColor: '#e0f2fe'
                        }}
                      >
                        {answeringQuestions.has(question.question_id) ? 'Thinking...' : 'Answer'}
                      </AnswerButton>
                    )}
                  </QuestionFooter>
                  {renderAnswer(question)}
                </QuestionItem>
              ))
            )}
          </QuestionsList>
        </QuestionsSection>
      </Container>
    );
  }

  if (loading) {
    return (
      <Container>
        <LoadingMessage>Loading questionnaires...</LoadingMessage>
      </Container>
    );
  }

  return (
    <Container>
      <UploadSection onClick={() => document.getElementById('fileInput').click()}>
        <FileInput
          id="fileInput"
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          disabled={uploading}
        />
        <UploadIcon>📄</UploadIcon>
        <UploadTitle>Upload Questionnaire PDF</UploadTitle>
        <UploadSubtitle>Drag and drop a PDF file or click to browse</UploadSubtitle>
        <UploadButton disabled={uploading}>
          {uploading ? 'Uploading...' : 'Choose File'}
        </UploadButton>
      </UploadSection>

      {error && <ErrorMessage>{error}</ErrorMessage>}

      <PreviousUploadsSection>
        <SectionTitle>Previous Uploads</SectionTitle>
        {questionnaires.length === 0 ? (
          <EmptyState>No questionnaires uploaded yet. Upload your first questionnaire to get started.</EmptyState>
        ) : (
          <UploadsList>
            {questionnaires.map((questionnaire) => (
              <UploadItem key={questionnaire._id || questionnaire.id}>
                <UploadInfo>
                  <UploadIconSmall>📋</UploadIconSmall>
                  <UploadDetails>
                    <UploadName>{questionnaire.filename}</UploadName>
                    <UploadMeta>
                      {new Date(questionnaire.uploadedAt).toLocaleDateString()} • 
                      {questionnaire.questions?.length || 0} questions
                    </UploadMeta>
                  </UploadDetails>
                </UploadInfo>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <StatusBadge status={questionnaire.status || 'ready'}>
                    {questionnaire.status || 'ready'}
                  </StatusBadge>
                  <ViewQuestionsButton 
                    onClick={() => handleViewQuestions(questionnaire)}
                    disabled={loadingQuestions}
                    title="View Questions"
                  >
                    {loadingQuestions ? 'Loading...' : 'View Questions'}
                  </ViewQuestionsButton>
                  <ActionButton onClick={handleRefresh} title="Refresh">
                    🔄
                  </ActionButton>
                </div>
              </UploadItem>
            ))}
          </UploadsList>
        )}
      </PreviousUploadsSection>

      {/* Detailed Answer Modal */}
      {showDetailedAnswer && detailedAnswer && (
        <DetailedAnswerModal onClick={handleCloseDetailedAnswer}>
          <DetailedAnswerContent onClick={(e) => e.stopPropagation()}>
            <DetailedAnswerHeader>
              <DetailedAnswerTitle>Answer Details</DetailedAnswerTitle>
              <CloseButton onClick={handleCloseDetailedAnswer}>Close</CloseButton>
            </DetailedAnswerHeader>
            
            <DetailedAnswerBody>
              <DetailSection>
                <DetailLabel>Question</DetailLabel>
                <DetailValue>{detailedAnswer.question}</DetailValue>
              </DetailSection>

              <DetailSection>
                <DetailLabel>Answer</DetailLabel>
                <DetailValue>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '12px',
                    marginBottom: '12px'
                  }}>
                    <span style={{
                      padding: '6px 12px',
                      borderRadius: '20px',
                      fontSize: '0.9rem',
                      fontWeight: '600',
                      textTransform: 'uppercase',
                      backgroundColor: detailedAnswer.answer === 'YES' ? '#dbeafe' : '#fecaca',
                      color: detailedAnswer.answer === 'YES' ? '#1e40af' : '#dc2626'
                    }}>
                      {detailedAnswer.answer}
                    </span>
                    <span style={{ color: '#6b7280', fontSize: '0.9rem' }}>
                      Confidence: {Math.round((detailedAnswer.confidence || 0) * 100)}%
                    </span>
                  </div>
                </DetailValue>
              </DetailSection>

              <DetailSection>
                <DetailLabel>Source Information</DetailLabel>
                <DetailValue>
                  <SourceInfo>
                    <SourceItem>
                      <SourceLabel>Document:</SourceLabel>
                      <SourceValue>{detailedAnswer.evidence_data?.most_relevant_document || detailedAnswer.source?.document_name || 'Unknown'} (Page {detailedAnswer.evidence_data?.page_number || detailedAnswer.source?.page_number || detailedAnswer.evidence?.page || 1})</SourceValue>
                    </SourceItem>
                    
                    <SourceItem>
                      <SourceLabel>Policy ID:</SourceLabel>
                      <SourceValue>{detailedAnswer.source?.policy_id || 'Unknown'}</SourceValue>
                    </SourceItem>
                    <SourceItem>
                      <SourceLabel>Created:</SourceLabel>
                      <SourceValue>
                        {detailedAnswer.created_at ? 
                          new Date(detailedAnswer.created_at).toLocaleString() : 
                          'Unknown'
                        }
                      </SourceValue>
                    </SourceItem>
                  </SourceInfo>
                </DetailValue>
              </DetailSection>

              <DetailSection>
                <DetailLabel>Reasoning</DetailLabel>
                <DetailValue>
                  <QuoteText>
                    {detailedAnswer.reasoning || 'No reasoning available'}
                  </QuoteText>
                </DetailValue>
              </DetailSection>

              {detailedAnswer.related_chunks && detailedAnswer.related_chunks.length > 0 && (
                <DetailSection>
                  <DetailLabel>Related Information</DetailLabel>
                  <DetailValue>
                    <RelatedChunks>
                      {detailedAnswer.related_chunks.map((chunk, index) => (
                        <RelatedChunk key={index}>
                          {chunk.text}
                        </RelatedChunk>
                      ))}
                    </RelatedChunks>
                  </DetailValue>
                </DetailSection>
              )}
            </DetailedAnswerBody>
          </DetailedAnswerContent>
        </DetailedAnswerModal>
      )}

      {(selectedQuestionnaire || internalSelectedQuestionnaire) && (
        <QuestionsSection>
          <QuestionsHeader>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <QuestionsTitle>
                Questions from {(selectedQuestionnaire || internalSelectedQuestionnaire).filename}
              </QuestionsTitle>
              <CloseQuestionsButton onClick={handleCloseQuestions}>
                Close
              </CloseQuestionsButton>
            </div>
          </QuestionsHeader>
          
          {loadingQuestions ? (
            <div style={{ padding: '40px', textAlign: 'center' }}>
              <LoadingMessage>Loading questions...</LoadingMessage>
            </div>
          ) : (
            <QuestionsList>
              {(questions || internalQuestions).length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center' }}>
                  <EmptyState>No questions found in this questionnaire.</EmptyState>
                </div>
              ) : (
                (questions || internalQuestions).map((question, index) => (
                  <QuestionItem key={index}>
                    <QuestionHeader>
                      <QuestionText>{question.text || question.requirement}</QuestionText>
                    </QuestionHeader>
                    {question.reference ? (
                      <QuestionReference>
                        <strong>Reference:</strong> {question.reference}
                      </QuestionReference>
                    ) : (
                      <NoReference>
                        No reference information available
                      </NoReference>
                    )}
                    <QuestionFooter>
                      {question.answered || questionAnswers[question.question_id] || question.existingAnswer ? (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <AnswerButton 
                            onClick={() => handleAnswerQuestion(question)}
                            disabled={answeringQuestions.has(question.question_id)}
                            style={{
                              backgroundColor: '#f0f9ff',
                              color: '#0ea5e9',
                              borderColor: '#e0f2fe'
                            }}
                          >
                            {answeringQuestions.has(question.question_id) ? 'Thinking...' : 'Re-answer'}
                          </AnswerButton>
                        </div>
                      ) : (
                        <AnswerButton 
                          onClick={() => handleAnswerQuestion(question)}
                          disabled={answeringQuestions.has(question.question_id)}
                          style={{
                            backgroundColor: '#f0f9ff',
                            color: '#0ea5e9',
                            borderColor: '#e0f2fe'
                          }}
                        >
                          {answeringQuestions.has(question.question_id) ? 'Thinking...' : 'Answer'}
                        </AnswerButton>
                      )}
                    </QuestionFooter>
                    {renderAnswer(question)}
                  </QuestionItem>
                ))
              )}
            </QuestionsList>
          )}
        </QuestionsSection>
      )}
    </Container>
  );
}

export default QuestionnairePanel;
