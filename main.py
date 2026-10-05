import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Catraca Coletor Cloud Server")

agentes_conectados = {}

@app.get("/")
def painel_teste():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Controle de Catraca / Coletor</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background: #f4f6f9; }
            .card { background: white; max-width: 480px; margin: auto; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            button { color: white; border: none; padding: 12px 20px; font-size: 15px; border-radius: 5px; cursor: pointer; margin: 6px; }
            .btn-liberar { background: #28a745; }
            .btn-bloquear { background: #dc3545; }
            #status { margin-top: 15px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Cofre Coletor & Catraca</h2>
            <input type="text" id="slug" value="loja_beta" placeholder="Slug da Loja" style="padding: 8px; width: 80%; margin-bottom: 15px;"><br>
            <button class="btn-liberar" onclick="enviarComando(true, 'Acesso liberado Volte Sempre')">Simular Liberação (Comanda Paga)</button>
            <button class="btn-bloquear" onclick="enviarComando(false, 'Acesso Negado Valide no Caixa')">Simular Bloqueio (Com Débito)</button>
            <div id="status"></div>
        </div>

        <script>
            async function enviarComando(liberado, msg) {
                const slug = document.getElementById('slug').value;
                const statusDiv = document.getElementById('status');
                statusDiv.innerText = "Enviando comando...";

                const resp = await fetch(`/api/resposta-comanda/${slug}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ liberado: liberado, mensagem: msg })
                });
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
            msg_texto = await websocket.receive_text()
            dados = json.loads(msg_texto)
            print(f"[WS RECEBIDO de {slug}]: {dados}")

            # Fluxograma: Recebe comanda do coletor -> Verifica -> Responde
            if dados.get("evento") == "VALIDAR_COMANDA":
                comanda = dados.get("comanda")
                print(f"--> Validando pagamento da comanda: {comanda}")

                # Exemplo de regra (aqui você conecta no banco/API de PDV):
                # Se o saldo estiver OK, libera:
                resposta = {
                    "tipo": "RESPOSTA_COMANDA",
                    "liberado": True,
                    "mensagem": "Acesso liberado Volte Sempre"
                }
                await websocket.send_text(json.dumps(resposta))

    except WebSocketDisconnect:
        if slug in agentes_conectados:
            del agentes_conectados[slug]
        print(f"[WS] Agente '{slug}' desconectou")

@app.post("/api/resposta-comanda/{slug}")
async def simular_resposta_api(slug: str, dados: dict):
    if slug not in agentes_conectados:
        return {"erro": f"Nenhum agente online para '{slug}'"}, 404

    payload = {
        "tipo": "RESPOSTA_COMANDA",
        "liberado": dados.get("liberado", False),
        "mensagem": dados.get("mensagem", "")
    }
    ws = agentes_conectados[slug]
    await ws.send_text(json.dumps(payload))
    return {"status": "sucesso", "mensagem": "Comando enviado para o agente"}
