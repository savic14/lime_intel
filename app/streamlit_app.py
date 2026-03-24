"""
streamlit_app.py — Lime Intelligence Dashboard V3
- Dos secciones: datos frescos / datos desactualizados
- Scorecard visual con colores
- Señales del mercado
"""
import pandas as pd
import streamlit as st
from pathlib import Path

import os
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# En Streamlit Cloud los datos estan en la raiz del repo
if not (PROJECT_ROOT / 'data').exists():
    PROJECT_ROOT = Path(__file__).resolve().parents[0]
FORECAST_PATH  = PROJECT_ROOT / "data/processed/daily_forecast_base.csv"
SCORECARD_PATH = PROJECT_ROOT / "data/processed/daily_forecast_scorecard.csv"

st.set_page_config(page_title="Lime Intelligence", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding: 1.2rem 2rem; }
    .card {
        background: #1e2130;
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 8px;
        height: 100%;
    }
    .card-red    { border-left: 4px solid #ff1744; }
    .card-green  { border-left: 4px solid #00c853; }
    .card-yellow { border-left: 4px solid #ffd600; }
    .card-gray   { border-left: 4px solid #546e7a; }
    .card-dim    { border-left: 4px solid #37474f; opacity: 0.75; }
    .price-big   { font-size: 2.0rem; font-weight: 700; color: #ffffff; margin: 4px 0; }
    .price-dim   { font-size: 1.6rem; font-weight: 600; color: #90a4ae; margin: 4px 0; }
    .label-sm    { font-size: 0.70rem; color: #78909c; text-transform: uppercase; letter-spacing: 1px; }
    .label-date  { font-size: 0.72rem; color: #546e7a; }
    .sig-val     { font-size: 1.25rem; font-weight: 700; }
    .sube        { color: #00c853; }
    .baja        { color: #ff1744; }
    .estable     { color: #ffd600; }
    .conf-a      { color: #00c853; font-size:0.8rem; }
    .conf-b      { color: #ffd600; font-size:0.8rem; }
    .conf-c      { color: #78909c; font-size:0.8rem; }
    .divider     { border-top: 1px solid #2d3348; margin: 10px 0; }
    .section-hdr { font-size:0.75rem; font-weight:700; color:#546e7a;
                   text-transform:uppercase; letter-spacing:2px;
                   margin: 18px 0 8px 0; }
    .hit-yes     { color:#00c853; font-weight:700; }
    .hit-no      { color:#ff1744; font-weight:700; }
    .sc-row      { background:#1e2130; border-radius:8px; padding:10px 14px;
                   margin-bottom:6px; }
    table.fc-tbl { width:100%; font-size:0.82rem; color:#cfd8dc; border-collapse:collapse; }
    table.fc-tbl td { padding: 3px 0; }
</style>
""", unsafe_allow_html=True)

# ── Datos ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load():
    fc = pd.read_csv(FORECAST_PATH).sort_values("size").reset_index(drop=True) if FORECAST_PATH.exists() else pd.DataFrame()
    sc = pd.read_csv(SCORECARD_PATH).sort_values("rank_del_dia").reset_index(drop=True) if SCORECARD_PATH.exists() else pd.DataFrame()
    return fc, sc

fc, sc = load()
if fc.empty:
    st.error("No existe daily_forecast_base.csv — corre: limeupdate")
    st.stop()

# ── Helpers ───────────────────────────────────────────────────────────────────
def cd(d):
    d = str(d).upper()
    return "sube" if "SUBE" in d else ("baja" if "BAJA" in d else "estable")

def em(d):
    d = str(d).upper()
    return "▲" if "SUBE" in d else ("▼" if "BAJA" in d else "━")

def cc(c):
    try:
        c = float(c)
        return "conf-a" if c>=0.65 else ("conf-b" if c>=0.55 else "conf-c")
    except: return "conf-c"

def fp(p):
    try: return f"${float(p):.2f}"
    except: return "—"

def fc_pct(c):
    try: return f"{float(c):.0%}"
    except: return "—"

def border(d):
    d = str(d).upper()
    if "BAJA" in d: return "card-red"
    if "SUBE" in d: return "card-green"
    return "card-yellow"

def render_card(row, dim=False):
    size  = int(row["size"])
    precio= float(row.get("last_official_price", 0))
    fecha = str(row.get("last_date",""))
    d1    = str(row.get("direction_1d","ESTABLE"))
    p1    = row.get("predicted_target_1d","")
    d2    = str(row.get("direction_2d","ESTABLE"))
    p2    = row.get("predicted_target_2d","")
    d3    = str(row.get("direction_3d","ESTABLE"))
    p3    = row.get("predicted_target_3d","")
    d7    = str(row.get("direction_7d",""))
    p7    = row.get("predicted_target_7d","")
    clf   = str(row.get("direction_clf_1d_es","ESTABLE"))
    conf  = row.get("confidence_clf_1d","")
    mae   = row.get("mae_1d","")

    sig = clf if clf not in ["","nan"] else d1
    bc  = "card-dim" if dim else border(sig)
    pc  = "price-dim" if dim else "price-big"

    d7_row = ""
    if p7 and str(p7) not in ["","nan"]:
        d7_row = f"<tr><td><b>7 días</b></td><td class='{cd(d7)}'>{em(d7)} {d7}</td><td style='color:#fff'>{fp(p7)}</td></tr>"

    stale_badge = "<span style='background:#37474f;color:#90a4ae;font-size:0.65rem;padding:2px 6px;border-radius:4px;margin-left:6px'>DATOS VIEJOS</span>" if dim else ""

    return f"""
    <div class="card {bc}">
        <div class="label-sm">Calibre {size} BASE {stale_badge}</div>
        <div class="{pc}">{fp(precio)}</div>
        <div class="label-date">Precio al {fecha}</div>
        <div class="divider"></div>
        <div class="label-sm">Señal del modelo</div>
        <div class="sig-val {cd(sig)}">{em(sig)} {sig} <span class="{cc(conf)}">({fc_pct(conf)})</span></div>
        <div class="divider"></div>
        <table class="fc-tbl">
            <tr><td><b>Mañana</b></td><td class="{cd(d1)}">{em(d1)} {d1}</td><td style="color:#fff">{fp(p1)}</td></tr>
            <tr><td><b>2 días</b></td><td class="{cd(d2)}">{em(d2)} {d2}</td><td style="color:#fff">{fp(p2)}</td></tr>
            <tr><td><b>3 días</b></td><td class="{cd(d3)}">{em(d3)} {d3}</td><td style="color:#fff">{fp(p3)}</td></tr>
            {d7_row}
        </table>
        <div class="divider"></div>
        <div class="label-sm">Error histórico promedio: {"${:.2f}".format(float(mae)) if mae and str(mae)!="nan" else "—"}</div>
    </div>"""

# ── Header ────────────────────────────────────────────────────────────────────
max_date = pd.to_datetime(fc["last_date"]).max()
days_old = (pd.Timestamp.today().normalize() - max_date).days

col_t, col_s = st.columns([3,1])
with col_t:
    st.markdown("## 🍋 Lime Intelligence — McAllen FOB")
with col_s:
    if days_old > 3:
        st.error(f"⚠️ Hace {days_old} días — corre: limeupdate")
    else:
        st.success(f"✅ Actualizado: {max_date.strftime('%d %b %Y')}")

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# ── Resumen ───────────────────────────────────────────────────────────────────
st.markdown("### Resumen del día")
if not sc.empty:
    best      = sc.iloc[0]
    worst     = sc.sort_values("abs_error_1d", ascending=False).iloc[0]
    avg_err   = sc["abs_error_1d"].mean()
    min_err   = sc["abs_error_1d"].min()
    best_size = int(sc.loc[sc["abs_error_1d"].idxmin(), "size"])
    trend_ok  = int(sc["hit_1d"].astype(str).str.upper().eq("TRUE").sum())
    total     = len(sc)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📏 Error promedio ayer",    f"${avg_err:.2f}",
              help="Cuánto se alejó el modelo del precio real en promedio")
    c2.metric("🎯 Predicción más cercana", f"Calibre {best_size} — ${min_err:.2f}",
              help="El calibre donde el precio predicho estuvo más cerca del real")
    c3.metric("📈 Tendencia correcta",     f"{trend_ok} de {total} calibres",
              help="Cuántos calibres tuvieron la dirección correcta (sube/baja/estable)")
    c4.metric("📅 Datos hasta",            max_date.strftime("%d %b %Y"))
else:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📏 Error promedio","—")
    c2.metric("🎯 Más cercano","—")
    c3.metric("📈 Tendencia","—")
    c4.metric("📅 Datos hasta", max_date.strftime("%d %b %Y"))

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# ── Separar calibres por frescura ─────────────────────────────────────────────
dates     = pd.to_datetime(fc["last_date"])
max_fc    = dates.max()
fc_fresh  = fc[dates == max_fc].copy()
fc_stale  = fc[dates <  max_fc].copy()

# ── Sección 1: Datos frescos ──────────────────────────────────────────────────
st.markdown(f"### Forecast — datos al {max_fc.strftime('%d %b %Y')}")

fresh_sizes = fc_fresh["size"].tolist()
if fresh_sizes:
    n = len(fresh_sizes)
    cols = st.columns(min(n, 3))
    for i, size in enumerate(fresh_sizes):
        row = fc_fresh[fc_fresh["size"]==size].iloc[0]
        with cols[i % 3]:
            st.markdown(render_card(row, dim=False), unsafe_allow_html=True)

# ── Sección 2: Datos desactualizados ─────────────────────────────────────────
if not fc_stale.empty:
    stale_date = pd.to_datetime(fc_stale["last_date"]).max().strftime("%d %b %Y")
    st.markdown(f"<div class='section-hdr'>⚠️ Calibres sin datos recientes — último reporte USDA: {stale_date}</div>", unsafe_allow_html=True)
    stale_sizes = fc_stale["size"].tolist()
    cols2 = st.columns(min(len(stale_sizes), 3))
    for i, size in enumerate(stale_sizes):
        row = fc_stale[fc_stale["size"]==size].iloc[0]
        with cols2[i % 3]:
            st.markdown(render_card(row, dim=True), unsafe_allow_html=True)

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# ── Señales del mercado ───────────────────────────────────────────────────────
st.markdown("### Señales del mercado")

row_ref = fc[fc["size"]==200].iloc[0] if 200 in fc["size"].values else fc.iloc[0]

def get_val(col):
    try: return float(row_ref.get(col,""))
    except: return None

lluvia  = get_val("lluvia_14d_lag6")
usdmxn  = get_val("usd_mxn")
spike   = get_val("spike_230_lag14")
imp     = get_val("import_lag2")

s1,s2,s3,s4 = st.columns(4)

with s1:
    if lluvia is not None:
        nivel = "Alta ⚠️" if lluvia>20 else ("Media" if lluvia>5 else "Baja ✅")
        col   = "baja" if lluvia>20 else ("estable" if lluvia>5 else "sube")
        desc  = "Presión bajista en oferta" if lluvia>5 else "Sin impacto en corte"
        st.markdown(f'<div class="card card-gray"><div class="label-sm">🌧 Lluvia Veracruz (hace 6 días)</div><div class="sig-val {col}">{lluvia:.1f} mm — {nivel}</div><div class="label-sm">{desc}</div></div>', unsafe_allow_html=True)

with s2:
    if usdmxn is not None:
        st.markdown(f'<div class="card card-gray"><div class="label-sm">💱 Tipo de cambio USD/MXN</div><div class="sig-val estable">{usdmxn:.4f}</div><div class="label-sm">Peso {"débil → más exportación" if usdmxn>18 else "estable"}</div></div>', unsafe_allow_html=True)

with s3:
    if spike is not None:
        col  = "sube" if spike>1 else ("baja" if spike<-1 else "estable")
        desc = "Corte acelerado → oferta en ~14d" if spike>1 else ("Corte lento → escasez en ~14d" if spike<-1 else "Ritmo normal de corte")
        st.markdown(f'<div class="card card-gray"><div class="label-sm">📦 Calibre 230 — velocidad de corte</div><div class="sig-val {col}">{spike:+.2f}</div><div class="label-sm">{desc}</div></div>', unsafe_allow_html=True)

with s4:
    if imp is not None:
        vm = imp/1e6
        st.markdown(f'<div class="card card-gray"><div class="label-sm">🚢 Importaciones Col + Perú (hace 2 días)</div><div class="sig-val estable">{vm:.1f}M lbs</div><div class="label-sm">Oferta complementaria en mercado</div></div>', unsafe_allow_html=True)

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# ── Scorecard rediseñado ──────────────────────────────────────────────────────
if not sc.empty:
    st.markdown("### ¿Cómo le fue al modelo ayer?")
    st.caption("Comparación entre lo que predijo el modelo y el precio real que reportó USDA al día siguiente.")

    for _, row in sc.sort_values("rank_del_dia").iterrows():
        size     = int(row["size"])
        pred     = float(row["pred_1d"])
        real     = float(row["real_1d"])
        err      = float(row["abs_error_1d"])
        pred_dir = str(row.get("pred_dir_1d","—"))
        real_dir = str(row.get("real_dir_1d","—"))
        hit      = str(row.get("hit_1d","")).upper() == "TRUE"

        hit_html  = '<span class="hit-yes">✅ Dirección correcta</span>' if hit else '<span class="hit-no">❌ Dirección incorrecta</span>'
        err_color = "sube" if err < 1.5 else ("estable" if err < 3.0 else "baja")
        dir_match = pred_dir == real_dir

        st.markdown(f"""
        <div class="sc-row">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:1.1rem;font-weight:700;color:#fff">Calibre {size} BASE</span>
                    &nbsp;&nbsp;{hit_html}
                </div>
                <div style="text-align:right">
                    <span class="label-sm">Error: </span>
                    <span class="{err_color}" style="font-weight:700">${err:.2f}</span>
                </div>
            </div>
            <div style="margin-top:8px; display:flex; gap:32px; font-size:0.85rem; color:#90a4ae;">
                <div>
                    <div class="label-sm">Predicción</div>
                    <div style="color:#fff;font-size:1rem;font-weight:600">${pred:.2f}
                        <span class="{cd(pred_dir)}">{em(pred_dir)} {pred_dir}</span>
                    </div>
                </div>
                <div>
                    <div class="label-sm">Precio real USDA</div>
                    <div style="color:#fff;font-size:1rem;font-weight:600">${real:.2f}
                        <span class="{cd(real_dir)}">{em(real_dir)} {real_dir}</span>
                    </div>
                </div>
                <div>
                    <div class="label-sm">Diferencia</div>
                    <div class="{err_color}" style="font-size:1rem;font-weight:600">${err:.2f} {"✓ menos de $1.50" if err<1.5 else ""}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
