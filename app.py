import os
from functools import wraps
from flask import Flask, render_template, session, request, redirect, url_for, abort

app = Flask(__name__)
# For a real deployment set FLASK_KEY to a long, randomly generated value.
app.secret_key = os.environ.get('FLASK_KEY', 'demo-only-change-me')

# Demo-only user data. All changes reset when Flask restarts.
users = [
    {'id': 1, 'name': 'Alice Tan', 'email': 'alice@example.com', 'role': 'Customer', 'status': 'Approved'},
    {'id': 2, 'name': 'Daniel Lim', 'email': 'daniel@example.com', 'role': 'Interior Designer', 'status': 'Pending'},
    {'id': 3, 'name': 'Sarah Lee', 'email': 'sarah@example.com', 'role': 'Customer', 'status': 'Blocked'},
    {'id': 4, 'name': 'Marcus Wong', 'email': 'marcus@example.com', 'role': 'Interior Designer', 'status': 'Approved'},
]
next_user_id = 5

@app.route('/')
def home():
    return render_template('sites/Main.html')

@app.route('/login')
def login():
    return render_template('sites/Login.html')

@app.route('/loginCheck', methods=['POST'])
def loginCheck():
    email = request.form.get('email')
    password = request.form.get('password')
    # Reuse the existing loginCheck route for the demo administrator account.
    # Configure ADMIN_EMAIL, ADMIN_PASSWORD and FLASK_KEY before any real deployment.
    if (email == os.environ.get('ADMIN_EMAIL', 'Testing@email.com')
            and password == os.environ.get('ADMIN_PASSWORD', '123456')):
        session.clear()
        session['user'] = 'Admin'
        session['role'] = 'admin'
        return redirect(url_for('admin'))

    session.clear()
    return redirect(url_for('login', error='invalid'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/Designers')
def designers():
    return render_template('sites/Designers.html')

@app.route('/SignUp')
def signup():
    return render_template('sites/SignUp.html')

@app.route('/Projects')
def projects():
    return render_template('sites/Main.html')

@app.route('/About')
def about():
    return render_template('sites/Main.html')

# Admin pages and actions require an admin session, including direct URL access.
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'admin':
            if not session.get('user'):
                return redirect(url_for('login'))
            abort(403)
        return view(*args, **kwargs)
    return wrapped

@app.route('/admin')
@admin_required
def admin():
    return render_template('sites/Admin.html', users=users)

@app.route('/admin/add', methods=['POST'])
@admin_required
def admin_add():
    global next_user_id
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'Customer')
    if name and email and role in ('Customer', 'Interior Designer'):
        users.append({'id': next_user_id, 'name': name, 'email': email,
                      'role': role, 'status': 'Pending'})
        next_user_id += 1
    return redirect(url_for('admin'))

@app.route('/admin/status/<int:user_id>/<status>', methods=['POST'])
@admin_required
def admin_status(user_id, status):
    if status in ('Approved', 'Blocked'):
        for user in users:
            if user['id'] == user_id:
                user['status'] = status
                break
    return redirect(url_for('admin'))

@app.route('/admin/remove/<int:user_id>', methods=['POST'])
@admin_required
def admin_remove(user_id):
    users[:] = [user for user in users if user['id'] != user_id]
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
