import os
os.system("pip install Flask")

from Flask import Flask
from threading import Thread

app = flask(__name__)

@app.route('/')
def alive():
  return "alive"

def keep_alive():
  t = Thread(target=run)
  t.start()
