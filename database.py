import sqlite3
import os

DB_PATH = 'interior_design.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
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
            photo_type TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES interior_design_project(id)
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
