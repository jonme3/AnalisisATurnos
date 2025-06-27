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

    # Extraer todas las filas de días para tener todas las fechas
    filas = soup.find_all("tr", class_="item-user")
    fechas = []
    data = []

    for tr in filas:
        # Extraer la fecha
        fecha_td = tr.find("td")
        if not fecha_td:
            continue
        fecha_str = fecha_td.get_text(strip=True)
        try:
            fecha = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        except:
            continue

        fechas.append(fecha)

        # Detectar si es festivo o fin de semana
        tr_classes = tr.get("class", [])
        is_festive = ("festive" in tr_classes or "weekend" in tr_classes)

        # Si es festivo, no computar
        if is_festive:
            continue

        # Extraer barras de ese día
        barras = tr.find_all("div", class_="progress-bar")
        for barra in barras:
            clase = barra.get("class", [])
            tooltip = barra.get("data-original-title", "")

            # Detectar vacaciones o absentismo en la barra
            if any(c in clase for c in ["planned_holidays", "leave_holidays", "leave", "absenteeism"]):
                continue

            # Solo analizar fichajes reales (time-checkin)
            if not any("time-checkin" in c for c in clase):
                continue

            match = re.search(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})", tooltip)
            if match:
                inicio_str, fin_str = match.groups()
                inicio = parsea_hora(inicio_str)
                fin = parsea_hora(fin_str)
                if inicio and fin:
                    horas = (fin - inicio).seconds / 3600
                else:
                    horas = 0

                data.append({
                    "fecha": fecha,
                    "horas": horas
                })

    # Crear dataframe de datos
    df_data = pd.DataFrame(data)

    # Si df_data está vacío, crea las columnas para evitar KeyError
    if df_data.empty:
        df_data = pd.DataFrame(columns=["fecha", "horas"])

    # Agrupar por fecha si no está vacío
    if not df_data.empty:
        df_summary = df_data.groupby("fecha").agg({"horas": "sum"}).reset_index()
    else:
        df_summary = pd.DataFrame(columns=["fecha", "horas"])

    # Crear dataframe de todas las fechas analizadas
    df_fechas = pd.DataFrame(sorted(set(fechas)), columns=["fecha"])

    # Unir para tener días sin fichaje con 0h
    df_full = pd.merge(df_fechas, df_summary, on="fecha", how="left").fillna(0)

    # Calcular horas teóricas y desviación
    df_full["horas_teoricas"] = df_full["fecha"].apply(calcula_teoricas)
    df_full["desviacion"] = df_full["horas"] - df_full["horas_teoricas"]

    # Resumen semanal completo
    df_full["semana"] = df_full["fecha"].apply(lambda x: x.isocalendar()[1])
    df_semana = df_full.groupby("semana").agg({
        "horas": "sum",
        "horas_teoricas": "sum"
    }).reset_index()
    df_semana["desviacion"] = df_semana["horas"] - df_semana["horas_teoricas"]

    return False, "Análisis completado con éxito.", df_data, df_full, df_semana

# Interfaz Streamlit
uploaded_file = st.file_uploader("Sube el archivo HTML exportado desde ATurnos", type=["html"])

if uploaded_file:
    error, mensaje, df_data, df_full, df_semana = analiza_fichero(uploaded_file)

    if error:
        st.error(mensaje)
    else:
        st.success(mensaje)
        st.subheader("Datos de fichajes extraídos:")
        st.dataframe(df_data)

        st.subheader("Resumen por día (trabajado vs teórico):")
        st.dataframe(df_full)

        st.subheader("Resumen por semana (trabajado vs teórico):")
        st.dataframe(df_semana)

        st.subheader("📊 Desviación de horas por día")
        st.bar_chart(df_full.set_index("fecha")["desviacion"])

        st.subheader("📊 Desviación de horas por semana")
        st.bar_chart(df_semana.set_index("semana")["desviacion"])
