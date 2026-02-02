import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Procesador Universal CIQA", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)
st.markdown("---")

# Diccionario de Siglas según tus instrucciones guardadas
SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "turbidez": "Turbiedad", "bacteria aerobias heterotroficas": "BAH", 
    "bacterias coliformes totales": "BCT", "escherichia coli": "EC", 
    "pseudomonas aeruginosa": "PA", "fitoplancton": "fito", "zooplancton": "zoo",
    "compuestos orgánicos volátiles": "COV", "coliformes termotolerantes": "CF",
    "fósforo total": "P", "nitrógeno amoniacal": "NA", "sulfatos": "S",
    "dqo": "DQO", "dbo5": "DBO", "color": "color", "trihalometanos": "THM"
}

def procesar_laboratorio_final(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    # 1. Extracción de Fecha (Formato: 05 de enero de 2026 -> 05/01/2026)
    match_f = re.search(r'Fecha de muestreo[:\s]+(\d{2}) de (\w+) de (\d{4})', texto_completo, re.IGNORECASE)
    if match_f:
        dia, mes, anio = match_f.groups()
        meses = {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06", 
                 "julio": "07", "agosto": "08", "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}
        fecha_final = f"{dia}/{meses.get(mes.lower(), '01')}/{anio}"
    else:
        fecha_final = "No encontrada"

    total_parametros = 0
    fuera_de_limite = set()

    # 2. Análisis inteligente por línea
    lineas = texto_completo.split('\n')
    for linea in lineas:
        linea_up = linea.upper()
        
        # Exclusiones (Regla: Temperatura, N.A., N.S.)
        if any(ex in linea_up for ex in ["TEMPERATURA", "N.A."]):
            continue

        for nombre_p, sigla in SIGLAS_MAP.items():
            if nombre_p.upper() in linea_up:
                # Paso A: Detectar incumplimiento por asteriscos
                if "*" in linea:
                    fuera_de_limite.add(sigla)
                
                # Paso B: Contar parámetros (Solo los resultados antes de la unidad)
                # Buscamos todos los números (ej: 0,10 o 7,35)
                # También incluimos "N.S." para saber qué columnas ignorar
                partes = linea.split()
                
                # Buscamos dónde está la unidad (mg/L, UNT, pH, etc.)
                unidades = ["mg/L", "UNT", "uC/cm", "pH", "U.N.T.", "U.H.", "abs/m"]
                idx_unidad = -1
                for i, p in enumerate(partes):
                    if any(un in p for un in unidades):
                        idx_unidad = i
                        break
                
                if idx_unidad != -1:
                    # Los resultados están ENTRE el nombre del parámetro y la unidad
                    # Analizamos las palabras que hay en ese medio
                    for j in range(1, idx_unidad):
                        valor_potencial = partes[j]
                        # Si es un número (tiene dígitos) y NO es "N.S." ni "N.A."
                        if any(char.isdigit() for char in valor_potencial) and "N.S." not in valor_potencial:
                            total_parametros += 1
                break

    return {
        "fecha": fecha_final,
        "parametros fuera del limite": ", ".join(sorted(list(fuera_de_limite))),
        "parametros totales": total_parametros
    }

# --- APP STREAMLIT ---
archivo = st.file_uploader("Sube tu informe PDF aquí", type="pdf")

if archivo:
    with st.spinner("Analizando datos..."):
        res = procesar_laboratorio_final(archivo)
        
        # Estructura de tabla exacta solicitada
        df = pd.DataFrame([{
            "fecha": res["fecha"],
            "parametros fuera del limite": res["parametros fuera del limite"],
            "parametros totales": res["parametros totales"]
        }])
        
        st.markdown("### Previsualización")
        st.table(df)

        # Generar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Generar Archivo Excel",
            data=output.getvalue(),
            file_name=f"Reporte_{res['fecha'].replace('/','-')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
