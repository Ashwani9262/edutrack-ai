# EduTrack AI

A full-stack student performance and behavior analytics system built with Flask, SQLite, HTML, CSS, JavaScript, and Chart.js.

## Features
- Login / Register with student and teacher roles
- Student dashboard with study tracking, performance charts, grade prediction, leaderboard, and feedback
- Teacher dashboard with class cards, student details, and review submission
- Study sessions with start/stop tracking and tab-switch detection
- SQLite database schema for users, classes, sessions, marks, points, and reviews
- Professional blue-white SaaS-style UI

## Setup
1. Install Python 3.10+.
2. Create a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the app locally:
   ```powershell
   python app.py
   ```
5. Open `http://127.0.0.1:5000` in your browser.

## Docker Deployment
1. Build the image:
   ```powershell
   docker build -t edutrack-ai .
   ```
2. Run the container:
   ```powershell
   docker run -p 8080:8080 edutrack-ai
   ```
3. Open `http://127.0.0.1:8080`.

## Google Cloud Run Deployment
1. Install and authenticate the Google Cloud SDK.
2. Set your project:
   ```powershell
   gcloud config set project YOUR_PROJECT_ID
   ```
3. Build and push the container:
   ```powershell
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/edutrack-ai
   ```
4. Deploy to Cloud Run:
   ```powershell
   gcloud run deploy edutrack-ai --image gcr.io/YOUR_PROJECT_ID/edutrack-ai --platform managed --region us-central1 --allow-unauthenticated
   ```

## Notes
- The app uses SQLite by default. The database is created automatically in the `instance` directory.
- Replace `app.secret_key` in `app.py` with a secure random value for production.
- Chart.js is loaded from CDN for chart rendering.
