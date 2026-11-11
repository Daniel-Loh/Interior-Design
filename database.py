"""Local SQLite persistence for the Pending demo (no online database required)."""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash, check_password_hash

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
                name TEXT DEFAULT '', description TEXT DEFAULT '', contact_info TEXT DEFAULT ''
            );
            INSERT OR IGNORE INTO company_profile (id) VALUES (1);

            CREATE TABLE IF NOT EXISTS interior_design_project (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, description TEXT DEFAULT '',
                is_featured INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1,
                category TEXT DEFAULT '', style TEXT DEFAULT '', property_type TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS project_photo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL, image_url TEXT NOT NULL,
                photo_type TEXT NOT NULL CHECK(photo_type IN ('BEFORE', 'AFTER')),
                FOREIGN KEY(project_id) REFERENCES interior_design_project(id)
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
        for column in ('created_at', 'updated_at'):
            if column not in existing:
                conn.execute(f"ALTER TABLE interior_design_project ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
        if 'account_key' not in existing:
            conn.execute("ALTER TABLE interior_design_project ADD COLUMN account_key TEXT NOT NULL DEFAULT ''")
        count = conn.execute('SELECT COUNT(*) AS n FROM interior_design_project').fetchone()['n']
        if count == 0:
            _seed_demo_projects(conn)


def _seed_demo_projects(conn):
    """Only on an empty database. These are clearly sample listings, not real projects."""
    samples = [
        ('Warm Scandinavian 4-Room Home', 'Demo project: light oak, soft tones and practical family storage.', 'Residential','Scandinavian','HDB 4-Room','4 room','Standard apartment'),
        ('Minimalist City Penthouse', 'Demo project: airy spaces with clean lines and warm stone textures.', 'Residential','Minimalist','Condominium','5 room','Penthouse'),
        ('Modern Duplex Living', 'Demo project: double-height living area and a modern open-plan kitchen.', 'Residential','Modern','Condominium','4 room','Duplex'),
        ('Calm Studio Apartment', 'Demo project: multi-use furniture for compact, flexible living.', 'Residential','Minimalist','Condominium','3 room','Studio apartment'),
        ('Industrial Family Home', 'Demo project: textured concrete, steel accents and family-friendly finishes.', 'Residential','Industrial','HDB 5-Room','5 room','Standard apartment'),
        ('Contemporary Four-Room Flat', 'Demo project: refined neutrals, feature lighting and adaptable storage.', 'Residential','Contemporary','HDB 4-Room','4 room','Standard apartment'),
        ('Modern Penthouse Retreat', 'Demo project: panoramic views, dark timber and soft contemporary detailing.', 'Residential','Modern','Condominium','5 room','Penthouse'),
        ('Scandinavian Duplex Hideaway', 'Demo project: bright timber details across two levels.', 'Residential','Scandinavian','Condominium','4 room','Duplex'),
        ('Traditional Six-Room Residence', 'Demo project: classic finishes and generous entertaining spaces.', 'Residential','Traditional','Landed','6 room','Standard apartment'),
        ('Eclectic Three-Room Makeover', 'Demo project: cheerful accents and clever compact-space storage.', 'Residential','Eclectic','HDB 3-Room','3 room','Standard apartment'),
    ]
    date = now_sg()
    conn.executemany('''
        INSERT INTO interior_design_project
        (title,description,category,style,property_type,room_count,apartment_type,created_at,updated_at,is_featured)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', [(title, desc, category, style, prop, rooms, apartment, date, date, 1 if idx < 3 else 0) for
          idx,(title,desc,category,style,prop,rooms,apartment) in enumerate(samples)])


def get_company():
    with get_db() as conn:
        row = conn.execute('SELECT * FROM company_profile WHERE id=1').fetchone()
        return dict(row) if row else {}


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
        for field in TAG_FIELDS:
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
            (title,description,category,style,property_type,room_count,apartment_type,created_at,updated_at,account_key)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (title,description,category,style,property_type,room_count,apartment_type,timestamp,timestamp,actor))
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
        return project['is_featured'] if project else None


def toggle_visibility(project_id,actor='demo-designer'):
    with get_db() as conn:
        conn.execute('UPDATE interior_design_project SET is_visible=1-is_visible,updated_at=? WHERE id=?',
                     (now_sg(),project_id))
        project = conn.execute('SELECT title,is_visible FROM interior_design_project WHERE id=?',(project_id,)).fetchone()
        if project:
            record_activity(conn,'Unhid project' if project['is_visible'] else 'Hid project',project_id,project['title'],actor)
        return project['is_visible'] if project else None


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
    with get_db() as conn:
        photo = conn.execute('SELECT * FROM project_photo WHERE id=?',(photo_id,)).fetchone()
        if photo:
            conn.execute('DELETE FROM project_photo WHERE id=?',(photo_id,))
            project = conn.execute('SELECT title FROM interior_design_project WHERE id=?',(photo['project_id'],)).fetchone()
            if project:
                record_activity(conn,'Removed photo',photo['project_id'],project['title'])


def register_demo_login(account_key,email,role):
    timestamp = now_sg()
    with get_db() as conn:
        conn.execute('''INSERT INTO demo_users (account_key,email,role,created_at,last_login_at,login_count)
            VALUES (?,?,?,?,?,1)
            ON CONFLICT(account_key) DO UPDATE SET last_login_at=excluded.last_login_at, login_count=login_count+1''',
            (account_key,email,role,timestamp,timestamp))


def get_favorite_ids(account_key):
    with get_db() as conn:
        return {row['project_id'] for row in conn.execute('SELECT project_id FROM favorite_project WHERE account_key=?',(account_key,))}


def toggle_favorite(account_key,project_id):
    """Only visible projects may be favorited; returns True if saved, False if removed."""
    with get_db() as conn:
        project = conn.execute('SELECT is_visible FROM interior_design_project WHERE id=?',(project_id,)).fetchone()
        if not project or not project['is_visible']:
            raise ValueError('Project not available')
        saved = conn.execute('SELECT 1 FROM favorite_project WHERE account_key=? AND project_id=?',(account_key,project_id)).fetchone()
        if saved:
            conn.execute('DELETE FROM favorite_project WHERE account_key=? AND project_id=?',(account_key,project_id))
            return False
        conn.execute('INSERT INTO favorite_project (account_key,project_id,saved_at) VALUES (?,?,?)',
                     (account_key,project_id,now_sg()))
        return True


def get_favorite_projects(account_key):
    with get_db() as conn:
        return [dict(r) for r in conn.execute('''SELECT p.* FROM interior_design_project p
            JOIN favorite_project f ON f.project_id=p.id
            WHERE f.account_key=? AND p.is_visible=1 ORDER BY f.saved_at DESC,p.id DESC''',(account_key,))]


def get_project_stats():
    with get_db() as conn:
        row = conn.execute('''SELECT COUNT(*) total, COALESCE(SUM(is_visible),0) visible,
            COALESCE(SUM(1-is_visible),0) hidden,COALESCE(SUM(is_featured),0) featured
            FROM interior_design_project''').fetchone()
        photos = conn.execute('SELECT COUNT(*) photos FROM project_photo').fetchone()['photos']
        favorites = conn.execute('SELECT COUNT(*) n FROM favorite_project').fetchone()['n']
        breakdown = {}
        for field in TAG_FIELDS:
            breakdown[field] = [{'label': r['value'] or 'Unspecified', 'count': r['amount']}
                  for r in conn.execute(f'''SELECT {field} AS value,COUNT(*) AS amount
                      FROM interior_design_project GROUP BY {field} ORDER BY amount DESC,value''')]
        return {**dict(row), 'photos':photos,'favorites':favorites,'breakdown':breakdown}


def get_user_stats(start, end):
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) FROM demo_users').fetchone()[0]
        recent = conn.execute('SELECT COUNT(*) FROM demo_users WHERE created_at>=? AND created_at<?',(start,end)).fetchone()[0]
        roles = {r['role']: r['n'] for r in conn.execute('SELECT role,COUNT(*) AS n FROM demo_users GROUP BY role')}
        return {'total':total,'new_in_period':recent,'roles':{role:roles.get(role,0) for role in ('customer','designer','platform_manager')}}


def get_designer_activity(start,end):
    with get_db() as conn:
        events = [dict(r) for r in conn.execute('''SELECT account_key,event_type,project_title,occurred_at FROM designer_activity
            WHERE occurred_at>=? AND occurred_at<? ORDER BY occurred_at DESC,id DESC''',(start,end))]
        counts = {}
        actors = {}
        for event in events:
            key = event['event_type']
            counts[key] = counts.get(key,0) + 1
            actor = event['account_key']
            actors[actor] = actors.get(actor,0) + 1
        return {'total':len(events),'counts':counts,'actors':actors,'events':events}


# --- Users (real auth, separate from demo_users) ---

def create_user(email, password, role):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
            (email, generate_password_hash(password), role)
        )


def get_user_by_email(email):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        return dict(row) if row else None


def verify_user(email, password):
    """Return user dict on success, None on failure."""
    user = get_user_by_email(email)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None


def get_all_users():
    with get_db() as conn:
        return [dict(r) for r in conn.execute('SELECT id, email, role, created_at FROM users ORDER BY id')]


def update_user_role(user_id, role):
    with get_db() as conn:
        conn.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))


def delete_user(user_id):
    with get_db() as conn:
        conn.execute('DELETE FROM users WHERE id=?', (user_id,))


# --- Tags ---

def get_project_tags(project_id):
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT t.id, t.name FROM tags t
               JOIN project_tags pt ON pt.tag_id = t.id
               WHERE pt.project_id=? ORDER BY t.name''',
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def set_project_tags(project_id, tag_names):
    """Replace all tags on a project with the given list of tag name strings."""
    with get_db() as conn:
        conn.execute('DELETE FROM project_tags WHERE project_id=?', (project_id,))
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            row = conn.execute('SELECT id FROM tags WHERE name=?', (name,)).fetchone()
            tag_id = row['id'] if row else conn.execute('INSERT INTO tags (name) VALUES (?)', (name,)).lastrowid
            conn.execute('INSERT OR IGNORE INTO project_tags (project_id, tag_id) VALUES (?,?)', (project_id, tag_id))


def get_all_tags():
    with get_db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM tags ORDER BY name')]


# ─── Service classes (OOP interface over the data layer above) ─────────────

class CompanyService:
    """Manages the single company profile record."""

    def get(self):                  # implements CompanyProfile methods
        return get_company()        # getPublicProfile()

    def save(self, name, description, contact_info):
        return save_company(name, description, contact_info)


class ProjectService:
    """CRUD and state management for interior design projects."""

    def get(self, project_id):
        return get_project(project_id)

    def get_all(self):
        return get_all_projects()

    def get_visible(self, filters=None):
        return get_visible_projects(filters)

    def get_similar(self, tags, excluded_ids=None, limit=4):
        return get_similar_projects(tags, excluded_ids, limit)

    def get_filter_options(self):
        return get_filter_options()

    def get_stats(self):
        return get_project_stats()

    def create(self, title, description, category, style, property_type,
               room_count='', apartment_type='', actor='demo-designer'):
        return create_project(title, description, category, style, property_type,
                              room_count, apartment_type, actor)

    def save(self, project_id, title, description, category, style, property_type,
             room_count='', apartment_type='', actor='demo-designer'):
        return save_project(project_id, title, description, category, style,
                            property_type, room_count, apartment_type, actor)

    def toggle_featured(self, project_id, actor='demo-designer'):
        return toggle_featured(project_id, actor)

    def toggle_visibility(self, project_id, actor='demo-designer'):
        return toggle_visibility(project_id, actor)


class PhotoService:
    """Manages before/after photos attached to a project."""

    def get_all(self, project_id):
        return get_photos(project_id)

    def get(self, photo_id):
        return get_photo(photo_id)

    def add(self, project_id, image_url, photo_type):
        return add_photo(project_id, image_url, photo_type)

    def delete(self, photo_id):
        return delete_photo(photo_id)


class UserService:
    """User account creation, lookup and authentication."""

    def create(self, email, password, role):
        return create_user(email, password, role)

    def get_by_email(self, email):
        return get_user_by_email(email)

    def get_by_id(self, user_id):
        return get_user_by_id(user_id)

    def verify(self, email, password):
        return verify_user(email, password)

    def get_all(self):
        return get_all_users()

    def update_role(self, user_id, role):
        return update_user_role(user_id, role)

    def delete(self, user_id):
        return delete_user(user_id)
