# === Imports ===
import os
import pdfplumber
from docx import Document
from flask import Flask, request, render_template_string, session
from dotenv import load_dotenv
from io import BytesIO
import requests

# === Environment Setup ===
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# === Flask App Initialization ===
app = Flask(__name__)
app.secret_key = "your_secret_key_here"

resume_text = ""

# === Resume Text Extraction ===
def extract_text(file_stream, filename):
    if filename.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file_stream) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    elif filename.endswith(".docx"):
        doc = Document(BytesIO(file_stream.read()))
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return "Unsupported file type. Please upload a PDF or DOCX."

# === OpenRouter Q&A Function ===
def ask_about_resume(resume_text, question):
    if not OPENROUTER_API_KEY:
        return "Error: API key not loaded. Please check your .env file."

    try:
        resume_text = resume_text[:3000]
        prompt = f"You are a resume analysis bot. Here's the resume:\n\n{resume_text}\n\nAnswer this question: {question}"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": [
                {"role": "system", "content": "You are a helpful resume analysis assistant."},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )

        result = response.json()
        print("DEBUG:", result)

        if "error" in result:
            return f"API Error: {result['error']['message']}"
        return result["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"Error: {str(e)}"

# === Flask Route ===
@app.route("/", methods=["GET", "POST"])
def home():
    global resume_text
    answer = ""

    if "chat_history" not in session:
        session["chat_history"] = []

    if request.method == "POST":
        if "resume" in request.files and request.files["resume"].filename:
            file = request.files["resume"]
            resume_text = extract_text(file.stream, file.filename)
            session["chat_history"] = []

        if "question" in request.form and request.form["question"]:
            question = request.form["question"]
            if resume_text:
                answer = ask_about_resume(resume_text, question)
                session["chat_history"].append({"question": question, "answer": answer})
                session.modified = True

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>🧠 Resume Chatbot (OpenRouter)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #f8f9fa;
            padding: 2rem;
            font-family: 'Segoe UI', sans-serif;
        }
        .chat-bubble {
            padding: 1rem;
            border-radius: 1rem;
            margin-bottom: 1rem;
            max-width: 80%;
        }
        .user-bubble {
            background-color: #d1e7dd;
            align-self: flex-end;
        }
        .bot-bubble {
            background-color: #e2e3e5;
            align-self: flex-start;
        }
        .chat-container {
            display: flex;
            flex-direction: column;
        }
        .chat-history {
            margin-top: 2rem;
        }
        .form-section {
            margin-bottom: 2rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2 class="mb-4">🧠 Resume Chatbot <small class="text-muted">(OpenRouter)</small></h2>

        <div class="form-section">
            <form method="post" enctype="multipart/form-data" class="mb-3">
                <div class="input-group">
                    <input type="file" name="resume" accept=".pdf,.docx" class="form-control">
                    <button type="submit" class="btn btn-primary">Upload Resume</button>
                </div>
            </form>

            <form method="post">
                <div class="input-group">
                    <input type="text" name="question" placeholder="Ask a question about the resume" class="form-control">
                    <button type="submit" class="btn btn-success">Ask</button>
                </div>
            </form>
        </div>

        <div class="chat-history">
            <h4>💬 Chat History</h4>
            <div class="chat-container">
                {% for chat in session.get('chat_history', []) %}
                    <div class="chat-bubble user-bubble"><strong>You:</strong> {{ chat['question'] }}</div>
                    <div class="chat-bubble bot-bubble"><strong>Bot:</strong> {{ chat['answer'] }}</div>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
""")

# === Run App ===
if __name__ == "__main__":
    app.run(debug=True)