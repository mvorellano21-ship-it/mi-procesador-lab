import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="Procesador CIQA Final", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)

# Diccionario de Siglas según tus instrucciones
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

def procesar_informe(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = "\n".join([p.extract_text() or "" for p in pdf.pages])

    # 1. Extraer Fecha (Normalización)
    match_f = re.search(r'Fecha de muestreo[:\s]+(\d{2}) de (\w+) de (\d{4})', texto_completo, re.IGNORECASE)
    meses = {"enero":"01","febrero":"02","marzo":"03","abril":"04","mayo":"05","junio":"06",
             "julio":"07","agosto":"08","septiembre":"09","octubre":"10","noviembre":"11","diciembre":"12"}
    fecha = f"{match_f.group(1)}/{meses.get(match_f.group(2).lower(), '01')}/{match_f.group(3)}" if match_f else "05/01/2026"

    total_parametros = 0
    fuera_de_limite = set()
    bloques_contados = set() # Para asegurar que COV, fito, zoo, MC solo sumen 1

    lineas = texto_completo.split('\n')
    for linea in lineas:
        l_low = linea.lower()
        
        # Saltamos líneas que son encabezados o metadatos
        if "unidad" in l_low or "límite s.r.h." in l_low or "error (%)" in l_low:
            continue

        for nombre_p, sigla in SIGLAS_MAP.items():
            if nombre_p in l_low:
                # REGLA PARA BLOQUES (COV, Plancton, Microcistinas)
                if sigla in ["COV", "fito", "zoo", "MC"]:
                    if sigla not in bloques_contados:
                        total_parametros += 1
                        bloques_contados.add(sigla)
                else:
                    # PARÁMETROS INDIVIDUALES
                    # Buscamos si hay un resultado real: números (que no sean el código de 10 dígitos) o "Ausencia"
                    tokens = linea.split()
                    tiene_resultado = False
                    for t in tokens:
                        # Ignorar códigos de 10 dígitos (ej: 7426010901)
                        if re.match(r'^\d{10}$', t):
                            continue
                        # Contar si es un número (con coma o punto) o texto de resultado
                        if re.search(r'\d+,\d+|\d+\.\d+', t) or "Ausencia" in t or "<" in t:
                            # Evitamos contar los límites conocidos del informe
                            if t not in ["3,00", "5,00", "400", "500", "45", "1500", "0,2", "1,7"]:
                                tiene_resultado = True
                                break
                    
                    if tiene_resultado:
                        total_parametros += 1
                
                # REGLA DE FALLA: Cualquier asterisco activa la sigla
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
    res = procesar_informe(archivo)
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
