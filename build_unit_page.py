#!/usr/bin/env python3
"""Phase-2 prototype: per-unit phenology timeline page (day-of-year × year calendar
with phenophase colour + photo tooltips). Reads the registry + history store and
writes data/units/<unit_id>.html. Usage: python3 build_unit_page.py [ERG-052]"""
import json, os, sys, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REG = json.load(open(os.path.join(HERE, "data", "registry", "units.json")))
RECS = json.load(open(os.path.join(HERE, "data", "history", "records.json")))
UNIT = sys.argv[1] if len(sys.argv) > 1 else "ERG-052"
u = next(x for x in REG if x["unit_id"] == UNIT)

rows = [r for r in RECS if r["unit_id"] == UNIT and r["observed_on"]]
pts = []
for r in rows:
    dt = datetime.date.fromisoformat(r["observed_on"])
    pts.append({"yr": dt.year, "doy": dt.timetuple().tm_yday, "d": r["observed_on"],
                "p": r["phenophase"], "ph": r["photo"], "ob": r["user"],
                "q": r["quality"], "id": r["obs_id"]})
pts.sort(key=lambda x: x["d"])
# spread overlapping (year, doy) points vertically for legibility
g = collections.defaultdict(list)
for i, p in enumerate(pts):
    g[(p["yr"], p["doy"])].append(i)
for idxs in g.values():
    k = len(idxs)
    for j, i in enumerate(idxs):
        pts[i]["yj"] = round(pts[i]["yr"] + (j - (k - 1) / 2) * 0.13, 3)

years = sorted({p["yr"] for p in pts})
nobs = len(pts)
nobservers = len({p["ob"] for p in pts})
pc = collections.Counter(ph for p in pts for ph in (p["p"].split(";") if p["p"] else []))
npheno = sum(1 for p in pts if p["p"])
DATA = json.dumps(pts, ensure_ascii=False)

