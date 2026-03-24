"""
generate_forecast.py V5
Fix: usa ultimo precio real aunque target_1d sea NaN
6 calibres: 110, 150, 175, 200, 230, 250
"""
from pathlib import Path
import math, warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, f1_score
warnings.filterwarnings("ignore")

INPUT_PATH  = Path("data/processed/model_base.csv")
OUTPUT_PATH = Path("data/processed/daily_forecast_base.csv")
SIZES            = [110, 150, 175, 200, 230, 250]
QUALITY          = "BASE"
CONFIDENCE_MIN   = 0.55

REG_FEATS = ["official_price","price_lag_1","price_lag_3","price_lag_7","ma_3","ma_7","price_change_1d","momentum_3d","momentum_7d","volatility_7d","price_position_14d","lluvia_14d_lag6","lluvia_7d_lag7","usd_mxn_lag4","import_lag2","pharr_sum7d","spike_230_lag14","spread_200_230","month_sin","month_cos","supply_season"]
CLF_FEATS = ["price_lag_1","price_lag_3","price_lag_7","ma_3","ma_7","price_change_1d","momentum_3d","momentum_7d","volatility_7d","price_position_14d","price_accel","cross_p175_lag1","cross_p230_lag1","cross_p250_lag1","spread_200_230","spread_chg_3d","spread_175_200","spike_230_lag14","spike_250_lag15","spike_230_lag10","spike_250_lag10","lluvia_14d_lag6","lluvia_7d_lag7","lluvia_3d_lag7","lluvia_lag9","usd_mxn_lag4","usd_mxn_chg_7d","import_lag2","import_zscore_lag2","pharr_sum7d","month_sin","month_cos","dow_sin","dow_cos","supply_season"]
R7_FEATS  = ["official_price","price_lag_1","price_lag_7","ma_7","momentum_7d","volatility_7d","lluvia_14d_lag6","lluvia_7d_lag7","spike_230_lag14","spike_250_lag15","usd_mxn_lag4","usd_mxn_chg_7d","import_lag2","pharr_sum7d","month_sin","month_cos","supply_season"]

def dir_es(d): return {"UP":"SUBE","DOWN":"BAJA","LATERAL":"ESTABLE"}.get(str(d),"ESTABLE")
def dyn_thr(vol):
    try: return round(max(0.20, min(float(vol)*0.5, 1.50)), 2)
    except: return 0.30
def avail(s, feats): seen=set(); return [f for f in feats if f in s.columns and not (f in seen or seen.add(f))]
def get_last(s, col):
    try: return round(float(s[col].dropna().iloc[-1]), 4)
    except: return ""

def fit_reg(s, target, feats):
    data = s.sort_values("date").reset_index(drop=True)
    train_data = data[feats+[target,"date"]].dropna().sort_values("date").reset_index(drop=True)
    if len(train_data) < 30: return None
    sp = max(1, int(len(train_data)*0.8))
    tr, te = train_data.iloc[:sp], train_data.iloc[sp:]
    m = LinearRegression().fit(tr[feats], tr[target])
    pred_te = m.predict(te[feats])
    mae = mean_absolute_error(te[target], pred_te)
    rmse = math.sqrt(mean_squared_error(te[target], pred_te))
    last = data[feats+["date"]].dropna().reset_index(drop=True).iloc[-1]
    pred = float(m.predict(np.array(last[feats].values, dtype=float).reshape(1,-1))[0])
    return {"pred":pred,"mae":float(mae),"rmse":float(rmse),"rows":int(len(train_data)),"last":last}

def fit_clf(s, target_dir, feats):
    if target_dir not in s.columns: return None
    data = s.sort_values("date").reset_index(drop=True)
    d = data[feats+[target_dir,"date"]].dropna().sort_values("date").reset_index(drop=True)
    if len(d)<50 or d[target_dir].nunique()<2: return None
    sp = max(1, int(len(d)*0.8))
    tr, te = d.iloc[:sp], d.iloc[sp:]
    clf = GradientBoostingClassifier(n_estimators=300,learning_rate=0.03,max_depth=4,min_samples_leaf=15,random_state=42)
    clf.fit(tr[feats], tr[target_dir])
    f1 = round(float(f1_score(te[target_dir],clf.predict(te[feats]),average="macro",zero_division=0)),4) if len(te)>=10 else None
    last = data[feats+["date"]].dropna().iloc[-1]
    proba = clf.predict_proba(pd.DataFrame([last[feats]]))[0]
    classes = clf.classes_
    pd_ = dict(zip(classes,proba))
    conf = float(proba.max())
    pred = classes[proba.argmax()] if conf>=CONFIDENCE_MIN else "LATERAL"
    return {"dir":pred,"conf":round(conf,4),"up":round(pd_.get("UP",0),4),"down":round(pd_.get("DOWN",0),4),"lat":round(pd_.get("LATERAL",0),4),"f1":f1}

