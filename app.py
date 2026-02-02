import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="Procesador Lab Final", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)

# Diccionario completo de siglas (según tus instrucciones)
SIGLAS_MAP = {
    "cloro residual": "cloro", "ph": "pH", "turbiedad": "Turbiedad", 
    "turbidez": "Turbiedad", "aerobias heterotroficas": "BAH", "heterótrofas": "BAH",
    "coliformes totales": "BCT", "escherichia coli": "EC", "e. coli": "EC",
    "pseudomonas": "PA", "fitoplancton": "fito", "zooplancton": "zoo",
    "orgánicos volátiles": "COV", "termotolerantes": "CF", "fósforo total": "P",
    "nitrógeno amoniacal": "NA", "sulfatos": "S", "dqo": "DQO", "dbo5": "DBO",
    "color": "color", "trihalometanos": "THM"
}

def procesar_informe_maestro(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    # 1. Fecha de Muestreo (Normalización)
    match_f = re.search(r'Fecha de muestreo[:\s]+(\d{2}) de (\w+) de (\d{4})', texto_completo, re.IGNORECASE)
    meses = {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06", 
             "julio": "07", "agosto": "08", "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}
    fecha = f"{match_f.group(1)}/{meses.get(match_f.group(2).lower(), '01')}/{match_f.group(3)}" if match_f else "05/01/2026"

    total_parametros = 0
    fuera_de_limite = set()

    # 2. Análisis por líneas
    lineas = texto_completo.split('\n')
    for linea in lineas:
        linea_low = linea.lower()
        
        # Excluir N.A. y Temperatura
        if any(ex in linea.upper() for ex in ["N.A.", "TEMPERATURA"]):
            continue

        for nombre_p, sigla in SIGLAS_MAP.items():
            if nombre_p in linea_low:
                # Caso especial Fitoplancton/Zooplancton (se cuentan como 1)
                if sigla in ["fito", "zoo"]:
                    total_parametros += 1
                    if "*" in linea: fuera_de_limite.add(sigla)
                    break

                # Conteo de resultados numéricos
                # Buscamos números con coma que estén antes de las unidades
                valores = re.findall(r'(\d+,\d+|\d+\.\d+)', linea)
                
                if valores:
                    # En CIQA, el último valor es el límite. Lo quitamos.
                    resultados = valores[:-1]
                    
                    # Filtro para pH y Cloro (evitar contar incertidumbre o límites extra)
                    if sigla == "pH": 
                        total_parametros += 1 # El pH suele ser un solo punto de medición por sitio
                    elif sigla == "cloro":
                        # Solo contamos si no dice N.S.
                        if "n.s." not in linea_low:
                            # Si hay 2 sitios con datos, len(resultados) debería ser 2
                            total_parametros += len(resultados) if len(resultados) < 4 else 1
                    else:
                        total_parametros += len(resultados)

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
archivo = st.file_uploader("Subir Informe PDF", type="pdf")
if archivo:
    res = procesar_informe_maestro(archivo)
    df = pd.DataFrame([{
        "fecha": res["fecha"], 
        "parametros fuera del limite": res["fuera"], 
        "parametros totales": res["total"]
    }])
    st.table(df)
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Descargar Reporte Excel", buf.getvalue(), "Reporte_Final.xlsx")
