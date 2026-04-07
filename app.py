from flask import Flask, request, jsonify, Response
import psycopg2, os, re
import pandas as pd
from io import BytesIO

app = Flask(__name__)
DATABASE_URL = os.environ.get("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL)

# =========================
# CRIAR TABELAS
# =========================
def criar():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leituras(
        id SERIAL PRIMARY KEY,
        pacote TEXT,
        codigo TEXT,
        obra TEXT,
        usuario TEXT,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lista(
        id SERIAL PRIMARY KEY,
        obra TEXT,
        codigo TEXT,
        qtde INTEGER
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

criar()

# =========================
# TRATAR CÓDIGO
# =========================
def tratar_codigo(txt):
    txt = txt.upper()

    obra = None
    codigo = txt

    obra_match = re.search(r'OBRA\s*(\d+)', txt)
    cod_match = re.findall(r'\d+', txt)

    if obra_match:
        obra = obra_match.group(1)

    if cod_match:
        codigo = cod_match[0]

    return codigo, obra

# =========================
# SCAN (SERVIDOR)
# =========================
@app.route('/scan', methods=['POST'])
def scan():
    texto = request.json.get('code','').strip()
    usuario = request.json.get('usuario','OPERADOR')
    pacotes = request.json.get('pacotes', [])

    texto_up = texto.upper()

    if "PACOTE" in texto_up:
        nums = re.findall(r"\d+", texto_up)
        if nums:
            return {"novo_pacote": nums[0]}

    if not pacotes:
        return {"erro":"sem pacote"}

    codigo, obra = tratar_codigo(texto_up)

    conn = db()
    cur = conn.cursor()

    duplicado = False

    for p in pacotes:
        cur.execute("""
        SELECT 1 FROM leituras
        WHERE pacote=%s AND codigo=%s
        """,(p,codigo))

        if cur.fetchone():
            duplicado = True
        else:
            cur.execute("""
            INSERT INTO leituras (pacote,codigo,obra,usuario)
            VALUES (%s,%s,%s,%s)
            """,(p,codigo,obra,usuario))

    conn.commit()
    cur.close()
    conn.close()

    if duplicado:
        return {"duplicado": True}

    return {"ok": True}

# =========================
# EXPORTAR EXCEL
# =========================
@app.route('/exportar_excel')
def exportar_excel():
    conn = db()
    df = pd.read_sql("SELECT * FROM leituras", conn)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    if not df.empty:
        for obra in df['obra'].dropna().unique():
            df[df['obra']==obra].to_excel(writer, sheet_name=f"OBRA_{obra}", index=False)

    writer.close()
    output.seek(0)

    return Response(output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment;filename=expedicao.xlsx"})

# =========================
# EXPORTAR SEPARAÇÃO
# =========================
@app.route('/exportar_obra')
def exportar_obra():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT obra, pacote, codigo
    FROM leituras
    ORDER BY obra, pacote
    """)

    dados = cur.fetchall()

    estrutura = {}

    for obra, pacote, codigo in dados:
        estrutura.setdefault(obra, {})
        estrutura[obra].setdefault(pacote, [])
        estrutura[obra][pacote].append(codigo)

    texto = ""

    for obra in estrutura:
        texto += f"OBRA: {obra}\n\n"

        for pacote in estrutura[obra]:
            texto += f"VOLUME {pacote}\n"
            for cod in estrutura[obra][pacote]:
                texto += f"- {cod}\n"
            texto += "\n"

        texto += "\n---------------------\n\n"

    cur.close()
    conn.close()

    return Response(texto,
        mimetype="text/plain",
        headers={"Content-Disposition":"attachment;filename=separacao.txt"})

# =========================
# FRONT (OFFLINE)
# =========================
@app.route('/')
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://unpkg.com/html5-qrcode"></script>

<style>
body { margin:0; background:#111; color:white; font-family:Arial; }
.header { padding:10px; background:#222; }

.volume { margin:10px; padding:10px; border-radius:10px; }

.obra-1129 { background:#1b5e20; }
.obra-1130 { background:#0d47a1; }
.obra-1131 { background:#f9a825; color:black; }
.obra-1132 { background:#b71c1c; }

.item { border-bottom:1px solid rgba(255,255,255,0.1); }
.btn { padding:10px; margin:5px; background:#00c853; border:none; border-radius:8px; color:white; }
</style>
</head>

<body>

<div class="header">
<input id="user" placeholder="Usuário">
<button class="btn" onclick="sync()">🔄 Sync</button>
<button class="btn" onclick="excel()">📊 Excel</button>
<button class="btn" onclick="obra()">📦 Separação</button>
</div>

<div id="reader"></div>
<div id="lista"></div>

<script>
let dados = JSON.parse(localStorage.getItem("dados") || "{}");

function salvar(){ localStorage.setItem("dados", JSON.stringify(dados)); }

function detectarObra(txt){
    let m = txt.match(/OBRA\\s*(\\d+)/);
    if(m) return m[1];
    let n = txt.match(/\\d+/);
    return n ? n[0] : "0000";
}

function atualizar(){
    let html = "";

    for(let v in dados){
        let obra = dados[v].obra;
        let pecas = dados[v].pecas;

        html += `<div class="volume obra-${obra}">
        <b>📦 Volume ${v} | Obra ${obra} (${pecas.length})</b>`;

        pecas.forEach(p=>{
            html += `<div class="item">🔢 ${p}</div>`;
        });

        html += "</div>";
    }

    document.getElementById("lista").innerHTML = html;
}

function onScanSuccess(txt){

    txt = txt.toUpperCase();

    if(txt.includes("PACOTE")){
        let num = txt.match(/\\d+/);
        let obra = detectarObra(txt);

        if(num){
            let v = num[0];
            if(!dados[v]) dados[v] = {obra:obra, pecas:[]};
            salvar(); atualizar(); return;
        }
    }

    let cod = txt.match(/\\d+/);
    if(!cod) return;
    cod = cod[0];

    let vols = Object.keys(dados);
    if(vols.length===0){ alert("Leia volume"); return; }

    vols.forEach(v=>{
        if(!dados[v].pecas.includes(cod)){
            dados[v].pecas.push(cod);
        } else {
            alert("Duplicado");
        }
    });

    salvar(); atualizar();
}

function sync(){
    let user = document.getElementById("user").value;

    for(let v in dados){
        dados[v].pecas.forEach(c=>{
            fetch('/scan',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({code:c,usuario:user,pacotes:[v]})
            });
        });
    }

    alert("Sincronizado");
}

function excel(){ window.open('/exportar_excel'); }
function obra(){ window.open('/exportar_obra'); }

const html5QrCode = new Html5Qrcode("reader");
Html5Qrcode.getCameras().then(d=>{
    html5QrCode.start(d[0].id,{fps:10,qrbox:250},onScanSuccess);
});

atualizar();
</script>

</body>
</html>
"""

# =========================
# RENDER (OBRIGATÓRIO)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
