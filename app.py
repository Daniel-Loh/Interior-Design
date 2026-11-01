import os
from flask import Flask, render_template, session

print("DEBUG - Available Env Keys:", list(os.environ.keys()))
print("DEBUG - FLASK_KEY present?", 'FLASK_KEY' in os.environ)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_KEY')

@app.route('/')
def home():
    session['user'] = "Testing"
    return render_template("sites/Main.html")

@app.route('/Designers')
def designers():
    return render_template("sites/Designers.html")

@app.route("/SignUp")
def signup():
    return render_template("sites/SignUp.html")


if __name__ == "__main__":
    app.run(debug=True, port=3000)