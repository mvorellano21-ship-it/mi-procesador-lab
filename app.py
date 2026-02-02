import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="Procesador Experto Lab", layout="centered")
st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)

# Diccionario de Siglas
SIGLAS_MAP = {
    "aerobias heterotróficas": "BAH", "heterótrofas totales": "BH",
    "coliformes totales": "BCT", "escherichia coli": "EC",
    "pseudomonas aeruginosa": "PA", "fitoplancton": "fito", "zooplancton": "zoo",
    "orgánicos volátiles": "COV", "termotolerantes": "CF", "fósforo total": "P",
    "nitrógeno amoniacal": "NA", "sulfatos": "S", "dqo": "DQO", "dbo5": "DBO",
    "color": "color", "trihalometanos": "THM", "cloro residual": "cloro",
    "ph": "pH", "turbiedad": "Turbiedad", "turbidez": "Turbiedad",
    "dureza total": "Dureza", "aluminio": "Al", "fluoruros": "F",
    "cloruros": "Cl", "arsénico": "As", "arsenico": "As"
}

def limpiar_valor(texto):
    if not texto: return None
    texto = str(texto).replace(',', '.')
    if "ausencia" in texto.lower(): return 0.0
    if "presencia" in texto.lower(): return 1.0
    numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto)
    return float(numeros[0]) if numeros else None

def procesar_informe_detallado(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = "\n".join([p.extract_text() or "" for p in pdf.pages])
        
        # Fecha de Muestreo
        match_f = re.search(r'(?:Muestreo|Muestreo de fecha)[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
        fecha = match_f.group(1) if match_f else "No detectada"

        total_parametros = 0
        fuera_de_limite = set()
        excluir = ["N.S.", "N.A.", "TEMPERATURA"]

        for page in pdf.pages:
            tablas = page.extract_tables()
            for tabla in tablas:
                if not tabla: continue
                
                # Identificar índices de columnas por encabezado
                encabezado = [str(c).upper() for c in tabla[0] if c]
                idx_res = -2 # Por defecto penúltima
                idx_lim = -1 # Por defecto última
                
                for i, col in enumerate(encabezado):
                    if "RESULTADO" in col: idx_res = i
                    if "S.R.H" in col or "LÍMITE" in col: idx_lim = i

                for fila in tabla:
                    f = [str(c).strip() if c else "" for c in fila]
                    if not f or len(f) < 3 or any(ex in f[0].upper() for ex in excluir) or "PARÁMETRO" in f[0].upper():
                        continue
                    
                    nombre_p = f[0].lower()
                    val_res = limpiar_valor(f[idx_res])
                    val_lim = limpiar_valor(f[idx_lim])

                    # 1. Contabilizar (Regla Fito/Zoo)
                    if "fitoplancton" in nombre_p or "zooplancton" in nombre_p:
                        # Si es una lista de especies, no sumamos, solo sumamos la cabecera
                        if "especie" not in nombre_p: total_parametros += 1
                    else:
                        total_parametros += 1

                    # 2. Lógica de Siglas Fuera de Límite
                    es_fuera = False
                    
                    # Caso Especial: Cloro (Error si es < 0.2)
                    if "cloro" in nombre_p and val_res is not None:
                        if val_res < 0.2: es_fuera = True
                    
                    # Caso Especial: pH (Error si fuera de 6.5 - 8.5)
                    elif "ph" in nombre_p and val_res is not None:
                        if val_res < 6.5 or val_res > 8.5: es_fuera = True
                    
                    # Caso General: Resultado > Límite
                    elif val_res is not None and val_lim is not None:
                        if val_res > val_lim: es_fuera = True
                    
                    # Caso Microbiológico: Presencia
                    elif "presencia" in f[idx_res].lower():
                        es_fuera = True

                    if es_fuera:
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
archivo = st.file_uploader("Cargar PDF de Laboratorio", type="pdf")
if archivo:
    res = procesar_informe_detallado(archivo)
    st.table(pd.DataFrame([res]))
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        pd.DataFrame([res]).to_excel(writer, index=False)
    st.download_button("Descargar Excel", buf.getvalue(), "Reporte.xlsx")
