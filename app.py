from flask import Flask, request, render_template_string, jsonify
from datetime import datetime
import re

app = Flask(__name__)

leituras = []

# =========================
# 📷 SCANNER
# =========================
@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Scanner</title>
<script src="https://unpkg.com/html5-qrcode"></script>
</head>

<body style="text-align:center;font-family:Arial">

<h2>📷 Scanner</h2>

<div id="reader" style="width:300px;margin:auto;"></div>

<h2 id="status">Aguardando leitura...</h2>
<h3 id="raw"></h3>

<script>
function start(){
    let scanner = new Html5Qrcode("reader");

    Html5Qrcode.getCameras().then(devices => {

        let cam = devices[0].id;

        scanner.start(cam, { fps:10, qrbox:250 }, (text)=>{

            document.getElementById("raw").innerText = "RAW: " + text;

            fetch('/scan', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body: JSON.stringify({code:text})
            })
            .then(r=>r.json())
            .then(resp=>{
                document.getElementById("status").innerText = resp.msg;
            });

        });
    });
}

start();
</script>

</body>
</html>
""")

# =========================
# 📥 SCAN UNIVERSAL
# =========================
@app.route('/scan', methods=['POST'])
def scan():
    raw = request.json.get('code', '')
    texto = raw.upper()

    numeros = re.findall(r"\d+", texto)

    if len(numeros) >= 3:
        obra = numeros[0]
        caixa = numeros[1]
        pacote = numeros[2]
        total = numeros[3] if len(numeros) > 3 else "?"

        codigo = f"{obra}.{caixa}-{pacote}"

        # evitar duplicado
        for l in leituras:
            if l["codigo"] == codigo:
                return {"msg": f"⚠️ DUPLICADO: {codigo}"}

        leituras.append({
            "codigo": codigo,
            "obra": obra,
            "caixa": caixa,
            "pacote": pacote,
            "total": total,
            "hora": datetime.now().strftime("%H:%M:%S")
        })

        return {"msg": f"✅ {codigo}"}

    return {"msg": f"❌ NÃO RECONHECIDO"}

# =========================
# DEBUG DADOS
# =========================
@app.route('/dados')
def dados():
    return jsonify(leituras)

if __name__ == '__main__':
    app.run()
