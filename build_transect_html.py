#!/usr/bin/env python3
"""Publish the 二格山 ridgeline elevation transect as a self-contained HTML page:
荒野保護協會 brand palette, minimalist, summary cards (觀察/物種/科/屬/步道長/爬升),
科別+屬別 filter dropdowns, photo tooltips. Mobile: pinch-zoom + pan, bottom-sheet
tooltip, responsive cards. Also writes index.html (GitHub Pages entry)."""
import json, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "data", "2026-04-25")
pts = json.load(open(os.path.join(BASE, "profile_enriched.json")))
TX = json.load(open(os.path.join(HERE, "data", "registry", "taxa_taicol.json")))
for p in pts:                                  # merge TaiCoL family/genus (中拉) + status
    e = TX.get(p["s"], {})
    p["famSci"] = e.get("fam_sci") or p["f"]
    p["famZh"] = e.get("fam_zh") or p["fz"]
    p["genSci"] = e.get("gen_sci") or p["s"].split(" ")[0]
    p["genZh"] = e.get("gen_zh") or ""
    p["end"] = bool(e.get("is_endemic"))
    p["threat"] = e.get("threat")
DATA = json.dumps(pts, ensure_ascii=False)

nsp = len({p["s"] for p in pts})
nfam = len({p["famSci"] for p in pts})
ngen = len({p["genSci"] for p in pts})
els = [p["y"] for p in pts]
dist = int(round(pts[-1]["x"]))
xmax = int(math.ceil(pts[-1]["x"] / 25) * 25)
climb = int(round(pts[-1]["y"] - pts[0]["y"]))
e0, e1 = int(pts[0]["y"]), int(pts[-1]["y"])

HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>二格山稜線 植被海拔剖面圖 · 2026-04-25</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-zoom/2.0.1/chartjs-plugin-zoom.min.js"></script>
<style>
:root{--green:#587A30;--green2:#90B821;--gray:#666;--gray2:#B2B2B2;--yellow:#FFD900;--red:#E8380D;--ink:#3a3a36}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font-family:"Noto Sans TC",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1000px;margin:0 auto;padding:46px 28px 36px}
h1{font-weight:700;font-size:25px;color:var(--green);margin:0 0 6px;letter-spacing:.5px}
.sub{font-size:14px;color:var(--gray);margin:0 0 22px}
.cards{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:0 0 22px}
.card{background:#f5f4ef;border-radius:10px;padding:11px 12px}
.card .lbl{font-size:12px;color:var(--gray);margin-bottom:4px}
.card .val{font-size:22px;font-weight:500;color:var(--ink);line-height:1.15}
.card .sub2{font-size:11px;color:var(--gray2);margin-top:2px}
.card select{width:100%;font-family:inherit;font-size:13px;color:var(--ink);background:#fff;
  border:0.5px solid var(--gray2);border-radius:6px;padding:7px 6px;margin-top:3px;cursor:pointer}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:var(--gray);margin:0 0 10px}
.legend i{display:inline-block;vertical-align:middle;margin-right:6px}
.dot{width:11px;height:11px;border-radius:50%}
.diam{width:10px;height:10px;background:var(--green);border:1.5px solid var(--red);transform:rotate(45deg)}
.ctrl{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:0 0 8px;font-size:12px;color:var(--gray2)}
.ctrl button{font-family:inherit;font-size:12px;color:var(--gray);background:#fff;border:0.5px solid var(--gray2);
  border-radius:6px;padding:5px 10px;cursor:pointer}
.ctrl button:active{transform:scale(.97)}
.chartbox{position:relative;width:100%;height:450px;touch-action:none}
.ctt{position:fixed;opacity:0;transition:opacity .12s;background:#fff;z-index:30;font-size:12px;line-height:1.45;
  border:0.5px solid var(--gray2);border-radius:8px;padding:8px}
.ctt.float{width:178px;pointer-events:none}
.ctt.float img{width:100%;height:118px;object-fit:cover;border-radius:6px;margin-bottom:6px;display:block;background:#f1efe8}
.ctt.sheet{left:0;right:0;bottom:0;width:100%;border:none;border-top:0.5px solid var(--gray2);border-radius:12px 12px 0 0;
  box-shadow:0 -2px 14px rgba(0,0,0,.10);padding:12px 16px;display:flex;gap:12px;align-items:center;pointer-events:auto}
.ctt.sheet img{width:88px;height:88px;flex:0 0 auto;object-fit:cover;border-radius:8px;background:#f1efe8;margin:0}
.ctt .nm{font-weight:700;color:var(--green);font-size:15px}
.ctt .sci{font-style:italic;color:var(--gray)}
.ctt .fam{color:var(--gray)}
.ctt .lnk{display:inline-block;margin-top:6px;color:var(--green);font-weight:500;text-decoration:none}
.foot{margin-top:22px;font-size:11.5px;color:var(--gray2);line-height:1.6}
@media(max-width:760px){
  .wrap{padding:24px 16px 30px}
  .cards{grid-template-columns:repeat(3,1fr);gap:8px}
  .chartbox{height:400px}
}
@media(max-width:480px){
  h1{font-size:20px}.sub{font-size:13px;margin-bottom:16px}
  .cards{grid-template-columns:repeat(2,1fr)}
  .card .val{font-size:19px}
}
</style>
</head>
<body>
<div class="wrap">
  <h1>二格山稜線 · 植被海拔剖面圖</h1>
  <p class="sub">2026-04-25 踏查 · 稜線段（14:56 前）</p>

  <div class="cards">
    <div class="card"><div class="lbl">觀察數 observations</div><div class="val">__N__</div></div>
    <div class="card"><div class="lbl">物種數 species</div><div class="val">__SP__</div></div>
    <div class="card"><div class="lbl">科別 family</div><select id="famSel" autocomplete="off"></select></div>
    <div class="card"><div class="lbl">屬別 genus</div><select id="genSel" autocomplete="off"></select></div>
    <div class="card"><div class="lbl">步道長 trail</div><div class="val">__DIST__ m</div></div>
    <div class="card"><div class="lbl">爬升 climb</div><div class="val">+__CLIMB__ m</div><div class="sub2">__E0__ → __E1__ m</div></div>
  </div>

  <div class="legend">
    <span><i class="dot" style="background:var(--green)"></i>研究等級 research</span>
    <span><i class="dot" style="background:var(--green2)"></i>需鑑定 needs-ID</span>
    <span><i class="diam"></i>GPS &gt;100 m · 位置/高程內插 interpolated</span>
  </div>

  <div class="ctrl">
    <span>縮放：雙指 / 滾輪　平移：拖曳　點選點位 → 該物種物候時間軸</span>
    <button id="rz" type="button">重置 reset</button>
  </div>

  <div class="chartbox"><canvas id="t" role="img"
    aria-label="二格山稜線植被海拔剖面圖，橫軸為沿步道水平距離，縱軸為海拔，點為植物觀察，可縮放、平移與依科屬篩選"></canvas></div>

  <p class="foot">
    資料來源 iNaturalist API（觀察者 bunnytailgrass，地點 二格山 place_id 130869）·
    海拔 SRTM 30 m（雙線性內插）· GPS &gt;100 m 之點，位置與高程以鄰近可靠點時間內插
    （避免錯誤定位導致高程突降）· 科/屬中拉名與特有/保育狀態：TaiCoL 臺灣物種名錄 ·
    資料快照 2026/04/25 · 14:41 CST · 色彩：荒野保護協會。
  </p>
</div>

<script>
var DATA = __DATA__;
var FAM='*', GEN='*', chart;
function isMobile(){return window.matchMedia('(max-width:760px)').matches;}
function gen(d){return d.genSci;}
function active(d){return (FAM==='*'||d.famSci===FAM)&&(GEN==='*'||gen(d)===GEN);}
function pcol(c){var d=c.raw;if(!active(d))return '#D3D1C7';return d.g==='research'?'#587A30':'#90B821';}
function pbord(c){var d=c.raw;if(!active(d))return '#D3D1C7';return d.fl?'#E8380D':'#ffffff';}
function pbw(c){return (c.raw.fl&&active(c.raw))?2.5:1;}
function prad(c){var d=c.raw;if(!active(d))return 2.5;return d.fl?5.5:4;}
function pstyle(c){return c.raw.fl?'rectRot':'circle';}
function extTip(ctx){
  var tip=ctx.tooltip, mob=isMobile();
  var el=document.getElementById('ctt');
  if(!el){el=document.createElement('div');el.id='ctt';document.body.appendChild(el);}
  if(tip.opacity===0){el.style.opacity=0;return;}
  var d=tip.dataPoints[0].raw;
  var uid='ERG-'+String(d.n).padStart(3,'0');
  var img=d.ph?('<img src="'+d.ph+'" alt="">'):'';
  var link=mob?('<a class="lnk" href="data/units/'+uid+'.html">查看物候時間軸 →</a>'):'';
  var bd=(d.end?'<span style="color:#3B6D11">⬥臺灣特有</span> ':'')+(d.threat?'<span style="color:#A32D2D">'+(['CR','EN','VU','NT'].indexOf(d.threat)>=0?'IUCN ':'紅皮書 ')+d.threat+'</span>':'');
  el.innerHTML=img+'<div>'+'<div class="nm">'+(d.c||'—')+'</div><div class="sci">'+d.s+
    '</div><div class="fam">'+(d.famZh||'')+' '+d.famSci+'</div><div class="fam">'+(d.genZh||'')+' '+d.genSci+'</div>'+
    (bd?'<div class="fam">'+bd+'</div>':'')+
    (d.fl?'<div class="fam" style="color:#E8380D">GPS ±'+Math.round(d.a)+'m</div>':'')+link+'</div>';
  if(mob){
    el.className='ctt sheet';
    el.style.left='0';el.style.right='0';el.style.bottom='0';el.style.top='auto';el.style.width='';
  }else{
    el.className='ctt float';
    var r=ctx.chart.canvas.getBoundingClientRect();
    var left=r.left+tip.caretX+16; if(left+186>window.innerWidth)left=r.left+tip.caretX-186; if(left<4)left=4;
    var top=r.top+tip.caretY-30; if(top<4)top=4;
    el.style.left=left+'px';el.style.top=top+'px';el.style.right='auto';el.style.bottom='auto';
  }
  el.style.opacity=1;
}
function fillFamilies(){
  var fc={}, fz={};
  DATA.forEach(function(d){fc[d.famSci]=(fc[d.famSci]||0)+1; fz[d.famSci]=d.famZh;});
  var keys=Object.keys(fc).sort(function(a,b){return fc[b]-fc[a];});
  var h='<option value="*">全部 all ('+keys.length+' 科)</option>';
  keys.forEach(function(k){h+='<option value="'+k+'">'+(fz[k]?fz[k]+' ':'')+k+' · '+fc[k]+'</option>';});
  document.getElementById('famSel').innerHTML=h;
}
function fillGenera(fam){
  var gc={}, gz={};
  DATA.forEach(function(d){if(fam==='*'||d.famSci===fam){gc[d.genSci]=(gc[d.genSci]||0)+1;gz[d.genSci]=d.genZh;}});
  var keys=Object.keys(gc).sort();
  var h='<option value="*">全部 all ('+keys.length+' 屬)</option>';
  keys.forEach(function(k){h+='<option value="'+k+'">'+(gz[k]?gz[k]+' ':'')+k+' · '+gc[k]+'</option>';});
  document.getElementById('genSel').innerHTML=h;
}
function go(){
  fillFamilies(); fillGenera('*');
  document.getElementById('famSel').onchange=function(){FAM=this.value;GEN='*';fillGenera(FAM);chart.update();};
  document.getElementById('genSel').onchange=function(){GEN=this.value;chart.update();};
  document.getElementById('rz').onclick=function(){if(chart.resetZoom)chart.resetZoom();};
  chart=new Chart(document.getElementById('t'),{type:'line',
    data:{datasets:[{data:DATA,borderColor:'#666666',borderWidth:1.5,fill:'start',
      backgroundColor:'rgba(178,178,178,0.20)',tension:0.3,
      pointBackgroundColor:pcol,pointBorderColor:pbord,pointBorderWidth:pbw,
      pointRadius:prad,pointStyle:pstyle,pointHoverRadius:function(c){return prad(c)+2;}}]},
    options:{responsive:true,maintainAspectRatio:false,
      interaction:{mode:'nearest',intersect:false},
      onClick:function(e,els){if(!isMobile()&&els.length){var n=DATA[els[0].index].n;
        location.href='data/units/ERG-'+String(n).padStart(3,'0')+'.html';}},
      plugins:{legend:{display:false},tooltip:{enabled:false,external:extTip},
        zoom:{pan:{enabled:true,mode:'x'},
              zoom:{wheel:{enabled:true},pinch:{enabled:true},mode:'x'},
              limits:{x:{min:0,max:__XMAX__,minRange:40}}}},
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
