import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Catraca Cloud Server")

agentes_conectados = {}

@app.get("/")
def painel_teste():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Painel de Controle da Catraca</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background: #f4f6f9; }
            .card { background: white; max-width: 450px; margin: auto; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            button { background: #28a745; color: white; border: none; padding: 12px 25px; font-size: 16px; border-radius: 5px; cursor: pointer; margin: 5px; }
            button:hover { background: #218838; }
            #status { margin-top: 15px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Controle de Catraca</h2>
            <input type="text" id="slug" value="loja_beta" placeholder="Slug da Loja" style="padding: 8px; width: 80%; margin-bottom: 15px;"><br>
            <button onclick="enviarComando('horario')">Liberar Sentido Horário</button>
            <button onclick="enviarComando('anti-horario')">Liberar Anti-Horário</button>
            <div id="status"></div>
        </div>

        <script>
            async function enviarComando(sentido) {
                const slug = document.getElementById('slug').value;
                const statusDiv = document.getElementById('status');
                statusDiv.innerText = "Enviando comando...";

                const resp = await fetch(`/api/liberar/${slug}?sentido=${sentido}&mensagem=LIBERADO`, { method: 'POST' });
                const dados = await resp.json();
                statusDiv.innerText = dados.mensagem || dados.erro;
                statusDiv.style.color = resp.ok ? "green" : "red";
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.websocket("/admin/api/system/ws/turnstile/{slug}")
async def websocket_endpoint(websocket: WebSocket, slug: str, agent_id: str = ""):
    await websocket.accept()
    agentes_conectados[slug] = websocket
    print(f"[WS] Agente '{slug}' conectado")

    try:
        while True:
            mensagem = await websocket.receive_text()
            print(f"[EVENTO de {slug}]: {mensagem}")
    except WebSocketDisconnect:
        if slug in agentes_conectados:
            del agentes_conectados[slug]
        print(f"[WS] Agente '{slug}' desconectou")

@app.post("/api/liberar/{slug}")
async def liberar_catraca(slug: str, sentido: str = "horario", mensagem: str = "LIBERADO"):
    if slug not in agentes_conectados:
        return {"erro": f"Nenhum agente online para a loja '{slug}'"}, 404

    payload = {
        "tipo": "LIBERAR_CATRACA",
        "sentido": sentido,
        "mensagem": mensagem
    }

    ws = agentes_conectados[slug]
    await ws.send_text(json.dumps(payload))
    return {"status": "sucesso", "mensagem": f"Comando enviado para a catraca da loja '{slug}'"}
