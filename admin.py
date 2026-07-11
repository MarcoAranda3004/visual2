import streamlit as st
import pandas as pd
import os
from datetime import datetime

def mostrar_admin():
    st.title("🔐 Panel Administrativo")

    # RUTA DINÁMICA ABSOLUTA: Detecta automáticamente la carpeta del proyecto
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CSV_DIR = os.path.join(BASE_DIR, "csv")

    # Inicializar variables de estado para los mensajes persistentes
    if "mensaje_exito" not in st.session_state:
        st.session_state["mensaje_exito"] = None

    # =====================================================================
    # PANEL DE CONTROL DIRECTO
    # =====================================================================
    st.subheader("🛠️ Panel de Actualización de Datos")
    st.markdown("---")
    
    # Mostrar el mensaje de éxito si quedó guardado de la recarga anterior
    if st.session_state["mensaje_exito"]:
        st.success(st.session_state["mensaje_exito"])
        st.session_state["mensaje_exito"] = None  # Lo limpiamos para que no se quede fijo

    # ---------------------------------------------------------------------
    # SECCIÓN 1: CARGA MASIVA DE PRODUCTOS (CSV)
    # ---------------------------------------------------------------------
    st.markdown("#### 📈 Adjuntar Nuevos Precios de Productos al Histórico")
    st.write("Sube un CSV con los nuevos registros de frutas y verduras. El sistema los **añadirá** al final de la base de datos existente.")

    nombre_real_archivo_prod = "dataset_productos_anual.csv"
    ruta_destino_prod = os.path.join(CSV_DIR, nombre_real_archivo_prod)

    archivo_subido = st.file_uploader(f"Arrastra aquí el archivo con las nuevas filas para {nombre_real_archivo_prod}", type=["csv"])

    if archivo_subido is not None:
        try:
            df_nuevas_filas = pd.read_csv(archivo_subido)
            st.markdown("##### 🔍 Vista previa de las NUEVAS filas detectadas:")
            st.dataframe(df_nuevas_filas.head(5), use_container_width=True)

            if st.button(f"Confirmar y Combinar Productos", type="primary"):
                if os.path.exists(ruta_destino_prod):
                    df_historico = pd.read_csv(ruta_destino_prod)
                    df_historico.columns = df_historico.columns.str.strip().str.lower()
                    df_nuevas_filas.columns = df_nuevas_filas.columns.str.strip().str.lower()
                    
                    for df_temporal in [df_historico, df_nuevas_filas]:
                        col_prod = [c for c in df_temporal.columns if 'producto' in c or 'item' in c]
                        if col_prod:
                            df_temporal[col_prod[0]] = df_temporal[col_prod[0]].astype(str).str.strip().str.upper()
                            df_temporal[col_prod[0]] = (df_temporal[col_prod[0]]
                                                        .str.replace('Á', 'A')
                                                        .str.replace('É', 'E')
                                                        .str.replace('Í', 'I')
                                                        .str.replace('Ó', 'O')
                                                        .str.replace('Ú', 'U'))
                    
                    df_final = pd.concat([df_historico, df_nuevas_filas], ignore_index=True)
                    
                    col_fecha = [c for c in df_final.columns if 'fech' in c or 'date' in c or c == 'f']
                    if col_fecha:
                        df_final[col_fecha[0]] = pd.to_datetime(df_final[col_fecha[0]], errors='coerce')
                        df_final = df_final.dropna(subset=[col_fecha[0]])
                        df_final = df_final.sort_values(by=col_fecha[0]).reset_index(drop=True)
                        df_final[col_fecha[0]] = df_final[col_fecha[0]].dt.strftime('%Y-%m-%d')

                    df_final = df_final.drop_duplicates()
                else:
                    df_final = df_nuevas_filas
                
                df_final.to_csv(ruta_destino_prod, index=False)
                st.cache_data.clear()
                st.cache_resource.clear()
                
                st.session_state["mensaje_exito"] = f"✅ ¡Datos de productos añadidos correctamente!"
                st.rerun()
        except Exception as e:
            st.error(f"❌ Error al fusionar el archivo CSV de productos: {str(e)}")

    # ---------------------------------------------------------------------
    # SECCIÓN 2: FORMULARIO INDEPENDIENTE PARA DIESEL
    # ---------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### ✍️ Ingreso Manual de Datos (Diesel)")
    st.write("Registra de forma directa el precio del combustible para que se agregue al histórico.")
    
    nombre_real_archivo_diesel = "precios_diesel_anual.csv"
    ruta_destino_diesel = os.path.join(CSV_DIR, nombre_real_archivo_diesel)

    lista_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    with st.form("form_diesel_manual"):
        col1, col2, col3 = st.columns(3)
        anio_diesel = col1.number_input("Año", value=2026, step=1, key="anio_diesel")
        mes_nombre = col2.selectbox("Mes", options=lista_meses)
        precio = col3.number_input("Precio Lima (Soles)", format="%.2f")
        
        btn_guardar_diesel = st.form_submit_button("Guardar Diesel en CSV")
        
        if btn_guardar_diesel:
            mes_num = lista_meses.index(mes_nombre) + 1
            
            nueva_fila_diesel = pd.DataFrame({
                'anio': [anio_diesel],
                'mes_num': [mes_num],
                'mes_nombre': [mes_nombre],
                'diesel_lima_soles': [precio]
            })
            
            if os.path.exists(ruta_destino_diesel):
                df_hist = pd.read_csv(ruta_destino_diesel)
                df_hist.columns = df_hist.columns.str.strip().str.lower()
                df_final = pd.concat([df_hist, nueva_fila_diesel], ignore_index=True)
            else:
                df_final = nueva_fila_diesel
                
            df_final = df_final.drop_duplicates()
            df_final.to_csv(ruta_destino_diesel, index=False)
            st.cache_data.clear()
            st.cache_resource.clear()
            
            st.session_state["mensaje_exito"] = f"✅ ¡Fila de Diesel agregada correctamente para {mes_nombre} ({mes_num})!"
            st.rerun()

    # ---------------------------------------------------------------------
    # SECCIÓN 3: FORMULARIO INDEPENDIENTE PARA DECRETOS FLUVIALES
    # ---------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📜 Ingreso Manual de Decretos Fluviales / Bloqueos")
    st.write("Registra un nuevo decreto o evento de impacto logístico directo en la base de datos.")

    nombre_real_archivo_decretos = "decretos_fluviales_anuales.csv"
    ruta_destino_decretos = os.path.join(CSV_DIR, nombre_real_archivo_decretos)

    with st.form("form_decretos_manual"):
        col1, col2, col3 = st.columns(3)
        decreto = col1.text_input("Decreto (Ej: D.S. N° 001-2020-PCM)")
        anio_decreto = col2.number_input("Año", value=2026, step=1, key="anio_dec")
        tipo = col3.selectbox("Tipo", ["Original", "Prórroga"])
        
        col4, col5 = st.columns(2)
        evento = col4.text_input("Evento (Ej: Lluvias Intensas / Huaicos)")
        zona_impacto = col5.text_input("Zona de Impacto Logístico (Ej: Eje Centro)")
        
        col6, col7 = st.columns(2)
        fecha_inicio_dt = col6.date_input("Fecha de Inicio")
        fecha_fin_dt = col7.date_input("Fecha de Fin")
        
        btn_guardar_decreto = st.form_submit_button("Guardar Decreto en CSV")
        
        if btn_guardar_decreto:
            # Formateamos las fechas al formato texto original DD/MM/YYYY
            fecha_inicio_str = fecha_inicio_dt.strftime('%d/%m/%Y')
            fecha_fin_str = fecha_fin_dt.strftime('%d/%m/%Y')
            
            # Crear nueva fila adaptando los nombres de columnas a minúsculas
            nueva_fila_decreto = pd.DataFrame({
                'decreto': [decreto],
                'anio': [anio_decreto],
                'tipo': [tipo],
                'evento': [evento],
                'zona_impacto_logistico': [zona_impacto],
                'fecha_inicio': [fecha_inicio_str],
                'fecha_fin': [fecha_fin_str]
            })
            
            if os.path.exists(ruta_destino_decretos):
                df_hist_dec = pd.read_csv(ruta_destino_decretos)
                df_hist_dec.columns = df_hist_dec.columns.str.strip().str.lower()
                df_final_dec = pd.concat([df_hist_dec, nueva_fila_decreto], ignore_index=True)
            else:
                df_final_dec = nueva_fila_decreto
                
            df_final_dec = df_final_dec.drop_duplicates()
            df_final_dec.to_csv(ruta_destino_decretos, index=False)
            st.cache_data.clear()
            st.cache_resource.clear()
            
            st.session_state["mensaje_exito"] = f"✅ ¡Decreto {decreto} guardado con éxito!"
            st.rerun()
