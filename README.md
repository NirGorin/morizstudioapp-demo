# MorizStudioApp


**Backend system for managing a Pilates studio**  
Built with FastAPI, SQLAlchemy, and PostgreSQL – this project simulates a full SaaS backend for users, trainees, and studio owners.

---

## 🎯 Purpose

This project is part of my transition to a backend development career.  
It simulates a real-world SaaS system used by Pilates studios to manage everything from trainee limitations to AI-based training suggestions.

---

## 🧩 Features

- 🗓️ Class scheduling by day, time, and level (beginner, intermediate, advanced)
- 🧑‍🏫 User & trainee management
- 🧍‍♀️ Medical limitations: pregnancy, back/knee/neck injuries, surgeries, etc.
- 🧾 Subscription plans: 1-5 times/week, intro class, personal training
- 💬 Notifications (reminders, level upgrades, payment updates)
- 📈 Progress tracking and income analytics
- 🧠 Smart recommendations using AI (optional future feature)
- 📁 File uploads: medical certificates, profile images

---

## 🛠 Tech Stack

- **FastAPI** – high-performance Python web framework
- **SQLAlchemy** – ORM for data modeling
- **Alembic** – DB migrations
- **JWT** – authentication & authorization
- **PostgreSQL** – production-ready database
- **Pytest** – testing framework

---

## 🚀 Running the Project Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/NirGorin/MorizStudioApp.git
   cd MorizStudioApp
