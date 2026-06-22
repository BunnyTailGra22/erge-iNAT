#!/usr/bin/env python3
"""Scope the 2026-04-25 二格山 observations to those before a cutoff and build a
self-contained Leaflet map. Writes scoped CSV/JSON + an HTML map into data/<date>/."""
import csv, json, datetime, os
from datetime import timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATE = "2026-04-25"
CUTOFF = "2026-04-25T14:37:27+08:00"
TW = timezone(timedelta(hours=8))
BASE = os.path.join(HERE, "data", DATE)

cut = datetime.datetime.fromisoformat(CUTOFF)
rows = list(csv.DictReader(open(os.path.join(BASE, "observations.csv"))))


def t(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TW)


for r in rows:
    r["_t"] = t(r["time_observed_at"])
rows.sort(key=lambda r: r["_t"])
inc = [r for r in rows if r["_t"] < cut]

# scoped CSV (drop helper col)
cols = [c for c in inc[0].keys() if not c.startswith("_")]
with open(os.path.join(BASE, "scoped_before_1437.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows([{c: r[c] for c in cols} for r in inc])

# compact records for the map
pts = []
for i, r in enumerate(inc, 1):
    acc = float(r["positional_accuracy"]) if r["positional_accuracy"] else None
    pts.append({
        "n": i, "t": r["_t"].strftime("%H:%M:%S"),
        "s": r["scientific_name"], "c": r["common_name"] or "",
        "f": r["family"] or "", "g": r["quality_grade"],
        "a": acc, "p": r["phenology"] or "",
        "y": float(r["lat"]), "x": float(r["lng"]),
        "u": r["uri"], "ph": r["first_photo"] or "",
        "d": 1 if r["id"] == "353387038" else 0,   # known displaced outlier
    })
json.dump(pts, open(os.path.join(BASE, "scoped_before_1437.json"), "w"),
          ensure_ascii=False, indent=2)
# minified single-line copy for embedding into the widget
with open(os.path.join(BASE, "_map_data.min.json"), "w") as f:
    json.dump(pts, f, ensure_ascii=False, separators=(",", ":"))

DATA = json.dumps(pts, ensure_ascii=False, separators=(",", ":"))
flagged = sum(1 for p in pts if p["a"] and p["a"] > 100)
research = sum(1 for p in pts if p["g"] == "research")

# ---- shared map body (works inline in a widget; no <head> needed) ----
BODY = """
<div id="m" style="height:560px;border-radius:10px;overflow:hidden"></div>
<div id="leg" style="font:13px/1.5 system-ui,sans-serif;margin-top:8px;color:#333">
  <b>__N__ observations · __SP__ species</b> &nbsp;|&nbsp;
  before __CUT__ &nbsp;|&nbsp;
  <span style="color:#2e7d32">●</span> research-grade (__RG__) &nbsp;
  <span style="color:#ef6c00">●</span> needs-ID &nbsp;
  <span style="color:#c62828">◯</span> GPS&nbsp;&gt;100m (__FL__) &nbsp;
  <span style="color:#c62828">★</span> displaced outlier &nbsp;
  <span style="color:#3949ab">—</span> walk order
</div>
<script>
(function(){
  function go(){
    var D=__DATA__;
    var map=L.map('m',{scrollWheelZoom:true});
    L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      {maxZoom:17,attribution:'© OpenTopoMap, © OpenStreetMap contributors'}).addTo(map);
    var line=D.map(function(p){return [p.y,p.x];});
    L.polyline(line,{color:'#3949ab',weight:2,opacity:.6}).addTo(map);
    var bounds=[];
    D.forEach(function(p){
      bounds.push([p.y,p.x]);
      var col=p.g==='research'?'#2e7d32':'#ef6c00';
      if(p.a&&p.a>100){
        L.circle([p.y,p.x],{radius:p.a,color:'#c62828',weight:1,
          fillColor:'#c62828',fillOpacity:.05,dashArray:'4'}).addTo(map);
      }
      var mk=L.circleMarker([p.y,p.x],{radius:p.d?7:5,color:p.d?'#c62828':'#fff',
        weight:p.d?2:1,fillColor:col,fillOpacity:.9}).addTo(map);
      var ph=p.ph?'<img src="'+p.ph+'" style="width:170px;border-radius:6px;margin-top:6px">':'';
      var acc=p.a!=null?(p.a.toFixed(0)+' m'+(p.a>100?' ⚠':'')):'—';
      mk.bindPopup('<div style="font:13px system-ui,sans-serif;max-width:190px">'
        +'<b>#'+p.n+' · '+p.t+'</b><br>'
        +'<i>'+p.s+'</i>'+(p.c?' ('+p.c+')':'')+'<br>'
        +(p.f?'科 '+p.f+'<br>':'')
        +'品質 '+p.g+'<br>GPS ±'+acc
        +(p.p?'<br>物候 '+p.p:'')
        +(p.d?'<br><b style="color:#c62828">★ displaced GPS outlier</b>':'')
        +ph
        +'<br><a href="'+p.u+'" target="_blank">iNat ↗</a></div>');
      mk.bindTooltip('#'+p.n+' '+p.s,{direction:'top'});
    });
    map.fitBounds(bounds,{padding:[30,30]});
  }
  if(window.L){go();return;}
  var css=document.createElement('link');css.rel='stylesheet';
  css.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';document.head.appendChild(css);
  var js=document.createElement('script');
  js.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  js.onload=go;document.body.appendChild(js);
})();
</script>
"""
BODY = (BODY.replace("__DATA__", DATA).replace("__N__", str(len(pts)))
            .replace("__SP__", str(len({p["s"] for p in pts})))
            .replace("__RG__", str(research)).replace("__FL__", str(flagged))
            .replace("__CUT__", "14:37:27 CST"))

html = ("<!DOCTYPE html><html lang='zh-Hant'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>二格山 iNat 2026-04-25 (before 14:37:27)</title>"
        "<style>body{margin:16px;background:#fafafa}"
        "h2{font:600 18px system-ui;margin:0 0 10px}</style></head><body>"
        "<h2>二格山稜線踏查 · 2026-04-25 · scope &lt; 14:37:27 CST</h2>"
        + BODY + "</body></html>")
with open(os.path.join(BASE, "map_2026-04-25_before-1437.html"), "w") as f:
    f.write(html)

print(f"scoped {len(pts)} pts / {len({p['s'] for p in pts})} species "
      f"({research} research, {flagged} GPS>100m)")
print("wrote: scoped_before_1437.csv, scoped_before_1437.json, "
      "map_2026-04-25_before-1437.html, _map_data.min.json")