HTML = """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__UID__ · __SCI__ 物候時間軸</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{--green:#587A30;--green2:#90B821;--gray:#666;--gray2:#B2B2B2;--yellow:#FFD900;--red:#E8380D;--ink:#3a3a36}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font-family:"Noto Sans TC",system-ui,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:40px 26px 34px}
h1{font-weight:700;font-size:23px;color:var(--green);margin:0 0 2px}
h1 .sci{font-style:italic;font-weight:500}
.sub{font-size:14px;color:var(--gray);margin:0 0 20px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:0 0 18px}
@media(max-width:600px){.cards{grid-template-columns:repeat(2,1fr)}}
.card{background:#f5f4ef;border-radius:10px;padding:11px 12px}
.card .lbl{font-size:12px;color:var(--gray)}.card .val{font-size:22px;font-weight:500}
.card .sub2{font-size:11px;color:var(--gray2);margin-top:2px}
.legend{display:flex;flex-wrap:wrap;gap:15px;font-size:13px;color:var(--gray);margin:0 0 8px}
.legend i{display:inline-block;width:11px;height:11px;border-radius:50%;vertical-align:middle;margin-right:6px}
.insight{font-size:13px;color:var(--green);margin:0 0 14px}
.chartbox{position:relative;width:100%;height:430px}
.ctt{position:fixed;opacity:0;transition:opacity .12s;width:170px;background:#fff;border:0.5px solid var(--gray2);
  border-radius:8px;padding:8px;z-index:30;font-size:12px;line-height:1.45;pointer-events:none}
.ctt img{width:100%;height:118px;object-fit:cover;border-radius:6px;margin-bottom:6px;display:block;background:#f1efe8}
.ctt .ph{font-weight:700;color:var(--green)}.ctt .mt{color:var(--gray)}
.foot{margin-top:20px;font-size:11.5px;color:var(--gray2);line-height:1.6}
</style></head><body><div class="wrap">
<h1>__UID__ · <span class="sci">__SCI__</span> __CN__</h1>
<p class="sub">__FZ__ __FAM__ · 海拔 __EL__ m · 步道 __DX__ m　|　二格山稜線長期定點 · 物候時間軸</p>
<div class="cards">
  <div class="card"><div class="lbl">觀察數 observations</div><div class="val">__NOBS__</div></div>
  <div class="card"><div class="lbl">年期 years</div><div class="val">__NYR__</div><div class="sub2">__Y0__–__Y1__</div></div>
  <div class="card"><div class="lbl">觀察者 observers</div><div class="val">__NOB__</div></div>
  <div class="card"><div class="lbl">物候標記 phenophase</div><div class="val">__NPH__</div><div class="sub2">__PHBR__</div></div>
</div>
<div class="legend">
  <span><i style="background:#E8380D"></i>開花 flower</span>
  <span><i style="background:#FFD900;border:1px solid #BA7517"></i>結果 fruit</span>
  <span><i style="background:#90B821"></i>花苞 bud</span>
  <span><i style="background:#CFCDC4"></i>未標記（僅照片）photo only</span>
</div>
<p class="insight">__INSIGHT__</p>
<div class="chartbox"><canvas id="c" role="img" aria-label="__UID__ 物候時間軸：橫軸為一年中的日序（月份），縱軸為年份，點為觀察，顏色為物候階段"></canvas></div>
<p class="foot">資料來源 iNaturalist（地點 二格山 place_id 130869，同種就近歸入此樣點）· 物候階段取自 iNat 註記（term 12：開花/結果/花苞）；其餘為僅有照片之觀察，葉相需由照片判讀 · 點擊點位開啟 iNaturalist · 色彩：荒野保護協會。</p>
</div>
<script>
var DATA=__DATA__;
function col(p){if(p.indexOf('flower')>=0)return '#E8380D';if(p.indexOf('fruit')>=0)return '#FFD900';if(p.indexOf('bud')>=0)return '#90B821';return '#CFCDC4';}
function bord(p){if(p.indexOf('fruit')>=0)return '#BA7517';if(!p)return '#B2B2B2';return '#ffffff';}
var ZH={flower:'開花',fruit:'結果',bud:'花苞'};
function phZh(p){return p?p.split(';').map(function(x){return ZH[x]||x;}).join('、'):'（未標記）';}
function extTip(ctx){var tip=ctx.tooltip;var el=document.getElementById('ctt');
  if(!el){el=document.createElement('div');el.id='ctt';el.className='ctt';document.body.appendChild(el);}
  if(tip.opacity===0){el.style.opacity=0;return;}
  var d=tip.dataPoints[0].raw;
  el.innerHTML=(d.ph?'<img src="'+d.ph+'" alt="">':'')+'<div class="ph">'+phZh(d.p)+'</div>'+
    '<div class="mt">'+d.d+'　'+d.q+'</div><div class="mt">@'+d.ob+'</div>';
  var r=ctx.chart.canvas.getBoundingClientRect();var left=r.left+tip.caretX+14;
  if(left+178>window.innerWidth)left=r.left+tip.caretX-178;if(left<4)left=4;
  var top=r.top+tip.caretY-20;if(top<4)top=4;
  el.style.left=left+'px';el.style.top=top+'px';el.style.opacity=1;}
var MS=[1,32,60,91,121,152,182,213,244,274,305,335];
var ML=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
new Chart(document.getElementById('c'),{type:'scatter',
 data:{datasets:[{data:DATA.map(function(d){return Object.assign({x:d.doy,y:d.yj},d);}),
   pointBackgroundColor:function(c){return col(c.raw.p);},
   pointBorderColor:function(c){return bord(c.raw.p);},
   pointBorderWidth:function(c){return c.raw.p?1.5:1;},
   pointRadius:function(c){return c.raw.p?6:4;},pointHoverRadius:function(c){return (c.raw.p?6:4)+2;}}]},
 options:{responsive:true,maintainAspectRatio:false,
   onClick:function(e,el){if(el.length)window.open('https://www.inaturalist.org/observations/'+DATA[el[0].index].id,'_blank');},
   plugins:{legend:{display:false},tooltip:{enabled:false,external:extTip}},
   scales:{x:{min:1,max:366,title:{display:true,text:'一年中的日序 day of year',color:'#666'},
     grid:{color:'rgba(178,178,178,0.25)'},ticks:{color:'#666',autoSkip:false,
       callback:function(v){var i=MS.indexOf(v);return i>=0?ML[i]:'';}},afterBuildTicks:function(a){a.ticks=MS.map(function(v){return {value:v};});}},
    y:{min:__Y0__-0.6,max:__Y1__+0.6,title:{display:true,text:'年 year',color:'#666'},
     grid:{color:'rgba(178,178,178,0.25)'},ticks:{color:'#666',stepSize:1,callback:function(v){return Number.isInteger(v)?v:'';}}}}}});
</script></body></html>"""

# spring (Mar-May) share of observations -> flowering-season signal
spring = sum(1 for p in pts if 60 <= p["doy"] <= 151)
insight = (f"觀察高峰落在 3–5 月（{100*spring//nobs}% 的觀察），對應金毛杜鵑花期；"
           f"全年其餘月份為營養／果期照片。") if UNIT == "ERG-052" else \
          f"3–5 月觀察占 {100*spring//nobs}%。"
phbr = " / ".join(f"{ZH}{n}" for ZH, n in [("花", pc.get("flower", 0)), ("果", pc.get("fruit", 0)), ("苞", pc.get("bud", 0))] if n)
ZH = {"flower": "開花", "fruit": "結果", "bud": "花苞"}

rep = {"__UID__": UNIT, "__SCI__": u["scientific"], "__CN__": u["common"] or "",
       "__FZ__": u["family_zh"] or "", "__FAM__": u["family"], "__EL__": str(int(u["elev_m"])),
       "__DX__": str(int(u["dist_m"])), "__NOBS__": str(nobs), "__NYR__": str(len(years)),
       "__Y0__": str(years[0]), "__Y1__": str(years[-1]), "__NOB__": str(nobservers),
       "__NPH__": str(npheno), "__PHBR__": phbr or "—", "__INSIGHT__": insight, "__DATA__": DATA}
for k, v in rep.items():
    HTML = HTML.replace(k, v)

os.makedirs(os.path.join(HERE, "data", "units"), exist_ok=True)
out = os.path.join(HERE, "data", "units", f"{UNIT}.html")
open(out, "w").write(HTML)
print(f"wrote {out} | {nobs} obs, {len(years)} yr ({years[0]}-{years[-1]}), "
      f"{nobservers} observers, {npheno} phenophase ({phbr})")
