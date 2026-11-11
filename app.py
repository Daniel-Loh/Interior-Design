import re

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


def _save_photo(project_id, field_name, photo_type):
    file = request.files.get(field_name)
    if not file or file.filename == '':
        return
    if not allowed_file(file.filename):
        flash(f'Invalid file type for {photo_type.lower()} photo. Use JPG, PNG or WEBP.')
        return
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        flash(f'{photo_type.capitalize()} photo too large. Maximum 5 MB.')
        return
    filename = secure_filename(f"{project_id}_{photo_type}_{file.filename}")
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    database.add_photo(project_id, f'uploads/{filename}', photo_type)


# ── Public routes ─────────────────────────────────────────────────────────────


# ── Customer Feature: Filter Interior Design Projects ──────────────

def _explore_context():

    # Get the filters selected by the Customer
    filters = {
        name: request.args.get(name, '').strip()
        for name in (
            'category',
            'style',
            'property_type',
            'q',
            'budget_min',
            'budget_max'
        )
    }

    # Retrieve matching projects from the database
    projects = database.get_customer_projects(filters)

    # Retrieve project cover photos
    covers = {}

    for project in projects:
        photos = database.get_photos(project['id'])

        cover = next(
            (photo for photo in photos
             if photo['photo_type'] == 'AFTER'),
            photos[0] if photos else None
        )

        covers[project['id']] = cover

    # Send the project data to Main.html
    return {
        'projects': projects,
        'filters': filters,
        'options': database.get_filter_options(),
        'covers': covers,
        'result_count': len(projects)
    }



@app.route('/')
def home():
    return render_template(
        'sites/Main.html',
        **_explore_context()
    )



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account_type = request.form.get('account_type', 'customer')
        session['role'] = account_type
        if account_type == 'designer':
            return redirect(url_for('designer_dashboard'))
        return redirect(url_for('home'))
    return render_template('sites/Login.html')


@app.route('/loginCheck', methods=['POST'])
def loginCheck():
    email = request.form.get('email')
    password = request.form.get('password')
    if email == 'Testing@email.com' and password == '123456':
        session['user'] = 'Testing'
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/Designers')
def designers():
    return render_template('sites/Designers.html')


@app.route('/SignUp')
def signup():
    return render_template('sites/SignUp.html')



@app.route('/Projects')
def projects():
    return render_template(
        'sites/Main.html',
        **_explore_context()
    )




@app.route('/About')
def about():
    return redirect(url_for('home') + '#about')




@app.route('/idp/<int:project_id>')
def idp_view(project_id):

    project = database.get_project(project_id)

    if not project or not project['is_visible']:
        return render_template('sites/404.html'), 404

    # Existing photo functionality
    photos = database.get_photos(project_id)

    before = [
        p for p in photos
        if p['photo_type'] == 'BEFORE'
    ]

    after = [
        p for p in photos
        if p['photo_type'] == 'AFTER'
    ]

    # CUSTOMER FEATURE US-C-04
    similar = database.get_customer_similar_projects(project_id)

    similar_covers = {}

    for item in similar:
        item_photos = database.get_photos(item['id'])

        cover = next(
            (p for p in item_photos if p['photo_type'] == 'AFTER'),
            item_photos[0] if item_photos else None
        )

        similar_covers[item['id']] = cover

    return render_template(
        'sites/idp_view.html',
        project=project,
        before=before,
        after=after,
        similar=similar,
        similar_covers=similar_covers
    )


# ── CUSTOMER FEATURE US-C-02: BROWSE DESIGNER PORTFOLIO ──

@app.route('/customer/portfolio')
def customer_portfolio():

    # Retrieve Interior Designer company information
    company = database.get_company()

    # Retrieve publicly visible projects
    projects = database.get_visible_projects()

    # Retrieve project cover images
    covers = {}

    for project in projects:
        photos = database.get_photos(project['id'])

        cover = next(
            (photo for photo in photos
             if photo['photo_type'] == 'AFTER'),
            photos[0] if photos else None
        )

        covers[project['id']] = cover

    return render_template(
        'sites/customer_portfolio.html',
        company=company,
        projects=projects,
        covers=covers
    )


# ── CUSTOMER FEATURE US-C-03: CONTACT DESIGNER ──

@app.route('/customer/contact/<int:project_id>', methods=['GET', 'POST'])
def customer_contact(project_id):

    # Retrieve the selected project
    project = database.get_project(project_id)

    # Check whether the project exists and is visible
    if not project or not project['is_visible']:
        return render_template('sites/404.html'), 404

    error = None

    # Keep entered values if validation fails
    form = {
        'name': '',
        'email': '',
        'message': ''
    }

    if request.method == 'POST':

        # Retrieve Customer information
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()

        form = {
            'name': name,
            'email': email,
            'message': message
        }

        # Validate the form
        if not name or not email or not message:
            error = 'Please fill in all required fields.'

        elif len(name) > 100 or len(email) > 254 or len(message) > 2000:
            error = 'One or more fields exceed the allowed length.'

        elif not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
            error = 'Please enter a valid email address.'

        else:
            # Save enquiry into database
            database.save_customer_enquiry(
                project_id=project_id,
                customer_name=name,
                customer_email=email,
                message=message
            )

            # Redirect after successful submission
            return redirect(
                url_for('customer_contact', project_id=project_id, sent=1)
            )

    return render_template(
        'sites/customer_contact.html',
        project=project,
        error=error,
        form=form,
        submitted=request.args.get('sent') == '1'
    )



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
    cover = {p['id']: database.get_photos(p['id'])[:1] for p in projects}
    return render_template('sites/company_preview.html', company=company, projects=projects, cover=cover)


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
    _save_photo(project_id, 'before_photo', 'BEFORE')
    _save_photo(project_id, 'after_photo', 'AFTER')
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
        _save_photo(project_id, 'before_photo', 'BEFORE')
        _save_photo(project_id, 'after_photo', 'AFTER')
        flash('Project saved.')
        return redirect(url_for('idp_edit', project_id=project_id))
    photos = database.get_photos(project_id)
    return render_template('sites/idp_edit.html', project=project, photos=photos)


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
