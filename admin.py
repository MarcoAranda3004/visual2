import streamlit as st
import pandas as pd
import os

def mostrar_admin():
    st.title("🔐 Panel Administrativo")

    # RUTA DINÁMICA ABSOLUTA: Detecta automáticamente la carpeta del proyecto
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CSV_DIR = os.path.join(BASE_DIR, "csv")

    # Inicializar la variable de sesión para el estado del login
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    # Formulario de Login Simple
    if not st.session_state["autenticado"]:
        st.subheader("🔑 Acceso Restringido")
        
        with st.form("formulario_login"):
            usuario = st.text_input("Usuario admin:")
            contrasena = st.text_input("Contraseña:", type="password")
        
            boton_ingresar = st.form_submit_button("Ingresar")
            
            if boton_ingresar:
                if usuario == "admin" and contrasena == "agro2026":
                    st.session_state["autenticado"] = True
                    st.success("¡Acceso concedido!")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
    else:
        # =====================================================================
        # PANEL DE CONTROL PRIVADO (Solo visible tras loguearse)
        # =====================================================================
        st.subheader("🛠️ Panel de Actualización de Datos")
        
        if st.button("Cerrar Sesión"):
            st.session_state["autenticado"] = False
            st.rerun()
            
        st.markdown("---")
        st.markdown("#### 📈 Adjuntar Nuevos Precios Reales al Histórico")
        st.write("Sube un CSV con los nuevos registros. El sistema los **añadirá** al final de la base de datos existente sin borrar el pasado.")

        # Selector para saber qué archivo se va a actualizar
        opcion_archivo = st.selectbox(
            "Selecciona la base de datos a la que deseas añadir datos:",
            [
                "dataset_productos_anual.csv (Precios de Frutas/Verduras)",
                "precios_diesel_anual.csv (Precios de Combustible)",
                "decretos_fluviales_anuales.csv (Historial de Bloqueos)"
            ]
        )

        # Mapeo del nombre del archivo real
        if "dataset_productos_anual" in opcion_archivo:
            nombre_real_archivo = "dataset_productos_anual.csv"
        elif "precios_diesel_anual" in opcion_archivo:
            nombre_real_archivo = "precios_diesel_anual.csv"
        else:
            nombre_real_archivo = "decretos_fluviales_anuales.csv"

        # Componente para arrastrar y soltar el archivo con los datos nuevos
        archivo_subido = st.file_uploader(f"Arrastra aquí el archivo con las nuevas filas para {nombre_real_archivo}", type=["csv"])

        if archivo_subido is not None:
            try:
                # 1. Leer las nuevas filas subidas
                df_nuevas_filas = pd.read_csv(archivo_subido)
                
                st.markdown("##### 🔍 Vista previa de las NUEVAS filas detectadas:")
                st.dataframe(df_nuevas_filas.head(5), use_container_width=True)

                # Ruta del archivo viejo/actual
                ruta_destino = os.path.join(CSV_DIR, nombre_real_archivo)

               # 2. Botón de confirmación para fusionar
                if st.button(f"Confirmar y Combinar Datos", type="primary"):
                    
                    if os.path.exists(ruta_destino):
                        # Leer el archivo histórico actual
                        df_historico = pd.read_csv(ruta_destino)
                        
                        # =======================================================
                        # ¡LA SOLUCIÓN!: Forzamos a que ambos tengan el mismo formato de columnas
                        # =======================================================
                        df_historico.columns = df_historico.columns.str.strip().str.title()
                        df_nuevas_filas.columns = df_nuevas_filas.columns.str.strip().str.title()
                        
                        # Unir el histórico con lo nuevo
                        df_final = pd.concat([df_historico, df_nuevas_filas], ignore_index=True)
                        
                        # Limpieza inteligente: Elimina filas idénticas duplicadas
                        df_final = df_final.drop_duplicates()
                    else:
                        df_final = df_nuevas_filas
                    
                    # Guardar el archivo combinado final en la carpeta
                    df_final.to_csv(ruta_destino, index=False)
                    
                    # 3. Limpiamos las cachés de Streamlit de inmediato para actualizar los gráficos
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    
                    st.success(f"✅ ¡Datos añadidos y normalizados con éxito! Las cachés se limpiaron correctamente. Regresa al Dashboard.")
            except Exception as e:
                st.error(f"❌ Error al fusionar el archivo CSV: {str(e)}")