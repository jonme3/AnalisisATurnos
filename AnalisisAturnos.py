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

    filas = soup.find_all("tr", class_="item-user")
    fechas = []
    data = []

    for tr in filas:
        fecha_td = tr.find("td")
        if not fecha_td:
            continue
        fecha_str = fecha_td.get_text(strip=True)
        try:
            fecha = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        except:
            continue

        fechas.append(fecha)

        tr_classes = tr.get("class", [])
        if "festive" in tr_classes or "weekend" in tr_classes:
            continue

        barras = tr.find_all("div", class_="progress-bar")
        for barra in barras:
            clase = barra.get("class", [])
            tooltip = barra.get("data-original-title", "")

            if any(c in clase for c in ["planned_holidays", "leave_holidays", "leave", "absenteeism"]):
                continue

            # Buscar horas en el tooltip
            match = re.search(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})", tooltip)
            if match:
                inicio_str, fin_str = match.groups()
                inicio = parsea_hora(inicio_str)
                fin = parsea_hora(fin_str)
                if inicio and fin:
                    horas = (fin - inicio).seconds / 3600
                else:
                    horas = 0

                tipo = "planned" if "planned" in clase else ("real" if "time-checkin" in clase else "otro")

                data.append({
                    "fecha": fecha,
                    "inicio_str": inicio_str,
                    "fin_str": fin_str,
                    "horas": horas,
                    "tipo": tipo
                })

    # Crear dataframe de resultados
    df = pd.DataFrame(data)

    if df.empty:
        return True, "No se pudieron extraer datos de horarios.", None, None, None

    # Resumen de horas por día y tipo
    df_summary = df.groupby(['fecha', 'tipo'])['horas'].sum().unstack(fill_value=0).reset_index()

    # Añadir horas teóricas y desviación
    df_summary['horas_teoricas'] = df_summary['fecha'].apply(calcula_teoricas)
    df_summary['horas_reales'] = df_summary.get('real', 0)
    df_summary['desviacion'] = df_summary['horas_reales'] - df_summary['horas_teoricas']

    # Resumen semanal
    df_summary["semana"] = df_summary["fecha"].apply(lambda x: x.isocalendar()[1])
    df_semana = df_summary.groupby("semana").agg({
        "horas_reales": "sum",
        "horas_teoricas": "sum"
    }).reset_index()
    df_semana["desviacion"] = df_semana["horas_reales"] - df_semana["horas_teoricas"]

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

        st.subheader("Resumen por día (planificado, real, teórico):")
        st.dataframe(df_summary)

        st.subheader("Resumen por semana (trabajado vs teórico):")
        st.dataframe(df_semana)

        st.subheader("📊 Desviación de horas por día")
        st.bar_chart(df_summary.set_index("fecha")["desviacion"])

        st.subheader("📊 Desviación de horas por semana")
        st.bar_chart(df_semana.set_index("semana")["desviacion"])
