import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Procesador CIQA", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)
st.markdown("---")

# Diccionario de Siglas (Basado en tus instrucciones)
SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "bacteria aerobias": "BAH", "coliformes totales": "BCT",
    "escherichia coli": "EC", "pseudomonas": "PA"
}

def procesar_informe_ciqa(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    # 1. Extracción de Fecha (Normalización de "05 de enero de 2026")
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

    # 2. Análisis por Línea para contar sitios (SAL VLB y VLB 1)
    lineas = texto_completo.split('\n')
    for linea in lineas:
        linea_upper = linea.upper()
        
        # Excluir N.A. y Temperatura
        if any(ex in linea_upper for ex in ["N.A.", "TEMPERATURA"]):
            continue

        for nombre_p, sigla in SIGLAS_MAP.items():
            if nombre_p.upper() in linea_upper:
                # Buscamos valores numéricos (ej: 0,10 o 7,35)
                valores = re.findall(r'\d+,\d+', linea)
                
                # En CIQA el último valor suele ser el límite fijo, no lo contamos
                if len(valores) > 1:
                    resultados_reales = valores[:-1] 
                    total_parametros += len(resultados_reales)
                
                # Si la línea contiene los asteriscos (***) de incumplimiento
                if "***" in linea:
                    fuera_de_limite.add(sigla)
                break

    return {
        "fecha": fecha_final,
        "parametros fuera del limite": ", ".join(sorted(list(fuera_de_limite))),
        "parametros totales": total_parametros
    }

# --- APP ---
archivo = st.file_uploader("Sube el PDF de CIQA aquí", type="pdf")

if archivo:
    res = procesar_informe_ciqa(archivo)
    
    df = pd.DataFrame([{
        "fecha": res["fecha"],
        "parametros fuera del limite": res["parametros fuera del limite"],
        "parametros totales": res["parametros totales"]
    }])
    
    st.table(df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 Generar Archivo Excel",
        data=output.getvalue(),
        file_name=f"Reporte_{res['fecha'].replace('/','-')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
