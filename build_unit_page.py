#!/usr/bin/env python3
"""Phase-2: per-unit phenology timeline pages (day-of-year × year calendar with
phenophase colour + photo tooltips), with back / prev / next navigation.
Reads the registry + history store; writes data/units/<unit_id>.html.
Usage:  python3 build_unit_page.py ERG-052     # one unit
        python3 build_unit_page.py --all        # all 93 units"""
import json, os, sys, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REG = json.load(open(os.path.join(HERE, "data", "registry", "units.json")))
RECS = json.load(open(os.path.join(HERE, "data", "history", "records.json")))
TX = json.load(open(os.path.join(HERE, "data", "registry", "taxa_taicol.json")))
BYUNIT = collections.defaultdict(list)
for r in RECS:
    if r["observed_on"]:
        BYUNIT[r["unit_id"]].append(r)
ORDER = [x["unit_id"] for x in REG]
ZH = {"flower": "開花", "fruit": "結果", "bud": "花苞"}
OUTDIR = os.path.join(HERE, "data", "units")
os.makedirs(OUTDIR, exist_ok=True)

TPL = """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__UID__ · __SCI__ 物候時間軸</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{--green:#587A30;--green2:#90B821;--gray:#666;--gray2:#B2B2B2;--yellow:#FFD900;--red:#E8380D;--ink:#3a3a36}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font-family:"Noto Sans TC",system-ui,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:30px 26px 34px}
.nav{font-size:13px;margin:0 0 16px}.nav a{color:var(--green);text-decoration:none;margin-right:14px}
h1{font-weight:700;font-size:23px;color:var(--green);margin:0 0 2px}h1 .sci{font-style:italic;font-weight:500}
.sub{font-size:14px;color:var(--gray);margin:0 0 6px}
.note{font-size:12.5px;color:var(--gray);margin:0 0 18px}.note i{font-style:italic}
.bdg{font-size:12px;font-weight:500;padding:2px 9px;border-radius:11px;margin-left:8px;white-space:nowrap}
.bdg.end{background:#eaf3de;color:#3B6D11}.bdg.thr{background:#fcebeb;color:#A32D2D}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:0 0 18px}
@media(max-width:600px){.cards{grid-template-columns:repeat(2,1fr)}}
.card{background:#f5f4ef;border-radius:10px;padding:11px 12px}
.card .lbl{font-size:12px;color:var(--gray)}.card .val{font-size:22px;font-weight:500}
.card .sub2{font-size:11px;color:var(--gray2);margin-top:2px}
.legend{display:flex;flex-wrap:wrap;gap:15px;font-size:13px;color:var(--gray);margin:0 0 8px}
.legend i{display:inline-block;width:11px;height:11px;border-radius:50%;vertical-align:middle;margin-right:6px}
.insight{font-size:13px;color:var(--green);margin:0 0 14px;min-height:1px}
.filt{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px;font-size:13px;align-items:center}
.filt button{font-family:inherit;font-size:13px;color:var(--gray);background:#fff;border:0.5px solid var(--gray2);border-radius:8px;padding:6px 12px;cursor:pointer}
.filt button.on{background:var(--green);color:#fff;border-color:transparent;font-weight:500}
.chartbox{position:relative;width:100%;height:430px}
.ctt{position:fixed;opacity:0;transition:opacity .12s;width:170px;background:#fff;border:0.5px solid var(--gray2);
  border-radius:8px;padding:8px;z-index:30;font-size:12px;line-height:1.45;pointer-events:none}
.ctt img{width:100%;height:118px;object-fit:cover;border-radius:6px;margin-bottom:6px;display:block;background:#f1efe8}
.ctt .ph{font-weight:700;color:var(--green)}.ctt .mt{color:var(--gray)}
.foot{margin-top:20px;font-size:11.5px;color:var(--gray2);line-height:1.6}
</style></head><body><div class="wrap">
<div class="nav"><a href="../../index.html">← 剖面圖 transect</a>__PN__</div>
<h1>__UID__ · <span class="sci">__SCI__</span> __CN____BADGES__</h1>
<p class="sub">__FAMZH__ __FAMSCI__　·　屬 __GENZH__ __GENSCI__　·　海拔 __EL__ m · 步道 __DX__ m　|　二格山稜線長期定點</p>
__ACCNOTE__
<div class="cards">
  <div class="card"><div class="lbl">觀察數 observations</div><div class="val">__NOBS__</div></div>
  <div class="card"><div class="lbl">年期 years</div><div class="val">__NYR__</div><div class="sub2">__YSPAN__</div></div>
  <div class="card"><div class="lbl">觀察者 observers</div><div class="val">__NOB__</div></div>
  <div class="card"><div class="lbl">物候標記 phenophase</div><div class="val">__NPH__</div><div class="sub2">__PHBR__</div></div>
</div>
<div class="legend">
  <span><i style="background:#E8380D"></i>開花 flower</span>
  <span><i style="background:#FFD900;border:1px solid #BA7517"></i>結果 fruit</span>
  <span><i style="background:#90B821"></i>花苞 bud</span>
  <span><i style="background:#CFCDC4"></i>未標記（僅照片）photo only</span>
</div>
<div class="legend" style="color:var(--gray2)">距樣點 GPS 距離（形狀 shape）：<span>● ≤50 m 此株 on-spot</span><span>▲ 50–250 m 鄰近 near</span><span>◆ &gt;250 m 他處同種 elsewhere</span></div>
<p class="insight">__INSIGHT__</p>
<p class="insight" style="color:var(--gray);margin-top:-8px">__DISTSUM__</p>
<div class="filt"><span style="color:var(--gray2)">顯示 show：</span>
  <button data-t="0" class="on">全部 all</button>
  <button data-t="250">≤250 m 鄰近 near</button>
  <button data-t="50">≤50 m 此株 on-spot</button></div>
<div class="chartbox"><canvas id="c" role="img" aria-label="__UID__ 物候時間軸：橫軸為一年中的日序（月份），縱軸為年份，點為觀察，顏色為物候階段，可依距樣點距離篩選"></canvas></div>
<p class="foot">資料來源 iNaturalist（地點 二格山 place_id 130869，同種就近歸入此樣點）· 物候階段取自 iNat 註記（term 12：開花/結果/花苞）；其餘為僅有照片之觀察，葉相需由照片判讀 · 學名/科屬中拉名/特有/保育：TaiCoL 臺灣物種名錄 · 點擊點位開啟 iNaturalist · 色彩：荒野保護協會。</p>
</div>
<script>
var DATA=__DATA__;
function col(p){if(p.indexOf('flower')>=0)return '#E8380D';if(p.indexOf('fruit')>=0)return '#FFD900';if(p.indexOf('bud')>=0)return '#90B821';return '#CFCDC4';}
function bord(p){if(p.indexOf('fruit')>=0)return '#BA7517';if(!p)return '#B2B2B2';return '#ffffff';}
function shp(dm){return (dm==null||dm<=50)?'circle':(dm<=250?'triangle':'rectRot');}
var ZH={flower:'開花',fruit:'結果',bud:'花苞'};
function phZh(p){return p?p.split(';').map(function(x){return ZH[x]||x;}).join('、'):'（未標記）';}
function extTip(ctx){var tip=ctx.tooltip;var el=document.getElementById('ctt');
  if(!el){el=document.createElement('div');el.id='ctt';el.className='ctt';document.body.appendChild(el);}
  if(tip.opacity===0){el.style.opacity=0;return;}
  var d=tip.dataPoints[0].raw;
  el.innerHTML=(d.ph?'<img src="'+d.ph+'" alt="">':'')+'<div class="ph">'+phZh(d.p)+'</div>'+
    '<div class="mt">'+d.d+'　'+d.q+'</div><div class="mt">@'+d.ob+'　·　距樣點 '+(d.dm==null?'?':Math.round(d.dm))+' m</div>';
  var r=ctx.chart.canvas.getBoundingClientRect();var left=r.left+tip.caretX+14;
  if(left+178>window.innerWidth)left=r.left+tip.caretX-178;if(left<4)left=4;
  var top=r.top+tip.caretY-20;if(top<4)top=4;
  el.style.left=left+'px';el.style.top=top+'px';el.style.opacity=1;}
var MS=[1,32,60,91,121,152,182,213,244,274,305,335];
var ML=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
var ALL=DATA.map(function(d){return Object.assign({x:d.doy,y:d.yj},d);});
var chart=new Chart(document.getElementById('c'),{type:'scatter',
 data:{datasets:[{data:ALL,
   pointBackgroundColor:function(c){return col(c.raw.p);},pointBorderColor:function(c){return bord(c.raw.p);},
   pointBorderWidth:function(c){return c.raw.p?1.5:1;},
   pointRadius:function(c){return c.raw.p?6:4;},pointHoverRadius:function(c){return (c.raw.p?6:4)+2;},
   pointStyle:function(c){return shp(c.raw.dm);}}]},
 options:{responsive:true,maintainAspectRatio:false,
   onClick:function(e,el,ch){if(el.length)window.open('https://www.inaturalist.org/observations/'+ch.data.datasets[0].data[el[0].index].id,'_blank');},
   plugins:{legend:{display:false},tooltip:{enabled:false,external:extTip}},
   scales:{x:{min:1,max:366,title:{display:true,text:'一年中的日序 day of year',color:'#666'},
     grid:{color:'rgba(178,178,178,0.25)'},ticks:{color:'#666',autoSkip:false,callback:function(v){var i=MS.indexOf(v);return i>=0?ML[i]:'';}},
     afterBuildTicks:function(a){a.ticks=MS.map(function(v){return {value:v};});}},
    y:{min:__YMIN__,max:__YMAX__,title:{display:true,text:'年 year',color:'#666'},
     grid:{color:'rgba(178,178,178,0.25)'},ticks:{color:'#666',stepSize:1,callback:function(v){return Number.isInteger(v)?v:'';}}}}}});
document.querySelectorAll('.filt button').forEach(function(b){b.onclick=function(){
  document.querySelectorAll('.filt button').forEach(function(x){x.classList.remove('on');});
  b.classList.add('on');var t=+b.getAttribute('data-t');
  chart.data.datasets[0].data=t?ALL.filter(function(d){return d.dm!=null&&d.dm<=t;}):ALL;chart.update();};});
</script></body></html>"""


