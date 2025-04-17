# app.py - Entry point for Hugging Face Spaces
import uvicorn
from main import app
import os

# This is the file that Hugging Face Spaces will look for
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)