import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="ALIV SaaS - Gestão de Catraca & Comandas")

# Armazenamento em memória (estado do sistema)
agentes_conectados = {}

# Estado das Catracas cadastradas
catracas_config = {
    "loja_beta": {
        "nome": "Catraca de Saída / Coletor",
        "ip": "192.168.13.102",
        "porta": 3000,
        "segundos": 7,
        "ativa": True,
        "cartao_sem_cadastro_entra": False,
        "cartao_sem_cadastro_nao_sai": True
    }
}

# Simulação da base de comandas (1 a 10) baseada nas telas
comandas_db = {
    "1": {"saldo": 8.80, "status": "aberta", "detalhes": "1x Esfiha de Atum"},
    "2": {"saldo": 11.00, "status": "aberta", "detalhes": "1x Esfiha de Atum c/ Catupiry"},
    "3": {"saldo": 25.85, "status": "aberta", "detalhes": "2x Esfiha Atum c/ Queijo, 1x Água"},
    "4": {"saldo": 7.70, "status": "aberta", "detalhes": "1x Esfiha de Bauru"},
    "5": {"saldo": 68.74, "status": "aberta", "detalhes": "1x Pizza Grande, 1x Água"},
    "6": {"saldo": 8.80, "status": "aberta", "detalhes": "1x Esfiha de Atum"},
    "7": {"saldo": 0.00, "status": "livre", "detalhes": "Sem consumo"},
    "8": {"saldo": 11.00, "status": "aberta", "detalhes": "1x Esfiha Atum c/ Catupiry"},
    "9": {"saldo": 11.00, "status": "aberta", "detalhes": "Mesa 12 - Guilherme"},
    "10": {"saldo": 756.71, "status": "aberta", "detalhes": "1x Pizza Broto, 1x Pizza Grande"}
}

historico_passagens = []

