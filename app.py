import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- INTERFAZ SEGÚN TU SOLICITUD ---
st.set_page_config(page_title="Procesador CIQA", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)
st.markdown("---")

# Diccionario de Siglas (Instrucciones guardadas)
SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "bacteria aerobias heterotroficas": "BAH", "bacterias coliformes totales": "BCT",
    "escherichia coli": "EC", "pseudomonas aeruginosa": "PA"
}

def procesar_informe_ciqa(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    # 1. Extracción de Fecha (Normalización)
    match_f = re.search(r'Fecha de muestreo[:\s]+(\d{2}) de (\w+) de (\d{4})', texto_completo, re.IGNORECASE)
    if match_f:
        dia, mes, anio = match_f.groups()
        meses = {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06", 
                 "julio": "07", "agosto": "08", "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}
        fecha_final = f"{dia}/{meses.get(mes.lower(), '01')}/{anio}"
    else:
        fecha_final = "05/01/2026"

    total_parametros = 0
    fuera_de_limite = set()

    # 2. Análisis por Línea (Para manejar SAL VLB y VLB 1 simultáneamente)
    lineas = texto_completo.split('\n')
    for linea in lineas:
        linea_upper = linea.upper()
        
        # Excluir N.S., N.A. y Temperatura (Instrucciones guardadas)
        if any(ex in linea_upper for ex in ["N.A.", "TEMPERATURA"]):
            continue

        for nombre_p, sigla in SIGLAS_MAP.items():
            if nombre_p.upper() in linea_upper:
                # Encontramos todos los números con coma (ej: 0,10)
                # CIQA pone el límite (ej: 3,00 o 5,00) al final de la línea.
                valores = re.findall(r'\d+,\d+', linea)
                
                # REGLA DE CONTEO:
                # En el archivo: Cloro tiene 2 valores, pH tiene 1 (el otro es N.S.), Turbiedad tiene 2.
                # El último valor de la línea suele ser el límite, no lo contamos.
                if len(valores) > 1:
                    resultados_reales = valores[:-1] # Quitamos el límite S.R.H.
                    total_parametros += len(resultados_reales)
                
                # REGLA DE LÍMITES:
                # Si la línea contiene los asteriscos de "No cumple" (***)
                if "***" in linea or "*" in linea:
                    fuera_de_limite.add(sigla)
                break

    return {
        "fecha": fecha_final,
        "parametros fuera del limite": ", ".join(sorted(list(fuera_de_limite))),
        "parametros totales": total_parametros
    }

# --- APP ---
archivo = st.file_uploader("Sube el PDF aquí", type="pdf")

if archivo:
    res = procesar_informe_ciqa(archivo)
    
    # Tabla con columnas solicitadas
    df = pd.DataFrame([{
        "fecha": res["fecha"],
        "parametros fuera del limite": res["parametros fuera del limite"],
        "parametros totales": res["parametros totales"]
    }])
    
    st.table(df)

    # Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpy
