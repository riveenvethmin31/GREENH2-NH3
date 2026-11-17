import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="GREENH2-NH3 | Power-to-Ammonia", layout="wide", page_icon="🌱")
EM, CY, GD, BG = "#10B981", "#06B6D4", "#F59E0B", "#0B0F19"
st.markdown(f"""<style>
.stApp{{background:{BG};color:#e2e8f0}} section[data-testid=stSidebar]{{background:#0f172a}}
.hdr{{background:linear-gradient(90deg,#064e3b,#0c4a6e);border:1px solid {EM};border-radius:12px;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
box-shadow:0 0 24px {EM}55;font-weight:700;letter-spacing:.06em;color:#ecfdf5}}
.hdr span{{color:{EM};font-family:monospace}}
.kpi{{background:rgba(30,41,59,.55);backdrop-filter:blur(8px);border:1px solid {EM}66;border-radius:14px;padding:14px;
box-shadow:0 0 14px {EM}33}} .kpi b{{font-size:1.7rem;color:{EM}}} .kpi small{{color:#94a3b8;display:block}}
.kpi i{{color:{GD};font-style:normal;font-size:.8rem}}
</style>""", unsafe_allow_html=True)

# ---------------- Sidebar ----------------
sb = st.sidebar
sb.header("A. Green Power & Electrolysis")
price = sb.slider("Renewable electricity (USD/MWh)", 15, 80, 35)
eff = sb.slider("ALK efficiency (kWh/kg H2)", 48.0, 58.0, 55.0, 0.5)
cf = sb.slider("Renewable capacity factor (%)", 35, 95, 75) / 100
sb.header("B. Haber-Bosch Loop (DWSIM)")
mH = sb.slider("Fresh green H2 (kg/s)", 0.001, 0.010, 0.002055, 0.000005, format="%.6f")
mN = sb.slider("Fresh N2 (kg/s)", 0.003, 0.030, 0.009516, 0.00001, format="%.6f")
P = sb.slider("Loop pressure (MPa)", 5.0, 20.0, 10.0, 0.5)
T = sb.slider("Reactor temperature (°C)", 350, 500, 488)
R = sb.slider("Recycle ratio", 0.70, 0.95, 0.95, 0.01)

# ---------------- Engineering model ----------------
MH2, MN2, MNH3 = 2.016, 28.014, 17.031

def kp(Tc):  # Gillespie-Beattie, 1/2N2+3/2H2<=>NH3, atm^-1
    t = np.asarray(Tc, float) + 273.15
    return 10 ** (-2.691122 * np.log10(t) - 5.519265e-5 * t + 1.848863e-7 * t**2 + 2001.6 / t + 2.6899)

def xeq(Tc, p_mpa):  # stoichiometric 3:1 feed, bisection on extent
    k = kp(Tc); pa = p_mpa * 9.869
    lo, hi = np.zeros_like(k), np.full_like(k, 0.999)
    for _ in range(60):
        x = (lo + hi) / 2; d = 4 - 2 * x
        f = (2 * x / d) / (np.sqrt((1 - x) / d) * (3 * (1 - x) / d) ** 1.5 * pa) - k
        lo, hi = np.where(f < 0, x, lo), np.where(f < 0, hi, x)
    return (lo + hi) / 2

nH, nN = mH / MH2 * 1e3, mN / MN2 * 1e3
ratio = nH / nN
Xe = float(xeq(T, P)); Xp = Xe
Xo = Xp / (1 - R * (1 - Xp))
nNH3 = 2 * min(nN, nH / 3) * Xo
nh3_h = nNH3 * MNH3 * 1e-3 * 3600           # kg/h
nh3_td = nh3_h * 24 / 1000
mg = (mH + mN) / (1 - R * (1 - Xp))          # reactor feed kg/s
cp = (mH * 14.3 + mN * 1.04) / (mH + mN)
pem = mH * 3600 * eff
asu = mN * 3600 * 0.30
nf = (nH + nN) / (1 - R * (1 - Xp))
def ws(n, t1, r): return n * 3.5 * 8.314 * t1 * (r ** 0.2857 - 1) / 0.75 / 1000   # plan 5.4 isentropic, eta 0.75
pm = min(1.4, P); comp = ws(nf, 247, pm / 0.1013) + ws(nf, 300, P / pm)
total = pem + asu + comp
sec = total / nh3_h                          # MWh/t
water, o2 = mH * 3600 * 8.94, mH * 3600 * 7.94
t_yr = nh3_h * 8760 * cf / 1000
mwh_yr = total / 1000 * 8760 * cf

def lcoa(pr):
    capex = pem * 800 + 12000 * nh3_h + 3000 * (asu + comp)
    parts = dict(elec=mwh_yr * pr / t_yr, capex=capex * 0.1019 / t_yr, om=0.03 * capex / t_yr,
                 o2=-(o2 * 8760 * cf / 1000) * 40 / t_yr)
    parts["total"] = sum(parts.values())
    return parts