def dir_thr(pred, last, thr):
    d = pred - last
    if d > thr: return "SUBE"
    if d < -thr: return "BAJA"
    return "ESTABLE"

def main():
    if not INPUT_PATH.exists(): raise SystemExit(f"No existe {INPUT_PATH}")
    print("Cargando model_base...")
    df = pd.read_csv(INPUT_PATH)
    df["date"] = pd.to_datetime(df["date"],errors="coerce")
    max_date = df["date"].max()
    days_old = (pd.Timestamp.today().normalize()-max_date).days
    print(f"{'OK' if days_old<=3 else 'AVISO'} Ultimo dato: {max_date.date()} ({days_old}d)")
    rows = []
    for size in SIZES:
        s = df[(df["size"]==size)&(df["quality"]==QUALITY)].sort_values("date").reset_index(drop=True)
        print(f"-- {size} BASE ({len(s)} filas)")
        if len(s)<30: continue
        rf = avail(s,REG_FEATS); cf = avail(s,CLF_FEATS); r7f = avail(s,R7_FEATS)
        r1=fit_reg(s,"target_1d",rf); r2=fit_reg(s,"target_2d",rf)
        r3=fit_reg(s,"target_3d",rf); r7=fit_reg(s,"target_7d",r7f)
        if r1 is None: continue
        lp = float(s["official_price"].dropna().iloc[-1])
        ld = s["date"].dropna().iloc[-1].strftime("%Y-%m-%d")
        vol = s["volatility_7d"].dropna().iloc[-1] if "volatility_7d" in s.columns and s["volatility_7d"].notna().any() else None
        t1=dyn_thr(vol); t2=round(t1*1.4,2); t3=round(t1*1.8,2); t7=round(t1*3.0,2)
        c1=fit_clf(s,"direction_target_1d",cf)
        c7=fit_clf(s,"direction_target_7d",cf) if "direction_target_7d" in s.columns else None
        print(f"  Precio ({ld}): ${lp:.2f}  1D:{dir_thr(r1['pred'],lp,t1)}  Clasif:{dir_es(c1['dir']) if c1 else 'N/A'} {c1['conf']:.0%}" if c1 else f"  Precio ({ld}): ${lp:.2f}  1D:{dir_thr(r1['pred'],lp,t1)}")
        rows.append({
            "run_datetime":pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "forecast_family":"BASE_MULTI_SIZE_V5","market":"US_MCALLEN",
            "size":int(size),"quality":QUALITY,"last_date":ld,
            "last_official_price":round(lp,4),
            "predicted_target_1d":round(r1["pred"],4),"direction_1d":dir_thr(r1["pred"],lp,t1),
            "mae_1d":round(r1["mae"],4),"rmse_1d":round(r1["rmse"],4),"rows_used_1d":r1["rows"],"threshold_1d":t1,
            "direction_clf_1d":c1["dir"] if c1 else "","direction_clf_1d_es":dir_es(c1["dir"]) if c1 else "",
            "confidence_clf_1d":c1["conf"] if c1 else "","prob_up_1d":c1["up"] if c1 else "",
            "prob_down_1d":c1["down"] if c1 else "","f1_macro_1d":c1["f1"] if c1 else "",
            "predicted_target_2d":round(r2["pred"],4) if r2 else "","direction_2d":dir_thr(r2["pred"],lp,t2) if r2 else "",
            "mae_2d":round(r2["mae"],4) if r2 else "",
            "predicted_target_3d":round(r3["pred"],4) if r3 else "","direction_3d":dir_thr(r3["pred"],lp,t3) if r3 else "",
            "mae_3d":round(r3["mae"],4) if r3 else "",
            "predicted_target_7d":round(r7["pred"],4) if r7 else "","direction_7d":dir_thr(r7["pred"],lp,t7) if r7 else "",
            "direction_clf_7d_es":dir_es(c7["dir"]) if c7 else "","confidence_clf_7d":c7["conf"] if c7 else "",
            "mae_7d":round(r7["mae"],4) if r7 else "",
            "lluvia_14d_lag6":get_last(s,"lluvia_14d_lag6"),"usd_mxn":get_last(s,"usd_mxn"),
            "spike_230_lag14":get_last(s,"spike_230_lag14"),"import_lag2":get_last(s,"import_lag2"),
        })
    out = pd.DataFrame(rows).sort_values("size").reset_index(drop=True)
    OUTPUT_PATH.parent.mkdir(parents=True,exist_ok=True)
    out.to_csv(OUTPUT_PATH,index=False)
    print("\n"+"="*60+"\nFORECAST V5\n"+"="*60)
    cols=["size","last_date","last_official_price","predicted_target_1d","direction_1d","direction_clf_1d_es","confidence_clf_1d","predicted_target_7d","direction_7d","mae_1d"]
    print(out[[c for c in cols if c in out.columns]].to_string(index=False))
    print(f"\nGuardado: {OUTPUT_PATH}")

if __name__=="__main__":
    main()
