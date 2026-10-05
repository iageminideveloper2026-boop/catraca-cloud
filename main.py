import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="ALIV SaaS - Gestão Completa (Cardápio, Pedidos e Catraca)")

# Conexões WebSocket ativas {slug: websocket}
agentes_conectados = {}

# Banco de dados em memória
cardapio_db = [
    {"id": 1, "nome": "Esfiha de Atum", "categoria": "Salgados", "preco": 8.80},
    {"id": 2, "nome": "Esfiha de Atum c/ Catupiry", "categoria": "Salgados", "preco": 11.00},
    {"id": 3, "nome": "Esfiha de Atum c/ Queijo", "categoria": "Salgados", "preco": 12.00},
    {"id": 4, "nome": "Esfiha de Bauru", "categoria": "Salgados", "preco": 7.70},
    {"id": 5, "nome": "Pizza Grande (8 Fatias)", "categoria": "Pizzas", "preco": 55.00},
    {"id": 6, "nome": "Pizza Broto (4 Fatias)", "categoria": "Pizzas", "preco": 32.00},
    {"id": 7, "nome": "Água Mineral 510ml c/ Gás", "categoria": "Bebidas", "preco": 6.50},
    {"id": 8, "nome": "Refrigerante Lata 350ml", "categoria": "Bebidas", "preco": 7.00}
]

# Inicializa comandas de 1 a 20 (baseado na tela)
comandas_db = {}
for i in range(1, 21):
    comandas_db[str(i)] = {
        "numero": str(i),
        "status": "livre",
        "total": 0.0,
        "itens": [],
        "abertura": None
    }

# Popula alguns dados de exemplo idênticos à tela
comandas_db["1"] = {"numero": "1", "status": "aberta", "total": 8.80, "itens": ["1x Esfiha de Atum"], "abertura": "14:10"}
comandas_db["2"] = {"numero": "2", "status": "aberta", "total": 11.00, "itens": ["1x Esfiha de Atum c/ Catupiry"], "abertura": "15:20"}
comandas_db["3"] = {"numero": "3", "status": "aberta", "total": 25.85, "itens": ["2x Esfiha de Atum c/ Queijo", "1x Água Mineral"], "abertura": "14:35"}
comandas_db["4"] = {"numero": "4", "status": "aberta", "total": 7.70, "itens": ["1x Esfiha de Bauru"], "abertura": "15:00"}
comandas_db["5"] = {"numero": "5", "status": "aberta", "total": 68.74, "itens": ["1x Pizza Grande", "1x Água Mineral"], "abertura": "13:40"}
comandas_db["6"] = {"numero": "6", "status": "aberta", "total": 8.80, "itens": ["1x Esfiha de Atum"], "abertura": "15:15"}
comandas_db["8"] = {"numero": "8", "status": "aberta", "total": 11.00, "itens": ["Mesa 12 - Vitor"], "abertura": "14:50"}
comandas_db["9"] = {"numero": "9", "status": "aberta", "total": 11.00, "itens": ["Mesa 12 - Guilherme"], "abertura": "14:55"}
comandas_db["10"] = {"numero": "10", "status": "aberta", "total": 756.71, "itens": ["1x Pizza Broto", "1x Pizza Grande"], "abertura": "12:10"}

historico_passagens = []

class ProdutoItem(BaseModel):
    nome: str
    categoria: str
    preco: float

class AdicionarItemComanda(BaseModel):
    produto_id: int
    quantidade: int = 1

