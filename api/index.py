from flask import Flask, render_template
from vercel_wsgi import handle_request

app = Flask(__name__, template_folder="templates")

@app.route("/")
def home():
    return render_template("index.html")

def handler(environ, start_response):
    return handle_request(app, environ, start_response)