@app.get("/", response_class=HTMLResponse)
def dashboard_catraca():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>ALIV SaaS - Catraca EVO</title>
        <style>
            :root {
                --bg-body: #0d1322;
                --bg-card: #151d30;
                --bg-input: #1d263b;
                --border-color: #27344e;
                --primary: #3b82f6;
                --success: #10b981;
                --danger: #ef4444;
                --warning: #f59e0b;
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            body { background: var(--bg-body); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }

            /* Sidebar */
            .sidebar { width: 220px; background: #0a0f1d; border-right: 1px solid var(--border-color); padding: 20px 15px; display: flex; flex-direction: column; gap: 15px; }
            .logo { font-size: 20px; font-weight: bold; color: var(--primary); display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
            .menu-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; color: var(--text-muted); cursor: pointer; text-decoration: none; font-size: 14px; }
            .menu-item.active, .menu-item:hover { background: #1e293b; color: white; }

            /* Conteúdo Principal */
            .main { flex: 1; padding: 25px; overflow-y: auto; }
            .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .badge-beta { background: #374151; font-size: 11px; padding: 3px 8px; border-radius: 4px; color: #60a5fa; font-weight: bold; margin-left: 8px; }

            .grid-container { display: grid; grid-template-columns: 1fr 1.2fr; gap: 20px; }
            .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 20px; }
            .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; font-size: 16px; font-weight: 600; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }

            /* Formulários */
            .form-group { margin-bottom: 12px; }
            label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 5px; }
            input, select { width: 100%; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 10px; color: white; font-size: 13px; }
            .row-form { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

            /* Botões */
            .btn { border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: 0.2s; }
            .btn-primary { background: var(--primary); color: white; }
            .btn-success { background: var(--success); color: white; }
            .btn-danger { background: var(--danger); color: white; }
            .btn-sm { padding: 4px 8px; font-size: 11px; }

            /* Tabela de Comandas */
            table { width: 100%; border-collapse: collapse; font-size: 12px; }
            th { text-align: left; padding: 8px; color: var(--text-muted); border-bottom: 1px solid var(--border-color); font-weight: 600; }
            td { padding: 8px; border-bottom: 1px solid var(--border-color); }
            .status-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
            .status-aberta { background: rgba(239, 68, 68, 0.15); color: #f87171; }
            .status-livre { background: rgba(16, 185, 129, 0.15); color: #34d399; }

            /* Logs / Passagens */
            .logs-container { margin-top: 20px; }
            .log-item { display: flex; justify-content: space-between; font-size: 12px; padding: 6px 0; border-bottom: 1px dashed var(--border-color); }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo">🚀 ALIV <span>SaaS</span></div>
            <a class="menu-item">📊 Visão Geral</a>
            <a class="menu-item">📦 Pedidos</a>
            <a class="menu-item">🍽️ Cardápio</a>
            <a class="menu-item active">🛡️ Catraca EVO</a>
            <a class="menu-item">💰 Financeiro</a>
        </div>

        <div class="main">
            <div class="top-bar">
                <div>
                    <h2>Catraca EVO <span class="badge-beta">BETA</span></h2>
                    <p style="color: var(--text-muted); font-size: 13px;">O cartão de comanda só sai pela catraca com a conta paga. Comunicação via Agente Coletor.</p>
                </div>
                <div style="display:flex; gap:10px; align-items:center;">
                    <span id="agente-status" style="font-size: 12px; color: #ef4444; font-weight: 600;">● Agente Offline</span>
                    <button class="btn btn-primary" onclick="dispararSincronismo()">🔄 Sincronizar Agora</button>
                </div>
            </div>

            <div class="grid-container">
                <!-- Painel da Catraca -->
                <div class="card">
                    <div class="card-header">
                        <span>⚙️ Catraca / Coletor</span>
                        <button class="btn btn-sm btn-primary" onclick="salvarConfig()">Salvar</button>
                    </div>

                    <div class="form-group">
                        <label>Nome do Ponto de Acesso</label>
                        <input type="text" id="cat-nome" value="Catraca de Saída / Coletor">
                    </div>

                    <div class="row-form">
                        <div class="form-group">
                            <label>IP da Catraca</label>
                            <input type="text" id="cat-ip" value="192.168.13.102">
                        </div>
                        <div class="form-group">
                            <label>Porta</label>
                            <input type="text" id="cat-porta" value="3000">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Segundos de Liberação</label>
                        <input type="number" id="cat-segundos" value="7">
                    </div>

                    <div class="form-group" style="display:flex; align-items:center; gap:8px; margin-top:15px;">
                        <input type="checkbox" id="cat-ativa" checked style="width:auto;">
                        <label for="cat-ativa" style="margin:0; cursor:pointer;">Equipamento Ativo</label>
                    </div>

                    <div style="margin-top:20px; display:flex; gap:10px;">
                        <button class="btn btn-success" style="flex:1;" onclick="acionarManual(true)">🔓 Liberar Manual</button>
                        <button class="btn btn-danger" style="flex:1;" onclick="acionarManual(false)">⛔ Bloquear Manual</button>
                    </div>
                </div>

                <!-- Painel de Comandas -->
                <div class="card">
                    <div class="card-header">
                        <span>💳 Cartões - Comandas</span>
                        <span style="font-size:12px; color:var(--text-muted);">Comandas Ativas no Salão</span>
                    </div>

                    <table>
                        <thead>
                            <tr>
                                <th>Nº</th>
                                <th>Saldo / Consumo</th>
                                <th>Situação</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="tabela-comandas">
                            <!-- Preenchido via JS -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Passagens Recentes -->
            <div class="card logs-container">
                <div class="card-header">
                    <span>🕒 Passagens e Leituras Recentes</span>
                </div>
                <div id="lista-passagens">
                    <p style="color:var(--text-muted); font-size:12px;">Aguardando leituras de comandas...</p>
                </div>
            </div>
        </div>

        <script>
            const slug = "loja_beta";

            async function carregarDados() {
                try {
                    const resp = await fetch(`/api/status/${slug}`);
                    const dados = await resp.json();

                    // Status Agente
                    const statusSpan = document.getElementById("agente-status");
                    if (dados.agente_online) {
                        statusSpan.innerText = "● Agente Online (Conectado)";
                        statusSpan.style.color = "#10b981";
                    } else {
                        statusSpan.innerText = "● Agente Offline";
                        statusSpan.style.color = "#ef4444";
                    }

                    // Preenche Comandas
                    const tbody = document.getElementById("tabela-comandas");
                    tbody.innerHTML = "";
                    for (const [id, c] of Object.entries(dados.comandas)) {
                        const tr = document.createElement("tr");
                        const statusClass = c.status === "aberta" ? "status-aberta" : "status-livre";
                        const statusTxt = c.status === "aberta" ? `Bloqueado (R$ ${c.saldo.toFixed(2)})` : "Liberada (Paga/Livre)";
                        
                        tr.innerHTML = `
                            <td><strong>${id.padStart(2, '0')}</strong></td>
                            <td>R$ ${c.saldo.toFixed(2)} <span style="color:var(--text-muted); font-size:10px;">(${c.detalhes})</span></td>
                            <td><span class="status-badge ${statusClass}">${statusTxt}</span></td>
                            <td>
                                ${c.status === "aberta" 
                                    ? `<button class="btn btn-sm btn-success" onclick="pagarComanda('${id}')">Pagar</button>` 
                                    : `<button class="btn btn-sm btn-danger" onclick="abrirComanda('${id}')">Consumir</button>`
                                }
                            </td>
                        `;
                        tbody.appendChild(tr);
                    }

                    // Preenche Passagens
                    const logsContainer = document.getElementById("lista-passagens");
                    if (dados.passagens.length > 0) {
                        logsContainer.innerHTML = dados.passagens.map(p => `
                            <div class="log-item">
                                <span>Comanda: <strong>#${p.comanda}</strong> - ${p.resultado}</span>
                                <span style="color:var(--text-muted);">${p.hora}</span>
                            </div>
                        `).join('');
                    }
                } catch(e) {
                    console.error("Erro ao carregar dados", e);
                }
            }

            async function pagarComanda(id) {
                await fetch(`/api/comanda/${id}/pagar`, { method: "POST" });
                carregarDados();
            }

            async function abrirComanda(id) {
                await fetch(`/api/comanda/${id}/abrir`, { method: "POST" });
                carregarDados();
            }

            async function acionarManual(liberar) {
                await fetch(`/api/resposta-comanda/${slug}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        liberado: liberar,
                        mensagem: liberar ? "Acesso liberado Volte Sempre" : "Acesso Negado Valide no Caixa"
                    })
                });
            }

            setInterval(carregarDados, 2000);
            carregarDados();
        </script>
    </body>
    </html>
    """

# API para carregar status completo no Frontend
@app.get("/api/status/{slug}")
def get_status(slug: str):
    return {
        "agente_online": slug in agentes_conectados,
        "config": catracas_config.get(slug, {}),
        "comandas": comandas_db,
        "passagens": historico_passagens[-8:]  # Últimas 8 passagens
    }

# Rota para dar baixa/pagamento na comanda
@app.post("/api/comanda/{comanda_id}/pagar")
def pagar_comanda(comanda_id: str):
    if comanda_id in comandas_db:
        comandas_db[comanda_id]["saldo"] = 0.0
        comandas_db[comanda_id]["status"] = "livre"
        comandas_db[comanda_id]["detalhes"] = "Conta Paga"
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Comanda não encontrada")

# Rota para simular novo consumo
@app.post("/api/comanda/{comanda_id}/abrir")
def abrir_comanda(comanda_id: str):
    if comanda_id in comandas_db:
        comandas_db[comanda_id]["saldo"] = 15.00
        comandas_db[comanda_id]["status"] = "aberta"
        comandas_db[comanda_id]["detalhes"] = "1x Lanche"
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Comanda não encontrada")

# Rota WebSocket onde o agente se conecta
@app.websocket("/admin/api/system/ws/turnstile/{slug}")
async def websocket_endpoint(websocket: WebSocket, slug: str, agent_id: str = ""):
    await websocket.accept()
    agentes_conectados[slug] = websocket
    print(f"[WS] Agente conectado: {slug} ({agent_id})")

    try:
        while True:
            msg = await websocket.receive_text()
            dados = json.loads(msg)

            # Validação da Comanda vinda do Coletor
            if dados.get("evento") == "VALIDAR_COMANDA":
                comanda_raw = dados.get("comanda", "")
                
                # Trata números com zeros à esquerda (ex: 00000000000012651543 ou 00007 -> 7)
                try:
                    comanda_num = str(int(comanda_raw))
                except ValueError:
                    comanda_num = comanda_raw

                # Checa na base se a comanda tem consumo em aberto
                info = comandas_db.get(comanda_num, None)
                hora_str = time.strftime("%H:%M:%S")

                if info and info["status"] == "aberta" and info["saldo"] > 0:
                    # Bloqueia (Tem débito)
                    liberado = False
                    resposta_txt = "Acesso Negado Valide no Caixa"
                    historico_passagens.append({
                        "comanda": comanda_num,
                        "resultado": f"⛔ BLOQUEADO (Débito: R$ {info['saldo']:.2f})",
                        "hora": hora_str
                    })
                else:
                    # Libera (Paga ou Livre)
                    liberado = True
                    resposta_txt = "Acesso liberado Volte Sempre"
                    historico_passagens.append({
                        "comanda": comanda_num,
                        "resultado": "✅ LIBERADO (Conta Zerada)",
                        "hora": hora_str
                    })

                # Devolve o comando pro Agente disparar no Coletor
                await websocket.send_text(json.dumps({
                    "tipo": "RESPOSTA_COMANDA",
                    "liberado": liberado,
                    "mensagem": resposta_txt
                }))

    except WebSocketDisconnect:
        if slug in agentes_conectados:
            del agentes_conectados[slug]
        print(f"[WS] Agente desconectou: {slug}")

# Disparo manual do painel
@app.post("/api/resposta-comanda/{slug}")
async def resposta_manual(slug: str, dados: dict):
    if slug not in agentes_conectados:
        raise HTTPException(status_code=404, detail="Agente offline")

    ws = agentes_conectados[slug]
    await ws.send_text(json.dumps({
        "tipo": "RESPOSTA_COMANDA",
        "liberado": dados.get("liberado", False),
        "mensagem": dados.get("mensagem", "")
    }))
    return {"status": "ok"}
