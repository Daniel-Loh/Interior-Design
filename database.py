import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = 'interior_design.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Customer', 'Interior Designer', 'Platform Manager')),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS company_profile (
            id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT DEFAULT '',
            description TEXT DEFAULT '',
            contact_info TEXT DEFAULT ''
        );
        INSERT OR IGNORE INTO company_profile (id) VALUES (1);

        CREATE TABLE IF NOT EXISTS interior_design_project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_featured INTEGER DEFAULT 0,
            is_visible INTEGER DEFAULT 1,
            category TEXT DEFAULT '',
            style TEXT DEFAULT '',
            property_type TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS project_photo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            photo_type TEXT NOT NULL CHECK(photo_type IN ('BEFORE', 'AFTER')),
            FOREIGN KEY (project_id) REFERENCES interior_design_project(id)
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS project_tags (
            project_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (project_id, tag_id),
            FOREIGN KEY (project_id) REFERENCES interior_design_project(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        );
    ''')
    conn.commit()
    conn.close()


def get_company():
    conn = get_db()
    row = conn.execute('SELECT * FROM company_profile WHERE id = 1').fetchone()
    conn.close()
    return dict(row) if row else {}


def save_company(name, description, contact_info):
    conn = get_db()
    conn.execute(
        'UPDATE company_profile SET name=?, description=?, contact_info=? WHERE id=1',
        (name, description, contact_info)
    )
    conn.commit()
    conn.close()


def get_all_projects():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM interior_design_project ORDER BY is_featured DESC, id DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_visible_projects():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM interior_design_project WHERE is_visible=1 ORDER BY is_featured DESC, id DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project(project_id):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM interior_design_project WHERE id=?', (project_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_project(title, description, category, style, property_type):
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO interior_design_project (title, description, category, style, property_type) VALUES (?,?,?,?,?)',
        (title, description, category, style, property_type)
    )
    project_id = cur.lastrowid
    conn.commit()
    conn.close()
    return project_id


def save_project(project_id, title, description, category, style, property_type):
    conn = get_db()
    conn.execute(
        'UPDATE interior_design_project SET title=?, description=?, category=?, style=?, property_type=? WHERE id=?',
        (title, description, category, style, property_type, project_id)
    )
    conn.commit()
    conn.close()


def toggle_featured(project_id):
    conn = get_db()
    conn.execute(
        'UPDATE interior_design_project SET is_featured = 1 - is_featured WHERE id=?',
        (project_id,)
    )
    conn.commit()
    conn.close()


def toggle_visibility(project_id):
    conn = get_db()
    conn.execute(
        'UPDATE interior_design_project SET is_visible = 1 - is_visible WHERE id=?',
        (project_id,)
    )
    conn.commit()
    conn.close()


def get_photos(project_id):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM project_photo WHERE project_id=?', (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_photo(photo_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM project_photo WHERE id=?', (photo_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_photo(project_id, image_url, photo_type):
    conn = get_db()
    conn.execute(
        'INSERT INTO project_photo (project_id, image_url, photo_type) VALUES (?,?,?)',
        (project_id, image_url, photo_type)
    )
    conn.commit()
    conn.close()


def delete_photo(photo_id):
    conn = get_db()
    conn.execute('DELETE FROM project_photo WHERE id=?', (photo_id,))
    conn.commit()
    conn.close()


# --- Users ---

def create_user(email, password, role):
    conn = get_db()
    conn.execute(
        'INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
        (email, generate_password_hash(password), role)
    )
    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_user(email, password):
    """Return user dict on success, None on failure."""
    user = get_user_by_email(email)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None


def get_all_users():
    conn = get_db()
    rows = conn.execute('SELECT id, email, role, created_at FROM users ORDER BY id').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_role(user_id, role):
    conn = get_db()
    conn.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()


# --- Tags ---

def get_or_create_tag(name):
    conn = get_db()
    row = conn.execute('SELECT id FROM tags WHERE name=?', (name,)).fetchone()
    if row:
        tag_id = row['id']
    else:
        cur = conn.execute('INSERT INTO tags (name) VALUES (?)', (name,))
        tag_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tag_id


def get_all_tags():
    conn = get_db()
    rows = conn.execute('SELECT * FROM tags ORDER BY name').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project_tags(project_id):
    conn = get_db()
    rows = conn.execute(
        '''SELECT t.id, t.name FROM tags t
           JOIN project_tags pt ON pt.tag_id = t.id
           WHERE pt.project_id=? ORDER BY t.name''',
        (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_project_tags(project_id, tag_names):
    """Replace all tags on a project with the given list of tag name strings."""
    conn = get_db()
    conn.execute('DELETE FROM project_tags WHERE project_id=?', (project_id,))
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        row = conn.execute('SELECT id FROM tags WHERE name=?', (name,)).fetchone()
        if row:
            tag_id = row['id']
        else:
            cur = conn.execute('INSERT INTO tags (name) VALUES (?)', (name,))
            tag_id = cur.lastrowid
        conn.execute('INSERT OR IGNORE INTO project_tags (project_id, tag_id) VALUES (?,?)', (project_id, tag_id))
    conn.commit()
    conn.close()


def remove_project_tag(project_id, tag_id):
    conn = get_db()
    conn.execute('DELETE FROM project_tags WHERE project_id=? AND tag_id=?', (project_id, tag_id))
    conn.commit()
    conn.close()
