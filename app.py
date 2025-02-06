import os
import requests
import pdfplumber
import google.generativeai as genai
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, send_file

# 🔹 Replace this with your actual Gemini API key
GEMINI_API_KEY = "AIzaSyDJiCkjjOJzbQP3kDu7F5ku9CuSOMy4JBk"

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text.strip()

# Function to extract text from a webpage
def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join([p.get_text() for p in paragraphs])
        return text.strip() if text else None
    except:
        return None

# Function to summarize using Gemini API
def summarize_with_gemini(text):
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(f"Summarize this research paper:\n\n{text}")
    return response.text if response else "Failed to generate summary."

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize():
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

    return jsonify({"summary": summary, "download_link": summary_filename})

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Ensure the file exists in the "uploads" directory
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

