from flask import Flask, request, jsonify, send_file, redirect
from datetime import datetime
import psycopg2
import os
import re
from openpyxl import Workbook
import io

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

# =========================
# HOME
# =========================
@app.route('/')
def home():
    return redirect('/scanner')

# =========================
# SCANNER APP STYLE
# =========================
@app.route('/scanner')
def scanner():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scanner PRO</title>

<script src="https://unpkg.com/html5-qrcode"></script>

<style>
body {
    font-family: Arial;
    background: #0f172a;
    color: white;
    text-align: center;
}

h2 { margin-top: 10px; }

#reader {
    width: 320px;
    margin: auto;
    border-radius: 12px;
    overflow: hidden;
}

button {
    padding: 12px;
    margin: 5px;
    border: none;
    border-radius: 10px;
    font-size: 16px;
}

.flash { background: orange; }
.painel { background: #22c55e; }
.apagar { background: red; }

#status {
    margin-top: 10px;
    font-size: 18px;
}

#raw {
    font-size: 14px;
    color: #94a3b8;
}
</style>
</head>

<body>

<h2>📷 Scanner</h2>

<div id="reader"></div>

<div>
    <button class="flash" onclick="toggleFlash()">🔦 Flash</button>
    <button class="painel" onclick="window.location='/dashboard'">📊 Painel</button>
</div>

<h2 id="status">Iniciando...</h2>
<div id="raw"></div>

<script>
let scanner;
let flashOn = false;
let ultimo = "";

// ======================
function iniciar(){

    scanner = new Html5Qrcode("reader");

    scanner.start(
        { facingMode: "environment" },
        {
            fps: 20,
            qrbox: { width: 280, height: 280 }
        },
        (text) => {

            if(text === ultimo) return;
            ultimo = text;

            processar(text);

            setTimeout(()=>{ ultimo=""; }, 1500);
        }
    ).then(()=>{
        document.getElementById("status").innerText = "📷 Pronto";
    }).catch(()=>{
        document.getElementById("status").innerText = "❌ Erro câmera";
    });
}

// ======================
function toggleFlash(){
    if(!scanner) return;

    scanner.getRunningTrackCapabilities().then(cap=>{
        if(cap.torch){
            scanner.applyVideoConstraints({
                advanced: [{ torch: !flashOn }]
            });
            flashOn = !flashOn;
        } else {
            alert("Flash não suportado");
        }
    });
}

// ======================
function processar(text){

    document.getElementById("raw").innerText = text;

    fetch('/scan',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({code:text})
    })
    .then(r=>r.json())
    .then(d=>{
        document.getElementById("status").innerText = d.msg;
    });

    // 🔊 bip
    new Audio("https://www.soundjay.com/buttons/sounds/beep-07.mp3").play();

    // 📳 vibração
    if (navigator.vibrate) {
        navigator.vibrate(200);
    }
}

iniciar();
</script>

</body>
</html>
"""

# =========================
# SCAN
# =========================
@app.route('/scan', methods=['POST'])
def scan():

    raw = request.json.get('code','')
    texto = raw.upper().strip()

    numeros = re.findall(r"\d+", texto)

    if len(numeros) >= 2:
        pacote = numeros[0]
        obra = numeros[1]
    else:
        return {"msg":"❌ NÃO RECONHECIDO"}

    codigo = f"{obra}.1-{pacote}"

    data = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leituras(
        id SERIAL PRIMARY KEY,
        codigo TEXT UNIQUE,
        obra TEXT,
        pacote TEXT,
        data TEXT,
        hora TEXT
    )
    """)

    try:
        cur.execute("""
        INSERT INTO leituras (codigo, obra, pacote, data, hora)
        VALUES (%s,%s,%s,%s,%s)
        """,(codigo,obra,pacote,data,hora))
        conn.commit()
    except:
        conn.rollback()
        return {"msg":f"⚠️ DUPLICADO {codigo}"}

    cur.close()
    conn.close()

    return {"msg":f"✅ {codigo}"}

# =========================
# DADOS
# =========================
@app.route('/dados')
def dados():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id,codigo,obra,pacote,data FROM leituras ORDER BY id DESC")

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([{
        "id":r[0],
        "codigo":r[1],
        "obra":r[2],
        "pacote":r[3],
        "data":r[4]
    } for r in rows])

# =========================
# APAGAR
# =========================
@app.route('/delete/<int:id>')
def delete(id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM leituras WHERE id=%s",(id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect('/dashboard')

# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    return """
<h2>📊 Painel</h2>

🔍 <input type="text" id="busca" placeholder="Pesquisar">

<h3 id="total"></h3>

<table border="1">
<thead>
<tr>
<th>Código</th>
<th>Obra</th>
<th>Pacote</th>
<th>Ação</th>
</tr>
</thead>
<tbody id="tb"></tbody>

<script>
let listaGlobal = [];

function carregar(){
    fetch('/dados')
    .then(r=>r.json())
    .then(lista=>{
        listaGlobal = lista;
        render(lista);
    });
}

function render(lista){
    let tb=document.getElementById("tb");
    tb.innerHTML="";

    lista.forEach(l=>{
        tb.innerHTML+=`<tr>
        <td>${l.codigo}</td>
        <td>${l.obra}</td>
        <td>${l.pacote}</td>
        <td><a href="/delete/${l.id}">🗑️</a></td>
        </tr>`;
    });
}

document.getElementById("busca").addEventListener("input", function(){
    let termo = this.value.toLowerCase();

    let filtrado = listaGlobal.filter(l =>
        l.codigo.toLowerCase().includes(termo) ||
        l.obra.toLowerCase().includes(termo)
    );

    render(filtrado);
});

carregar();
</script>
"""

# =========================
# EXPORTAR
# =========================
@app.route('/exportar')
def exportar():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT codigo,obra,pacote,data FROM leituras")
    rows = cur.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.append(["Código","Obra","Pacote","Data"])

    for r in rows:
        ws.append(r)

    file = io.BytesIO()
    wb.save(file)
    file.seek(0)

    return send_file(file, download_name="relatorio.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run()
