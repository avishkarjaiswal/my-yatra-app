# Dwarka Yatra Registration System 🕉️

A comprehensive web application for managing Dwarka Yatra registrations with integrated payment processing, receipt generation, and admin management.

## 🔐 Security Setup (IMPORTANT!)

### Before Deployment:

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file with your actual credentials:**
   ```bash
   # Open .env and replace all placeholder values
   nano .env  # or use any text editor
   ```

3. **Required Environment Variables:**
   - `SECRET_KEY`: Generate a strong random secret key
   - `RAZORPAY_API_KEY`: Your Razorpay API key
   - `RAZORPAY_API_SECRET`: Your Razorpay API secret
   - `GMAIL_ADDRESS`: Gmail address for sending receipts
   - `GMAIL_APP_PASSWORD`: Gmail app password (not regular password)
   - `ADMIN_USERNAME`: Admin login username
   - `ADMIN_PASSWORD`: Admin login password (use a strong password!)

### Generate a Strong Secret Key:

```python
import secrets
print(secrets.token_hex(32))
```

Or in bash:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 📦 Installation

1. **Clone or download the project**

2. **Create a virtual environment:**
   ```bash
   python -m venv env
   ```

3. **Activate the virtual environment:**
   - Windows:
     ```bash
     env\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source env/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables** (see Security Setup above)

6. **Initialize the database:**
   ```bash
   python
   >>> from app import app, db
   >>> with app.app_context():
   ...     db.create_all()
   >>> exit()
   ```

## 🚀 Running the Application

### Development Mode:
```bash
python app.py
```
Visit: http://localhost:5000

### Production Mode (with Gunicorn):
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## 🌐 Deployment

### Important Security Checklist:

- [ ] `.env` file is created with actual credentials
- [ ] `.env` is listed in `.gitignore` (already done)
- [ ] Strong `SECRET_KEY` is set
- [ ] Strong `ADMIN_PASSWORD` is set
- [ ] `FLASK_ENV=production` in `.env`
- [ ] `FLASK_DEBUG=False` in `.env`
- [ ] Database backups are configured
- [ ] HTTPS is enabled on your hosting platform

### Recommended Hosting Platforms:

1. **Render.com** (Free tier available)
2. **Railway.app** (Easy deployment)
3. **PythonAnywhere** (Good for beginners)
4. **Heroku** (Paid)
5. **DigitalOcean App Platform**

### Environment Variables on Hosting Platform:

Make sure to set all environment variables from `.env` in your hosting platform's dashboard. **Never commit `.env` to Git!**

## 📁 Project Structure

```
Dwarka Yatra/
├── app.py                          # Main application
├── models.py                       # Database models
├── email_utils.py                  # Email and PDF utilities
├── .env                            # Environment variables (DO NOT COMMIT!)
├── .env.example                    # Template for .env
├── .gitignore                      # Git ignore rules
├── requirements.txt                # Python dependencies
├── templates/                      # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── package_selection.html
│   ├── registration_summary.html
│   ├── payment.html
│   ├── receipt.html
│   ├── admin_login.html
│   ├── admin_dashboard.html
│   └── admin_create_registration.html
├── static/                         # Static files
│   ├── css/
│   ├── js/
│   └── images/
└── yatra.db                        # SQLite database (auto-created)
```

## 🔑 Features

- **User Registration**: Multi-traveler registration with guardian support
- **Package Selection**: Customizable hotel, food, and travel options
- **Age-based Pricing**: Automatic discounts for children
- **OTM Integration**: One Time Membership verification
- **Payment Gateway**: Razorpay integration
- **Receipt Generation**: PDF receipts with email delivery
- **Admin Panel**: 
  - View all registrations
  - Create manual registrations with custom discounts
  - Generate receipts for any booking
  - Export data to Excel/CSV
  - Manage OTM IDs
- **WhatsApp Integration**: Auto-join group link in receipts

## 🛡️ Security Features

- Environment variable configuration
- Secure credential management
- Session-based authentication
- Payment signature verification
- SQL injection protection (SQLAlchemy ORM)
- XSS protection (Jinja2 auto-escaping)

## 📧 Gmail Setup for Receipts

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account → Security
   - Under "2-Step Verification", select "App passwords"
   - Generate a password for "Mail"
3. Use this app password in `GMAIL_APP_PASSWORD` (not your regular password)

## 🔧 Admin Access

- URL: `/admin/login`
- Username: Set in `.env` (`ADMIN_USERNAME`)
- Password: Set in `.env` (`ADMIN_PASSWORD`)

## 📊 Database Tables

- `passenger_insider`: Travelers with OTM
- `passenger_outsider`: Travelers without OTM
- `otm_active`: Active OTM IDs
- `otm_expired`: Used OTM IDs

## 🐛 Troubleshooting

### "RAZORPAY_API_KEY must be set" error:
- Ensure `.env` file exists in the project root
- Check that all required variables are set in `.env`

### Email not sending:
- Verify Gmail app password is correct
- Check that 2FA is enabled on Gmail
- Ensure `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` are set

### Database errors:
- Delete `yatra.db` and reinitialize
- Check file permissions

## 📝 License

This project is proprietary software for Dwarka Yatra management.

## 👨‍💻 Developer

Developed for Dwarka Yatra 2026

---

**⚠️ IMPORTANT REMINDER:**
- Never commit `.env` file to version control
- Always use strong passwords in production
- Keep your API keys and secrets secure
- Regularly backup your database
