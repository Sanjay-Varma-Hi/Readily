import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add any auth headers here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      console.error('Unauthorized access');
    }
    return Promise.reject(error);
  }
);

// Policy API functions
export const getPolicyFolders = async () => {
  const response = await api.get('/api/policies/folders');
  return response.data;
};

export const getFolderDocuments = async (policyType) => {
  const response = await api.get(`/api/policies/folders/${policyType}/documents`);
  return response.data;
};

export const uploadPolicy = async (formData) => {
  const response = await api.post('/api/policies', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const deletePolicy = async (docId) => {
  const response = await api.delete(`/api/policies/${docId}`);
  return response.data;
};

export const getPolicies = async (filters = {}) => {
  const params = new URLSearchParams();
  Object.keys(filters).forEach(key => {
    if (filters[key]) {
      params.append(key, filters[key]);
    }
  });
  
  const response = await api.get(`/api/policies?${params.toString()}`);
  return response.data;
};

// Questionnaire API functions
export const uploadQuestionnaire = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/api/questionnaires', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getQuestionnaires = async () => {
  const response = await api.get('/api/questionnaires');
  return response.data;
};

export const getQuestionnaire = async (questionnaireId) => {
  const response = await api.get(`/api/questionnaires/${questionnaireId}`);
  return response.data;
};

export const getQuestionnaireQuestions = async (questionnaireId) => {
  const response = await api.get(`/api/questionnaires/${questionnaireId}/questions`);
  return response.data;
};

export const getQuestionnaireQuestionsFormatted = async (questionnaireId) => {
  const response = await api.get(`/api/questionnaires/${questionnaireId}/questions-formatted`);
  return response.data;
};

export const deleteQuestionnaire = async (questionnaireId) => {
  const response = await api.delete(`/api/questionnaires/${questionnaireId}`);
  return response.data;
};

// Answer API functions
export const generateAnswers = async (questionnaireId, qids = null) => {
  const response = await api.post('/api/answers/batch', {
    questionnaire_id: questionnaireId,
    qids: qids
  });
  return response.data;
};

export const getAnswers = async (questionnaireId) => {
  const response = await api.get(`/api/answers?questionnaire_id=${questionnaireId}`);
  return response.data;
};

export const getAnswerSummary = async (questionnaireId) => {
  const response = await api.get(`/api/answers/${questionnaireId}/summary`);
  return response.data;
};

export const deleteAnswers = async (questionnaireId) => {
  const response = await api.delete(`/api/answers/${questionnaireId}`);
  return response.data;
};

// Audit Answer API functions
export const answerAuditQuestion = async (question, questionId = null) => {
  const response = await api.post('/api/audit-answers/single', {
    question: question,
    question_id: questionId
  });
  return response.data;
};

export const getAuditAnswer = async (questionId) => {
  const response = await api.get(`/api/audit-answers/${questionId}`);
  return response.data;
};

export const getAuditAnswers = async (questionId = null, questionnaireId = null) => {
  const params = new URLSearchParams();
  if (questionId) params.append('question_id', questionId);
  if (questionnaireId) params.append('questionnaire_id', questionnaireId);
  
  const queryString = params.toString();
  const response = await api.get(`/api/audit-answers${queryString ? `?${queryString}` : ''}`);
  return response.data;
};

export const deleteAuditAnswer = async (questionId) => {
  const response = await api.delete(`/api/audit-answers/${questionId}`);
  return response.data;
};

export const getAnswerDetails = async (questionId) => {
  const response = await api.get(`/api/audit-answers/${questionId}/details`);
  return response.data;
};

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;

