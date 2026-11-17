#!/usr/bin/env python3
"""Wasl node. One file, Python standard library only, runs offline.

  python3 wasl.py --role truck  --port 8080                      # Raspberry Pi in the water truck
  python3 wasl.py --role clinic --port 8081 --peers http://10.42.0.1:8080   # laptop in town

A node stores bundles (messages) and events (receipts), and syncs with whoever it meets.
Phones are browsers talking to the truck; the clinic is a peer daemon that polls the truck.
"""
import argparse, hashlib, json, os, random, socket, sqlite3, threading, time
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, 'web')

SCHEMA = """
PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS bundles(id TEXT PRIMARY KEY, src TEXT, src_name TEXT, camp TEXT, dst TEXT, kind TEXT,
  pri INTEGER, created REAL, re TEXT, body TEXT, blob_size INTEGER DEFAULT 0, blob_have INTEGER DEFAULT 0,
  blob BLOB, complete INTEGER DEFAULT 1, purged INTEGER DEFAULT 0, received REAL);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, bundle TEXT, node TEXT, node_name TEXT, role TEXT,
  type TEXT, t REAL, extra TEXT);
CREATE TABLE IF NOT EXISTS contacts(id INTEGER PRIMARY KEY AUTOINCREMENT, peer TEXT, peer_name TEXT, role TEXT,
  camp TEXT, t0 REAL, t1 REAL, n_in INTEGER DEFAULT 0, n_out INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY AUTOINCREMENT, camp TEXT, minutes REAL, seeded INTEGER);
CREATE TABLE IF NOT EXISTS visits(id INTEGER PRIMARY KEY AUTOINCREMENT, camp TEXT, t REAL, seeded INTEGER);
"""