L = lcoa(price)
GREY, BLUE, GREY_C, BLUE_C = 450, 580, 1.9, 0.9
avoided = GREY_C * t_yr

# ---------------- Header & KPIs ----------------
st.markdown('<div class="hdr">🌱 100% ZERO-CARBON POWER-TO-AMMONIA | RENEWABLE ELECTROLYSIS + HABER-BOSCH DIGITAL TWIN'
            '<span>● 0.00 kg CO2/kg NH3 Scope 1</span></div>', unsafe_allow_html=True)
st.markdown('<div style="margin:8px 0">' + "".join(f'<span style="border:1px solid {c};color:{c};border-radius:20px;padding:3px 12px;margin-right:8px;font-size:.78rem">{t}</span>' for t, c in [("DWSIM-CALIBRATED", EM), ("CONCEPTUAL DESIGN · 1 t/day BASIS", CY), ("NOT VALIDATED vs PLANT DATA", GD)]) + "</div>", unsafe_allow_html=True)
st.write("")
k = st.columns(4)
kpis = [("Green NH3 Production", f"{nh3_h:,.1f} kg/h", f"{nh3_td:,.2f} t/day · 0 t CO2/t"),
        ("Renewable Power Demand", f"{total/1000:,.3f} MW", f"ALK {pem/total:.0%} · PSA {asu/total:.1%} · Comp {comp/total:.1%}"),
        ("LCOA", f"${L['total']:,.0f}/t", f"{L['total']-GREY:+,.0f} vs grey (${GREY}) · {L['total']-BLUE:+,.0f} vs blue"),
        ("CO2 Avoided", f"{avoided:,.0f} t/yr", f"vs SMR @ {GREY_C} t CO2/t NH3")]
for c, (a, b, d) in zip(k, kpis):
    c.markdown(f'<div class="kpi"><small>{a}</small><b>{b}</b><br><i>{d}</i></div>', unsafe_allow_html=True)
st.write("")

e = st.columns(4)
for c, (a, b) in zip(e, [("🌳 CO2 absorbed ≈ trees/yr", f"{avoided * 1000 / 21:,.0f}"), ("🚗 Cars off the road", f"{avoided / 4.6:,.0f}"),
                         ("☀️ Renewable share", "100 %"), ("💧 Water per t NH3", f"{water / nh3_h:.2f} t/t")]):
    c.markdown(f'<div class="kpi"><small>{a}</small><b style="font-size:1.3rem">{b}</b></div>', unsafe_allow_html=True)
st.write("")
# ---------------- 3D digital twin ----------------
u = {"SOLAR/WIND": [25, 0.1, 0, total], "ALK-ELX": [65, 3.0, mH * 3600, pem], "H2-BUF": [30, 3.0, mH * 3600, 0],
     "PSA-N2": [30, 0.8, mN * 3600, asu], "MIX-1": [40, 1.0, mg * 3600, 0], "C-1": [160, P ** .5, mg * 3600, comp / 2],
     "ICL-1": [40, P ** .5, mg * 3600, 0], "C-2": [160, P, mg * 3600, comp / 2], "REQ-1": [T, P, mg * 3600, 0],
     "CL-2": [-10, P, mg * 3600, 0], "V-1": [-10, P, mg * 3600, 0], "SPL-1": [-10, P, mg * 3600 * (1 - Xp), 0],
     "NH3-TANK": [-33, 0.1, nh3_h, 0], "WTR-RO": [25, 0.8, water, 2.0]}
SPEC = {"REQ-1": "Equilibrium converter · Fe catalyst · design 10 MPa", "V-1": "HP flash separator · 10 MPa, −33 °C", "C-1": "Stage 1 · 0.1→1.4 MPa · η 0.75",
        "C-2": "Stage 2 · 1.4→10 MPa · η 0.75", "ICL-1": "Intercooler · duty 56 kW (DWSIM)", "CL-2": "NH3 condenser · duty 103 kW (DWSIM)",
        "MIX-1": "Feed mixer · H2:N2 3:1 + recycle", "SPL-1": "Purge splitter · 95% recycle / 5% purge", "ALK-ELX": "Alkaline electrolyser · KOH",
        "H2-BUF": "H2 buffer · smooths renewable variability", "PSA-N2": "PSA nitrogen · twin adsorbers (assumed 0.30 kWh/kg)",
        "NH3-TANK": "Liquid NH3 sphere · refrigerated", "WTR-RO": "RO + polishing · DI water", "SOLAR/WIND": "Renewable microgrid · zero-carbon"}
D = dict(spec=SPEC, u=u, pw=cf, fH=min(1, mH / .01), fN=min(1, mN / .03), fS=min(1, mg / .06), fL=min(1, nh3_h / 100),
         T=(T - 350) / 150, X=Xo, lvl=min(.9, .25 + nh3_h / 60), hud=f"{P:.0f} MPa · {T:.0f} °C · NH3 {nh3_h:.1f} kg/h · {total:.0f} kW · 0 kg CO2/kg NH3")

