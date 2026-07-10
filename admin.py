import streamlit as st
import pandas as pd
import os
import re
import pdfplumber
import tempfile  # Librería estándar (no requiere instalación)

# =====================================================================
# CONSTANTES Y FUNCIONES (Mismo motor original)
# =====================================================================
MUROS_DIVISORES = {'BANDEJA', 'KILOGRAMO', 'JABA', 'CAJON', 'SACO', 'ATADO', 'UNIDAD', 'KG', 'BALDE', 'CAJA', 'BOLSA', 'CIENTO', 'DOCENA', 'PAQUETE', 'MALLA'}
MESES_MAP = {
    'enero':'01','febrero':'02','marzo':'03','abril':'04','mayo':'05','junio':'06',
    'julio':'07','agosto':'08','septiembre':'09','octubre':'10','noviembre':'11','diciembre':'12'
}

def format_fecha(txt):
    try:
        txt = txt.lower()
        for m_es, m_num in MESES_MAP.items():
            if f' de {m_es} de ' in txt: txt = txt.replace(f' de {m_es} de ', f'/{m_num}/')
            elif f' de {m_es} del ' in txt: txt = txt.replace(f' de {m_es} del ', f'/{m_num}/')
        return txt
    except:
        return None

def procesar_pdf_stream(archivo_subido, nombre_original):
    """Procesamiento conservador usando archivo temporal para estabilidad"""
    resultados = []
    
    # 1. Crear archivo temporal para evitar el Segmentation fault
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(archivo_subido.getbuffer())
        ruta_tmp = tmp.name

    try:
        # 2. Abrimos usando la ruta física, más estable en entornos de nube
        with pdfplumber.open(ruta_tmp) as pdf:
            texto_pag1 = pdf.pages[0].extract_text()
            match_fecha = re.search(r'(\d{1,2}\s+de\s+\w+\s+de\s+(\d{4}))', texto_pag1, re.IGNORECASE)
            fecha_str = match_fecha.group(1) if match_fecha else nombre_original.replace('.pdf', '')

            for pagina in pdf.pages:
                tabla = pagina.extract_table()
                if not tabla: continue

                for fila in tabla:
                    if not fila or fila[0] is None: continue

                    prod_raw = str(fila[0]).split('\n')[0]
                    nombre_item = ' '.join(re.sub(r'[\d\.]+', '', prod_raw).split()).upper().strip()
                    if not nombre_item or nombre_item in ['PRODUCTOS', 'NONE', 'PRECIOS', 'VARIACIÓN', '']: continue

                    idx_muro = -1
                    for idx_c, celda in enumerate(fila):
                        if celda:
                            celda_upper = str(celda).upper().strip().replace('\n', '')
                            if any(muro in celda_upper for muro in MUROS_DIVISORES):
                                idx_muro = idx_c; break
                    if idx_muro == -1: continue

                    texto_izq = ' '.join([str(fila[i]) for i in range(1, idx_muro) if fila[i]])
                    vols = re.findall(r'\d+\.\d+|\d+', texto_izq)

                    texto_der = ' '.join([str(fila[i]) for i in range(idx_muro + 2, len(fila)) if fila[i]])
                    precios = re.findall(r'\d+\.\d+|\d+', texto_der.replace(',', '.'))

                    if len(vols) >= 1 and len(precios) >= 2:
                        resultados.append({
                            'fecha_original': fecha_str, 'producto': nombre_item,
                            'volumen_hoy': vols[0], 'volumen_7dias': vols[1] if len(vols) > 1 else vols[0],
                            'precio_ayer': precios[0], 'precio_7dias': precios[2] if len(precios) > 2 else precios[0],
                            'precio_hoy_kg': precios[1] if len(precios) > 1 else precios[0]
                        })
    finally:
        # 3. Limpieza obligatoria del archivo temporal
        if os.path.exists(ruta_tmp):
            os.remove(ruta_tmp)

    if not resultados: return pd.DataFrame()

    df_diario = pd.DataFrame(resultados)
    for col in ['volumen_hoy', 'volumen_7dias', 'precio_ayer', 'precio_7dias', 'precio_hoy_kg']:
        df_diario[col] = pd.to_numeric(df_diario[col], errors='coerce').fillna(0).round(2)

    df_diario['fecha_dt'] = pd.to_datetime(df_diario['fecha_original'].apply(format_fecha), errors='coerce', dayfirst=True)
    df_diario = df_diario.dropna(subset=['fecha_dt']).sort_values(['fecha_dt', 'producto'])

    return df_diario[[
        'fecha_dt', 'producto', 'volumen_hoy', 'volumen_7dias', 'precio_ayer', 'precio_7dias', 'precio_hoy_kg'
    ]].rename(columns={
        'fecha_dt': 'Fecha', 'producto': 'Producto', 'volumen_hoy': 'Volumen_Hoy',
        'volumen_7dias': 'Volumen_7Dias', 'precio_ayer': 'Precio_Ayer',
        'precio_7dias': 'Precio_7Dias', 'precio_hoy_kg': 'Precio_Hoy_Kg'
    })