def quantile(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    i = p * (len(xs) - 1)
    lo = int(i)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


class Store:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def q(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def x(self, sql, args=()):
        with self.lock:
            self.db.execute(sql, args)


class Node:
    def __init__(self, a):
        self.role = a.role
        self.world = json.load(open(os.path.join(ROOT, 'world.json'), encoding='utf-8'))
        self.id = a.id or ('clinic' if a.role == 'clinic' else self.world['truck']['id'])
        self.name = a.name or (self.world['town']['name'] if a.role == 'clinic' else self.world['truck']['name'])
        self.peers = [p.strip().rstrip('/') for p in (a.peers or '').split(',') if p.strip()]
        self.peer_status = {}
        self.store = Store(a.db)
        self.position = 'free'    # free | camp | road | town   (range emulation for single-room demos)
        self.quality = 'strong'   # strong | weak
        self.offset = 0.0         # the Pi has no clock battery: it learns the time from phones it meets
        if self.role == 'truck' and not self.store.q('SELECT 1 FROM trips LIMIT 1'):
            self.seed()

    # ---------- time, identity ----------
    def now(self):
        return time.time() + self.offset

    def info(self):
        return {'id': self.id, 'name': self.name, 'role': self.role}

    # ---------- simulated history the forecast learns from ----------
    def seed(self):
        s, now = self.store, self.now()
        with s.lock:
            s.x('BEGIN')
            s.x('DELETE FROM trips WHERE seeded=1')
            s.x('DELETE FROM visits WHERE seeded=1')
            for c in self.world['camps']:
                rng = random.Random(c['id'])
                for _ in range(40):                       # 40 past trips camp -> town, with the odd sandstorm
                    m = c['leg_min'] * rng.lognormvariate(0, 0.16)
                    if rng.random() < 0.08:
                        m += rng.uniform(60, 240)
                    s.x('INSERT INTO trips(camp,minutes,seeded) VALUES(?,?,1)', (c['id'], m))
                gaps = [84 * rng.lognormvariate(0, 0.14) for _ in range(26)]   # hours between visits (~3.5 days)
                t = now - (quantile(gaps, .5) - rng.uniform(3.5, 6.5)) * 3600
                for g in gaps:
                    s.x('INSERT INTO visits(camp,t,seeded) VALUES(?,?,1)', (c['id'], t))
                    t -= g * 3600
            s.x('COMMIT')

    def forecast(self, camp):
        trips = [r['minutes'] for r in self.store.q('SELECT minutes FROM trips WHERE camp=?', (camp,))]
        vis = [r['t'] for r in self.store.q('SELECT t FROM visits WHERE camp=? ORDER BY t', (camp,))]
        gaps = [(b - a) / 3600 for a, b in zip(vis, vis[1:]) if b - a >= 6 * 3600]
        return {'camp': camp, 'trip_p50': quantile(trips, .5), 'trip_p90': quantile(trips, .9), 'trips_n': len(trips),
                'gap_p50': quantile(gaps, .5), 'gap_p90': quantile(gaps, .9), 'visits_n': len(vis),
                'last_visit': vis[-1] if vis else None}

    # ---------- range / link emulation ----------
    def gate(self, role):
        up = True
        if self.position == 'road':
            up = False
        elif self.position == 'camp':
            up = role == 'phone'
        elif self.position == 'town':
            up = role != 'phone'
        if not up:
            return 'down'
        return 'weak' if self.quality == 'weak' else 'up'

    # ---------- bundles and events ----------
    def bjson(self, r):
        return {'id': r['id'], 'src': r['src'], 'src_name': r['src_name'], 'camp': r['camp'], 'dst': r['dst'],
                'kind': r['kind'], 'pri': r['pri'], 'created': r['created'], 're': r['re'],
                'body': json.loads(r['body'] or '{}'), 'blob_size': r['blob_size'] or 0}

    def ejson(self, r):
        return {'id': r['id'], 'bundle': r['bundle'], 'node': r['node'], 'node_name': r['node_name'],
                'role': r['role'], 'type': r['type'], 't': r['t'], 'extra': json.loads(r['extra']) if r['extra'] else None}

    def get_bundle(self, bid):
        r = self.store.q('SELECT * FROM bundles WHERE id=?', (bid,))
        return self.bjson(r[0]) if r else None

    def add_event(self, e):
        if not e or not e.get('id') or not e.get('bundle'):
            return False
        s = self.store
        with s.lock:
            if s.q('SELECT 1 FROM events WHERE id=?', (e['id'],)):
                return False
            s.x('INSERT INTO events VALUES(?,?,?,?,?,?,?,?)',
                (e['id'], e['bundle'], e.get('node'), e.get('node_name'), e.get('role'), e.get('type'), e.get('t'),
                 json.dumps(e['extra']) if e.get('extra') else None))
            if e.get('type') == 'delivered' and self.role == 'truck':
                b = s.q('SELECT dst,camp FROM bundles WHERE id=?', (e['bundle'],))
                if b and b[0]['dst'] != '*':
                    # the destination has it: free the hold, and learn from the trip
                    s.x('UPDATE bundles SET blob=NULL, purged=1 WHERE id=?', (e['bundle'],))
                    c = s.q('SELECT t FROM events WHERE id=?', ('%s.%s.custody' % (e['bundle'], self.id),))
                    if c and b[0]['dst'] == 'clinic' and b[0]['camp'] and e['t'] - c[0]['t'] >= 600:
                        s.x('INSERT INTO trips(camp,minutes,seeded) VALUES(?,?,0)', (b[0]['camp'], (e['t'] - c[0]['t']) / 60))
        return True

    def make_event(self, bid, typ, extra=None):
        e = {'id': '%s.%s.%s' % (bid, self.id, typ), 'bundle': bid, 'node': self.id, 'node_name': self.name,
             'role': self.role, 'type': typ, 't': self.now(), 'extra': extra}
        self.add_event(e)
        return e

    def accept_bundle(self, b):
        """Store a bundle we were handed. Returns the receipts (events) this creates."""
        s = self.store
        with s.lock:
            if s.q('SELECT 1 FROM bundles WHERE id=?', (b['id'],)):
                return []
            size = int(b.get('blob_size') or 0)
            s.x('INSERT INTO bundles(id,src,src_name,camp,dst,kind,pri,created,re,body,blob_size,complete,received) '
                'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (b['id'], b.get('src'), b.get('src_name'), b.get('camp'), b.get('dst'), b.get('kind'),
                 int(b.get('pri', 3)), b.get('created'), b.get('re'), json.dumps(b.get('body') or {}), size,
                 0 if size else 1, self.now()))
        return [] if size else self.on_complete(b)

    def on_complete(self, b):
        now = self.now()
        if self.role == 'truck':
            extra = None
            if b.get('camp'):
                f = self.forecast(b['camp'])
                if b.get('dst') == 'clinic' and f['trip_p50']:
                    extra = {'to': 'clinic', 'eta50': now + f['trip_p50'] * 60, 'eta90': now + f['trip_p90'] * 60,
                             'n': f['trips_n']}
                    if self.store.q("SELECT 1 FROM bundles WHERE kind='alert' AND body LIKE '%storm%' AND created>?",
                                    (now - 86400,)):
                        # a sandstorm warning is on board and the trip history has no storm in it: promise less
                        extra.update(eta50=now + f['trip_p50'] * 90, eta90=now + f['trip_p90'] * 150, storm=True)
                elif f['gap_p50'] and f['last_visit']:
                    extra = {'to': 'camp', 'eta50': f['last_visit'] + f['gap_p50'] * 3600,
                             'eta90': f['last_visit'] + f['gap_p90'] * 3600, 'n': f['visits_n']}
            return [self.make_event(b['id'], 'custody', extra)]
        if self.role == 'clinic' and b.get('dst') in ('clinic', self.id) and b.get('src') != self.id:
            return [self.make_event(b['id'], 'delivered')]
        return []

    def blob_put(self, bid, offset, data):
        s = self.store
        with s.lock:
            r = s.q('SELECT blob,blob_have,blob_size,complete FROM bundles WHERE id=?', (bid,))
            if not r:
                return {'have': 0, 'error': 'unknown'}
            r = r[0]
            if r['complete']:
                return {'have': r['blob_size']}
            if offset != r['blob_have']:
                return {'have': r['blob_have']}
            blob = (r['blob'] or b'') + data
            done = len(blob) >= r['blob_size']
            s.x('UPDATE bundles SET blob=?, blob_have=?, complete=? WHERE id=?', (blob, len(blob), 1 if done else 0, bid))
        return {'have': len(blob), 'events': self.on_complete(self.get_bundle(bid)) if done else []}

    def compose(self, d):
        created = self.now()
        body = d.get('body') or {}
        bid = hashlib.sha256(('%s|%s|%s' % (self.id, created, json.dumps(body))).encode()).hexdigest()[:16]
        b = {'id': bid, 'src': self.id, 'src_name': self.name, 'camp': d.get('camp'), 'dst': d.get('dst'),
             'kind': d.get('kind', 'msg'), 'pri': int(d.get('pri', 2)), 'created': created, 're': d.get('re'),
             'body': body, 'blob_size': 0}
        self.accept_bundle(b)
        return b

    # ---------- contacts ----------
    def touch(self, peer, visit=True, n_in=0, n_out=0):
        pid = peer.get('id')
        if not pid:
            return
        s, now = self.store, self.now()
        with s.lock:
            r = s.q('SELECT id FROM contacts WHERE peer=? AND t1>? ORDER BY id DESC LIMIT 1', (pid, now - 15))
            if r:
                s.x('UPDATE contacts SET t1=?, n_in=n_in+?, n_out=n_out+? WHERE id=?', (now, n_in, n_out, r[0]['id']))
                return
            s.x('INSERT INTO contacts(peer,peer_name,role,camp,t0,t1,n_in,n_out) VALUES(?,?,?,?,?,?,?,?)',
                (pid, peer.get('name'), peer.get('role'), peer.get('camp'), now, now, n_in, n_out))
            # a new contact with a camp phone is a visit to that camp
            if visit and self.role == 'truck' and peer.get('role') == 'phone' and peer.get('camp'):
                last = s.q('SELECT MAX(t) m FROM visits WHERE camp=? AND seeded=0', (peer['camp'],))[0]['m']
                if not last or now - last > 600:
                    s.x('INSERT INTO visits(camp,t,seeded) VALUES(?,?,0)', (peer['camp'], now))

    # ---------- sync, server side ----------
    def carries(self, h, peer):
        if h.get('dst') == peer.get('id'):
            return False                      # already at its destination
        if self.role == 'truck':
            return True                       # the mule carries everything
        return h.get('dst') in ('clinic', self.id, '*')

    def offers(self, r, peer):
        if r['src'] == peer.get('id'):
            return False
        role = peer.get('role')
        if role == 'phone':
            return r['dst'] in (peer.get('id'), '*')
        if role == 'clinic':
            return r['dst'] in ('clinic', peer.get('id'))
        return r['dst'] != self.id

    def sync(self, req):
        peer = req.get('node') or {}
        if self.role == 'truck' and req.get('time') and abs(req['time'] - self.now()) > 30:
            big = abs(req['time'] - self.now()) > 3600
            self.offset = req['time'] - time.time()
            if big:
                self.seed()
        for e in req.get('events') or []:
            self.add_event(e)
        have = {h['id']: h for h in req.get('have') or []}
        mine = {r['id']: r['complete'] for r in self.store.q('SELECT id,complete FROM bundles')}
        want = [h['id'] for h in sorted(have.values(), key=lambda h: (h.get('pri', 9), h.get('created', 0)))
                if not mine.get(h['id']) and self.carries(h, peer)]
        offer = [self.bjson(r) for r in
                 self.store.q('SELECT * FROM bundles WHERE complete=1 AND purged=0 ORDER BY pri, created')
                 if r['id'] not in have and self.offers(r, peer)]
        ids = set(have) | {b['id'] for b in offer}
        evh = set(req.get('ev_have') or [])
        evs = [self.ejson(r) for r in self.store.q('SELECT * FROM events') if r['bundle'] in ids and r['id'] not in evh]
        self.touch(peer, visit=not req.get('fresh'), n_out=len(offer))
        out = {'node': self.info(), 'time': self.now(), 'want': want, 'bundles': offer, 'events': evs}
        if self.role == 'truck' and peer.get('camp'):
            out['forecast'] = self.forecast(peer['camp'])
        return out

    def receive(self, req):
        evs = []
        for b in req.get('bundles') or []:
            evs += self.accept_bundle(b)
        self.touch(req.get('node') or {}, n_in=len(req.get('bundles') or []))
        return {'events': evs}

    # ---------- sync, client side (clinic daemon -> truck) ----------
    def http(self, url, data=None, timeout=2.5):
        headers = {'X-Wasl-Role': self.role, 'X-Wasl-Node': self.id}
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(url, data=body, headers=headers, method='POST' if body is not None else 'GET')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()

    def sync_with(self, base):
        hello = json.loads(self.http(base + '/api/hello', timeout=1.5))
        self.peer_status[base] = {'ok': True, 't': self.now(), 'name': hello.get('name'), 'id': hello.get('id'),
                                  'link': hello.get('link')}
        s = self.store
        have = [dict(r) for r in s.q('SELECT id,dst,pri,created FROM bundles WHERE complete=1')]
        res = json.loads(self.http(base + '/api/sync', {
            'node': self.info(), 'time': self.now(), 'have': have,
            'ev_have': [r['id'] for r in s.q('SELECT id FROM events')],
            'events': [self.ejson(r) for r in s.q('SELECT * FROM events ORDER BY t DESC LIMIT 500')]}))
        n_in = 0
        for b in res.get('bundles') or []:
            if not s.q('SELECT 1 FROM bundles WHERE id=?', (b['id'],)):
                n_in += 1
            self.accept_bundle(b)
        for e in res.get('events') or []:
            self.add_event(e)
        n_out = 0
        for bid in res.get('want') or []:
            b = self.get_bundle(bid)
            if not b:
                continue
            r = json.loads(self.http(base + '/api/bundles', {'node': self.info(), 'bundles': [b]}))
            for e in r.get('events') or []:
                self.add_event(e)
            n_out += 1
        self.touch(hello, n_in=n_in, n_out=n_out)
        # pull attachments, resuming from wherever the last contact stopped
        for r in s.q('SELECT id,blob_have,blob_size FROM bundles WHERE complete=0'):
            have_b = r['blob_have']
            while have_b < r['blob_size']:
                data = self.http('%s/api/blob/%s?offset=%d&len=16384' % (base, r['id'], have_b), timeout=6)
                if not data:
                    break
                have_b = self.blob_put(r['id'], have_b, data)['have']

    def peer_loop(self):
        while True:
            for base in self.peers:
                try:
                    self.sync_with(base)
                except Exception:
                    st = self.peer_status.setdefault(base, {'t': None, 'name': None})
                    st['ok'] = False
            time.sleep(1.2)

    # ---------- state for the dashboards ----------
    def state(self):
        s = self.store
        evs = {}
        for r in s.q('SELECT * FROM events ORDER BY t'):
            evs.setdefault(r['bundle'], []).append(self.ejson(r))
        bundles = []
        for r in s.q('SELECT * FROM bundles ORDER BY created DESC LIMIT 400'):
            b = self.bjson(r)
            b.update(complete=r['complete'], purged=r['purged'], blob_have=r['blob_have'], received=r['received'],
                     events=evs.get(r['id'], []))
            bundles.append(b)
        hold = [b for b in bundles if b['complete'] and not b['purged'] and b['dst'] != self.id]
        out = {'node': self.info(), 'time': self.now(), 'position': self.position, 'quality': self.quality,
               'peers': self.peer_status, 'bundles': bundles,
               'contacts': [dict(r) for r in s.q('SELECT * FROM contacts ORDER BY id DESC LIMIT 14')],
               'hold': {'n': len(hold), 'bytes': sum(len(json.dumps(b['body'])) + 96 + b['blob_size'] for b in hold)},
               'clock_learned': bool(self.offset)}
        if self.role == 'truck':
            out['forecast'] = {c['id']: self.forecast(c['id']) for c in self.world['camps']}
        return out

    def reset(self):
        s = self.store
        with s.lock:
            for t in ('bundles', 'events', 'contacts', 'trips', 'visits'):
                s.x('DELETE FROM ' + t)
        if self.role == 'truck':
            self.seed()
        self.position, self.quality = 'free', 'strong'


N = None
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
         '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png'}
