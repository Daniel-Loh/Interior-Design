from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("sites/Main.html")


@app.route('/login')
def login():
    return render_template("sites/Login.html")


if __name__ == "__main__":
    # Port 5000 is already in use on this machine by another app.
    app.run(debug=True, port=5001)
