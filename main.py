import time
from typing import Optional, List
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="ADAS Telemetry Server")
app.mount("/static", StaticFiles(directory="static"), name="static")

class EventoADAS(BaseModel):
    # Formato enviado por la TTGO (evento original de la ESP32-P4)
    event_id: Optional[int] = None
    uptime_ms: Optional[int] = None
    event_type: Optional[str] = None
    duration_ms: Optional[int] = None
    head_x: Optional[float] = None
    head_y: Optional[float] = None
    alert_sent: Optional[int] = None
    bateria_pct: Optional[int] = None
    # Campos heredados, para aceptar equipos/versiones anteriores
    timestamp: Optional[int] = None
    tipo_evento: Optional[str] = None
    valor_medido: Optional[float] = None
    alerta_activa: Optional[int] = None

class ConfiguracionADAS(BaseModel):
    umbral_distraccion: float = Field(default=2.0, ge=0.0, le=10.0)
    tiempo_somnolencia: float = Field(default=1.5, ge=0.0, le=10.0)
    volumen_alerta: int = Field(default=90, ge=0, le=100)

# Almacenamiento en memoria (se conserva el comportamiento actual del servidor).
eventos_db: List[dict] = []
configuracion_actual = {
    "umbral_distraccion": 2.0,
    "tiempo_somnolencia": 1.5,
    "volumen_alerta": 90,
}
telemetria_actual = {
    "bateria_pct": None,
    "ultimo_sync": 0,
    "ultimo_evento": "Ninguno",
    "valor_medido": None,
    "alerta_activa": 0,
    "event_id": None,
    "uptime_ms": None,
    "duration_ms": None,
    "head_x": None,
    "head_y": None,
}

@app.post("/api/v1/eventos")
def recibir_evento(evento: EventoADAS):
    recibido = evento.model_dump(exclude_none=True)
    tipo = evento.event_type or evento.tipo_evento
    if not tipo:
        return {"status": "error", "detalle": "Falta event_type/tipo_evento"}

    # Compatibilidad: se guardan los campos originales y los alias que usa el dashboard.
    data = dict(recibido)
    data["timestamp"] = int(time.time())  # hora de recepción en Render
    data["tipo_evento"] = tipo
    data["alerta_activa"] = int(
        evento.alert_sent if evento.alert_sent is not None
        else (evento.alerta_activa or 0)
    )
    # No se inventa una magnitud: valor_medido queda solo si llegó el campo antiguo.
    if evento.valor_medido is not None:
        data["valor_medido"] = evento.valor_medido

    eventos_db.append(data)
    if len(eventos_db) > 100:
        eventos_db.pop(0)

    telemetria_actual.update({
        "bateria_pct": evento.bateria_pct,
        "ultimo_sync": int(time.time()),
        "ultimo_evento": tipo,
        "valor_medido": evento.valor_medido,
        "alerta_activa": data["alerta_activa"],
        "event_id": evento.event_id,
        "uptime_ms": evento.uptime_ms,
        "duration_ms": evento.duration_ms,
        "head_x": evento.head_x,
        "head_y": evento.head_y,
    })
    return {"status": "ok", "recibido": data}

@app.get("/api/v1/eventos")
def listar_eventos():
    return list(reversed(eventos_db))

@app.get("/api/v1/configuracion")
def obtener_configuracion():
    return configuracion_actual

@app.get("/api/v1/telemetria")
def obtener_telemetria():
    return telemetria_actual

