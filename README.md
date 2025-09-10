# READILY - Policy Document Analysis Platform

A comprehensive policy document analysis system that uses DeepSeek for intelligent answer generation and MongoDB for document storage and retrieval. The platform enables organizations to upload policy documents, analyze questionnaires, and get AI-powered answers with proper citations and evidence.

## 🚀 Key Features

### 📁 **Document Management**
- **Multi-format Support**: Upload PDF, DOCX, and TXT documents
- **Organized Storage**: Categorize documents by policy type (Healthcare, Education, Environment, etc.)
- **Document Properties**: View detailed metadata including title, version, checksum, file size, and more
- **Google Drive Integration**: Direct links to source documents in Google Drive

### 📋 **Questionnaire Analysis**
- **Smart Extraction**: Automatically extract questions from uploaded questionnaire PDFs
- **Batch Processing**: Process multiple questions simultaneously
- **Question Management**: Organize and track questions by questionnaire

### 🤖 **AI-Powered Q&A System**
- **Intelligent Answering**: Uses DeepSeek AI for context-aware answer generation
- **Evidence-Based Responses**: Provides specific quotes and page references
- **Confidence Scoring**: Shows confidence levels for each answer
- **Chunk Rotation**: Ensures diverse answers by rotating through different document sections
- **Reasoning Display**: Shows detailed reasoning for each answer

### 🎨 **Modern UI/UX**
- **Clean Interface**: Modern, responsive design with hidden scrollbars
- **Interactive Modals**: Click any document to view detailed properties
- **Real-time Status**: Live updates on document processing status
- **Smooth Animations**: Professional transitions and hover effects

## 🏗️ Project Structure

```
/Readily
├── /frontend          # React frontend with styled-components
│   ├── /src
│   │   ├── /components
│   │   │   ├── MainLayout.js      # Main application layout
│   │   │   ├── PolicyPanel.js     # Policy document management
│   │   │   ├── FolderContents.js  # Document listing and properties
│   │   │   └── QuestionnairePanel.js # Question analysis interface
│   │   └── /services
│   │       └── api.js             # API service layer
├── /backend           # FastAPI backend
│   ├── /api
│   │   ├── policies.py           # Policy document endpoints
│   │   ├── questionnaires.py     # Questionnaire processing
│   │   └── audit_answers.py      # AI answer generation
│   ├── /core
│   │   ├── database.py           # MongoDB connection
│   │   ├── ingestion.py          # Document processing
│   │   └── audit_answering.py    # Answer logic
│   └── main.py                   # FastAPI application
├── /env               # Environment configuration
└── README.md
```

## ⚡ Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB (local or MongoDB Atlas)
- DeepSeek API key

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Sanjay-Varma-Hi/Readily.git
cd Readily

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install
```

### 2. Configuration

Copy and configure environment variables:

```bash
cp env/example.env .env
```

Edit `.env` with your settings:
```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
DB_NAME=policiesdb

# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

### 3. Start the Application

```bash
# Terminal 1 - Start Backend
cd backend
python main.py

# Terminal 2 - Start Frontend
cd frontend
npm start
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 API Endpoints

### Policy Documents
- `POST /api/policies` - Upload policy documents
- `GET /api/policies` - List all policy documents
- `DELETE /api/policies/{doc_id}` - Delete a document
- `POST /api/policies/folders` - Create policy folders
- `GET /api/policies/folders` - List policy folders
- `POST /api/policies/folders/{folder_id}/documents` - Upload to specific folder

### Questionnaires
- `POST /api/questionnaires` - Upload questionnaire PDFs
- `GET /api/questionnaires` - List questionnaires
- `DELETE /api/questionnaires/{id}` - Delete questionnaire

### AI Answering
- `POST /api/audit-answers/single` - Answer a single question
- `POST /api/audit-answers/batch` - Answer multiple questions
- `GET /api/audit-answers` - Retrieve saved answers

## 🎯 How It Works

### 1. **Document Upload**
- Upload policy documents in PDF, DOCX, or TXT format
- Documents are automatically processed and chunked
- Metadata is extracted and stored in MongoDB

### 2. **Questionnaire Processing**
- Upload questionnaire PDFs
- Questions are automatically extracted using AI
- Questions are organized by questionnaire

### 3. **AI Answer Generation**
- Select questions to answer
- AI searches through document chunks for relevant content
- Generates answers with evidence, reasoning, and page references
- Implements chunk rotation to ensure diverse responses

### 4. **Answer Display**
- Shows YES/NO answers with confidence scores
- Displays reasoning and evidence quotes
- Provides document source and page numbers
- Links to original documents in Google Drive

## 🛠️ Technical Stack

### Backend
- **FastAPI**: Modern Python web framework
- **MongoDB**: Document database for storage
- **DeepSeek API**: AI-powered answer generation
- **PyPDF2**: PDF text extraction
- **python-docx**: DOCX document processing

### Frontend
- **React**: Modern JavaScript framework
- **Styled Components**: CSS-in-JS styling
- **Axios**: HTTP client for API calls
- **Modern CSS**: Hidden scrollbars, smooth animations

## 🔒 Security Features

- **Input Validation**: All inputs are validated and sanitized
- **Error Handling**: Comprehensive error handling and logging
- **Rate Limiting**: Built-in protection against abuse
- **Secure File Upload**: File type and size validation

## 📊 Performance Features

- **Chunk Rotation**: Prevents repetitive answers
- **Caching**: Intelligent caching for improved performance
- **Background Processing**: Non-blocking document processing
- **Optimized Queries**: Efficient database queries

## 🚀 Deployment

The application is designed to be deployed in cloud environments. For production deployment:

1. **File Storage**: Configure cloud storage (AWS S3, Google Cloud Storage, etc.)
2. **Database**: Use MongoDB Atlas for production database
3. **Environment**: Set production environment variables
4. **Scaling**: Configure load balancing and auto-scaling

