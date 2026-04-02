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
# SCANNER COM TELA DINÂMICA
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
body { background:#0f172a; color:white; text-align:center; font-family:Arial; }

#reader { width:320px; margin:auto; border-radius:12px; overflow:hidden; }

button {
    padding:10px;
    margin:5px;
    border:none;
    border-radius:10px;
}

#pacote {
    font-size:20px;
    margin:10px;
    color:#22c55e;
}

#lista {
    max-height:200px;
    overflow:auto;
    background:#111827;
    padding:10px;
    border-radius:10px;
    margin:10px;
}

.item {
    border-bottom:1px solid #333;
    padding:5px;
    font-size:14px;
}
</style>
</head>

<body>

<h2>📷 Scanner</h2>

<div id="reader"></div>

<button onclick="toggleFlash()">🔦 Flash</button>

<h2 id="status">Iniciando...</h2>

<div id="pacote">📦 Nenhum pacote</div>

<div id="lista"></div>

<script>
let scanner;
let ultimo="";
let flashOn=false;

function iniciar(){
    scanner = new Html5Qrcode("reader");

    scanner.start(
        { facingMode: "environment" },
        { fps:20, qrbox:{width:280,height:280} },
        (text)=>{

            if(text===ultimo) return;
            ultimo=text;

            fetch('/scan',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({code:text})
            })
            .then(r=>r.json())
            .then(d=>{
                document.getElementById("status").innerText=d.msg;

                if(d.pacote){
                    document.getElementById("pacote").innerText="📦 PACOTE "+d.pacote;
                    document.getElementById("lista").innerHTML="";
                }

                if(d.peca){
                    adicionarLista(d.peca);
                }
            });

            new Audio("https://www.soundjay.com/buttons/sounds/beep-07.mp3").play();
            if(navigator.vibrate) navigator.vibrate(200);

            setTimeout(()=>{ultimo=""},1000);
        }
    );
}

function adicionarLista(txt){
    let div=document.createElement("div");
    div.className="item";
    div.innerText=txt;

    let lista=document.getElementById("lista");
    lista.prepend(div);
}

async function toggleFlash(){
    try{
        const track = scanner.getRunningTrack();
        const cap = track.getCapabilities();

        if(cap.torch){
            await track.applyConstraints({
                advanced:[{torch:!flashOn}]
            });
            flashOn=!flashOn;
        } else {
            alert("Flash não suportado");
        }
    }catch(e){
        alert("Erro flash");
    }
}

iniciar();
</script>

</body>
</html>
"""

# =========================
# SCAN COM RETORNO EM TEMPO REAL
# =========================
@app.route('/scan', methods=['POST'])
def scan():

    raw = request.json.get('code','')
    texto = raw.upper().strip()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leituras(
        id SERIAL PRIMARY KEY,
        tipo TEXT,
        codigo TEXT UNIQUE,
        obra TEXT,
        pacote TEXT,
        data TEXT,
        hora TEXT
    )
    """)

    data = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")

    # PACOTE
    if "PACOTE" in texto:

        numeros = re.findall(r"\d+", texto)

        if len(numeros) >= 2:
            pacote = numeros[0]
            obra = numeros[1]

            codigo = f"{obra}.1-{pacote}"

            try:
                cur.execute("""
                INSERT INTO leituras (tipo,codigo,obra,pacote,data,hora)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,("PACOTE",codigo,obra,pacote,data,hora))
                conn.commit()
            except:
                conn.rollback()

            return {"msg":f"📦 PACOTE {pacote}", "pacote": pacote}

    # PEÇA
    else:

        cur.execute("""
        SELECT pacote, obra FROM leituras
        WHERE tipo='PACOTE'
        ORDER BY id DESC LIMIT 1
        """)

        ultimo = cur.fetchone()

        if not ultimo:
            return {"msg":"⚠️ LEIA PACOTE"}

        pacote, obra = ultimo

        try:
            cur.execute("""
            INSERT INTO leituras (tipo,codigo,obra,pacote,data,hora)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,("PECA",texto,obra,pacote,data,hora))
            conn.commit()
        except:
            conn.rollback()
            return {"msg":"⚠️ DUPLICADO"}

        return {
            "msg":f"🔩 OK",
            "peca": texto,
            "pacote": pacote
        }

# =========================
# EXPORTAR
# =========================
@app.route('/exportar')
def exportar():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT tipo,codigo,obra,pacote,data FROM leituras")
    rows = cur.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.append(["Tipo","Código","Obra","Pacote","Data"])

    for r in rows:
        ws.append(r)

    file = io.BytesIO()
    wb.save(file)
    file.seek(0)

    return send_file(file, download_name="relatorio.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run()
