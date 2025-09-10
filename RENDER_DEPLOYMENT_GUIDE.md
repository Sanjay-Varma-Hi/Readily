# Render Deployment Guide for READILY

This guide addresses the 502 Bad Gateway error and MongoDB SSL issues on Render.

## 🔧 Issues Fixed

### 1. Port Configuration
- **Problem**: Application was hardcoded to port 8000, but Render expects PORT environment variable
- **Solution**: Updated `main.py` to use `os.getenv("PORT", 8000)`

### 2. Health Check Endpoints
- **Problem**: Render health checks were failing with 405 Method Not Allowed
- **Solution**: Added multiple health check endpoints:
  - `GET /` - Root endpoint
  - `GET /health` - Basic health check
  - `GET /healthz` - Kubernetes-style health check
  - `HEAD /` and `HEAD /health` - For HEAD requests

### 3. MongoDB SSL Configuration
- **Problem**: SSL parameter conflicts between connection string and client constructor
- **Solution**: Removed SSL parameters from AsyncIOMotorClient, let connection string handle SSL

### 4. Environment-Specific Configuration
- **Problem**: Same configuration for local and production
- **Solution**: Created environment-specific settings and connection parameters

### 5. Driver Version Compatibility
- **Problem**: Unpinned versions causing compatibility issues
- **Solution**: Pinned all package versions for stability

## 🚀 Render Configuration

### Build Command
Set this in your Render service settings:
```bash
pip install --upgrade pip && pip install -r backend/requirements.txt
```

### Python Version
Set this environment variable in Render:
```
PYTHON_VERSION=3.11
```

### Required Environment Variables
```
MONGODB_URI=mongodb+srv://sanjayvarmacol2:Sanjay1234@cluster01.inf1rib.mongodb.net/policiesdb?retryWrites=true&w=majority&appName=Cluster01
DB_NAME=policiesdb
RENDER=true
```

### Optional Variables
```
DEBUG=False
LOG_LEVEL=INFO
CHUNK_TOKENS=800
CHUNK_OVERLAP=120
MAX_PARALLEL_QUESTIONS=6
MAX_FILE_SIZE_MB=50
ALLOWED_EXTENSIONS=pdf,docx,txt
```

## 🔍 Health Check Configuration

In Render dashboard:
1. Go to your service settings
2. Set **Health Check Path** to `/healthz`
3. Set **Health Check Timeout** to 30 seconds

## 📦 Package Versions

All packages are now pinned to stable versions:
- `fastapi==0.104.1`
- `uvicorn[standard]==0.24.0`
- `pymongo==4.6.1`
- `motor==3.3.2`
- `python-dotenv==1.0.0`
- And more...

## 🌍 Environment Detection

The application automatically detects if it's running on Render:
- Checks for `RENDER=true` environment variable
- Uses production-specific connection parameters
- Adjusts timeouts and pool sizes for production

## 🔒 MongoDB Atlas Configuration

Ensure your MongoDB Atlas cluster:
1. Allows connections from `0.0.0.0/0` (all IPs)
2. Has proper user permissions
3. Uses the correct connection string format

## 🐛 Troubleshooting

### If you still get 502 errors:
1. Check Render logs for startup errors
2. Verify all environment variables are set
3. Test the health check endpoint manually
4. Check MongoDB Atlas network access settings

### If you get SSL errors:
1. Verify the connection string format
2. Check MongoDB Atlas SSL settings
3. Ensure you're using the pinned driver versions

## 📝 Testing Locally

Test the production configuration locally:
```bash
export RENDER=true
export MONGODB_URI="your_production_uri"
cd backend
python main.py
```

## 🎯 Next Steps

1. Update Render environment variables
2. Set health check path to `/healthz`
3. Redeploy your service
4. Monitor logs for any remaining issues

The application should now work correctly on Render without 502 errors or SSL issues.
