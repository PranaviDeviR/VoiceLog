# VoiceLog – Smart Voice-Powered Expense Tracker

## 1. Project Overview

VoiceLog is a voice-powered expense tracking application that helps users record their daily expenses through speech instead of manually entering each transaction.

It uses Gnani AI's speech-to-text API to convert voice recordings into text. The application then extracts individual expense items, identifies their amounts, categorizes them, and stores them in the expense history.

## 2. Problem Statement

Manually recording daily expenses can be time-consuming and inconvenient. People may forget small transactions or find it difficult to maintain an accurate expense record.

VoiceLog aims to simplify expense tracking through voice-based input.

## 3. Key Features

- Voice-based expense recording.
- Speech-to-text conversion using Gnani AI.
- Supports English and tested Tanglish input.
- Extracts multiple expenses from a single recording.
- Automatically identifies expense amounts.
- Categorizes expenses, such as Food & Dining and Travel.
- Displays individual transactions in expense history.
- Stores expense records locally.

## 4. Technologies Used

- **Gnani AI Prisma API:** Speech-to-text conversion.
- **Python:** Expense processing and backend logic.
- **Flask:** Backend web framework.
- **Electron:** Desktop application framework.
- **HTML, CSS and JavaScript:** User interface.
- **JSON:** Local expense data storage.

## 5. Project Structure

VoiceLog/
- VoiceLog.py – Python backend and expense processing.
- main.js – Electron application entry point.
- package.json – Node.js project configuration.
- requirements.txt – Python dependencies.
- README.txt – Project documentation.
- .env.example – Example environment configuration.
- templates/index.html – Application interface.

## 6. How to Run the Application

### Prerequisites
- Python installed.
- Node.js and npm installed.
- A valid Gnani AI API key.

### Step 1: Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Install Node.js dependencies

```bash
npm install
```

### Step 3: Configure the API key

Set your Gnani AI API key as an environment variable.

In Windows PowerShell:

```powershell
$env:GNANI_API_KEY="YOUR_ACTUAL_API_KEY"
$env:GNANI_API_URL="https://api.vachana.ai/stt/v3"
```

Never upload your actual API key to GitHub.

### Step 4: Start the Python backend

```bash
python VoiceLog.py
```

### Step 5: Start the Electron application

Open another terminal in the project folder and run:

```bash
npm start
```

## 7. Working Flow

1. The user records an expense using their voice.
2. The audio is processed and sent to the Gnani AI speech-to-text API.
3. The recognized text is received by the Python backend.
4. The backend extracts individual expense descriptions and amounts.
5. Each expense is assigned an appropriate category.
6. The expense records are saved and displayed in the application.

## 8. Future Enhancements

- Monthly and weekly expense reports.
- Visual spending analytics and charts.
- Budget setting and alerts.
- Improved support for different languages and accents.
- Cloud-based expense backup and synchronization.

## 9. Conclusion

VoiceLog makes everyday expense tracking simpler and more convenient by combining speech recognition with automated expense extraction and categorization. It demonstrates how AI-powered voice interaction can be used to solve a practical daily-life problem.