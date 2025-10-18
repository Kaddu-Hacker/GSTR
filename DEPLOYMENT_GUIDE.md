# Deployment Guide: GST Filing Automation

## Overview
This application consists of:
- **Frontend**: React app (deploy to Netlify)
- **Backend**: FastAPI with Supabase (deploy to Render/Railway)
- **Database**: Supabase PostgreSQL (already configured)

---

## Step 1: Setup Supabase Database

### 1.1 Create Tables
1. Go to your Supabase dashboard: https://cuqvhbyymoeeiumqbfge.supabase.co
2. Navigate to **SQL Editor**
3. Copy the SQL from `/app/backend/supabase_schema.sql`
4. Paste and run it in the SQL Editor
5. Verify tables are created: `uploads`, `invoice_lines`, `gstr_exports`

### 1.2 Verify Connection
```bash
cd /app
python3 scripts/init_supabase.py
```

---

## Step 2: Deploy Backend (FastAPI)

### Option A: Deploy to Render (Recommended)

1. **Create account**: https://render.com

2. **Create new Web Service**
   - Connect your GitHub repository
   - Or use the Render Blueprint:

3. **Configuration**:
   ```
   Name: gst-filing-backend
   Environment: Python 3
   Build Command: pip install -r backend/requirements.txt
   Start Command: cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
   ```

4. **Environment Variables** (in Render dashboard):
   ```
   SUPABASE_URL=https://cuqvhbyymoeeiumqbfge.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1cXZoYnl5bW9lZWl1bXFiZmdlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDYzOTg0MywiZXhwIjoyMDc2MjE1ODQzfQ.SYg6mEwrYhoZ3iNuizzPI4kdLcEPBLY2gTVAcIsLCXw
   GEMINI_API_KEY=AIzaSyBToUXh6mtAkBdwwO-UZsBhntZv_yeCAW8
   CORS_ORIGINS=*
   ```

5. **Deploy** and note your backend URL (e.g., `https://gst-filing-backend.onrender.com`)

### Option B: Deploy to Railway

1. **Create account**: https://railway.app

2. **New Project** → **Deploy from GitHub**

3. **Configuration**:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables** (same as above)

5. **Deploy** and note your backend URL

---

## Step 3: Deploy Frontend (React to Netlify)

### 3.1 Update Backend URL

1. Edit `/app/frontend/.env.production`:
   ```
   REACT_APP_BACKEND_URL=https://your-backend-url.onrender.com
   ```
   Replace with your actual backend URL from Step 2

### 3.2 Deploy to Netlify

#### Method 1: Netlify CLI (Recommended)

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login to Netlify
netlify login

# Navigate to frontend
cd /app/frontend

# Build the app
yarn build

# Deploy
netlify deploy --prod

# Follow prompts:
# - Create new site? Yes
# - Publish directory: build
```

#### Method 2: Netlify Dashboard

1. Go to https://app.netlify.com
2. Click "Add new site" → "Import an existing project"
3. Connect your Git repository
4. **Build settings**:
   ```
   Base directory: frontend
   Build command: yarn build
   Publish directory: frontend/build
   ```

5. **Environment variables**:
   ```
   REACT_APP_BACKEND_URL=https://your-backend-url.onrender.com
   ```

6. Click **Deploy site**

#### Method 3: Drag & Drop (Quick Test)

```bash
# Build the app
cd /app/frontend
yarn build

# Drag the 'build' folder to Netlify: https://app.netlify.com/drop
```

---

## Step 4: Test Deployment

### 4.1 Test Backend
```bash
curl https://your-backend-url.onrender.com/api/
# Should return: {"message":"GST Filing Automation API with AI","version":"2.0"}
```

### 4.2 Test Frontend
1. Open your Netlify URL
2. Upload test files
3. Verify GSTR generation works
4. Test download buttons

---

## Step 5: Custom Domain (Optional)

### Frontend (Netlify)
1. Go to Netlify dashboard → Site settings → Domain management
2. Add custom domain
3. Follow DNS configuration instructions

### Backend (Render/Railway)
1. Go to your backend service settings
2. Add custom domain
3. Update CORS_ORIGINS in backend .env

---

## Troubleshooting

### Backend Issues

**Error: "Could not find the table 'public.uploads'"**
- Run the SQL schema in Supabase dashboard (Step 1.1)

**Error: "CORS policy"**
- Update CORS_ORIGINS in backend environment variables
- Add your Netlify domain

**Error: "Gemini API rate limit"**
- The free tier has limits. Use your own API key if needed

### Frontend Issues

**Download button not working**
- Check browser console for errors
- Verify backend URL is correct in .env.production
- Check if GSTR data is generated (look in Network tab)

**Files not uploading**
- Check backend logs
- Verify file size limits (Netlify: 100MB, Render: depends on plan)

**Blank page after deployment**
- Check browser console
- Verify build completed successfully
- Check _redirects file exists in build folder

---

## Architecture Overview

```
┌─────────────────┐
│   Netlify       │
│   (Frontend)    │
│   React App     │
└────────┬────────┘
         │
         │ HTTPS
         │
┌────────▼────────────────┐
│   Render/Railway        │
│   (Backend)             │
│   FastAPI + Uvicorn     │
└────────┬────────────────┘
         │
         ├─────► Supabase (PostgreSQL)
         │
         └─────► Gemini AI (Google)
```

---

## Monitoring & Maintenance

### Logs
- **Backend**: Check Render/Railway logs dashboard
- **Frontend**: Netlify deploy logs and function logs
- **Database**: Supabase dashboard → Database → Logs

### Performance
- Monitor API response times
- Check Supabase database usage
- Monitor Gemini API quota

---

## Security Checklist

- [ ] Supabase RLS policies configured
- [ ] API keys stored in environment variables (not in code)
- [ ] CORS properly configured
- [ ] HTTPS enabled on all services
- [ ] Rate limiting configured (if needed)

---

## Cost Estimate (Free Tier)

- **Netlify**: Free (100GB bandwidth, unlimited sites)
- **Render**: Free tier (750 hours/month, goes to sleep after 15min inactivity)
- **Supabase**: Free tier (500MB database, 50,000 monthly active users)
- **Gemini AI**: Free tier (limited requests per minute)

**Note**: Free tier services may have cold starts (2-3 seconds delay on first request)

---

## Upgrading

When you need more resources:
- **Netlify**: $19/month for Pro
- **Render**: $7/month for always-on service
- **Supabase**: $25/month for Pro
- **Gemini AI**: Pay-as-you-go pricing

---

## Support

For issues:
1. Check logs in respective dashboards
2. Review error messages
3. Check database connectivity
4. Verify environment variables

Good luck with your deployment! 🚀