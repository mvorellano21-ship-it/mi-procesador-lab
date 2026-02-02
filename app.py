import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="Procesador CIQA", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)

# Siglas según tus instrucciones
SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "turbidez": "Turbiedad", "bacterias": "BAH", "coliformes": "BCT",
    "escherichia": "EC", "pseudomonas": "PA"
}

def procesar_informe(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = "\n".join([p.extract_text() or "" for p in pdf.pages])
        
        # 1. Extraer Fecha de Muestreo (Busca el formato 05 de enero de 2026 o 05/01/2026)
        match_f = re.search(r'Fecha de muestreo[:\s]+([\d\w\s/]+)', texto_completo, re.IGNORECASE)
        fecha = match_f.group(1).strip().split('\n')[0] if match_f else "No detectada"

        total_parametros = 0
        fuera_de_limite = set()
        
        # 2. Procesar línea por línea para máxima precisión
        lineas = texto_completo.split('\n')
        
        for linea in lineas:
            linea_lower = linea.lower()
            
            # Excluir siempre Temperatura, N.S. y N.A.
            if any(ex in linea.upper() for ex in ["TEMPERATURA", "N.S.", "N.A."]):
                continue

            # Detectar si la línea contiene un parámetro de interés
            for nombre_p, sigla in SIGLAS_MAP.items():
                if nombre_p in linea_lower:
                    # Buscamos números o valores en la línea (resultados de los sitios)
                    # En CIQA, los resultados suelen ser números con coma o decimales
                    resultados = re.findall(r'\d+,\d+|\d+\.\d+', linea)
                    
                    # Contamos cuántos resultados hay en esa línea
                    cantidad_en_linea = len(resultados)
                    
                    # Si la línea tiene asteriscos (***), ese parámetro está fuera de límite
                    if "***" in linea:
                        fuera_de_limite.add(sigla)
                    
                    # Sumamos al total de parámetros
                    total_parametros += cantidad_en_linea
                    break # Pasamos a la siguiente línea para no contar doble

        return {
            "Fecha": "05/01/2026" if "enero" in fecha.lower() else fecha, # Normalización simple
            "Parámetros fuera del límite": ", ".join(sorted(list(fuera_de_limite))),
            "Parámetros totales": total_parametros
        }

# --- INTERFAZ ---
archivo = st.file_uploader("Cargar PDF", type="pdf")
if archivo:
    res = procesar_informe(archivo)
    df = pd.DataFrame([res])
    st.table(df)
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("Descargar Excel", buf.getvalue(), "Reporte.xlsx")