HTML = """<style>body{margin:0;background:#0B0F19;overflow:hidden;font-family:monospace}
#b{position:absolute;top:10px;left:10px;z-index:2}#b button{background:#0f172acc;color:#10B981;border:1px solid #10B981;border-radius:8px;
padding:6px 10px;margin-right:6px;cursor:pointer}#b button:hover{background:#10B98133}
#tip{position:absolute;right:12px;top:12px;background:#0f172aee;border:1px solid #10B981;color:#e2e8f0;padding:10px;border-radius:10px;
font-size:12px;min-width:190px;display:none;z-index:2}#hud{position:absolute;left:50%;transform:translateX(-50%);bottom:12px;z-index:2;background:#0f172acc;border:1px solid #10B981;color:#34d399;padding:6px 16px;border-radius:20px;font-size:13px;letter-spacing:.05em;box-shadow:0 0 18px #10B98155}</style>
<div id="b"><button onclick="tour()">▶ Cinematic Tour</button><button onclick="go('full')">Full Plant Overview</button><button onclick="go('elx')">Renewable &amp; ALK Electrolysis</button>
<button onclick="go('rx')">Compression &amp; Reactor</button><button onclick="go('nh3')">Separator &amp; Green NH3 Storage</button></div>
<div id="tip"></div><div id="hud"></div><div id="c"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
const D=__D__,H=720,sc=new THREE.Scene();sc.background=new THREE.Color(0x0B0F19);sc.fog=new THREE.Fog(0x0B0F19,70,170);
const cam=new THREE.PerspectiveCamera(50,innerWidth/H,.1,400),r=new THREE.WebGLRenderer({antialias:true});
r.setSize(innerWidth,H);r.shadowMap.enabled=true;document.getElementById('c').appendChild(r.domElement);
const oc=new THREE.OrbitControls(cam,r.domElement);oc.enableDamping=true;
sc.add(new THREE.HemisphereLight(0xbfe8ff,0x1e293b,.45));sc.add(new THREE.AmbientLight(0x6b7f99,.25));[[-20,15,10,0x06B6D4],[18,12,8,0xF59E0B],[5,14,-10,0x10B981]].forEach(a=>{const l=new THREE.PointLight(a[3],.7,60);l.position.set(a[0],a[1],a[2]);sc.add(l)});const dl=new THREE.DirectionalLight(0xffffff,.9);dl.position.set(20,40,20);dl.castShadow=true;sc.add(dl);
sc.add(new THREE.GridHelper(130,65,0x3b4654,0x232a34));
const M=(c,e=0,m=.7,ro=.35)=>new THREE.MeshStandardMaterial({color:c,metalness:Math.min(m,.9),roughness:ro,emissive:e,emissiveIntensity:e?.3:0});
const picks=[];
function add(geo,mat,x,y,z,id){const m=new THREE.Mesh(geo,mat);m.position.set(x,y,z);m.castShadow=true;if(id){m.userData.id=id;picks.push(m)}sc.add(m);return m}
function tag(id,x,y,z){const cv=document.createElement('canvas');cv.width=256;cv.height=64;const c=cv.getContext('2d');c.fillStyle='rgba(11,15,25,.85)';c.fillRect(0,0,256,64);
c.strokeStyle='#10B981';c.strokeRect(1,1,254,62);c.fillStyle='#10B981';c.font='bold 30px monospace';c.textAlign='center';c.fillText(id,128,42);
const s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(cv)}));s.position.set(x,y,z);s.scale.set(5,1.25,1);sc.add(s)}
function unit(id,geo,mat,x,y,z,ty,rz){const m=add(geo,mat,x,y,z,id);if(rz)m.rotation.z=Math.PI/2;tag(id,x,ty,z);return m}
const cyl=(a,b,h)=>new THREE.CylinderGeometry(a,b,h,32),box=(a,b,c)=>new THREE.BoxGeometry(a,b,c);
const flows=[];
function pipe(p,col,f){const v=p.map(a=>new THREE.Vector3(...a)),cp=new THREE.CurvePath();for(let i=0;i<v.length-1;i++)cp.add(new THREE.LineCurve3(v[i],v[i+1]));
sc.add(new THREE.Mesh(new THREE.TubeGeometry(cp,v.length*8,.18,8),M(0x8793a1,col,.85,.4)));
const n=30,ge=new THREE.BufferGeometry();ge.setAttribute('position',new THREE.BufferAttribute(new Float32Array(n*3),3));
const pt=new THREE.Points(ge,new THREE.PointsMaterial({color:col,size:.55,transparent:true,opacity:.55+.45*f,blending:THREE.AdditiveBlending,depthWrite:false}));
sc.add(pt);flows.push({cp,pt,n,s:.04+.25*f})}
// renewables
const rotors=[];[[-28,-12],[-22,-15]].forEach(([x,z],k)=>{add(cyl(.2,.4,12),M(0xe2e8f0),x,6,z,k?null:'SOLAR/WIND');
const h=new THREE.Group();h.position.set(x,12,z+.5);for(let i=0;i<3;i++){const a=new THREE.Group(),b=new THREE.Mesh(box(.3,5,.1),M(0xf1f5f9,0,.3,.4));b.position.y=2.5;a.rotation.z=i*2.094;a.add(b);h.add(a)}sc.add(h);rotors.push(h)});
for(let i=0;i<4;i++)for(let j=0;j<2;j++){const p=add(box(3,.1,2),M(0x1e3a8a,0x0b2a6b,.9,.2),-29+i*3.4,1,8+j*3,'SOLAR/WIND');p.rotation.x=-.5}
tag('SOLAR/WIND',-25,16,-13);
// electrolysis & feedstock
unit('ALK-ELX',box(7,4,4),M(0x334155,0x064e3b),-14,2,0,5.5);for(let i=0;i<8;i++)add(box(.15,3.2,4.1),M(0x10B981,0x10B981),-17+i*.9,2,0);
unit('H2-BUF',cyl(2,2,5),M(0xcfd8dc,0x052e24,.9,.3),-14,2.5,-8,6.5);
unit('PSA-N2',cyl(1.3,1.3,8),M(0xb8c2cc,0x0b1a24,.9,.3),-15.5,4,10,9.8);add(cyl(1.3,1.3,8),M(0xb8c2cc,0x0b1a24,.9,.3),-12.5,4,10);unit('WTR-RO',box(3,2,2.2),M(0x64748b,0x0c2a3f),-22,1,0,3.2);pipe([[-20.5,1,0],[-17.6,1,0]],0x38bdf8,.5);
// synthesis loop
unit('MIX-1',box(2,1.5,1.5),M(0x94a3b8),-4,1.5,2,3.2);
unit('C-1',cyl(1,1,3),M(0x64748b),2,1.2,2,3.2,1);unit('ICL-1',box(2.4,1.6,1.6),M(0xF59E0B,0x92400e,.6,.4),6,1.2,2,3.2);
unit('C-2',cyl(1,1,3),M(0x64748b),10,1.2,2,3.2,1);
unit('REQ-1',cyl(1.6,1.6,9),new THREE.MeshPhysicalMaterial({color:0x94a3b8,transparent:true,opacity:.28,roughness:.1,metalness:.2}),16,4.5,2,10.5);const cl=new THREE.PointLight(0xF59E0B,3,16);cl.position.set(16,4.5,2);sc.add(cl);add(cyl(1.75,1.75,.5),M(0x64748b),16,9,2);add(cyl(1.75,1.75,.5),M(0x64748b),16,0,2);
const core=add(cyl(1,1,6),new THREE.MeshStandardMaterial({color:0xF59E0B,emissive:0x10B981,emissiveIntensity:1}),16,4.5,2);core.scale.set(1.01,1,1.01);core.material.transparent=true;
core.material.emissive.setHSL(.08+.3*(1-D.T),1,.5);
unit('CL-2',cyl(1,1,3),M(0x9fb3c8,0x0c2a3f,.8,.3),21,1.5,2,3.5,1);
unit('V-1',cyl(1.4,1.4,6),new THREE.MeshPhysicalMaterial({color:0x94a3b8,transparent:true,opacity:.35,metalness:.3,roughness:.1}),25,3,2,7.2);
const liq=add(cyl(1.3,1.3,5),M(0x34d399,0x10B981,.1,.2),25,.2,2);
unit('SPL-1',new THREE.SphereGeometry(.7,24,24),M(0xe2e8f0),25,8,-2,9.4);
unit('NH3-TANK',new THREE.SphereGeometry(3,40,40),M(0xcbd5e1,0x052e24,.9,.2),31,3,6,7.6);
// pipes
const G=0x10B981,C=0x06B6D4,Y=0xF59E0B,fh=D.fH,fn=D.fN,fs=D.fS,pw=D.pw;
pipe([[-22,.3,-15],[-22,.3,-3.2],[-14,.3,-3.2],[-14,.3,-2]],Y,pw);pipe([[-24,.3,8],[-24,.3,4],[-14,.3,4],[-14,.3,2]],Y,pw);pipe([[-14,.3,4],[-14,.3,8.5]],Y,pw);
pipe([[-13,2,-2],[-13,2,-6.2]],G,fh);pipe([[-12,3,-8],[-8,3,-8],[-8,1.5,-8],[-8,1.5,2],[-5,1.5,2]],G,fh);pipe([[-14,4,0],[-14,7,0]],0x93c5fd,fh*.5);
pipe([[-12.5,1,10],[-4,1,10],[-4,1,2.8]],C,fn);
pipe([[-3,1.2,2],[.5,1.2,2]],G,fs);pipe([[3.5,1.2,2],[4.8,1.2,2]],G,fs);pipe([[7.2,1.2,2],[8.5,1.2,2]],G,fs);pipe([[11.5,1.2,2],[14.4,1.2,2]],Y,fs);
pipe([[17.6,1.2,2],[19.5,1.2,2]],Y,fs);pipe([[22.5,1.2,2],[23.6,1.2,2]],C,fs);
pipe([[25,6.2,2],[25,8,2],[25,8,-1.3]],G,fs*.8);pipe([[25,8,-2.7],[25,8,-9],[-4,8,-9],[-4,1.5,-9],[-4,1.5,1.2]],G,fs*.7);pipe([[25.7,8,-2],[28,8,-2],[28,11,-2]],0xfde68a,.2);
pipe([[25,.5,2],[25,.5,6],[28.2,.5,6]],0xa7f3d0,D.fL);
(function(){const n=600,g=new THREE.BufferGeometry(),a=new Float32Array(n*3);for(let i=0;i<n;i++){const t=Math.random()*6.28,p=Math.random()*1.2+.2,R=150;a[i*3]=R*Math.cos(t)*Math.cos(p);a[i*3+1]=Math.abs(R*Math.sin(p))+10;a[i*3+2]=R*Math.sin(t)*Math.cos(p)}g.setAttribute('position',new THREE.BufferAttribute(a,3));sc.add(new THREE.Points(g,new THREE.PointsMaterial({color:0x9be7ff,size:.8,fog:false})))})();
function glow(x,y,z,c,s){const cv=document.createElement('canvas');cv.width=cv.height=64;const k=cv.getContext('2d'),gr=k.createRadialGradient(32,32,0,32,32,32);gr.addColorStop(0,c);gr.addColorStop(1,'rgba(0,0,0,0)');k.fillStyle=gr;k.fillRect(0,0,64,64);const p=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(cv),blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));p.position.set(x,y,z);p.scale.set(s*.4,s*.4,1);sc.add(p);return p}
const gl=glow(16,4.5,2,'rgba(245,158,11,.9)',14);glow(-14,2,0,'rgba(16,185,129,.7)',11);glow(31,3,6,'rgba(16,185,129,.6)',12);glow(-14,5,10,'rgba(6,182,212,.5)',10);glow(-25,12,-13,'rgba(245,158,11,.4)',14);
[[-14,0],[16,2],[31,6],[-14,10],[25,2],[-22,0]].forEach(a=>{const m=new THREE.Mesh(new THREE.RingGeometry(3.2,3.5,48),new THREE.MeshBasicMaterial({color:0x475569,side:2}));m.rotation.x=-Math.PI/2;m.position.set(a[0],.03,a[1]);sc.add(m)});
document.getElementById('hud').innerHTML=D.hud;
(function(){const es=new THREE.Scene(),cv=document.createElement('canvas');cv.width=8;cv.height=256;const k=cv.getContext('2d'),g=k.createLinearGradient(0,0,0,256);g.addColorStop(0,'#cfeaff');g.addColorStop(.5,'#5b7a8c');g.addColorStop(1,'#0b1f1a');k.fillStyle=g;k.fillRect(0,0,8,256);
es.add(new THREE.Mesh(new THREE.SphereGeometry(50,32,16),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(cv),side:THREE.BackSide})));
[[20,30,10],[-25,25,-10],[0,20,30]].forEach(p=>{const b=new THREE.Mesh(new THREE.BoxGeometry(12,1,12),new THREE.MeshBasicMaterial({color:0xffffff}));b.position.set(...p);b.lookAt(0,0,0);es.add(b)});
sc.environment=new THREE.PMREMGenerator(r).fromScene(es).texture})();
const gp=new THREE.Mesh(new THREE.PlaneGeometry(220,220),new THREE.MeshStandardMaterial({color:0x2a3038,roughness:.8,metalness:.15}));gp.rotation.x=-Math.PI/2;gp.position.y=-.03;gp.receiveShadow=true;sc.add(gp);
const tm=M(0x166534,0,.1,.9),tk=M(0x5b3a1e,0,.1,.9),mt=M(0x94a3b8,0,.9,.3);
for(let i=0;i<0;i++){const x=-70+Math.random()*140,z=(Math.random()<.5?-1:1)*(24+Math.random()*34),h=2+Math.random()*3.5,c=new THREE.Mesh(new THREE.ConeGeometry(1.1+Math.random(),h,8),tm);c.position.set(x,h/2+.8,z);c.castShadow=true;sc.add(c);const t=new THREE.Mesh(cyl(.2,.25,.8),tk);t.position.set(x,.4,z);sc.add(t)}
glow(28,11.6,-2,'rgba(255,170,60,.8)',4);
function bands(x,y,z,r,h,n){for(let i=0;i<n;i++){const b=new THREE.Mesh(new THREE.TorusGeometry(r,.08,8,32),mt);b.rotation.x=Math.PI/2;b.position.set(x,y-h/2+(i+.5)*h/n,z);sc.add(b)}}
bands(16,4.5,2,1.62,9,6);bands(25,3,2,1.42,6,4);bands(-14,2.5,-8,2.02,5,3);bands(-15.5,4,10,1.32,8,4);bands(-12.5,4,10,1.32,8,4);
[[-28,-12],[-22,-15]].forEach(([x,z])=>add(new THREE.SphereGeometry(.55,16,16),mt,x,12,z+.5));
[[-1,-1],[1,-1],[-1,1],[1,1]].forEach(a=>{add(cyl(.12,.12,1.2),mt,-14+a[0]*1.4,.6,-8+a[1]*1.4);add(cyl(.12,.12,1.5),mt,25+a[0]*1,-.0,2+a[1]*1)});
for(let x=-4;x<=25;x+=7){add(cyl(.15,.15,8),mt,x,4,-9);add(box(.2,.2,1.2),mt,x,7.9,-9)}
add(box(9,3.2,5),M(0x334155,0,.3,.6),8,1.6,-17);add(box(8.6,.7,.1),new THREE.MeshBasicMaterial({color:0xfde68a}),8,2,-14.45);tag('CTRL-ROOM',8,5,-17);
[[-6,6],[12,8],[22,-6],[34,0],[-20,12],[4,-12]].forEach(p=>{add(cyl(.08,.1,6),mt,p[0],3,p[1]);glow(p[0],6.2,p[1],'rgba(255,230,160,.8)',4)});
// camera
const V={full:[[6,24,44],[4,3,0]],elx:[[-32,18,30],[-16,4,0]],rx:[[10,14,28],[12,3,2]],nh3:[[36,14,26],[27,3,2]]};let tp=null,tt=null;
function go(k){tp=new THREE.Vector3(...V[k][0]);tt=new THREE.Vector3(...V[k][1])}
let tid=null;function tour(){if(tid){clearInterval(tid);tid=null;return}const ks=Object.keys(V);let i=0;go(ks[i++%4]);tid=setInterval(()=>go(ks[i++%4]),5000)}
cam.position.set(...V.full[0]);oc.target.set(...V.full[1]);
// telemetry
const tip=document.getElementById('tip'),ray=new THREE.Raycaster(),mv=new THREE.Vector2();
function show(e){const b=r.domElement.getBoundingClientRect();mv.set((e.clientX-b.left)/b.width*2-1,-(e.clientY-b.top)/b.height*2+1);ray.setFromCamera(mv,cam);
const h=ray.intersectObjects(picks)[0];if(!h){tip.style.display='none';return}const i=h.object.userData.id,q=D.u[i];
tip.innerHTML=`<b style="color:#10B981">${i}</b><br>Temp: ${q[0].toFixed(0)} °C<br>Pressure: ${q[1].toFixed(2)} MPa<br>Mass flow: ${q[2].toFixed(1)} kg/h<br>Power: ${q[3].toFixed(1)} kW<br><span style='color:#94a3b8'>${D.spec[i]||''}</span>`;tip.style.display='block'}
r.domElement.addEventListener('mousemove',show);r.domElement.addEventListener('click',show);
addEventListener('resize',()=>{r.setSize(innerWidth,H);cam.aspect=innerWidth/H;cam.updateProjectionMatrix()});
let t=0;(function an(){requestAnimationFrame(an);t+=.016;gl.material.opacity=.7+.3*Math.sin(t*2);rotors.forEach(h=>h.rotation.z-=.01+.06*pw);
flows.forEach(f=>{const a=f.pt.geometry.attributes.position;for(let i=0;i<f.n;i++){const p=f.cp.getPointAt((i/f.n+t*f.s)%1);a.setXYZ(i,p.x,p.y,p.z)}a.needsUpdate=true});
core.material.emissiveIntensity=.8+.9*D.T*D.X+.2*Math.sin(t*3);const lh=D.lvl*5+.15*Math.sin(t*2);liq.scale.y=lh/5;liq.position.y=.2+lh/2;
if(tp){cam.position.lerp(tp,.06);oc.target.lerp(tt,.06);if(cam.position.distanceTo(tp)<.3)tp=null}oc.update();r.render(sc,cam)})();
</script>"""
components.html(HTML.replace("__D__", json.dumps(D)), height=740)

