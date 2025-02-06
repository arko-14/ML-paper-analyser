import os
import requests
import pdfplumber
import google.generativeai as genai
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from celery import Celery

# 🔹 Replace this with your actual Gemini API key
GEMINI_API_KEY = "AIzaSyDJiCkjjOJzbQP3kDu7F5ku9CuSOMy4JBk"

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Flask app
app = Flask(__name__)

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'  # Set up your Redis broker URL here
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'  # Set up your Redis backend
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

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

# Celery task to summarize text
@celery.task(bind=True)
def summarize_task(self, text):
    try:
        summary = summarize_with_gemini(text)
        return summary
    except Exception as e:
        raise self.retry(exc=e)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize():
    text = None

    if "pdf_file" in request.files and request.files["pdf_file"].filename != "":
        pdf_file = request.files["pdf_file"]
        
        # Check file extension and size
        if not allowed_file(pdf_file.filename):
            return jsonify({"error": "Invalid file type. Only PDF is allowed."}), 400
        
        # Secure the filename and save
        pdf_filename = secure_filename(pdf_file.filename)
        pdf_path = os.path.join("uploads", pdf_filename)
        pdf_file.save(pdf_path)

        text = extract_text_from_pdf(pdf_path)

    elif "paper_url" in request.form and request.form["paper_url"].strip() != "":
        text = extract_text_from_url(request.form["paper_url"])

    if not text:
        return jsonify({"error": "No valid input provided or could not extract text."}), 400

    # Start the summarization task asynchronously using Celery
    task = summarize_task.apply_async(args=[text])

    # Return the task ID so the client can query the result later
    return jsonify({"task_id": task.id}), 202

@app.route("/task_status/<task_id>")
def task_status(task_id):
    task = summarize_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': task.state}
    elif task.state != 'FAILURE':
        response = {'state': task.state, 'summary': task.result}
    else:
        response = {'state': task.state, 'error': str(task.info)}
    return jsonify(response)

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)
