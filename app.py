import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Procesador CIQA Final", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)

# Diccionario de Siglas según instrucciones guardadas
SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "alcalinidad": "alcalinidad", "aluminio": "Al", "cloruros": "Cl", 
    "dureza total": "Dureza", "fluoruros": "F", "nitratos": "NA", 
    "sulfatos": "S", "hierro": "Fe", "solidos disueltos": "SDT",
    "orgánicos": "COV", "aerobias heterotróficas": "BAH", 
    "coliformes totales": "BCT", "escherichia coli": "EC", 
    "pseudomonas aeruginosa": "PA", "fitoplancton": "fito", 
    "zooplancton": "zoo", "microcistina": "MC"
}

def procesar_informe_definitivo(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = "\n".join([p.extract_text() or "" for p in pdf.pages])

    # 1. Extraer Fecha
    match_f = re.search(r'Fecha de muestreo[:\s]+(\d{2}) de (\w+) de (\d{4})', texto_completo, re.IGNORECASE)
    meses = {"enero":"01","febrero":"02","marzo":"03","abril":"04","mayo":"05","junio":"06",
             "julio":"07","agosto":"08","septiembre":"09","octubre":"10","noviembre":"11","diciembre":"12"}
    fecha = f"{match_f.group(1)}/{meses.get(match_f.group(2).lower(), '01')}/{match_f.group(3)}" if match_f else "05/01/2026"

    total_parametros = 0
    fuera_de_limite = set()
    bloques_procesados = set() # Para contar bloques como 1 solo

    lineas = texto_completo.split('\n')
    for linea in lineas:
        linea_low = linea.lower()
        
        # Excluir líneas vacías o de error de proceso
        if "error (%)" in linea_low or "metodología" in linea_low:
            continue

        for nombre_p, sigla in SIGLAS_MAP.items():
            if nombre_p in linea_low:
                # Regla para Bloques (Solo cuentan 1 vez aunque tengan muchas sustancias debajo)
                if sigla in ["COV", "fito", "zoo", "MC"]:
                    if sigla not in bloques_procesados:
                        total_parametros += 1
                        bloques_procesados.add(sigla)
                else:
                    # Parámetros individuales (Cloro, pH, etc.)
                    # Contamos si tiene una unidad o un valor "Ausencia/Presencia"
                    if any(u in linea for u in ["mg/L", "UpH", "UNT", "UFC", "NMP", "Ausencia"]):
                        total_parametros += 1
                
                # Detección de Falla (Asteriscos)
                if "*" in linea:
                    fuera_de_limite.add(sigla)
                break

    return {
        "fecha": fecha,
        "fuera": ", ".join(sorted(list(fuera_de_limite))),
        "total": total_parametros
    }

# --- INTERFAZ ---
archivo = st.file_uploader("Subir PDF", type="pdf")
if archivo:
    res = procesar_informe_definitivo(archivo)
    df = pd.DataFrame([{
        "fecha": res["fecha"], 
        "parametros fuera del limite": res["fuera"], 
        "parametros totales": res["total"]
    }])
    st.table(df)
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Descargar Reporte Excel", buf.getvalue(), "Reporte.xlsx")
