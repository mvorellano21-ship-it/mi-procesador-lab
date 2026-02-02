import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Procesador Experto Lab", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)

# Diccionario de Siglas según instrucciones del usuario
SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "turbidez": "Turbiedad", "bacteria aerobias": "BAH", "coliformes": "BCT",
    "escherichia coli": "EC", "pseudomonas": "PA", "fitoplancton": "fito",
    "zooplancton": "zoo", "orgánicos volátiles": "COV", "termotolerantes": "CF",
    "fósforo total": "P", "nitrógeno amoniacal": "NA", "sulfatos": "S",
    "dqo": "DQO", "dbo5": "DBO", "color": "color", "trihalometanos": "THM"
}

def procesar_informe_matriz(file):
    with pdfplumber.open(file) as pdf:
        # 1. Extraer Fecha de Muestreo
        texto_completo = "\n".join([p.extract_text() or "" for p in pdf.pages])
        match_f = re.search(r'Fecha de muestreo[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
        fecha = match_f.group(1) if match_f else "No detectada"

        total_parametros = 0
        fuera_de_limite = set()
        
        # 2. Procesar Tablas
        for page in pdf.pages:
            tablas = page.extract_tables()
            for tabla in tablas:
                if not tabla or len(tabla) < 2: continue
                
                # Identificamos las columnas de los sitios (SAL VLB, VLB 1, etc.)
                # Buscamos la fila que contiene los nombres de las muestras
                idx_sitios = []
                for i, celda in enumerate(tabla[0]):
                    if celda and any(keyword in str(celda) for keyword in ["VLB", "SAL", "Muestra"]):
                        idx_sitios.append(i)
                
                # Si no encontramos sitios en la primera fila, probamos en las siguientes (por si hay celdas unidas)
                if not idx_sitios and len(tabla) > 2:
                    for i, celda in enumerate(tabla[1]):
                        if celda and any(keyword in str(celda) for keyword in ["VLB", "SAL"]):
                            idx_sitios.append(i)

                # 3. Recorrer las filas de parámetros
                for fila in tabla:
                    f = [str(c).strip() if c else "" for c in fila]
                    if not f or "Parámetro" in f[0] or "Unidad" in f[0]: continue
                    
                    nombre_p = f[0].lower()
                    
                    # Exclusiones (Temperatura, N.S., N.A.)
                    if any(ex in nombre_p.upper() for ex in ["TEMPERATURA", "N.S.", "N.A."]):
                        continue

                    # 4. Contar y Validar por cada sitio detectado
                    for idx in idx_sitios:
                        if idx < len(f):
                            valor = f[idx].upper()
                            
                            # Si hay un dato real (no es N.S. ni está vacío)
                            if valor and valor not in ["N.S.", "N.A.", "-"]:
                                total_parametros += 1
                                
                                # Detección de Fuera de Límite (Por asteriscos en la celda)
                                if "*" in valor:
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
archivo = st.file_uploader("Cargar PDF de Laboratorio (CIQA / Otros)", type="pdf")

if archivo:
    with st.spinner("Analizando matriz de datos..."):
        res = procesar_informe_matriz(archivo)
        df = pd.DataFrame([res])
        
        st.markdown("### Resultados Extraídos")
        st.table(df)
        
        # Exportación
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Descargar Excel",
            data=buf.getvalue(),
            file_name=f"Reporte_{res['Fecha'].replace('/','-')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
