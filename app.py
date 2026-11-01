import os
from flask import Flask, render_template, session, request, redirect

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_KEY')

def home():    
    return render_template("sites/Main.html")

@app.route('/login', methods=['POST'])
def login():
    return render_template("sites/Login.html")

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect("/")

@app.route('/Designers')
def designers():
    return render_template("sites/Designers.html")

@app.route("/SignUp")
def signup():
    return render_template("sites/SignUp.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