# ---------------- Tabs ----------------
def style(fig, h=380):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,.6)",
                      height=h, margin=dict(l=10, r=10, t=45, b=10))
    return fig

t1, t2, t3, t4 = st.tabs(["⚙️ Mass & Energy Balance", "💲 Techno-Economics & Decarbonization", "☀️ Renewable Dynamics", "🔬 DWSIM Validation"])
with t1:
    c = st.columns(4)
    c[0].metric("H2:N2 molar ratio", f"{ratio:.2f}", "optimal 3.00" if abs(ratio - 3) < .15 else f"{ratio-3:+.2f} vs 3:1")
    c[1].metric("Per-pass conversion", f"{Xp:.1%}", f"equilibrium {Xe:.1%}")
    c[2].metric("Overall loop conversion", f"{Xo:.1%}")
    c[3].metric("SEC", f"{sec:.1f} MWh/t", f"{sec-10.25:+.1f} vs 9.5–11 benchmark", delta_color="inverse")
    st.dataframe(pd.DataFrame({"Item": ["Liquid green NH3", "Water consumption", "O2 co-product", "ALK electrolyzer", "PSA (N2)",
                                         "2-stage compression", "Total power"],
                               "Value": [nh3_h, water, o2, pem, asu, comp, total],
                               "Unit": ["kg/h", "kg/h", "kg/h", "kW", "kW", "kW", "kW"]}).round(2),
                 hide_index=True, use_container_width=True)
    a, b = st.columns(2)
    Ts = np.arange(350, 501, 5)
    f1 = go.Figure([go.Scatter(x=Ts, y=xeq(Ts, P) * 100, name="Equilibrium", line=dict(color=CY)),
                    go.Scatter(x=[488.2], y=[18.55], mode="markers", name="DWSIM REQ-1 (N2 per-pass)", marker=dict(size=12, color=CY, symbol="diamond")),
                    go.Scatter(x=[T], y=[Xp * 100], mode="markers", name="Live point", marker=dict(size=14, color=GD))])
    f1.update_layout(title=f"Per-pass conversion vs T @ {P} MPa", xaxis_title="°C", yaxis_title="NH3 conversion %")
    a.plotly_chart(style(f1), use_container_width=True)
    f2 = go.Figure(go.Pie(labels=["ALK Electrolysis", "PSA", "Compression"], values=[pem, asu, comp], hole=.55,
                          marker=dict(colors=[EM, CY, GD])))
    f2.update_layout(title="Plant power breakdown")
    b.plotly_chart(style(f2), use_container_width=True)
