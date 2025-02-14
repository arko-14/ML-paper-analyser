# Paperdigest

Paperdigest is an AI-powered research paper summarizer that distills lengthy academic texts into concise, easy-to-read summaries. It leverages the Gemini API as the primary summarization engine with fallback options (using Sumy's TextRank and Gensim), offers estimated reading times, and provides accessibility features like Text-to-Speech (TTS). Users can download summaries & share summaries via social media, and enjoy a clean, user-friendly web interface.

## Features

- **AI-Driven Summarization:**
    
    Utilizes the Gemini API to generate comprehensive summaries across key dimensions such as research context, methodology, key findings, and implications.
    
- **Fallback Summarizers:**
    
    In case the Gemini API fails, the application automatically falls back to:
    
    - Sumy’s TextRank summarizer,
    - Gensim summarization (if available),
    - A simple fallback that returns the first five sentences.
- **Multiple Input Options:**
    
    Accepts research paper input either as a PDF upload or via a URL. The text is extracted using PyMuPDF (for PDFs) and Requests-HTML (for webpages).
    
- **Download Options:**
    
    Generates both a text file and a PDF file of the summary, enabling users to download their summaries in their preferred format.
    
- **Reading Time Estimation:**
    
    Calculates and displays the estimated reading time for the original paper and the summary, helping users quickly gauge the time saved.
    
- **Accessibility with Text-to-Speech (TTS):**
    
    Provides a “Listen” button that uses the Web Speech API to read the summary aloud, supporting accessibility for visually impaired users.
    
- **Sharing Capability:**
    
    Includes a share button that lets users quickly share the generated summary via Email, Twitter, or Facebook.
    
- **Usage Statistics:**
    
    Maintains a persistent counter for the number of papers summarized.
    

## Demo

*(Include a screenshot or link to a live demo if available.)*

## Installation

### Prerequisites

- Python 3.7 or higher
- Git
- (Optional) A virtual environment tool such as `venv` or `virtualenv`

### Clone the Repository

```bash
bash
CopyEdit
git clone https://github.com/yourusername/paperdigest.git
cd paperdigest

```

### Set Up Virtual Environment (Optional but Recommended)

```bash
bash
CopyEdit
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

```

### Install Dependencies

Make sure you have all necessary dependencies installed by running:

```bash
bash
CopyEdit
pip install -r requirements.txt

```

Your `requirements.txt` should include:

```
ini
CopyEdit
Flask==2.2.2
google-generativeai==<appropriate-version>
fpdf2==2.4.7
PyMuPDF==1.22.3
sumy==0.9.0
gensim==4.2.0
requests==2.28.2
requests-html==0.10.0
beautifulsoup4==4.11.1

```

> Note: Replace <appropriate-version> for google-generativeai with the version you are using.
> 

## Configuration

1. **API Key:**Replace the placeholder Gemini API key in your `app.py` file:
    
    ```python
    python
    CopyEdit
    GEMINI_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY"
    
    ```
    
2. **Uploads Folder:**The application will create an `uploads` folder in the project directory to store temporary files (e.g., uploaded PDFs and generated summary files).

## Running the Application

To start the Flask development server, run:

```bash
bash
CopyEdit
python app.py

```

The application will be accessible at http://127.0.0.1:5000/.

## Usage

1. **Upload or URL:**
    
    On the homepage, you can either:
    
    - Upload a PDF file of a research paper, or
    - Enter a research paper URL.
2. **Generate Summary:**
    
    Click the "Summarize" button to generate a summary. The summary box will display:
    
    - The generated summary,
    - Estimated reading times for the original text and the summary,
    - Download links for the text and PDF versions,
    - Share and Listen (TTS) buttons.
3. **Text-to-Speech:**
    
    Click the "Listen" button to have the summary read aloud using the browser's TTS functionality. The TTS feature attempts to use an Indian English voice (if available) with a calm tone.
    
4. **Download:**
    
    Use the provided download links to save the summary in your preferred format.
    
5. **Share:**
    
    The share button offers options to share the summary via Email, Twitter, or Facebook.
    
6. **Paper Counter:**
    
    The bottom of the page displays the number of papers summarized so far.
    
## Contributing

Contributions are welcome! If you'd like to contribute:

- Fork this repository.
- Create a new branch for your feature or bugfix.
- Submit a pull request describing your changes.

## License

This project is licensed under the MIT License.

## Contact

For questions, feedback, or suggestions, feel free to reach out via [Twitter](https://twitter.com/futurebeast_04) or open an issue in this repository.
