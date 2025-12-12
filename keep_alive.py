from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ DV Bot is Alive and Running!"

def run():
    # Render assigns a random port to the PORT environment variable
    # We must listen on that port, or default to 10000 for local testing
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def start_server():
    t = Thread(target=run)
    t.start()