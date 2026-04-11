<div align="center">
  <img src="egamescout/web/static/web/images/logo.png" alt="E-Game Scout Logo" width="200"/>

  # E-Game Scout
  ### 🎮 Discover. Compete. Get Signed.

  [![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
  [![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
  [![AWS EC2](https://img.shields.io/badge/AWS-EC2-FF9900?style=for-the-badge&logo=amazonec2&logoColor=white)](https://aws.amazon.com/ec2/)
  [![AWS RDS](https://img.shields.io/badge/AWS-RDS%20MySQL-527FFF?style=for-the-badge&logo=amazonrds&logoColor=white)](https://aws.amazon.com/rds/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
  [![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=for-the-badge)](https://github.com/kachhadiyajanvi/E-GAMESCOUT/pulls)
</div>

---

## 📖 About the Project

**E-Game Scout** is a full-stack esports scouting platform that connects **talented players** with **professional esports organizations**. Players can build rich profiles, track tournament history, receive contract offers, and participate in bidding seasons — all from a single platform. Organizations get dedicated dashboards to scout players, manage rosters, run tournaments, and issue professional PDF contracts.

> Built with Django, Tailwind CSS, and powered by Google Gemini AI + Groq API.

---

## ✨ Features

### 👤 Player Portal
- 📋 **Rich Player Profiles** — Game UIDs, competitive roles, social links (Instagram, YouTube, Discord)
- 📊 **Tournament History & Stats** — Full history with AI-powered scorecard analysis
- 💰 **Bidding System** — Accept, reject, or negotiate contract bids from organizations
- 🔔 **Real-time Notifications** — Stay updated on contract offers & tournament announcements
- 🔐 **Secure Auth** — OTP-based login + optional Two-Factor Authentication (TOTP/QR)

### 🏢 Organization Portal
- 🔍 **Player Scouting** — Browse a global talent pool with advanced filters
- 🏆 **Tournament Management** — Create, publish, and manage esports tournaments
- 📜 **Contract Management** — Draft, send, and export professional PDF contracts
- 🤖 **AI Scorecard Tool** — Upload scorecards and get AI-driven player analysis via Gemini
- 💸 **Bidding Dashboard** — Place bids, manage negotiations, track transaction history
- 📨 **External Invites** — Invite players to join your organization via email

### 🛡️ Admin Portal
- 📈 **Analytics Dashboard** — Platform-wide stats & charts
- ✅ **Tournament Approvals** — Review and approve/reject org-submitted tournaments
- 🧾 **Bidding Reports & Exports** — Full bidding season management and CSV/PDF exports
- 📣 **Bulk Notifications** — Broadcast messages to all players or organizations
- 🗄️ **Archive Management** — Manage deactivated users and deleted entities safely

---

## 🚀 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, Django 6.0 |
| **Frontend** | HTML5, Tailwind CSS, JavaScript, Glassmorphism UI |
| **Database** | AWS RDS (MySQL 8.0) |
| **Server** | AWS EC2 (Gunicorn + WhiteNoise) |
| **AI** | Google Gemini API (`google-generativeai`), Groq API |
| **Auth** | OTP Email Verification, TOTP 2FA (pyotp + QR codes) |
| **PDF Generation** | xhtml2pdf, ReportLab, lxml |
| **Email** | Gmail SMTP with App Password |

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- MySQL 8.0 (or PostgreSQL)
- A Google Gemini API key & Groq API key
- A Gmail account with App Passwords enabled

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kachhadiyajanvi/E-GAMESCOUT.git
   cd E-GAMESCOUT/egamescout
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   # .venv\Scripts\activate         # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your actual values (see the table below).

5. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Open in browser:**
   ```
   http://127.0.0.1:8000/
   ```

---

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | ✅ Yes |
| `DEBUG` | Debug mode (`True`/`False`) | No (default: `False`) |
| `GEMINI_API_KEY` | Google Gemini AI API key | ✅ Yes |
| `GROQ_API_KEY` | Groq API key | ✅ Yes |
| `DB_NAME` | Database name | No (default: `Dname`) |
| `DB_USER` | Database user | No (default: `Duser`) |
| `DB_PASSWORD` | Database password | No |
| `DB_HOST` | Database host | No (default: `Dhost`) |
| `DB_PORT` | Database port | No (default: `Dport`) |
| `EMAIL_HOST_USER` | Gmail address for sending emails | ✅ Yes |
| `EMAIL_HOST_PASSWORD` | Gmail App Password | ✅ Yes |

> ⚠️ **Never commit your `.env` file.** It is already listed in `.gitignore`.

---

## 🎯 How It Works

```
┌─────────────┐     Scout & Bid     ┌──────────────────┐
│   PLAYER    │◄───────────────────►│   ORGANIZATION   │
│  (Profile,  │                     │  (Dashboard,     │
│  Bidding,   │                     │   Tournaments,   │
│  Contracts) │                     │   Contracts,     │
└─────────────┘                     │   Scout Players) │
       ▲                            └──────────────────┘
       │  OTP Auth                          ▲
       │  + 2FA                             │ AI Scorecard
       ▼                                    │ + Bidding
┌─────────────┐    Approve / Manage ┌──────────────────┐
│    ADMIN    │◄───────────────────►│   PLATFORM DATA  │
│  (Analytics,│                     │  (Tournaments,   │
│  Reports,   │                     │   Contracts,     │
│  Approvals) │                     │   Bids, Invites) │
└─────────────┘                     └──────────────────┘
```

---

## 📁 Folder Structure

```text
E-GAMESCOUT/
├── SETUP.md                  # Environment & API setup guide
└── egamescout/               # Django project root
    ├── .env                  # Secrets (NOT in git)
    ├── .env.example          # Template for secrets
    ├── requirements.txt      # Python dependencies
    ├── manage.py             # Django management CLI
    ├── egamescout/           # Core config
    │   ├── settings.py       # Project settings
    │   └── urls.py           # Root URL dispatcher
    └── web/                  # Main application
        ├── models.py         # DB schema (Player, Org, Contract, Bid...)
        ├── views.py          # Player & Organization views
        ├── admin_views.py    # Admin portal views
        ├── urls.py           # All URL routes
        ├── context_processors.py
        ├── templates/
        │   └── web/
        │       ├── base.html             # Root base template
        │       ├── Player/               # Player dashboards
        │       ├── Organization/         # Org dashboards
        │       ├── Admin/                # Admin portal
        │       └── emails/              # Transactional email templates
        └── static/
            └── web/
                ├── images/              # Logo, hero images
                ├── css/                 # Custom stylesheets
                └── js/                 # Frontend scripts
```

---

## 🔮 Future Improvements

- [ ] 💬 **In-App Messaging** — Real-time chat between organizations and players
- [ ] 🕹️ **Game API Integrations** — Auto-pull live stats from Riot, Steam, or BGMI APIs
- [ ] 🤝 **Scrim Scheduler** — Automated practice match / scrim booking between orgs
- [ ] 🧠 **Advanced AI Analytics** — Predictive player potential scoring via Gemini
- [ ] 📱 **Mobile App** — Native iOS/Android companion app
- [ ] 🌍 **Multi-language Support** — Localization for South Asian & Southeast Asian markets

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">
  <sub>Built with ❤️ for the Indian Esports community</sub>
</div>
