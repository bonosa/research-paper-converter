# Deploy to Railway.app - Step by Step Guide

Railway.app is perfect for your AI-powered Research Paper Converter. No size limits, $5/month, and handles large AI libraries.

## Step 1: Create GitHub Repository

1. **Go to GitHub.com** and create new repository
2. **Name**: `research-paper-converter`
3. **Make it Public** (required for Railway free tier)
4. **Upload all files** from your deployment package

## Step 2: Deploy on Railway.app

1. **Sign up at railway.app** with GitHub
2. **Click "Deploy from GitHub repo"**
3. **Select your repository**
4. **Add PostgreSQL database** (New → Database → PostgreSQL)
5. **Set environment variable**: `SESSION_SECRET` (32-character random string)
6. **Deploy automatically**

## Step 3: Generate SESSION_SECRET

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 4: Test Deployment

1. Visit your Railway.app URL
2. Test registration and login
3. Upload a PDF and verify AI conversion works
4. Download the markdown file

## Why Railway.app?

- **No Docker Size Limits**: Handles MarkItDown + Docling
- **$5/month**: Cheaper than Replit
- **Auto-scaling**: Handles traffic
- **Free PostgreSQL**: Database included
- **SSL**: Automatic HTTPS

Your full AI-powered converter will be live in minutes!

## Troubleshooting

**Build failing?** Check requirements.txt is in root
**Database issues?** Verify PostgreSQL service is running
**AI libraries not working?** Railway handles them (unlike Render)

*Railway.app is built for AI applications like yours.*