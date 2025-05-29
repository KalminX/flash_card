# =========================
# 📦 Imports
# =========================
import os
import re
import json
import hashlib
import asyncio
import aiohttp
import requests
from flask import Flask, request, render_template, redirect, session
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# =========================
# 🌱 Environment Setup
# =========================
load_dotenv()

# =========================
# ⚙️ Configuration
# =========================
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.0-flash"
CHUNK_SIZE = 3000
UPLOAD_FOLDER = "uploads"
CACHE_FILE = "flashcard_cache.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# 🔧 Flask App Setup
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "0b8a96ee70c586cf0a38b9e325fc55adfd9854c9")  # Add secret key for sessions
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# =========================
# 💾 Load Flashcard Cache
# =========================
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        flashcard_cache = json.load(f)
else:
    flashcard_cache = {}

semaphore = asyncio.Semaphore(3)

# =========================
# 🧩 Utility Functions
# =========================
def chunk_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()

def extract_text_chunks(filepath, max_chars=CHUNK_SIZE):
    reader = PdfReader(filepath)
    full_text = ""

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text += text + "\n"
        else:
            print(f"⚠️ Warning: No text on page {i + 1}")
        if i == 50:
            break

    return [full_text[i:i + max_chars] for i in range(0, len(full_text), max_chars)]

def extract_dict_from_markdown(markdown_string):
    match = re.search(r'```json\n(.*?)\n```', markdown_string, re.DOTALL)
    if not match:
        return None
    raw_json = match.group(1).strip()
    return json.loads(raw_json)

def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(i) for i in obj]
    elif obj is None:
        return ""
    else:
        return obj

# =========================
# 🤖 Gemini API Calls
# =========================
async def summarize_chunk_with_cache(session, chunk):
    async with semaphore:
        key = chunk_hash(chunk)
        if key in flashcard_cache:
            print("✅ Cache hit")
            return flashcard_cache[key]

        print("⏳ Cache miss – calling Gemini API...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
        prompt = (
            "Read the following content and return only a list of flashcard-style questions and answers. "
            "Do not include any introductions, explanations, or conclusions. "
            "Strictly output only the Q&A flashcards. In a json format of the form [{'1': {'q': 'response', 'a': 'response'}}]\n\n"
            f"{chunk}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        headers = {"Content-Type": "application/json"}

        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    summary_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    summary = extract_dict_from_markdown(summary_text)
                    flashcard_cache[key] = summary
                    with open(CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(flashcard_cache, f, indent=2)
                    return summary
                else:
                    print("❌ Error:", response.status, await response.text())
                    return "[Error summarizing]"
        except Exception as e:
            print("❌ Exception:", e)
            return "[Exception occurred]"

async def summarize_all_chunks(chunks):
    async with aiohttp.ClientSession() as session:
        tasks = [summarize_chunk_with_cache(session, chunk) for chunk in chunks]
        return await asyncio.gather(*tasks)


def clear_upload_folder():
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

def clear_cache_file():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        print(f"Cleared cache file: {CACHE_FILE}")
    except Exception as e:
        print(f"Error clearing cache file: {e}")

def cleanup_task():
    print("Running cleanup task...")
    clear_upload_folder()
    clear_cache_file()
    print("Cleanup task done.")


scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_task, trigger="interval", minutes=30)
scheduler.start()

# Shut down scheduler when exiting app
import atexit
atexit.register(lambda: scheduler.shutdown())

# =========================
# 🌐 Flask Routes
# =========================
@app.route("/", methods=["GET"])
def home():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("pdf")
    if file and file.filename.endswith(".pdf"):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        session["pdf_path"] = filepath
        return redirect("/loading")
    return "Invalid file", 400

@app.route("/loading", methods=["GET"])
def loading():
    return render_template("loading.html")

@app.route("/flashcards", methods=["GET", "POST"])
async def flashcards_view():
    filepath = session.get("pdf_path")
    if not filepath:
        return redirect("/")

    chunks = extract_text_chunks(filepath)
    flashcards = await summarize_all_chunks(chunks)
    questions_count = len(flashcards)    

    return render_template("index.html", flashcards=flashcards, questions_count=questions_count)

# =========================
# 🚀 Run Server
# =========================
if __name__ == "__main__":
    app.run(debug=True)