PAGES = {'/app': 'app.html', '/clinic': 'clinic.html', '/truck': 'truck.html', '/sim': 'sim.html', '/stage': 'stage.html', '/pitch': 'pitch.html'}


class H(BaseHTTPRequestHandler):
    server_version = 'Wasl/1'

    def log_message(self, *a):
        pass

    def send(self, code, data, ctype='application/json'):
        if not isinstance(data, (bytes, bytearray)):
            data = json.dumps(data).encode()
        try:
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def raw(self):
        n = int(self.headers.get('Content-Length') or 0)
        return self.rfile.read(n) if n else b''

    def js(self):
        try:
            return json.loads(self.raw() or b'{}')
        except ValueError:
            return {}

    def gated(self, slow=0.0):
        """Radio-range emulation. Dashboards send no role header and are never gated."""
        role = self.headers.get('X-Wasl-Role')
        if not role:
            return 'up'
        st = N.gate(role)
        if st == 'down':
            self.send(503, {'error': 'out_of_range'})
            return None
        if st == 'weak':
            time.sleep(random.uniform(.12, .4) + slow)
            if random.random() < 0.2:
                self.send(503, {'error': 'dropped'})
                return None
        return st

    def do_GET(self):
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)
        if p == '/api/hello':
            st = self.gated()
            return st and self.send(200, dict(N.info(), time=N.now(), link=st))
        if p == '/api/state':
            return self.send(200, N.state())
        if p == '/api/world':
            return self.send(200, N.world)
        if p.startswith('/api/blob/'):
            parts = p.split('/')
            bid = parts[3]
            if not self.gated(0.3):
                return
            r = N.store.q('SELECT blob,blob_have FROM bundles WHERE id=?', (bid,))
            if len(parts) > 4 and parts[4] == 'have':
                return self.send(200, {'have': r[0]['blob_have'] if r else 0})
            data = bytes(r[0]['blob'] or b'') if r else b''
            if 'offset' in q:
                off = int(q['offset'][0])
                data = data[off:off + int(q.get('len', ['16384'])[0])]
            return self.send(200, data, 'image/jpeg')
        # static files
        name = PAGES.get(p) or ('app.html' if N.role == 'truck' else 'clinic.html') if p in PAGES or p == '/' else p.lstrip('/')
        path = os.path.normpath(os.path.join(WEB, name))
        if not path.startswith(WEB) or not os.path.isfile(path):
            return self.send(404, {'error': 'not found'})
        with open(path, 'rb') as f:
            self.send(200, f.read(), TYPES.get(os.path.splitext(path)[1], 'application/octet-stream'))

    def do_POST(self):
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)
        if p == '/api/sync':
            d = self.js()
            return self.gated() and self.send(200, N.sync(d))
        if p == '/api/bundles':
            d = self.js()
            return self.gated() and self.send(200, N.receive(d))
        if p.startswith('/api/blob/'):
            data = self.raw()
            if not self.gated(0.3):
                return
            return self.send(200, N.blob_put(p.split('/')[3], int(q.get('offset', ['0'])[0]), data))
        d = self.js()
        if p == '/api/compose':
            return self.send(200, N.compose(d))
        if p == '/api/event':
            return self.send(200, N.make_event(d['bundle'], d.get('type', 'seen')))
        if p == '/api/admin/link':
            if d.get('position') in ('free', 'camp', 'road', 'town'):
                N.position = d['position']
            if d.get('quality') in ('strong', 'weak'):
                N.quality = d['quality']
            return self.send(200, {'position': N.position, 'quality': N.quality})
        if p == '/api/admin/reset':
            N.reset()
            return self.send(200, {'ok': True})
        self.send(404, {'error': 'not found'})


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return '127.0.0.1'


def main():
    global N
    ap = argparse.ArgumentParser(description='Wasl node')
    ap.add_argument('--role', choices=['truck', 'clinic'], required=True)
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--name')
    ap.add_argument('--id')
    ap.add_argument('--peers', help='comma-separated base URLs of nodes to sync with when reachable')
    ap.add_argument('--db')
    a = ap.parse_args()
    if not a.db:
        os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
        a.db = os.path.join(ROOT, 'data', '%s-%d.db' % (a.role, a.port))
    N = Node(a)
    if N.peers:
        threading.Thread(target=N.peer_loop, daemon=True).start()
    srv = ThreadingHTTPServer(('0.0.0.0', a.port), H)
    srv.daemon_threads = True
    print('Wasl %s "%s" on http://%s:%d  (peers: %s)' % (N.role, N.name, lan_ip(), a.port, ', '.join(N.peers) or 'none'), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
