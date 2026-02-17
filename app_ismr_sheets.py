import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import json
import hashlib

# ============================================================================
# GESTIÓN DE CONTRASEÑAS EN GOOGLE SHEETS
# ============================================================================

def conectar_sheet_usuarios():
    """Conecta con la hoja de usuarios (contraseñas)"""
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        
        # Hoja separada para usuarios
        sheet_name = st.secrets.get("sheet_usuarios", "ISMR_Usuarios")
        
        try:
            spreadsheet = client.open(sheet_name)
        except:
            # Si no existe, crearla
            spreadsheet = client.create(sheet_name)
            # Compartir con el service account
            spreadsheet.share(credentials_dict["client_email"], perm_type='user', role='writer')
        
        worksheet = spreadsheet.sheet1
        
        # Encabezados para usuarios
        headers = ["username", "password_hash", "nombre_completo", "es_admin", "debe_cambiar_password"]
        current_headers = worksheet.row_values(1)
        
        if not current_headers:
            worksheet.append_row(headers)
        
        return worksheet
    except Exception as e:
        st.error(f"Error al conectar sheet de usuarios: {str(e)}")
        return None

def obtener_usuario(username):
    """Obtiene datos de un usuario"""
    worksheet = conectar_sheet_usuarios()
    if not worksheet:
        return None
    
    try:
        datos = worksheet.get_all_records()
        for usuario in datos:
            if usuario['username'] == username:
                return usuario
        return None
    except:
        return None

def actualizar_password(username, nuevo_password_hash, debe_cambiar=False):
    """Actualiza la contraseña de un usuario"""
    worksheet = conectar_sheet_usuarios()
    if not worksheet:
        return False
    
    try:
        datos = worksheet.get_all_values()
        for idx, fila in enumerate(datos[1:], start=2):  # Empezar desde fila 2 (después de header)
            if fila[0] == username:  # username está en columna 0
                worksheet.update_cell(idx, 2, nuevo_password_hash)  # password_hash en columna 2
                worksheet.update_cell(idx, 5, str(debe_cambiar).upper())  # debe_cambiar en columna 5
                return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar contraseña: {str(e)}")
        return False

def crear_usuario(username, password_hash, nombre_completo, es_admin=False, debe_cambiar=True):
    """Crea un nuevo usuario"""
    worksheet = conectar_sheet_usuarios()
    if not worksheet:
        return False
    
    try:
        # Verificar si ya existe
        if obtener_usuario(username):
            return False
        
        nueva_fila = [
            username,
            password_hash,
            nombre_completo,
            str(es_admin).upper(),
            str(debe_cambiar).upper()
        ]
        worksheet.append_row(nueva_fila)
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {str(e)}")
        return False

def listar_usuarios():
    """Lista todos los usuarios"""
    worksheet = conectar_sheet_usuarios()
    if not worksheet:
        return []
    
    try:
        return worksheet.get_all_records()
    except:
        return []

# ============================================================================
# AUTENTICACIÓN
# ============================================================================

def verificar_credenciales(username, password):
    """Verifica credenciales contra Google Sheets"""
    usuario = obtener_usuario(username)
    
    if not usuario:
        return False, None, False, False
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash == usuario['password_hash']:
        debe_cambiar = str(usuario.get('debe_cambiar_password', 'FALSE')).upper() == 'TRUE'
        es_admin = str(usuario.get('es_admin', 'FALSE')).upper() == 'TRUE'
        return True, usuario['nombre_completo'], debe_cambiar, es_admin
    
    return False, None, False, False

# ============================================================================
# PANTALLAS DE LOGIN Y CAMBIO DE CONTRASEÑA
# ============================================================================

def pantalla_cambiar_password():
    """Pantalla para cambiar contraseña (obligatoria en primer login)"""
    st.title("🔐 Cambio de Contraseña Obligatorio")
    st.markdown("---")
    
    st.warning("⚠️ Debes cambiar tu contraseña por defecto antes de continuar")
    
    st.info(f"👤 Usuario: **{st.session_state.username}**")
    
    with st.form("cambiar_password_form"):
        st.subheader("🔑 Nueva Contraseña")
        
        nueva_password = st.text_input("Nueva Contraseña", type="password", 
                                       help="Mínimo 8 caracteres")
        confirmar_password = st.text_input("Confirmar Nueva Contraseña", type="password")
        
        st.caption("💡 Usa una contraseña segura con letras, números y símbolos")
        
        submit = st.form_submit_button("✅ Cambiar Contraseña", use_container_width=True, type="primary")
        
        if submit:
            errores = []
            
            if len(nueva_password) < 8:
                errores.append("La contraseña debe tener mínimo 8 caracteres")
            
            if nueva_password != confirmar_password:
                errores.append("Las contraseñas no coinciden")
            
            if not nueva_password:
                errores.append("La contraseña no puede estar vacía")
            
            if errores:
                for error in errores:
                    st.error(f"❌ {error}")
            else:
                # Actualizar contraseña
                nuevo_hash = hashlib.sha256(nueva_password.encode()).hexdigest()
                
                if actualizar_password(st.session_state.username, nuevo_hash, debe_cambiar=False):
                    st.session_state.debe_cambiar_password = False
                    st.success("✅ ¡Contraseña actualizada exitosamente!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Error al actualizar contraseña. Intenta de nuevo.")

