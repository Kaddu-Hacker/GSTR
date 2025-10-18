# \ud83d\ude80 Quick Start Guide

## For Local Development

### 1. Setup Supabase Database (One-time)

1. Go to your Supabase dashboard: https://cuqvhbyymoeeiumqbfge.supabase.co
2. Click on **SQL Editor** in the left sidebar
3. Copy the entire content from `/app/backend/supabase_schema.sql`
4. Paste it in the SQL Editor
5. Click **Run** button
6. You should see: "Success. No rows returned"

\u2705 Your database is now ready!

### 2. Start the Application

The application is already configured and running in supervisor. Just access:

**Frontend**: https://ux-upgrade-9.preview.emergentagent.com

### 3. Test the Application

1. **Enter GST Details**:
   - GSTIN: Enter your 15-digit GSTIN (e.g., `27AABCE1234F1Z5`)
   - State Code: First 2 digits (e.g., `27`)
   - Filing Period: `012025` (January 2025)

2. **Upload Test Files**:
   ```bash
   # Generate sample test data
   cd /app
   python3 scripts/generate_sample_data.py
   
   # Files will be created in /app/test_data/
   ```

3. **Upload files** via the UI and watch the magic happen!

---

## For Production Deployment

### Quick Deploy Checklist

- [ ] **Step 1**: Run SQL in Supabase dashboard (see above)
- [ ] **Step 2**: Deploy backend to Render/Railway
  - Use environment variables from `/app/backend/.env`
  - Note your backend URL
- [ ] **Step 3**: Update frontend `.env.production`
  - Set `REACT_APP_BACKEND_URL` to your backend URL
- [ ] **Step 4**: Deploy frontend to Netlify
  ```bash
  cd /app/frontend
  yarn build
  netlify deploy --prod
  ```

\ud83d\udcda Full deployment guide: [DEPLOYMENT_GUIDE.md](/app/DEPLOYMENT_GUIDE.md)

---

## Testing the Features

### 1. File Upload
- Upload individual Excel/CSV files or ZIP archive
- System auto-detects file types
- See real-time progress

### 2. AI Validation
- Gemini AI analyzes invoice sequences
- Detects missing invoices automatically
- Validates GST calculations

### 3. Data Preview
- Review state-wise breakdown
- Check document types
- View audit logs
- See AI insights

### 4. Download GSTR Files
- Click download buttons
- Files download as JSON
- Ready for GST portal upload

---

## Troubleshooting Common Issues

### Issue: "Could not find the table 'public.uploads'"
**Solution**: Run the SQL schema in Supabase dashboard (Step 1 above)

### Issue: Download button not working
**Solution**: 
1. Check browser console for errors
2. Verify GSTR data is generated (check Data Review section)
3. Try different browser
4. Clear browser cache

### Issue: Backend API not responding
**Solution**:
```bash
# Check backend logs
tail -f /var/log/supervisor/backend.err.log

# Restart backend
sudo supervisorctl restart backend
```

### Issue: Frontend not loading
**Solution**:
```bash
# Check frontend logs
tail -f /var/log/supervisor/frontend.err.log

# Restart frontend
sudo supervisorctl restart frontend
```

---

## API Testing

Test backend API directly:

```bash
# Health check
curl http://localhost:8001/api/

# Test upload (with sample files)
curl -X POST http://localhost:8001/api/upload \
  -F "files=@/app/test_data/tcs_sales.xlsx" \
  -F "files=@/app/test_data/Tax_invoice_details.xlsx" \
  "?seller_state_code=27&gstin=27AABCE1234F1Z5&filing_period=012025"
```

---

## Environment Variables

### Backend (`/app/backend/.env`)
```env
SUPABASE_URL=https://cuqvhbyymoeeiumqbfge.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GEMINI_API_KEY=AIzaSyBToUXh6mtAkBdwwO-UZsBhntZv_yeCAW8
CORS_ORIGINS=*
```

### Frontend (`/app/frontend/.env`)
```env
REACT_APP_BACKEND_URL=https://ux-upgrade-9.preview.emergentagent.com
```

---

## Next Steps

1. \u2705 Complete Supabase setup (run SQL)
2. \u2705 Test locally with sample data
3. \ud83d\ude80 Deploy to production (follow DEPLOYMENT_GUIDE.md)
4. \ud83c\udf89 Start filing GST returns!

---

## Support

Need help? Check:
1. [DEPLOYMENT_GUIDE.md](/app/DEPLOYMENT_GUIDE.md) - Full deployment instructions
2. [README.md](/app/README.md) - Complete documentation
3. Backend logs: `/var/log/supervisor/backend.err.log`
4. Frontend logs: `/var/log/supervisor/frontend.err.log`

---

Made with \u2764\ufe0f using Emergent AI Platform
