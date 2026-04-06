"""
streamlit_app.py — Lime Intelligence V15
Base: V14 (funcionando)
Fixes:
  1. Forecast cards: renderizar una por una via st.columns (fix HTML concat bug)
  2. Scorecard cards: mismo fix — loop con st.columns individual
  3. API key: leer de st.secrets["ANTHROPIC_API_KEY"] O variable de entorno
  4. Terminal markets: sigue usando archivos individuales terminal_*.csv (igual que V14)
"""
import os
import html as _html
import pandas as pd
import streamlit as st
import requests, json
from pathlib import Path
from datetime import date, timedelta

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
MTT_PATH        = DATA / "mtt_prices.csv"
SNIIM_PATH      = DATA / "sniim_limon_persa.csv"
DEST_WEATHER_PATH = DATA / "dest_weather.csv"
TCP_PRICE_PATH    = DATA / "mtt_bascula_prices.csv"

ZONAS_LLUVIA = [
    ("mtt",      "Martínez de la Torre", 54, DATA/"lluvia_mtt.csv"),
    ("tuxtepec", "Tuxtepec, Oax.",       16, DATA/"lluvia_tuxtepec.csv"),
    ("tabasco",  "Huimanguillo, Tab.",    7,  DATA/"lluvia_tabasco.csv"),
    ("yucatan",  "Valladolid, Yuc.",      5,  DATA/"lluvia_yucatan.csv"),
    ("slp",      "Cd. Valles, SLP",       5,  DATA/"lluvia_slp.csv"),
]
RAIN_FALLBACK = DATA / "lluvia_veracruz_historico.csv"

FLETES = {
    "terminal_atlanta.csv":  {"label": "Atlanta",      "flete": 5.28},
    "terminal_chicago.csv":  {"label": "Chicago",      "flete": 4.91},
    "terminal_la.csv":       {"label": "Los Angeles",  "flete": 4.40},
    "terminal_ny.csv":       {"label": "New York",     "flete": 8.06},
    "terminal_miami.csv":    {"label": "Miami",        "flete": 5.56},
}

CALENDAR_EVENTS = {
    "2026-03-30": ("Semana Santa MX", "Puede bajar demanda y movimiento en frontera."),
    "2026-04-06": ("Post Semana Santa", "Regresa actividad — posible repunte."),
    "2026-05-25": ("Memorial Day", "Demanda alta en EE.UU."),
    "2026-06-29": ("4th of July", "Demanda alta — precio puede subir."),
    "2026-11-23": ("Thanksgiving", "Demanda alta — precio tiende a subir."),
    "2026-12-21": ("Navidad", "Demanda alta en EE.UU."),
}