def login_page():
    """Página de login"""
    st.title("🔐 Acceso al Sistema ISMR")
    st.markdown("---")
    
    st.info("👋 Identifícate para acceder al sistema")
    
    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="tu.usuario")
        password = st.text_input("Contraseña", type="password")
        
        submit = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True, type="primary")
        
        if submit:
            if username and password:
                es_valido, nombre_completo, debe_cambiar, es_admin = verificar_credenciales(username, password)
                
                if es_valido:
                    st.session_state.autenticado = True
                    st.session_state.username = username
                    st.session_state.nombre_completo = nombre_completo
                    st.session_state.debe_cambiar_password = debe_cambiar
                    st.session_state.es_admin = es_admin
                    st.success(f"✅ Bienvenido, {nombre_completo}")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Por favor completa todos los campos")
    
    st.markdown("---")
    st.caption("🔒 Si tienes problemas para acceder, contacta al administrador")

def logout():
    """Cierra sesión"""
    st.session_state.autenticado = False
    st.session_state.username = None
    st.session_state.nombre_completo = None
    st.session_state.debe_cambiar_password = False
    st.session_state.es_admin = False
    st.rerun()

# ============================================================================
# PANEL DE GESTIÓN DE USUARIOS (SOLO ADMIN)
# ============================================================================

