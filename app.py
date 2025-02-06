import nltk

# Download required NLTK resources
nltk.download('punkt')
nltk.download('stopwords')
import os
import re
import requests
import pdfplumber
import google.generativeai as genai
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, send_file
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from functools import lru_cache

# Fallback summarizer libraries for TextRank
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# Attempt to import gensim's summarizer
try:
    from gensim.summarization import summarize as gensim_summarize
except ImportError:
    gensim_summarize = None

# 🔹 Replace this with your actual Gemini API key
GEMINI_API_KEY = "AIzaSyDJiCkjjOJzbQP3kDu7F5ku9CuSOMy4JBk"

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)

# ----------------------------
# Utility Functions
# ----------------------------
def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file, skipping pages with no text."""
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                texts.append(page_text)
    return "\n".join(texts).strip()

def extract_text_from_url(url):
    """Extracts text from a webpage URL."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join([p.get_text() for p in paragraphs])
        return text.strip() if text else None
    except Exception as e:
        print("Error extracting text from URL:", e)
        return None

def limit_text(text, max_words=2000):
    """Limit the text to a maximum number of words for faster processing."""
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words])
    return text

# Precompile a regex pattern for sentence splitting
SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.!?])\s+')

# ----------------------------
# Individual Summarization Methods
# ----------------------------
def gemini_api_call(text):
    """
    Attempts to summarize text using the Gemini API.
    Returns the summary if successful, or None on failure.
    """
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(f"Summarize this research paper in simple words:\n\n{text}")
        if response and response.text:
            return response.text
    except Exception as e:
        print("Gemini API failed:", e)
    return None

def text_rank_summarizer(text):
    """
    Uses the TextRank algorithm via Sumy to extract key sentences.
    Returns a summary string or None if it fails.
    """
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = TextRankSummarizer()
        summary_sentences = summarizer(parser.document, 5)  # Extract 5 key sentences
        summary = " ".join(str(sentence) for sentence in summary_sentences)
        if summary:
            return summary
    except Exception as e:
        print("TextRank summarization failed:", e)
    return None

def gensim_nlp_summarizer(text):
    """
    Uses Gensim's summarizer (an NLP-based technique) to summarize the text.
    Returns the summary or None if it fails.
    """
    if not gensim_summarize:
        print("Gensim is not available.")
        return None

    try:
        # Gensim's summarize may fail if the text is too short or not well-formed.
        summary = gensim_summarize(text)
        if summary:
            return summary
    except Exception as e:
        print("Gensim summarization failed:", e)
    return None

def simple_fallback_summarizer(text):
    """
    A very basic fallback that returns the first five sentences of the text.
    """
    try:
        sentences = SENTENCE_SPLIT_REGEX.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) >= 5:
            summary = '. '.join(sentences[:5])
            if not summary.endswith('.'):
                summary += '.'
        else:
            summary = text
        return summary
    except Exception as e:
        print("Simple fallback summarizer failed:", e)
        return "Failed to generate summary using fallback methods."

# ----------------------------
# Concurrent Summarization with Timeouts
# ----------------------------
def concurrent_summarize(text):
    """
    Runs multiple summarization methods concurrently:
      - Gemini API call (full text)
      - TextRank summarization (on limited text)
      - Gensim summarization (on limited text)
    Returns the first valid summary that is produced or falls back to a simple summarizer.
    Each task has a per-call timeout.
    """
    limited_text = limit_text(text)
    methods = {
        "gemini": gemini_api_call,
        "text_rank": text_rank_summarizer,
        "gensim": gensim_nlp_summarizer
    }
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_method = {
            executor.submit(method, text if name == "gemini" else limited_text): name
            for name, method in methods.items()
        }
        for future in as_completed(future_to_method):
            method_name = future_to_method[future]
            try:
                # Set a timeout for each method (in seconds)
                result = future.result(timeout=5)
                if result and result.strip():
                    print(f"{method_name} method succeeded.")
                    return result
                else:
                    print(f"{method_name} method returned an empty summary.")
            except TimeoutError:
                print(f"{method_name} method timed out.")
            except Exception as e:
                print(f"{method_name} method failed with exception: {e}")

    # If none of the concurrent tasks produce a valid summary, use the simple fallback.
    print("Falling back to simple summarizer.")
    return simple_fallback_summarizer(limited_text)

@lru_cache(maxsize=32)
def cached_summarize(text):
    """Caches the summarization result for a given text."""
    return concurrent_summarize(text)

def summarize_with_concurrency(text):
    """
    Attempts to summarize the text by running multiple methods concurrently.
    Uses caching to avoid reprocessing the same text.
    """
    return cached_summarize(text)

# ----------------------------
# Flask Routes
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize_route():
    text = None

    if "pdf_file" in request.files and request.files["pdf_file"].filename != "":
        pdf_file = request.files["pdf_file"]
        pdf_path = os.path.join("uploads", pdf_file.filename)
        pdf_file.save(pdf_path)
        text = extract_text_from_pdf(pdf_path)
    elif "paper_url" in request.form and request.form["paper_url"].strip() != "":
        text = extract_text_from_url(request.form["paper_url"])

    if not text:
        return jsonify({"error": "No valid input provided or could not extract text."}), 400

    summary = summarize_with_concurrency(text)

    # Create a summary file
    summary_filename = "summary.txt"
    summary_path = os.path.join("uploads", summary_filename)
    with open(summary_path, "w") as summary_file:
        summary_file.write(summary)

    return jsonify({"summary": summary, "download_link": summary_filename})

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
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)


