# Netlify Deployment Guide

## Prerequisites
- Netlify account
- Backend deployed on a server (e.g., Heroku, Railway, or any cloud provider)
- Supabase database configured

## Steps to Deploy Frontend on Netlify

### 1. Prepare Environment Variables

Create a `.env.production` file in `/app/frontend/`:

```bash
REACT_APP_BACKEND_URL=https://your-backend-url.com
```

### 2. Deploy via Netlify Dashboard

1. Go to https://app.netlify.com/
2. Click "Add new site" → "Import an existing project"
3. Connect your Git repository
4. Configure build settings:
   - **Base directory**: `frontend`
   - **Build command**: `yarn build`
   - **Publish directory**: `frontend/build`
5. Add environment variable:
   - Key: `REACT_APP_BACKEND_URL`
   - Value: Your backend URL (e.g., `https://your-backend.herokuapp.com`)
6. Click "Deploy site"

### 3. Deploy via Netlify CLI

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login to Netlify
netlify login

# Deploy from frontend directory
cd /app/frontend
netlify deploy --prod
```

### 4. Configure Custom Domain (Optional)

1. Go to Site settings → Domain management
2. Add your custom domain
3. Configure DNS settings as shown by Netlify

## Backend Deployment

Your backend needs to be deployed separately. Options:

### Option A: Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Option B: Heroku
```bash
# Install Heroku CLI
# Login and create app
heroku login
heroku create your-app-name

# Deploy backend
cd /app/backend
git push heroku main
```

### Option C: Render
1. Go to https://render.com
2. Create new Web Service
3. Connect your repository
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`

## Environment Variables for Backend

Make sure your backend has these environment variables:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
GEMINI_API_KEY=your-gemini-api-key
CORS_ORIGINS=https://your-netlify-site.netlify.app
```

## Important Notes

1. **CORS Configuration**: Update `CORS_ORIGINS` in backend to include your Netlify URL
2. **API Routes**: All API calls use `/api` prefix
3. **Environment Variables**: Set `REACT_APP_BACKEND_URL` to your backend URL
4. **Build Time**: First build may take 2-3 minutes
5. **SSL**: Netlify provides free SSL certificates automatically

## Troubleshooting

### Issue: API calls failing
- Check `REACT_APP_BACKEND_URL` is set correctly
- Verify backend CORS settings allow your Netlify domain
- Check browser console for CORS errors

### Issue: Build fails
- Ensure all dependencies are in `package.json`
- Check Node version (18+ recommended)
- Run `yarn build` locally first to test

### Issue: 404 on refresh
- The `netlify.toml` file handles SPA routing
- Ensure it's in the root directory

## Testing Locally

Before deploying, test the production build:

```bash
cd /app/frontend

# Build production version
yarn build

# Serve locally
npx serve -s build
```

## Continuous Deployment

Netlify automatically deploys when you push to your Git repository:
- Push to `main` branch → Production deployment
- Push to other branches → Preview deployments

## Support

For issues:
1. Check Netlify build logs
2. Check browser console
3. Verify environment variables
4. Test API endpoints directly
