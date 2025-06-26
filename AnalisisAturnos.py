import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime

st.title("Análisis de Horas desde archivo de ATurnos (.html)")

def parsea_hora(hora_str):
    try:
        return datetime.strptime(hora_str, "%H:%M")
    except:
        return None

def analiza_fichero(fichero_html):
    contenido = fichero_html.read()
    soup = BeautifulSoup(contenido, "html.parser")

    # Extraer todos los tooltips de las barras de planificación
    barras = soup.find_all("div", class_="progress-bar")

    if not barras:
        return True, "No se encontraron barras de tiempo en el archivo.", None, None

    data = []
    for barra in barras:
        estilo = barra.get("style", "")
        clase = barra.get("class", [])
        tooltip = barra.get("data-original-title", "")

        # Buscar la fecha del día asociada a esta barra
        td = barra.find_parent("td")
        if not td:
            continue
        tr = td.find_parent("tr")
        if not tr:
            continue
        fecha_str = tr.find("td").get_text(strip=True)
        try:
            fecha = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        except:
            continue

        # Buscar horas en el tooltip
        match = re.search(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})", tooltip)
        if match:
            inicio_str, fin_str = match.groups()
            data.append({
                "fecha": fecha,
                "Inicio_str": inicio_str,
                "Fin_str": fin_str,
                "tooltip": tooltip,
                "class": "planned" if "planned" in clase else ("real" if "real" in clase else "otro")
            })

    if not data:
        return True, "No se pudieron extraer datos de horarios.", None, None

    df = pd.DataFrame(data)
    df["Inicio"] = df["Inicio_str"].apply(parsea_hora)
    df["Fin"] = df["Fin_str"].apply(parsea_hora)

    # Calcular horas por tipo (planned, real)
    df_summary = df.groupby(['fecha', 'class']).apply(
        lambda x: (x['Fin'] - x['Inicio']).sum().total_seconds() / 3600
    ).unstack(fill_value=0).reset_index()

    df_summary.columns.name = None
    df_summary.rename(columns={'planned': 'horas_planificadas', 'real': 'horas_reales'}, inplace=True)
    df_summary['desviacion_horas'] = df_summary['horas_reales'] - df_summary['horas_planificadas']

    return False, "Análisis completado con éxito.", df, df_summary

# Interfaz Streamlit
uploaded_file = st.file_uploader("Sube el archivo HTML exportado desde ATurnos", type=["html"])

if uploaded_file:
    error, mensaje, df, df_summary = analiza_fichero(uploaded_file)

    if error:
        st.error(mensaje)
    else:
        st.success(mensaje)
        st.subheader("Datos extraídos:")
        st.dataframe(df)

        st.subheader("Resumen por día (planificado vs real):")
        st.dataframe(df_summary)

        # Mostrar gráfico de desviaciones
        st.subheader("📊 Desviación de horas por día")
        st.bar_chart(df_summary.set_index("fecha")["desviacion_horas"])
