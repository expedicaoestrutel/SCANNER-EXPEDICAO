from flask import Flask, request, render_template_string, jsonify, send_file
from datetime import datetime
import psycopg2
import os
import re
from openpyxl import Workbook

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return None

leituras_memoria = []

# =========================
# 📷 SCANNER
# =========================
@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Scanner Expedição</title>
<script src="https://unpkg.com/html5-qrcode"></script>
</head>

<body style="text-align:center;font-family:Arial">

<h2>📷 Scanner Expedição</h2>

<div id="reader" style="width:320px;margin:auto;"></div>

<br>
<button onclick="trocarCamera()">🔄 Trocar Câmera</button>

<h2 id="status">Aguardando leitura...</h2>

<br>
<a href="/dashboard">📊 Painel</a>

<script>
let html5QrCode;
let cameras = [];
let cameraIndex = 0;

function iniciar(cameraId){
    html5QrCode = new Html5Qrcode("reader");

    html5QrCode.start(
        cameraId,
        { fps: 10, qrbox: 250 },
        (decodedText) => {

            fetch('/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: decodedText})
            })
            .then(r => r.json())
            .then(resp => {
                document.getElementById("status").innerText = resp.msg;
            });

            let audio = new Audio("https://www.soundjay.com/buttons/sounds/beep-07.mp3");
            audio.play();
        }
    );
}

function startScanner(){
    Html5Qrcode.getCameras().then(devices => {

        cameras = devices;

        let traseira = devices.find(d =>
            d.label.toLowerCase().includes("back")
        );

        cameraIndex = traseira ? devices.indexOf(traseira) : 0;

        iniciar(devices[cameraIndex].id);

    });
}

function trocarCamera(){
    html5QrCode.stop().then(() => {
        cameraIndex = (cameraIndex + 1) % cameras.length;
        iniciar(cameras[cameraIndex].id);
    });
}

startScanner();
</script>

</body>
</html>
""")

# =========================
# 📥 SCAN INTELIGENTE
# =========================
@app.route('/scan', methods=['POST'])
def scan():
    raw = request.json.get('code', '').strip()
    texto = raw.upper()

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 🔥 FORMATO 1: 123456.3-5
    match = re.search(r"(\\d+)\\.(\\d+)-(\\d+)", texto)

    if match:
        obra = match.group(1)
        caixa = match.group(2)
        pacote = match.group(3)
        total = "?"

    else:
        # 🔥 FORMATO 2: só números
        numeros = re.findall(r"\\d+", texto)

        if len(numeros) >= 3:
            obra, caixa, pacote = numeros[0], numeros[1], numeros[2]
            total = numeros[3] if len(numeros) >= 4 else "?"
        else:
            return {"msg": f"❌ Não reconhecido: {raw}"}

    codigo = f"{obra}.{caixa}-{pacote}"

    # =========================
    # SALVAR
    # =========================
    conn = get_db()

    if conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS leituras (
                    id SERIAL PRIMARY KEY,
                    codigo TEXT UNIQUE,
                    obra TEXT,
                    caixa TEXT,
                    pacote TEXT,
                    total TEXT,
                    data TEXT
                )
            """)

            cur.execute("""
                INSERT INTO leituras (codigo, obra, caixa, pacote, total, data)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (codigo, obra, caixa, pacote, total, agora))

            conn.commit()
        except:
            conn.rollback()
            return {"msg": f"⚠️ DUPLICADO: {codigo}"}
        finally:
            cur.close()
            conn.close()
    else:
        for item in leituras_memoria:
            if item["codigo"] == codigo:
                return {"msg": f"⚠️ DUPLICADO: {codigo}"}

        leituras_memoria.append({
            "codigo": codigo,
            "obra": obra,
            "caixa": caixa,
            "pacote": pacote,
            "total": total
        })

    return {"msg": f"✅ LIDO: {codigo}"}

# =========================
# DADOS
# =========================
@app.route('/dados')
def dados():
    conn = get_db()

    if conn:
        cur = conn.cursor()
        cur.execute("SELECT obra, caixa, pacote, total FROM leituras")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        lista = [{"obra": r[0], "caixa": r[1], "pacote": r[2], "total": r[3]} for r in rows]
    else:
        lista = leituras_memoria

    return jsonify({"lista": lista})

# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    return "<h1>Painel funcionando 🚀</h1>"

if __name__ == '__main__':
    app.run()
