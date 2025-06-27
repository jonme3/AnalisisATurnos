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

    filas = soup.find_all("tr", class_="item-user")
    data = []
    fechas_totales = []

    for tr in filas:
        fecha_td = tr.find("td")
        if not fecha_td:
            continue
        fecha_str = fecha_td.get_text(strip=True)
        try:
            fecha = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        except:
            continue

        fechas_totales.append(fecha)

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

    # Crear dataframe con todas las fechas entre mínimo y máximo
    if fechas_totales:
        fecha_min = min(fechas_totales)
        fecha_max = max(fechas_totales)
        rango_fechas = pd.date_range(fecha_min, fecha_max, freq='D').date
        df_fechas = pd.DataFrame(rango_fechas, columns=["fecha"])
    else:
        return True, "No se encontraron fechas en el archivo.", None, None, None

    # Crear dataframe de resultados
    df = pd.DataFrame(data)

    # Calcular horas trabajadas por fecha y tipo si hay datos
    if not df.empty:
        df_summary = df.groupby(['fecha', 'tipo'])['horas'].sum().unstack(fill_value=0).reset_index()
    else:
        df_summary = pd.DataFrame(columns=["fecha", "planned", "real", "otro"])

    # Unir con el dataframe completo de fechas para incluir días sin fichaje
    df_final = pd.merge(df_fechas, df_summary, on="fecha", how="left").fillna(0)

    # Calcular horas teóricas y desviación
    df_final['horas_teoricas'] = df_final['fecha'].apply(calcula_teoricas)
    df_final['desviacion'] = df_final.get('real', 0) - df_final['horas_teoricas']

    # Añadir columna de semana
    df_final["semana"] = df_final["fecha"].apply(lambda x: x.isocalendar()[1])

    # Resumen semanal completo
    df_semana = df_final.groupby("semana").agg({
        "real": "sum",
        "horas_teoricas": "sum"
    }).reset_index()
    df_semana["desviacion"] = df_semana["real"] - df_semana["horas_teoricas"]

    return False, "Análisis completado con éxito.", df, df_final, df_semana

# Interfaz Streamlit
uploaded_file = st.file_uploader("Sube el archivo HTML exportado desde ATurnos", type=["html"])

if uploaded_file:
    error, mensaje, df, df_final, df_semana = analiza_fichero(uploaded_file)

    if error:
        st.error(mensaje)
    else:
        st.success(mensaje)
        st.subheader("Datos extraídos:")
        st.dataframe(df)

        st.subheader("Resumen por día (planificado, real, teórico):")
        st.dataframe(df_final)

        st.subheader("Resumen por semana (trabajado vs teórico):")
        st.dataframe(df_semana)

        st.subheader("📊 Desviación de horas por día")
        st.bar_chart(df_final.set_index("fecha")["desviacion"])

        st.subheader("📊 Desviación de horas por semana")
        st.bar_chart(df_semana.set_index("semana")["desviacion"])