def build(i):
    u = REG[i]
    UNIT = u["unit_id"]
    e = TX.get(u["scientific"], {})
    fam_sci = e.get("fam_sci") or u["family"]
    fam_zh = e.get("fam_zh") or (u["family_zh"] or "")
    gen_sci = e.get("gen_sci") or u["scientific"].split(" ")[0]
    gen_zh = e.get("gen_zh") or ""
    threat = e.get("threat")
    badges = ""
    if e.get("is_endemic"):
        badges += '<span class="bdg end">臺灣特有</span>'
    if threat:
        lab = ("IUCN " + threat) if threat in ("CR", "EN", "VU", "NT") else ("紅皮書 " + threat)
        badges += f'<span class="bdg thr">{lab}</span>'
    acc = e.get("accepted_sci")
    accnote = (f'<p class="note">臺灣接受學名 TaiCoL：<i>{acc}</i></p>'
               if acc and acc != u["scientific"] else "")
    rows = BYUNIT.get(UNIT, [])
    pts = []
    for r in rows:
        dt = datetime.date.fromisoformat(r["observed_on"])
        pts.append({"yr": dt.year, "doy": dt.timetuple().tm_yday, "d": r["observed_on"],
                    "p": r["phenophase"], "ph": r["photo"], "ob": r["user"],
                    "q": r["quality"], "id": r["obs_id"], "dm": r.get("dist_to_unit_m")})
    pts.sort(key=lambda x: x["d"])
    g = collections.defaultdict(list)
    for k, p in enumerate(pts):
        g[(p["yr"], p["doy"])].append(k)
    for idxs in g.values():
        kk = len(idxs)
        for j, k in enumerate(idxs):
            pts[k]["yj"] = round(pts[k]["yr"] + (j - (kk - 1) / 2) * 0.13, 3)
    years = sorted({p["yr"] for p in pts}) or [2026]
    nobs = len(pts)
    nob = len({p["ob"] for p in pts})
    pc = collections.Counter(ph for p in pts for ph in (p["p"].split(";") if p["p"] else []))
    npheno = sum(1 for p in pts if p["p"])
    dm = sorted(p["dm"] for p in pts if p["dm"] is not None)
    near = sum(1 for x in dm if x <= 50)
    mid = sum(1 for x in dm if 50 < x <= 250)
    far = len(dm) - near - mid
    med = int(dm[len(dm) // 2]) if dm else 0
    distsum = (f"距樣點 GPS 距離（形狀）：● 此株 ≤50 m {near} · ▲ 鄰近 50–250 m {mid} · "
               f"◆ 他處同種 &gt;250 m {far}（中位 {med} m）" if dm else "無 GPS 距離資料")
    spring = sum(1 for p in pts if 60 <= p["doy"] <= 151)
    if nobs == 0:
        insight = "尚無歷史觀察，後續每日同步將累積。"
    elif UNIT == "ERG-052":
        insight = (f"觀察高峰落在 3–5 月（{100*spring//nobs}% 的觀察），對應金毛杜鵑花期；"
                   "全年其餘月份為營養／果期照片。")
    else:
        insight = f"3–5 月觀察占 {100*spring//nobs}%；灰點為僅有照片、待判讀葉/花/果。"
    phbr = " / ".join(f"{lab}{n}" for lab, n in
                      [("花", pc.get("flower", 0)), ("果", pc.get("fruit", 0)), ("苞", pc.get("bud", 0))] if n) or "—"
    # prev / next nav
    pn = []
    if i > 0:
        pn.append(f'<a href="{ORDER[i-1]}.html">‹ {ORDER[i-1]}</a>')
    if i < len(ORDER) - 1:
        pn.append(f'<a href="{ORDER[i+1]}.html">{ORDER[i+1]} ›</a>')
    rep = {"__UID__": UNIT, "__SCI__": u["scientific"], "__CN__": u["common"] or "",
           "__BADGES__": badges, "__ACCNOTE__": accnote,
           "__FAMZH__": fam_zh, "__FAMSCI__": fam_sci, "__GENZH__": gen_zh, "__GENSCI__": gen_sci,
           "__EL__": str(int(u["elev_m"])),
           "__DX__": str(int(u["dist_m"])), "__NOBS__": str(nobs), "__NYR__": str(len(years)),
           "__YSPAN__": f"{years[0]}–{years[-1]}", "__NOB__": str(nob), "__NPH__": str(npheno),
           "__PHBR__": phbr, "__INSIGHT__": insight, "__DISTSUM__": distsum,
           "__PN__": (" · " + " ".join(pn)) if pn else "",
           "__YMIN__": str(years[0] - 0.6), "__YMAX__": str(years[-1] + 0.6),
           "__DATA__": json.dumps(pts, ensure_ascii=False)}
    html = TPL
    for k, v in rep.items():
        html = html.replace(k, v)
    open(os.path.join(OUTDIR, f"{UNIT}.html"), "w").write(html)
    return nobs


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "ERG-052"
    if arg == "--all":
        tot = sum(build(i) for i in range(len(REG)))
        print(f"wrote {len(REG)} unit pages -> {OUTDIR}  ({tot} records total)")
    else:
        i = ORDER.index(arg)
        n = build(i)
        print(f"wrote {arg}.html ({n} obs)")


if __name__ == "__main__":
    main()
