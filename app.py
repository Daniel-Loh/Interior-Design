from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("sites/Main.html")

@app.route('/Designers')
def designers():
    return render_template("sites/Designers.html")

@app.route("/SignUp")
def signup():
    return render_template("sites/SignUp.html")


if __name__ == "__main__":
    app.run(debug=True, port=3000)