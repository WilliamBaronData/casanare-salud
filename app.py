"""
╔══════════════════════════════════════════════════════════════════════╗
║  GOBERNACIÓN DE CASANARE — Vigilancia Epidemiológica Dengue          ║
║  Seguimiento a casos  - Secretaría de Salud                          ║
║                                                                      ║
║  Formatos : XLS · XLSX · XLSM · ODS · CSV · TSV                      ║
║  Estructura: SIVIGILA departamental (PARA CRUZAR) o formulario IEC   ║
║  Paleta   : epidemiológica OPS/OMS                                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import io, os, subprocess, tempfile, unicodedata
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────
# 1. CONSTANTES DE COLOR — paleta epidemiológica OPS/OMS
# ─────────────────────────────────────────────────────────────────────
BG       = "#0a0f1e"
PANEL    = "#060c1a"
TEXTO    = "#c8d8e8"
TEXTO2   = "#4a6a8a"
AZUL     = "#00b4d8"
VERDE    = "#2ecc71"   # sin signos de alarma
AMARILLO = "#f4d03f"   # con signos de alarma
NARANJA  = "#e67e22"   # grave
ROJO     = "#e74c3c"   # mortalidad / crítico

ANO_HOY = date.today().year

# ─────────────────────────────────────────────────────────────────────
# 2. COLUMNAS SIVIGILA — nombres reales del archivo departamental
#    Formato: PARA_CRUZAR_DEP_SE_XX_DE_YYYY_NNN.xlsx / .csv
# ─────────────────────────────────────────────────────────────────────
# Mapeo campo_lógico → nombre_columna_real
COLS_SIVIGILA = {
    "semana":      "semana",
    "municipio":   "nmun_proce",
    "depto":       "ndep_proce",
    "edad":        "edad_",
    "unidad_edad": "uni_med_",
    "sexo":        "sexo_",
    "barrio":      "bar_ver_",
    "lat":         "lat_dir",
    "lon":         "long_dir",
    "aseguradora": "cod_ase_",
    "tipo_caso":   "tip_cas_",
    "hospitalizado":"pac_hos_",
    "cond_final":  "con_fin_",
    "ajuste":      "ajuste_",
    "clasif":      "clasfinal",
    "conducta":    "conducta",
    "fec_muestra": "fec_exa_muestra_prueba_valor_1_pos",
}

# Palabras clave alternativas para detección automática en otros formatos
KEYWORDS = {
    "semana":      ["semana", "sem_ini", "semana_ini", "sem_not", "semana_epidemiologica",
                    "sem_", "epi", "week"],
    "municipio":   ["nmun_proce", "municipio", "muni_res", "nom_mun_res", "municipio_res",
                    "municipio_residencia", "localidad", "ciudad", "mpio"],
    "edad":        ["edad_", "edad", "age"],
    "unidad_edad": ["uni_med_", "unid_med", "uni_med", "unidad"],
    "sexo":        ["sexo_", "sexo", "genero", "gender", "sex"],
    "lat":         ["lat_dir", "lat", "latitud", "latitude"],
    "lon":         ["long_dir", "lon", "longitud", "longitude", "lng"],
    "tipo_caso":   ["tip_cas_", "tipo_cas", "tip_cas", "tipo_caso"],
    "hospitalizado":["pac_hos_", "pac_hos", "hospitalizado"],
    "cond_final":  ["con_fin_", "cond_final", "condicion_final"],
    "ajuste":      ["ajuste_", "ajuste"],
    "clasif":      ["clasfinal", "clasificacion_final", "clasf", "clasificacion"],
    "conducta":    ["conducta", "tipo_atencion", "atencion"],
    "aseguradora": ["cod_ase_", "aseguradora", "eps", "ase"],
    "fec_muestra": ["fec_exa_muestra_prueba_valor_1_pos", "fec_muestra", "fecha_muestra"],
}

# Coordenadas de los 19 municipios de Casanare (fallback sin GPS)
COORDS = {
    "yopal":                (5.3378, -72.3959),
    "aguazul":              (5.1731, -72.5517),
    "chameza":              (5.1025, -72.9006),
    "hato corozal":         (6.1500, -71.7667),
    "la salina":            (6.0333, -72.3167),
    "mani":                 (4.8167, -72.2833),
    "monterrey":            (4.8944, -72.8958),
    "nunchia":              (5.6500, -72.2000),
    "orocue":               (4.7906, -71.3364),
    "paz de ariporo":       (5.8833, -71.9000),
    "pore":                 (5.7167, -71.9833),
    "recetor":              (5.0333, -73.0333),
    "sabanalarga":          (4.8500, -72.5167),
    "sacama":               (6.0000, -72.2000),
    "san luis de palenque": (5.3833, -71.7667),
    "tamara":               (5.8333, -72.1667),
    "tauramena":            (5.0122, -72.7436),
    "trinidad":             (5.4167, -71.6667),
    "villanueva":           (4.6167, -72.9333),
}

# Decodificadores de campos numéricos
CLASIF_LABEL  = {1: "Sin signos de alarma", 2: "Con signos de alarma"}
CLASIF_COLOR  = {1: VERDE, 2: AMARILLO}
TIPO_CASO_LBL = {2: "Probable", 3: "Confirmado", 5: "Nexo epidemiológico"}
CONDUCTA_LBL  = {1: "Ambulatorio", 2: "Hospitalización", 3: "UCI",
                 4: "Observación", 5: "Remisión"}
AJUSTE_LBL    = {0: "Ninguno", 3: "Confirmado lab.", 5: "Nexo epidem.",
                 6: "Descartado lab.", 7: "Otra variable", "D": "Error digitación"}
COND_FINAL_LBL= {1: "Vivo", 2: "Muerto"}

# ─────────────────────────────────────────────────────────────────────
# 3. CONFIGURACIÓN STREAMLIT
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"Gobernación de Casanare · Vigilancia Dengue {ANO_HOY}",
    layout="wide",
    page_icon="🏛️",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
html,body,[class*="css"],.stApp,.stApp>header,.stApp>div,
section.main,.main,.block-container,
div[data-testid="stAppViewContainer"],
div[data-testid="stAppViewBlockContainer"]{
    background-color:#0a0f1e !important;color:#c8d8e8 !important;
}
.block-container{padding-top:1.5rem !important;max-width:100% !important;}
[data-testid="stSidebar"],[data-testid="stSidebar"]>div,
section[data-testid="stSidebar"]{
    background-color:#060c1a !important;
    border-right:1px solid rgba(0,180,216,0.15) !important;
}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stMarkdown{color:#c8d8e8 !important;}
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#00b4d8 !important;}
div[data-testid="metric-container"]{
    background:#060c1a !important;
    border:1px solid rgba(0,180,216,0.25) !important;
    border-radius:8px !important;padding:12px 14px !important;
}
div[data-testid="metric-container"] label,
div[data-testid="metric-container"] [data-testid="stMetricLabel"],
div[data-testid="metric-container"]>div:first-child{
    color:#4a6a8a !important;font-size:0.7rem !important;
    text-transform:uppercase !important;letter-spacing:0.06em !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"],
div[data-testid="metric-container"]>div:nth-child(2){
    color:#00b4d8 !important;font-weight:700 !important;
    font-size:clamp(1.3rem,2.5vw,2rem) !important;
}
h1,h2,h3{color:#00b4d8 !important;}
hr{border-color:rgba(0,180,216,0.25) !important;}
[data-testid="stExpander"]{
    background:#060c1a !important;
    border:1px solid rgba(0,180,216,0.2) !important;border-radius:8px !important;
}
[data-testid="stToggle"] label{color:#c8d8e8 !important;}
.stPlotlyChart,.stPlotlyChart>div{background:transparent !important;}
@media(max-width:768px){
    .block-container{padding:0.5rem !important;}
    div[data-testid="column"]{width:100% !important;flex:none !important;}
    div[data-testid="metric-container"]>div:nth-child(2){font-size:1.4rem !important;}
}
</style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# 4. FUNCIONES AUXILIARES
# ─────────────────────────────────────────────────────────────────────

def sin_tildes(txt):
    return "".join(
        c for c in unicodedata.normalize("NFD", str(txt).lower())
        if unicodedata.category(c) != "Mn"
    )


def detectar_col(df_cols, campo):
    """Busca la columna real para un campo lógico."""
    # Prioridad 1: nombre exacto SIVIGILA
    exacto = COLS_SIVIGILA.get(campo)
    if exacto and exacto in df_cols:
        return exacto
    # Prioridad 2: búsqueda por keyword
    cols_norm = {sin_tildes(c): c for c in df_cols}
    for kw in KEYWORDS.get(campo, []):
        for cn, co in cols_norm.items():
            if sin_tildes(kw) in cn:
                return co
    return None


def detectar_columnas(df_cols):
    return {campo: detectar_col(df_cols, campo)
            for campo in list(COLS_SIVIGILA.keys()) + list(KEYWORDS.keys())}


def convertir_office(file_bytes, suffix):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes); tp = tmp.name
    od = tempfile.mkdtemp()
    try:
        subprocess.run(["libreoffice","--headless","--convert-to","xlsx",
                        "--outdir", od, tp],
                       capture_output=True, timeout=120)
        out = os.path.join(od, os.path.splitext(os.path.basename(tp))[0] + ".xlsx")
        return out if os.path.exists(out) else None
    except Exception:
        return None
    finally:
        try: os.unlink(tp)
        except: pass


@st.cache_data(show_spinner="Procesando archivo…")
def cargar_datos(file_bytes, filename):
    name = filename.lower()
    buf  = io.BytesIO(file_bytes)
    df   = None
    try:
        if name.endswith((".csv", ".tsv")):
            sep = "\t" if name.endswith(".tsv") else None
            for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
                try:
                    buf.seek(0)
                    df = pd.read_csv(buf, encoding=enc, sep=sep,
                                     engine="python", on_bad_lines="skip")
                    if len(df.columns) > 1: break
                    df = None
                except Exception: continue
        elif name.endswith((".xlsx", ".xlsm")):
            xf  = pd.ExcelFile(buf, engine="openpyxl")
            dfs = {s: pd.read_excel(xf, sheet_name=s) for s in xf.sheet_names}
            df  = max(dfs.values(), key=len)
        elif name.endswith(".xls"):
            xlsx = convertir_office(file_bytes, ".xls")
            if xlsx:
                xf  = pd.ExcelFile(xlsx, engine="openpyxl")
                dfs = {s: pd.read_excel(xf, sheet_name=s) for s in xf.sheet_names}
                df  = max(dfs.values(), key=len)
            else:
                df = pd.read_excel(buf, engine="xlrd")
        elif name.endswith(".ods"):
            xlsx = convertir_office(file_bytes, ".ods")
            df = pd.read_excel(xlsx if xlsx else buf,
                               engine="openpyxl" if xlsx else "odf")
        else:
            return None, None, f"Formato no soportado: {filename}"

        if df is None or df.empty:
            return None, None, "El archivo está vacío."

        df = df.dropna(how="all").dropna(axis=1, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        cols = detectar_columnas(df.columns.tolist())

        # Municipio → Title Case
        mc = cols.get("municipio")
        if mc and mc in df.columns:
            df[mc] = (df[mc].fillna("").astype(str).str.strip().str.title()
                      .str.replace(r"\bDe\b", "de", regex=True)
                      .str.replace(r"\bEl\b", "el", regex=True)
                      .str.replace(r"\bLa\b", "la", regex=True)
                      .str.replace(r"\bDel\b", "del", regex=True))

        # Coordenadas — lat ÷ 100000, lon ÷ 10000 si están escaladas
        lc, nc = cols.get("lat"), cols.get("lon")
        if lc and lc in df.columns and nc and nc in df.columns:
            df[lc] = pd.to_numeric(df[lc], errors="coerce")
            df[nc] = pd.to_numeric(df[nc], errors="coerce")
            # Corregir fila a fila: si abs(lat) > 90 → escala ×100000
            mask_lat = df[lc].abs() > 90
            df.loc[mask_lat, lc] = df.loc[mask_lat, lc] / 100_000
            # lon: si abs > 180 → escala ×10000
            mask_lon = df[nc].abs() > 180
            df.loc[mask_lon, nc] = df.loc[mask_lon, nc] / 10_000
            # Filtrar coordenadas fuera de Colombia (lat 1-8, lon -67 a -77)
            df.loc[(df[lc] < 1) | (df[lc] > 8), lc] = np.nan
            df.loc[(df[nc] > -67) | (df[nc] < -77), nc] = np.nan

        # Semana → numérico
        sc = cols.get("semana")
        if sc and sc in df.columns:
            df[sc] = pd.to_numeric(df[sc], errors="coerce")

        # Edad → numérico
        ec = cols.get("edad")
        if ec and ec in df.columns:
            df[ec] = pd.to_numeric(df[ec], errors="coerce")

        # Decodificar clasfinal → etiqueta texto (para gráficas)
        clf = cols.get("clasif")
        if clf and clf in df.columns:
            df["_clasif_label"] = df[clf].map(CLASIF_LABEL).fillna("Sin clasificar")

        return df, cols, None
    except Exception as e:
        return None, None, str(e)


def coords_muni(nombre):
    return COORDS.get(sin_tildes(nombre), (None, None))


def color_clasif(label):
    m = {"Sin signos de alarma": VERDE, "Con signos de alarma": AMARILLO,
         "Sin clasificar": AZUL}
    return m.get(label, AZUL)


def color_intensidad(casos, max_c):
    if max_c == 0: return VERDE
    r = casos / max_c
    if r < 0.10: return VERDE
    if r < 0.30: return AMARILLO
    if r < 0.65: return NARANJA
    return ROJO


def layout_plotly(height=None):
    cfg = dict(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXTO, size=11),
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(bgcolor="rgba(6,12,26,0.9)",
                    bordercolor="rgba(0,180,216,0.33)",
                    borderwidth=1,
                    font=dict(color=TEXTO, size=10)),
    )
    if height: cfg["height"] = height
    return cfg


def seccion(icono, titulo):
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;margin:8px 0 4px'>"
        f"<span style='font-size:16px'>{icono}</span>"
        f"<span style='font-size:1.1rem;font-weight:600;color:#00b4d8'>{titulo}</span>"
        f"<div style='flex:1;height:1px;background:rgba(0,180,216,0.2);margin-left:6px'></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def nivel_alerta(df, cols):
    clf = cols.get("clasif")
    if clf and clf in df.columns and "_clasif_label" in df.columns:
        n_csa  = (df["_clasif_label"] == "Con signos de alarma").sum()
        n_tot  = len(df)
        pct    = n_csa / n_tot if n_tot > 0 else 0
        muertos = 0
        cof = cols.get("cond_final")
        if cof and cof in df.columns:
            muertos = (df[cof] == 2).sum()
        if muertos > 0:       return "Alerta Crítica", "🔴", ROJO
        if pct > 0.40:        return "Alerta Alta",    "🟠", NARANJA
        if pct > 0.20:        return "Monitoreo",      "🟡", AMARILLO
        return                       "Normal",          "🟢", VERDE
    return "Sin datos", "⚪", TEXTO2


# ─────────────────────────────────────────────────────────────────────
# 5. LOGO EMBEBIDO (base64 — funciona sin internet)
# ─────────────────────────────────────────────────────────────────────
_LOGO_B64 = "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"

_BANDERA = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 60" width="90" height="60" '
    'style="border-radius:4px;flex-shrink:0;box-shadow:0 2px 6px rgba(0,0,0,0.5)">'
    '<polygon points="0,0 90,0 90,60" fill="#CC0000"/>'
    '<polygon points="0,0 0,60 90,60" fill="#1B7A2E"/>'
    '<polygon points="45.0,18.0 47.3,24.46 53.49,21.51 50.54,27.7 57.0,30.0 50.54,32.3 53.49,38.49 47.3,35.54 45.0,42.0 42.7,35.54 36.51,38.49 39.46,32.3 33.0,30.0 39.46,27.7 36.51,21.51 42.7,24.46" fill="#F5C400"/>'
    '</svg>'
)

_LOGO_IMG = (
    '<img src="data:image/jpeg;base64,' + _LOGO_B64 +
    '" height="70" style="object-fit:contain;background:#fff;'
    'border-radius:6px;padding:4px 8px;flex-shrink:0">'
)

def _render_header(subtitulo=""):
    html = (
        '<div style="display:flex;align-items:center;gap:16px;padding:4px 0 14px 0;' 
        'border-bottom:1px solid rgba(0,180,216,0.15);margin-bottom:12px">' 
        + _BANDERA + _LOGO_IMG +
        '<div style="flex:1">' 
        '<div style="font-size:clamp(1.1rem,2.5vw,1.6rem);font-weight:700;' 
        'color:#00b4d8;margin-bottom:5px">Gobernación de Casanare</div>' 
        f'<div style="font-size:0.85rem;color:#4a6a8a">{subtitulo}</div>' 
        '</div>' 
        '<div style="display:flex;align-items:center;gap:6px;flex-shrink:0">' 
        '<div style="width:8px;height:8px;border-radius:50%;background:#2ecc71"></div>' 
        '<span style="font-size:10px;color:#2ecc71;font-weight:500">Sistema activo</span>' 
        '</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# 6. CABECERA Y SIDEBAR
# ─────────────────────────────────────────────────────────────────────
subtitulo_ph = st.empty()
_render_header(f"Secretaría de Salud · Vigilancia Epidemiológica · {ANO_HOY}")
st.divider()

with st.sidebar:
    st.markdown("## Panel de control")

    uploaded = st.file_uploader(
        "Cargar archivo de datos",
        type=["xlsx", "xlsm", "xls", "ods", "csv", "tsv"],
        help="SIVIGILA departamental (PARA CRUZAR) o formulario IEC · XLS · XLSX · CSV",
    )

    if not uploaded:
        st.info("Carga el archivo para iniciar la exposición.")
        st.stop()

    file_bytes = uploaded.read()
    df_raw, cols, error = cargar_datos(file_bytes, uploaded.name)

    if error or df_raw is None:
        st.error(f"Error al leer el archivo:\n{error}")
        st.stop()

    st.success(f"{len(df_raw):,} registros · {len(df_raw.columns)} columnas")

    # ── Detectar año desde semana o fecha ────────────────────────
    fec_c = cols.get("fec_muestra")
    if fec_c and fec_c in df_raw.columns:
        try:
            años = df_raw[fec_c].dropna().astype(str).str.extract(r"(\d{4})")[0]
            ano_arch = int(años.mode()[0]) if not años.dropna().empty else ANO_HOY
        except Exception:
            ano_arch = ANO_HOY
    else:
        ano_arch = ANO_HOY

    sc = cols.get("semana")
    if sc and sc in df_raw.columns:
        svals     = df_raw[sc].dropna()
        sem_min_v = int(svals.min()) if not svals.empty else 1
        sem_max_v = int(svals.max()) if not svals.empty else 1
        sem_str   = f"SE {sem_min_v}–{sem_max_v}"
    else:
        sem_min_v = sem_max_v = None
        sem_str   = "Semanas N/D"

    # Actualizar cabecera con datos reales
    _render_header(
        f"Secretaría de Salud &nbsp;·&nbsp; Vigilancia Epidemiológica &nbsp;·&nbsp;"
        f"<b style='color:#00b4d8'>Dengue</b> &nbsp;·&nbsp;"
        f"<b style='color:#00b4d8'>{sem_str} · {ano_arch}</b>"
    )

    # ── FILTROS ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Filtros")

    mc  = cols.get("municipio")
    clf = cols.get("clasif")
    lc  = cols.get("lat")
    nc  = cols.get("lon")
    ac  = cols.get("area") or cols.get("aseguradora")

    munis_sel = []
    if mc and mc in df_raw.columns:
        munis_sel = st.multiselect(
            "Municipio",
            sorted(df_raw[mc].replace("", pd.NA).dropna().unique()),
            default=[], placeholder="Todos",
        )

    clasif_sel = []
    if "_clasif_label" in df_raw.columns:
        clasif_sel = st.multiselect(
            "Clasificación",
            sorted(df_raw["_clasif_label"].dropna().unique()),
            default=[], placeholder="Todas",
        )

    sem_rango = None
    if sc and sc in df_raw.columns and sem_min_v is not None:
        sem_rango = st.slider("Semanas", sem_min_v, sem_max_v, (sem_min_v, sem_max_v))

    st.markdown("---")
    st.markdown("### Modo de conexión")
    modo_offline = st.toggle(
        "Modo sin internet",
        value=False,
        help="Activa si no hay wifi. El mapa satelital requiere internet; "
             "los demás gráficos funcionan igual.",
    )
    if modo_offline:
        st.info("Mapa desactivado — todos los gráficos funcionan sin internet.")

    # ── Diagnóstico de columnas ───────────────────────────────────
    with st.expander("🔍 Columnas detectadas"):
        campos_es = {
            "semana": "Semana epidem.", "municipio": "Municipio",
            "clasif": "Clasificación", "edad": "Edad", "sexo": "Sexo",
            "tipo_caso": "Tipo de caso", "hospitalizado": "Hospitalizado",
            "cond_final": "Condición final", "conducta": "Conducta",
            "lat": "Latitud GPS", "lon": "Longitud GPS",
        }
        for campo, label in campos_es.items():
            col_real = cols.get(campo)
            color = "#2ecc71" if col_real else "#e74c3c"
            icono = "✓" if col_real else "✗"
            val   = f"<code style='font-size:10px'>{col_real}</code>" if col_real else "no detectado"
            st.markdown(
                f"<div style='font-size:11px;margin:2px 0'>"
                f"<span style='color:{color}'>{icono}</span> "
                f"<span style='color:#4a6a8a'>{label}:</span> {val}</div>",
                unsafe_allow_html=True,
            )
    st.caption(f"`{uploaded.name}`")

# ─────────────────────────────────────────────────────────────────────
# 7. FILTRAR DATOS
# ─────────────────────────────────────────────────────────────────────
df = df_raw.copy()
if munis_sel and mc and mc in df.columns:
    df = df[df[mc].isin(munis_sel)]
if clasif_sel and "_clasif_label" in df.columns:
    df = df[df["_clasif_label"].isin(clasif_sel)]
if sem_rango and sc and sc in df.columns:
    df = df[df[sc].between(sem_rango[0], sem_rango[1])]

if df.empty:
    st.warning("Sin registros con los filtros actuales.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────
# 8. MÉTRICAS PRINCIPALES
# ─────────────────────────────────────────────────────────────────────
alerta_txt, alerta_emoji, _ = nivel_alerta(df, cols)

n_ssa  = (df["_clasif_label"] == "Sin signos de alarma").sum() if "_clasif_label" in df.columns else 0
n_csa  = (df["_clasif_label"] == "Con signos de alarma").sum() if "_clasif_label" in df.columns else 0
n_hosp = (df[cols["hospitalizado"]] == 1).sum() if cols.get("hospitalizado") and cols["hospitalizado"] in df.columns else 0
n_conf = (df[cols["tipo_caso"]] == 3).sum() if cols.get("tipo_caso") and cols["tipo_caso"] in df.columns else 0
n_muni = df[mc].replace("", pd.NA).dropna().nunique() if mc and mc in df.columns else 0

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Total casos",            f"{len(df):,}")
c2.metric("Sin signos alarma",      f"{n_ssa:,}")
c3.metric("Con signos alarma",      f"{n_csa:,}")
c4.metric("Hospitalizados",         f"{n_hosp:,}")
c5.metric("Confirmados lab.",       f"{n_conf:,}")
c6.metric(f"{alerta_emoji} Alerta", alerta_txt)

st.divider()

# ─────────────────────────────────────────────────────────────────────
# 9. MAPA + BARRAS MUNICIPIO
# ─────────────────────────────────────────────────────────────────────
col_map, col_bar = st.columns([3, 2])

with col_map:
    seccion("📍", "Georreferenciación de casos")

    if modo_offline:
        # Tabla de municipios con nivel de alerta
        if mc and mc in df.columns:
            tbl = df[mc].replace("", pd.NA).dropna().value_counts().reset_index()
            tbl.columns = ["Municipio", "Casos"]
            max_c_tbl = tbl["Casos"].max()
            def _alerta_m(x):
                r = x / max_c_tbl if max_c_tbl > 0 else 0
                if r >= 0.65: return "🔴 Crítico"
                if r >= 0.30: return "🟠 Alerta"
                if r >= 0.10: return "🟡 Monitoreo"
                return "🟢 Normal"
            tbl["Alerta"]    = tbl["Casos"].apply(_alerta_m)
            tbl["% del total"] = (tbl["Casos"]/tbl["Casos"].sum()*100).round(1).astype(str)+"%"
            st.dataframe(tbl[["Municipio","Casos","% del total","Alerta"]],
                         use_container_width=True, hide_index=True, height=390)
    elif lc and lc in df.columns and nc and nc in df.columns:
        keep = [c for c in [mc, "_clasif_label", lc, nc] if c and c in df.columns]
        df_geo = df[keep].dropna(subset=[lc, nc]).copy()

        # Fallback centroide para registros sin GPS
        if mc and mc in df.columns:
            rng    = np.random.default_rng(42)
            df_sin = df[df[lc].isna()].copy()
            if not df_sin.empty:
                ctrs = df_sin.groupby(mc).size().reset_index(name="n")
                ctrs["lf"] = ctrs[mc].apply(lambda m: coords_muni(m)[0])
                ctrs["nf"] = ctrs[mc].apply(lambda m: coords_muni(m)[1])
                ctrs = ctrs.dropna(subset=["lf","nf"])
                filas = []
                for _, r in ctrs.iterrows():
                    for _ in range(int(r["n"])):
                        filas.append({
                            lc: r["lf"] + rng.uniform(-0.012,0.012),
                            nc: r["nf"] + rng.uniform(-0.012,0.012),
                            mc: r[mc],
                            "_clasif_label": "Sin coordenada exacta",
                        })
                if filas:
                    df_geo = pd.concat([df_geo, pd.DataFrame(filas)], ignore_index=True)

        if not df_geo.empty and "_clasif_label" in df_geo.columns:
            cmap = {l: color_clasif(l) for l in df_geo["_clasif_label"].dropna().unique()}
            fig_map = px.scatter_mapbox(
                df_geo, lat=lc, lon=nc, color="_clasif_label",
                color_discrete_map=cmap,
                hover_name=mc if mc else None,
                hover_data={"_clasif_label": True, lc: False, nc: False},
                labels={"_clasif_label": "Clasificación"},
                zoom=7, mapbox_style="carto-darkmatter", opacity=0.85,
            )
            fig_map.update_traces(marker_size=6)
            fig_map.update_layout(**layout_plotly(height=420),
                                  mapbox=dict(zoom=7, center=dict(lat=5.3, lon=-72.4)))
            st.plotly_chart(fig_map, use_container_width=True,
                            config=dict(scrollZoom=True, displayModeBar=True,
                                        modeBarButtonsToRemove=["toImage"],
                                        displaylogo=False))
        elif not df_geo.empty:
            fig_map = px.scatter_mapbox(df_geo, lat=lc, lon=nc,
                                        zoom=7, mapbox_style="carto-darkmatter")
            fig_map.update_layout(**layout_plotly(height=420))
            st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("Sin coordenadas GPS en este archivo.")

with col_bar:
    seccion("📊", "Casos por municipio")
    if mc and mc in df.columns:
        mc_df = df[mc].replace("",pd.NA).dropna().value_counts().reset_index()
        mc_df.columns = ["Municipio","Casos"]
        max_c = mc_df["Casos"].max()
        mc_df["Color"] = mc_df["Casos"].apply(lambda x: color_intensidad(x, max_c))
        fig_bar = go.Figure(go.Bar(
            x=mc_df["Casos"], y=mc_df["Municipio"], orientation="h",
            marker_color=mc_df["Color"],
            hovertemplate="%{y}: %{x:,} casos<extra></extra>",
        ))
        fig_bar.update_layout(**layout_plotly(height=420),
                              yaxis=dict(categoryorder="total ascending", tickfont=dict(size=10)))
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown(
            f"<div style='display:flex;gap:14px;font-size:11px;color:{TEXTO2};flex-wrap:wrap'>"
            f"<span><b style='color:{VERDE}'>■</b> Normal</span>"
            f"<span><b style='color:{AMARILLO}'>■</b> Monitoreo</span>"
            f"<span><b style='color:{NARANJA}'>■</b> Alerta</span>"
            f"<span><b style='color:{ROJO}'>■</b> Crítico</span></div>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# 10. CURVA EPIDÉMICA
# ─────────────────────────────────────────────────────────────────────
seccion("📈", "Curva epidémica semanal")

if sc and sc in df.columns and "_clasif_label" in df.columns:
    cv = (df.groupby([sc, "_clasif_label"]).size()
          .reset_index(name="Casos").sort_values(sc))
    cv["Semana"] = cv[sc].astype(int).apply(lambda x: f"SE {x}")
    cmap_cv = {l: color_clasif(l) for l in cv["_clasif_label"].unique()}
    fig_cv = px.area(cv, x="Semana", y="Casos", color="_clasif_label",
                     color_discrete_map=cmap_cv,
                     labels={"Semana":"Semana epidemiológica",
                             "_clasif_label":"Clasificación"})
    fig_cv.update_traces(line_width=1.5)
    fig_cv.update_layout(**layout_plotly(height=260))
    st.plotly_chart(fig_cv, use_container_width=True)
elif sc and sc in df.columns:
    cv = df.groupby(sc).size().reset_index(name="Casos").sort_values(sc)
    cv["Semana"] = cv[sc].astype(int).apply(lambda x: f"SE {x}")
    fig_cv = px.area(cv, x="Semana", y="Casos", color_discrete_sequence=[AZUL])
    fig_cv.update_layout(**layout_plotly(height=260))
    st.plotly_chart(fig_cv, use_container_width=True)
else:
    st.info("No se detectó columna de semana epidemiológica.")

# ─────────────────────────────────────────────────────────────────────
# 11. DISTRIBUCIONES: EDAD · SEXO · TIPO DE CASO
# ─────────────────────────────────────────────────────────────────────
col_e, col_s, col_tc = st.columns(3)

with col_e:
    seccion("👥", "Grupos de edad")
    ec = cols.get("edad")
    uc = cols.get("unidad_edad")
    if ec and ec in df.columns:
        # Convertir todo a años
        df_edad = df[[ec]].copy()
        if uc and uc in df.columns:
            df_edad["_ed_años"] = df_edad[ec].copy()
            mask_m = df[uc] == 2  # meses
            mask_d = df[uc] == 3  # días
            df_edad.loc[mask_m, "_ed_años"] = df_edad.loc[mask_m, ec] / 12
            df_edad.loc[mask_d, "_ed_años"] = df_edad.loc[mask_d, ec] / 365
        else:
            df_edad["_ed_años"] = df_edad[ec]

        bins = [0,4,9,14,19,25,40,59,120]
        labs = ["0-4","5-9","10-14","15-19","20-25","26-40","41-59","60+"]
        ge   = pd.cut(df_edad["_ed_años"].dropna(), bins=bins, labels=labs)
        df_e = ge.value_counts().sort_index().reset_index()
        df_e.columns = ["Grupo","Casos"]
        mx = df_e["Casos"].max()
        df_e["Color"] = df_e["Casos"].apply(lambda x: color_intensidad(x, mx))
        fig_e = go.Figure(go.Bar(x=df_e["Grupo"], y=df_e["Casos"],
                                 marker_color=df_e["Color"],
                                 hovertemplate="%{x}: %{y:,}<extra></extra>"))
        fig_e.update_layout(**layout_plotly(height=240))
        st.plotly_chart(fig_e, use_container_width=True)
    else:
        st.info("Sin columna de edad.")

with col_s:
    seccion("⚥", "Sexo / género")
    sxc = cols.get("sexo")
    if sxc and sxc in df.columns:
        sd = df[sxc].dropna().value_counts().reset_index()
        sd.columns = ["Sexo","Casos"]
        fig_s = px.pie(sd, names="Sexo", values="Casos", hole=0.45,
                       color_discrete_sequence=[AZUL, VERDE, AMARILLO])
        fig_s.update_layout(**layout_plotly(height=240))
        st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("Sin columna de sexo.")

with col_tc:
    seccion("🔬", "Tipo de caso")
    tc = cols.get("tipo_caso")
    if tc and tc in df.columns:
        td = df[tc].map(TIPO_CASO_LBL).fillna("Otro").value_counts().reset_index()
        td.columns = ["Tipo","Casos"]
        td["Color"] = td["Tipo"].map(
            {"Probable": AMARILLO, "Confirmado": VERDE, "Nexo epidemiológico": AZUL})
        fig_tc = go.Figure(go.Bar(x=td["Casos"], y=td["Tipo"], orientation="h",
                                  marker_color=td["Color"],
                                  hovertemplate="%{y}: %{x:,}<extra></extra>"))
        fig_tc.update_layout(**layout_plotly(height=240),
                             yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig_tc, use_container_width=True)
    else:
        st.info("Sin columna de tipo de caso.")

# ─────────────────────────────────────────────────────────────────────
# 12. HOSPITALIZACION + CONDUCTA + CONDICIÓN FINAL
# ─────────────────────────────────────────────────────────────────────
st.divider()
col_h, col_cd, col_cf = st.columns(3)

with col_h:
    seccion("🏥", "Hospitalización")
    hc = cols.get("hospitalizado")
    if hc and hc in df.columns:
        hd = df[hc].map({1:"Hospitalizado", 2:"No hospitalizado"}).fillna("N/D")
        hd = hd.value_counts().reset_index()
        hd.columns = ["Estado","Casos"]
        hd["Color"] = hd["Estado"].map({"Hospitalizado": NARANJA, "No hospitalizado": VERDE})
        fig_h = px.pie(hd, names="Estado", values="Casos", hole=0.45,
                       color="Estado", color_discrete_map={"Hospitalizado": NARANJA,
                                                            "No hospitalizado": VERDE,
                                                            "N/D": TEXTO2})
        fig_h.update_layout(**layout_plotly(height=220))
        st.plotly_chart(fig_h, use_container_width=True)

with col_cd:
    seccion("💊", "Conducta / atención")
    cdc = cols.get("conducta")
    if cdc and cdc in df.columns:
        cdd = df[cdc].map(CONDUCTA_LBL).fillna("Otro").value_counts().reset_index()
        cdd.columns = ["Conducta","Casos"]
        fig_cd = go.Figure(go.Bar(
            x=cdd["Casos"], y=cdd["Conducta"], orientation="h",
            marker_color=AZUL,
            hovertemplate="%{y}: %{x:,}<extra></extra>"))
        fig_cd.update_layout(**layout_plotly(height=220),
                             yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig_cd, use_container_width=True)

with col_cf:
    seccion("📋", "Condición final")
    cfc = cols.get("cond_final")
    if cfc and cfc in df.columns:
        cfd = df[cfc].map(COND_FINAL_LBL).fillna("N/D").value_counts().reset_index()
        cfd.columns = ["Condición","Casos"]
        fig_cf = px.pie(cfd, names="Condición", values="Casos", hole=0.45,
                        color="Condición",
                        color_discrete_map={"Vivo": VERDE, "Muerto": ROJO, "N/D": TEXTO2})
        fig_cf.update_layout(**layout_plotly(height=220))
        st.plotly_chart(fig_cf, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────
# 13. TABLA DE DETALLE
# ─────────────────────────────────────────────────────────────────────
st.divider()
with st.expander("📋 Tabla de registros", expanded=False):
    campos_tbl = [
        ("Municipio",    cols.get("municipio")),
        ("Clasificación","_clasif_label"),
        ("Semana",       cols.get("semana")),
        ("Edad",         cols.get("edad")),
        ("Sexo",         cols.get("sexo")),
        ("Tipo caso",    cols.get("tipo_caso")),
        ("Hospitalizado",cols.get("hospitalizado")),
        ("Conducta",     cols.get("conducta")),
        ("Cond. final",  cols.get("cond_final")),
        ("Ajuste",       cols.get("ajuste")),
    ]
    ct = [(n, c) for n, c in campos_tbl if c and c in df.columns]
    if ct:
        df_t = df[[c for _, c in ct]].head(500).copy()
        df_t.columns = [n for n, _ in ct]
        # Decodificar columnas numéricas
        if "Tipo caso" in df_t.columns:
            df_t["Tipo caso"] = df_t["Tipo caso"].map(TIPO_CASO_LBL).fillna(df_t["Tipo caso"])
        if "Hospitalizado" in df_t.columns:
            df_t["Hospitalizado"] = df_t["Hospitalizado"].map({1:"Sí",2:"No"}).fillna("N/D")
        if "Conducta" in df_t.columns:
            df_t["Conducta"] = df_t["Conducta"].map(CONDUCTA_LBL).fillna(df_t["Conducta"])
        if "Cond. final" in df_t.columns:
            df_t["Cond. final"] = df_t["Cond. final"].map(COND_FINAL_LBL).fillna("N/D")
        if "Ajuste" in df_t.columns:
            df_t["Ajuste"] = df_t["Ajuste"].map(AJUSTE_LBL).fillna(df_t["Ajuste"])
        st.dataframe(df_t, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df.head(200), use_container_width=True)
    st.caption(f"Mostrando hasta 500 de {len(df):,} registros.")

# ─────────────────────────────────────────────────────────────────────
# 14. PIE DE PÁGINA
# ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<p style='font-size:11px;color:{TEXTO2};text-align:center'>"
    f"Gobernación de Casanare · Secretaría de Salud · {ano_arch}"
    f" &nbsp;|&nbsp; {uploaded.name}"
    f" &nbsp;|&nbsp; {len(df_raw):,} registros · {len(df):,} con filtros"
    f"</p>", unsafe_allow_html=True)
