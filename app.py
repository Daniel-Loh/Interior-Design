from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
import database

app = Flask(__name__)
app.secret_key = 'dev-secret-key'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Public routes ────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('sites/Main.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account_type = request.form.get('account_type', 'customer')
        session['role'] = account_type
        if account_type == 'designer':
            return redirect(url_for('designer_dashboard'))
        return redirect(url_for('home'))
    return render_template('sites/Login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/idp/<int:project_id>')
def idp_view(project_id):
    project = database.get_project(project_id)
    if not project or not project['is_visible']:
        return render_template('sites/404.html'), 404
    photos = database.get_photos(project_id)
    before = [p for p in photos if p['photo_type'] == 'BEFORE']
    after  = [p for p in photos if p['photo_type'] == 'AFTER']
    return render_template('sites/idp_view.html', project=project, before=before, after=after)


# ── Designer routes ───────────────────────────────────────────────────────────

@app.route('/designer/dashboard')
def designer_dashboard():
    projects = database.get_all_projects()
    return render_template('sites/designer_dashboard.html', projects=projects)


@app.route('/designer/company', methods=['GET', 'POST'])
def company_edit():
    if request.method == 'POST':
        database.save_company(
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            contact_info=request.form.get('contact_info', '')
        )
        flash('Company profile saved.')
        return redirect(url_for('company_edit'))
    company = database.get_company()
    return render_template('sites/company_edit.html', company=company)


@app.route('/designer/company/preview')
def company_preview():
    company = database.get_company()
    projects = database.get_visible_projects()
    return render_template('sites/company_preview.html', company=company, projects=projects)


@app.route('/designer/idp/new')
def idp_new():
    return render_template('sites/idp_edit.html', project=None, photos=[])


@app.route('/designer/idp/create', methods=['POST'])
def idp_create():
    project_id = database.create_project(
        title=request.form.get('title', 'Untitled'),
        description=request.form.get('description', ''),
        category=request.form.get('category', ''),
        style=request.form.get('style', ''),
        property_type=request.form.get('property_type', '')
    )
    flash('Project created.')
    return redirect(url_for('idp_edit', project_id=project_id))


@app.route('/designer/idp/<int:project_id>/edit', methods=['GET', 'POST'])
def idp_edit(project_id):
    project = database.get_project(project_id)
    if not project:
        return redirect(url_for('designer_dashboard'))
    if request.method == 'POST':
        database.save_project(
            project_id=project_id,
            title=request.form.get('title', ''),
            description=request.form.get('description', ''),
            category=request.form.get('category', ''),
            style=request.form.get('style', ''),
            property_type=request.form.get('property_type', '')
        )
        flash('Project saved.')
        return redirect(url_for('idp_edit', project_id=project_id))
    photos = database.get_photos(project_id)
    return render_template('sites/idp_edit.html', project=project, photos=photos)


@app.route('/designer/idp/<int:project_id>/photo', methods=['POST'])
def idp_upload_photo(project_id):
    photo_type = request.form.get('photo_type', 'BEFORE')
    file = request.files.get('photo')

    if not file or file.filename == '':
        flash('No file selected.')
        return redirect(url_for('idp_edit', project_id=project_id))

    if not allowed_file(file.filename):
        flash('Invalid file type. Use JPG, PNG or WEBP.')
        return redirect(url_for('idp_edit', project_id=project_id))

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        flash('File too large. Maximum 5 MB.')
        return redirect(url_for('idp_edit', project_id=project_id))

    filename = secure_filename(f"{project_id}_{photo_type}_{file.filename}")
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    database.add_photo(project_id, f'uploads/{filename}', photo_type)
    flash('Photo uploaded.')
    return redirect(url_for('idp_edit', project_id=project_id))


@app.route('/designer/idp/<int:project_id>/photo/<int:photo_id>/delete', methods=['POST'])
def idp_delete_photo(project_id, photo_id):
    photo = database.get_photo(photo_id)
    if photo:
        file_path = os.path.join('static', photo['image_url'])
        if os.path.exists(file_path):
            os.remove(file_path)
        database.delete_photo(photo_id)
        flash('Photo removed.')
    return redirect(url_for('idp_edit', project_id=project_id))


@app.route('/designer/idp/<int:project_id>/feature', methods=['POST'])
def idp_toggle_feature(project_id):
    database.toggle_featured(project_id)
    return redirect(url_for('designer_dashboard'))


@app.route('/designer/idp/<int:project_id>/hide', methods=['POST'])
def idp_toggle_hide(project_id):
    database.toggle_visibility(project_id)
    return redirect(url_for('designer_dashboard'))


if __name__ == '__main__':
    database.init_db()
    app.run(debug=True, port=5001)