def panel_gestion_usuarios():
    """Panel para que admins gestionen usuarios"""
    st.title("👥 Gestión de Usuarios")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["➕ Crear Usuario", "📋 Ver Usuarios", "🔑 Ver Contraseñas"])
    
    # TAB 1: CREAR USUARIO
    with tab1:
        st.subheader("➕ Crear Nuevo Usuario")
        
        with st.form("crear_usuario_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_username = st.text_input("Usuario *", placeholder="nombre.apellido")
                nuevo_nombre = st.text_input("Nombre Completo *", placeholder="Juan Pérez")
            
            with col2:
                password_default = st.text_input(
                    "Contraseña por Defecto *", 
                    value="ISMR2024",
                    help="El usuario deberá cambiarla en su primer login"
                )
                es_admin_nuevo = st.checkbox("¿Es Administrador?", value=False)
            
            st.info("💡 El usuario deberá cambiar la contraseña en su primer acceso")
            
            submit_crear = st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary")
            
            if submit_crear:
                if nuevo_username and nuevo_nombre and password_default:
                    password_hash = hashlib.sha256(password_default.encode()).hexdigest()
                    
                    if crear_usuario(nuevo_username, password_hash, nuevo_nombre, es_admin_nuevo, debe_cambiar=True):
                        st.success(f"✅ Usuario '{nuevo_username}' creado exitosamente!")
                        st.info(f"""
                        **Datos del nuevo usuario:**
                        - Usuario: {nuevo_username}
                        - Contraseña temporal: {password_default}
                        - Nombre: {nuevo_nombre}
                        - Rol: {"Administrador" if es_admin_nuevo else "Analista"}
                        
                        ⚠️ Deberá cambiar la contraseña en su primer acceso
                        """)
                    else:
                        st.error("❌ Error: El usuario ya existe o hubo un problema al crear")
                else:
                    st.warning("⚠️ Completa todos los campos obligatorios")
    
    # TAB 2: VER USUARIOS
    with tab2:
        st.subheader("📋 Lista de Usuarios")
        
        usuarios = listar_usuarios()
        
        if usuarios:
            df = pd.DataFrame(usuarios)
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Usuarios", len(df))
            with col2:
                admins = df[df['es_admin'].str.upper() == 'TRUE'].shape[0] if 'es_admin' in df.columns else 0
                st.metric("Administradores", admins)
            with col3:
                analistas = len(df) - admins
                st.metric("Analistas", analistas)
            
            # Tabla
            st.dataframe(
                df[['username', 'nombre_completo', 'es_admin', 'debe_cambiar_password']], 
                use_container_width=True
            )
        else:
            st.info("📭 No hay usuarios registrados")
    
    # TAB 3: VER CONTRASEÑAS
    with tab3:
        st.subheader("🔑 Contraseñas Actuales")
        st.warning("⚠️ Esta información es sensible. Solo visible para administradores.")
        
        if st.checkbox("Mostrar contraseñas (hashes)", value=False):
            usuarios = listar_usuarios()
            
            if usuarios:
                for usuario in usuarios:
                    with st.expander(f"👤 {usuario['nombre_completo']} (@{usuario['username']})"):
                        st.code(usuario['password_hash'], language=None)
                        st.caption(f"Debe cambiar: {usuario.get('debe_cambiar_password', 'N/A')}")
            else:
                st.info("No hay usuarios")

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

st.set_page_config(
    page_title="Sistema ISMR",
    page_icon="📋",
    layout="centered"
)

# Inicializar session state
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "username" not in st.session_state:
    st.session_state.username = None
if "nombre_completo" not in st.session_state:
    st.session_state.nombre_completo = None
if "debe_cambiar_password" not in st.session_state:
    st.session_state.debe_cambiar_password = False
if "es_admin" not in st.session_state:
    st.session_state.es_admin = False

# ============================================================================
# CONEXIÓN A GOOGLE SHEETS (CASOS)
# ============================================================================

def conectar_google_sheets():
    """Conecta con Google Sheets de casos"""
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet_name = st.secrets.get("sheet_name", "ISMR_Casos")
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.sheet1
        
        headers = [
            "Timestamp", "OT-TE", "Edad", "Sexo", "Departamento", 
            "Municipio", "Solicitante", "Nivel de Riesgo", 
            "Observaciones", "Analista", "Usuario Analista"
        ]
        
        current_headers = worksheet.row_values(1)
        if not current_headers:
            worksheet.append_row(headers)
        elif current_headers != headers:
            worksheet.update('A1', [headers])
        
        return worksheet, spreadsheet.url
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        return None, None

# ============================================================================
# FORMULARIO
# ============================================================================

def formulario_casos():
    """Formulario de registro de casos"""
    
    # Header con info del usuario
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("📋 Registro de Casos ISMR")
    
    with col2:
        st.success(f"👤 {st.session_state.nombre_completo}")
        if st.button("🚪 Salir", use_container_width=True):
            logout()
    
    st.markdown("---")
    st.info(f"📝 Registrando como: **{st.session_state.nombre_completo}**")
    
    worksheet, sheet_url = conectar_google_sheets()
    
    if worksheet is None:
        st.error("⚠️ No se pudo conectar a Google Sheets")
        return
    
    # Formulario
    with st.form("formulario_casos", clear_on_submit=True):
        st.subheader("📝 Información del Caso")
        
        ot_te = st.text_input("OT-TE *", placeholder="Ejemplo: OT-2024-001")
        
        col1, col2 = st.columns(2)
        
        with col1:
            edad = st.number_input("Edad *", min_value=0, max_value=120, value=None)
            sexo = st.selectbox("Sexo *", ["Seleccione...", "Hombre", "Mujer", "Otro", "No Reporta"])
            departamento = st.text_input("Departamento *", placeholder="Ejemplo: Antioquia")
        
        with col2:
            municipio = st.text_input("Municipio *", placeholder="Ejemplo: Medellín")
            solicitante = st.selectbox("Entidad Solicitante *", ["Seleccione...", "ARN", "SESP", "OTRO"])
            nivel_riesgo = st.selectbox("Nivel de Riesgo *", ["Seleccione...", "EXTRAORDINARIO", "EXTREMO", "ORDINARIO"])
        
        observaciones = st.text_area("Observaciones (Opcional)", height=100)
        
        st.markdown("---")
        submitted = st.form_submit_button("✅ REGISTRAR CASO", use_container_width=True, type="primary")
        
        if submitted:
            errores = []
            
            if not ot_te or ot_te.strip() == "":
                errores.append("El campo OT-TE es obligatorio")
            if edad is None or edad == 0:
                errores.append("La edad es obligatoria")
            if sexo == "Seleccione...":
                errores.append("Debe seleccionar un sexo")
            if not departamento or departamento.strip() == "":
                errores.append("El departamento es obligatorio")
            if not municipio or municipio.strip() == "":
                errores.append("El municipio es obligatorio")
            if solicitante == "Seleccione...":
                errores.append("Debe seleccionar una entidad solicitante")
            if nivel_riesgo == "Seleccione...":
                errores.append("Debe seleccionar un nivel de riesgo")
            
            if errores:
                st.error("❌ Por favor corrija los siguientes errores:")
                for error in errores:
                    st.write(f"   • {error}")
            else:
                try:
                    todas_filas = worksheet.get_all_values()
                    ot_existentes = [fila[1] for fila in todas_filas[1:]]
                    
                    if ot_te.strip() in ot_existentes:
                        st.error(f"❌ El caso con OT-TE '{ot_te}' ya existe")
                    else:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        nueva_fila = [
                            timestamp, ot_te.strip(), edad, sexo,
                            departamento.strip(), municipio.strip(),
                            solicitante, nivel_riesgo,
                            observaciones.strip() if observaciones else "",
                            st.session_state.nombre_completo,
                            st.session_state.username
                        ]
                        
                        worksheet.append_row(nueva_fila)
                        st.success(f"✅ Caso {ot_te} registrado exitosamente!")
                        st.balloons()
                except Exception as e:
                    st.error(f"❌ Error al guardar: {str(e)}")
    
    st.markdown("---")
    st.caption("🔒 Datos almacenados de forma segura")

# ============================================================================
# PANEL DE VISUALIZACIÓN
# ============================================================================

def panel_visualizacion():
    """Panel de visualización de datos (solo admin)"""
    
    st.title("📊 Casos Registrados")
    st.markdown("---")
    
    worksheet, sheet_url = conectar_google_sheets()
    
    if worksheet is None:
        st.error("No se pudo conectar a Google Sheets")
        return
    
    if sheet_url:
        st.markdown(f"[📝 Abrir en Google Sheets]({sheet_url})")
    
    try:
        datos = worksheet.get_all_records()
        
        if datos:
            df = pd.DataFrame(datos)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Casos", len(df))
            with col2:
                st.metric("Departamentos", df['Departamento'].nunique() if 'Departamento' in df.columns else 0)
            with col3:
                st.metric("Municipios", df['Municipio'].nunique() if 'Municipio' in df.columns else 0)
            with col4:
                riesgo_alto = df['Nivel de Riesgo'].isin(['EXTREMO', 'EXTRAORDINARIO']).sum() if 'Nivel de Riesgo' in df.columns else 0
                st.metric("Riesgo Alto", riesgo_alto)
            
            st.subheader("🔍 Filtrar datos")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                depto = st.selectbox("Departamento", ["Todos"] + sorted(df['Departamento'].unique().tolist()) if 'Departamento' in df.columns else ["Todos"])
            with col2:
                riesgo = st.selectbox("Nivel de Riesgo", ["Todos"] + sorted(df['Nivel de Riesgo'].unique().tolist()) if 'Nivel de Riesgo' in df.columns else ["Todos"])
            with col3:
                analista_filtro = st.selectbox("Analista", ["Todos"] + sorted(df['Analista'].unique().tolist()) if 'Analista' in df.columns else ["Todos"])
            
            df_filtrado = df.copy()
            
            if depto != "Todos" and 'Departamento' in df.columns:
                df_filtrado = df_filtrado[df_filtrado['Departamento'] == depto]
            if riesgo != "Todos" and 'Nivel de Riesgo' in df.columns:
                df_filtrado = df_filtrado[df_filtrado['Nivel de Riesgo'] == riesgo]
            if analista_filtro != "Todos" and 'Analista' in df.columns:
                df_filtrado = df_filtrado[df_filtrado['Analista'] == analista_filtro]
            
            st.subheader(f"📋 Resultados ({len(df_filtrado)} casos)")
            st.dataframe(df_filtrado, use_container_width=True)
            
            csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"casos_ismr_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 No hay casos registrados")
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")

# ============================================================================
# MAIN
# ============================================================================

import time

def main():
    # Si no está autenticado → Login
    if not st.session_state.autenticado:
        login_page()
        return
    
    # Si debe cambiar contraseña → Forzar cambio
    if st.session_state.debe_cambiar_password:
        pantalla_cambiar_password()
        return
    
    # Si es admin → Menú completo
    if st.session_state.es_admin:
        st.sidebar.title("📊 Sistema ISMR")
        st.sidebar.success(f"👤 {st.session_state.nombre_completo}")
        st.sidebar.markdown("---")
        
        opcion = st.sidebar.radio(
            "Menú",
            ["📋 Formulario", "📊 Ver Datos", "👥 Gestionar Usuarios"]
        )
        
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()
        
        if opcion == "📋 Formulario":
            formulario_casos()
        elif opcion == "📊 Ver Datos":
            panel_visualizacion()
        else:
            panel_gestion_usuarios()
    
    # Si es analista → Solo formulario
    else:
        formulario_casos()

if __name__ == "__main__":
    main()