# =====================================================================
# VISTA DEL PANEL ADMINISTRATIVO
# =====================================================================
def mostrar_admin():
    st.title("🔐 Panel Administrativo")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CSV_DIR = os.path.join(BASE_DIR, "csv")

    if "autenticado" not in st.session_state: st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.subheader("🔑 Acceso Restringido")
        with st.form("formulario_login"):
            usuario = st.text_input("Usuario admin:")
            contrasena = st.text_input("Contraseña:", type="password")
            boton_ingresar = st.form_submit_button("Ingresar")
            if boton_ingresar:
                if usuario == "admin" and contrasena == "agro2026":
                    st.session_state["autenticado"] = True
                    st.rerun()
                else: st.error("Credenciales incorrectas.")
    else:
        st.subheader("🛠️ Panel de Actualización de Datos")
        if st.button("Cerrar Sesión"):
            st.session_state["autenticado"] = False
            st.rerun()
            
        st.markdown("---")
        opcion_archivo = st.selectbox("Selecciona la base de datos:", 
            ["dataset_productos_anual.csv", "precios_diesel_anual.csv", "decretos_fluviales_anuales.csv"])
        
        archivo_subido = st.file_uploader("Arrastra aquí el reporte PDF", type=["pdf"])

        if archivo_subido is not None:
            try:
                with st.spinner("🧠 Procesando PDF..."):
                    df_nuevas_filas = procesar_pdf_stream(archivo_subido, archivo_subido.name)
                
                if df_nuevas_filas.empty:
                    st.warning("⚠️ No se pudieron extraer datos.")
                else:
                    st.markdown("##### 🔍 Vista previa:")
                    # CORRECCIÓN: width='stretch' en lugar de use_container_width=True
                    st.dataframe(df_nuevas_filas.head(10), width='stretch')
                    
                    if st.button("Confirmar e Inyectar al Histórico", type="primary"):
                        ruta_destino = os.path.join(CSV_DIR, opcion_archivo)
                        
                        # --- LÓGICA ORIGINAL DE GUARDADO ---
                        if os.path.exists(ruta_destino):
                            df_historico = pd.read_csv(ruta_destino)
                            df_historico.columns = df_historico.columns.str.strip().str.lower()
                            df_nuevas_filas.columns = df_nuevas_filas.columns.str.strip().str.lower()
                            
                            for df_temp in [df_historico, df_nuevas_filas]:
                                col_prod = [c for c in df_temp.columns if 'producto' in c or 'item' in c]
                                if col_prod:
                                    df_temp[col_prod[0]] = df_temp[col_prod[0]].astype(str).str.strip().str.upper()
                                    for char in ['Á','É','Í','Ó','Ú']: df_temp[col_prod[0]] = df_temp[col_prod[0]].str.replace(char, char.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U'))
                            
                            df_final = pd.concat([df_historico, df_nuevas_filas], ignore_index=True)
                            col_fecha = [c for c in df_final.columns if 'fech' in c or 'date' in c or c == 'f']
                            if col_fecha:
                                df_final[col_fecha[0]] = pd.to_datetime(df_final[col_fecha[0]], errors='coerce')
                                df_final = df_final.dropna(subset=[col_fecha[0]]).drop_duplicates(subset=[col_fecha[0], [c for c in df_final.columns if 'producto' in c or 'item' in c][0]], keep='last')
                                df_final = df_final.sort_values(by=col_fecha[0]).reset_index(drop=True)
                                df_final[col_fecha[0]] = df_final[col_fecha[0]].dt.strftime('%Y-%m-%d')
                        else: df_final = df_nuevas_filas
                        
                        df_final.to_csv(ruta_destino, index=False)
                        st.cache_data.clear()
                        st.success("✅ ¡Éxito! Datos inyectados.")
            except Exception as e:
                st.error(f"❌ Error crítico: {str(e)}")