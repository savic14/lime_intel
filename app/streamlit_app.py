"""
streamlit_app.py — Lime Intelligence Dashboard V8
Enfasis en interpretacion operativa en cada seccion
"""
import pandas as pd
import streamlit as st
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
    if (Path(__file__).resolve().parents[1] / "data").exists()
    else Path(__file__).resolve().parent
)

DATA = PROJECT_ROOT / "data/processed"
FORECAST_PATH  = DATA / "daily_forecast_base.csv"
SCORECARD_PATH = DATA / "daily_forecast_scorecard.csv"
PRICE_PATH     = DATA / "shipping_point_core.csv"
MOVE_PATH      = DATA / "movement_core.csv"
FX_PATH        = DATA / "usd_mxn_historico.csv"
MTT_PATH       = DATA / "mtt_prices.csv"

ZONAS_LLUVIA = {
    "mtt":      ("Martínez de la Torre, Ver.", 54, DATA / "lluvia_mtt.csv"),
    "tuxtepec": ("Tuxtepec, Oax.",             16, DATA / "lluvia_tuxtepec.csv"),
    "tabasco":  ("Huimanguillo, Tab.",           7, DATA / "lluvia_tabasco.csv"),
    "yucatan":  ("Valladolid, Yuc.",             5, DATA / "lluvia_yucatan.csv"),
    "slp":      ("Cd. Valles, SLP",              5, DATA / "lluvia_slp.csv"),
}
RAIN_FALLBACK = DATA / "lluvia_veracruz_historico.csv"

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
.lsm{font-size:0.70rem;color:#78909c;text-transform:uppercase;letter-spacing:1px}
.ldate{font-size:0.72rem;color:#546e7a}
.sv{font-size:1.15rem;font-weight:700}
.sube{color:#00c853}.baja{color:#ff1744}.estable{color:#ffd600}
.ca{color:#00c853;font-size:0.8rem}.cb{color:#ffd600;font-size:0.8rem}.cc{color:#78909c;font-size:0.8rem}
.div{border-top:1px solid #2d3348;margin:10px 0}
.tnup{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;background:#1b5e20;color:#00c853}
.tndn{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;background:#b71c1c;color:#ff8a80}
.tnfl{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;background:#33373f;color:#90a4ae}
.tbl{width:100%;font-size:0.82rem;color:#cfd8dc;border-collapse:collapse}
.tbl td{padding:3px 0}
.badge-old{background:#37474f;color:#90a4ae;font-size:0.65rem;padding:2px 6px;border-radius:4px;margin-left:6px}
.src-box{background:#161926;border-radius:8px;padding:10px 14px;margin:4px 0;border:1px solid #2d3348}
.interp{font-size:0.8rem;color:#b0bec5;margin-top:6px;line-height:1.4}
.interp-key{color:#fff;font-weight:600}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load():
    fc    = pd.read_csv(FORECAST_PATH).sort_values("size").reset_index(drop=True) if FORECAST_PATH.exists() else pd.DataFrame()
    sc    = pd.read_csv(SCORECARD_PATH).sort_values("rank_del_dia").reset_index(drop=True) if SCORECARD_PATH.exists() else pd.DataFrame()
    price = pd.read_csv(PRICE_PATH) if PRICE_PATH.exists() else pd.DataFrame()
    move  = pd.read_csv(MOVE_PATH)  if MOVE_PATH.exists()  else pd.DataFrame()
    fx    = pd.read_csv(FX_PATH)    if FX_PATH.exists()    else pd.DataFrame()
    mtt   = pd.read_csv(MTT_PATH)   if MTT_PATH.exists()   else pd.DataFrame()
    for df in [fc, sc, price, move, fx, mtt]:
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return fc, sc, price, move, fx, mtt

fc, sc, price_df, move_df, fx_df, mtt_df = load()

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
    except: return "cc"

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
    if any(x in t for x in ["higher","firmer","strong"]):
        return "<span class=\"tnup\">▲ USDA: Precio subiendo</span>"
    if any(x in t for x in ["lower","weak","light","exceed"]):
        return "<span class=\"tndn\">▼ USDA: Precio bajando</span>"
    if any(x in t for x in ["steady","stable","unchanged"]):
        return "<span class=\"tnfl\">━ USDA: Precio estable</span>"
    return ""

def get_price_detail(size, quality="BASE"):
    if price_df.empty: return None
    s = price_df[(price_df["size"]==size)&(price_df["quality"]==quality)].sort_values("date")
    if s.empty: return None
    last = s.iloc[-1]
    def sf(col):
        v = last.get(col)
        return float(v) if v is not None and pd.notna(v) else None
    return {
        "official": float(last["official_price"]),
        "low":   sf("low_price"),   "high":  sf("high_price"),
        "mlow":  sf("mostly_low_price"), "mhigh": sf("mostly_high_price"),
        "tone":  str(last.get("market_tone","")),
        "demand": str(last.get("demand_tone","")),
    }

def pred_range_str(pred_val, mae_val):
    try:
        p = float(pred_val); m = float(mae_val)
        return f"${p-m:.2f} — ${p+m:.2f}"
    except: return ""

def get_predictions(size, row):
    sources = []
    mae = row.get("mae_1d", 1.5)
    p1  = row.get("predicted_target_1d","")
    d1  = str(row.get("direction_1d",""))
    clf = str(row.get("direction_clf_1d_es",""))
    conf = row.get("confidence_clf_1d","")
    rng = pred_range_str(p1, mae)
    if rng:
        dir_final = clf if clf not in ["","nan"] else d1
        conf_pct = fpc(conf)
        interp = ""
        if "BAJA" in dir_final.upper():
            interp = "El modelo anticipa corrección hacia abajo mañana. Evalúa si conviene vender hoy o esperar."
        elif "SUBE" in dir_final.upper():
            interp = "El modelo anticipa que el precio sube mañana. Podría convenir esperar un día antes de vender."
        else:
            interp = "El modelo no ve un movimiento claro mañana. El precio probablemente se mantenga en rango similar."
        sources.append({"nombre":"Modelo ML","rango":rng,"dir":dir_final,"conf":conf_pct,"color":"#4fc3f7","interp":interp})

    detail = get_price_detail(size)
    if detail:
        t = detail["tone"].lower()
        if any(x in t for x in ["higher","firmer"]):
            td,ti = "SUBE","USDA reportó precio subiendo en su último reporte. Señal directa del mercado."
        elif any(x in t for x in ["lower","weak","exceed"]):
            td,ti = "BAJA","USDA reportó precio bajando. Hay más oferta que demanda en el mercado."
        elif any(x in t for x in ["steady","stable"]):
            td,ti = "ESTABLE","USDA reportó precio estable. El mercado no muestra presión en ninguna dirección."
        else:
            td,ti = "", ""
        if td and detail["mlow"] and detail["mhigh"]:
            rng_usda = f"${detail['mlow']:.0f} — ${detail['mhigh']:.0f}"
            sources.append({"nombre":"Señal USDA","rango":rng_usda+" (rango donde más se vendió hoy)","dir":td,"conf":"Directa","color":"#a5d6a7","interp":ti})

    if not mtt_df.empty and not fx_df.empty:
        try:
            last_mtt = mtt_df.dropna(subset=["precio_min_kg"]).sort_values("date").iloc[-1]
            last_fx  = fx_df.sort_values("date").iloc[-1]
            usdmxn   = float(last_fx["usd_mxn"])
            mtt_date = pd.to_datetime(last_mtt["date"]).strftime("%d %b")
            min_kg   = float(last_mtt["precio_min_kg"])
            max_kg   = float(last_mtt["precio_max_kg"])
            KG_CAJA  = 18.14
            mtt_low  = round((min_kg*KG_CAJA/usdmxn)+15.0, 2)
            mtt_high = round((max_kg*KG_CAJA/usdmxn)+22.0, 2)
            interp_mtt = (
                f"Precio en campo MTT era ${min_kg:.0f}-{max_kg:.0f} MXN/kg el {mtt_date}. "
                "Convertido a USD/caja McAllen sumando empaque, flete y cruce estimado ($15-22). "
                "Úsalo como referencia del piso de precio — si el mercado baja de este rango, los productores dejan de exportar."
            )
            sources.append({"nombre":f"MTT en McAllen est. ({mtt_date})","rango":f"${mtt_low:.2f} — ${mtt_high:.2f}","dir":"REFERENCIA","conf":"±margen","color":"#ffcc80","interp":interp_mtt})
        except:
            pass
    return sources

def render_card(row, dim=False):
    size   = int(row["size"])
    precio = float(row.get("last_official_price",0))
    fecha  = str(row.get("last_date",""))
    d1=str(row.get("direction_1d","ESTABLE")); p1=row.get("predicted_target_1d","")
    d2=str(row.get("direction_2d","ESTABLE")); p2=row.get("predicted_target_2d","")
    d3=str(row.get("direction_3d","ESTABLE")); p3=row.get("predicted_target_3d","")
    d7=str(row.get("direction_7d","")); p7=row.get("predicted_target_7d","")
    clf=str(row.get("direction_clf_1d_es","ESTABLE"))
    conf=row.get("confidence_clf_1d",""); mae=row.get("mae_1d",1.5)

    detail  = get_price_detail(size)
    tone_h  = tone_badge(detail["tone"]) if detail else ""
    tone_sec= ("<div class=\"div\"></div>"+tone_h) if tone_h else ""

    range_html=""
    if detail and detail["mlow"] and detail["mhigh"]:
        range_html=(
            "<div style=\"font-size:0.9rem;color:#90a4ae;margin-bottom:2px\">"
            "Se vendió más entre: <b style=\"color:#fff\">${:.0f} — ${:.0f}</b>".format(detail["mlow"],detail["mhigh"])+
            " &nbsp;|&nbsp; Rango completo: ${:.0f} — ${:.0f}".format(detail["low"],detail["high"])+
            "</div>"
        )

    sig=clf if clf not in ["","nan"] else d1
    bc ="card-old" if dim else border(sig)
    pc ="price-old" if dim else "price-big"
    badge="<span class=\"badge-old\">DATOS VIEJOS</span>" if dim else ""

    sources_html=""
    if not dim:
        sources=get_predictions(size,row)
        if sources:
            sources_html="<div class=\"div\"></div><div class=\"lsm\">¿Qué dicen las 3 fuentes para mañana?</div>"
            for src in sources:
                dir_color="#00c853" if src["dir"]=="SUBE" else ("#ff1744" if src["dir"]=="BAJA" else "#ffd600")
                sources_html+=(
                    "<div class=\"src-box\">"
                    "<div style=\"display:flex;justify-content:space-between;align-items:center\">"
                    "<span style=\"font-size:0.8rem;font-weight:700;color:"+src["color"]+"\">"+src["nombre"]+"</span>"
                    "<span style=\"font-size:0.75rem;color:#546e7a\">"+src["conf"]+"</span>"
                    "</div>"
                    "<div style=\"font-size:1.0rem;font-weight:600;color:#fff\">"+src["rango"]+"</div>"
                    "<div style=\"font-size:0.8rem;color:"+dir_color+"\">"+em(src["dir"])+" "+src["dir"]+"</div>"
                    "<div class=\"interp\">"+src.get("interp","")+"</div>"
                    "</div>"
                )

    d7_row=""
    if p7 and str(p7) not in ["","nan"]:
        r7=pred_range_str(p7,mae)
        d7_row="<tr><td><b>7 días</b></td><td class=\""+cd(d7)+"\">"+em(d7)+" "+d7+"</td><td style=\"color:#fff\">"+(r7 if r7 else fp(p7))+"</td></tr>"

    html=(
        "<div class=\"card "+bc+"\">"
        "<div class=\"lsm\">Calibre "+str(size)+" BASE "+badge+"</div>"
        "<div class=\""+pc+"\">"+fp(precio)+"</div>"
        +range_html+
        "<div class=\"ldate\">Último precio oficial USDA — "+fecha+"</div>"
        +tone_sec
        +sources_html+
        "<div class=\"div\"></div>"
        "<table class=\"tbl\">"
        "<tr style=\"color:#546e7a;font-size:0.7rem\"><td>HORIZONTE</td><td>DIR</td><td>RANGO PROBABLE</td></tr>"
        "<tr><td><b>Mañana</b></td><td class=\""+cd(d1)+"\">"+em(d1)+" "+d1+"</td><td style=\"color:#fff\">"+(pred_range_str(p1,mae) or fp(p1))+"</td></tr>"
        "<tr><td><b>2 días</b></td><td class=\""+cd(d2)+"\">"+em(d2)+" "+d2+"</td><td style=\"color:#fff\">"+(pred_range_str(p2,mae) or fp(p2))+"</td></tr>"
        "<tr><td><b>3 días</b></td><td class=\""+cd(d3)+"\">"+em(d3)+" "+d3+"</td><td style=\"color:#fff\">"+(pred_range_str(p3,mae) or fp(p3))+"</td></tr>"
        +d7_row+
        "</table>"
        "<div class=\"div\"></div>"
        "<div class=\"lsm\">Error histórico promedio del modelo: "+("${:.2f}".format(float(mae)) if mae and str(mae)!="nan" else "—")+"</div>"
        "</div>"
    )
    return html

# ── Header ────────────────────────────────────────────────────────────────────
max_date = pd.to_datetime(fc["last_date"]).max()
days_old = (pd.Timestamp.today().normalize()-max_date).days
col_t,col_s = st.columns([3,1])
with col_t: st.markdown("## 🍋 Lime Intelligence — McAllen FOB")
with col_s:
    if days_old>3: st.error(f"⚠️ Hace {days_old} días — corre: limeupdate")
    else: st.success(f"✅ Datos al {max_date.strftime('%d %b %Y')}")

dates  = pd.to_datetime(fc["last_date"])
desync = fc[dates<dates.max()]
if not desync.empty:
    atrasados=[f"{int(r['size'])} ({r['last_date']})" for _,r in desync.iterrows()]
    st.warning(f"⚠️ Sin datos recientes: calibres {', '.join(atrasados)} — USDA no los reportó recientemente")

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Forecast ──────────────────────────────────────────────────────────────────
fresh_fc=fc[dates==dates.max()].copy()
stale_fc=fc[dates<dates.max()].copy()

st.markdown(f"### Forecast — datos al {max_date.strftime('%d %b %Y')}")
st.caption(
    "💡 Cada tarjeta muestra el precio actual de USDA y 3 fuentes independientes que predicen el precio de mañana. "
    "Cuando las 3 fuentes apuntan en la misma dirección, la señal es más confiable. "
    "Usa los rangos — es más probable que el precio caiga dentro del rango que exactamente en el número."
)

if not fresh_fc.empty:
    cols=st.columns(min(len(fresh_fc),3))
    for i,size in enumerate(fresh_fc["size"].tolist()):
        row=fresh_fc[fresh_fc["size"]==size].iloc[0]
        with cols[i%3]: st.markdown(render_card(row,dim=False),unsafe_allow_html=True)

if not stale_fc.empty:
    stale_date=pd.to_datetime(stale_fc["last_date"]).max().strftime("%d %b %Y")
    st.markdown(
        "<div style=\"font-size:0.75rem;font-weight:700;color:#546e7a;"
        "text-transform:uppercase;letter-spacing:2px;margin:18px 0 8px 0\">"
        "⚠️ Sin datos recientes de USDA — último reporte: "+stale_date+"</div>",
        unsafe_allow_html=True)
    cols2=st.columns(min(len(stale_fc),3))
    for i,size in enumerate(stale_fc["size"].tolist()):
        row=stale_fc[stale_fc["size"]==size].iloc[0]
        with cols2[i%3]: st.markdown(render_card(row,dim=True),unsafe_allow_html=True)

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Lluvia ────────────────────────────────────────────────────────────────────
st.markdown("### 🌧 Lluvia en zonas productoras")
st.markdown(
    "**¿Para qué sirve esto?** La lluvia fuerte detiene el corte en campo. "
    "Si hay lluvia intensa hoy, en 5-10 días llega menos fruta a McAllen → precio sube. "
    "Si no llueve y hay corte activo, en 5-10 días llega más fruta → precio baja. "
    "**Mira el acumulado de 7 días, no el día puntual.**"
)

zona_cols=st.columns(len(ZONAS_LLUVIA))
all_lluvias=[]
for i,(key,(nombre,pct,path)) in enumerate(ZONAS_LLUVIA.items()):
    with zona_cols[i]:
        if path.exists():
            df_z=pd.read_csv(path); df_z["date"]=pd.to_datetime(df_z["date"]); fuente="NASA POWER"
        elif RAIN_FALLBACK.exists():
            df_z=pd.read_csv(RAIN_FALLBACK); df_z["date"]=pd.to_datetime(df_z["date"]); fuente="MTT (proxy)"
        else:
            df_z=pd.DataFrame(); fuente="sin datos"

        if not df_z.empty:
            last=df_z.sort_values("date").iloc[-1]
            ll7 = float(last.get("lluvia_7d", df_z.tail(7)["lluvia_mm"].sum() if "lluvia_mm" in df_z.columns else 0) or 0)
            all_lluvias.append(ll7)
            rain_date=pd.to_datetime(last["date"]).strftime("%d %b")
            color_ll="#ff1744" if ll7>40 else ("#ffd600" if ll7>15 else "#00c853")
            nivel_ll="Alta ⚠️" if ll7>40 else ("Media" if ll7>15 else "Baja ✅")
            pct_ll=min(ll7/80,1.0)*100
            impacto="En 5-10d → menos fruta → precio SUBE" if ll7>15 else "Sin impacto — corte normal"
            st.markdown(
                "<div class=\"card card-gray\" style=\"padding:12px\">"
                "<div class=\"lsm\">"+nombre+"</div>"
                "<div style=\"font-size:0.7rem;color:#78909c;margin-bottom:4px\">"+str(pct)+"% prod. nacional | "+fuente+"</div>"
                "<div style=\"font-size:1.1rem;font-weight:700;color:"+color_ll+"\">"+f"{ll7:.1f} mm / 7d</div>"
                "<div style=\"background:#2d3348;border-radius:4px;height:6px;margin-top:6px\">"
                "<div style=\"background:"+color_ll+";width:"+f"{pct_ll:.0f}%;height:6px;border-radius:4px\"></div>"
                "</div>"
                "<div class=\"lsm\" style=\"margin-top:4px\">"+nivel_ll+" — al "+rain_date+"</div>"
                "<div style=\"font-size:0.72rem;color:#90a4ae;margin-top:4px\">"+impacto+"</div>"
                "</div>",
                unsafe_allow_html=True)
        else:
            all_lluvias.append(0)
            st.markdown("<div class=\"card card-gray\" style=\"padding:12px\"><div class=\"lsm\">"+nombre+"</div><div style=\"color:#546e7a\">Sin datos</div></div>",unsafe_allow_html=True)

# Interpretacion global de lluvia
if all_lluvias:
    avg_ll=sum(all_lluvias)/len(all_lluvias)
    if avg_ll>40:
        st.error("🌧 **Lluvia intensa en zonas productoras** — Espera menos fruta en McAllen en 5-10 días. Precio tenderá a subir.")
    elif avg_ll>15:
        st.warning("🌦 **Lluvia moderada** — Puede haber algo menos de oferta en los próximos días. Monitorea.")
    else:
        st.success("☀️ **Sin lluvia significativa** — Corte normal en campo. La oferta debería mantenerse estable.")

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Movimiento en frontera ────────────────────────────────────────────────────
st.markdown("### 🚛 Entrada de fruta por la frontera")
st.markdown(
    "**¿Para qué sirve esto?** Muestra cuánta fruta cruzó la frontera hacia EE.UU. en los últimos 7 días. "
    "**Más camiones = más oferta = presión para que el precio baje.** "
    "**Menos camiones = menos oferta = precio tiende a subir.** "
    "El dato de Pharr/McAllen es el más directo para tu mercado — es la fruta que ya está llegando."
)

if not move_df.empty:
    move_sorted=move_df.sort_values("date")
    last7=move_sorted.tail(7); prev7=move_sorted.iloc[-14:-7] if len(move_sorted)>=14 else move_sorted.head(7)
    pharr_hoy=last7["pharr_seedless_lb"].mean(); pharr_prev=prev7["pharr_seedless_lb"].mean()
    mx_hoy=last7["mx_seedless_lb"].mean(); col_hoy=last7["colombia_seedless_lb"].mean()
    per_hoy=last7["peru_seedless_lb"].mean(); total_hoy=last7["total_seedless_lb"].mean()
    move_date=pd.to_datetime(move_sorted.iloc[-1]["date"]).strftime("%d %b")
    pharr_chg=((pharr_hoy-pharr_prev)/(pharr_prev+1))*100
    imp_total=col_hoy+per_hoy; imp_pct=(imp_total/(total_hoy+1))*100; mx_pct=(mx_hoy/(total_hoy+1))*100

    m1,m2,m3,m4=st.columns(4)
    with m1:
        color_p="#ff1744" if pharr_chg>20 else ("#ffd600" if pharr_chg>0 else "#00c853")
        if pharr_chg>20:
            desc_p="Entró mucho más que la semana pasada → hay más oferta → precio puede BAJAR"
        elif pharr_chg>5:
            desc_p="Entró un poco más que la semana pasada → ligera presión bajista"
        elif pharr_chg<-20:
            desc_p="Entró mucho menos que la semana pasada → menos oferta → precio puede SUBIR"
        elif pharr_chg<-5:
            desc_p="Entró un poco menos → ligera presión alcista"
        else:
            desc_p="Entrada similar a la semana pasada → mercado estable en oferta"
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">🚛 Pharr/McAllen — TU MERCADO</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:"+color_p+"\">"+f"{pharr_hoy/1e6:.1f}M lbs/día</div>"
            "<div style=\"font-size:0.85rem;color:"+color_p+"\">"+f"{pharr_chg:+.0f}% vs semana anterior</div>"
            "<div class=\"interp\">"+desc_p+"</div>"
            "<div class=\"lsm\" style=\"margin-top:4px\">Dato más reciente: "+move_date+"</div>"
            "</div>",unsafe_allow_html=True)
    with m2:
        if mx_hoy>0:
            pct_ph=pharr_hoy/mx_hoy*100
            st.markdown(
                "<div class=\"card card-gray\">"
                "<div class=\"lsm\">🇲🇽 Total México — todos los puertos</div>"
                "<div style=\"font-size:1.2rem;font-weight:700;color:#fff\">"+f"{mx_hoy/1e6:.1f}M lbs/día</div>"
                "<div class=\"interp\">Pharr representa el "+f"{pct_ph:.0f}% de todo el limón mexicano. "
                "El resto entra por Laredo, Nogales y Eagle Pass hacia otros mercados de EE.UU.</div>"
                "</div>",unsafe_allow_html=True)
    with m3:
        color_i="#ffd600" if imp_pct>20 else "#90a4ae"
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">🚢 Colombia + Perú (importado)</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:"+color_i+"\">"+f"{imp_total/1e6:.1f}M lbs/día</div>"
            "<div class=\"interp\">"+f"{imp_pct:.0f}% del total en este reporte. "
            "Históricamente ~5%. Este limón entra principalmente por Miami y Los Ángeles — "
            "no compite directamente en McAllen pero sí afecta el precio nacional.</div>"
            "</div>",unsafe_allow_html=True)
    with m4:
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">⚖️ Balance del mercado — prom. 7d</div>"
            "<div style=\"font-size:1.2rem;font-weight:700;color:#fff\">"+f"{total_hoy/1e6:.1f}M lbs/día total</div>"
            "<div style=\"background:#2d3348;border-radius:4px;height:8px;margin:6px 0\">"
            "<div style=\"background:#00c853;width:"+f"{mx_pct:.0f}%;height:8px;border-radius:4px\"></div>"
            "</div>"
            "<div class=\"interp\">🟢 México "+f"{mx_pct:.0f}% | 🟡 Col+Per {imp_pct:.0f}%<br>"
            "Cuando México baja de 85% es señal de que la oferta mexicana está disminuyendo.</div>"
            "</div>",unsafe_allow_html=True)

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Tipo de cambio ────────────────────────────────────────────────────────────
if not fx_df.empty:
    last_fx=fx_df.sort_values("date").iloc[-1]
    usdmxn=float(last_fx.get("usd_mxn",0))
    chg_7d=float(last_fx.get("usd_mxn_chg_7d",0) or 0)
    fx_date=pd.to_datetime(last_fx["date"]).strftime("%d %b")
    color_fx="#ff1744" if chg_7d>0.5 else ("#00c853" if chg_7d<-0.5 else "#ffd600")
    if chg_7d>0.3:
        desc_fx="El peso se debilitó → el productor recibe más pesos por cada dólar → tiene más incentivo para exportar → más oferta → presión bajista en precio McAllen."
    elif chg_7d<-0.3:
        desc_fx="El peso se fortaleció → el productor recibe menos pesos → menos incentivo para exportar → puede haber menos oferta → presión alcista."
    else:
        desc_fx="Tipo de cambio estable esta semana → sin presión adicional por este lado."
    st.markdown("### 💱 Tipo de cambio USD/MXN")
    st.caption("El tipo de cambio afecta directamente el incentivo del productor mexicano para exportar.")
    col_fx,_=st.columns([1,3])
    with col_fx:
        st.markdown(
            "<div class=\"card card-gray\">"
            "<div class=\"lsm\">USD/MXN al "+fx_date+"</div>"
            "<div style=\"font-size:1.8rem;font-weight:700;color:#fff\">"+f"{usdmxn:.4f}</div>"
            "<div style=\"font-size:0.85rem;color:"+color_fx+"\">"+f"{chg_7d:+.4f} vs hace 7 días</div>"
            "<div class=\"interp\" style=\"margin-top:8px\">"+desc_fx+"</div>"
            "</div>",unsafe_allow_html=True)

st.markdown("<div class=\"div\"></div>", unsafe_allow_html=True)

# ── Scorecard ─────────────────────────────────────────────────────────────────
if not sc.empty:
    try:
        last_fc_date=pd.to_datetime(fc["last_date"]).max()
        pred_date=(last_fc_date-pd.Timedelta(days=1)).strftime("%d %b")
        real_date=last_fc_date.strftime("%d %b")
        title_dates=f" — predicción del {pred_date} vs precio real del {real_date}"
    except:
        title_dates=""

    st.markdown("### 📊 ¿Qué tan cerca estuvo el modelo ayer?"+title_dates)
    st.markdown(
        "**¿Para qué sirve esto?** Te muestra si el modelo está funcionando bien. "
        f"El modelo hizo sus predicciones el **{pred_date}** para el precio del **{real_date}**. "
        "Aquí comparamos esa predicción vs lo que realmente publicó USDA. "
        "**Si el precio real cae dentro del rango predicho, el modelo está calibrado correctamente.** "
        "No busques que acierte el número exacto — busca que acierte el rango y la dirección."
    )

    for _,row in sc.sort_values("abs_error_1d").iterrows():
        size=int(row["size"]); pred=float(row["pred_1d"]); real=float(row["real_1d"])
        err=float(row["abs_error_1d"]); pred_dir=str(row.get("pred_dir_1d","—"))
        real_dir=str(row.get("real_dir_1d","—")); hit=str(row.get("hit_1d","")).upper()=="TRUE"
        fc_row=fc[fc["size"]==size]
        mae_val=float(fc_row["mae_1d"].iloc[0]) if not fc_row.empty and "mae_1d" in fc_row.columns else 1.5
        rng=f"${pred-mae_val:.2f} — ${pred+mae_val:.2f}"
        dentro=(pred-mae_val)<=real<=(pred+mae_val)
        err_color="#00c853" if err<1.5 else ("#ffd600" if err<3.0 else "#ff1744")
        dir_html=("<span style=\"color:#00c853;font-weight:700\">✅ Dirección correcta</span>" if hit
                  else "<span style=\"color:#ff1744;font-weight:700\">❌ Dirección incorrecta</span>")
        rng_html=("<span style=\"color:#00c853\">✅ Dentro del rango</span>" if dentro
                  else "<span style=\"color:#ffd600\">⚠️ Fuera del rango</span>")
        st.markdown(
            "<div class=\"card card-gray\" style=\"margin-bottom:8px\">"
            "<div style=\"display:flex;justify-content:space-between;align-items:center\">"
            "<span style=\"font-size:1.05rem;font-weight:700;color:#fff\">Calibre "+str(size)+" BASE</span>"
            "<span style=\"font-size:1.0rem;font-weight:700;color:"+err_color+"\">Diferencia: $"+f"{err:.2f}</span>"
            "</div>"
            "<div style=\"display:flex;gap:24px;margin-top:10px;font-size:0.85rem;flex-wrap:wrap\">"
            "<div><div class=\"lsm\">Predijo el modelo ("+pred_date+")</div>"
            "<div style=\"color:#fff;font-size:1rem;font-weight:600\">"+fp(pred)+" <span class=\""+cd(pred_dir)+"\">"+em(pred_dir)+" "+pred_dir+"</span></div>"
            "<div style=\"font-size:0.75rem;color:#546e7a\">Rango: "+rng+"</div></div>"
            "<div><div class=\"lsm\">Precio real USDA ("+real_date+")</div>"
            "<div style=\"color:#fff;font-size:1rem;font-weight:600\">"+fp(real)+" <span class=\""+cd(real_dir)+"\">"+em(real_dir)+" "+real_dir+"</span></div></div>"
            "<div style=\"align-self:center\">"+dir_html+"</div>"
            "<div style=\"align-self:center\">"+rng_html+"</div>"
            "</div></div>",
            unsafe_allow_html=True)
