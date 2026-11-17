#!/usr/bin/env python3
"""Build docs/ : the static pages (deck, simulation, kit) for GitHub Pages.
The three-screen demo needs the two node processes, so it is not part of the static site."""
import os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB, OUT = os.path.join(ROOT, 'web'), os.path.join(ROOT, 'docs')
VIDEO = sys.argv[1] if len(sys.argv) > 1 else ''
REPO = 'https://github.com/siddharth-vegesna/wasl'

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
for f in ('common.css', 'pixel.css', 'common.js'):
    shutil.copy(os.path.join(WEB, f), OUT)
open(os.path.join(OUT, '.nojekyll'), 'w').close()

LINKS = {'/sim': 'sim.html', '/pitch': 'index.html', '/stage': 'live.html', '/clinic': 'live.html'}
def fix(s):
    s = s.replace('href="/common.css"', 'href="common.css"').replace('href="/pixel.css"', 'href="pixel.css"').replace('src="/common.js"', 'src="common.js"')
    for a, b in LINKS.items():
        s = s.replace('href="%s"' % a, 'href="%s"' % b)
    return s

for src, dst in (('pitch.html', 'index.html'), ('sim.html', 'sim.html'), ('kit.html', 'kit.html')):
    with open(os.path.join(WEB, src), encoding='utf-8') as f:
        s = fix(f.read())
    with open(os.path.join(OUT, dst), 'w', encoding='utf-8') as f:
        f.write(s)

video = ('<a class="btn on" href="%s">Watch the demo video</a>' % VIDEO) if VIDEO else ''
live = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wasl · Live demo</title>
<link rel="stylesheet" href="common.css"><link rel="stylesheet" href="pixel.css" data-skin>
<style>body{padding:21px;max-width:900px;margin:0 auto}.bar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:21px}
.box{padding:18px;margin-bottom:21px}pre{background:var(--ink);color:var(--paper);padding:12px;overflow:auto;margin:9px 0;font-family:var(--mono)}
p{margin:9px 0;font-size:15px}.links{display:flex;gap:9px;flex-wrap:wrap;margin-top:15px}</style></head>
<body>
<div class="bar"><span data-brand="3"></span><nav class="top"><a href="index.html">Pitch</a><a href="sim.html">Simulation</a><a href="kit.html">Kit</a><a class="cur" href="live.html">Live demo</a></nav></div>
<div class="box"><canvas class="px" id="sc"></canvas></div>
<div class="box">
  <div data-px="4">The live demo is three machines.</div>
  <p>Wasl is a camp phone, a small computer in a water truck, and a clinic laptop exchanging messages with no internet between them. That cannot run on a static web page, so run it yourself below. The truck node is designed for a Raspberry Pi; so far it has run on a laptop, with radio range emulated.</p>
  <div class="links">%s<a class="btn" href="%s">Code on GitHub</a><a class="btn" href="sim.html">Network simulation</a></div>
</div>
<div class="box">
  <div data-px="3">Run all three on your laptop</div>
  <p>Python 3 only. No installs, nothing fetched from the internet.</p>
  <pre>git clone %s.git
cd wasl
./scripts/run-local.sh</pre>
  <p>Then open <b>http://localhost:8081/stage</b>: the phone, the truck and the clinic side by side, with buttons that move the truck in and out of range.</p>
</div>
<script src="common.js"></script>
<script>const s = Scene($('#sc'), 'route'); let i = 0; setInterval(() => s.set({pos: ['camp', 'road', 'town', 'road'][i++ %% 4]}), 3500);</script>
</body></html>''' % (video, REPO, REPO)
with open(os.path.join(OUT, 'live.html'), 'w', encoding='utf-8') as f:
    f.write(live)
print('built', sorted(os.listdir(OUT)))
