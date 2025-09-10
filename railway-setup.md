# Railway Deployment Guide for READILY

## Why Railway?
- ✅ Much simpler than Render
- ✅ Better free tier ($5/month credit)
- ✅ Auto-detects FastAPI
- ✅ Built-in MongoDB support
- ✅ No complex configuration

## Quick Setup Steps

### 1. Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Connect your repository

### 2. Deploy Backend
1. Click "New Project" → "Deploy from GitHub repo"
2. Select your READILY repository
3. Railway will auto-detect it's a Python app
4. Set the **Root Directory** to `backend`

### 3. Environment Variables
Add these in Railway dashboard:
```
MONGODB_URI=mongodb+srv://sanjayvarmacol2:Sanjay1234@cluster01.inf1rib.mongodb.net/policiesdb?retryWrites=true&w=majority&appName=Cluster01
DB_NAME=policiesdb
```

### 4. That's it!
- Railway handles the rest automatically
- Your app will be available at `https://your-app-name.railway.app`
- Updates automatically when you push to GitHub

## Required Files (Already in your project)

### Procfile (Create this in backend/ folder)
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### runtime.txt (Create this in backend/ folder)
```
python-3.11.0
```

## Benefits over Render
- 🚀 Faster deployments
- 📊 Better monitoring
- 🔧 Simpler configuration
- 💰 More generous free tier
- 🐛 Better error messages
- 📝 Cleaner logs

## Troubleshooting
If you have issues:
1. Check Railway logs (much clearer than Render)
2. Verify environment variables are set
3. Make sure PORT is used correctly (Railway sets this automatically)

## Next Steps
1. Create Railway account
2. Deploy your backend
3. Update your frontend CORS to use the new Railway URL
4. Enjoy stress-free hosting! 🎉