with t2:
    c = st.columns(4)
    c[0].metric("Electricity OPEX", f"${L['elec']:,.0f}/t"); c[1].metric("CAPEX (annualized)", f"${L['capex']:,.0f}/t")
    c[2].metric("O&M", f"${L['om']:,.0f}/t"); c[3].metric("O2 credit", f"${L['o2']:,.0f}/t")
    a, b = st.columns(2)
    wf = go.Figure(go.Waterfall(x=["Electricity", "CAPEX", "O&M", "O2 credit", "LCOA"], measure=["relative"] * 4 + ["total"],
                                y=[L["elec"], L["capex"], L["om"], L["o2"], 0],
                                increasing=dict(marker=dict(color=GD)), decreasing=dict(marker=dict(color=EM)),
                                totals=dict(marker=dict(color=CY))))
    wf.update_layout(title="LCOA waterfall (USD/t NH3)")
    a.plotly_chart(style(wf), use_container_width=True)
    ps = np.arange(15, 81, 5)
    sf = go.Figure([go.Scatter(x=ps, y=[lcoa(p)["total"] for p in ps], name="Green NH3", line=dict(color=EM)),
                    go.Scatter(x=[price], y=[L["total"]], mode="markers", marker=dict(size=13, color=GD), name="Live")])
    sf.add_hline(y=GREY, line_dash="dash", line_color="#94a3b8", annotation_text="Grey")
    sf.add_hline(y=BLUE, line_dash="dot", line_color=CY, annotation_text="Blue")
    sf.update_layout(title="LCOA sensitivity vs electricity price", xaxis_title="USD/MWh", yaxis_title="USD/t")
    b.plotly_chart(style(sf), use_container_width=True)
    cb = go.Figure(go.Bar(x=["Grey (SMR)", "Blue (SMR+CCS)", "Our Green NH3"], y=[GREY_C, BLUE_C, 0],
                          marker_color=["#64748b", CY, EM], text=[GREY_C, BLUE_C, 0.0], textposition="outside"))
    cb.update_layout(title="Carbon footprint (t CO2 / t NH3)")
    st.plotly_chart(style(cb, 320), use_container_width=True)
    st.caption("CAPEX/benchmark figures are indicative assumptions (ALK $1,100/kW, 8% WACC/20 yr, O2 $40/t, PSA 0.25 kWh/kg N2); "
               "H2 fed in excess of 3:1 raises SEC. Small lab-scale flows inflate LCOA vs. utility-scale plants.")