st.set_page_config(page_title="Lime Intel", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
*{box-sizing:border-box}
.block-container{padding:0.7rem 1.2rem !important;max-width:100% !important}
.stApp{background:#f5f6fa}
.c-g{color:#1b5e20}.c-r{color:#b71c1c}.c-y{color:#e65100}.c-b{color:#1a237e}.c-m{color:#37474f}

/* Tabla forecast detallada */
.tbl-wrap{background:#fff;border-radius:10px;border:1px solid #dde1ea;overflow-x:auto;margin-bottom:10px}
.th{background:#eef0f7;display:grid;padding:8px 14px;font-size:11px;font-weight:700;
    color:#37474f;text-transform:uppercase;letter-spacing:0.8px;border-bottom:1px solid #dde1ea;
    grid-template-columns:60px 68px 130px 90px 240px 130px 60px;gap:8px;align-items:center;min-width:800px}
.tr{display:grid;padding:11px 14px;border-bottom:1px solid #f0f2f7;
    grid-template-columns:60px 68px 130px 90px 240px 130px 60px;gap:8px;align-items:start;min-width:800px}
.tr:last-child{border:none}
.tr:hover{background:#f8f9fd}
.sz{font-size:14px;font-weight:800;color:#1a237e;padding-top:2px}
.pr{font-size:20px;font-weight:800;color:#0d1b6e;line-height:1.1}
.rng-hdr{font-size:13px;font-weight:700;color:#1a237e}
.rng-sub{font-size:11px;color:#546e7a;margin-top:2px}
.tend-arrow{font-size:24px;font-weight:800;line-height:1}
.tend-txt{font-size:11px;color:#37474f;margin-top:3px;line-height:1.3;font-weight:600}
.hz{display:flex;gap:6px;margin-bottom:3px;align-items:center}
.hl{width:26px;font-size:11px;color:#37474f;font-weight:700;flex-shrink:0}
.hd{font-size:11px;font-weight:800;width:14px;flex-shrink:0}
.hr{font-size:11px;font-weight:700;color:#1a237e}
.hs{color:#1b5e20}.hb{color:#b71c1c}.he{color:#455a64}
.sc-ttl{font-size:11px;font-weight:700;color:#37474f;margin-bottom:4px}
.sc-row{display:flex;justify-content:space-between;margin-bottom:3px}
.sc-lbl{font-size:11px;color:#37474f;font-weight:600}
.sc-val{font-size:11px;font-weight:800}
.ay-v{font-size:14px;font-weight:800;text-align:right}
.ay-s{font-size:10px;color:#455a64;text-align:right;line-height:1.3;margin-top:1px}
.tag-e{font-size:10px;background:#e8eaf6;color:#1a237e;padding:1px 5px;border-radius:5px;margin-left:3px;font-weight:700}
.tag-o{font-size:10px;background:#eceff1;color:#546e7a;padding:1px 5px;border-radius:5px;margin-left:3px;font-weight:600}

/* Forecast cards */
.fc-card-wrap{background:#fff;border:1px solid #dde1ea;border-radius:12px;
              padding:14px 16px;position:relative;margin-bottom:4px}
.fc-card-wrap.stale{opacity:0.6;border-style:dashed}
.fc-calibre{font-size:12px;font-weight:700;color:#546e7a;text-transform:uppercase;letter-spacing:1px}
.fc-price{font-size:2.2rem;font-weight:800;color:#0d1b6e;line-height:1.1;margin:4px 0}
.fc-pred{font-size:14px;color:#37474f;margin-top:4px;font-weight:600}
.fc-dir-BAJA,.fc-dir-DOWN{color:#c62828;font-weight:700}
.fc-dir-SUBE,.fc-dir-UP{color:#2e7d32;font-weight:700}
.fc-dir-ESTABLE,.fc-dir-LATERAL{color:#e65100;font-weight:700}
.fc-conf{font-size:12px;color:#546e7a;margin-top:4px;font-weight:600}
.fc-mae{font-size:11px;color:#78909c;margin-top:6px}
.fc-stale-badge{background:#eceff1;color:#90a4ae;font-size:10px;font-weight:700;
                border-radius:4px;padding:2px 6px;display:inline-block;margin-bottom:4px}

/* Scorecard cards */
.sc-card-wrap{background:#fff;border:1px solid #dde1ea;border-radius:12px;
              padding:14px 16px;margin-bottom:4px}
.sc-card-size{font-size:11px;font-weight:700;color:#90a4ae;text-transform:uppercase;letter-spacing:1.5px}
.sc-card-err-ok{font-size:1.4rem;font-weight:800;color:#2e7d32}
.sc-card-err-warn{font-size:1.4rem;font-weight:800;color:#e65100}
.sc-card-err-bad{font-size:1.4rem;font-weight:800;color:#c62828}
.sc-card-row{display:flex;justify-content:space-between;font-size:12px;margin-top:5px;color:#546e7a}
.sc-hit-yes{color:#2e7d32;font-weight:700}
.sc-hit-no{color:#c62828;font-weight:700}

/* Resumen ejecutivo */
.exec-card{background:#fff;border-radius:12px;border:2px solid #1a237e;padding:16px 20px;margin-bottom:14px}
.exec-title{font-size:13px;font-weight:800;color:#1a237e;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px}
.exec-body{font-size:13px;color:#212121;line-height:1.7;white-space:pre-wrap}
.ai-signal{display:inline-block;padding:5px 16px;border-radius:20px;font-size:13px;font-weight:800;letter-spacing:1px}
.sig-buy{background:#e8f5e9;color:#1b5e20;border:1px solid #4caf50}
.sig-sell{background:#fce4ec;color:#880e4f;border:1px solid #e91e63}
.sig-hold{background:#fff8e1;color:#e65100;border:1px solid #ff9800}

/* Señales */
.sig{background:#fff;border-radius:10px;border:1px solid #dde1ea;padding:14px 16px;height:100%}
.sig-lbl{font-size:11px;font-weight:700;color:#37474f;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px}
.sig-val{font-size:20px;font-weight:800;margin:2px 0;line-height:1.1}
.sig-desc{font-size:12px;color:#37474f;line-height:1.4;margin-top:5px;font-weight:500}
.mt{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
.mt th{color:#37474f;font-size:11px;text-transform:uppercase;padding:4px 6px;text-align:left;
       font-weight:700;border-bottom:1px solid #eef0f7;letter-spacing:0.5px}
.mt td{padding:5px 6px;border-bottom:1px solid #f5f6fa;color:#1a237e;font-weight:600}
.mt tr:last-child td{border:none}

/* Header */
.hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px}
.main-title{font-size:17px;font-weight:800;color:#0d1b6e}
.chip-ok{background:#e8f5e9;color:#1b5e20;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700}
.chip-warn{background:#fff3e0;color:#bf360c;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700}
.sec{font-size:11px;font-weight:700;color:#37474f;text-transform:uppercase;letter-spacing:2px;margin:16px 0 8px}
.cal-alert{background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:8px 14px;
           font-size:12px;color:#bf360c;margin-bottom:10px;font-weight:600}
.cal-info{background:#e8eaf6;border:1px solid #c5cae9;border-radius:8px;padding:8px 14px;
          font-size:12px;color:#1a237e;margin-bottom:10px;font-weight:600}
.divider{border-top:1px solid #eef0f7;margin:10px 0}
.note{font-size:11px;color:#546e7a;margin-bottom:10px;font-weight:500}

/* Lluvia */
.rain-bars{display:flex;gap:2px;align-items:flex-end;height:44px;margin:8px 0 2px}
.rain-sep{width:3px;background:#1a237e;height:44px;border-radius:2px;flex-shrink:0}
.rain-legend{display:flex;justify-content:space-between;font-size:10px;color:#90a4ae;margin-bottom:6px}
</style>
""", unsafe_allow_html=True)


# ─────────────── HELPERS ─────────────────────────────────────────────────────

def get_api_key():
    # 1. Variable de entorno
    env_key = os.environ.get("GROQ_API_KEY", "")
    if env_key.startswith("gsk_"):
        return env_key
    # 2. st.secrets
    try:
        k = st.secrets["GROQ_API_KEY"]
        if k: return k
    except Exception:
        pass
    # 3. Leer secrets.toml directamente
    try:
        import toml
        candidates = [
            Path(os.getcwd()) / ".streamlit" / "secrets.toml",
            Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml",
            Path(__file__).resolve().parent / ".streamlit" / "secrets.toml",
        ]
        for p in candidates:
            if p.exists():
                data = toml.load(str(p))
                k = data.get("GROQ_API_KEY", "")
                if k: return k
    except Exception:
        pass
    return ""

@st.cache_data(ttl=300)
def load():
    fc    = pd.read_csv(FORECAST_PATH) if FORECAST_PATH.exists() else pd.DataFrame()
    sc    = pd.read_csv(SCORECARD_PATH) if SCORECARD_PATH.exists() else pd.DataFrame()
    price = pd.read_csv(PRICE_PATH)    if PRICE_PATH.exists()    else pd.DataFrame()
    move  = pd.read_csv(MOVE_PATH)     if MOVE_PATH.exists()     else pd.DataFrame()
    fx    = pd.read_csv(FX_PATH)       if FX_PATH.exists()       else pd.DataFrame()
    mtt   = pd.read_csv(MTT_PATH)      if MTT_PATH.exists()      else pd.DataFrame()
    for df in [fc, sc, price, move, fx, mtt]:
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
    sniim = pd.read_csv(SNIIM_PATH)       if SNIIM_PATH.exists()       else pd.DataFrame()
    tcp   = pd.read_csv(TCP_PRICE_PATH)    if TCP_PRICE_PATH.exists()    else pd.DataFrame()
    destw = pd.read_csv(DEST_WEATHER_PATH) if DEST_WEATHER_PATH.exists() else pd.DataFrame()
    if not fc.empty:
        fc["last_date_clean"] = fc["last_date"].str.replace(r" \(est\.\)", "", regex=True)
        fc["date_clean"] = pd.to_datetime(fc["last_date_clean"], errors="coerce")
        fc = fc.sort_values("size").reset_index(drop=True)
    return fc, sc, price, move, fx, mtt, sniim, destw, tcp

fc, sc_df, price_df, move_df, fx_df, mtt_df, sniim_df, destw_df, tcp_df = load()
if fc.empty:
    st.error("Sin datos — corre: limeupdate"); st.stop()

def em(d):
    d = str(d).upper()
    return "▲" if ("SUBE" in d or "UP" in d) else ("▼" if ("BAJA" in d or "DOWN" in d) else "━")

def hz_cls(d):
    d = str(d).upper()
    return "hs" if ("SUBE" in d or "UP" in d) else ("hb" if ("BAJA" in d or "DOWN" in d) else "he")

def fp(p, dec=0):
    try: return f"${float(p):.{dec}f}"
    except: return "—"

def frange(pred, mae, dec=0):
    try: p=float(pred); m=float(mae); return f"${p-m:.{dec}f}–${p+m:.{dec}f}"
    except: return "—"

def pct_color(pct):
    if pct is None: return "c-m"
    return "c-g" if pct >= 0.6 else ("c-y" if pct >= 0.4 else "c-r")

def days_ago_label(dt_str):
    try:
        d = pd.to_datetime(dt_str).date()
        delta = (date.today() - d).days
        if delta == 0: return "hoy"
        if delta == 1: return "ayer"
        return f"hace {delta}d"
    except: return "—"

def dir_display(d):
    d = str(d).strip().upper()
    MAP = {
        "UP":      ("▲ SUBE",    "fc-dir-SUBE"),
        "SUBE":    ("▲ SUBE",    "fc-dir-SUBE"),
        "DOWN":    ("▼ BAJA",    "fc-dir-BAJA"),
        "BAJA":    ("▼ BAJA",    "fc-dir-BAJA"),
        "LATERAL": ("◆ LATERAL", "fc-dir-LATERAL"),
        "ESTABLE": ("◆ ESTABLE", "fc-dir-ESTABLE"),
    }
    return MAP.get(d, (d, "fc-dir-ESTABLE"))

def get_detail(size, quality="BASE"):
    if price_df.empty: return {}
    s = price_df[(price_df["size"] == size) & (price_df["quality"] == quality)].sort_values("date")
    if s.empty: return {}
    last = s.iloc[-1]
    def sf(c):
        v = last.get(c); return float(v) if v is not None and pd.notna(v) else None
    return {"mlow": sf("mostly_low_price"), "mhigh": sf("mostly_high_price"),
            "low": sf("low_price"), "high": sf("high_price"),
            "tone": str(last.get("market_tone", ""))}

def mtt_est():
    if mtt_df.empty or fx_df.empty: return None
    try:
        last_mtt = mtt_df.dropna(subset=["precio_min_kg"]).sort_values("date").iloc[-1]
        usdmxn   = float(fx_df.sort_values("date").iloc[-1]["usd_mxn"])
        lo = round((float(last_mtt["precio_min_kg"]) * 18.14 / usdmxn) + 15, 1)
        hi = round((float(last_mtt["precio_max_kg"]) * 18.14 / usdmxn) + 22, 1)
        return {"lo": lo, "hi": hi, "fecha": pd.to_datetime(last_mtt["date"]).strftime("%d %b")}
    except: return None

def build_sc_stats():
    stats = {}
    if sc_df.empty or fc.empty: return stats
    for size in fc["size"].unique():
        size = int(size)
        sc_s = (sc_df[sc_df["size"] == size].sort_values("date")
                if "date" in sc_df.columns else sc_df[sc_df["size"] == size])
        if sc_s.empty: continue
        fc_row  = fc[fc["size"] == size]
        mae_val = float(fc_row["mae_1d"].iloc[0]) if not fc_row.empty and "mae_1d" in fc_row.columns else 1.5
        en_rango, dir_ok, errs = [], [], []
        for _, r in sc_s.tail(5).iterrows():
            try:
                pred=float(r["pred_1d"]); real=float(r["real_1d"]); err=float(r["abs_error_1d"])
                hit = str(r.get("hit_1d","")).upper() == "TRUE"
                en_rango.append((pred - mae_val) <= real <= (pred + mae_val))
                dir_ok.append(hit); errs.append(err)
            except: pass
        n = len(en_rango)
        sc_last = sc_s.iloc[-1] if len(sc_s) > 0 else None
        ayer_ok = False; ayer_err = 0.0
        if sc_last is not None:
            try:
                pred=float(sc_last["pred_1d"]); real=float(sc_last["real_1d"])
                ayer_err=float(sc_last["abs_error_1d"])
                ayer_ok=(pred - mae_val) <= real <= (pred + mae_val)
            except: pass
        stats[size] = {"n": n,
            "pct_rango": sum(en_rango)/n if n>0 else None,
            "pct_dir":   sum(dir_ok)/n   if n>0 else None,
            "mae_prom":  sum(errs)/len(errs) if errs else mae_val,
            "ayer_ok": ayer_ok, "ayer_err": ayer_err}
    return stats

sc_stats = build_sc_stats()


# ─────────────── RESUMEN EJECUTIVO IA ────────────────────────────────────────

def build_context_for_ai():
    ctx = []
    hoy = date.today()
    ctx.append(f"FECHA: {hoy.strftime('%A %d %B %Y')}")

    if not price_df.empty:
        # BASE prices
        base = price_df[price_df["quality"] == "BASE"].sort_values("date")
        ctx.append("\nPRECIOS MCALLEN FOB (USDA) — BASE (US#1 estándar):")
        for size in [175, 200, 230, 250]:
            s = base[base["size"] == size]
            if not s.empty:
                last = s.iloc[-1]
                mlow=last.get("mostly_low_price"); mhigh=last.get("mostly_high_price")
                lo=last.get("low_price"); hi=last.get("high_price")
                rng_mostly = f"mostly ${float(mlow):.0f}-${float(mhigh):.0f}" if pd.notna(mlow) and pd.notna(mhigh) else ""
                rng_total  = f"total ${float(lo):.0f}-${float(hi):.0f}" if pd.notna(lo) and pd.notna(hi) else ""
                tone = str(last.get("market_tone", ""))
                ctx.append(f"  Calibre {size}: ${last['official_price']:.2f} | {rng_mostly} | {rng_total} | USDA: {tone}")
        # #1 = Fine appearance, #2 = Fair/lower appearance
        fine = price_df[price_df["quality"] == "#1"].sort_values("date")
        if not fine.empty:
            ctx.append("\nPRECIOS #1 / FINE APPEARANCE (fruta de primera, verde intenso — precio premium):")
            for size in [175, 200, 230, 250]:
                s = fine[fine["size"] == size]
                if not s.empty:
                    last = s.iloc[-1]
                    mlow=last.get("mostly_low_price"); mhigh=last.get("mostly_high_price")
                    lo=last.get("low_price"); hi=last.get("high_price")
                    rng_m = f"mostly ${float(mlow):.0f}-${float(mhigh):.0f}" if pd.notna(mlow) and pd.notna(mhigh) else ""
                    rng_t = f"total ${float(lo):.0f}-${float(hi):.0f}" if pd.notna(lo) and pd.notna(hi) else ""
                    ctx.append(f"  Calibre {size}: oficial ${last['official_price']:.0f} | {rng_m} | {rng_t}")
        fair = price_df[price_df["quality"] == "#2"].sort_values("date")
        if not fair.empty:
            ctx.append("\nPRECIOS #2 / FAIR APPEARANCE (fruta con defectos, color pálido — precio descuento):")
            for size in [175, 200, 230, 250]:
                s = fair[fair["size"] == size]
                if not s.empty:
                    last = s.iloc[-1]
                    mlow=last.get("mostly_low_price"); mhigh=last.get("mostly_high_price")
                    rng_m = f"mostly ${float(mlow):.0f}-${float(mhigh):.0f}" if pd.notna(mlow) and pd.notna(mhigh) else ""
                    ctx.append(f"  Calibre {size}: oficial ${last['official_price']:.0f} | {rng_m}")
        ctx.append("\nNOTA CALIDAD USDA: #1=Fine appearance (premio $8-14 sobre BASE), BASE=estándar, #2=Fair (descuento $2-4).")
        ctx.append("Fruta TCP bien empacada y verde clasifica #1 o BASE. Fruta amarilla o con daño clasifica #2.")

    if not fc.empty:
        ctx.append("\nFORECAST MODELO:")
        max_d = fc["date_clean"].max()
        for _, row in fc[fc["date_clean"] == max_d].iterrows():
            size=int(row["size"]); lp=float(row["last_official_price"])
            p7=row.get("predicted_target_7d",""); d7=str(row.get("direction_7d",""))
            try: slope=(float(p7)-lp)/7; tend=f"tendencia {slope:+.2f}/día"
            except: tend=""
            ctx.append(f"  Calibre {size}: hoy ${lp:.0f} | 7d {em(d7)} rango {frange(p7,row.get('mae_1d',1.3))} | {tend}")

    if not move_df.empty:
        ms = move_df.sort_values("date").copy()
        ms["week_start"] = ms["date"].dt.to_period("W").dt.start_time
        weekly = ms.groupby("week_start").agg(
            pharr_total=("pharr_seedless_lb","sum"), fecha_fin=("date","max")
        ).reset_index().sort_values("week_start", ascending=False)
        weekly["chg"] = weekly["pharr_total"].pct_change(-1) * 100
        ctx.append("\nMOVIMIENTO PHARR/MCALLEN:")
        for _, w in weekly.head(3).iterrows():
            fi=pd.to_datetime(w["week_start"]).strftime("%d %b")
            ff=pd.to_datetime(w["fecha_fin"]).strftime("%d %b")
            cam=int(w["pharr_total"]/40000)
            chg_s=f"({w['chg']:+.0f}% vs ant.)" if pd.notna(w["chg"]) else ""
            ctx.append(f"  {fi}-{ff}: {w['pharr_total']/1e6:.1f}M lbs ~{cam} camiones {chg_s}")

    lluvia_resumen = []
    for key, nombre, pct, path in ZONAS_LLUVIA:
        src = path if path.exists() else RAIN_FALLBACK
        if not src.exists(): continue
        try:
            df=pd.read_csv(src); df["date"]=pd.to_datetime(df["date"],errors="coerce")
            df=df.dropna(subset=["date"]).sort_values("date")
            today=pd.Timestamp.today().normalize()
            hist=df[df["date"]<today]
            ll7_r=hist.tail(7)["lluvia_mm"].sum() if not hist.empty and "lluvia_mm" in hist.columns else 0
            lluvia_resumen.append(f"  {nombre} ({pct}%): real 7d={ll7_r:.1f}mm")
        except: pass
    if lluvia_resumen:
        ctx.append("\nLLUVIA EN ZONAS PRODUCTORAS:")
        ctx.extend(lluvia_resumen)

    if not fx_df.empty:
        lf=fx_df.sort_values("date").iloc[-1]
        usdmxn=float(lf["usd_mxn"]); chg7=float(lf.get("usd_mxn_chg_7d",0) or 0)
        ctx.append(f"\nTIPO DE CAMBIO: USD/MXN={usdmxn:.4f} (cambio 7d: {chg7:+.4f})")

    # Precio MTT báscula
    if not tcp_df.empty and "precio_mxn_kg" in tcp_df.columns:
        last_t = tcp_df.sort_values("date").iloc[-1]
        pt = float(last_t["precio_mxn_kg"]) if pd.notna(last_t.get("precio_mxn_kg")) else None
        if pt:
            usdmxn = float(fx_df.sort_values("date").iloc[-1]["usd_mxn"]) if not fx_df.empty else 17.5
            pt_usd = (pt * 18.14) / usdmxn
            cal_t  = str(last_t.get("calibre",""))
            ctx.append(f"\nPRECIO BÁSCULA TCP (mi costo de compra): ${pt:.2f} MXN/kg = ${pt_usd:.1f} USD/caja est. calibre {cal_t} (fecha: {str(last_t['date'])[:10]})")
            ctx.append(f"  Este es mi costo real de compra en báscula MTT en origen. Margen bruto estimado = precio McAllen FOB - ${pt_usd:.1f} USD/caja")

    # Temperatura ciudades destino
    if not destw_df.empty:
        try:
            fw = destw_df[destw_df["tipo"]=="forecast"].copy()
            fw["date"] = pd.to_datetime(fw["date"])
            next7 = fw[fw["date"] <= pd.Timestamp.today() + timedelta(days=7)]
            if not next7.empty:
                ctx.append("\nTEMPERATURA PRÓXIMOS 7 DÍAS EN DESTINOS (°C máx promedio):")
                for city in ["Chicago","Atlanta","New York","Los Angeles","Houston"]:
                    cd = next7[next7["city"]==city]
                    if not cd.empty:
                        avg = cd["temp_max"].mean()
                        signal = "CALOR ALTO → demanda ↑↑" if avg>=30 else ("CALOR MODERADO → demanda ↑" if avg>=22 else "FRÍO → demanda ↓")
                        ctx.append(f"  {city}: {avg:.0f}°C — {signal}")
        except Exception:
            pass

    eventos=[]
    for i in range(14):
        d=(date.today()+timedelta(days=i)).strftime("%Y-%m-%d")
        if d in CALENDAR_EVENTS:
            ev,desc=CALENDAR_EVENTS[d]; eventos.append(f"  En {i} días: {ev} — {desc}")
    if eventos:
        ctx.append("\nEVENTOS PRÓXIMOS 14 DÍAS:"); ctx.extend(eventos)

    return "\n".join(ctx)


@st.cache_data(ttl=1800)
def generate_executive_summary(context_str, fecha_str, api_key=""):
    if not api_key:
        return ("HOLD",
                "⚠️  GROQ_API_KEY no configurada.\n\n"
                "Crea el archivo  .streamlit/secrets.toml  con:\n\n"
                "    GROQ_API_KEY = 'gsk_...'")
    prompt = f"""Eres Victor, operador senior de Top Fresh LLC (McAllen TX), importador de limón persa México-EE.UU.
Compras en Tabasco/Veracruz y vendes FOB McAllen a distribuidores como Houston Fruitland.
Tu fruta principal es calibres 230 y 250, pero analiza TODOS los calibres disponibles en los datos para identificar cuál tiene mejor precio relativo esta semana.
Hoy es {fecha_str}.

DATOS DEL SISTEMA:
{context_str}

Analiza estos datos como operador que arriesga dinero real, no como académico.

FORMATO DE RESPUESTA (primera línea SOLO la señal BUY/SELL/HOLD, luego el análisis):

BUY

SITUACIÓN DEL MERCADO
Explica en 2-3 oraciones qué está pasando con el precio esta semana, si está alto/bajo vs histórico, y por qué.

OFERTA Y CRUCES
Explica qué significa el volumen de Pharr esta semana vs la semana anterior. Si bajó mucho, explica que menos fruta = precio sube. Si subió, explica presión bajista.

CALIDAD Y PRECIO DE TU FRUTA
Dado que tu fruta es calibre 230/250 BASE/Fine, ¿en qué rango de precio debería estar? Menciona el premio de Fine appearance si aplica.

MEJOR MERCADO TERMINAL
¿A qué mercado conviene mandar la fruta? ¿Por qué? Menciona el margen neto estimado por caja.

CLIMA Y OFERTA FUTURA
¿Qué implica la lluvia actual para la oferta en 7-14 días? ¿Habrá más o menos fruta llegando?

ALERTA DE CALENDARIO
Si hay evento relevante (Semana Santa, feriados) que afecte demanda u operación, explícalo.

RECOMENDACIÓN CONCRETA
Dile a Victor exactamente qué hacer esta semana: ¿comprar cuántas cajas, a qué precio máximo, vender a quién, esperar?

CONFIANZA: ALTA/MEDIA/BAJA
Explica en una línea por qué tienes esa confianza (qué datos faltan o son inciertos).

Máximo 35 líneas total. Sé específico con números. Habla en primera persona como Victor."""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "content-type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "max_tokens": 900,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        data = resp.json()
        if resp.status_code != 200:
            err_msg = data.get("error", {}).get("message", str(resp.text))
            return "HOLD", f"⚠️ Error Groq API ({resp.status_code}): {err_msg}"
        text   = data["choices"][0]["message"]["content"].strip()
        lines  = text.splitlines()
        signal = lines[0].strip().upper()
        if signal not in ("BUY","SELL","HOLD"): signal = "HOLD"
        return signal, "\n".join(lines[1:]).strip()
    except Exception as e:
        return "HOLD", f"⚠️ Error conexión: {e}"


# ─────────────── CALENDARIO ──────────────────────────────────────────────────
hoy = date.today()
es_martes = hoy.weekday() == 1
prox_martes = hoy + timedelta(days=(1 - hoy.weekday()) % 7)
eventos_activos = []
for i in range(14):
    d = (hoy + timedelta(days=i)).strftime("%Y-%m-%d")
    if d in CALENDAR_EVENTS:
        ev, desc = CALENDAR_EVENTS[d]; eventos_activos.append((ev, desc, i))


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
max_date = fc["date_clean"].max()
days_old = (pd.Timestamp.today().normalize() - max_date).days
chip_cls = "chip-ok" if days_old <= 3 else "chip-warn"
chip_txt = (f"✓ Datos al {max_date.strftime('%d %b %Y')}" if days_old <= 3
            else f"⚠ Hace {days_old}d — corre limeupdate")
st.markdown(
    f"<div class='hdr'><span class='main-title'>🍋 Lime Intelligence — McAllen FOB</span>"
    f"<span class='{chip_cls}'>{chip_txt}</span></div>",
    unsafe_allow_html=True)

if es_martes:
    st.markdown("<div class='cal-alert'>📅 Hoy es martes — USDA publica reporte semanal. Corre limeupdate en la tarde.</div>", unsafe_allow_html=True)
else:
    dias_m = (1 - hoy.weekday()) % 7
    if dias_m > 0:
        st.markdown(f"<div class='cal-info'>📅 Próximo martes {prox_martes.strftime('%d %b')} — USDA publica reporte semanal de movimiento.</div>", unsafe_allow_html=True)
for ev, desc, dias in eventos_activos[:1]:
    lbl = "Esta semana" if dias < 7 else f"En {dias} días"
    st.markdown(f"<div class='cal-alert'>🗓 {lbl}: {ev} — {desc}</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — RESUMEN EJECUTIVO IA
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='sec'>📋 Resumen ejecutivo — análisis de mercado</div>", unsafe_allow_html=True)

with st.spinner("Generando análisis de mercado..."):
    signal, ai_body = generate_executive_summary(
        build_context_for_ai(), hoy.strftime("%A %d de %B de %Y"),
        api_key=get_api_key())

sig_class = {"BUY":"sig-buy","SELL":"sig-sell","HOLD":"sig-hold"}.get(signal,"sig-hold")
sig_emoji = {"BUY":"🟢 BUY","SELL":"🔴 SELL","HOLD":"🟡 HOLD"}.get(signal, signal)

col_ai, col_sig = st.columns([4, 1])
with col_ai:
    safe_body = _html.escape(ai_body).replace("\n", "<br>")
    st.markdown(
        f"<div class='exec-card'>"
        f"<div class='exec-title'>📋 Análisis — {hoy.strftime('%d %b %Y')}</div>"
        f"<div class='exec-body'>{safe_body}</div></div>",
        unsafe_allow_html=True)
with col_sig:
    st.markdown(
        f"<div style='display:flex;flex-direction:column;align-items:center;"
        f"justify-content:center;height:100%;gap:10px;padding-top:8px'>"
        f"<span class='ai-signal {sig_class}'>{sig_emoji}</span>"
        f"<div style='font-size:10px;color:#90a4ae;text-align:center'>Actualiza<br>cada 30 min</div>"
        f"</div>", unsafe_allow_html=True)

if st.button("🔄 Actualizar análisis"):
    st.cache_data.clear(); st.rerun()

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — FORECAST CARDS  ← FIX: una tarjeta por st.column, no HTML concat
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='sec'>📊 Forecast de precios por calibre</div>", unsafe_allow_html=True)

dates    = fc["date_clean"]; max_d = dates.max()
fresh_fc = fc[dates == max_d].copy()
stale_fc = fc[dates < max_d].copy()

def render_fc_cards(rows_df, stale=False):
    if rows_df.empty: return
    n_cols = min(len(rows_df), 4)
    cols   = st.columns(n_cols)
    for idx, (_, row) in enumerate(rows_df.iterrows()):
        size    = int(row["size"])
        quality = str(row.get("quality", "BASE"))
        price   = float(row.get("last_official_price", 0))
        p1d     = row.get("predicted_target_1d", None)
        p7d     = row.get("predicted_target_7d", None)
        d1_raw  = str(row.get("direction_clf_1d_es", row.get("direction_1d", "—")))
        conf    = row.get("confidence_clf_1d", None)
        mae     = row.get("mae_1d", None)
        ld      = str(row.get("last_date_clean", row.get("last_date", "")))

        d1_txt, d1_cls = dir_display(d1_raw)

        def safe_fmt(v, prefix="$", dec=2):
            try:
                f = float(v)
                if pd.isna(f): return "—"
                return f"{prefix}{f:.{dec}f}"
            except: return "—"

        p1d_str  = safe_fmt(p1d)
        p7d_str  = safe_fmt(p7d)
        conf_str = f"Confianza: {float(conf)*100:.0f}%" if conf and str(conf) not in ["nan",""] else ""
        mae_str  = f"MAE: ${float(mae):.2f}" if mae and str(mae) not in ["nan",""] else ""
        age_str  = days_ago_label(ld)
        stale_html = "<span class='fc-stale-badge'>DATO VIEJO</span><br>" if stale else ""
        card_cls   = "fc-card-wrap stale" if stale else "fc-card-wrap"

        # Precios #1/BASE/#2 desde shipping_point_core
        quality_rows = ""
        if not price_df.empty:
            for q, label, color in [("#1","Fine #1","#1b5e20"),("BASE","Base","#1a237e"),("#2","Fair #2","#b71c1c")]:
                sq = price_df[(price_df["size"]==size) & (price_df["quality"]==q)].sort_values("date")
                if not sq.empty:
                    last_q = sq.iloc[-1]
                    ml = last_q.get("mostly_low_price"); mh = last_q.get("mostly_high_price")
                    if pd.notna(ml) and pd.notna(mh):
                        quality_rows += f"<div style=\'display:flex;justify-content:space-between;font-size:12px;margin-top:3px\'><span style=\'color:{color};font-weight:700\'>{label}</span><span style=\'color:{color};font-weight:800\'>${ml:.0f}\u2013${mh:.0f}</span></div>"

        with cols[idx % n_cols]:
            q_section = f"<div style=\'border-top:1px solid #f0f0f0;margin-top:8px;padding-top:6px\'>{quality_rows}</div>" if quality_rows else ""
            st.markdown(f"""
<div class="{card_cls}">
  {stale_html}
  <div class="fc-calibre">{size} · {quality} · {age_str}</div>
  <div class="fc-price">${price:.2f}</div>
  <div class="fc-pred">1D: <strong>{p1d_str}</strong> &nbsp; 7D: <strong>{p7d_str}</strong></div>
  <div class="fc-pred">Dir: <span class="{d1_cls}">{d1_txt}</span></div>
  {q_section}
  <div class="fc-conf">{conf_str}</div>
  <div class="fc-mae">{mae_str}</div>
</div>""", unsafe_allow_html=True)

if not fresh_fc.empty:
    render_fc_cards(fresh_fc, stale=False)

if not stale_fc.empty:
    st.markdown(
        "<div style='font-size:12px;font-weight:600;color:#90a4ae;margin:14px 0 6px'>"
        "Calibres con datos desactualizados <em>(USDA no publicó precio reciente)</em></div>",
        unsafe_allow_html=True)
    render_fc_cards(stale_fc, stale=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — FORECAST DETALLADO (tabla V14 — funciona sin cambios)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='sec'>📈 Forecast detallado — horizontes y rangos</div>", unsafe_allow_html=True)

def render_table(rows_df, banner=""):
    html = "<div class='tbl-wrap'>"
    if banner:
        html += f"<div style='background:#fff8e1;padding:7px 14px;font-size:11px;color:#bf360c;font-weight:700;border-bottom:1px solid #ffe082'>⚠ {banner}</div>"
    html += ("<div class='th'><div>Calibre</div><div>Precio</div><div>Rango hoy</div>"
             "<div>Tendencia</div><div>Horizontes</div><div>Acierto modelo</div><div>Ayer</div></div>")
    for _, row in rows_df.iterrows():
        size = int(row["size"]); lp=float(row["last_official_price"])
        mae  = float(row.get("mae_1d",1.3)); est=bool(row.get("estimated_price",False))
        ld   = str(row.get("last_date_clean","")); det=get_detail(size)
        tag  = "<span class='tag-e'>EST</span>" if est else ("" if det.get("mlow") else "<span class='tag-o'>OLD</span>")
        if det.get("mlow") and det.get("mhigh"):
            rng_html=(f"<div class='rng-hdr'>{fp(det['mlow'])}–{fp(det['mhigh'])}</div>"
                      f"<div class='rng-sub'>{fp(det['low'])}–{fp(det['high'])} total</div>")
        elif est:
            rng_html="<div class='rng-sub'>Est. calibre<br>adyacente</div>"
        else:
            rng_html=f"<div class='rng-sub'>Sin dato USDA<br>desde {ld}</div>"
        try:
            p7v=float(row.get("predicted_target_7d","")); slope=(p7v-lp)/7
            if   slope>0.5:  tarr,tcls,tdesc="↗","c-g","Sube gradual<br>próx. 2 sem."
            elif slope>0.15: tarr,tcls,tdesc="↗","c-g","Leve alza"
            elif slope<-0.5: tarr,tcls,tdesc="↘","c-r","Baja gradual<br>próx. 2 sem."
            elif slope<-0.15:tarr,tcls,tdesc="↘","c-r","Leve baja"
            else:             tarr,tcls,tdesc="→","c-b","Sin cambio"
        except: tarr,tcls,tdesc="→","c-b","—"
        tend_html=f"<div class='tend-arrow {tcls}'>{tarr}</div><div class='tend-txt'>{tdesc}</div>"
        hz_html=""
        for h,col_p,col_d,lbl in [(1,"predicted_target_1d","direction_1d","1d"),
                                    (2,"predicted_target_2d","direction_2d","2d"),
                                    (3,"predicted_target_3d","direction_3d","3d"),
                                    (7,"predicted_target_7d","direction_7d","7d")]:
            pp=row.get(col_p,""); dd=str(row.get(col_d,""))
            if pp and str(pp) not in ["","nan"]:
                mae_h=mae*(1+h*0.08); rng=frange(pp,mae_h)
                hz_html+=f"<div class='hz'><span class='hl'>{lbl}</span><span class='hd {hz_cls(dd)}'>{em(dd)}</span><span class='hr'>{rng}</span></div>"
        try:
            p7v=float(row.get("predicted_target_7d","")); slope=(p7v-lp)/7
            for h,lbl in [(10,"10d"),(14,"14d")]:
                p_h=lp+slope*h; mae_h=mae*(1+h*0.08); rng=frange(p_h,mae_h)
                dir_h="SUBE" if slope>0.15 else ("BAJA" if slope<-0.15 else "ESTABLE")
                hz_html+=f"<div class='hz'><span class='hl'>{lbl}</span><span class='hd {hz_cls(dir_h)}'>{em(dir_h)}</span><span class='hr'>{rng}</span></div>"
        except: pass
        st_=sc_stats.get(size,{})
        if st_ and st_.get("n",0)>0:
            n_=st_["n"]; pr=st_["pct_rango"]; pd_=st_["pct_dir"]; me=st_["mae_prom"]
            sc_html=(f"<div class='sc-ttl'>Últimos {n_} días</div>"
                     f"<div class='sc-row'><span class='sc-lbl'>En rango</span><span class='sc-val {pct_color(pr)}'>{pr:.0%}</span></div>"
                     f"<div class='sc-row'><span class='sc-lbl'>Dirección</span><span class='sc-val {pct_color(pd_)}'>{pd_:.0%}</span></div>"
                     f"<div class='sc-row'><span class='sc-lbl'>Error prom.</span><span class='sc-val'>±${me:.2f}</span></div>")
        else:
            sc_html="<div class='sc-ttl' style='color:#90a4ae'>Sin historial</div>"
        if st_:
            ay_ok=st_["ayer_ok"]; ay_err=st_["ayer_err"]
            ay_c="c-g" if ay_ok else "c-r"
            ay_t="en rango" if ay_ok else "fuera rango"
            ayer_html=f"<div class='ay-v {ay_c}'>{'✓' if ay_ok else '✗'}</div><div class='ay-s'>{ay_t}<br>±${ay_err:.2f}</div>"
        else:
            ayer_html="<div class='ay-v' style='color:#e0e0e0'>—</div>"
        html+=(f"<div class='tr'><div class='sz'>{size}{tag}</div><div class='pr'>{fp(lp)}</div>"
               f"<div>{rng_html}</div><div>{tend_html}</div>"
               f"<div>{hz_html}</div><div>{sc_html}</div><div>{ayer_html}</div></div>")
    html += "</div>"
    return html

if not fresh_fc.empty:
    st.markdown(render_table(fresh_fc), unsafe_allow_html=True)
if not stale_fc.empty:
    est_mask = (stale_fc["estimated_price"]==True) if "estimated_price" in stale_fc.columns else pd.Series([False]*len(stale_fc))
    est_rows=stale_fc[est_mask]; old_rows=stale_fc[~est_mask]
    if not est_rows.empty:
        st.markdown(render_table(est_rows,"Calibres estimados desde adyacente — USDA no los reportó recientemente"), unsafe_allow_html=True)
    if not old_rows.empty:
        st.markdown(render_table(old_rows,"Sin datos recientes de USDA"), unsafe_allow_html=True)

st.markdown("<div class='note'>Verde ≥60% · Amarillo ≥40% · Rojo &lt;40% — % de días en que el precio real cayó dentro del rango predicho (últimos 5 días).</div>", unsafe_allow_html=True)
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — SCORECARD  ← FIX: una tarjeta por st.column, no HTML concat
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='sec'>🎯 Scorecard · Precisión del modelo</div>", unsafe_allow_html=True)

if not sc_df.empty:
    size_col = "size" if "size" in sc_df.columns else None
    pred_col = next((c for c in ["pred_1d","predicted_target_1d"] if c in sc_df.columns), None)
    real_col = next((c for c in ["real_1d","actual_1d"]          if c in sc_df.columns), None)
    err_col  = next((c for c in ["abs_error_1d","mae_1d"]        if c in sc_df.columns), None)
    hit_col  = next((c for c in ["hit_1d","direction_hit"]       if c in sc_df.columns), None)

    total   = len(sc_df)
    hits    = int(sc_df[hit_col].astype(str).str.upper().isin(["TRUE","1","YES"]).sum()) if hit_col else 0
    avg_err = sc_df[err_col].mean() if err_col else None

    pct_txt = f"{hits/total*100:.0f}%" if total else "—"
    err_txt = f"${avg_err:.2f}" if avg_err else "—"
    hit_col_c = "#2e7d32" if total and hits/total >= 0.6 else "#e65100" if total and hits/total >= 0.4 else "#c62828"
    err_col_c = "#2e7d32" if avg_err and avg_err < 1.5 else "#e65100" if avg_err and avg_err < 3.5 else "#c62828"
    st.markdown(
        f"<div style='display:flex;gap:24px;margin-bottom:14px;flex-wrap:wrap'>"
        f"<div><div style='font-size:11px;color:#78909c;font-weight:700;text-transform:uppercase;letter-spacing:1px'>Aciertos dirección</div>"
        f"<div style='font-size:1.6rem;font-weight:800;color:{hit_col_c}'>{hits}/{total} <span style='font-size:1rem'>{pct_txt}</span></div></div>"
        f"<div><div style='font-size:11px;color:#78909c;font-weight:700;text-transform:uppercase;letter-spacing:1px'>Error promedio 1D</div>"
        f"<div style='font-size:1.6rem;font-weight:800;color:{err_col_c}'>{err_txt}</div></div>"
        f"<div><div style='font-size:11px;color:#78909c;font-weight:700;text-transform:uppercase;letter-spacing:1px'>Calibres en scorecard</div>"
        f"<div style='font-size:1.6rem;font-weight:800;color:#1a237e'>{total}</div></div>"
        f"</div>",
        unsafe_allow_html=True)

    n_cards  = len(sc_df)
    cols_sc  = st.columns(min(n_cards, 4))
    for idx, (_, r) in enumerate(sc_df.iterrows()):
        size    = str(int(r[size_col])) if size_col else "—"
        quality = str(r.get("quality","BASE"))
        pred    = r.get(pred_col, None) if pred_col else None
        real    = r.get(real_col, None) if real_col else None
        err     = r.get(err_col,  None) if err_col  else None
        hit     = str(r.get(hit_col,"")).upper() if hit_col else ""

        hit_bool = hit in ("TRUE","1","YES")
        try:    err_f = float(err)
        except: err_f = None
        err_cls  = ("sc-card-err-ok"   if err_f and err_f < 1.5 else
                    "sc-card-err-warn" if err_f and err_f < 3.5 else "sc-card-err-bad")
        err_str  = f"${err_f:.2f}"       if err_f  and pd.notna(err_f)  else "—"
        pred_str = f"${float(pred):.2f}" if pred   and pd.notna(pred)   else "—"
        real_str = f"${float(real):.2f}" if real   and pd.notna(real)   else "—"
        hit_str  = "<span class='sc-hit-yes'>✓ Dirección OK</span>" if hit_bool else "<span class='sc-hit-no'>✗ Dirección errónea</span>"

        with cols_sc[idx % len(cols_sc)]:
            st.markdown(f"""
<div class="sc-card-wrap">
  <div class="sc-card-size">{size} · {quality}</div>
  <div class="{err_cls}">{err_str} <span style="font-size:11px;font-weight:400;color:#90a4ae">error abs</span></div>
  <div class="sc-card-row"><span>Predicho</span><strong>{pred_str}</strong></div>
  <div class="sc-card-row"><span>Real</span><strong>{real_str}</strong></div>
  <div style="font-size:11px;margin-top:5px">{hit_str}</div>
</div>""", unsafe_allow_html=True)
else:
    st.info("No se encontró daily_forecast_scorecard.csv — se genera tras el primer ciclo de validación.")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — SEÑALES (lluvia, movimiento, FX) — igual que V14
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='sec'>📡 Señales del mercado</div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)

def render_rain_bars(key, path):
    if not path.exists(): path = RAIN_FALLBACK
    if not path.exists(): return "", 0, 0
    try:
        df=pd.read_csv(path); df["date"]=pd.to_datetime(df["date"],errors="coerce")
        df=df.dropna(subset=["date"]).sort_values("date")
        today=pd.Timestamp.today().normalize()
        df_hist=df[df["date"]<today].tail(14)
        df_fc  =df[df["date"]>=today].head(14) if "tipo" in df.columns else pd.DataFrame()
        max_mm =max(df_hist["lluvia_mm"].max() if not df_hist.empty else 0,
                    df_fc["lluvia_mm"].max()   if not df_fc.empty  else 0, 5)
        html="<div class='rain-bars'>"
        for _,row in df_hist.iterrows():
            mm=float(row.get("lluvia_mm",0) or 0); h=max(int(mm/max_mm*40),2)
            c_="#b71c1c" if mm>20 else ("#e65100" if mm>10 else "#1b5e20" if mm>1 else "#e0e4ea")
            d_=row["date"].strftime("%d/%m")
            html+=f"<div title='{d_}: {mm:.1f}mm' style='width:5px;height:{h}px;background:{c_};border-radius:2px 2px 0 0;flex-shrink:0'></div>"
        html+="<div class='rain-sep'></div>"
        for _,row in df_fc.iterrows():
            mm=float(row.get("lluvia_mm",0) or 0); h=max(int(mm/max_mm*40),2)
            c_="#ef9a9a" if mm>20 else ("#ffcc80" if mm>10 else "#a5d6a7" if mm>1 else "#f5f5f5")
            d_=row["date"].strftime("%d/%m")
            html+=f"<div title='{d_}: {mm:.1f}mm pronóst.' style='width:5px;height:{h}px;background:{c_};border-radius:2px 2px 0 0;border:1px dashed #b0bec5;flex-shrink:0'></div>"
        html+="</div><div class='rain-legend'><span>← 14d reales</span><span style='color:#1a237e;font-weight:700'>│hoy</span><span>pronóstico 14d →</span></div>"
        ll7_r=df_hist.tail(7)["lluvia_mm"].sum() if not df_hist.empty else 0
        ll7_f=df_fc.head(7)["lluvia_mm"].sum()   if not df_fc.empty  else 0
        return html, ll7_r, ll7_f
    except: return "", 0, 0

lluvia_data=[]; rain_rows_html=""
for key,nombre,pct,path in ZONAS_LLUVIA:
    bars_html,ll7_r,ll7_f=render_rain_bars(key,path)
    lluvia_data.append({"zona":nombre,"pct":pct,"ll7_real":ll7_r,"ll7_fc":ll7_f,"bars":bars_html})
    if ll7_r>40:   dc,nv="c-r","Alta ⚠"
    elif ll7_r>15: dc,nv="c-y","Media"
    else:          dc,nv="c-g","Baja ✓"
    fc_note=f"pronóst. 7d: {ll7_f:.0f}mm" if ll7_f>0 else "—"
    rain_rows_html+=(f"<tr><td>{nombre.split(',')[0]}</td><td style='color:#546e7a'>{pct}%</td>"
                     f"<td class='{dc}' style='font-weight:800'>{ll7_r:.1f}</td>"
                     f"<td class='{dc}'>{nv}</td><td style='color:#546e7a'>{fc_note}</td></tr>")

avg_ll=sum(z["ll7_real"] for z in lluvia_data)/len(lluvia_data) if lluvia_data else 0
avg_fc=sum(z["ll7_fc"]   for z in lluvia_data)/len(lluvia_data) if lluvia_data else 0
if avg_ll>40:   ll_cls,ll_msg="c-r","Lluvia intensa → en 5-10d MENOS fruta → precio puede SUBIR"
elif avg_ll>15: ll_cls,ll_msg="c-y","Lluvia moderada → posible reducción de oferta en 5-10 días"
else:           ll_cls,ll_msg="c-g","Sin lluvia — corte normal — oferta estable"
fc_alert=""
if avg_fc>20:
    fc_alert=f"<div style='margin-top:6px;font-size:12px;color:#b71c1c;font-weight:700'>⚠ Pronóstico: {avg_fc:.0f}mm en próx. 7d → posible impacto en oferta</div>"
mtt_bars=next((z["bars"] for z in lluvia_data if "Martínez" in z["zona"]),"")

with c1:
    st.markdown(
        f"<div class='sig'><div class='sig-lbl'>🌧 Lluvia zonas productoras</div>"
        f"<div class='sig-val {ll_cls}'>{avg_ll:.1f} mm/7d</div>"
        f"<div class='sig-desc'>{ll_msg}</div>{mtt_bars}"
        f"<div style='font-size:11px;color:#37474f;font-weight:600;margin:4px 0 2px'>MTT (54%) — sólido=real · punteado=pronóstico</div>"
        f"<table class='mt'><tr><th>Zona</th><th>%</th><th>mm/7d</th><th>Nivel</th><th>Pronóst. 7d</th></tr>"
        f"{rain_rows_html}</table>{fc_alert}</div>",
        unsafe_allow_html=True)

def get_movement_weekly():
    if move_df.empty: return pd.DataFrame()
    ms=move_df.sort_values("date").copy()
    ms["week_start"]=ms["date"].dt.to_period("W").dt.start_time
    weekly=ms.groupby("week_start").agg(
        pharr_total=("pharr_seedless_lb","sum"), mx_total=("mx_seedless_lb","sum"),
        total=("total_seedless_lb","sum"), dias=("date","count"), fecha_fin=("date","max"),
    ).reset_index()
    weekly["camiones"]=(weekly["pharr_total"]/40000).round(0).astype(int)
    weekly["pharr_m"] =(weekly["pharr_total"]/1e6).round(2)
    weekly=weekly.sort_values("week_start",ascending=False).reset_index(drop=True)
    weekly["chg_pct"]=(weekly["pharr_total"].pct_change(-1)*100).round(1)
    return weekly

weekly=get_movement_weekly()
ph_val="—"; ph_cls="c-b"; ph_msg="Sin datos (USDA ~10d retraso)"; move_rows_html=""
if not weekly.empty:
    last_w=weekly.iloc[0]; ph_val=f"{last_w['pharr_m']:.1f}M lbs"; chg=last_w["chg_pct"]
    if   pd.notna(chg) and chg>20:  ph_cls,ph_msg="c-r",f"↑{chg:.0f}% más → más oferta → precio puede BAJAR"
    elif pd.notna(chg) and chg>5:   ph_cls,ph_msg="c-y",f"↑{chg:.0f}% más → ligera presión bajista"
    elif pd.notna(chg) and chg<-20: ph_cls,ph_msg="c-g",f"↓{abs(chg):.0f}% menos → menos oferta → precio puede SUBIR"
    elif pd.notna(chg) and chg<-5:  ph_cls,ph_msg="c-y",f"↓{abs(chg):.0f}% menos → ligera presión alcista"
    else: ph_cls,ph_msg="c-b","Oferta similar a semana anterior"
    for _,w in weekly.head(4).iterrows():
        fi=pd.to_datetime(w["week_start"]).strftime("%d %b"); ff=pd.to_datetime(w["fecha_fin"]).strftime("%d %b")
        chg_s=""
        if pd.notna(w["chg_pct"]):
            c_chg="c-r" if w["chg_pct"]>10 else ("c-g" if w["chg_pct"]<-10 else "c-m")
            chg_s=f"<span class='{c_chg}'>{w['chg_pct']:+.0f}%</span>"
        move_rows_html+=(f"<tr><td style='white-space:nowrap'>{fi}–{ff}</td>"
                         f"<td style='font-weight:800;color:#1a237e'>{w['pharr_m']:.1f}M</td>"
                         f"<td style='color:#546e7a'>~{w['camiones']}</td><td>{chg_s}</td></tr>")

with c2:
    st.markdown(
        f"<div class='sig'><div class='sig-lbl'>🚛 Entrada Pharr/McAllen — por semana</div>"
        f"<div class='sig-val {ph_cls}'>{ph_val}</div><div class='sig-desc'>{ph_msg}</div>"
        f"<table class='mt'><tr><th>Semana</th><th>lbs total</th><th>Camiones</th><th>vs ant.</th></tr>"
        f"{move_rows_html}</table>"
        f"<div style='font-size:11px;color:#90a4ae;margin-top:6px'>~40k lbs/camión. USDA publica con ~10 días de retraso.</div>"
        f"</div>", unsafe_allow_html=True)

mtt=mtt_est(); fx_val="—"; fx_cls="c-b"; fx_msg=""; mtt_html=""; fx_date_s="—"
if not fx_df.empty:
    lf=fx_df.sort_values("date").iloc[-1]
    usdmxn=float(lf["usd_mxn"]); chg7=float(lf.get("usd_mxn_chg_7d",0) or 0)
    fx_date_s=pd.to_datetime(lf["date"]).strftime("%d %b"); fx_val=f"{usdmxn:.4f}"
    if   chg7>0.5:  fx_cls,fx_msg="c-r",f"Peso débil ({chg7:+.2f}) → exportación ↑ → presión bajista"
    elif chg7<-0.5: fx_cls,fx_msg="c-g",f"Peso fuerte ({chg7:+.2f}) → exportación ↓ → menos oferta"
    else:            fx_cls,fx_msg="c-b",f"Estable ({chg7:+.4f} en 7d) — sin presión adicional"
    if mtt:
        mtt_html=(f"<div class='divider'></div><div class='sig-lbl'>🏭 MTT → McAllen est. ({mtt['fecha']})</div>"
                  f"<div style='font-size:16px;font-weight:800;color:#e65100;margin:3px 0'>${mtt['lo']:.1f} — ${mtt['hi']:.1f} USD/caja</div>"
                  f"<div class='sig-desc'>Piso de precio — si el mercado cae aquí, productores dejan de exportar</div>")

with c3:
    st.markdown(
        f"<div class='sig'><div class='sig-lbl'>💱 USD/MXN al {fx_date_s}</div>"
        f"<div class='sig-val {fx_cls}'>{fx_val}</div>"
        f"<div class='sig-desc'>{fx_msg}</div>{mtt_html}</div>",
        unsafe_allow_html=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6 — MERCADOS TERMINALES (igual que V14)
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN NUEVA — INDICADORES ADELANTADOS (SNIIM + Temperatura destinos)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class=\'sec\'>📊 Indicadores adelantados</div>", unsafe_allow_html=True)
c_sniim, c_destw = st.columns(2)

with c_sniim:
    st.markdown("<div class='sig'><div class='sig-lbl'>🏭 Precio báscula MTT (entrada manual)</div>", unsafe_allow_html=True)

    # Mostrar último precio registrado
    tcp_last = None
    if not tcp_df.empty and "precio_mxn_kg" in tcp_df.columns:
        tcp_sorted = tcp_df.sort_values("date")
        last_tcp   = tcp_sorted.iloc[-1]
        tcp_last   = float(last_tcp["precio_mxn_kg"])
        usdmxn_now = float(fx_df.sort_values("date").iloc[-1]["usd_mxn"]) if not fx_df.empty else 17.5
        tcp_usd    = (tcp_last * 18.14) / usdmxn_now
        prev_tcp   = tcp_sorted.iloc[-2]["precio_mxn_kg"] if len(tcp_sorted)>1 else None
        chg_t = ""
        t_cls = "c-b"
        if prev_tcp is not None:
            try:
                delta = tcp_last - float(prev_tcp)
                chg_t = f"({delta:+.2f} MXN/kg)"
                t_cls = "c-g" if delta>0 else "c-r" if delta<0 else "c-b"
            except: pass
        # Señal: si precio TCP sube, exportar es menos atractivo para productor
        if tcp_last > 20: sig,sc2 = "Precio báscula alto → productor prefiere MX → menos exportación","c-r"
        elif tcp_last > 14: sig,sc2 = "Precio moderado → exportación y mercado MX equilibrados","c-b"
        else: sig,sc2 = "Precio bajo → exportación más atractiva → más oferta en McAllen","c-g"
        # Historial últimas 5 entradas
        rows_t = ""
        for _,r in tcp_sorted.tail(5).iloc[::-1].iterrows():
            try:
                d = str(r["date"])[:10]; p = float(r["precio_mxn_kg"])
                cal = str(r.get("calibre","")) or "—"; nota = str(r.get("nota","")) or ""
                rows_t += f"<tr><td>{d}</td><td>${p:.2f}</td><td>{cal}</td><td style='color:#90a4ae;font-size:11px'>{nota[:20]}</td></tr>"
            except: pass
        st.markdown(
            f"<div class='sig-val {t_cls}'>${tcp_last:.2f} MXN/kg</div>"
            f"<div class='sig-desc'>${tcp_usd:.1f} USD/caja est. {chg_t}</div>"
            f"<div class='sig-desc {sc2}'>{sig}</div>"
            f"<table class='mt'><tr><th>Fecha</th><th>MXN/kg</th><th>Calibre</th><th>Nota</th></tr>{rows_t}</table>",
            unsafe_allow_html=True)
    else:
        st.markdown("<div class='sig-desc' style='color:#90a4ae'>Sin registros aún — ingresa el primer precio abajo</div>", unsafe_allow_html=True)

    # Formulario MTT — fecha, rango de precio, múltiples calibres
    st.markdown("<div style='border-top:1px solid #e0e0e0;margin:10px 0 8px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px;font-weight:700;color:#37474f;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>+ Registrar precio báscula MTT</div>", unsafe_allow_html=True)

    # Fila 1: fecha y nota
    col_fecha, col_nota = st.columns([1,2])
    with col_fecha:
        import datetime as _dt
        nueva_fecha = st.date_input("Fecha", value=date.today(), key="mtt_fecha")
    with col_nota:
        nueva_nota = st.text_input("Nota", key="mtt_nota", placeholder="ej: semana 14, post lluvia")

    # Fila 2: calibres a registrar (múltiple selección)
    calibres_sel = st.multiselect(
        "Calibres a registrar",
        options=["110","150","175","200","230","250"],
        default=["230","250"],
        key="mtt_calibres"
    )

    # Fila 3: precio por calibre seleccionado (mín y máx)
    mtt_precios = {}
    if calibres_sel:
        st.markdown("<div style='font-size:11px;color:#546e7a;margin:4px 0 6px'>Precio por calibre (MXN/kg)</div>", unsafe_allow_html=True)
        n_cols = min(len(calibres_sel), 3)
        cal_cols = st.columns(n_cols)
        for i, cal in enumerate(calibres_sel):
            with cal_cols[i % n_cols]:
                st.markdown(f"<div style='font-size:11px;font-weight:700;color:#1a237e;margin-bottom:2px'>Cal {cal}</div>", unsafe_allow_html=True)
                p_min = st.number_input(f"Mín", min_value=1.0, max_value=80.0, value=18.0, step=0.5, key=f"mtt_min_{cal}")
                p_max = st.number_input(f"Máx", min_value=1.0, max_value=80.0, value=22.0, step=0.5, key=f"mtt_max_{cal}")
                mtt_precios[cal] = {"min": p_min, "max": p_max, "frec": round((p_min + p_max) / 2, 2)}

    if st.button("💾 Guardar precios MTT", key="btn_mtt", type="primary"):
        if not calibres_sel:
            st.warning("Selecciona al menos un calibre")
        else:
            import csv
            fieldnames = ["date","calibre","precio_min_kg","precio_max_kg","precio_mxn_kg","nota"]
            tcp_existe = TCP_PRICE_PATH.exists()
            with open(TCP_PRICE_PATH, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                if not tcp_existe: w.writeheader()
                for cal, precios in mtt_precios.items():
                    w.writerow({
                        "date":           nueva_fecha.isoformat(),
                        "calibre":        cal,
                        "precio_min_kg":  precios["min"],
                        "precio_max_kg":  precios["max"],
                        "precio_mxn_kg":  precios["frec"],
                        "nota":           nueva_nota,
                    })
            resumen = " | ".join([f"Cal {c}: ${v['min']:.1f}-${v['max']:.1f}" for c,v in mtt_precios.items()])
            st.success(f"✓ Guardado {nueva_fecha} — {resumen}")
            st.cache_data.clear(); st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with c_destw:
    destw_inner = ""
    if not destw_df.empty:
        try:
            fw = destw_df[destw_df["tipo"]=="forecast"].copy()
            fw["date"] = pd.to_datetime(fw["date"])
            next7 = fw[fw["date"] <= pd.Timestamp.today() + timedelta(days=7)]
            if not next7.empty:
                avg_by_city = next7.groupby("city")["temp_max"].mean()
                hottest = avg_by_city.idxmax(); hottest_t = avg_by_city.max()
                if hottest_t>=30:   d_msg,d_cls = f"🔥 {hottest} alcanzará {hottest_t:.0f}°C — demanda ↑↑","c-g"
                elif hottest_t>=22: d_msg,d_cls = f"☀️ Temperaturas moderadas — demanda normal","c-b"
                else:               d_msg,d_cls = f"❄️ Frío en destinos — demanda puede bajar","c-r"
                rows_w = ""
                for city in ["Chicago","Atlanta","New York","Los Angeles","Houston"]:
                    cd = next7[next7["city"]==city]
                    if not cd.empty:
                        avg_t = cd["temp_max"].mean()
                        em = "🔥" if avg_t>=30 else ("☀️" if avg_t>=22 else "❄️")
                        rows_w += f"<tr><td>{city}</td><td>{avg_t:.0f}°C</td><td>{em}</td></tr>"
                destw_inner = (f"<div class=\'sig-val {d_cls}\'>{hottest_t:.0f}°C</div>"
                               f"<div class=\'sig-desc\'>{d_msg}</div>"
                               f"<table class=\'mt\'><tr><th>Ciudad</th><th>Máx 7d avg</th><th></th></tr>{rows_w}</table>")
        except Exception as e:
            destw_inner = f"<div class=\'sig-desc\'>Error: {e}</div>"
    if not destw_inner:
        destw_inner = "<div class=\'sig-desc\'>Sin datos - corre fetch_dest_weather.py</div>"
    st.markdown(f"<div class=\'sig\'><div class=\'sig-lbl\'>🌡️ Temperatura ciudades destino (próx. 7d)</div>{destw_inner}</div>", unsafe_allow_html=True)

st.markdown("---")

st.markdown("<div class='sec'>🏪 Comparación de mercados terminales</div>", unsafe_allow_html=True)
st.caption("Precio terminal − FOB McAllen − flete estimado = margen neto/caja. Verde = conviene. Rojo = no conviene.")

mcallen_prices={}
if not price_df.empty:
    base=price_df[price_df["quality"]=="BASE"].sort_values("date")
    for size in [175,200,230,250]:
        s=base[base["size"]==size]
        if not s.empty: mcallen_prices[size]=float(s.iloc[-1]["official_price"])

mkt_data=[]
for fname,cfg in FLETES.items():
    fpath=DATA/fname
    if not fpath.exists(): continue
    try:
        df_t=pd.read_csv(fpath); df_t["date"]=pd.to_datetime(df_t["date"],errors="coerce")
        last_date=df_t["date"].max(); days_ago=(pd.Timestamp.today().normalize()-last_date).days
        df_last=df_t[df_t["date"]==last_date]
        for size in [175,200,230,250]:
            s_rows=df_last[df_last["size"]==size]
            if s_rows.empty: continue
            tp=float(s_rows["official_price"].mean()); mc=mcallen_prices.get(size)
            if not mc: continue
            fl=cfg["flete"]; mg=tp-mc-fl; tone=str(s_rows.iloc[0].get("market_tone","") or "")
            mkt_data.append({"mercado":cfg["label"],"size":size,"terminal":tp,
                              "mcallen":mc,"flete":fl,"margen":mg,"tone":tone,"days_ago":days_ago})
    except: continue

if mkt_data:
    df_mkt=pd.DataFrame(mkt_data)
    for size in [200,175,230,250]:
        sd=df_mkt[df_mkt["size"]==size].sort_values("margen",ascending=False)
        if sd.empty: continue
        mp=mcallen_prices.get(size,0)
        st.markdown(
            f"<div style='font-size:13px;font-weight:700;color:#37474f;margin:12px 0 5px'>"
            f"Calibre {size} — McAllen FOB: <span style='color:#1a237e'>${mp:.2f}</span></div>",
            unsafe_allow_html=True)
        rows_html=""
        for _,r in sd.iterrows():
            m=r["margen"]
            if   m>5:  mc2,mi="#1b5e20","▲ Excelente"
            elif m>2:  mc2,mi="#2e7d32","▲ Bueno"
            elif m>0:  mc2,mi="#e65100","━ Marginal"
            elif m>-3: mc2,mi="#c62828","▼ Riesgo"
            else:       mc2,mi="#b71c1c","▼ No conviene"
            bg="#f1f8e9" if m>2 else ("#fff8e1" if m>0 else "#ffebee")
            days_txt="hoy" if r["days_ago"]<=1 else f"hace {r['days_ago']}d"
            tone_s=r["tone"][:40] if r["tone"] and r["tone"]!="nan" else ""
            rows_html+=(f"<tr style='background:{bg}'>"
                        f"<td style='font-weight:700;color:#1a237e;font-size:13px'>{r['mercado']}</td>"
                        f"<td style='color:#37474f;font-size:13px'>${r['terminal']:.2f}</td>"
                        f"<td style='color:#546e7a;font-size:13px'>−${r['flete']:.2f}</td>"
                        f"<td style='font-weight:800;color:{mc2};font-size:13px'>{m:+.2f}</td>"
                        f"<td style='color:{mc2};font-weight:700;font-size:13px'>{mi}</td>"
                        f"<td style='color:#90a4ae;font-size:11px'>{tone_s}</td>"
                        f"<td style='color:#b0bec5;font-size:11px'>{days_txt}</td></tr>")
        st.markdown(
            "<div style='background:#fff;border-radius:10px;border:1px solid #dde1ea;"
            "overflow:hidden;margin-bottom:8px'>"
            "<table class='mt' style='width:100%'>"
            "<tr><th>Mercado</th><th>Precio terminal</th><th>Flete/caja</th>"
            "<th>Margen neto</th><th>Señal</th><th>Tono USDA</th><th>Dato</th></tr>"
            +rows_html+"</table></div>",
            unsafe_allow_html=True)
    st.caption("Flete est. McAllen→destino (base 1,080 cajas/camión). No incluye comisión broker ni manejo en destino.")
else:
    st.info("No se encontraron archivos terminal_*.csv · Corre: python update_prices.py --terminals")
