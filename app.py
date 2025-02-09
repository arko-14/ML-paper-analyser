import os
import requests
import pdfplumber
import google.generativeai as genai
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, send_file
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from transformers import pipeline

# Initialize Transformer summarization pipeline (using BART)
transformer_summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Replace with your actual Gemini API key
GEMINI_API_KEY = "AIzaSyDJiCkjjOJzbQP3kDu7F5ku9CuSOMy4JBk"
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
os.makedirs("uploads", exist_ok=True)

summary_counter = 0

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text.strip()

def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join([p.get_text() for p in paragraphs])
        return text.strip() if text else None
    except Exception as e:
        print(f"URL extraction failed: {e}")
        return None

def summarize_with_gemini(text):
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(f"Summarize this research paper comprehensively:\n{text}")
        return response.text if response else None
    except Exception as e:
        print(f"Gemini API failed: {e}")
        return None

def summarize_with_transformer(text):
    try:
        summary = transformer_summarizer(text, max_length=150, min_length=50, do_sample=False)
        return summary[0]['summary_text'] if summary and len(summary) > 0 else None
    except Exception as e:
        print(f"Transformer summarization failed: {e}")
        return None

def summarize_with_lsa(text):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary_sentences = summarizer(parser.document, 5)  # Extract 5 summary sentences
    summary = " ".join([str(sentence) for sentence in summary_sentences])
    return summary if summary else "Failed to generate summary."

# Updated reading time function: calculates hours and minutes
def estimate_reading_time(text, words_per_minute=200):
    word_count = len(text.split())
    total_seconds = (word_count / words_per_minute) * 60
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours} hrs {minutes} min"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize():
    global summary_counter
    text = None

    if "pdf_file" in request.files and request.files["pdf_file"].filename:
        pdf_file = request.files["pdf_file"]
        pdf_path = os.path.join("uploads", pdf_file.filename)
        pdf_file.save(pdf_path)
        text = extract_text_from_pdf(pdf_path)
    elif "paper_url" in request.form and request.form["paper_url"].strip():
        text = extract_text_from_url(request.form["paper_url"])

    if not text:
        return jsonify({"error": "No valid input provided or could not extract text."}), 400

    # Try summarization in a chain: Gemini > Transformer > LSA
    summary = summarize_with_gemini(text)
    if not summary:
        summary = summarize_with_transformer(text)
    if not summary:
        summary = summarize_with_lsa(text)

    summary_counter += 1

    summary_filename = "summary.txt"
    summary_path = os.path.join("uploads", summary_filename)
    with open(summary_path, "w") as summary_file:
        summary_file.write(summary)

    orig_reading_time = estimate_reading_time(text)
    summary_reading_time = estimate_reading_time(summary)

    return jsonify({
        "summary": summary,
        "download_link": summary_filename,
        "papers_count": summary_counter,
        "original_reading_time": orig_reading_time,
        "summary_reading_time": summary_reading_time
    })

@app.route("/get_count")
def get_count():
    return jsonify({"papers_count": summary_counter})

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join("uploads", filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found!"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

