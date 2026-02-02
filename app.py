import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="Procesador de Laboratorio", layout="centered")

st.markdown("<h1 style='text-align: center;'>Procesador de Informes de Laboratorio</h1>", unsafe_allow_html=True)
st.markdown("---")

# Diccionario maestro de siglas (Instrucciones del usuario)
SIGLAS_MAP = {
    "bacteria aerobias heterotróficas": "BAH",
    "bacterias heterótrofas totales": "BH",
    "bacterias coliformes totales": "BCT",
    "escherichia coli": "EC",
    "pseudomonas aeruginosa": "PA",
    "fitoplancton": "fito",
    "zooplancton": "zoo",
    "compuestos orgánicos volátiles": "COV",
    "coliformes termotolerantes": "CF",
    "fósforo total": "P",
    "nitrógeno amoniacal": "NA",
    "sulfatos": "S",
    "dqo": "DQO",
    "dbo5": "DBO",
    "color": "color",
    "trihalometanos": "THM",
    "cloro residual": "cloro",
    "ph": "pH",
    "turbiedad": "Turbiedad",
    "turbidez": "Turbiedad",
    "dureza total": "Dureza",
    "aluminio": "Al",
    "fluoruros": "F",
    "cloruros": "Cl",
    "arsénico": "As",
    "arsenico": "As"
}

def limpiar_valor(texto):
    """Convierte texto de tabla a número (ej: '<0.1' -> 0.1)"""
    if not texto: return None
    # Cambia comas por puntos y busca números
    texto = str(texto).replace(',', '.')
    numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto)
    return float(numeros[0]) if numeros else None

def procesar_laboratorio(file):
    with pdfplumber.open(file) as pdf:
        # 1. Extraer todo el texto para la fecha
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() or ""
        
        # Buscar Fecha de Muestreo (Regex robusta)
        match_fecha = re.search(r'Fecha de Muestreo[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
        fecha_muestreo = match_fecha.group(1) if match_fecha else "No detectada"

        total_parametros = 0
        fuera_de_limite = []
        
        # 2. Procesar tablas para parámetros y límites
        for page
