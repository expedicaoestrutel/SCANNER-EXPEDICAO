<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Leitor QR - Expedição</title>

<script src="https://unpkg.com/html5-qrcode@2.3.8"></script>

<style>
body {
    margin: 0;
    font-family: Arial;
    background: #f2f2f2;
}

/* HEADER */
.header {
    background: #e53935;
    color: white;
    padding: 15px;
    font-size: 18px;
}

/* BUSCA */
.search-box {
    padding: 10px;
    background: white;
}

.search-box input {
    width: 100%;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #ccc;
}

/* LISTA */
.item {
    background: white;
    padding: 15px;
    margin: 5px 10px;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
}

/* BOTÕES */
.btn-camera {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #e53935;
    width: 65px;
    height: 65px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 28px;
}

/* CAMERA */
#reader {
    width: 100%;
    height: 300px;
    display: none;
}
</style>
</head>

<body>

<div class="header">RELATÓRIO DE CARGA</div>

<div class="search-box">
    <input type="text" placeholder="Buscar..." onkeyup="filtrar(this.value)">
</div>

<div id="reader"></div>

<div id="lista"></div>

<div class="btn-camera" onclick="iniciarScanner()">📷</div>

<script>
let lista = [];
let html5QrCode;
let scanning = false;

/* INICIAR SCANNER (CORRIGIDO) */
function iniciarScanner() {

    document.getElementById("reader").style.display = "block";

    html5QrCode = new Html5Qrcode("reader");

    const config = {
        fps: 15,
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0
    };

    html5QrCode.start(
        { facingMode: "environment" }, // 🔥 GARANTE câmera traseira
        config,
        (decodedText) => {
            if (!scanning) {
                scanning = true;

                navigator.vibrate(200);

                if (!lista.includes(decodedText)) {
                    lista.push(decodedText);
                    atualizarLista();
                }

                // 🔥 EVITA TRAVAR
                setTimeout(() => scanning = false, 1200);
            }
        },
        (error) => {
            // ignora erros de leitura
        }
    ).catch(err => {
        alert("Erro ao abrir câmera: " + err);
    });
}

/* LISTA */
function atualizarLista() {
    let div = document.getElementById("lista");
    div.innerHTML = "";

    lista.forEach((item, index) => {
        div.innerHTML += `
        <div class="item" onclick="editar(${index})">
            <span>${item}</span>
            <span>✔</span>
        </div>`;
    });
}

/* EDITAR */
function editar(i) {
    let novo = prompt("Editar:", lista[i]);
    if (novo) {
        lista[i] = novo;
        atualizarLista();
    }
}

/* BUSCA */
function filtrar(txt) {
    txt = txt.toLowerCase();

    let filtrado = lista.filter(i => i.toLowerCase().includes(txt));

    let div = document.getElementById("lista");
    div.innerHTML = "";

    filtrado.forEach(item => {
        div.innerHTML += `
        <div class="item">
            <span>${item}</span>
            <span>✔</span>
        </div>`;
    });
}
</script>

</body>
</html>
