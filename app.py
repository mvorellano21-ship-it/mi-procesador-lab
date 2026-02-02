import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Procesador de Laboratorio", layout="centered")

st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)
st.markdown("---")

SIGLAS_MAP = {
    "bacteria aerobias heterotróficas": "BAH", "bacterias heterótrofas totales": "BH",
    "bacterias coliformes totales": "BCT", "escherichia coli": "EC",
    "pseudomonas aeruginosa": "PA", "fitoplancton": "fito", "zooplancton": "zoo",
    "compuestos orgánicos volátiles": "COV", "coliformes termotolerantes": "CF",
    "fósforo total": "P", "nitrógeno amoniacal": "NA", "sulfatos": "S",
    "dqo": "DQO", "dbo5": "DBO", "color": "color", "trihalometanos": "THM",
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad",
    "turbidez": "Turbiedad", "dureza total": "Dureza", "aluminio": "Al",
    "fluoruros": "F", "cloruros": "Cl", "arsénico": "As", "arsenico": "As"
}

def limpiar_valor(texto):
    if not texto: return None
    texto = str(texto).replace(',', '.')
    numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto)
    return float(numeros[0]) if numeros else None

def procesar_laboratorio(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() or ""
        
        match_fecha = re.search(r'Fecha de Muestreo[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
        fecha_muestreo = match_fecha.group(1) if match_fecha else "No detectada"

        total_parametros = 0
        fuera_de_limite = []
        
        for page in pdf.pages:
            tablas = page.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    f = [str(c).strip() if c else "" for c in fila]
                    if not f or len(f) < 3: continue
                    
                    nombre_p = f[0].lower()
                    if any(exc in nombre_p.upper() for exc in ["N.S.", "N.A.", "TEMPERATURA"]):
                        continue

                    if "fitoplancton" in nombre_p or "zooplancton" in nombre_p:
                        total_parametros += 1
                    else:
                        total_parametros += 1

                    res_num = limpiar_valor(f[-2])
                    lim_num = limpiar_valor(f[-1])

                    if res_num is not None and lim_num is not None:
                        if res_num > lim_num:
                            for clave, sigla in SIGLAS_MAP.items():
                                if clave in nombre_p:
                                    if sigla not in fuera_de_limite:
                                        fuera_de_limite.append(sigla)
                                    break
        
        return {"Fecha": fecha_muestreo, "Parámetros fuera del límite": ", ".join(fuera_de_limite), "Parámetros totales": total_parametros}

# --- INTERFAZ ---
archivo = st.file_uploader("Cargar PDF", type="pdf")
if archivo:
    res = procesar_laboratorio(archivo)
    df = pd.DataFrame([res])
    st.table(df)
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    st.download_button(label="Generar Excel", data=buf.getvalue(), file_name="Reporte.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