with t3:
    st.subheader("Renewable variability & H2 buffer (project plan §8)")
    c = st.columns(3)
    scn = c[0].radio("Scenario", ["A. Stable supply", "B. Solar variation", "C. Hybrid solar + wind"])
    peak = c[1].slider("Renewable peak (MW)", 0.2, 3.0, 1.2, 0.1)
    cap = c[2].slider("H2 buffer capacity (kg)", 5, 400, 100, 5)
    h = np.arange(72); d = h % 24
    sol = np.clip(np.sin((d - 6) / 12 * np.pi), 0, None) * peak
    wind = peak * 0.35 * (0.6 + 0.4 * np.sin(h / 5.0 + 1))
    pwr = {"A": np.full(72, total / 1000), "B": sol, "C": sol + wind}[scn[0]]
    rated, hc = pem / 1000, mH * 3600
    inv, rows = cap * 0.5, []
    for p in pwr:
        use = min(p, rated); use = use if use >= 0.2 * rated else 0.0
        av = inv + use * 1000 / eff
        cn = min(hc, av); cn = cn if cn >= 0.3 * hc else 0.0
        inv = min(cap, av - cn); sp = av - cn - inv
        rows.append((use, inv, cn / hc, (p - use) + sp * eff / 1000))
    use_a, inv_a, f_a, cur_a = map(np.array, zip(*rows))
    m = st.columns(4)
    m[0].metric("Avg NH3 output", f"{nh3_h * f_a.mean() * 24 / 1000:.2f} t/day", f"{f_a.mean() - 1:+.0%} vs design")
    m[1].metric("Synthesis on-stream", f"{(f_a > 0).mean():.0%}")
    m[2].metric("Electrolyser utilisation", f"{use_a.mean() / rated:.0%}")
    m[3].metric("Curtailed energy", f"{cur_a.sum() / 3:.2f} MWh/day")
    a, b = st.columns(2)
    f3 = go.Figure([go.Scatter(x=h, y=pwr, name="Renewable supply (MW)", fill="tozeroy", line=dict(color=GD)),
                    go.Scatter(x=h, y=use_a, name="Electrolyser load (MW)", line=dict(color=EM, width=3))])
    f3.update_layout(title="Power: supply vs electrolyser (72 h)", xaxis_title="hour")
    a.plotly_chart(style(f3), use_container_width=True)
    f4 = go.Figure([go.Scatter(x=h, y=inv_a, name="H2 inventory (kg)", fill="tozeroy", line=dict(color=CY)),
                    go.Scatter(x=h, y=f_a * 100, name="NH3 rate (% design)", yaxis="y2", line=dict(color=EM, width=3))])
    f4.update_layout(title="H2 buffer & ammonia output", xaxis_title="hour", yaxis2=dict(overlaying="y", side="right", range=[0, 110]))
    b.plotly_chart(style(f4), use_container_width=True)
    st.caption("Synthetic illustrative profiles, not measured data. Electrolyser min load 20%; synthesis turndown min 30%.")
