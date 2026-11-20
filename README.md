# Attendly — Student Attendance Tracker

A small college project with **HTML and CSS for the frontend** and a **Python backend**. It uses only Python's standard library.

## Demo login

- Username: `teacher`
- Password: `teach123`

## Run locally

1. Install Python 3.
2. Open a terminal in this folder.
3. Run `py app.py` on Windows (or `python app.py`).
4. Visit `http://localhost:8000`.

## Publish with Render

The included `render.yaml` sets up a free Python web service. Create a **private GitHub repository** and upload the project files, then connect that repository to Render and create the service from its Blueprint. Render will build and publish the app at a public `onrender.com` URL. Use that URL for your presentation.

The app saves attendance to `attendance.json`. On a free cloud service, this local file can reset when the service restarts, so use sample records for the presentation.

## Features

- Teacher login and logout.
- A sample class of 10 students.
- Attendance by date: Present, Absent, Late, or Not marked.
- Attendance summary and percentage.
- HTML form submissions handled by Python; the frontend has no JavaScript.

This is a classroom demo with sample credentials, not a production login system.
