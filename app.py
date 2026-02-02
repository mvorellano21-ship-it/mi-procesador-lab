import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Procesador CIQA - 5 Parámetros", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)

# Diccionario de Siglas según tus instrucciones
SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "turbidez": "Turbiedad", "bacteria aerobias": "BAH", "coliformes": "BCT",
    "escherichia coli": "EC", "pseudomonas": "PA"
}

def procesar_informe_ciqa(file):
    with pdfplumber.open(file) as pdf:
        # 1. Extraer Fecha (Página 1 o 2)
        texto_completo = "\n".join([p.extract_text() or "" for p in pdf.pages])
        match_f = re.search(r'Fecha de muestreo[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
        fecha = match_f.group(1) if match_f else "No detectada"

        total_parametros = 0
        fuera_de_limite = set()
        
        # 2. Procesar Tablas de Resultados
        for page in pdf.pages:
            tablas = page.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    # Limpiar y filtrar filas vacías o encabezados
                    f = [str(c).strip() if c else "" for c in fila]
                    if not f or len(f) < 4 or "Parámetro" in f[0]:
                        continue
                    
                    nombre_p = f[0].lower()
                    
                    # Regla de Exclusión (Temperatura, N.S., N.A.)
                    if any(ex in nombre_p.upper() for ex in ["TEMPERATURA", "N.S.", "N.A."]):
                        continue

                    # --- LÓGICA DE CONTEO (Crucial para que dé 5) ---
                    # Revisamos las columnas donde el laboratorio pone resultados (SAL VLB y VLB 1)
                    # En CIQA suelen ser la columna 1 y 2 después del nombre del parámetro
                    resultados_en_fila = f[1:3] # Toma las celdas de los dos sitios
                    
                    for r in resultados_en_fila:
                        # Si la celda tiene un resultado válido (no es N.S., ni está vacía)
                        if r and r.upper() != "N.S." and r.upper() != "N.A.":
                            total_parametros += 1
                            
                            # Detección de Fuera de Límite por asteriscos (***)
                            if "***" in r:
                                for clave, sigla in SIGLAS_MAP.items():
                                    if clave in nombre_p:
                                        fuera_de_limite.add(sigla)
                                        break
        
        return {
            "Fecha": fecha,
            "Parámetros fuera del límite": ", ".join(sorted(list(fuera_de_limite))),
            "Parámetros totales": total_parametros
        }

# --- INTERFAZ STREAMLIT ---
archivo = st.file_uploader("Cargar PDF de Laboratorio", type="pdf")

if archivo:
    with st.spinner("Procesando..."):
        res = procesar_informe_ciqa(archivo)
        df = pd.DataFrame([res])
        
        st.markdown("### Previsualización de Datos")
        st.table(df)
        
        # Botón de Descarga
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="🟢 Generar Archivo Excel",
            data=buf.getvalue(),
            file_name=f"Reporte_{res['Fecha'].replace('/','-')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