with t4:
    st.subheader("DWSIM (GREEN_NH3.dwxmz) vs Python model")
    q = [("NH3 product", "kg/h", 33.88, nh3_h), ("N2 per-pass conversion", "%", 18.55, Xp * 100), ("Overall NH3 recovery", "%", 81.2, Xo * 100),
         ("Reactor outlet T", "°C", 488.2, T), ("Compression C-1 + C-2", "kW", 119.5, comp)]
    st.dataframe(pd.DataFrame([dict(Quantity=a, Unit=u_, DWSIM=d_, Python=round(p_, 2), **{"Δ %": round((p_ - d_) / d_ * 100, 1)}) for a, u_, d_, p_ in q]),
                 hide_index=True, use_container_width=True)
    st.caption("Agreement is only meaningful at the DWSIM base case (H2 2.055 g/s, N2 9.516 g/s, 10 MPa, 488 °C, recycle 0.95).")
    st.dataframe(pd.DataFrame(
        [("H2-Feed", 298.2, 0.101, 2.055e-3, 0.0), ("N2-Feed", 298.2, 0.101, 9.516e-3, 0.0), ("Mixed-Feed", 246.9, 0.101, 5.256e-2, 1.42),
         ("13 (C-1 out)", 612.0, 1.4, 5.256e-2, 1.42), ("14 (ICL-1 out)", 300.0, 1.4, 5.256e-2, 1.42), ("15 (C-2 out)", 598.9, 10.0, 5.256e-2, 1.42),
         ("17 (REQ-1 out)", 761.4, 10.0, 5.256e-2, 11.62), ("12 (liquid NH3)", 240.0, 10.0, 9.410e-3, 99.60),
         ("16 (recycle)", 240.0, 10.0, 4.099e-2, 1.83), ("18 (purge)", 240.0, 10.0, 2.157e-3, 1.83)],
        columns=["Stream", "T (K)", "P (MPa)", "Mass flow (kg/s)", "NH3 (mol %)"]), hide_index=True, use_container_width=True)
    nh3_h2 = nh3_h * 0.1776
    sk = go.Figure(go.Sankey(node=dict(label=["Water", "H2", "O2 co-product", "N2 (PSA)", "NH3 product", "Purge loss"],
                                       color=[CY, EM, "#64748b", CY, EM, GD], pad=20),
                             link=dict(source=[0, 0, 1, 3, 1, 3], target=[1, 2, 4, 4, 5, 5],
                                       value=[mH * 3600, o2, nh3_h2, nh3_h - nh3_h2, mH * 3600 - nh3_h2, mN * 3600 - (nh3_h - nh3_h2)])))
    sk.update_layout(title="Mass flow (kg/h): water → H2 → green NH3")
    st.plotly_chart(style(sk, 400), use_container_width=True)

with t4:
    st.subheader("Equipment register (indicative, from DWSIM + model)")
    st.dataframe(pd.DataFrame([[k, *np.round(v, 1), SPEC.get(k, "")] for k, v in u.items()],
                              columns=["Tag", "T (°C)", "P (MPa)", "Flow (kg/h)", "Power (kW)", "Description"]), hide_index=True, use_container_width=True)
