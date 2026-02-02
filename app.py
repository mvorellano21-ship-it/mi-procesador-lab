import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Procesador CIQA", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes CIQA</h1>", unsafe_allow_html=True)

SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "turbidez": "Turbiedad", "bacteria aerobias": "BAH", "coliformes": "BCT",
    "escherichia coli": "EC", "pseudomonas": "PA"
}

def procesar_ciqa(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = "\n".join([p.extract_text() or "" for p in pdf.pages])
        
        # Fecha de Muestreo (Busca el formato exacto del informe)
        match_f = re.search(r'Fecha de muestreo[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
        fecha = match_f.group(1) if match_f else "No detectada"

        total_parametros = 0
        fuera_de_limite = set()
        
        # Secciones permitidas para contar parámetros
        secciones_validas = [
            "ENSAYOS REALIZADOS EN CAMPO", 
            "ANÁLISIS FISICOQUÍMICOS", 
            "ANÁLISIS BACTERIOLÓGICOS"
        ]

        for page in pdf.pages:
            tablas = page.extract_tables()
            texto_pag = page.extract_text() or ""
            
            # Solo procesar si la página pertenece a una sección de resultados
            if not any(s in texto_pag.upper() for s in secciones_validas):
                continue

            for tabla in tablas:
                for fila in tabla:
                    f = [str(c).strip() if c else "" for c in fila]
                    # Una fila de parámetro válida en CIQA suele tener 5+ columnas y una unidad (mg/L, UNT, etc)
                    if len(f) < 4 or f[0] == "" or "Parámetro" in f[0]:
                        continue
                    
                    # Exclusiones
                    if any(ex in f[0].upper() for ex in ["TEMPERATURA", "N.S.", "N.A."]):
                        continue

                    # Contamos el parámetro (SAL VLB y VLB 1 cuentan como sitios distintos si hay datos en ambos)
                    # En tu ejemplo hay 2 sitios con datos: SAL VLB y VLB 1
                    sitios_con_datos = 0
                    if f[1] and f[1] != "N.S.": sitios_con_datos += 1
                    if f[2] and f[2] != "N.S.": sitios_con_datos += 1
                    
                    total_parametros += sitios_con_datos
                    
                    # Detección de "Fuera de Límite" (CIQA usa *** para indicar error)
                    nombre_p = f[0].lower()
                    texto_fila = " ".join(f)
                    
                    if "***" in texto_fila:
                        for clave, sigla in SIGLAS_MAP.items():
                            if clave in nombre_p:
                                fuera_de_limite.add(sigla)
                                break
        
        return {
            "Fecha": fecha,
            "Parámetros fuera del límite": ", ".join(sorted(list(fuera_de_limite))),
            "Parámetros totales": total_parametros
        }

# --- INTERFAZ ---
archivo = st.file_uploader("Cargar PDF", type="pdf")
if archivo:
    res = procesar_ciqa(archivo)
    st.table(pd.DataFrame([res]))
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        pd.DataFrame([res]).to_excel(writer, index=False)
    st.download_button("Generar Excel", buf.getvalue(), "Reporte_CIQA.xlsx")
