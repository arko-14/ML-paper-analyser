#!/bin/bash

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Download NLTK punkt resource
python -c "import nltk; nltk.download('punkt')"
