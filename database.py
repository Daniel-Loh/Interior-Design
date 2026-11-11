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

    # Customer Feature: Add renovation budget column
    existing_columns = {
        row['name']
        for row in conn.execute(
            "PRAGMA table_info(interior_design_project)"
        )
    }

    if 'budget' not in existing_columns:
        conn.execute(
            "ALTER TABLE interior_design_project ADD COLUMN budget REAL"
        )


    # Customer Feature US-C-03: Store enquiries
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_enquiry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id)
                REFERENCES interior_design_project(id)
        )
    """)


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


# ── CUSTOMER FEATURE: FILTER INTERIOR DESIGN PROJECTS ────────

def get_filter_options():
    """Retrieve available filter options for Customers."""

    conn = get_db()

    options = {}

    for field in ('category', 'style', 'property_type'):

        rows = conn.execute(
            f"""
            SELECT DISTINCT {field}
            FROM interior_design_project
            WHERE is_visible = 1
            AND {field} IS NOT NULL
            AND {field} != ''
            ORDER BY {field}
            """
        ).fetchall()

        options[field] = [row[0] for row in rows]

    conn.close()

    return options


def get_customer_projects(filters=None):
    """Retrieve visible projects matching Customer filters."""

    filters = filters or {}

    query = """
        SELECT *
        FROM interior_design_project
        WHERE is_visible = 1
    """

    values = []

    # Filter by category, style and property type
    for field in ('category', 'style', 'property_type'):

        value = (filters.get(field) or '').strip()

        if value:
            query += f" AND {field} = ?"
            values.append(value)

    # Search project name or description
    keyword = (filters.get('q') or '').strip()

    if keyword:
        query += " AND (title LIKE ? OR description LIKE ?)"
        values.extend([f"%{keyword}%", f"%{keyword}%"])

    # Filter by renovation budget
    budget_min = (filters.get('budget_min') or '').strip()
    budget_max = (filters.get('budget_max') or '').strip()

    try:
        minimum = float(budget_min) if budget_min else None
        maximum = float(budget_max) if budget_max else None

        if minimum is not None and (minimum < 0 or minimum != minimum):
            return []

        if maximum is not None and (maximum < 0 or maximum != maximum):
            return []

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                return []

        if minimum is not None:
            query += " AND budget >= ?"
            values.append(minimum)

        if maximum is not None:
            query += " AND budget <= ?"
            values.append(maximum)

    except ValueError:
        return []

    # Display featured projects first
    query += " ORDER BY is_featured DESC, id DESC"

    conn = get_db()

    rows = conn.execute(query, values).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ── CUSTOMER FEATURE US-C-03: SAVE CUSTOMER ENQUIRY ──

def save_customer_enquiry(project_id, customer_name, customer_email, message):
    """Save a Customer's enquiry about an Interior Design Project."""

    conn = get_db()

    try:
        cursor = conn.execute(
            """
            INSERT INTO customer_enquiry
            (project_id, customer_name, customer_email, message)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, customer_name, customer_email, message)
        )

        conn.commit()
        return cursor.lastrowid

    finally:
        conn.close()


# ── CUSTOMER FEATURE US-C-04: SIMILAR PROJECTS ──

def get_customer_similar_projects(project_id, limit=4):
    """Find similar visible Interior Design Projects."""

    # Retrieve the current project
    current_project = get_project(project_id)

    if not current_project or not current_project['is_visible']:
        return []

    # Retrieve all publicly visible projects
    projects = get_visible_projects()

    similar_projects = []

    for project in projects:

        # Do not recommend the currently viewed project
        if project['id'] == project_id:
            continue

        # Calculate similarity score
        score = 0

        if (current_project['category'] and
                project['category'] == current_project['category']):
            score += 1

        if (current_project['style'] and
                project['style'] == current_project['style']):
            score += 3

        if (current_project['property_type'] and
                project['property_type'] == current_project['property_type']):
            score += 2

        # Only include projects with matching attributes
        if score > 0:
            project['similarity_score'] = score
            similar_projects.append(project)

    # Display the most relevant projects first
    similar_projects.sort(
        key=lambda p: (
            -p['similarity_score'],
            -p['is_featured'],
            -p['id']
        )
    )

    return similar_projects[:limit]
