import os
import json
import base64
import http.server
import threading
import webbrowser
from scorer import assign

HTML_DASHBOARD = "dashboard.html"
HTML_REQUEST = "request.html"
MAP_IMAGE = r"C:\Users\moham\Downloads\5663353_2954453.jpg"

def load_map_image():
    if os.path.exists(MAP_IMAGE):
        with open(MAP_IMAGE, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{data}"
    print(f"  [WARNING] Map image not found at: {MAP_IMAGE}")
    return ""

def build_dashboard_html():
    with open("data/drones.json", encoding="utf-8") as f: 
        drones = json.load(f)
    with open("data/pharmacies.json", encoding="utf-8") as f: 
        pharmacies = json.load(f)

    drones_js = json.dumps(drones)
    pharmacies_js = json.dumps(pharmacies)
    map_src = load_map_image()
    total_drones = len(drones)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Drone Dashboard — Live Control</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}}
  body{{background:#f4f4f0;color:#1a1a1a}}
  header{{background:#534AB7;color:white;padding:14px 24px;display:flex;align-items:center;gap:12px}}
  header h1{{font-size:18px;font-weight:500}}
  .map-wrap{{position:relative;width:100%;height:calc(100vh - 130px);border-radius:12px;border:1px solid #ddd;overflow:hidden;background:#e8f0e4;margin:16px}}
  .map-wrap img{{width:100%;height:100%;object-fit:cover;display:block;opacity:0.85}}
  canvas#map{{position:absolute;top:0;left:0;width:100%;height:100%}}
  .legend{{display:flex;flex-wrap:wrap;gap:14px;margin:10px 20px;font-size:13px}}
  .legend-item{{display:flex;align-items:center;gap:6px}}
  .dot{{width:12px;height:12px;border-radius:50%}}
  .status-bar{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:0 20px 20px}}
  .stat{{background:white;border-radius:10px;padding:14px;border:1px solid #e0e0e0}}
  .stat-label{{font-size:12px;color:#666}}
  .stat-val{{font-size:28px;font-weight:600}}
</style>
</head>
<body>
<header>
  <div style="width:32px;height:32px;background:rgba(255,255,255,0.2);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:20px">⬡</div>
  <h1>Drone Delivery — Live Dashboard</h1>
</header>

<div class="map-wrap">
  <img src="{map_src}" alt="city map">
  <canvas id="map"></canvas>
</div>

<div class="legend">
  <div class="legend-item"><div class="dot" style="background:#185FA5"></div>Idle Drone</div>
  <div class="legend-item"><div class="dot" style="background:#639922"></div>En Route</div>
  <div class="legend-item"><div class="dot" style="background:#BA7517"></div>Charging</div>
  <div class="legend-item"><div class="dot" style="background:#D85A30"></div>Pharmacy (open)</div>
</div>

<div class="status-bar" id="status-bar">
  <div class="stat"><div class="stat-label">Total Drones</div><div class="stat-val">{total_drones}</div></div>
  <div class="stat"><div class="stat-label">Idle</div><div class="stat-val" id="idle-count">0</div></div>
  <div class="stat"><div class="stat-label">En Route</div><div class="stat-val" id="enroute-count">0</div></div>
</div>

<script>
const DRONES = {drones_js};
const PHARMACIES = {pharmacies_js};
const HQ = {{lat:36.8060, lon:10.1810}};

let droneState = DRONES.map(d => ({{
  ...d, 
  ox: 0, oy: 0, 
  angle: Math.random()*Math.PI*2, 
  mission: null, 
  progress: 0
}}));

const canvas = document.getElementById('map');
const ctx = canvas.getContext('2d');
let W, H, minLat, maxLat, minLon, maxLon;

function haversine(a,b,c,e){{
  const R=6371, dl=(c-a)*Math.PI/180, dn=(e-b)*Math.PI/180;
  const x = Math.sin(dl/2)**2 + Math.cos(a*Math.PI/180)*Math.cos(c*Math.PI/180)*Math.sin(dn/2)**2;
  return R*2*Math.asin(Math.sqrt(x));
}}

function initBounds(){{
  const lats = [...DRONES.map(d=>d.lat), ...PHARMACIES.map(p=>p.lat), HQ.lat];
  const lons = [...DRONES.map(d=>d.lon), ...PHARMACIES.map(p=>p.lon), HQ.lon];
  minLat = Math.min(...lats)-0.012; 
  maxLat = Math.max(...lats)+0.012;
  minLon = Math.min(...lons)-0.014; 
  maxLon = Math.max(...lons)+0.014;
}}

function toXY(lat,lon){{
  return {{
    x: (lon - minLon) / (maxLon - minLon) * W,
    y: (1 - (lat - minLat) / (maxLat - minLat)) * H
  }};
}}

function resize(){{
  const r = canvas.getBoundingClientRect();
  canvas.width = r.width * devicePixelRatio;
  canvas.height = r.height * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  W = r.width; H = r.height;
}}

function draw(){{
  ctx.clearRect(0,0,W,H);

  PHARMACIES.forEach(p => {{
    const pos = toXY(p.lat, p.lon);
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, 14, 0, Math.PI*2);
    ctx.fillStyle = p.open ? 'rgba(216,90,48,0.95)' : 'rgba(136,136,136,0.95)';
    ctx.fill();
    ctx.strokeStyle = '#fff'; 
    ctx.lineWidth = 2; 
    ctx.stroke();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 10px sans-serif';
    ctx.textAlign = 'center'; 
    ctx.textBaseline = 'middle';
    ctx.fillText('Rx', pos.x, pos.y);
  }});

  const hq = toXY(HQ.lat, HQ.lon);
  ctx.fillStyle = 'rgba(83,74,183,0.95)';
  ctx.beginPath(); 
  ctx.roundRect(hq.x-32, hq.y-20, 64, 40, 8); 
  ctx.fill();
  ctx.strokeStyle = '#fff'; 
  ctx.lineWidth = 2; 
  ctx.stroke();
  ctx.fillStyle = '#fff'; 
  ctx.font = 'bold 13px sans-serif';
  ctx.fillText('HQ', hq.x, hq.y + 2);

  droneState.forEach(d => {{
    let base = toXY(d.lat, d.lon);
    let x = base.x + d.ox;
    let y = base.y + d.oy;

    if (d.mission) {{
      const start = toXY(d.mission.startLat, d.mission.startLon);
      const end = toXY(d.mission.endLat, d.mission.endLon);
      const dx = end.x - start.x;
      const dy = end.y - start.y;

      d.progress = Math.min(d.progress + 0.008, 1);
      x = start.x + dx * d.progress;
      y = start.y + dy * d.progress;

      ctx.strokeStyle = 'rgba(83,74,183,0.4)';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();

      const angle = Math.atan2(dy, dx);
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.fillStyle = '#534AB7';
      ctx.beginPath();
      ctx.moveTo(20, 0);
      ctx.lineTo(-10, 12);
      ctx.lineTo(-6, 0);
      ctx.lineTo(-10, -12);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }} else if (d.status === 'idle') {{
      d.angle += 0.014;
      const r = 26;
      d.ox = Math.cos(d.angle) * r;
      d.oy = Math.sin(d.angle) * r;
    }}

    const color = d.mission ? '#639922' : '#185FA5';
    ctx.fillStyle = '#ffffff';
    ctx.beginPath(); 
    ctx.arc(x, y, 15, 0, Math.PI*2); 
    ctx.fill();
    ctx.strokeStyle = color; 
    ctx.lineWidth = 3.5; 
    ctx.stroke();

    ctx.fillStyle = color;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(d.angle);
    ctx.beginPath();
    ctx.moveTo(12, 0);
    ctx.lineTo(-9, 9);
    ctx.lineTo(-5, 0);
    ctx.lineTo(-9, -9);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    ctx.fillStyle = 'rgba(30,30,30,0.9)';
    ctx.beginPath(); 
    ctx.roundRect(x-20, y-45, 40, 18, 4); 
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(d.id, x, y-33);
  }});

  const idleCount = droneState.filter(d => !d.mission).length;
  const enrouteCount = droneState.filter(d => d.mission).length;
  document.getElementById('idle-count').textContent = idleCount;
  document.getElementById('enroute-count').textContent = enrouteCount;

  requestAnimationFrame(draw);
}}

setInterval(() => {{
  const missionData = localStorage.getItem('activeMission');
  if (missionData) {{
    const mission = JSON.parse(missionData);
    const drone = droneState.find(d => d.id === mission.droneId);
    if (drone && !drone.mission) {{
      drone.mission = {{
        startLat: drone.lat,
        startLon: drone.lon,
        endLat: mission.userLat,
        endLon: mission.userLon,
        pharmacy: mission.pharmacy
      }};
      drone.progress = 0;
      
      setTimeout(() => {{
        drone.mission = null;
        localStorage.removeItem('activeMission');
      }}, 8000);
    }}
  }}
}}, 500);

initBounds();
resize();
window.addEventListener('resize', resize);
draw();
</script>
</body>
</html>"""

def build_request_html():
    with open("data/drones.json", encoding="utf-8") as f: 
        drones = json.load(f)
    with open("data/pharmacies.json", encoding="utf-8") as f: 
        pharmacies = json.load(f)

    drones_js = json.dumps(drones)
    pharmacies_js = json.dumps(pharmacies)
    map_src = load_map_image()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Request Medical Delivery</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}}
  body{{background:#f4f4f0;padding:30px}}
  .card{{max-width:720px;margin:40px auto;background:white;border-radius:16px;box-shadow:0 15px 40px rgba(0,0,0,0.12);overflow:hidden}}
  header{{background:#534AB7;color:white;padding:25px;text-align:center}}
  .content{{padding:40px}}
  .map-container{{position:relative;width:100%;height:320px;border:2px solid #ddd;border-radius:12px;overflow:hidden;margin-bottom:20px;cursor:crosshair}}
  .map-container img{{width:100%;height:100%;object-fit:cover}}
  .form-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
  label{{display:block;font-size:14px;color:#444;margin-bottom:8px}}
  input, select{{width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;font-size:15px}}
  .run-btn{{width:100%;margin-top:25px;padding:16px;font-size:17px;font-weight:600;background:#534AB7;color:white;border:none;border-radius:12px;cursor:pointer}}
  .run-btn:hover{{background:#3c3489}}
  .result-box{{margin-top:25px;padding:25px;border:1px solid #e0e0e0;border-radius:12px;background:#fafafa;min-height:140px}}
</style>
</head>
<body>
<div class="card">
  <header>
    <h1>🚁 Request Drone Delivery</h1>
    <p>Click on the map to set delivery location</p>
  </header>
  <div class="content">
    <div class="map-container" id="map-container">
      <img src="{map_src}" alt="Click to select location">
    </div>

    <div class="form-grid">
      <div><label>User Latitude</label><input type="number" id="d-lat" value="36.7950" step="0.0001" readonly></div>
      <div><label>User Longitude</label><input type="number" id="d-lon" value="10.1780" step="0.0001" readonly></div>
      <div>
        <label>Medical Supply</label>
        <select id="d-supply">
          <option value="insulin">Insulin</option>
          <option value="paracetamol">Paracetamol</option>
          <option value="bandages">Bandages</option>
          <option value="antibiotics">Antibiotics</option>
          <option value="epinephrine">Epinephrine</option>
        </select>
      </div>
      <div>
        <label>Priority Level</label>
        <input type="range" id="d-priority" min="1" max="5" value="3" oninput="document.getElementById('pval').textContent=this.value">
        <div style="display:flex;justify-content:space-between;font-size:13px;margin-top:4px">
          <span>1 - Routine</span>
          <span id="pval" style="font-weight:600">3</span>
          <span>5 - Emergency</span>
        </div>
      </div>
    </div>

    <button class="run-btn" onclick="runRequest()">REQUEST SUPPLY</button>

    <div id="result-box" class="result-box">
      <p style="color:#777;text-align:center">Click on the map to choose delivery location, then click the button</p>
    </div>
  </div>
</div>

<script>
const MAP_CONTAINER = document.getElementById('map-container');

MAP_CONTAINER.addEventListener('click', function(e) {{
  const rect = MAP_CONTAINER.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top;

  // Convert pixel position to approximate lat/lon (based on your map bounds)
  const lat = 36.83 - (clickY / rect.height) * (36.83 - 36.78);
  const lon = 10.16 + (clickX / rect.width) * (10.20 - 10.16);

  document.getElementById('d-lat').value = lat.toFixed(4);
  document.getElementById('d-lon').value = lon.toFixed(4);
}});

async function runRequest() {{
  const lat = parseFloat(document.getElementById('d-lat').value);
  const lon = parseFloat(document.getElementById('d-lon').value);
  const supply = document.getElementById('d-supply').value;
  const priority = parseInt(document.getElementById('d-priority').value);

  if (!lat || !lon) {{
    alert("Please click on the map to select delivery location");
    return;
  }}

  const response = await fetch('/api/assign', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ lat, lon, supply, priority }})
  }});

  const result = await response.json();

  if (result.status === "error") {{
    alert(result.message || "Assignment failed");
    return;
  }}

  const mission = {{
    droneId: result.drone_id,
    userLat: lat,
    userLon: lon,
    pharmacy: result.pharmacy_name
  }};
  localStorage.setItem('activeMission', JSON.stringify(mission));

  document.getElementById('result-box').innerHTML = `
    <strong style="color:#534AB7">✅ Drone ${'{result.drone_id}' } assigned successfully!</strong><br><br>
    Pickup from: <strong>${'{result.pharmacy_name}'}</strong><br>
    Total distance: ${'{result.total_distance_km}'} km<br>
    ETA ≈ ${'{result.eta_minutes}'} minutes<br>
    Battery: ${'{result.drone_battery}'}%<br><br>
    <button onclick="window.open('dashboard.html','_blank')" 
            style="padding:12px 28px;background:#534AB7;color:white;border:none;border-radius:10px;cursor:pointer">
      👀 Watch the drone flying live →
    </button>
  `;
}}
</script>
</body>
</html>"""

# ===================== SERVER (unchanged) =====================
def serve():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            super().end_headers()

        def do_POST(self):
            if self.path == '/api/assign':
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    request_data = json.loads(post_data)

                    with open("data/drones.json", encoding="utf-8") as f:
                        drones = json.load(f)
                    with open("data/pharmacies.json", encoding="utf-8") as f:
                        pharmacies = json.load(f)

                    best, status = assign(request_data, drones, pharmacies)

                    if status != "ok":
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": status}).encode())
                        return

                    response_data = {
                        "status": "success",
                        "drone_id": best["drone_id"],
                        "pharmacy_name": best["pharmacy_name"],
                        "total_distance_km": best["total_distance_km"],
                        "drone_battery": best["drone_battery"],
                        "eta_minutes": best["eta_minutes"]
                    }

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
            else:
                self.send_error(404)

        def log_message(self, *args): pass

    with http.server.HTTPServer(("", 5500), Handler) as server:
        print("\n  🚁 Drone Delivery System - Clickable Map Version")
        print("  ================================================")
        print("  Request Delivery → http://localhost:5500/request.html")
        print("  Live Dashboard   → http://localhost:5500/dashboard.html")
        print("  Press Ctrl+C to stop\n")
        server.serve_forever()

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    with open(HTML_DASHBOARD, "w", encoding="utf-8") as f:
        f.write(build_dashboard_html())
    
    with open(HTML_REQUEST, "w", encoding="utf-8") as f:
        f.write(build_request_html())

    threading.Thread(target=serve, daemon=True).start()
    webbrowser.open("http://localhost:5500/request.html")
    
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n  Server stopped.")