@app.get("/", response_class=HTMLResponse)
def index():
    html_content = r'''<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#071426"><title>ADAS | Centro de monitoreo</title>
<style>
:root{--bg:#071426;--panel:#0d2038;--line:rgba(148,183,218,.16);--text:#edf5ff;--muted:#91a8c2;--cyan:#35d4e8;--green:#38d996;--yellow:#ffc857;--red:#ff637d}
*{box-sizing:border-box}body{margin:0;color:var(--text);font-family:Inter,"Segoe UI",Arial,sans-serif;background:radial-gradient(circle at 85% 0%,rgba(24,111,183,.22),transparent 30%),radial-gradient(circle at 0% 35%,rgba(31,183,201,.10),transparent 28%),var(--bg);min-height:100vh}
.shell{max-width:1400px;margin:auto;padding:28px 24px 42px}header{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:4px 0 24px;border-bottom:1px solid var(--line);flex-wrap:wrap}.brand{display:flex;align-items:center;gap:15px}.brand-mark{width:58px;height:58px;border-radius:15px;display:grid;place-items:center;background:linear-gradient(145deg,#0e70ba,#092c55);border:1px solid rgba(76,204,237,.5);font-weight:900;font-size:21px}.brand-name{font-size:12px;color:var(--cyan);letter-spacing:2px;font-weight:800}.brand-sub{color:var(--muted);font-size:12px;margin-top:5px}h1{margin:5px 0 0;font-size:clamp(22px,3vw,30px)}.pill{display:inline-flex;align-items:center;gap:8px;padding:9px 13px;border:1px solid var(--line);background:rgba(13,32,56,.8);border-radius:30px;color:var(--muted);font-size:12px}.dot{width:8px;height:8px;border-radius:50%;background:var(--yellow)}.dot.online{background:var(--green);box-shadow:0 0 10px var(--green)}
.section-title{margin:28px 0 14px;display:flex;justify-content:space-between;align-items:end;gap:12px;flex-wrap:wrap}.section-title h2{font-size:16px;margin:0}.section-title span{color:var(--muted);font-size:12px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.card{background:linear-gradient(150deg,rgba(16,41,67,.96),rgba(10,27,48,.96));border:1px solid var(--line);border-radius:16px;padding:19px;min-width:0}.card-label{color:var(--muted);text-transform:uppercase;font-size:10px;letter-spacing:1.3px;font-weight:800}.metric{font-size:29px;font-weight:750;margin:13px 0 8px;overflow-wrap:anywhere}.metric.small{font-size:21px}.sub{color:var(--muted);font-size:12px}.bar{height:7px;background:#1b3550;border-radius:10px;margin-top:15px;overflow:hidden}.bar-fill{height:100%;width:0;border-radius:10px}.status{display:inline-flex;align-items:center;gap:7px;border-radius:20px;padding:6px 10px;font-size:11px;font-weight:700;background:rgba(56,217,150,.12);color:var(--green)}.status.warn{background:rgba(255,200,87,.12);color:var(--yellow)}.status.bad{background:rgba(255,99,125,.12);color:var(--red)}.params{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.param-value{font-size:28px;font-weight:750;margin:15px 0 5px}.readonly{display:inline-block;font-size:10px;color:var(--cyan);border:1px solid rgba(53,212,232,.25);padding:5px 8px;border-radius:20px}.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:15px;background:rgba(13,32,56,.85)}table{width:100%;border-collapse:collapse;min-width:1050px}th,td{text-align:left;padding:13px 14px;border-bottom:1px solid var(--line);font-size:12px;white-space:nowrap}th{color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-size:10px}td{color:#dceaff}tr:last-child td{border-bottom:0}.event-tag{color:var(--cyan);font-weight:800}.empty{text-align:center;color:var(--muted);padding:28px}footer{margin-top:25px;color:#6f88a4;font-size:11px;text-align:center}@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.shell{padding:18px 14px 30px}.grid{grid-template-columns:1fr 1fr;gap:9px}.card{padding:14px}.metric{font-size:23px}.params{grid-template-columns:1fr}}
</style></head><body><div class="shell">
<header><div class="brand"><div class="brand-mark">UTN</div><div><div class="brand-name">UNIVERSIDAD TECNOLÓGICA NACIONAL</div><h1>ADAS · Centro de monitoreo</h1><div class="brand-sub">Sistema de asistencia y supervisión del conductor</div></div></div><div class="pill"><span id="cloud-dot" class="dot"></span><span id="cloud-status">Verificando servidor</span></div></header>
<div class="section-title"><h2>Estado del sistema</h2><span>Información recibida desde la unidad telemática</span></div>
<section class="grid">
<div class="card"><div class="card-label">Batería TTGO · 4G</div><div class="metric" id="bat-val">--</div><div class="sub" id="bat-note">Esperando medición real</div><div class="bar"><div class="bar-fill" id="bat-bar"></div></div></div>
<div class="card"><div class="card-label">Último evento detectado</div><div class="metric small" id="evento-val">En espera</div><span id="alerta-badge" class="status warn">Sin datos</span></div>
<div class="card"><div class="card-label">Última comunicación</div><div class="metric small" id="sync-val">--</div><div class="sub" id="sync-note">Esperando telemetría</div></div>
<div class="card"><div class="card-label">Eventos almacenados</div><div class="metric" id="count-val">--</div><div class="sub">Registros disponibles en memoria del servidor</div></div>
</section>
<div class="section-title"><h2>Parámetros temporales</h2><span>Valores informativos · Solo lectura</span></div><section class="params">
<div class="card"><div class="card-label">Tiempo de distracción</div><div class="param-value" id="cfg-distraccion">-- s</div><span class="readonly">SOLO LECTURA</span></div>
<div class="card"><div class="card-label">Tiempo de somnolencia</div><div class="param-value" id="cfg-somnolencia">-- s</div><span class="readonly">No implementado en esta versión</span></div></section>
<div class="section-title"><h2>Historial de eventos</h2><span>Datos originales recibidos desde la ESP32-P4</span></div>
<div class="table-wrap"><table><thead><tr><th>ID evento</th><th>Recepción Render</th><th>Uptime P4 (ms)</th><th>Tipo</th><th>Duración (ms)</th><th>Head X</th><th>Head Y</th><th>Alerta enviada</th><th>Batería TTGO</th></tr></thead><tbody id="eventos-body"><tr><td colspan="9" class="empty">Cargando historial...</td></tr></tbody></table></div>
<footer>PROYECTO ADAS · UNIVERSIDAD TECNOLÓGICA NACIONAL · PANEL DE TELEMETRÍA</footer></div>
<script>
const fmt=v=>(v!==null&&v!==undefined&&Number.isFinite(Number(v)))?Number(v).toFixed(3):'--';
async function cargarConfiguracion(){try{const r=await fetch('/api/v1/configuracion',{cache:'no-store'});if(!r.ok)throw Error();const c=await r.json();document.getElementById('cfg-distraccion').textContent=Number(c.umbral_distraccion).toFixed(2)+' s';document.getElementById('cfg-somnolencia').textContent=Number(c.tiempo_somnolencia).toFixed(2)+' s';}catch(e){console.error(e)}}
async function actualizarDashboard(){const dot=document.getElementById('cloud-dot'),cloud=document.getElementById('cloud-status');try{const [tr,er]=await Promise.all([fetch('/api/v1/telemetria',{cache:'no-store'}),fetch('/api/v1/eventos',{cache:'no-store'})]);if(!tr.ok||!er.ok)throw Error('API no disponible');const t=await tr.json(),ev=await er.json();dot.className='dot online';cloud.textContent='Servidor conectado';const p=t.bateria_pct,bat=document.getElementById('bat-val'),bar=document.getElementById('bat-bar');if(p!==null&&p!==undefined){const n=Math.max(0,Math.min(100,Number(p)));bat.textContent=n+'%';bar.style.width=n+'%';bar.style.background=n>50?'linear-gradient(90deg,#35d4e8,#38d996)':n>20?'#ffc857':'#ff637d';document.getElementById('bat-note').textContent='Último valor informado por la TTGO';}else{bat.textContent='N/D';bar.style.width='0%';document.getElementById('bat-note').textContent='Medición no disponible';}
document.getElementById('evento-val').textContent=t.ultimo_evento||'Ninguno';const b=document.getElementById('alerta-badge');if(Number(t.alerta_activa)===1){b.className='status bad';b.textContent='ALERTA ENVIADA';}else{b.className='status';b.textContent='Sin alerta enviada';}
if(Number(t.ultimo_sync)>0){const d=new Date(Number(t.ultimo_sync)*1000);document.getElementById('sync-val').textContent=d.toLocaleTimeString();document.getElementById('sync-note').textContent=d.toLocaleDateString();}else{document.getElementById('sync-val').textContent='--';}document.getElementById('count-val').textContent=ev.length;const tb=document.getElementById('eventos-body');if(!ev.length){tb.innerHTML='<tr><td colspan="9" class="empty">Todavía no hay eventos registrados.</td></tr>';}else{tb.innerHTML=ev.map(e=>`<tr><td>${e.event_id??'--'}</td><td>${e.timestamp?new Date(e.timestamp*1000).toLocaleString():'--'}</td><td>${e.uptime_ms??'--'}</td><td class="event-tag">${e.event_type??e.tipo_evento??'--'}</td><td>${e.duration_ms??'--'}</td><td>${fmt(e.head_x)}</td><td>${fmt(e.head_y)}</td><td>${Number(e.alert_sent??e.alerta_activa)===1?'Sí':'No'}</td><td>${e.bateria_pct==null?'N/D':e.bateria_pct+'%'}</td></tr>`).join('');}}
catch(e){dot.className='dot';cloud.textContent='Sin comunicación con API';document.getElementById('sync-note').textContent='No se pudo actualizar la telemetría';console.error(e)}}
cargarConfiguracion();actualizarDashboard();setInterval(actualizarDashboard,3000);setInterval(cargarConfiguracion,30000);
</script></body></html>'''
    return HTMLResponse(content=html_content)
