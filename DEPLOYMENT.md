# Deployment Guide for Dwarka Yatra Application

## 🚀 Quick Deployment Options

### Option 0: Vercel (Serverless - Good for Static/Demo)
**WARNING:** Vercel is "serverless" and has a **Read-Only Filesystem**.
- You **CANNOT** use the local SQLite database (`yatra.db`) for more than a demo (data will be lost or it will error).
- You **MUST** use an external database like **Neon (Postgres)** or **Supabase** for a working app.
- We have added a `vercel.json` file for you.

1. **Push code** to GitHub.
2. **Import project** in Vercel.
3. **Add Environment Variables:**
   - `DATABASE_URI`: Connection string for your external Postgres DB (e.g., `postgresql://...`)
   - Plus all other variables (`SECRET_KEY`, `RAZORPAY...`)

### Option 1: Render.com (Recommended - Persistent Data)

1. **Create account** at [render.com](https://render.com)

2. **Create a new Web Service:**
   - Connect your GitHub repository (or upload code)
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`

3. **Set Environment Variables** in Render Dashboard:
   ```
   SECRET_KEY=<your-secret-key>
   RAZORPAY_API_KEY=<your-razorpay-key>
   RAZORPAY_API_SECRET=<your-razorpay-secret>
   GMAIL_ADDRESS=<your-gmail>
   GMAIL_APP_PASSWORD=<your-gmail-app-password>
   ADMIN_USERNAME=<your-admin-username>
   ADMIN_PASSWORD=<your-admin-password>
   DATABASE_URI=sqlite:///yatra.db
   FLASK_ENV=production
   FLASK_DEBUG=False
   ```

4. **Deploy!** Render will automatically deploy your app.

---

### Option 2: Railway.app (Easy & Fast)

1. **Create account** at [railway.app](https://railway.app)

2. **Deploy from GitHub:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Add Environment Variables:**
   - Go to Variables tab
   - Add all variables from `.env.example`

4. **Railway will auto-detect** Flask and deploy!

---

### Option 3: PythonAnywhere (Great for Beginners)

1. **Create account** at [pythonanywhere.com](https://www.pythonanywhere.com)

2. **Upload your code:**
   - Use "Files" tab to upload project
   - Or clone from GitHub

3. **Create virtual environment:**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 dwarka-env
   pip install -r requirements.txt
   ```

4. **Configure Web App:**
   - Go to "Web" tab
   - Add a new web app (Flask)
   - Set WSGI configuration file:
     ```python
     import sys
     import os
     
     # Add your project directory
     project_home = '/home/yourusername/Dwarka-Yatra'
     if project_home not in sys.path:
         sys.path = [project_home] + sys.path
     
     # Load environment variables
     from dotenv import load_dotenv
     load_dotenv(os.path.join(project_home, '.env'))
     
     from app import app as application
     ```

5. **Set environment variables** in `.env` file on server

6. **Reload** web app

---

### Option 4: Heroku (Paid)

1. **Install Heroku CLI**

2. **Create Heroku app:**
   ```bash
   heroku create dwarka-yatra
   ```

3. **Set environment variables:**
   ```bash
   heroku config:set SECRET_KEY=<your-secret-key>
   heroku config:set RAZORPAY_API_KEY=<your-key>
   heroku config:set RAZORPAY_API_SECRET=<your-secret>
   heroku config:set GMAIL_ADDRESS=<your-gmail>
   heroku config:set GMAIL_APP_PASSWORD=<your-password>
   heroku config:set ADMIN_USERNAME=<username>
   heroku config:set ADMIN_PASSWORD=<password>
   ```

4. **Create Procfile:**
   ```
   web: gunicorn -w 4 app:app
   ```

5. **Deploy:**
   ```bash
   git push heroku main
   ```

---

## 📋 Pre-Deployment Checklist

- [ ] All environment variables are set
- [ ] `.env` file is NOT committed to Git
- [ ] Strong passwords are used
- [ ] Database is initialized
- [ ] Test all features locally first
- [ ] Gmail app password is configured
- [ ] Razorpay keys are correct (test vs live)
- [ ] Admin credentials are secure

---

## 🔒 Security Best Practices

### 1. Generate Strong Secret Key:
```python
import secrets
print(secrets.token_hex(32))
```

### 2. Use Strong Admin Password:
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Don't use "1234" or "admin"!

### 3. Razorpay Keys:
- Use **test keys** for testing
- Use **live keys** for production
- Never expose keys in client-side code

### 4. Database Backups:
- Set up automatic backups on your hosting platform
- Download backups regularly
- Test restore process

---

## 🌐 Custom Domain Setup

### Render.com:
1. Go to Settings → Custom Domain
2. Add your domain
3. Update DNS records as instructed

### Railway.app:
1. Go to Settings → Domains
2. Add custom domain
3. Configure DNS

### PythonAnywhere:
1. Upgrade to paid plan
2. Go to Web tab → Add custom domain
3. Update DNS settings

---

## 📊 Monitoring & Logs

### View Logs:
- **Render**: Dashboard → Logs tab
- **Railway**: Deployment → View Logs
- **PythonAnywhere**: Files → Error log, Server log
- **Heroku**: `heroku logs --tail`

### Monitor Performance:
- Set up uptime monitoring (e.g., UptimeRobot)
- Monitor database size
- Check error logs regularly

---

## 🔄 Updates & Maintenance

### Updating the Application:

1. **Make changes locally**
2. **Test thoroughly**
3. **Commit to Git:**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```
4. **Platform auto-deploys** (Render, Railway) or manually deploy

### Database Migrations:
If you change database schema:
```python
# Backup database first!
# Then recreate tables
from app import app, db
with app.app_context():
    db.drop_all()  # WARNING: Deletes all data!
    db.create_all()
```

---

## 🆘 Common Issues

### Issue: "Module not found"
**Solution:** Ensure all dependencies are in `requirements.txt`

### Issue: "Database locked"
**Solution:** SQLite doesn't handle high concurrency well. Consider PostgreSQL for production.

### Issue: "Payment verification failed"
**Solution:** Check Razorpay signature verification and API keys

### Issue: "Email not sending"
**Solution:** Verify Gmail app password and 2FA settings

---

## 📞 Support

For deployment issues:
- Check hosting platform documentation
- Review application logs
- Verify all environment variables are set correctly

---

**Remember:** Always test in a staging environment before deploying to production!
