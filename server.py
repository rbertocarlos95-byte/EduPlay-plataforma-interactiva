from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import hashlib
import hmac
import json
import secrets
import sqlite3
import urllib.parse
import uuid
ROOT = Path(__file__).parent
DB = ROOT / 'eduplay.db'
QUESTIONS = {'Palabras': [{'q': '¿Cuál palabra rima con «casa»?',
               'opts': ['Taza', 'Perro', 'Sol'],
               'answer': 0,
               'hint': 'Piensa en algo donde tomas café.'},
              {'q': 'Completa: «El ___ brilla de noche».',
               'opts': ['Luna', 'Mesa', 'Libro'],
               'answer': 0,
               'hint': 'Está en el cielo y acompaña a las estrellas.'},
              {'q': '¿Cuál es el plural de «flor»?',
               'opts': ['Flores', 'Flors', 'Floros'],
               'answer': 0,
               'hint': 'Agregamos «es» al final.'},
              {'q': '¿Cuál palabra empieza con la misma letra que «mariposa»?',
               'opts': ['Montaña', 'Sol', 'Árbol'],
               'answer': 0,
               'hint': 'Busca otra palabra que comience con M.'}],
 'Ciencia': [{'q': '¿Qué necesitan las plantas para crecer?',
              'opts': ['Agua y luz', 'Solo música', 'Hielo y sombra'],
              'answer': 0,
              'hint': 'Piensa en lo que reciben del sol y la lluvia.'},
             {'q': '¿En qué planeta vivimos?',
              'opts': ['Tierra', 'Marte', 'Saturno'],
              'answer': 0,
              'hint': 'Es nuestro hogar azul.'},
             {'q': '¿Qué órgano usamos para respirar?',
              'opts': ['Pulmones', 'Estómago', 'Rodillas'],
              'answer': 0,
              'hint': 'Se llenan de aire cuando inhalamos.'},
             {'q': '¿Qué animal es un mamífero?',
              'opts': ['Delfín', 'Tortuga', 'Mariposa'],
              'answer': 0,
              'hint': 'Este animal alimenta a sus crías con leche.'}],
 'Matemáticas': [{'q': '¿Cuánto es 7 + 5?',
                  'opts': ['12', '11', '13'],
                  'answer': 0,
                  'hint': 'Cuenta cinco más después del siete.'},
                 {'q': 'Si tienes 10 manzanas y regalas 3, ¿cuántas quedan?',
                  'opts': ['7', '8', '6'],
                  'answer': 0,
                  'hint': 'Resta las que regalaste.'},
                 {'q': '¿Qué número sigue? 2, 4, 6, __',
                  'opts': ['8', '7', '9'],
                  'answer': 0,
                  'hint': 'La secuencia avanza de dos en dos.'},
                 {'q': '¿Cuánto es 3 × 4?',
                  'opts': ['12', '7', '14'],
                  'answer': 0,
                  'hint': 'Suma tres grupos de cuatro.'}]}

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS players(id TEXT PRIMARY KEY,username TEXT UNIQUE,name TEXT NOT NULL,avatar TEXT NOT NULL,password_hash TEXT,password_salt TEXT,xp INTEGER DEFAULT 0,streak INTEGER DEFAULT 0,created TEXT DEFAULT CURRENT_TIMESTAMP)')
    cols = {r['name'] for r in c.execute('PRAGMA table_info(players)').fetchall()}
    for name, kind in [('username', 'TEXT'), ('password_hash', 'TEXT'), ('password_salt', 'TEXT')]:
        if name not in cols:
            c.execute(f'ALTER TABLE players ADD COLUMN {name} {kind}')
    c.execute('CREATE TABLE IF NOT EXISTS answers(id INTEGER PRIMARY KEY,player_id TEXT,subject TEXT,correct INTEGER,created TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(player_id) REFERENCES players(id))')
    c.execute('CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,player_id TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(player_id) REFERENCES players(id))')
    c.commit()
    return c

def new_session(c, pid):
    token = secrets.token_urlsafe(32)
    c.execute('INSERT INTO sessions(token,player_id) VALUES(?,?)', (token, pid))
    return token

