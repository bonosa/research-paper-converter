# Research Paper Converter - Full AI Version

A powerful web application that converts PDF research papers to Markdown format using Microsoft's MarkItDown and IBM's Docling libraries with full AI capabilities.

## Features

- **Advanced AI Processing**: Microsoft MarkItDown + IBM Docling
- **Complex Document Support**: Mathematical formulas, tables, diagrams
- **Multi-language Support**: Handles German, English, and other languages
- **User Authentication**: JWT token-based security
- **PostgreSQL Database**: Secure data storage
- **Professional UI**: Bootstrap 5 responsive design
- **7-day Trial License**: (modifiable by code-savvy users)

## AI Capabilities

✅ **Smart Content Extraction**: Understands document structure
✅ **Formula Processing**: Handles mathematical equations
✅ **Table Recognition**: Preserves table formatting
✅ **Multi-modal Analysis**: Text, images, and layout understanding
✅ **Language Detection**: Supports multiple languages
✅ **Academic Paper Optimization**: Designed for research documents

## Deployment on Railway.app

Railway.app is perfect for AI applications with large dependencies:

### Quick Deploy Steps:

1. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Deploy from GitHub**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your repository

3. **Add PostgreSQL Database**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway auto-connects DATABASE_URL

4. **Set Environment Variables**
   - Go to your service settings
   - Add: `SESSION_SECRET` (generate random 32-character string)
   - Railway handles PORT automatically

5. **Deploy**
   - Railway automatically builds and deploys
   - Handles large AI libraries (no 8GB limit)
   - Gets custom railway.app domain

### Why Railway.app for AI Apps:

- ✅ **No Size Limits**: Handles large AI libraries
- ✅ **$5/month**: Cheaper than Replit
- ✅ **Auto-scaling**: Handles traffic spikes
- ✅ **GitHub Integration**: Auto-deploys on push
- ✅ **Free PostgreSQL**: Database included
- ✅ **SSL/HTTPS**: Automatic certificates

## Alternative Deployment Options

### Fly.io (Free Tier Available)
```bash
flyctl launch
flyctl postgres create
flyctl deploy
```

### DigitalOcean App Platform ($5/month)
- Upload repository
- Add PostgreSQL database
- Set environment variables
- Deploy

## Cost Comparison

| Platform | Monthly Cost | AI Libraries | Database | Auto-deploy |
|----------|--------------|--------------|----------|-------------|
| Railway.app | $5 | ✅ | ✅ | ✅ |
| Fly.io | Free/$5 | ✅ | ✅ | ✅ |
| DigitalOcean | $5 | ✅ | ✅ | ✅ |
| Replit | $7-10 | ✅ | ✅ | ✅ |
| Render.com | Free | ❌ Size limit | ✅ | ✅ |

## Environment Variables

Set these in your Railway dashboard:
```
DATABASE_URL=postgresql://...  (auto-configured)
SESSION_SECRET=your-32-char-secret
PORT=3000  (auto-configured)
```

## Local Development

```bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://localhost/research_papers"
export SESSION_SECRET="your-secret-key"
python main.py
```

## Files Included

- `main.py` - Full Flask app with AI processing
- `requirements.txt` - All dependencies including AI libraries
- `templates/index.html` - Complete frontend interface
- `railway.json` - Railway deployment configuration
- `nixpacks.toml` - Build configuration

## Tech Stack

- **AI Processing**: MarkItDown, Docling, Anthropic
- **Backend**: Python Flask, SQLAlchemy
- **Database**: PostgreSQL
- **Frontend**: HTML, Bootstrap 5, JavaScript
- **Authentication**: JWT tokens with bcrypt
- **Deployment**: Railway.app with Nixpacks

## Support

This version maintains all advanced AI capabilities while being optimized for Railway.app deployment. Perfect for processing complex academic papers with mathematical formulas and multi-language support.

*"More power to those who can change main.py!" - Deploy the full AI version on Railway.app*