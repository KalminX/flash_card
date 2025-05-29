import os
import hashlib
import json
from flask import Flask, request, render_template
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import requests
import re
import aiohttp
import asyncio


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

def extract_dict_from_markdown(markdown_string):
    # Step 1: Extract raw JSON string from the markdown
    match = re.search(r'```json\n(.*?)\n```', markdown_string, re.DOTALL)
    if not match:
        return None
    
    raw_json = match.group(1).strip()
    
    # Step 2: Convert JSON string to Python object (list of dicts)
    return json.loads(raw_json)

# def summarize_chunk_with_cache(chunk):
#     key = chunk_hash(chunk)
#     if key in flashcard_cache:
#         print("✅ Cache hit")
#         return flashcard_cache[key]

#     print("⏳ Cache miss – calling Gemini API...")
#     url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

#     prompt = prompt = (
#         "Read the following content and return only a list of flashcard-style questions and answers. "
#         "Do not include any introductions, explanations, or conclusions. "
#         "Strictly output only the Q&A flashcards. In a json format of the form [{'1': {'q': 'response', 'a': 'response'}}]\n\n"
#         ""
#         f"{chunk}"
#     )


#     payload = {
#         "contents": [
#             {
#                 "parts": [{"text": prompt}]
#             }
#         ]
#     }

#     headers = {
#         "Content-Type": "application/json"
#     }

#     response = requests.post(url, headers=headers, json=payload)
#     if response.ok:
#         summary = response.json()["candidates"][0]["content"]["parts"][0]["text"]
#         summary = extract_dict_from_markdown(summary)
#         flashcard_cache[key] = summary
#         with open(CACHE_FILE, "w", encoding="utf-8") as f:
#             json.dump(flashcard_cache, f, indent=2)
#         return summary
#     else:
#         print("❌ Error:", response.status_code, response.text)
#         return "[Error summarizing]"

semaphore = asyncio.Semaphore(3)

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

def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(i) for i in obj]
    elif obj is None:
        return ""
    else:
        return obj

@app.route("/", methods=["GET", "POST"])
def index():
    flashcards = []
    # if request.method == "POST":
    #     file = request.files.get("pdf")
    #     if file and file.filename.endswith(".pdf"):
    #         filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    #         file.save(filepath)

    chunks = extract_text_chunks("ground.pdf")
    flashcards = asyncio.run(summarize_all_chunks(chunks))
    flashcards = sanitize(flashcards)
    
    questions_count = len(flashcards)
    

    # return render_template("index.html", flashcards=flashcards)
    
    print(flashcards)

    return render_template("index.html", flashcards=flashcards, questions_count=questions_count)

if __name__ == "__main__":
    app.run(debug=True)
