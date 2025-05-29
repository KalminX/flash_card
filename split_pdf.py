import os
import hashlib
import json
from flask import Flask, request, render_template
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import requests

# ==== Load environment variables ====
load_dotenv()

# ======= CONFIGURATION =======
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.0-flash"
CHUNK_SIZE = 3000
UPLOAD_FOLDER = "uploads"
CACHE_FILE = "flashcard_cache.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Flask setup
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ====== Load or initialize flashcard cache ======
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        flashcard_cache = json.load(f)
else:
    flashcard_cache = {}

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

def summarize_chunk_with_cache(chunk):
    key = chunk_hash(chunk)
    if key in flashcard_cache:
        print("✅ Cache hit")
        return flashcard_cache[key]

    print("⏳ Cache miss – calling Gemini API...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

    prompt = f"Turn the following content into a flashcard-style summary:\n\n{chunk}"

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.ok:
        summary = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        flashcard_cache[key] = summary
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(flashcard_cache, f, indent=2)
        return summary
    else:
        print("❌ Error:", response.status_code, response.text)
        return "[Error summarizing]"

@app.route("/", methods=["GET", "POST"])
def index():
    flashcards = []
    if request.method == "POST":
        file = request.files.get("pdf")
        if file and file.filename.endswith(".pdf"):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)

            chunks = extract_text_chunks(filepath)
            for chunk in chunks:
                summary = summarize_chunk_with_cache(chunk)
                flashcards.append(summary)

    return render_template("index.html", flashcards=flashcards)
