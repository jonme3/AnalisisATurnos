import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime, timedelta

st.title("Análisis de Horas desde archivo de ATurnos (.html)")

def parsea_hora(hora_str):
    try:
        return datetime.strptime(hora_str, "%H:%M")
    except:
        return None

def calcula_teoricas(fecha):
    """
    Calcula las horas teóricas según el día de la semana y si está en periodo de verano.
    """
    verano_inicio = datetime(fecha.year, 6, 15).date()
    verano_fin = datetime(fecha.year, 9, 15).date()
    if verano_inicio <= fecha <= verano_fin:
        return 7 + 16/60  # 7h16m en verano

    weekday = fecha.weekday()
    if weekday in range(0, 4):  # Lunes a jueves
        return 7 + 30/60  # 7h30m
    elif weekday == 4:  # Viernes
        return 6 + 20/60  # 6h20m
    else:
        return 0  # Sábado y domingo no computan

def analiza_fichero(fichero_html):
    contenido = fichero_html.read()
    soup = BeautifulSoup(contenido, "html.parser")

    barras = soup.find_all("div", class_="progress-bar")

    if not barras:
        return True, "No se encontraron barras de tiempo en el archivo.", None, None, None

    data = []
    for barra in barras:
        estilo = barra.get("style", "")
        clase = barra.get("class", [])
        tooltip = barra.get("data-original-title", "")

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

        # Detectar días festivos o absentismos
        tr_classes = tr.get("class", [])
        barra_classes = clase

        if ("festive" in tr_classes or
            "weekend" in tr_classes or
            any(c in barra_classes for c in ["planned_holidays", "leave_holidays", "leave", "absenteeism"])):
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
        return True, "No se pudieron extraer datos de horarios.", None, None, None

    df = pd.DataFrame(data)
    df["Inicio"] = df["Inicio_str"].apply(parsea_hora)
    df["Fin"] = df["Fin_str"].apply(parsea_hora)

    # Calcular horas trabajadas por día (sumando segmentos)
    df["horas"] = (df["Fin"] - df["Inicio"]).dt.total_seconds() / 3600

    df_summary = df.groupby('fecha').agg({"horas": "sum"}).reset_index()

    # Calcular horas teóricas y desviación
    df_summary["horas_teoricas"] = df_summary["fecha"].apply(calcula_teoricas)
    df_summary["desviacion"] = df_summary["horas"] - df_summary["horas_teoricas"]

    # Resumen semanal
    df_summary["semana"] = df_summary["fecha"].apply(lambda x: x.isocalendar()[1])
    df_semana = df_summary.groupby("semana").agg({
        "horas": "sum",
        "horas_teoricas": "sum"
    }).reset_index()
    df_semana["desviacion"] = df_semana["horas"] - df_semana["horas_teoricas"]

    return False, "Análisis completado con éxito.", df, df_summary, df_semana

# Interfaz Streamlit
uploaded_file = st.file_uploader("Sube el archivo HTML exportado desde ATurnos", type=["html"])

if uploaded_file:
    error, mensaje, df, df_summary, df_semana = analiza_fichero(uploaded_file)

    if error:
        st.error(mensaje)
    else:
        st.success(mensaje)
        st.subheader("Datos extraídos:")
        st.dataframe(df)

        st.subheader("Resumen por día (trabajado vs teórico):")
        st.dataframe(df_summary)

        st.subheader("Resumen por semana (trabajado vs teórico):")
        st.dataframe(df_semana)

        # Gráfico de desviaciones diarias
        st.subheader("📊 Desviación de horas por día")
        st.bar_chart(df_summary.set_index("fecha")["desviacion"])

        # Gráfico de desviaciones semanales
        st.subheader("📊 Desviación de horas por semana")
        st.bar_chart(df_semana.set_index("semana")["desviacion"])