@app.get("/", response_class=HTMLResponse)
def painel_principal():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>ALIV SaaS - Gestão de Pedidos & Catraca</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            :root {
                --bg-body: #0d1322;
                --bg-sidebar: #0a0f1d;
                --bg-card: #151d30;
                --bg-card-livre: #172138;
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
            .sidebar { width: 230px; background: var(--bg-sidebar); border-right: 1px solid var(--border-color); padding: 20px 15px; display: flex; flex-direction: column; gap: 8px; }
            .logo { font-size: 20px; font-weight: bold; color: var(--primary); display: flex; align-items: center; gap: 8px; margin-bottom: 25px; }
            .menu-item { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-radius: 8px; color: var(--text-muted); cursor: pointer; text-decoration: none; font-size: 14px; font-weight: 500; transition: 0.2s; }
            .menu-item.active, .menu-item:hover { background: #1e293b; color: white; }

            /* Conteúdo Principal */
            .main { flex: 1; padding: 25px; overflow-y: auto; }
            .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .badge-beta { background: #374151; font-size: 11px; padding: 3px 8px; border-radius: 4px; color: #60a5fa; font-weight: bold; }

            /* Botões e Inputs */
            .btn { border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: 0.2s; }
            .btn-primary { background: var(--primary); color: white; }
            .btn-success { background: var(--success); color: white; }
            .btn-danger { background: var(--danger); color: white; }
            .btn-sm { padding: 4px 8px; font-size: 11px; }
            input, select { background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 10px; color: white; font-size: 13px; }

            /* Abas */
            .tab-content { display: none; }
            .tab-content.active { display: block; }

            /* Grid de Comandas (Visual igual à imagem) */
            .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 16px; margin-top: 15px; }
            .card-comanda { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; min-height: 140px; cursor: pointer; transition: transform 0.15s, border-color 0.15s; }
            .card-comanda:hover { transform: translateY(-2px); border-color: var(--primary); }
            .card-comanda.livre { background: var(--bg-card-livre); border-style: dashed; }
            .card-header-comanda { display: flex; justify-content: space-between; align-items: center; font-size: 12px; font-weight: bold; }
            .card-valor { font-size: 20px; font-weight: bold; margin: 10px 0 4px 0; color: #fff; }
            .card-detalhes { font-size: 11px; color: var(--text-muted); line-height: 1.3; max-height: 32px; overflow: hidden; text-overflow: ellipsis; }

            /* Tabelas */
            table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
            th { text-align: left; padding: 10px; color: var(--text-muted); border-bottom: 1px solid var(--border-color); font-weight: 600; }
            td { padding: 10px; border-bottom: 1px solid var(--border-color); }
            .card-container { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 20px; }

            /* Modal */
            .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: none; justify-content: center; align-items: center; z-index: 1000; }
            .modal-box { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; width: 440px; padding: 20px; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo">🚀 ALIV <span>SaaS</span></div>
            <a class="menu-item" onclick="trocarAba('pedidos')">📦 Pedidos / Comandas</a>
            <a class="menu-item" onclick="trocarAba('cardapio')">🍽️ Cardápio & Produtos</a>
            <a class="menu-item active" onclick="trocarAba('catraca')">🛡️ Catraca EVO</a>
        </div>

        <div class="main">
            <!-- ABA 1: PEDIDOS / COMANDAS -->
            <div id="aba-pedidos" class="tab-content">
                <div class="top-bar">
                    <div>
                        <h2>Quadro de Comandas</h2>
                        <p style="color: var(--text-muted); font-size: 13px;">Selecione uma comanda para lançar produtos ou efetuar o pagamento.</p>
                    </div>
                </div>
                <div class="cards-grid" id="grid-comandas">
                    <!-- Cards de Comandas Gerados Via JavaScript -->
                </div>
            </div>

            <!-- ABA 2: CARDÁPIO / PRODUTOS -->
            <div id="aba-cardapio" class="tab-content">
                <div class="top-bar">
                    <div>
                        <h2>Cardápio e Produtos</h2>
                        <p style="color: var(--text-muted); font-size: 13px;">Cadastre os produtos que poderão ser lançados nas comandas.</p>
                    </div>
                    <button class="btn btn-primary" onclick="abrirModalProduto()">+ Novo Produto</button>
                </div>
                <div class="card-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Nome do Produto</th>
                                <th>Categoria</th>
                                <th>Preço (R$)</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="tabela-produtos">
                            <!-- Preenchido via JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- ABA 3: CATRACA EVO -->
            <div id="aba-catraca" class="tab-content active">
                <div class="top-bar">
                    <div>
                        <h2>Catraca EVO <span class="badge-beta">BETA</span></h2>
                        <p style="color: var(--text-muted); font-size: 13px;">O cartão de comanda só é liberado pelo coletor caso esteja com a conta paga.</p>
                    </div>
                    <span id="agente-status" style="font-size: 12px; color: #ef4444; font-weight: 600;">● Agente Offline</span>
                </div>

                <div class="card-container" style="display: grid; grid-template-columns: 1fr 1.3fr; gap: 20px;">
                    <div>
                        <h3 style="margin-bottom: 15px;">⚙️ Configuração da Catraca</h3>
                        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 8px;">IP: <strong>192.168.13.102</strong> | Porta: <strong>3000</strong></p>
                        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 20px;">Tempo de Abertura: <strong>7 segundos</strong></p>
                        
                        <div style="display:flex; gap: 10px;">
                            <button class="btn btn-success" style="flex:1;" onclick="acionarManual(true)">🔓 Liberar Manual</button>
                            <button class="btn btn-danger" style="flex:1;" onclick="acionarManual(false)">⛔ Bloquear Manual</button>
                        </div>
                    </div>

                    <div>
                        <h3 style="margin-bottom: 15px;">🕒 Passagens e Leituras Recentes</h3>
                        <div id="lista-passagens" style="max-height: 250px; overflow-y:auto; font-size: 12px;">
                            <p style="color:var(--text-muted);">Aguardando leituras de comandas no cofre...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL: DETALHES / LANÇAMENTO DE COMANDA -->
        <div id="modal-comanda" class="modal-overlay">
            <div class="modal-box">
                <h3 id="modal-comanda-titulo" style="margin-bottom: 10px;">Comanda</h3>
                <p id="modal-comanda-status" style="font-size: 13px; color: var(--text-muted); margin-bottom: 15px;"></p>
                
                <div style="margin-bottom: 15px;">
                    <label>Lançar Produto na Comanda:</label>
                    <div style="display: flex; gap: 8px;">
                        <select id="select-produtos" style="flex: 1;"></select>
                        <button class="btn btn-primary" onclick="lancarProdutoComanda()">Adicionar</button>
                    </div>
                </div>

                <div style="max-height: 150px; overflow-y: auto; margin-bottom: 15px; border-bottom: 1px solid var(--border-color); padding-bottom: 10px;" id="modal-comanda-itens">
                </div>

                <div style="display:flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <span>Total a Pagar:</span>
                    <strong style="font-size: 18px; color: #10b981;" id="modal-comanda-total">R$ 0,00</strong>
                </div>

                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-success" style="flex: 1;" onclick="pagarComandaModal()">Pagar / Liberar Saída</button>
                    <button class="btn btn-danger" onclick="fecharModais()">Fechar</button>
                </div>
            </div>
        </div>

        <!-- MODAL: NOVO PRODUTO -->
        <div id="modal-produto" class="modal-overlay">
            <div class="modal-box">
                <h3 style="margin-bottom: 15px;">Cadastrar Produto</h3>
                <div style="margin-bottom: 10px;">
                    <label>Nome do Produto:</label>
                    <input type="text" id="prod-nome" placeholder="Ex: Pizza Calabresa">
                </div>
                <div style="margin-bottom: 10px;">
                    <label>Categoria:</label>
                    <input type="text" id="prod-categoria" placeholder="Ex: Pizzas, Bebidas">
                </div>
                <div style="margin-bottom: 15px;">
                    <label>Preço (R$):</label>
                    <input type="number" step="0.01" id="prod-preco" placeholder="0.00">
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-primary" style="flex: 1;" onclick="salvarProduto()">Salvar Produto</button>
                    <button class="btn btn-danger" onclick="fecharModais()">Cancelar</button>
                </div>
            </div>
        </div>

        <script>
            let comandaSelecionada = null;

            function trocarAba(aba) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));

                document.getElementById(`aba-${aba}`).classList.add('active');
                event.target.classList.add('active');
            }

            async function carregarDados() {
                try {
                    // Carrega Status e Comandas
                    const resp = await fetch('/api/status/loja_beta');
                    const dados = await resp.json();

                    // Status do Agente
                    const statusSpan = document.getElementById("agente-status");
                    if (dados.agente_online) {
                        statusSpan.innerText = "● Agente Online (Conectado)";
                        statusSpan.style.color = "#10b981";
                    } else {
                        statusSpan.innerText = "● Agente Offline";
                        statusSpan.style.color = "#ef4444";
                    }

                    // Renderiza Grid de Comandas
                    const grid = document.getElementById("grid-comandas");
                    grid.innerHTML = "";

                    for (const [id, c] of Object.entries(dados.comandas)) {
                        const div = document.createElement("div");
                        const isLivre = c.status === "livre";
                        div.className = `card-comanda ${isLivre ? 'livre' : ''}`;
                        div.onclick = () => abrirModalComanda(id);

                        div.innerHTML = `
                            <div>
                                <div class="card-header-comanda">
                                    <span>COMANDA ${id}</span>
                                    <span style="color: ${isLivre ? '#9ca3af' : '#10b981'}">${isLivre ? 'LIVRE' : (c.abertura || 'Ativa')}</span>
                                </div>
                                <div class="card-valor">${isLivre ? 'Livre' : `R$ ${c.total.toFixed(2)}`}</div>
                                <div class="card-detalhes">${isLivre ? 'Sem consumo registrado' : c.itens.join(', ')}</div>
                            </div>
                            <div style="margin-top: 10px; font-size: 11px; color: ${isLivre ? '#34d399' : '#f87171'}; font-weight: bold;">
                                ${isLivre ? '● Pronta p/ uso' : '● Em atendimento'}
                            </div>
                        `;
                        grid.appendChild(div);
                    }

                    // Renderiza Passagens
                    const logsDiv = document.getElementById("lista-passagens");
                    if (dados.passagens.length > 0) {
                        logsDiv.innerHTML = dados.passagens.map(p => `
                            <div style="padding: 6px 0; border-bottom: 1px solid var(--border-color); display:flex; justify-content:space-between;">
                                <span>Comanda: <strong>#${p.comanda}</strong> - ${p.resultado}</span>
                                <span style="color:var(--text-muted);">${p.hora}</span>
                            </div>
                        `).join('');
                    }

                } catch(e) {
                    console.error("Erro ao atualizar dados:", e);
                }
            }

            async function carregarCardapio() {
                const resp = await fetch('/api/cardapio');
                const prods = await resp.json();

                // Tabela
                const tbody = document.getElementById("tabela-produtos");
                tbody.innerHTML = "";
                prods.forEach(p => {
                    tbody.innerHTML += `
                        <tr>
                            <td>#${p.id}</td>
                            <td><strong>${p.nome}</strong></td>
                            <td>${p.categoria}</td>
                            <td>R$ ${p.preco.toFixed(2)}</td>
                            <td><button class="btn btn-sm btn-danger" onclick="excluirProduto(${p.id})">Excluir</button></td>
                        </tr>
                    `;
                });

                // Select do Modal
                const sel = document.getElementById("select-produtos");
                sel.innerHTML = prods.map(p => `<option value="${p.id}">${p.nome} - R$ ${p.preco.toFixed(2)}</option>`).join('');
            }

            async function abrirModalComanda(id) {
                comandaSelecionada = id;
                const resp = await fetch(`/api/comanda/${id}`);
                const c = await resp.json();

                document.getElementById("modal-comanda-titulo").innerText = `Comanda #${id}`;
                document.getElementById("modal-comanda-status").innerText = c.status === "livre" ? "Status: LIVRE" : `Status: ABERTA (Abertura: ${c.abertura || 'N/A'})`;
                document.getElementById("modal-comanda-total").innerText = `R$ ${c.total.toFixed(2)}`;

                const itensDiv = document.getElementById("modal-comanda-itens");
                itensDiv.innerHTML = c.itens.length > 0 
                    ? c.itens.map(i => `<p style="font-size:12px; margin: 3px 0;">• ${i}</p>`).join('')
                    : `<p style="font-size:12px; color:var(--text-muted);">Nenhum item lançado ainda.</p>`;

                document.getElementById("modal-comanda").style.display = "flex";
            }

            async function lancarProdutoComanda() {
                const prodId = document.getElementById("select-produtos").value;
                await fetch(`/api/comanda/${comandaSelecionada}/lancar`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ produto_id: parseInt(prodId), quantidade: 1 })
                });
                abrirModalComanda(comandaSelecionada);
                carregarDados();
            }

            async function pagarComandaModal() {
                await fetch(`/api/comanda/${comandaSelecionada}/pagar`, { method: "POST" });
                fecharModais();
                carregarDados();
            }

            function abrirModalProduto() {
                document.getElementById("modal-produto").style.display = "flex";
            }

            async function salvarProduto() {
                const nome = document.getElementById("prod-nome").value;
                const categoria = document.getElementById("prod-categoria").value;
                const preco = parseFloat(document.getElementById("prod-preco").value);

                if (!nome || isNaN(preco)) return alert("Preencha os campos corretamente.");

                await fetch('/api/cardapio', {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ nome, categoria, preco })
                });

                fecharModais();
                carregarCardapio();
            }

            async function excluirProduto(id) {
                await fetch(`/api/cardapio/${id}`, { method: "DELETE" });
                carregarCardapio();
            }

            async function acionarManual(liberar) {
                await fetch(`/api/resposta-comanda/loja_beta`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        liberado: liberar,
                        mensagem: liberar ? "Acesso liberado Volte Sempre" : "Acesso Negado Valide no Caixa"
                    })
                });
            }

            function fecharModais() {
                document.querySelectorAll('.modal-overlay').forEach(el => el.style.display = "none");
            }

            setInterval(carregarDados, 2000);
            carregarDados();
            carregarCardapio();
        </script>
    </body>
    </html>
    """

# ==========================================
# ENDPOINTS REST: CARDÁPIO & PRODUTOS
# ==========================================
@app.get("/api/cardapio")
def listar_produtos():
    return cardapio_db

@app.post("/api/cardapio")
def adicionar_produto(produto: ProdutoItem):
    novo_id = len(cardapio_db) + 1
    item = {"id": novo_id, "nome": produto.nome, "categoria": produto.categoria, "preco": produto.preco}
    cardapio_db.append(item)
    return item

@app.delete("/api/cardapio/{produto_id}")
def excluir_produto(produto_id: int):
    global cardapio_db
    cardapio_db = [p for p in cardapio_db if p["id"] != produto_id]
    return {"status": "ok"}

# ==========================================
# ENDPOINTS REST: COMANDAS & PEDIDOS
# ==========================================
@app.get("/api/comanda/{comanda_id}")
def obter_comanda(comanda_id: str):
    if comanda_id in comandas_db:
        return comandas_db[comanda_id]
    raise HTTPException(status_code=404, detail="Comanda não encontrada")

@app.post("/api/comanda/{comanda_id}/lancar")
def lancar_item(comanda_id: str, dados: AdicionarItemComanda):
    if comanda_id not in comandas_db:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    produto = next((p for p in cardapio_db if p["id"] == dados.produto_id), None)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    c = comandas_db[comanda_id]
    c["status"] = "aberta"
    c["total"] += (produto["preco"] * dados.quantidade)
    c["itens"].append(f"{dados.quantidade}x {produto['nome']}")
    if not c["abertura"]:
        c["abertura"] = time.strftime("%H:%M")
    return c

@app.post("/api/comanda/{comanda_id}/pagar")
def pagar_comanda(comanda_id: str):
    if comanda_id in comandas_db:
        c = comandas_db[comanda_id]
        c["status"] = "livre"
        c["total"] = 0.0
        c["itens"] = []
        c["abertura"] = None
        return {"status": "ok", "mensagem": "Comanda quitada com sucesso"}
    raise HTTPException(status_code=404, detail="Comanda não encontrada")

# ==========================================
# ENDPOINTS REST: CATRACA & STATUS
# ==========================================
@app.get("/api/status/{slug}")
def get_status(slug: str):
    return {
        "agente_online": slug in agentes_conectados,
        "comandas": comandas_db,
        "passagens": historico_passagens[-8:]
    }

# ==========================================
# WEBSOCKET: COMUNICAÇÃO COM O COLETOR (REON)
# ==========================================
@app.websocket("/admin/api/system/ws/turnstile/{slug}")
async def websocket_endpoint(websocket: WebSocket, slug: str, agent_id: str = ""):
    await websocket.accept()
    agentes_conectados[slug] = websocket
    print(f"[WS] Agente conectado: {slug} (Agent ID: {agent_id})")

    try:
        while True:
            msg_texto = await websocket.receive_text()
            dados = json.loads(msg_texto)

            # Evento vindo do agente ao depositar comanda no cofre
            if dados.get("evento") == "VALIDAR_COMANDA":
                comanda_raw = dados.get("comanda", "")
                
                # Trata zeros à esquerda (ex: 00000000000012651543 ou 00005 -> 5)
                try:
                    comanda_num = str(int(comanda_raw))
                except ValueError:
                    comanda_num = comanda_raw

                info = comandas_db.get(comanda_num, None)
                hora_str = time.strftime("%H:%M:%S")

                # Regra: se existir e estiver aberta com débito -> Bloqueia
                if info and info["status"] == "aberta" and info["total"] > 0:
                    liberado = False
                    resposta_txt = "Acesso Negado Valide no Caixa"
                    historico_passagens.append({
                        "comanda": comanda_num,
                        "resultado": f"⛔ BLOQUEADO (Débito: R$ {info['total']:.2f})",
                        "hora": hora_str
                    })
                else:
                    # Se não tem débito ou está livre -> Libera e engole comanda
                    liberado = True
                    resposta_txt = "Acesso liberado Volte Sempre"
                    historico_passagens.append({
                        "comanda": comanda_num,
                        "resultado": "✅ LIBERADO (Conta Paga)",
                        "hora": hora_str
                    })

                # Devolve a ordem para o Agente despachar o comando REON
                await websocket.send_text(json.dumps({
                    "tipo": "RESPOSTA_COMANDA",
                    "liberado": liberado,
                    "mensagem": resposta_txt
                }))

    except WebSocketDisconnect:
        if slug in agentes_conectados:
            del agentes_conectados[slug]
        print(f"[WS] Agente desconectou: {slug}")

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
