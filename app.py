from flask import Flask, request, jsonify, redirect
import re

app = Flask(__name__)

# =========================
@app.route('/')
def home():
    return redirect('/app')

# =========================
# TELA PRINCIPAL (SESSÕES)
# =========================
@app.route('/app')
def app_ui():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body { margin:0; font-family:Arial; background:#eee; }

/* HEADER */
.header {
    background:#d32f2f;
    color:white;
    padding:15px;
    font-size:20px;
    text-align:center;
}

/* LISTA */
.card {
    background:white;
    margin:10px;
    padding:15px;
    border-radius:10px;
}

.title { font-size:16px; font-weight:bold; }
.sub { color:gray; font-size:13px; }

/* BOTÃO */
.fab {
    position:fixed;
    bottom:20px;
    right:20px;
    background:#f44336;
    width:60px;
    height:60px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:28px;
    color:white;
    cursor:pointer;
}
</style>
</head>

<body>

<div class="header">Sessões de leitura</div>

<div id="lista"></div>

<div class="fab" onclick="window.location='/scanner'">📷</div>

<script>

let sessoes = {};

function render(){

    let html="";

    for(let s in sessoes){

        let total = sessoes[s].length;

        html+=`
        <div class="card" onclick="abrir('${s}')">
            <div class="title">PACOTE Nº${s}</div>
            <div class="sub">Número de leituras: ${total}</div>
        </div>
        `;
    }

    document.getElementById("lista").innerHTML = html;
}

function abrir(s){
    localStorage.setItem("pacote", s);
    window.location = "/detalhe";
}

// simulação inicial
render();

</script>

</body>
</html>
"""

# =========================
# DETALHE DO PACOTE
# =========================
@app.route('/detalhe')
def detalhe():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body { margin:0; font-family:Arial; }

.header {
    background:#d32f2f;
    color:white;
    padding:15px;
    text-align:center;
}

.item {
    padding:10px;
    border-bottom:1px solid #ccc;
}
</style>
</head>

<body>

<div class="header" id="titulo"></div>

<div id="lista"></div>

<script>

let pacote = localStorage.getItem("pacote");
document.getElementById("titulo").innerText = "PACOTE Nº" + pacote;

let dados = JSON.parse(localStorage.getItem("dados") || "{}");

let html="";

(dados[pacote] || []).forEach(p=>{
    html += `<div class="item">${p}</div>`;
});

document.getElementById("lista").innerHTML = html;

</script>

</body>
</html>
"""

# =========================
# SCANNER
# =========================
@app.route('/scanner')
def scanner():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://unpkg.com/html5-qrcode"></script>

<style>
body { text-align:center; font-family:Arial; }
#reader { width:300px; margin:auto; }
</style>
</head>

<body>

<h3>Scanner</h3>

<div id="reader"></div>

<script>
let scanner;
let ultimo="";
let pacoteAtual="";

let dados = JSON.parse(localStorage.getItem("dados") || "{}");

function salvar(){
    localStorage.setItem("dados", JSON.stringify(dados));
}

function iniciar(){
    scanner = new Html5Qrcode("reader");

    scanner.start(
        { facingMode:"environment" },
        { fps:20, qrbox:250 },
        (text)=>{

            if(text===ultimo) return;
            ultimo=text;

            // PACOTE
            if(text.toUpperCase().includes("PACOTE")){

                let nums = text.match(/\\d+/g);
                pacoteAtual = nums[0];

                if(!dados[pacoteAtual]){
                    dados[pacoteAtual] = [];
                }

                salvar();
                alert("PACOTE "+pacoteAtual);
            }
            else{

                if(!pacoteAtual){
                    alert("Leia um pacote primeiro");
                    return;
                }

                dados[pacoteAtual].push(text);
                salvar();
            }

            new Audio("https://www.soundjay.com/buttons/sounds/beep-07.mp3").play();

            setTimeout(()=>{ultimo=""},800);
        }
    );
}

iniciar();
</script>

</body>
</html>
"""

# =========================
if __name__ == '__main__':
    app.run()
