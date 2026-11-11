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
