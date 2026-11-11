"""Local SQLite persistence for the Pending demo (no online database required)."""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import randint

DB_PATH = Path(__file__).resolve().parent / 'interior_design.db'
SGT = timezone(timedelta(hours=8))  # Singapore has no daylight saving time
TAG_FIELDS = ('category', 'style', 'property_type', 'room_count', 'apartment_type')
TAG_WEIGHTS = {'category': 1, 'style': 3, 'property_type': 2, 'room_count': 2, 'apartment_type': 3}
ROOM_OPTIONS = ('3 room', '4 room', '5 room', '6 room')
APARTMENT_OPTIONS = ('Studio apartment', 'Penthouse', 'Duplex', 'Standard apartment')


def now_sg():
    return datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')


class _DemoConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def get_db():
    connection = sqlite3.connect(DB_PATH, factory=_DemoConnection)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def init_db():
    """Create demo tables and safely add columns to an existing local database."""
    with get_db() as conn:
        # To use if you need to recreate/reset the values in database
        #reset = True
        #if reset:
        #    conn.execute("DROP TABLE IF EXISTS company_profile")
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS company_profile (
                id INTEGER PRIMARY KEY DEFAULT 1,
                name TEXT DEFAULT '', description TEXT DEFAULT '', contact_info TEXT DEFAULT '', weights_views INTEGER DEFAULT 0.5, weights_short INTEGER DEFAULT 0.5
            );
            INSERT OR IGNORE INTO company_profile (id) VALUES (1);
            CREATE TABLE IF NOT EXISTS interior_design_project (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, description TEXT DEFAULT '',
                is_featured INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1,
                category TEXT DEFAULT '', style TEXT DEFAULT '', property_type TEXT DEFAULT '',
                viewership_count INTEGER DEFAULT 0.5, shortlist_count INTEGER DEFAULT 0.5
            );
            CREATE TABLE IF NOT EXISTS project_photo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL, image_url TEXT NOT NULL, photo_type TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES interior_design_project(id)
            );
            CREATE TABLE IF NOT EXISTS demo_users (
                account_key TEXT PRIMARY KEY, email TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL, created_at TEXT NOT NULL, last_login_at TEXT NOT NULL,
                login_count INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS favorite_project (
                account_key TEXT NOT NULL, project_id INTEGER NOT NULL,
                saved_at TEXT NOT NULL, PRIMARY KEY(account_key, project_id),
                FOREIGN KEY(project_id) REFERENCES interior_design_project(id)
            );
            CREATE TABLE IF NOT EXISTS designer_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_key TEXT NOT NULL DEFAULT 'demo-designer',
                event_type TEXT NOT NULL,
                project_id INTEGER,
                project_title TEXT NOT NULL DEFAULT '',
                occurred_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_favorite_account ON favorite_project(account_key);
            CREATE INDEX IF NOT EXISTS idx_activity_date ON designer_activity(occurred_at);
        ''')
        existing = {c['name'] for c in conn.execute('PRAGMA table_info(interior_design_project)')}
        for column in ('room_count', 'apartment_type'):
            if column not in existing:
                conn.execute(f"ALTER TABLE interior_design_project ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
        for column in ('created_at', 'updated_at', 'viewership_count', 'shortlist_count'):
            if column not in existing:
                conn.execute(f"ALTER TABLE interior_design_project ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0")
        count = conn.execute('SELECT COUNT(*) AS n FROM interior_design_project').fetchone()['n']
        if count == 0:
            _seed_demo_projects(conn)


def _seed_demo_projects(conn):
    """Only on an empty database. These are clearly sample listings, not real projects."""
    samples = [
        ('Warm Scandinavian 4-Room Home', 'Demo project: light oak, soft tones and practical family storage.', 'Residential','Scandinavian','HDB 4-Room','4 room','Standard apartment', randint(0,100), randint(0,100)),
        ('Minimalist City Penthouse', 'Demo project: airy spaces with clean lines and warm stone textures.', 'Residential','Minimalist','Condominium','5 room','Penthouse', randint(0,100), randint(0,100)),
        ('Modern Duplex Living', 'Demo project: double-height living area and a modern open-plan kitchen.', 'Residential','Modern','Condominium','4 room','Duplex', randint(0,100), randint(0,100)),
        ('Calm Studio Apartment', 'Demo project: multi-use furniture for compact, flexible living.', 'Residential','Minimalist','Condominium','3 room','Studio apartment', randint(0,100), randint(0,100)),
        ('Industrial Family Home', 'Demo project: textured concrete, steel accents and family-friendly finishes.', 'Residential','Industrial','HDB 5-Room','5 room','Standard apartment', randint(0,100), randint(0,100)),
        ('Contemporary Four-Room Flat', 'Demo project: refined neutrals, feature lighting and adaptable storage.', 'Residential','Contemporary','HDB 4-Room','4 room','Standard apartment', randint(0,100), randint(0,100)),
        ('Modern Penthouse Retreat', 'Demo project: panoramic views, dark timber and soft contemporary detailing.', 'Residential','Modern','Condominium','5 room','Penthouse', randint(0,100), randint(0,100)),
        ('Scandinavian Duplex Hideaway', 'Demo project: bright timber details across two levels.', 'Residential','Scandinavian','Condominium','4 room','Duplex', randint(0,100), randint(0,100)),
        ('Traditional Six-Room Residence', 'Demo project: classic finishes and generous entertaining spaces.', 'Residential','Traditional','Landed','6 room','Standard apartment', randint(0,100), randint(0,100)),
        ('Eclectic Three-Room Makeover', 'Demo project: cheerful accents and clever compact-space storage.', 'Residential','Eclectic','HDB 3-Room','3 room','Standard apartment', randint(0,100), randint(0,100)),
    ]
    date = now_sg()
    conn.executemany('''
        INSERT INTO interior_design_project
        (title,description,category,style,property_type,room_count,apartment_type,created_at,updated_at,viewership_count,shortlist_count,is_featured)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ''', [(title, desc, category, style, prop, rooms, apartment, date, date, viewership, shortlist, 1 if idx < 3 else 0) for
          idx,(title,desc,category,style,prop,rooms,apartment, viewership, shortlist) in enumerate(samples)])


def get_company():
    with get_db() as conn:
        row = conn.execute('SELECT * FROM company_profile WHERE id=1').fetchone()
        return dict(row) if row else {}


def get_all_companies():
    with get_db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM company_profile ORDER BY id')]


def save_weights(views, short):
    with get_db() as conn:
        conn.execute('UPDATE company_profile SET weights_views=?, weights_short=? WHERE id=1',
                     (views, short))


def save_company(name, description, contact_info):
    with get_db() as conn:
        conn.execute('UPDATE company_profile SET name=?, description=?, contact_info=? WHERE id=1',
                     (name,description,contact_info))


def get_all_projects():
    with get_db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM interior_design_project ORDER BY is_featured DESC,id DESC')]


def get_visible_projects(filters=None):
    filters = filters or {}
    query = 'SELECT * FROM interior_design_project WHERE is_visible=1'
    values = []
    for field in TAG_FIELDS:
        value = (filters.get(field) or '').strip()
        if value:
            query += f' AND {field} = ?'
            values.append(value)
    search = (filters.get('q') or '').strip()
    if search:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        values += [f'%{search}%', f'%{search}%']
    query += ' ORDER BY is_featured DESC, id DESC'
    with get_db() as conn:
        return [dict(r) for r in conn.execute(query,values)]


def get_project(project_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM interior_design_project WHERE id=?',(project_id,)).fetchone()
        return dict(row) if row else None


def get_filter_options():
    options = {}
    with get_db() as conn:
        for field in TAG_FIELDS:  # predefined column names only
            rows = conn.execute(f'SELECT DISTINCT {field} FROM interior_design_project WHERE is_visible=1 AND {field} != "" ORDER BY {field}').fetchall()
            options[field] = [r[0] for r in rows]
    return options


def get_similar_projects(tags, excluded_ids=None, limit=4):
    """Return visible projects ranked by weighted exact tag matches, excluding zero matches."""
    excluded_ids = set(excluded_ids or ())
    ranked = []
    for project in get_visible_projects():
        if project['id'] in excluded_ids:
            continue
        matched = [field for field in TAG_FIELDS if (tags.get(field) or '').strip() and
                   project.get(field) == tags.get(field)]
        score = sum(TAG_WEIGHTS[f] for f in matched)
        if score:
            project['matched_tags'] = [project[f] for f in matched]
            project['match_score'] = score
            ranked.append(project)
    ranked.sort(key=lambda p: (-p['match_score'], -p['is_featured'], -p['id']))
    return ranked[:limit]


def record_activity(conn, event_type, project_id, project_title, account_key='demo-designer'):
    conn.execute('INSERT INTO designer_activity (account_key,event_type,project_id,project_title,occurred_at) VALUES (?,?,?,?,?)',
                 (account_key, event_type, project_id, project_title, now_sg()))


def create_project(title, description, category, style, property_type, room_count='', apartment_type='', actor='demo-designer'):
    with get_db() as conn:
        timestamp = now_sg()
        cursor = conn.execute('''INSERT INTO interior_design_project
            (title,description,category,style,property_type,room_count,apartment_type,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (title,description,category,style,property_type,room_count,apartment_type,timestamp,timestamp))
        project_id = cursor.lastrowid
        record_activity(conn, 'Created project',project_id,title,actor)
        return project_id


def save_project(project_id,title,description,category,style,property_type,room_count='',apartment_type='',actor='demo-designer'):
    with get_db() as conn:
        cursor = conn.execute('''UPDATE interior_design_project
            SET title=?,description=?,category=?,style=?,property_type=?,room_count=?,apartment_type=?,updated_at=?
            WHERE id=?''',
            (title,description,category,style,property_type,room_count,apartment_type,now_sg(),project_id))
        if cursor.rowcount:
            record_activity(conn,'Edited project',project_id,title,actor)


def toggle_featured(project_id,actor='demo-designer'):
    with get_db() as conn:
        conn.execute('UPDATE interior_design_project SET is_featured=1-is_featured,updated_at=? WHERE id=?',
                     (now_sg(),project_id))
        project = conn.execute('SELECT title,is_featured FROM interior_design_project WHERE id=?',(project_id,)).fetchone()
        if project:
            record_activity(conn,'Featured project' if project['is_featured'] else 'Unfeatured project',project_id,project['title'],actor)


def toggle_visibility(project_id,actor='demo-designer'):
    with get_db() as conn:
        conn.execute('UPDATE interior_design_project SET is_visible=1-is_visible,updated_at=? WHERE id=?',
                     (now_sg(),project_id))
        project = conn.execute('SELECT title,is_visible FROM interior_design_project WHERE id=?',(project_id,)).fetchone()
        if project:
            record_activity(conn,'Unhid project' if project['is_visible'] else 'Hid project',project_id,project['title'],actor)


def get_photos(project_id):
    with get_db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM project_photo WHERE project_id=? ORDER BY id',(project_id,))]


def get_photo(photo_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM project_photo WHERE id=?',(photo_id,)).fetchone()
        return dict(row) if row else None


def add_photo(project_id,image_url,photo_type):
    with get_db() as conn:
        conn.execute('INSERT INTO project_photo (project_id,image_url,photo_type) VALUES (?,?,?)',
                     (project_id,image_url,photo_type))
        project = conn.execute('SELECT title FROM interior_design_project WHERE id=?',(project_id,)).fetchone()
        if project:
            record_activity(conn,'Added photo',project_id,project['title'])


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
