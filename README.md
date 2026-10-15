# Dino AI — Hackathon MVP

A responsive Flask + Gemini starter for Dino AI: an AI chat workspace with task history, temporary pairing-code flow, and a companion page concept.

## Important scope note

This is a working MVP foundation, not a fully autonomous computer-control system. Pairing currently validates a short-lived code; it does **not** establish a persistent secure device channel. The “open URL” endpoint validates a URL but does not remotely control a device. Do not present those two features as full remote control until a real authenticated companion connection is implemented and tested.

## Features

- Dark red/black responsive UI with mobile-friendly layout
- Register/login with hashed passwords
- Gemini-powered chat when `GEMINI_API_KEY` is configured
- Friendly demo mode if the API key is missing
- SQLite task history
- Temporary one-time pairing codes
- Companion page with a local, user-confirmed open-URL demo
- Health endpoint at `/health`

## Run locally

1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`.
5. Set `FLASK_SECRET_KEY` to a long random value.
6. Add your own `GEMINI_API_KEY` to `.env` to enable Gemini responses.
7. Start the app:

   ```bash
   python app.py
   ```

8. Open `http://127.0.0.1:5000`, register an account, and try Dino AI.

## Get a Gemini API key

Use Google's official AI Studio: https://aistudio.google.com/app/apikey

Keep the key only in `.env`. Never place it in frontend JavaScript or commit `.env` to GitHub.

## Project structure

```text
dino_ai_hackathon/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   ├── landing.html
│   ├── auth.html
│   ├── dashboard.html
│   └── companion.html
└── static/
    ├── css/style.css
    └── js/
        ├── app.js
        └── companion.js
```

## Before production or judging

- Replace the development secret and configure HTTPS.
- Add CSRF protection, login rate limiting, secure deployment cookie settings, and stricter account controls.
- Implement a real device token and authenticated persistent channel before claiming cross-device control.
- If adding Playwright, run it in a restricted environment, validate destinations, block private/internal IP ranges, and require user approval for sensitive actions.
- Never allow model output to execute arbitrary Python, shell commands, or unrestricted browser actions.
- Test the complete demo on the actual deployment platform.

## Deploying

This Flask application can run on a Python host such as Render. Set `GEMINI_API_KEY` and `FLASK_SECRET_KEY` in the host's environment settings. Use a production WSGI server such as Gunicorn for deployment and configure the start command accordingly, for example:

```bash
gunicorn app:app
```

The MVP does not use Socket.IO yet, so it does not require WebSocket configuration. Add persistent real-time communication only when the device companion channel is implemented.
