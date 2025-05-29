# 🧠 Flashcard PDF Summarizer

A sleek, dictionary-style web app that extracts and summarizes content from PDFs and turns them into flashcards for fast and effective studying. Built with Flask, served via ASGI using Uvicorn, and designed for student productivity.

[Check it out](https://kal-flashcard-ce64036bef75.herokuapp.com/)

## ✨ Features

- 📄 Upload academic PDFs
- 🧠 AI-generated summaries (via Gemini API)
- 📋 Automatically generates flashcards (Q&A format)
- 🧭 Clean, compact UI inspired by dictionary/thesaurus layouts
- ⚡ Fast and deployable using ASGI (Uvicorn)

## 🛠 Tech Stack

- **Backend**: Flask + WsgiToAsgi + Uvicorn
- **Frontend**: HTML, CSS (dictionary-style UI)
- **AI/LLM**: Gemini API
- **Others**: dotenv for config, pdfminer or PyMuPDF for parsing

## 📦 Installation

```bash
git clone https://github.com/kalminx/flash_card.git
cd flashcard-summarizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

## 🔐 Environment Setup

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key
GEMINI_API_KEY=your-gemini-api-key
UPLOAD_FOLDER=./uploads
```

## 🚀 Running the App

### Development (Flask dev server)

```bash
python app.py
```

### ASGI (Uvicorn)

```bash
uvicorn app:asgi_app --reload
```

## 🧪 Usage

1. Visit `http://localhost:8000` or `http://127.0.0.1:5000`
2. Upload a PDF file
3. View the summarized flashcards in a compact dictionary-style interface
4. Study smarter!

## 📁 Project Structure

flashcard-summarizer/
├── app.py
├── templates/
│   └── index.html
├── static/
│   ├── styles.css
├── .env
├── requirements.txt
└── README.md

## 🧠 Future Features

* Save flashcards to user account
* Export to Anki-compatible format
* Multilingual support
* Image + formula extraction

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

## 🙌 Credits

* Built with ❤️ by Kalmin
* Gemini API by Google
* ASGI wrapping by `asgiref`
