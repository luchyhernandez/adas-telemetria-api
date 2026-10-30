import time
from typing import Optional, List
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="ADAS Telemetry & Config Server")

# ================= MODELOS DE DATOS =================

class EventoADAS(BaseModel):
    timestamp: int
    tipo_evento: str
    valor_medido: float
    alerta_activa: int
    bateria_pct: Optional[int] = 100

class ConfiguracionADAS(BaseModel):
    umbral_distraccion: float = Field(default=2.0, ge=0.0, le=10.0)  # Rango: 0 a 10 segundos
    tiempo_somnolencia: float = Field(default=1.5, ge=0.0, le=10.0)  # Rango: 0 a 10 segundos
    volumen_alerta: int = Field(default=90, ge=0, le=100)

# ================= ALMACENAMIENTO EN MEMORIA =================

eventos_db: List[dict] = []
configuracion_actual = {
    "umbral_distraccion": 2.0,
    "tiempo_somnolencia": 1.5,
    "volumen_alerta": 90
}
telemetria_actual = {
    "bateria_pct": 100,
    "ultimo_sync": 0,
    "ultimo_evento": "Ninguno",
    "valor_medido": 0.0,
    "alerta_activa": 0
}

# ================= ENDPOINTS DE LA API =================

@app.post("/api/v1/eventos")
def recibir_evento(evento: EventoADAS):
    data = evento.model_dump()
    eventos_db.append(data)
    
    if len(eventos_db) > 100:
        eventos_db.pop(0)

    telemetria_actual["bateria_pct"] = evento.bateria_pct if evento.bateria_pct is not None else 100
    telemetria_actual["ultimo_sync"] = int(time.time())
    telemetria_actual["ultimo_evento"] = evento.tipo_evento
    telemetria_actual["valor_medido"] = evento.valor_medido
    telemetria_actual["alerta_activa"] = evento.alerta_activa

    return {"status": "ok", "recibido": data}

@app.get("/api/v1/eventos")
def listar_eventos():
    return list(reversed(eventos_db))

@app.get("/api/v1/configuracion")
def obtener_configuracion():
    return configuracion_actual

@app.post("/api/v1/configuracion")
def actualizar_configuracion(cfg: ConfiguracionADAS):
    configuracion_actual["umbral_distraccion"] = round(cfg.umbral_distraccion, 2)
    configuracion_actual["tiempo_somnolencia"] = round(cfg.tiempo_somnolencia, 2)
    configuracion_actual["volumen_alerta"] = cfg.volumen_alerta
    return {"status": "ok", "configuracion": configuracion_actual}

@app.get("/api/v1/telemetria")
def obtener_telemetria():
    return telemetria_actual

# ================= DASHBOARD WEB INTEGRADO =================