class Handler(SimpleHTTPRequestHandler):

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass

    def send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        return json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')

    def do_POST(self):
        try:
            data = self.body()
        except Exception:
            return self.send_json({'error': 'JSON inválido'}, 400)
        c = connect()
        if self.path == '/api/register':
            name = ' '.join(str(data.get('name', '')).split())[:18]
            username = ''.join(str(data.get('username', '')).lower().split())[:24]
            password = str(data.get('password', ''))
            avatar = str(data.get('avatar', '🐉'))[:8]
            if len(name) < 2 or len(username) < 3 or len(password) < 8:
                c.close()
                return self.send_json({'error': 'Usa un nombre de 2 letras, usuario de 3 y contraseña de 8 caracteres.'}, 400)
            if not all((ch.isalnum() or ch in '._-' for ch in username)):
                c.close()
                return self.send_json({'error': 'El usuario solo puede tener letras, números, punto, guion o guion bajo.'}, 400)
            salt = secrets.token_bytes(16)
            digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310000).hex()
            pid = uuid.uuid4().hex
            try:
                c.execute('INSERT INTO players(id,username,name,avatar,password_hash,password_salt) VALUES(?,?,?,?,?,?)', (pid, username, name, avatar, digest, salt.hex()))
                token = new_session(c, pid)
                c.commit()
            except sqlite3.IntegrityError:
                c.close()
                return self.send_json({'error': 'Ese nombre de usuario ya está en uso.'}, 409)
            result = self.state(c, pid)
            result['token'] = token
            c.close()
            return self.send_json(result, 201)
        if self.path == '/api/login':
            username = ''.join(str(data.get('username', '')).lower().split())[:24]
            password = str(data.get('password', ''))
            p = c.execute('SELECT * FROM players WHERE username=?', (username,)).fetchone()
            if not p or not p['password_hash'] or (not hmac.compare_digest(hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(p['password_salt']), 310000).hex(), p['password_hash'])):
                c.close()
                return self.send_json({'error': 'Usuario o contraseña incorrectos.'}, 401)
            token = new_session(c, p['id'])
            c.commit()
            result = self.state(c, p['id'])
            result['token'] = token
            c.close()
            return self.send_json(result)
        if self.path == '/api/logout':
            c.execute('DELETE FROM sessions WHERE token=?', (str(data.get('token', '')),))
            c.commit()
            c.close()
            return self.send_json({'ok': True})
        if self.path == '/api/answer':
            token = str(data.get('token', ''))
            session = c.execute('SELECT player_id FROM sessions WHERE token=?', (token,)).fetchone()
            subject = str(data.get('subject', ''))
            qi = int(data.get('question', -1))
            choice = int(data.get('choice', -1))
            qs = QUESTIONS.get(subject, [])
            if not session:
                c.close()
                return self.send_json({'error': 'Inicia sesión para guardar tu avance.'}, 401)
            if not qs or not 0 <= qi < len(qs) or (not 0 <= choice < 3):
                c.close()
                return self.send_json({'error': 'Respuesta no válida'}, 400)
            q = qs[qi]
            correct = choice == q['answer']
            pid = session['player_id']
            xp = 10 if correct else 2
            c.execute('INSERT INTO answers(player_id,subject,correct) VALUES(?,?,?)', (pid, subject, int(correct)))
            c.execute('UPDATE players SET xp=xp+?,streak=streak+? WHERE id=?', (xp, int(correct), pid))
            c.commit()
            result = {'correct': correct, 'xpEarned': xp, 'hint': None if correct else q['hint'], 'state': self.state(c, pid)}
            c.close()
            return self.send_json(result)
        c.close()
        self.send_json({'error': 'Ruta no encontrada'}, 404)

    def do_GET(self):
        if self.path.startswith('/api/state?'):
            token = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('token', [''])[0]
            c = connect()
            session = c.execute('SELECT player_id FROM sessions WHERE token=?', (token,)).fetchone()
            if not session:
                c.close()
                return self.send_json({'error': 'Sesión vencida'}, 401)
            result = self.state(c, session['player_id'])
            c.close()
            return self.send_json(result)
        if self.path == '/api/questions':
            return self.send_json(QUESTIONS)
        return super().do_GET()

    @staticmethod
    def state(c, pid):
        p = c.execute('SELECT * FROM players WHERE id=?', (pid,)).fetchone()
        if not p:
            return None
        totals = c.execute('SELECT COUNT(*) total,SUM(correct) correct FROM answers WHERE player_id=?', (pid,)).fetchone()
        subjects = c.execute('SELECT subject,COUNT(*) total,SUM(correct) correct FROM answers WHERE player_id=? GROUP BY subject', (pid,)).fetchall()
        daily = c.execute("SELECT COUNT(*) FROM answers WHERE player_id=? AND date(created,'localtime')=date('now','localtime')", (pid,)).fetchone()[0]
        xp = p['xp']
        badges = []
        for limit, title, icon in [(1, 'Primer paso', '🌱'), (5, 'Mente curiosa', '🔎'), (10, 'Estrella brillante', '⭐'), (25, 'Gran explorador', '🚀'), (50, 'Leyenda EduPlay', '🏆')]:
            if totals['total'] >= limit:
                badges.append({'title': title, 'icon': icon})
        return {'id': p['id'], 'username': p['username'], 'name': p['name'], 'avatar': p['avatar'], 'xp': xp, 'level': xp // 50 + 1, 'levelProgress': xp % 50, 'streak': p['streak'], 'answered': totals['total'] or 0, 'correct': totals['correct'] or 0, 'daily': daily, 'badges': badges, 'subjects': {r['subject']: {'total': r['total'], 'correct': r['correct']} for r in subjects}}
if __name__ == '__main__':
    connect().close()
    print('EduPlay listo en http://localhost:8000')
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()