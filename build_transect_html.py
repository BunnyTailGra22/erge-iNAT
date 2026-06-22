#!/usr/bin/env python3
"""Publish the 二格山 ridgeline elevation transect as a self-contained HTML page:
荒野保護協會 brand palette, minimalist, summary cards (觀察/物種/科/屬/步道長/爬升),
科別+屬別 filter dropdowns, and photo + name tooltips. Also writes index.html."""
import json, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "data", "2026-04-25")
pts = json.load(open(os.path.join(BASE, "profile_enriched.json")))
DATA = json.dumps(pts, ensure_ascii=False)

nsp = len({p["s"] for p in pts})
nfam = len({p["f"] for p in pts})
ngen = len({p["s"].split(" ")[0] for p in pts})
els = [p["y"] for p in pts]
dist = int(round(pts[-1]["x"]))
xmax = int(math.ceil(pts[-1]["x"] / 25) * 25)
climb = int(round(pts[-1]["y"] - pts[0]["y"]))
e0, e1 = int(pts[0]["y"]), int(pts[-1]["y"])

HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>二格山稜線 植被海拔剖面圖 · 2026-04-25</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{--green:#587A30;--green2:#90B821;--gray:#666;--gray2:#B2B2B2;--yellow:#FFD900;--red:#E8380D;--ink:#3a3a36}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font-family:"Noto Sans TC",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1000px;margin:0 auto;padding:46px 28px 36px}
h1{font-weight:700;font-size:25px;color:var(--green);margin:0 0 6px;letter-spacing:.5px}
.sub{font-size:14px;color:var(--gray);margin:0 0 22px}
.cards{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:0 0 22px}
@media(max-width:760px){.cards{grid-template-columns:repeat(3,1fr)}}
.card{background:#f5f4ef;border-radius:10px;padding:11px 12px}
.card .lbl{font-size:12px;color:var(--gray);margin-bottom:4px}
.card .val{font-size:22px;font-weight:500;color:var(--ink);line-height:1.15}
.card .sub2{font-size:11px;color:var(--gray2);margin-top:2px}
.card select{width:100%;font-family:inherit;font-size:13px;color:var(--ink);background:#fff;
  border:0.5px solid var(--gray2);border-radius:6px;padding:7px 6px;margin-top:3px;cursor:pointer}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:var(--gray);margin:0 0 12px}
.legend i{display:inline-block;vertical-align:middle;margin-right:6px}
.dot{width:11px;height:11px;border-radius:50%}
.diam{width:10px;height:10px;background:var(--green);border:1.5px solid var(--red);transform:rotate(45deg)}
.chartbox{position:relative;width:100%;height:450px}
.ctt{position:absolute;pointer-events:none;opacity:0;transition:opacity .12s;width:178px;background:#fff;
  border:0.5px solid var(--gray2);border-radius:8px;padding:8px;z-index:5;font-size:12px;line-height:1.45}
.ctt img{width:100%;height:118px;object-fit:cover;border-radius:6px;margin-bottom:6px;background:#f1efe8;display:block}
.ctt .nm{font-weight:700;color:var(--green);font-size:14px}
.ctt .sci{font-style:italic;color:var(--gray)}
.ctt .fam{color:var(--gray)}
.foot{margin-top:22px;font-size:11.5px;color:var(--gray2);line-height:1.6}
</style>
</head>
<body>
<div class="wrap">
  <h1>二格山稜線 · 植被海拔剖面圖</h1>
  <p class="sub">2026-04-25 踏查 · 稜線段（14:56 前）· 滑過點位看照片，點擊開啟 iNaturalist</p>

  <div class="cards">
    <div class="card"><div class="lbl">觀察數 observations</div><div class="val">__N__</div></div>
    <div class="card"><div class="lbl">物種數 species</div><div class="val">__SP__</div></div>
    <div class="card"><div class="lbl">科別 family</div><select id="famSel"></select></div>
    <div class="card"><div class="lbl">屬別 genus</div><select id="genSel"></select></div>
    <div class="card"><div class="lbl">步道長 trail</div><div class="val">__DIST__ m</div></div>
    <div class="card"><div class="lbl">爬升 climb</div><div class="val">+__CLIMB__ m</div><div class="sub2">__E0__ → __E1__ m</div></div>
  </div>

  <div class="legend">
    <span><i class="dot" style="background:var(--green)"></i>研究等級 research</span>
    <span><i class="dot" style="background:var(--green2)"></i>需鑑定 needs-ID</span>
    <span><i class="diam"></i>GPS &gt;100 m · 位置/高程內插 interpolated</span>
  </div>

  <div class="chartbox"><canvas id="t" role="img"
    aria-label="二格山稜線植被海拔剖面圖，橫軸為沿步道水平距離，縱軸為海拔，點為植物觀察，可依科屬篩選"></canvas></div>

  <p class="foot">
    資料來源 iNaturalist API（觀察者 bunnytailgrass，地點 二格山 place_id 130869）·
    海拔 SRTM 30 m（雙線性內插）· GPS &gt;100 m 之點，位置與高程以鄰近可靠點時間內插
    （避免錯誤定位導致高程突降）· 資料快照 2026/04/25 · 14:41 CST · 色彩：荒野保護協會。
  </p>
</div>

<script>
var DATA = __DATA__;
var FAM='*', GEN='*';
function gen(d){return d.s.split(' ')[0];}
function active(d){return (FAM==='*'||d.f===FAM)&&(GEN==='*'||gen(d)===GEN);}
function pcol(c){var d=c.raw;if(!active(d))return '#D3D1C7';return d.g==='research'?'#587A30':'#90B821';}
function pbord(c){var d=c.raw;if(!active(d))return '#D3D1C7';return d.fl?'#E8380D':'#ffffff';}
function pbw(c){return (c.raw.fl&&active(c.raw))?2.5:1;}
function prad(c){var d=c.raw;if(!active(d))return 2.5;return d.fl?5.5:4;}
function pstyle(c){return c.raw.fl?'rectRot':'circle';}
function extTip(ctx){
  var chart=ctx.chart, tip=ctx.tooltip, wrap=chart.canvas.parentNode;
  var el=wrap.querySelector('.ctt');
  if(!el){el=document.createElement('div');el.className='ctt';wrap.appendChild(el);}
  if(tip.opacity===0){el.style.opacity=0;return;}
  var d=tip.dataPoints[0].raw;
  var img=d.ph?('<img src="'+d.ph+'" alt="">'):'';
  el.innerHTML=img+'<div class="nm">'+(d.c||'—')+'</div><div class="sci">'+d.s+
    '</div><div class="fam">'+d.fz+' · '+d.f+'</div>';
  var cw=wrap.clientWidth, left=tip.caretX+16;
  if(left+186>cw){left=tip.caretX-186;} if(left<0){left=4;}
  var top=tip.caretY-30; if(top<0){top=4;}
  el.style.left=left+'px'; el.style.top=top+'px'; el.style.opacity=1;
}
var chart;
function fillFamilies(){
  var fc={}, fz={};
  DATA.forEach(function(d){fc[d.f]=(fc[d.f]||0)+1; fz[d.f]=d.fz;});
  var keys=Object.keys(fc).sort(function(a,b){return fc[b]-fc[a];});
  var h='<option value="*">全部 all ('+keys.length+' 科)</option>';
  keys.forEach(function(k){h+='<option value="'+k+'">'+fz[k]+' '+k+' · '+fc[k]+'</option>';});
  document.getElementById('famSel').innerHTML=h;
}
function fillGenera(fam){
  var gc={};
  DATA.forEach(function(d){if(fam==='*'||d.f===fam){var g=gen(d);gc[g]=(gc[g]||0)+1;}});
  var keys=Object.keys(gc).sort();
  var h='<option value="*">全部 all ('+keys.length+' 屬)</option>';
  keys.forEach(function(k){h+='<option value="'+k+'">'+k+' · '+gc[k]+'</option>';});
  document.getElementById('genSel').innerHTML=h;
}
function go(){
  fillFamilies(); fillGenera('*');
  document.getElementById('famSel').onchange=function(){FAM=this.value;GEN='*';fillGenera(FAM);chart.update();};
  document.getElementById('genSel').onchange=function(){GEN=this.value;chart.update();};
  chart=new Chart(document.getElementById('t'),{type:'line',
    data:{datasets:[{data:DATA,borderColor:'#666666',borderWidth:1.5,fill:'start',
      backgroundColor:'rgba(178,178,178,0.20)',tension:0.3,
      pointBackgroundColor:pcol,pointBorderColor:pbord,pointBorderWidth:pbw,
      pointRadius:prad,pointStyle:pstyle,pointHoverRadius:function(c){return prad(c)+2;}}]},
    options:{responsive:true,maintainAspectRatio:false,
      interaction:{mode:'nearest',intersect:false},
      onClick:function(e,els){if(els.length)window.open(DATA[els[0].index].u,'_blank');},
      plugins:{legend:{display:false},tooltip:{enabled:false,external:extTip}},
      scales:{
        x:{type:'linear',min:0,max:__XMAX__,
           title:{display:true,text:'沿步道水平距離 horizontal distance (m)',color:'#666666'},
           grid:{color:'rgba(178,178,178,0.30)'},ticks:{color:'#666666',callback:function(v){return v+' m';}}},
        y:{min:512,max:668,title:{display:true,text:'海拔 elevation (m)',color:'#666666'},
           grid:{color:'rgba(178,178,178,0.30)'},ticks:{color:'#666666',callback:function(v){return v+' m';}}}}}});
}
if(window.Chart){go();}else{var w=setInterval(function(){if(window.Chart){clearInterval(w);go();}},60);}
</script>
</body>
</html>
"""
HTML = (HTML.replace("__DATA__", DATA).replace("__N__", str(len(pts)))
            .replace("__SP__", str(nsp)).replace("__DIST__", str(dist))
            .replace("__XMAX__", str(xmax)).replace("__CLIMB__", str(climb))
            .replace("__E0__", str(e0)).replace("__E1__", str(e1)))
for path in (os.path.join(BASE, "transect_2026-04-25.html"), os.path.join(HERE, "index.html")):
    open(path, "w").write(HTML)
print(f"wrote transect ({len(HTML)} bytes) + index.html | {len(pts)} obs, {nsp} sp, "
      f"{nfam} fam, {ngen} gen, {dist} m, +{climb} m")
