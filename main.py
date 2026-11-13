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
    bateria_pct: Optional[int] = None

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
    "bateria_pct": None,
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

    telemetria_actual["bateria_pct"] = evento.bateria_pct
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
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#071426"><title>ADAS | Centro de monitoreo</title>
<style>
:root{--bg:#071426;--panel:#0d2038;--line:rgba(148,183,218,.16);--text:#edf5ff;--muted:#91a8c2;--cyan:#35d4e8;--green:#38d996;--yellow:#ffc857;--red:#ff637d}
*{box-sizing:border-box}body{margin:0;color:var(--text);font-family:Inter,"Segoe UI",Arial,sans-serif;background:radial-gradient(circle at 85% 0%,rgba(24,111,183,.22),transparent 30%),radial-gradient(circle at 0% 35%,rgba(31,183,201,.10),transparent 28%),var(--bg);min-height:100vh}
.shell{max-width:1280px;margin:auto;padding:28px 24px 42px}header{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:4px 0 24px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:15px}.brand-mark{width:58px;height:58px;border-radius:15px;display:grid;place-items:center;background:linear-gradient(145deg,#0e70ba,#092c55);border:1px solid rgba(76,204,237,.5);font-weight:900;font-size:21px;letter-spacing:-1px}
.brand-name{font-size:12px;color:var(--cyan);letter-spacing:2px;font-weight:800}.brand-sub{color:var(--muted);font-size:12px;margin-top:5px}h1{margin:5px 0 0;font-size:clamp(22px,3vw,30px);letter-spacing:-.7px}
.header-right{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.pill{display:inline-flex;align-items:center;gap:8px;padding:9px 13px;border:1px solid var(--line);background:rgba(13,32,56,.8);border-radius:30px;color:var(--muted);font-size:12px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--yellow)}.dot.online{background:var(--green);box-shadow:0 0 10px var(--green)}
.section-title{margin:28px 0 14px;display:flex;justify-content:space-between;align-items:end;gap:12px;flex-wrap:wrap}.section-title h2{font-size:16px;margin:0;letter-spacing:.3px}.section-title span{color:var(--muted);font-size:12px}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.card{background:linear-gradient(150deg,rgba(16,41,67,.96),rgba(10,27,48,.96));border:1px solid var(--line);border-radius:16px;padding:19px;box-shadow:0 12px 30px rgba(0,0,0,.12);min-width:0}
.card-label{color:var(--muted);text-transform:uppercase;font-size:10px;letter-spacing:1.3px;font-weight:800}.metric{font-size:29px;font-weight:750;letter-spacing:-1px;margin:13px 0 8px;overflow-wrap:anywhere}.metric.small{font-size:21px}.sub{color:var(--muted);font-size:12px}
.bar{height:7px;background:#1b3550;border-radius:10px;margin-top:15px;overflow:hidden}.bar-fill{height:100%;width:0;border-radius:10px;transition:width .4s}
.status{display:inline-flex;align-items:center;gap:7px;border-radius:20px;padding:6px 10px;font-size:11px;font-weight:700;background:rgba(56,217,150,.12);color:var(--green)}.status.warn{background:rgba(255,200,87,.12);color:var(--yellow)}.status.bad{background:rgba(255,99,125,.12);color:var(--red)}
.params{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.param-value{font-size:28px;font-weight:750;margin:15px 0 5px}.readonly{display:inline-block;font-size:10px;color:var(--cyan);border:1px solid rgba(53,212,232,.25);padding:5px 8px;border-radius:20px;letter-spacing:.7px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:15px;background:rgba(13,32,56,.85)}table{width:100%;border-collapse:collapse;min-width:650px}th,td{text-align:left;padding:14px 16px;border-bottom:1px solid var(--line);font-size:12px}th{color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-size:10px;background:rgba(255,255,255,.025)}td{color:#dceaff}tr:last-child td{border-bottom:0}.event-tag{color:var(--cyan);font-weight:800}.empty{text-align:center;color:var(--muted);padding:28px}
footer{margin-top:25px;color:#6f88a4;font-size:11px;text-align:center}@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.shell{padding:18px 14px 30px}.grid{grid-template-columns:1fr 1fr;gap:9px}.card{padding:14px}.metric{font-size:23px}.params{grid-template-columns:1fr}.brand-mark{width:48px;height:48px}.header-right{width:100%}}
</style></head>
<body><div class="shell">
<header><div class="brand"><div class="brand-mark">UTN</div><div><div class="brand-name">UNIVERSIDAD TECNOLÓGICA NACIONAL</div><h1>ADAS · Centro de monitoreo</h1><div class="brand-sub">Sistema de asistencia y supervisión del conductor</div></div></div>
<div class="header-right"><div class="pill"><span id="cloud-dot" class="dot"></span><span id="cloud-status">Verificando servidor</span></div><div class="pill">ACTUALIZACIÓN AUTOMÁTICA · 3 S</div></div></header>

<div class="section-title"><h2>Estado del sistema</h2><span>Información recibida desde la unidad telemática</span></div>
<section class="grid">
<div class="card"><div class="card-label">Batería TTGO · 4G</div><div class="metric" id="bat-val">--</div><div class="sub" id="bat-note">Esperando medición real</div><div class="bar"><div class="bar-fill" id="bat-bar"></div></div></div>
<div class="card"><div class="card-label">Último evento detectado</div><div class="metric small" id="evento-val">En espera</div><span id="alerta-badge" class="status warn">Sin datos</span></div>
<div class="card"><div class="card-label">Última comunicación</div><div class="metric small" id="sync-val">--</div><div class="sub" id="sync-note">Esperando telemetría</div></div>
<div class="card"><div class="card-label">Eventos almacenados</div><div class="metric" id="count-val">--</div><div class="sub">Registros disponibles en el servidor</div></div>
</section>

<div class="section-title"><h2>Parámetros temporales</h2><span>Valores informativos · No modificables desde esta página</span></div>
<section class="params">
<div class="card"><div class="card-label">Tiempo de distracción</div><div class="param-value" id="cfg-distraccion">-- s</div><span class="readonly">SOLO LECTURA</span><div class="sub" style="margin-top:12px">Umbral temporal definido en la configuración del sistema</div></div>
<div class="card"><div class="card-label">Tiempo de somnolencia</div><div class="param-value" id="cfg-somnolencia">-- s</div><span class="readonly">SOLO LECTURA</span><div class="sub" style="margin-top:12px">Parámetro informativo; la detección de somnolencia no está activa en la versión actual</div></div>
</section>

<div class="section-title"><h2>Historial de eventos</h2><span>Últimos registros recibidos</span></div>
<div class="table-wrap"><table><thead><tr><th>Timestamp (P4)</th><th>Evento</th><th>Valor medido</th><th>Alerta</th><th>Batería</th></tr></thead><tbody id="eventos-body"><tr><td colspan="5" class="empty">Cargando historial...</td></tr></tbody></table></div>
<footer>PROYECTO ADAS · UNIVERSIDAD TECNOLÓGICA NACIONAL · PANEL DE TELEMETRÍA</footer></div>

<script>
const fmt=v=>Number.isFinite(Number(v))?Number(v).toFixed(2):'--';
async function cargarConfiguracion(){try{const r=await fetch('/api/v1/configuracion',{cache:'no-store'});if(!r.ok)throw Error();const c=await r.json();document.getElementById('cfg-distraccion').textContent=c.umbral_distraccion==null?'-- s':`${fmt(c.umbral_distraccion)} s`;document.getElementById('cfg-somnolencia').textContent=c.tiempo_somnolencia==null?'-- s':`${fmt(c.tiempo_somnolencia)} s`;}catch(e){console.error('Error al cargar parámetros',e)}}
async function actualizarDashboard(){const dot=document.getElementById('cloud-dot'),cloud=document.getElementById('cloud-status');try{
const [tr,er]=await Promise.all([fetch('/api/v1/telemetria',{cache:'no-store'}),fetch('/api/v1/eventos',{cache:'no-store'})]);if(!tr.ok||!er.ok)throw Error('API no disponible');const t=await tr.json(),ev=await er.json();dot.className='dot online';cloud.textContent='Servidor conectado';
const p=t.bateria_pct,bat=document.getElementById('bat-val'),bar=document.getElementById('bat-bar');if(p!==null&&p!==undefined&&Number.isFinite(Number(p))){const n=Math.max(0,Math.min(100,Number(p)));bat.textContent=n+'%';bar.style.width=n+'%';bar.style.background=n>50?'linear-gradient(90deg,#35d4e8,#38d996)':n>20?'#ffc857':'#ff637d';document.getElementById('bat-note').textContent='Último valor informado por la TTGO';}else{bat.textContent='N/D';bar.style.width='0%';document.getElementById('bat-note').textContent='La medición de batería aún no está disponible';}
document.getElementById('evento-val').textContent=t.ultimo_evento||'Ninguno';const b=document.getElementById('alerta-badge');if(Number(t.alerta_activa)===1){b.className='status bad';b.textContent='ALERTA ACTIVA';}else{b.className='status';b.textContent='Sin alerta activa';}
if(Number(t.ultimo_sync)>0){const d=new Date(Number(t.ultimo_sync)*1000);document.getElementById('sync-val').textContent=d.toLocaleTimeString();document.getElementById('sync-note').textContent=d.toLocaleDateString();}else{document.getElementById('sync-val').textContent='--';}
document.getElementById('count-val').textContent=ev.length;const tb=document.getElementById('eventos-body');if(!ev.length){tb.innerHTML='<tr><td colspan="5" class="empty">Todavía no hay eventos registrados.</td></tr>';}else{tb.innerHTML=ev.map(e=>`<tr><td>${e.timestamp??'--'}</td><td class="event-tag">${String(e.tipo_evento??'--')}</td><td>${fmt(e.valor_medido)}</td><td>${Number(e.alerta_activa)===1?'<span style="color:#ff637d;font-weight:700">ACTIVA</span>':'No'}</td><td>${e.bateria_pct==null?'N/D':e.bateria_pct+'%'}</td></tr>`).join('');}
}catch(e){dot.className='dot';cloud.textContent='Sin comunicación con API';document.getElementById('sync-note').textContent='No se pudo actualizar la telemetría';console.error('Error al actualizar dashboard',e)}}
cargarConfiguracion();actualizarDashboard();setInterval(actualizarDashboard,3000);setInterval(cargarConfiguracion,30000);
</script></body></html>
"""
    return HTMLResponse(content=html_content)
