#!/bin/bash

# Script to switch between local and production environments

if [ "$1" = "local" ]; then
    echo "Switching to local development environment..."
    echo "REACT_APP_API_URL=http://localhost:8000" > .env
    echo "REACT_APP_API_URL=http://localhost:8000" > .env.local
    echo "✅ Switched to local environment (http://localhost:8000)"
elif [ "$1" = "production" ]; then
    echo "Switching to production environment..."
    echo "REACT_APP_API_URL=https://readily-mgtk.onrender.com" > .env
    echo "REACT_APP_API_URL=https://readily-mgtk.onrender.com" > .env.local
    echo "✅ Switched to production environment (https://readily-mgtk.onrender.com)"
else
    echo "Usage: ./switch-env.sh [local|production]"
    echo ""
    echo "Examples:"
    echo "  ./switch-env.sh local      # Switch to local development"
    echo "  ./switch-env.sh production # Switch to production"
    echo ""
    echo "Current environment:"
    if grep -q "localhost" .env; then
        echo "  🏠 Local development (http://localhost:8000)"
    else
        echo "  🌐 Production (https://readily-mgtk.onrender.com)"
    fi
fi

