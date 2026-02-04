# E-GAMESCOUT Environment Setup

## 🔐 Security Configuration

This project uses environment variables to keep sensitive information secure. **Never commit the `.env` file to GitHub!**

## 📋 Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your actual credentials:
   ```bash
   nano .env  # or use your preferred editor
   ```

3. Update the following values in `.env`:
   - `SECRET_KEY`: Generate a new Django secret key for production
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `GROQ_API_KEY`: Your Groq API key
   - `DB_PASSWORD`: Your MySQL database password (if any)
   - `EMAIL_HOST_USER`: Your Gmail address
   - `EMAIL_HOST_PASSWORD`: Your Gmail app password
   - `DEBUG`: Set to `False` in production

### 3. Database Setup

```bash
python manage.py migrate
```

### 4. Run the Development Server

```bash
python manage.py runserver
```

## 🔑 Required API Keys

### Google Gemini API
- Get your API key from: https://makersuite.google.com/app/apikey
- Add to `.env` as `GEMINI_API_KEY`

### Groq API
- Get your API key from: https://console.groq.com/keys
- Add to `.env` as `GROQ_API_KEY`

### Gmail App Password
- Enable 2-Step Verification in your Google Account
- Generate an App Password: https://myaccount.google.com/apppasswords
- Add to `.env` as `EMAIL_HOST_PASSWORD`

## ⚠️ Important Security Notes

- ✅ `.env` is in `.gitignore` - your secrets are safe
- ✅ `.env.example` is committed - shows required variables
- ❌ **NEVER** commit `.env` to version control
- ❌ **NEVER** share your API keys publicly
- 🔄 Rotate your keys if accidentally exposed

## 📁 File Structure

```
egamescout/
├── .env                 # Your actual secrets (NOT in git)
├── .env.example         # Template (safe to commit)
├── .gitignore          # Protects sensitive files
├── requirements.txt    # Python dependencies
└── egamescout/
    └── settings.py     # Loads from environment variables
```

## 🚀 Deployment

When deploying to production:

1. Set `DEBUG=False` in your `.env`
2. Generate a new `SECRET_KEY`
3. Configure your production database credentials
4. Set up environment variables on your hosting platform
5. Never use development keys in production

## 📝 Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SECRET_KEY` | Django secret key | Yes | - |
| `DEBUG` | Debug mode | No | False |
| `GEMINI_API_KEY` | Google Gemini API key | Yes | - |
| `GROQ_API_KEY` | Groq API key | Yes | - |
| `DB_NAME` | Database name | No | egamescout |
| `DB_USER` | Database user | No | root |
| `DB_PASSWORD` | Database password | No | (empty) |
| `DB_HOST` | Database host | No | 127.0.0.1 |
| `DB_PORT` | Database port | No | 3306 |
| `EMAIL_HOST_USER` | Gmail address | Yes | - |
| `EMAIL_HOST_PASSWORD` | Gmail app password | Yes | - |
