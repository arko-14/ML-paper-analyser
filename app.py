import os
import re
import requests
import pdfplumber
import google.generativeai as genai
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, send_file

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
# Counter Persistence Functions
# ----------------------------
COUNTER_FILE = "counter.txt"

def load_counter():
    """Load the counter from file. Returns 0 if the file doesn't exist or is invalid."""
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                return int(f.read().strip())
        except Exception as e:
            print("Error loading counter:", e)
            return 0
    return 0

def save_counter(counter):
    """Save the counter value to a file."""
    try:
        with open(COUNTER_FILE, "w") as f:
            f.write(str(counter))
    except Exception as e:
        print("Error saving counter:", e)

# Global summary counter is now loaded from file at startup
summary_counter = load_counter()

# ----------------------------
# Utility Functions
# ----------------------------
def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file, skipping pages with no text."""
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n".join(text).strip()

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
# Fallback Summarization Methods
# ----------------------------
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

def fallback_summarizer(text):
    """
    Attempts different summarization techniques in order:
    1. TextRank summarization.
    2. Gensim summarization (if available).
    3. Simple fallback (first 5 sentences).
    We limit the text size first to speed up processing.
    """
    limited_text = limit_text(text)
    summary = text_rank_summarizer(limited_text)
    if summary and summary.strip():
        return summary

    summary = gensim_nlp_summarizer(limited_text)
    if summary and summary.strip():
        return summary

    return simple_fallback_summarizer(limited_text)

# ----------------------------
# Primary Summarization Function
# ----------------------------
def summarize_with_gemini(text):
    """
    Tries to summarize text using the Gemini API.
    If that fails, falls back to local summarization techniques.
    """
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(
            f"Summarize this research paper comprehensively across these key dimensions:\n\n"
            f"Research Context:\n- Domain\n- Research Question\n- Significance\n\n"
            f"Methodology:\n- Design\n- Data Collection\n- Analytical Approach\n\n"
            f"Key Findings:\n- Primary Outcomes\n- Statistical Significance\n- Novel Discoveries\n\n"
            f"Implications:\n- Theoretical Impact\n- Practical Applications\n- Future Research Directions\n\n"
            f"Paper Text:\n{text}"
        )
        if response and response.text:
            return response.text
    except Exception as e:
        print("Gemini API failed:", e)

    # If Gemini summarization fails, use fallback summarization techniques
    return fallback_summarizer(text)

# ----------------------------
# New Utility: Reading Time Estimation
# ----------------------------
def estimate_reading_time(text, words_per_minute=80):
    """
    Calculates estimated reading time in hours and minutes based on word count.
    Returns a string in the format "X hrs Y" (without extra units).
    """
    word_count = len(text.split())
    total_seconds = (word_count / words_per_minute) * 60
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours} hrs {minutes}"

# ----------------------------
# Flask Routes
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize():
    global summary_counter
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

    summary = summarize_with_gemini(text)

    # Create a summary file
    summary_filename = "summary.txt"
    summary_path = os.path.join("uploads", summary_filename)
    with open(summary_path, "w") as summary_file:
        summary_file.write(summary)

    # Increment summary counter and save it to disk
    summary_counter += 1
    save_counter(summary_counter)

    # Estimate reading times
    original_reading_time = estimate_reading_time(text)
    summary_reading_time = estimate_reading_time(summary)

    return jsonify({
        "summary": summary,
        "download_link": summary_filename,
        "papers_count": summary_counter,
        "original_reading_time": original_reading_time,
        "summary_reading_time": summary_reading_time
    })

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