@app.get("/", response_class=HTMLResponse)
def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Panel de Control ADAS</title>
        <style>
            * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background: #f0f2f5; margin: 0; padding: 24px; color: #1c1e21; }
            .container { max-width: 1000px; margin: 0 auto; }
            h1 { margin-bottom: 24px; font-size: 26px; }
            h2 { margin-top: 32px; font-size: 20px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
            .card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
            .card h3 { margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; color: #65676b; letter-spacing: 0.5px; }
            .metric { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
            .progress-bg { background: #e4e6eb; border-radius: 6px; height: 12px; width: 100%; overflow: hidden; }
            .progress-fill { height: 100%; width: 0%; transition: width 0.4s ease, background-color 0.4s ease; }
            .status-badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 12px; }
            .status-ok { background: #e7f3ff; color: #1877f2; }
            .status-alert { background: #ffebe8; color: #e41e3f; }
            
            .config-section { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 24px; }
            .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; align-items: end; }
            .form-group { display: flex; flex-direction: column; }
            .form-group label { font-size: 13px; font-weight: 600; color: #65676b; margin-bottom: 6px; }
            .form-group input { padding: 10px; border: 1px solid #ccd0d5; border-radius: 6px; font-size: 15px; outline: none; }
            .form-group input:focus { border-color: #1877f2; }
            .btn-save { background: #1877f2; color: white; border: none; padding: 12px 20px; border-radius: 6px; font-weight: 600; font-size: 15px; cursor: pointer; transition: background 0.2s; }
            .btn-save:hover { background: #166fe5; }
            .msg-success { color: #28a745; font-size: 14px; margin-top: 10px; display: none; }

            table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
            th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #f0f2f5; font-size: 14px; }
            th { background: #fafbfc; color: #65676b; font-weight: 600; }
            tr:hover { background: #f8f9fa; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Sistema ADAS - Telemetría y Configuración</h1>
            
            <div class="grid">
                <div class="card">
                    <h3>Batería TTGO (4G)</h3>
                    <div id="bat-val" class="metric">-- %</div>
                    <div class="progress-bg">
                        <div id="bat-bar" class="progress-fill" style="width: 0%; background: #28a745;"></div>
                    </div>
                </div>

                <div class="card">
                    <h3>Último Evento</h3>
                    <div id="evento-val" class="metric" style="font-size: 22px;">En espera...</div>
                    <span id="alerta-badge" class="status-badge status-ok">Sin alertas</span>
                </div>

                <div class="card">
                    <h3>Métrica (EAR)</h3>
                    <div id="metrica-val" class="metric">0.00</div>
                    <span style="font-size: 12px; color: #65676b;">Apertura Ocular</span>
                </div>

                <div class="card">
                    <h3>Último Sync</h3>
                    <div id="sync-val" class="metric" style="font-size: 20px;">--</div>
                    <span class="status-badge status-ok">Nube Online</span>
                </div>
            </div>

            <!-- PANEL DE CONFIGURACIÓN -->
            <div class="config-section">
                <h3 style="margin-top:0; font-size:16px;">Parámetros Temporales de Alerta (Rango 0 - 10 s)</h3>
                <form id="config-form" onsubmit="guardarConfiguracion(event)">
                    <div class="form-grid">
                        <div class="form-group">
                            <label for="cfg-distraccion">Tiempo Distracción (0.0 - 10.0 s)</label>
                            <input type="number" id="cfg-distraccion" step="0.1" min="0" max="10" required>
                        </div>
                        <div class="form-group">
                            <label for="cfg-somnolencia">Tiempo Somnolencia (0.0 - 10.0 s)</label>
                            <input type="number" id="cfg-somnolencia" step="0.1" min="0" max="10" required>
                        </div>
                        <div class="form-group">
                            <label for="cfg-volumen">Volumen Parlante (0 - 100)</label>
                            <input type="number" id="cfg-volumen" min="0" max="100" required>
                        </div>
                        <div class="form-group">
                            <button type="submit" class="btn-save">Guardar Parámetros</button>
                        </div>
                    </div>
                    <div id="msg-status" class="msg-success">Parámetros guardados correctamente.</div>
                </form>
            </div>

            <!-- HISTORIAL -->
            <h2>Historial de Detecciones</h2>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp (P4)</th>
                        <th>Tipo de Evento</th>
                        <th>Métrica</th>
                        <th>Alerta</th>
                        <th>Batería</th>
                    </tr>
                </thead>
                <tbody id="eventos-body">
                    <tr><td colspan="5" style="text-align: center; color: #888;">Cargando historial...</td></tr>
                </tbody>
            </table>
        </div>

        <script>
            async function cargarConfiguracion() {
                try {
                    const res = await fetch('/api/v1/configuracion');
                    const cfg = await res.json();
                    document.getElementById('cfg-distraccion').value = cfg.umbral_distraccion;
                    document.getElementById('cfg-somnolencia').value = cfg.tiempo_somnolencia;
                    document.getElementById('cfg-volumen').value = cfg.volumen_alerta;
                } catch (err) {
                    console.error("Error al cargar configuracion:", err);
                }
            }

            async function guardarConfiguracion(e) {
                e.preventDefault();
                const payload = {
                    umbral_distraccion: parseFloat(document.getElementById('cfg-distraccion').value),
                    tiempo_somnolencia: parseFloat(document.getElementById('cfg-somnolencia').value),
                    volumen_alerta: parseInt(document.getElementById('cfg-volumen').value)
                };

                try {
                    const res = await fetch('/api/v1/configuracion', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    if (res.ok) {
                        const msg = document.getElementById('msg-status');
                        msg.style.display = 'block';
                        setTimeout(() => { msg.style.display = 'none'; }, 4000);
                    }
                } catch (err) {
                    alert("Error al guardar configuración en el servidor");
                }
            }

            async function actualizarDashboard() {
                try {
                    const resTel = await fetch('/api/v1/telemetria');
                    const tel = await resTel.json();

                    const pct = tel.bateria_pct ?? 0;
                    document.getElementById('bat-val').innerText = pct + '%';
                    const bar = document.getElementById('bat-bar');
                    bar.style.width = pct + '%';
                    if (pct > 50) {
                        bar.style.backgroundColor = '#28a745';
                    } else if (pct > 20) {
                        bar.style.backgroundColor = '#ffc107';
                    } else {
                        bar.style.backgroundColor = '#dc3545';
                    }

                    document.getElementById('evento-val').innerText = tel.ultimo_evento;
                    document.getElementById('metrica-val').innerText = Number(tel.valor_medido).toFixed(2);
                    
                    const badgeAlerta = document.getElementById('alerta-badge');
                    if (tel.alerta_activa === 1) {
                        badgeAlerta.className = 'status-badge status-alert';
                        badgeAlerta.innerText = '¡ALERTA ACTIVA!';
                    } else {
                        badgeAlerta.className = 'status-badge status-ok';
                        badgeAlerta.innerText = 'Normal';
                    }

                    if (tel.ultimo_sync > 0) {
                        const date = new Date(tel.ultimo_sync * 1000);
                        document.getElementById('sync-val').innerText = date.toLocaleTimeString();
                    }

                    const resEvt = await fetch('/api/v1/eventos');
                    const eventos = await resEvt.json();
                    const tbody = document.getElementById('eventos-body');
                    
                    if (eventos.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #888;">No hay eventos registrados aún.</td></tr>';
                    } else {
                        tbody.innerHTML = eventos.map(e => `
                            <tr>
                                <td>${e.timestamp}</td>
                                <td><b>${e.tipo_evento}</b></td>
                                <td>${Number(e.valor_medido).toFixed(2)}</td>
                                <td>${e.alerta_activa === 1 ? '<span style="color:red; font-weight:bold;">SI</span>' : 'NO'}</td>
                                <td>${e.bateria_pct !== undefined ? e.bateria_pct + '%' : 'N/A'}</td>
                            </tr>
                        `).join('');
                    }

                } catch (err) {
                    console.error("Error al actualizar dashboard:", err);
                }
            }

            cargarConfiguracion();
            setInterval(actualizarDashboard, 3000);
            actualizarDashboard();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)