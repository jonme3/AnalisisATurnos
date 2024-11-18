import streamlit as st
import pandas as pd
#import matplotlib.pyplot as plt
import numpy as np
from bs4 import BeautifulSoup
import re
 
# Función para analizar un archivo HTML
def analiza_fichero(file) :
    try :
        #with open(path, "r", encoding="utf-8") as file:
        contenido_html = file.read()

        # Analiza el HTML con BeautifulSoup
        soup = BeautifulSoup(contenido_html, "lxml")

        elementos_row = soup.find_all(id=re.compile("^row"))

        clases_busqueda = set()  # Usamos un conjunto para evitar duplicados

        # Buscar todos los elementos que contienen la clase "progress-bar"
        for elemento in soup.find_all(class_="progress-bar"):
            # Obtener todas las clases del elemento
            clases = elemento.get("class", [])
            
            # Añadir las clases que no sean "progress-bar" a la lista de acompañantes
            clases_busqueda.update(clase for clase in clases if clase != "pro gress-bar")

        # Convertir el conjunto a lista si se necesita, o imprimir directamente
        clases_busqueda = list(clases_busqueda)
        #print(clases_busqueda)

        # Crear una lista para almacenar la información de cada elemento
        data = []
        # Extraer la información específica de cada elemento
        for elemento in elementos_row:
            elemento_id = elemento.get("id")

            # Recorrer cada clase que contiene la información en "data-original-title"
            for clase in clases_busqueda:
                sub_elementos = elemento.find_all(class_=clase)
                
                for sub_elemento in sub_elementos:
                    data_original_title = sub_elemento.get("data-original-title", "")
                    
                    # Separar las líneas en cada `<br>`
                    lineas = data_original_title.split("<br>")
                    lineas = [BeautifulSoup(line, "lxml").get_text(strip=True) for line in lineas if line.strip()]

                    # Crear un diccionario con la información extraída
                    fila = {"row_id": elemento_id, "class": clase}
                    
                    # Agregar cada línea como una columna
                    for i, linea in enumerate(lineas):
                        fila[f"line_{i+1}"] = linea
                    
                    # Agregar la fila a los datos
                    data.append(fila)

        # Crear un DataFrame a partir de la lista de diccionarios
        df = pd.DataFrame(data)

        # Mostrar el DataFrame
        #print(df.columns)

        df['fecha'] = pd.to_datetime(df['row_id'].str.replace('row-', ''))

        clases=['planned', 'planned_holidays', 'time-absenteeism']

        df['tipo'] = df['line_1'].where(df['class'].isin(clases), "fichaje")


        # Filtrar las filas donde 'class' sea 'planned'
        mask = (df['class'].isin(clases)) & (df['line_3'].notna())
        # Crear un DataFrame intermedio con el resultado del split
        split_df = df.loc[mask, 'line_3'].str.split(' - ', expand=True)
        df.loc[mask, 'Inicio_str'] = split_df[0]
        df.loc[mask, 'Fin_str'] = split_df[1]
        mask = (df['class'].isin(clases)) & (df['line_3'].isna())
        split_df = df.loc[mask, 'line_2'].str.split(' - ', expand=True)
        df.loc[mask, 'Inicio_str'] = split_df[0]
        df.loc[mask, 'Fin_str'] = split_df[1]
        #mask = df['class'] == 'time-checkin'
        mask = df['class'].isin(['time-checkin', 'not-close'])
        # Crear un DataFrame intermedio con el resultado del split
        split_df = df.loc[mask, 'line_1'].str.split(' - ', expand=True)

        # Asignar las columnas 'Inicio' y 'Fin' usando el DataFrame intermedio
        df.loc[mask, 'Inicio_str'] = split_df[0]
        df.loc[mask, 'Fin_str'] = split_df[1]
        print(df['fecha'].astype(str) + " " + df['Inicio_str'])

        df['Inicio'] = pd.to_datetime(df['fecha'].astype(str) + " " + df['Inicio_str'], errors='coerce', format='%Y-%m-%d %H:%M')
        df['Fin'] = pd.to_datetime(df['fecha'].astype(str) + " " + df['Fin_str'], errors='coerce', format='%Y-%m-%d %H:%M')

        df['metodo_ini'] = np.nan

        #Entradas sin marcador en linea_5
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & ~(df['line_5'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = 'Automatico'
        #Entradas con marcador en linea_5
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & (df['line_5'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = df.loc[mask, 'line_5']
        #Entradas sin marcador en linea_5
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & ~(df['line_5'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = 'Automatico'
        #Entradas con marcador en linea_6
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & (df['line_6'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = df.loc[mask, 'line_6']

        #Entradas sin marcador (teletrabajo, desplazamiento)
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & ~(df['line_3'].str.contains('Check', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = df.loc[mask, 'line_3']

        #Salidas sin marcador
        mask = (df['line_6'].str.contains('Salida', case=False, na=False)) & ~(df['line_9'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] ='Automatico'
        #Salidas con marcador
        mask = (df['line_6'].str.contains('Salida', case=False, na=False)) & (df['line_9'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_9']
        #Salidas con marcador
        mask = (df['line_6'].str.contains('Salida', case=False, na=False)) & (df['line_10'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_10']

        #Salidas sin marcador
        mask = (df['line_6'].str.contains('Salida', case=False, na=False)) & ~(df['line_7'].str.contains('Check', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_7']

        #Salidas sin marcador
        mask = (df['line_5'].str.contains('Salida', case=False, na=False)) 
        df.loc[mask, 'metodo_fin'] ='Automatico'

        #Salidas con marcador
        mask = (df['line_7'].str.contains('Salida', case=False, na=False)) & (df['line_10'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_10']
        #Salidas con marcador
        mask = (df['line_7'].str.contains('Salida', case=False, na=False)) & (df['line_11'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_11']
        #Salidas sin marcador
        mask = (df['line_7'].str.contains('Salida', case=False, na=False)) & ~(df['line_10'].str.contains('Tipo', case=False, na=False)) & ~(df['line_11'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] ='Automatico'

        df['tipo'] = df['tipo'].str.replace(r"^\[\-\] ", "", regex=True)
        df['metodo_ini'] = df['metodo_ini'].str.replace(r"Tipo: ", "", regex=True)
        df['metodo_fin'] = df['metodo_fin'].str.replace(r"Tipo: ", "", regex=True)

        #Cálculo de tiempo trabajado
        #df['t_trabajo'] =  (df['Fin'] - df['Inicio']).dt.total_seconds() / 60

        columnas_a_eliminar = ['row_id', 'line_1', 'line_2', 'line_3', 'line_4', 'line_5', 'line_6', 'line_7', 'line_8', 'line_9', 'line_10', 'line_11', 'Inicio_str', 'Fin_str']

        # Eliminar las columnas del DataFrame
        df = df.drop(columns=columnas_a_eliminar)


        return False, df

    except Exception as e:
        # En caso de error, devolvemos error = True y un DataFrame vacío
        print(f"Error al abrir o analizar el archivo: {e}")
        return True, pd.DataFrame()  # Devuelve True para error y un DataFrame vacío#hasta aqui la función que analiza el fichero html descargado

# Título de la aplicación
st.title("Visor de Datos ATurnos")

# Barra lateral para la selección del archivo y opciones de filtrado
st.sidebar.header("Opciones")

# Cargar archivo desde la barra lateral
uploaded_file = st.sidebar.file_uploader("Selecciona un archivo html", type=["html"])
print(uploaded_file)
# Crear el panel principal a la derecha
if uploaded_file is not None:
    
    error, df = analiza_fichero(uploaded_file)

    # Mostrar los datos en el panel derecho
    st.subheader("Datos cargados:")
    st.dataframe(df)

    # Selección de columnas para filtrar y graficar
    columnas_numericas = df.select_dtypes(include='number').columns.tolist()
    columnas = df.columns.tolist()

    # Selección de columna para filtrar
    columna_filtro = st.sidebar.selectbox("Selecciona la columna para filtrar", columnas)
    if columna_filtro:
        valores_filtro = st.sidebar.multiselect(f"Selecciona valores de '{columna_filtro}'", df[columna_filtro].unique())
        
        # Aplicar filtro
        if valores_filtro:
            df = df[df[columna_filtro].isin(valores_filtro)]
            st.write(f"Datos filtrados por {columna_filtro}:")
            st.dataframe(df)

    # Selección de columnas para gráficos
    st.sidebar.subheader("Opciones de Gráficos")
    columna_x = st.sidebar.selectbox("Selecciona la columna para el eje X", columnas_numericas)
    columna_y = st.sidebar.selectbox("Selecciona la columna para el eje Y", columnas_numericas)

    '''
    if columna_x and columna_y:
        # Crear gráfico
        st.subheader("Gráfico de Datos")
        fig, ax = plt.subplots()
        ax.plot(df[columna_x], df[columna_y], marker='o', linestyle='-')
        ax.set_xlabel(columna_x)
        ax.set_ylabel(columna_y)
        ax.set_title(f"Gráfico de {columna_y} vs {columna_x}")
        
        # Mostrar gráfico
        st.pyplot(fig)
    '''
    
    df_agrupado = df.groupby('fecha')

    # CSS para ajustar el ancho de la tabla
    st.markdown(
        """
        <style>
        .dataframe {
            width: 100% !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Mostrar el DataFrame en Streamlit
    st.write("Datos agrupados por fecha:")
    st.dataframe(df_agrupado)


    filters = {}
    colors = {}

    # Checkboxes dinámicos para cada valor único en la columna "Tipo"
    for tipo in df["tipo"].unique():
        st.sidebar.subheader(f"{tipo}")
        
        # Checkbox para filtrar por cada tipo
        is_selected = st.sidebar.checkbox(f"Incluir {tipo}", value=True)
        filters[tipo] = is_selected
        
        # Color Picker asociado al tipo
        color = st.sidebar.color_picker(f"Color para {tipo}", "#ffffff")
        colors[tipo] = color

    # Aplicar filtros según los checkboxes seleccionados
    selected_types = [tipo for tipo, is_selected in filters.items() if is_selected]
    filtered_df = df[df["tipo"].isin(selected_types)]

    # Aplicar colores dinámicos a la tabla
    def apply_styles(row):
        color = colors.get(row["tipo"], "#ffffff")  # Obtener el color para el tipo
        return [f"background-color: {color}"] * len(row)

    # Mostrar la tabla con filtros y estilos aplicados
    st.write("### Datos filtrados")
    styled_table = filtered_df.style.apply(apply_styles, axis=1)
    st.write(styled_table.to_html(), unsafe_allow_html=True)



else:
    st.write("Por favor, selecciona un archivo desde la barra lateral para cargar los datos.")
