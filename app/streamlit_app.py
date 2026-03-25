"""
streamlit_app.py — Lime Intelligence Dashboard V4
"""
import pandas as pd
import streamlit as st
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1] if (Path(__file__).resolve().parents[1] / "data").exists() else Path(__file__).resolve().parent

FORECAST_PATH  = PROJECT_ROOT / "data/processed/daily_forecast_base.csv"
SCORECARD_PATH = PROJECT_ROOT / "data/processed/daily_forecast_scorecard.csv"
PRICE_PATH     = PROJECT_ROOT / "data/processed/shipping_point_core.csv"
MOVE_PATH      = PROJECT_ROOT / "data/processed/movement_core.csv"
RAIN_PATH      = PROJECT_ROOT / "data/processed/lluvia_veracruz_historico.csv"
FX_PATH        = PROJECT_ROOT / "data/processed/usd_mxn_historico.csv"

st.set_page_config(page_title="Lime Intelligence", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container{padding:1.2rem 2rem}
.card{background:#1e2130;border-radius:12px;padding:16px 18px;margin-bottom:8px}
.card-red{border-left:4px solid #ff1744}
.card-green{border-left:4px solid #00c853}
.card-yellow{border-left:4px solid #ffd600}
.card-gray{border-left:4px solid #546e7a}
.card-old{border-left:4px solid #37474f;opacity:0.8}
.price-big{font-size:2.0rem;font-weight:700;color:#fff;margin:4px 0}
.price-old{font-size:1.6rem;font-weight:600;color:#90a4ae;margin:4px 0}
.lsm{font-size:0.70rem;color:#78909c;text-transform:uppercase;letter-spacing:1px}
.ldate{font-size:0.72rem;color:#546e7a}
.sv{font-size:1.2rem;font-weight:700}
.sube{color:#00c853}.baja{color:#ff1744}.estable{color:#ffd600}
.ca{color:#00c853;font-size:0.8rem}.cb{color:#ffd600;font-size:0.8rem}.cc{color:#78909c;font-size:0.8rem}
.div{border-top:1px solid #2d3348;margin:10px 0}
.tnup{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;background:#1b5e20;color:#00c853}
.tndn{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;background:#b71c1c;color:#ff8a80}
.tnfl{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;background:#33373f;color:#90a4ae}
.pnote{font-size:0.78rem;color:#ffd600;font-style:italic;margin-top:4px}
.tbl{width:100%;font-size:0.82rem;color:#cfd8dc;border-collapse:collapse}
.tbl td{padding:3px 0}
.badge-old{background:#37474f;color:#90a4ae;font-size:0.65rem;padding:2px 6px;border-radius:4px;margin-left:6px}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load():
    fc    = pd.read_csv(FORECAST_PATH).sort_values("size").reset_index(drop=True) if FORECAST_PATH.exists() else pd.DataFrame()
    sc    = pd.read_csv(SCORECARD_PATH).sort_values("rank_del_dia").reset_index(drop=True) if SCORECARD_PATH.exists() else pd.DataFrame()
    price = pd.read_csv(PRICE_PATH) if PRICE_PATH.exists() else pd.DataFrame()
    move  = pd.read_csv(MOVE_PATH)  if MOVE_PATH.exists()  else pd.DataFrame()
    rain  = pd.read_csv(RAIN_PATH)  if RAIN_PATH.exists()  else pd.DataFrame()
    fx    = pd.read_csv(FX_PATH)    if FX_PATH.exists()    else pd.DataFrame()
    for df in [fc, sc, price, move, rain, fx]:
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return fc, sc, price, move, rain, fx

fc, sc, price_df, move_df, rain_df, fx_df = load()

if fc.empty:
    st.error("No existe daily_forecast_base.csv")
    st.stop()

def cd(d):
    d = str(d).upper()
    return "sube" if "SUBE" in d else ("baja" if "BAJA" in d else "estable")

def em(d):
    d = str(d).upper()
    return "▲" if "SUBE" in d else ("▼" if "BAJA" in d else "━")

def cc(c):
    try:
        c = float(c)
        return "ca" if c >= 0.65 else ("cb" if c >= 0.55 else "cc")
    except:
        return "cc"

def fp(p):
    try: return f"${float(p):.2f}"
    except: return "—"

def fpc(c):
    try: return f"{float(c):.0%}"
    except: return "—"

def border(d):
    d = str(d).upper()
    return "card-red" if "BAJA" in d else ("card-green" if "SUBE" in d else "card-yellow")

def tone_badge(tone):
    t = str(tone).lower()
    if any(x in t for x in ["higher", "firmer", "strong"]):
        return "<span class=\"tnup\">▲ USDA: Precio subiendo</span>"
    if any(x in t for x in ["lower", "weak", "light", "exceed"]):
        return "<span class=\"tndn\">▼ USDA: Precio bajando</span>"
    if any(x in t for x in ["steady", "stable", "unchanged"]):
        return "<span class=\"tnfl\">━ USDA: Precio estable</span>"
    return ""

def get_tone(size, quality="BASE"):
    if price_df.empty: return "", ""
    s = price_df[(price_df["size"] == size) & (price_df["quality"] == quality)].sort_values("date")
    if s.empty: return "", ""
    last = s.iloc[-1]
    return str(last.get("market_tone", "")), str(last.get("demand_tone", ""))

def render_card(row, dim=False):
    size   = int(row["size"])
    precio = float(row.get("last_official_price", 0))
    fecha  = str(row.get("last_date", ""))
    d1 = str(row.get("direction_1d", "ESTABLE"))
    p1 = row.get("predicted_target_1d", "")
    d2 = str(row.get("direction_2d", "ESTABLE"))
    p2 = row.get("predicted_target_2d", "")
    d3 = str(row.get("direction_3d", "ESTABLE"))
    p3 = row.get("predicted_target_3d", "")
    d7 = str(row.get("direction_7d", ""))
    p7 = row.get("predicted_target_7d", "")
    clf  = str(row.get("direction_clf_1d_es", "ESTABLE"))
    conf = row.get("confidence_clf_1d", "")
    mae  = row.get("mae_1d", "")

    tone, demand = get_tone(size)
    tone_h = tone_badge(tone)

    sig = clf if clf not in ["", "nan"] else d1
    bc  = "card-old" if dim else border(sig)
    pc  = "price-old" if dim else "price-big"

    badge = "<span class=\"badge-old\">DATOS VIEJOS</span>" if dim else ""

    pred_note = ""
    if p1 and not dim:
        try:
            diff = float(p1) - precio
            if abs(diff) > 5:
                pred_note = (
                    "<div class=\"pnote\">Nota: el modelo predice corrección de "
                    + fp(p1) + ". Los precios actuales ("
                    + fp(precio) + ") están "
                    + str(round(abs(diff), 1))
                    + " USD sobre la media histórica del modelo.</div>"
                )
        except:
            pass

    d7_row = ""
    if p7 and str(p7) not in ["", "nan"]:
        d7_row = (
            "<tr><td><b>7 días</b></td>"
            "<td class=\"" + cd(d7) + "\">" + em(d7) + " " + d7 + "</td>"
            "<td style=\"color:#fff\">" + fp(p7) + "</td></tr>"
        )

    tone_section = ("<div class=\"div\"></div>" + tone_h) if tone_h else ""

    html = (
        "<div class=\"card " + bc + "\">"
        "<div class=\"lsm\">Calibre " + str(size) + " BASE " + badge + "</div>"
        "<div class=\"" + pc + "\">" + fp(precio) + "</div>"
        "<div class=\"ldate\">Último precio USDA — " + fecha + "</div>"
        + tone_section +
        "<div class=\"div\"></div>"
        "<div class=\"lsm\">¿Sube o baja mañana?</div>"
        "<div class=\"sv " + cd(sig) + "\">" + em(sig) + " " + sig + " "
        "<span class=\"" + cc(conf) + "\">(" + fpc(conf) + " confianza)</span></div>"
        + pred_note +
        "<div class=\"div\"></div>"
        "<table class=\"tbl\">"
        "<tr style=\"color:#546e7a;font-size:0.7rem\"><td>HORIZONTE</td><td>DIRECCIÓN</td><td>PRECIO EST.</td></tr>"
        "<tr><td><b>Mañana</b></td><td class=\"" + cd(d1) + "\">" + em(d1) + " " + d1 + "</td><td style=\"color:#fff\">" + fp(p1) + "</td></tr>"
        "<tr><td><b>2 días</b></td><td class=\"" + cd(d2) + "\">" + em(d2) + " " + d2 + "</td><td style=\"color:#fff\">" + fp(p2) + "</td></tr>"
        "<tr><td><b>3 días</b></td><td class=\"" + cd(d3) + "\">" + em(d3) + " " + d3 + "</td><td style=\"color:#fff\">" + fp(p3) + "</td></tr>"
        + d7_row +
        "</table>"
        "<div class=\"div\"></div>"
        "<div class=\"lsm\">Error histórico promedio del modelo: " + ("${:.2f}".format(float(mae)) if mae and str(mae) != "nan" else "—") + "</div>"
        "</div>"
    )
    return html

# ── Header ────────────────────────────────────────────────────────────────────
max_date = pd.to_datetime(fc["last_date"]).max()
days_old = (pd.Timestamp.today().normalize() - max_date).days

col_t, col_s = st.columns([3, 1])
with col_t:
    st.markdown("## 🍋 Lime Intelligence — McAllen FOB")
with col_s:
    if days_old > 3:
        st.error(f"⚠️ Hace {days_old} días — corre: limeupdate")
    else:
        st.success(f"✅ Actualizado: {max_date.strftime('%d %b %Y')}")

dates  = pd.to_datetime(fc["last_date"])
desync = fc[dates < dates.max()]
if not desync.empty:
    atrasados = [f"{int(r['size'])} ({r['last_date']})" for _, r in desync.iterrows()]
    st.warning(f"⚠️ Calibres sin datos recientes: {', '.join(atrasados)} — USDA no los reportó recientemente")

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Resumen ───────────────────────────────────────────────────────────────────
if not sc.empty:
    st.markdown("### Resumen del día")
    best_size = int(sc.loc[sc["abs_error_1d"].idxmin(), "size"])
    min_err   = sc["abs_error_1d"].min()
    c1, c2    = st.columns(2)
    c1.metric("🎯 Predicción más cercana ayer", f"Calibre {best_size} — ${min_err:.2f} de diferencia")
    c2.metric("📅 Datos USDA hasta", max_date.strftime("%d %b %Y"))
    st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Forecast frescos ──────────────────────────────────────────────────────────
fresh_fc = fc[dates == dates.max()].copy()
stale_fc = fc[dates <  dates.max()].copy()

st.markdown(f"### Forecast — datos al {max_date.strftime('%d %b %Y')}")
if not fresh_fc.empty:
    cols = st.columns(min(len(fresh_fc), 3))
    for i, size in enumerate(fresh_fc["size"].tolist()):
        row = fresh_fc[fresh_fc["size"] == size].iloc[0]
        with cols[i % 3]:
            st.markdown(render_card(row, dim=False), unsafe_allow_html=True)

if not stale_fc.empty:
    stale_date = pd.to_datetime(stale_fc["last_date"]).max().strftime("%d %b %Y")
    st.markdown(
        f"<div style=\"font-size:0.75rem;font-weight:700;color:#546e7a;"
        f"text-transform:uppercase;letter-spacing:2px;margin:18px 0 8px 0\">"
        f"⚠️ Sin datos recientes — último reporte USDA: {stale_date}</div>",
        unsafe_allow_html=True
    )
    cols2 = st.columns(min(len(stale_fc), 3))
    for i, size in enumerate(stale_fc["size"].tolist()):
        row = stale_fc[stale_fc["size"] == size].iloc[0]
        with cols2[i % 3]:
            st.markdown(render_card(row, dim=True), unsafe_allow_html=True)

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Señales del mercado ───────────────────────────────────────────────────────
st.markdown("### Señales del mercado")

ZONAS = {
    "Martínez de la Torre, Ver.": (20.0667, -97.0500),
    "Álamo Temapache, Ver.":      (21.0167, -97.6833),
    "Tuxtepec, Oax.":             (18.0833, -96.1167),
    "Tamazunchale, SLP":          (21.2667, -98.7833),
    "Ciudad Valles, SLP":         (21.9833, -99.0167),
}

st.markdown("#### 🌧 Lluvia en zonas productoras")
st.caption("La lluvia intensa detiene el corte de limón. El efecto en McAllen se siente 5-10 días después.")

if not rain_df.empty:
    last_rain = rain_df.sort_values("date").iloc[-1]
    lluvia_7  = float(last_rain.get("lluvia_7d", 0) or 0)
    color_ll  = "#ff1744" if lluvia_7 > 40 else ("#ffd600" if lluvia_7 > 15 else "#00c853")
    nivel_ll  = "Alta ⚠️" if lluvia_7 > 40 else ("Media" if lluvia_7 > 15 else "Baja ✅")
    pct_ll    = min(lluvia_7 / 80, 1.0) * 100

    zona_cols = st.columns(len(ZONAS))
    for i, (zona, _) in enumerate(ZONAS.items()):
        with zona_cols[i]:
            st.markdown(
                "<div class=\"card card-gray\" style=\"padding:12px\">"
                "<div class=\"lsm\">" + zona + "</div>"
                "<div style=\"font-size:1.1rem;font-weight:700;color:" + color_ll + "\">" + f"{lluvia_7:.1f}" + " mm / 7d</div>"
                "<div style=\"background:#2d3348;border-radius:4px;height:6px;margin-top:6px\">"
                "<div style=\"background:" + color_ll + ";width:" + f"{pct_ll:.0f}" + "%;height:6px;border-radius:4px\"></div>"
                "</div>"
                "<div class=\"lsm\" style=\"margin-top:4px\">" + nivel_ll + "</div>"
                "</div>",
                unsafe_allow_html=True
            )
    st.caption("⚠️ Mismo dato meteorológico para todas las zonas. Próximamente: fetch individual por zona.")

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Movimiento en frontera ────────────────────────────────────────────────────
st.markdown("#### 🚛 Movimiento en frontera")
st.caption("Pharr/McAllen es el principal punto de entrada del limón mexicano a Texas (~70%). Mayor volumen = más oferta = presión bajista.")

if not move_df.empty:
    last_move  = move_df.sort_values("date").iloc[-1]
    prev_move  = move_df.sort_values("date").iloc[-8] if len(move_df) > 8 else last_move
    pharr_hoy  = float(last_move.get("pharr_seedless_lb", 0) or 0)
    pharr_prev = float(prev_move.get("pharr_seedless_lb", 0) or 0)
    mx_hoy     = float(last_move.get("mx_seedless_lb",    0) or 0)
    col_hoy    = float(last_move.get("colombia_seedless_lb", 0) or 0)
    per_hoy    = float(last_move.get("peru_seedless_lb",  0) or 0)
    total_hoy  = float(last_move.get("total_seedless_lb", 0) or 0)
    move_date  = pd.to_datetime(last_move["date"]).strftime("%d %b")
    pharr_chg  = ((pharr_hoy - pharr_prev) / (pharr_prev + 1)) * 100
    imp_total  = col_hoy + per_hoy
    imp_pct    = (imp_total / (total_hoy + 1)) * 100
    mx_pct     = (mx_hoy / (total_hoy + 1)) * 100

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        color_p = "#ff1744" if pharr_chg > 20 else ("#ffd600" if pharr_chg > 0 else "#00c853")
        desc_p  = "Más oferta en McAllen" if pharr_chg > 10 else ("Oferta normal" if pharr_chg > -10 else "Menos oferta")
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">🚛 Pharr/McAllen — México</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:" + color_p + "\">" + f"{pharr_hoy/1e6:.1f}M lbs</div>"
            "<div style=\"font-size:0.8rem;color:" + color_p + "\">" + f"{pharr_chg:+.0f}% vs semana pasada</div>"
            "<div class=\"lsm\">" + desc_p + " — al " + move_date + "</div>"
            "</div>",
            unsafe_allow_html=True
        )

    with m2:
        if mx_hoy > 0:
            pct_pharr = pharr_hoy / mx_hoy * 100
            st.markdown(
                "<div class=\"card card-gray\">"
                "<div class=\"lsm\">🇲🇽 Total México (todos los puertos)</div>"
                "<div style=\"font-size:1.2rem;font-weight:700;color:#fff\">" + f"{mx_hoy/1e6:.1f}M lbs</div>"
                "<div class=\"lsm\">Incluye Laredo, Eagle Pass, Nogales</div>"
                "<div class=\"lsm\" style=\"color:#546e7a\">Pharr = " + f"{pct_pharr:.0f}% del total MX</div>"
                "</div>",
                unsafe_allow_html=True
            )

    with m3:
        color_i = "#ffd600" if imp_pct > 30 else "#90a4ae"
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">🚢 Colombia + Perú (importado)</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:" + color_i + "\">" + f"{imp_total/1e6:.1f}M lbs</div>"
            "<div style=\"font-size:0.78rem;color:#78909c\">" + f"{imp_pct:.0f}% del total en mercado</div>"
            "<div class=\"lsm\">Col: " + f"{col_hoy/1e6:.1f}M | Per: {per_hoy/1e6:.1f}M lbs</div>"
            "</div>",
            unsafe_allow_html=True
        )

    with m4:
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">⚖️ Balance del mercado</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:#fff\">" + f"{total_hoy/1e6:.1f}M lbs total</div>"
            "<div style=\"background:#2d3348;border-radius:4px;height:8px;margin:6px 0\">"
            "<div style=\"background:#00c853;width:" + f"{mx_pct:.0f}" + "%;height:8px;border-radius:4px\"></div>"
            "</div>"
            "<div class=\"lsm\">🟢 México " + f"{mx_pct:.0f}% | 🟡 Importado {100-mx_pct:.0f}%</div>"
            "</div>",
            unsafe_allow_html=True
        )

    st.caption("⚠️ Colombia y Perú también envían a Florida y Nueva York — no todo llega a McAllen.")

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Tipo de cambio ────────────────────────────────────────────────────────────
if not fx_df.empty:
    last_fx  = fx_df.sort_values("date").iloc[-1]
    usdmxn   = float(last_fx.get("usd_mxn", 0))
    chg_7d   = float(last_fx.get("usd_mxn_chg_7d", 0) or 0)
    fx_date  = pd.to_datetime(last_fx["date"]).strftime("%d %b")
    color_fx = "#ff1744" if chg_7d > 0.5 else ("#00c853" if chg_7d < -0.5 else "#ffd600")
    desc_fx  = ("Peso débil → productor exporta más → más oferta → presión bajista" if chg_7d > 0.3
                else ("Peso fuerte → menos incentivo a exportar" if chg_7d < -0.3
                else "Tipo de cambio estable"))

    st.markdown("#### 💱 Tipo de cambio USD/MXN")
    col_fx, _ = st.columns([1, 3])
    with col_fx:
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">USD/MXN al " + fx_date + "</div>"
            "<div style=\"font-size:1.8rem;font-weight:700;color:#fff\">" + f"{usdmxn:.4f}</div>"
            "<div style=\"font-size:0.85rem;color:" + color_fx + "\">" + f"{chg_7d:+.4f} vs hace 7 días</div>"
            "<div class=\"lsm\" style=\"margin-top:6px\">" + desc_fx + "</div>"
            "</div>",
            unsafe_allow_html=True
        )

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Scorecard ─────────────────────────────────────────────────────────────────
if not sc.empty:
    st.markdown("### ¿Qué tan cerca estuvo el modelo?")
    st.caption("Comparación entre el precio que predijo el modelo y el precio real que publicó USDA al día siguiente.")

    for _, row in sc.sort_values("abs_error_1d").iterrows():
        size     = int(row["size"])
        pred     = float(row["pred_1d"])
        real     = float(row["real_1d"])
        err      = float(row["abs_error_1d"])
        pred_dir = str(row.get("pred_dir_1d", "—"))
        real_dir = str(row.get("real_dir_1d", "—"))
        hit      = str(row.get("hit_1d", "")).upper() == "TRUE"

        err_color = "#00c853" if err < 1.5 else ("#ffd600" if err < 3.0 else "#ff1744")
        dir_html  = (
            "<span style=\"color:#00c853;font-weight:700\">✅ Dirección correcta</span>"
            if hit else
            "<span style=\"color:#ff1744;font-weight:700\">❌ Dirección incorrecta</span>"
        )

        st.markdown(
            "<div class=\"card card-gray\" style=\"margin-bottom:8px\">"
            "<div style=\"display:flex;justify-content:space-between;align-items:center\">"
            "<span style=\"font-size:1.05rem;font-weight:700;color:#fff\">Calibre " + str(size) + " BASE</span>"
            "<span style=\"font-size:1.1rem;font-weight:700;color:" + err_color + "\">" + f"${err:.2f} de diferencia</span>"
            "</div>"
            "<div style=\"display:flex;gap:32px;margin-top:10px;font-size:0.85rem\">"
            "<div><div class=\"lsm\">Lo que predijo el modelo</div>"
            "<div style=\"color:#fff;font-size:1rem;font-weight:600\">" + f"${pred:.2f} " +
            "<span class=\"" + cd(pred_dir) + "\">" + em(pred_dir) + " " + pred_dir + "</span></div></div>"
            "<div><div class=\"lsm\">Precio real USDA</div>"
            "<div style=\"color:#fff;font-size:1rem;font-weight:600\">" + f"${real:.2f} " +
            "<span class=\"" + cd(real_dir) + "\">" + em(real_dir) + " " + real_dir + "</span></div></div>"
            "<div style=\"align-self:center\">" + dir_html + "</div>"
            "</div></div>",
            unsafe_allow_html=True
        )
