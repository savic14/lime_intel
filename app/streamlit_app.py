"""
streamlit_app.py — Lime Intelligence Dashboard V6
Fixes:
- Movement: promedio 7 dias en vez de dia puntual
- Scorecard: fecha explicita de prediccion
- Precio predicho como rango (pred +/- MAE)
"""
import pandas as pd
import streamlit as st
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
    if (Path(__file__).resolve().parents[1] / "data").exists()
    else Path(__file__).resolve().parent
)

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
.price-big{font-size:2.0rem;font-weight:700;color:#fff;margin:2px 0}
.price-old{font-size:1.6rem;font-weight:600;color:#90a4ae;margin:2px 0}
.price-range{font-size:0.95rem;color:#90a4ae;margin-bottom:2px}
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
.range-box{background:#2d3348;border-radius:8px;padding:8px 12px;margin:8px 0}
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

def get_price_detail(size, quality="BASE"):
    if price_df.empty: return None
    s = price_df[(price_df["size"] == size) & (price_df["quality"] == quality)].sort_values("date")
    if s.empty: return None
    last = s.iloc[-1]
    def safe_float(col):
        v = last.get(col)
        return float(v) if v is not None and pd.notna(v) else None
    return {
        "official": float(last["official_price"]),
        "low":   safe_float("low_price"),
        "high":  safe_float("high_price"),
        "mlow":  safe_float("mostly_low_price"),
        "mhigh": safe_float("mostly_high_price"),
        "tone":  str(last.get("market_tone", "")),
    }

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

    detail = get_price_detail(size)
    tone_h = tone_badge(detail["tone"]) if detail else ""

    # Rango del precio actual (donde más se vendió)
    range_html = ""
    if detail and detail["mlow"] and detail["mhigh"]:
        range_html = (
            "<div class=\"price-range\">"
            "Se vendió más entre: "
            "<b style=\"color:#fff\">" + f"${detail['mlow']:.0f} — ${detail['mhigh']:.0f}" + "</b>"
            "&nbsp;|&nbsp;"
            "Rango completo: " + f"${detail['low']:.0f} — ${detail['high']:.0f}"
            "</div>"
        )

    # Rango de prediccion (pred +/- MAE)
    def pred_range(pred_val):
        try:
            p = float(pred_val)
            m = float(mae)
            return f"${p - m:.2f} — ${p + m:.2f}"
        except:
            return ""

    sig = clf if clf not in ["", "nan"] else d1
    bc  = "card-old" if dim else border(sig)
    pc  = "price-old" if dim else "price-big"
    badge = "<span class=\"badge-old\">DATOS VIEJOS</span>" if dim else ""
    tone_section = ("<div class=\"div\"></div>" + tone_h) if tone_h else ""

    # Rango predicho para mañana
    rango_1d = pred_range(p1)
    rango_1d_html = ""
    if rango_1d and not dim:
        d_text = cd(d1)
        rango_1d_html = (
            "<div class=\"range-box\">"
            "<div class=\"lsm\">Rango probable mañana (±error histórico)</div>"
            "<div style=\"font-size:1.1rem;font-weight:700;color:#fff\">" + rango_1d + "</div>"
            "<div style=\"font-size:0.78rem;color:#78909c\">El precio real cae dentro de este rango la mayoría de las veces</div>"
            "</div>"
        )

    d7_row = ""
    if p7 and str(p7) not in ["", "nan"]:
        r7 = pred_range(p7)
        d7_row = (
            "<tr><td><b>7 días</b></td>"
            "<td class=\"" + cd(d7) + "\">" + em(d7) + " " + d7 + "</td>"
            "<td style=\"color:#fff\">" + (r7 if r7 else fp(p7)) + "</td></tr>"
        )

    html = (
        "<div class=\"card " + bc + "\">"
        "<div class=\"lsm\">Calibre " + str(size) + " BASE " + badge + "</div>"
        "<div class=\"" + pc + "\">" + fp(precio) + "</div>"
        + range_html +
        "<div class=\"ldate\">Último precio oficial USDA — " + fecha + "</div>"
        + tone_section +
        "<div class=\"div\"></div>"
        "<div class=\"lsm\">¿Sube o baja mañana?</div>"
        "<div class=\"sv " + cd(sig) + "\">" + em(sig) + " " + sig + " "
        "<span class=\"" + cc(conf) + "\">(" + fpc(conf) + " confianza)</span></div>"
        + rango_1d_html +
        "<div class=\"div\"></div>"
        "<table class=\"tbl\">"
        "<tr style=\"color:#546e7a;font-size:0.7rem\"><td>HORIZONTE</td><td>DIRECCIÓN</td><td>RANGO PRECIO</td></tr>"
        "<tr><td><b>Mañana</b></td><td class=\"" + cd(d1) + "\">" + em(d1) + " " + d1 + "</td><td style=\"color:#fff\">" + (pred_range(p1) or fp(p1)) + "</td></tr>"
        "<tr><td><b>2 días</b></td><td class=\"" + cd(d2) + "\">" + em(d2) + " " + d2 + "</td><td style=\"color:#fff\">" + (pred_range(p2) or fp(p2)) + "</td></tr>"
        "<tr><td><b>3 días</b></td><td class=\"" + cd(d3) + "\">" + em(d3) + " " + d3 + "</td><td style=\"color:#fff\">" + (pred_range(p3) or fp(p3)) + "</td></tr>"
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

# ── Forecast ──────────────────────────────────────────────────────────────────
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
        "<div style=\"font-size:0.75rem;font-weight:700;color:#546e7a;"
        "text-transform:uppercase;letter-spacing:2px;margin:18px 0 8px 0\">"
        "⚠️ Sin datos recientes — último reporte USDA: " + stale_date + "</div>",
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

ZONAS = [
    ("Martínez de la Torre, Ver.", "54% prod. nacional", "#00c853"),
    ("Tuxtepec / Papaloapan, Oax.", "16% prod. nacional", "#00c853"),
    ("Huimanguillo, Tabasco", "7% prod. nacional", "#ffd600"),
    ("Valladolid, Yucatán", "5% prod. nacional", "#ffd600"),
    ("San Luis Potosí", "exportación directa", "#90a4ae"),
]

st.markdown("#### 🌧 Lluvia en zonas productoras")
st.caption("La lluvia intensa detiene el corte. El efecto en McAllen llega 5-10 días después.")

if not rain_df.empty:
    last_rain = rain_df.sort_values("date").iloc[-1]
    lluvia_7  = float(last_rain.get("lluvia_7d", 0) or 0)
    color_ll  = "#ff1744" if lluvia_7 > 40 else ("#ffd600" if lluvia_7 > 15 else "#00c853")
    nivel_ll  = "Alta ⚠️" if lluvia_7 > 40 else ("Media" if lluvia_7 > 15 else "Baja ✅")
    pct_ll    = min(lluvia_7 / 80, 1.0) * 100
    rain_date = pd.to_datetime(last_rain["date"]).strftime("%d %b")

    zona_cols = st.columns(len(ZONAS))
    for i, (zona, peso, color_zona) in enumerate(ZONAS):
        with zona_cols[i]:
            st.markdown(
                "<div class=\"card card-gray\" style=\"padding:12px\">"
                "<div class=\"lsm\">" + zona + "</div>"
                "<div style=\"font-size:0.7rem;color:" + color_zona + ";margin-bottom:4px\">" + peso + "</div>"
                "<div style=\"font-size:1.1rem;font-weight:700;color:" + color_ll + "\">" + f"{lluvia_7:.1f} mm / 7d</div>"
                "<div style=\"background:#2d3348;border-radius:4px;height:6px;margin-top:6px\">"
                "<div style=\"background:" + color_ll + ";width:" + f"{pct_ll:.0f}%;height:6px;border-radius:4px\"></div>"
                "</div>"
                "<div class=\"lsm\" style=\"margin-top:4px\">" + nivel_ll + " — al " + rain_date + "</div>"
                "</div>",
                unsafe_allow_html=True
            )
    st.caption("Dato de Martínez de la Torre (NASA POWER). Próximamente: fetch individual por zona.")

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Movimiento en frontera — promedio 7 dias ──────────────────────────────────
st.markdown("#### 🚛 Movimiento en frontera")
st.caption("Promedio de los últimos 7 días. Pharr/McAllen = ~70% del limón mexicano a Texas.")

if not move_df.empty:
    move_sorted = move_df.sort_values("date")
    last7 = move_sorted.tail(7)
    prev7 = move_sorted.iloc[-14:-7] if len(move_sorted) >= 14 else move_sorted.head(7)

    pharr_hoy  = last7["pharr_seedless_lb"].mean()
    pharr_prev = prev7["pharr_seedless_lb"].mean()
    mx_hoy     = last7["mx_seedless_lb"].mean()
    col_hoy    = last7["colombia_seedless_lb"].mean()
    per_hoy    = last7["peru_seedless_lb"].mean()
    total_hoy  = last7["total_seedless_lb"].mean()
    move_date  = pd.to_datetime(move_sorted.iloc[-1]["date"]).strftime("%d %b")

    pharr_chg  = ((pharr_hoy - pharr_prev) / (pharr_prev + 1)) * 100
    imp_total  = col_hoy + per_hoy
    imp_pct    = (imp_total / (total_hoy + 1)) * 100
    mx_pct     = (mx_hoy / (total_hoy + 1)) * 100

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        color_p = "#ff1744" if pharr_chg > 20 else ("#ffd600" if pharr_chg > 0 else "#00c853")
        desc_p  = "Más oferta → presión bajista" if pharr_chg > 10 else ("Oferta normal" if pharr_chg > -10 else "Menos oferta → precio sube")
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">🚛 Pharr/McAllen — promedio 7d</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:" + color_p + "\">" + f"{pharr_hoy/1e6:.1f}M lbs/día</div>"
            "<div style=\"font-size:0.8rem;color:" + color_p + "\">" + f"{pharr_chg:+.0f}% vs semana anterior</div>"
            "<div class=\"lsm\">" + desc_p + " — al " + move_date + "</div>"
            "</div>",
            unsafe_allow_html=True
        )

    with m2:
        if mx_hoy > 0:
            pct_pharr = pharr_hoy / mx_hoy * 100
            st.markdown(
                "<div class=\"card card-gray\">"
                "<div class=\"lsm\">🇲🇽 Total México — promedio 7d</div>"
                "<div style=\"font-size:1.2rem;font-weight:700;color:#fff\">" + f"{mx_hoy/1e6:.1f}M lbs/día</div>"
                "<div class=\"lsm\">Pharr = " + f"{pct_pharr:.0f}% del total MX</div>"
                "<div class=\"lsm\" style=\"color:#546e7a\">Resto: Laredo, Nogales, Eagle Pass</div>"
                "</div>",
                unsafe_allow_html=True
            )

    with m3:
        color_i = "#ffd600" if imp_pct > 20 else "#90a4ae"
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">🚢 Colombia + Perú — promedio 7d</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:" + color_i + "\">" + f"{imp_total/1e6:.1f}M lbs/día</div>"
            "<div style=\"font-size:0.78rem;color:#78909c\">" + f"{imp_pct:.0f}% del total — históricamente ~5%</div>"
            "<div class=\"lsm\">Col: " + f"{col_hoy/1e6:.1f}M | Per: {per_hoy/1e6:.1f}M lbs</div>"
            "<div class=\"lsm\" style=\"color:#546e7a\">Entran por Miami y Los Ángeles principalmente</div>"
            "</div>",
            unsafe_allow_html=True
        )

    with m4:
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">⚖️ Balance del mercado — promedio 7d</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:#fff\">" + f"{total_hoy/1e6:.1f}M lbs/día</div>"
            "<div style=\"background:#2d3348;border-radius:4px;height:8px;margin:6px 0\">"
            "<div style=\"background:#00c853;width:" + f"{mx_pct:.0f}%;height:8px;border-radius:4px\"></div>"
            "</div>"
            "<div class=\"lsm\">🟢 México " + f"{mx_pct:.0f}% | 🟡 Col+Per {imp_pct:.0f}%</div>"
            "<div class=\"lsm\" style=\"color:#546e7a\">Col+Per va principalmente a Costa Este y LA</div>"
            "</div>",
            unsafe_allow_html=True
        )

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Tipo de cambio ────────────────────────────────────────────────────────────
if not fx_df.empty:
    last_fx  = fx_df.sort_values("date").iloc[-1]
    usdmxn   = float(last_fx.get("usd_mxn", 0))
    chg_7d   = float(last_fx.get("usd_mxn_chg_7d", 0) or 0)
    fx_date  = pd.to_datetime(last_fx["date"]).strftime("%d %b")
    color_fx = "#ff1744" if chg_7d > 0.5 else ("#00c853" if chg_7d < -0.5 else "#ffd600")
    desc_fx  = (
        "Peso débil → productor exporta más → más oferta → presión bajista" if chg_7d > 0.3
        else ("Peso fuerte → menos incentivo a exportar → menos oferta" if chg_7d < -0.3
        else "Tipo de cambio estable — sin presión adicional")
    )

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

# ── Scorecard con fecha explicita ─────────────────────────────────────────────
if not sc.empty:
    # Determinar fechas del scorecard
    sc_sorted = sc.sort_values("abs_error_1d")
    
    # Intentar obtener la fecha de prediccion del forecast
    pred_date_str = ""
    real_date_str = ""
    try:
        last_fc_date = pd.to_datetime(fc["last_date"]).max()
        # La prediccion se hizo el dia anterior al ultimo dato
        pred_date = last_fc_date - pd.Timedelta(days=1)
        real_date = last_fc_date
        pred_date_str = pred_date.strftime("%d %b")
        real_date_str = real_date.strftime("%d %b")
    except:
        pass

    title_extra = ""
    if pred_date_str and real_date_str:
        title_extra = (
            f" — predicción hecha el {pred_date_str}, "
            f"precio real del {real_date_str}"
        )

    st.markdown("### ¿Qué tan cerca estuvo el modelo?" + title_extra)
    st.caption(
        "El modelo predijo el precio del día siguiente. "
        "Aquí comparamos esa predicción vs el precio que realmente publicó USDA. "
        "El rango probable es predicción ± error histórico del modelo."
    )

    for _, row in sc_sorted.iterrows():
        size     = int(row["size"])
        pred     = float(row["pred_1d"])
        real     = float(row["real_1d"])
        err      = float(row["abs_error_1d"])
        pred_dir = str(row.get("pred_dir_1d", "—"))
        real_dir = str(row.get("real_dir_1d", "—"))
        hit      = str(row.get("hit_1d", "")).upper() == "TRUE"

        # MAE del calibre
        fc_row = fc[fc["size"] == size]
        mae_val = float(fc_row["mae_1d"].iloc[0]) if not fc_row.empty and "mae_1d" in fc_row.columns else 1.5
        rango_pred = f"${pred - mae_val:.2f} — ${pred + mae_val:.2f}"

        err_color = "#00c853" if err < 1.5 else ("#ffd600" if err < 3.0 else "#ff1744")
        dentro_rango = (pred - mae_val) <= real <= (pred + mae_val)
        rango_status = (
            "<span style=\"color:#00c853\">✅ Precio real dentro del rango</span>"
            if dentro_rango else
            "<span style=\"color:#ffd600\">⚠️ Precio real fuera del rango</span>"
        )
        dir_html = (
            "<span style=\"color:#00c853;font-weight:700\">✅ Dirección correcta</span>"
            if hit else
            "<span style=\"color:#ff1744;font-weight:700\">❌ Dirección incorrecta</span>"
        )

        st.markdown(
            "<div class=\"card card-gray\" style=\"margin-bottom:8px\">"
            "<div style=\"display:flex;justify-content:space-between;align-items:center\">"
            "<span style=\"font-size:1.05rem;font-weight:700;color:#fff\">Calibre " + str(size) + " BASE</span>"
            "<span style=\"font-size:1.0rem;font-weight:700;color:" + err_color + "\">Diferencia: $" + f"{err:.2f}</span>"
            "</div>"
            "<div style=\"display:flex;gap:24px;margin-top:10px;font-size:0.85rem;flex-wrap:wrap\">"
            "<div>"
            "<div class=\"lsm\">Predijo el modelo</div>"
            "<div style=\"color:#fff;font-size:1rem;font-weight:600\">" + f"${pred:.2f} "
            "<span class=\"" + cd(pred_dir) + "\">" + em(pred_dir) + " " + pred_dir + "</span></div>"
            "<div style=\"font-size:0.75rem;color:#546e7a\">Rango: " + rango_pred + "</div>"
            "</div>"
            "<div>"
            "<div class=\"lsm\">Precio real USDA</div>"
            "<div style=\"color:#fff;font-size:1rem;font-weight:600\">" + f"${real:.2f} "
            "<span class=\"" + cd(real_dir) + "\">" + em(real_dir) + " " + real_dir + "</span></div>"
            "</div>"
            "<div style=\"align-self:center\">" + dir_html + "</div>"
            "<div style=\"align-self:center\">" + rango_status + "</div>"
            "</div></div>",
            unsafe_allow_html=True
        )
