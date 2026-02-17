import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import hashlib
import time

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

st.set_page_config(
    page_title="Sistema ISMR",
    page_icon="📋",
    layout="centered"
)

# Inicializar session state
defaults = {
    "autenticado": False,
    "username": None,
    "nombre_completo": None,
    "debe_cambiar_password": False,
    "es_admin": False,
    "vista": None  # None | "individual" | "colectivo"
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================================================
# CSS - PANTALLA DE SELECCIÓN
# ============================================================================

def inyectar_css_selector():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

        /* Reset y base */
        .stApp {
            background: #0A0A0F;
        }

        /* Ocultar elementos por defecto de Streamlit en pantalla selector */
        #MainMenu, footer, header { visibility: hidden; }

        /* Contenedor principal del selector */
        .selector-wrapper {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            font-family: 'DM Sans', sans-serif;
            background: #0A0A0F;
        }

        /* Header del selector */
        .selector-header {
            text-align: center;
            margin-bottom: 48px;
        }

        .selector-header .greeting {
            font-family: 'DM Sans', sans-serif;
            font-weight: 300;
            font-size: 14px;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 8px;
        }

        .selector-header .user-name {
            font-family: 'Bebas Neue', sans-serif;
            font-size: clamp(28px, 5vw, 42px);
            letter-spacing: 3px;
            color: #F0F0F0;
            margin-bottom: 4px;
        }

        .selector-header .subtitle {
            font-size: 13px;
            color: #555;
            letter-spacing: 1px;
        }

        /* Grid de botones */
        .selector-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            width: 100%;
            max-width: 860px;
        }

        /* Cada tarjeta de selección */
        .selector-card {
            position: relative;
            border-radius: 4px;
            padding: 60px 40px;
            cursor: pointer;
            overflow: hidden;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            text-decoration: none;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-end;
            min-height: 340px;
            border: 1px solid transparent;
        }

        .selector-card:hover {
            transform: translateY(-4px);
        }

        /* Tarjeta INDIVIDUAL */
        .card-individual {
            background: linear-gradient(145deg, #1A1A2E 0%, #16213E 50%, #0F3460 100%);
            border-color: rgba(79, 139, 255, 0.15);
            box-shadow: 0 0 0 0 rgba(79, 139, 255, 0);
        }

        .card-individual:hover {
            box-shadow: 0 20px 60px rgba(79, 139, 255, 0.15),
                        inset 0 0 80px rgba(79, 139, 255, 0.05);
            border-color: rgba(79, 139, 255, 0.4);
        }

        .card-individual .card-accent {
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, #4F8BFF, transparent);
        }

        .card-individual .card-number {
            color: rgba(79, 139, 255, 0.25);
        }

        .card-individual .card-icon-bg {
            background: rgba(79, 139, 255, 0.08);
            border: 1px solid rgba(79, 139, 255, 0.15);
        }

        .card-individual .card-icon {
            color: #4F8BFF;
        }

        .card-individual .card-title {
            color: #E8EEFF;
        }

        .card-individual .card-desc {
            color: rgba(200, 210, 255, 0.45);
        }

        .card-individual .card-arrow {
            color: #4F8BFF;
            border-color: rgba(79, 139, 255, 0.3);
        }

        /* Tarjeta COLECTIVO */
        .card-colectivo {
            background: linear-gradient(145deg, #1A1A1A 0%, #1E2A1E 50%, #0A3D0A 100%);
            border-color: rgba(74, 222, 128, 0.12);
            box-shadow: 0 0 0 0 rgba(74, 222, 128, 0);
        }

        .card-colectivo:hover {
            box-shadow: 0 20px 60px rgba(74, 222, 128, 0.12),
                        inset 0 0 80px rgba(74, 222, 128, 0.04);
            border-color: rgba(74, 222, 128, 0.35);
        }

        .card-colectivo .card-accent {
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, #4ADE80, transparent);
        }

        .card-colectivo .card-number {
            color: rgba(74, 222, 128, 0.2);
        }

        .card-colectivo .card-icon-bg {
            background: rgba(74, 222, 128, 0.07);
            border: 1px solid rgba(74, 222, 128, 0.15);
        }

        .card-colectivo .card-icon {
            color: #4ADE80;
        }

        .card-colectivo .card-title {
            color: #E8FFE8;
        }

        .card-colectivo .card-desc {
            color: rgba(200, 255, 200, 0.4);
        }

        .card-colectivo .card-arrow {
            color: #4ADE80;
            border-color: rgba(74, 222, 128, 0.3);
        }

        /* Elementos internos de cada card */
        .card-number {
            position: absolute;
            top: 28px;
            right: 32px;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 80px;
            line-height: 1;
            letter-spacing: -2px;
            pointer-events: none;
        }

        .card-icon-bg {
            width: 52px;
            height: 52px;
            border-radius: 3px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 28px;
        }

        .card-icon {
            font-size: 22px;
        }

        .card-title {
            font-family: 'Bebas Neue', sans-serif;
            font-size: clamp(26px, 3.5vw, 34px);
            letter-spacing: 3px;
            margin-bottom: 10px;
            line-height: 1;
        }

        .card-desc {
            font-size: 12px;
            letter-spacing: 0.5px;
            line-height: 1.6;
            margin-bottom: 32px;
            font-weight: 300;
        }

        .card-arrow {
            font-size: 11px;
            letter-spacing: 3px;
            text-transform: uppercase;
            padding: 8px 18px;
            border-radius: 2px;
            border: 1px solid;
        }

        /* Footer del selector */
        .selector-footer {
            margin-top: 40px;
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logout-btn-wrapper button {
            background: transparent !important;
            border: 1px solid #333 !important;
            color: #555 !important;
            font-size: 11px !important;
            letter-spacing: 2px !important;
            text-transform: uppercase !important;
            padding: 8px 20px !important;
            border-radius: 2px !important;
            transition: all 0.2s !important;
        }

        .logout-btn-wrapper button:hover {
            border-color: #666 !important;
            color: #999 !important;
        }

        /* Botones Streamlit para las tarjetas */
        .btn-individual > button,
        .btn-colectivo > button {
            width: 100% !important;
            min-height: 340px !important;
            border-radius: 4px !important;
            border: 1px solid !important;
            transition: all 0.3s ease !important;
            font-family: 'Bebas Neue', sans-serif !important;
            letter-spacing: 3px !important;
            font-size: 28px !important;
        }

        .btn-individual > button {
            background: linear-gradient(145deg, #1A1A2E 0%, #16213E 50%, #0F3460 100%) !important;
            border-color: rgba(79, 139, 255, 0.3) !important;
            color: #E8EEFF !important;
        }

        .btn-individual > button:hover {
            border-color: rgba(79, 139, 255, 0.7) !important;
            box-shadow: 0 20px 60px rgba(79, 139, 255, 0.2) !important;
            transform: translateY(-4px) !important;
        }

        .btn-colectivo > button {
            background: linear-gradient(145deg, #1A1A1A 0%, #1E2A1E 50%, #0A3D0A 100%) !important;
            border-color: rgba(74, 222, 128, 0.25) !important;
            color: #E8FFE8 !important;
        }

        .btn-colectivo > button:hover {
            border-color: rgba(74, 222, 128, 0.6) !important;
            box-shadow: 0 20px 60px rgba(74, 222, 128, 0.15) !important;
            transform: translateY(-4px) !important;
        }

        /* Estilos para los formularios */
        .form-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }

        .form-badge-individual {
            background: rgba(79, 139, 255, 0.12);
            border: 1px solid rgba(79, 139, 255, 0.3);
            color: #4F8BFF;
            font-size: 10px;
            letter-spacing: 2px;
            text-transform: uppercase;
            padding: 4px 10px;
            border-radius: 2px;
            font-family: 'DM Sans', sans-serif;
        }

        .form-badge-colectivo {
            background: rgba(74, 222, 128, 0.1);
            border: 1px solid rgba(74, 222, 128, 0.3);
            color: #4ADE80;
            font-size: 10px;
            letter-spacing: 2px;
            text-transform: uppercase;
            padding: 4px 10px;
            border-radius: 2px;
            font-family: 'DM Sans', sans-serif;
        }

        /* Botón volver */
        .stButton > button[kind="secondary"] {
            background: transparent !important;
            border: 1px solid #333 !important;
            color: #666 !important;
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# GOOGLE SHEETS - USUARIOS
# ============================================================================

def conectar_sheet_usuarios():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet_name = st.secrets.get("sheet_usuarios", "ISMR_Usuarios")

        try:
            spreadsheet = client.open(sheet_name)
        except:
            spreadsheet = client.create(sheet_name)
            spreadsheet.share(credentials_dict["client_email"], perm_type='user', role='writer')

        worksheet = spreadsheet.sheet1
        headers = ["username", "password_hash", "nombre_completo", "es_admin", "debe_cambiar_password"]
        current_headers = worksheet.row_values(1)
        if not current_headers:
            worksheet.append_row(headers)
        return worksheet
    except Exception as e:
        st.error(f"Error al conectar sheet de usuarios: {str(e)}")
        return None

def obtener_usuario(username):
    worksheet = conectar_sheet_usuarios()
    if not worksheet:
        return None
    try:
        datos = worksheet.get_all_records()
        for usuario in datos:
            if usuario.get('username') == username:
                return usuario
        return None
    except:
        return None

def actualizar_password(username, nuevo_password_hash, debe_cambiar=False):
    worksheet = conectar_sheet_usuarios()
    if not worksheet:
        return False
    try:
        datos = worksheet.get_all_values()
        for idx, fila in enumerate(datos[1:], start=2):
            if fila[0] == username:
                worksheet.update_cell(idx, 2, nuevo_password_hash)
                worksheet.update_cell(idx, 5, str(debe_cambiar).upper())
                return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar contraseña: {str(e)}")
        return False

def crear_usuario(username, password_hash, nombre_completo, es_admin=False, debe_cambiar=True):
    worksheet = conectar_sheet_usuarios()
    if not worksheet:
        return False
    try:
        if obtener_usuario(username):
            return False
        nueva_fila = [username, password_hash, nombre_completo,
                      str(es_admin).upper(), str(debe_cambiar).upper()]
        worksheet.append_row(nueva_fila)
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {str(e)}")
        return False

def listar_usuarios():
    worksheet = conectar_sheet_usuarios()
    if not worksheet:
        return []
    try:
        return worksheet.get_all_records()
    except:
        return []

# ============================================================================
# GOOGLE SHEETS - CASOS (Individual y Colectivo)
# ============================================================================

def conectar_sheet_casos(tipo="individual"):
    """
    Conecta a la hoja de casos según el tipo.
    tipo = "individual" → hoja 'Individual'
    tipo = "colectivo"  → hoja 'Colectivo'
    Ambas hojas están en el mismo Google Spreadsheet.
    """
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)

        # Mismo spreadsheet para ambos tipos
        sheet_name = st.secrets.get("sheet_name", "ISMR_Casos")
        spreadsheet = client.open(sheet_name)

        # Nombre de la pestaña según el tipo
        tab_name = "Individual" if tipo == "individual" else "Colectivo"

        # Buscar o crear la pestaña
        try:
            worksheet = spreadsheet.worksheet(tab_name)
        except:
            worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="20")

        # Encabezados
        headers = [
            "Timestamp", "OT-TE", "Edad", "Sexo",
            "Departamento", "Municipio", "Solicitante",
            "Nivel de Riesgo", "Observaciones", "Analista", "Usuario Analista"
        ]

        current_headers = worksheet.row_values(1)
        if not current_headers:
            worksheet.append_row(headers)
        elif current_headers != headers:
            worksheet.update('A1', [headers])

        return worksheet, spreadsheet.url

    except Exception as e:
        st.error(f"Error al conectar Google Sheets ({tipo}): {str(e)}")
        return None, None

# ============================================================================
# AUTENTICACIÓN
# ============================================================================

def verificar_credenciales(username, password):
    usuario = obtener_usuario(username)
    if not usuario:
        return False, None, False, False
    try:
        if 'password_hash' not in usuario:
            st.error("❌ La hoja de usuarios no tiene el formato correcto. Verifica los encabezados.")
            return False, None, False, False
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash == usuario['password_hash']:
            debe_cambiar = str(usuario.get('debe_cambiar_password', 'FALSE')).upper() == 'TRUE'
            es_admin = str(usuario.get('es_admin', 'FALSE')).upper() == 'TRUE'
            nombre = usuario.get('nombre_completo', username)
            return True, nombre, debe_cambiar, es_admin
        return False, None, False, False
    except Exception as e:
        st.error(f"❌ Error en verificación: {str(e)}")
        return False, None, False, False

def logout():
    for key in defaults:
        st.session_state[key] = defaults[key]
    st.rerun()

# ============================================================================
# PANTALLA: LOGIN
# ============================================================================

def login_page():
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
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Por favor completa todos los campos")

    st.markdown("---")
    st.caption("🔒 Si tienes problemas, contacta al administrador")

# ============================================================================
# PANTALLA: CAMBIO OBLIGATORIO DE CONTRASEÑA
# ============================================================================

def pantalla_cambiar_password():
    st.title("🔐 Cambio de Contraseña Obligatorio")
    st.markdown("---")
    st.warning("⚠️ Debes cambiar tu contraseña por defecto antes de continuar")
    st.info(f"👤 Usuario: **{st.session_state.username}**")

    with st.form("cambiar_password_form"):
        nueva_password = st.text_input("Nueva Contraseña", type="password", help="Mínimo 8 caracteres")
        confirmar_password = st.text_input("Confirmar Nueva Contraseña", type="password")
        st.caption("💡 Usa una contraseña segura con letras, números y símbolos")
        submit = st.form_submit_button("✅ Cambiar Contraseña", use_container_width=True, type="primary")

        if submit:
            errores = []
            if not nueva_password:
                errores.append("La contraseña no puede estar vacía")
            elif len(nueva_password) < 8:
                errores.append("La contraseña debe tener mínimo 8 caracteres")
            if nueva_password != confirmar_password:
                errores.append("Las contraseñas no coinciden")

            if errores:
                for e in errores:
                    st.error(f"❌ {e}")
            else:
                nuevo_hash = hashlib.sha256(nueva_password.encode()).hexdigest()
                if actualizar_password(st.session_state.username, nuevo_hash, debe_cambiar=False):
                    st.session_state.debe_cambiar_password = False
                    st.success("✅ ¡Contraseña actualizada!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Error al actualizar. Intenta de nuevo.")

# ============================================================================
# PANTALLA: SELECTOR (Individual / Colectivo)
# ============================================================================

def pantalla_selector():
    inyectar_css_selector()

    nombre = st.session_state.nombre_completo or "Analista"
    nombre_corto = nombre.split()[0] if nombre else "Analista"

    # Header
    st.markdown(f"""
    <div style="text-align:center; margin-bottom: 48px; margin-top: 20px;">
        <p style="font-family:'DM Sans',sans-serif; font-weight:300; font-size:13px;
                  letter-spacing:4px; text-transform:uppercase; color:#555; margin-bottom:6px;">
            BIENVENIDO
        </p>
        <p style="font-family:'Bebas Neue',sans-serif; font-size:clamp(28px,5vw,40px);
                  letter-spacing:3px; color:#F0F0F0; margin:0;">
            {nombre_corto}
        </p>
        <p style="font-size:12px; color:#444; letter-spacing:1px; margin-top:6px;">
            SELECCIONA EL TIPO DE FORMULARIO
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Botones en dos columnas
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown("""
        <div style="text-align:center; margin-bottom:12px;">
            <span style="font-size:32px;">👤</span>
            <p style="font-family:'DM Sans',sans-serif; font-size:11px; letter-spacing:3px;
                      color:rgba(79,139,255,0.6); text-transform:uppercase; margin:6px 0 2px;">
                REGISTRO
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="btn-individual">', unsafe_allow_html=True)
        if st.button(
            "FORMULARIO\nINDIVIDUAL",
            key="btn_individual",
            use_container_width=True,
            help="Registrar un caso individual"
        ):
            st.session_state.vista = "individual"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <p style="text-align:center; font-size:11px; color:#444;
                  letter-spacing:0.5px; margin-top:10px;">
            Un caso por registro
        </p>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="text-align:center; margin-bottom:12px;">
            <span style="font-size:32px;">👥</span>
            <p style="font-family:'DM Sans',sans-serif; font-size:11px; letter-spacing:3px;
                      color:rgba(74,222,128,0.6); text-transform:uppercase; margin:6px 0 2px;">
                REGISTRO
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="btn-colectivo">', unsafe_allow_html=True)
        if st.button(
            "FORMULARIO\nCOLECTIVO",
            key="btn_colectivo",
            use_container_width=True,
            help="Registrar un caso colectivo"
        ):
            st.session_state.vista = "colectivo"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <p style="text-align:center; font-size:11px; color:#444;
                  letter-spacing:0.5px; margin-top:10px;">
            Múltiples personas afectadas
        </p>
        """, unsafe_allow_html=True)

    # Botón cerrar sesión
    st.markdown("<br>", unsafe_allow_html=True)
    col_space1, col_logout, col_space2 = st.columns([2, 1, 2])
    with col_logout:
        if st.button("🚪 Cerrar sesión", use_container_width=True, type="secondary"):
            logout()


# ============================================================================
# FORMULARIO GENÉRICO (Individual o Colectivo)
# ============================================================================

def formulario_casos(tipo="individual"):
    """Formulario de registro — funciona para individual y colectivo"""

    es_individual = tipo == "individual"
    color = "#4F8BFF" if es_individual else "#4ADE80"
    icono = "👤" if es_individual else "👥"
    label_badge = "INDIVIDUAL" if es_individual else "COLECTIVO"
    titulo = "Formulario Individual" if es_individual else "Formulario Colectivo"

    worksheet, sheet_url = conectar_sheet_casos(tipo)

    if worksheet is None:
        st.error("⚠️ No se pudo conectar a Google Sheets")
        return

    # Header
    col_back, col_title = st.columns([1, 4])

    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista = None
            st.rerun()

    with col_title:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
            <span style="font-size:22px;">{icono}</span>
            <span style="font-size:22px; font-weight:600; color:#F0F0F0;">{titulo}</span>
            <span style="background:rgba({('79,139,255' if es_individual else '74,222,128')},0.1);
                         border:1px solid rgba({('79,139,255' if es_individual else '74,222,128')},0.3);
                         color:{color}; font-size:10px; letter-spacing:2px;
                         padding:3px 9px; border-radius:2px;">
                {label_badge}
            </span>
        </div>
        <p style="font-size:12px; color:#555; margin:0;">
            Registrando como: <strong style="color:#888;">{st.session_state.nombre_completo}</strong>
        </p>
        """, unsafe_allow_html=True)

    st.markdown("---")

    with st.form(f"formulario_{tipo}", clear_on_submit=True):
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

        btn_label = f"✅ REGISTRAR CASO {label_badge}"
        submitted = st.form_submit_button(btn_label, use_container_width=True, type="primary")

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
                for e in errores:
                    st.write(f"   • {e}")
            else:
                try:
                    todas_filas = worksheet.get_all_values()
                    ot_existentes = [fila[1] for fila in todas_filas[1:]]

                    if ot_te.strip() in ot_existentes:
                        st.error(f"❌ El caso '{ot_te}' ya existe en esta hoja")
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
                        st.success(f"✅ Caso {ot_te} registrado en {label_badge}!")
                        st.balloons()
                except Exception as e:
                    st.error(f"❌ Error al guardar: {str(e)}")

    st.markdown("---")
    st.caption(f"🔒 Los datos se guardan en la hoja '{label_badge.capitalize()}' de Google Sheets")


# ============================================================================
# PANEL VISUALIZACIÓN (Admin)
# ============================================================================

def panel_visualizacion():
    st.title("📊 Casos Registrados")
    st.markdown("---")

    tab_ind, tab_col = st.tabs(["👤 Individual", "👥 Colectivo"])

    for tab, tipo in [(tab_ind, "individual"), (tab_col, "colectivo")]:
        with tab:
            worksheet, sheet_url = conectar_sheet_casos(tipo)
            if worksheet is None:
                st.error(f"No se pudo conectar a la hoja {tipo}")
                continue

            if sheet_url:
                st.markdown(f"[📝 Abrir en Google Sheets]({sheet_url})")

            try:
                datos = worksheet.get_all_records()
                if datos:
                    df = pd.DataFrame(datos)

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Casos", len(df))
                    c2.metric("Departamentos", df['Departamento'].nunique() if 'Departamento' in df.columns else 0)
                    c3.metric("Municipios", df['Municipio'].nunique() if 'Municipio' in df.columns else 0)
                    riesgo_alto = df['Nivel de Riesgo'].isin(['EXTREMO', 'EXTRAORDINARIO']).sum() if 'Nivel de Riesgo' in df.columns else 0
                    c4.metric("Riesgo Alto", riesgo_alto)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        depto = st.selectbox("Departamento", ["Todos"] + sorted(df['Departamento'].unique().tolist()) if 'Departamento' in df.columns else ["Todos"], key=f"depto_{tipo}")
                    with col2:
                        riesgo = st.selectbox("Nivel de Riesgo", ["Todos"] + sorted(df['Nivel de Riesgo'].unique().tolist()) if 'Nivel de Riesgo' in df.columns else ["Todos"], key=f"riesgo_{tipo}")
                    with col3:
                        analista_f = st.selectbox("Analista", ["Todos"] + sorted(df['Analista'].unique().tolist()) if 'Analista' in df.columns else ["Todos"], key=f"analista_{tipo}")

                    df_f = df.copy()
                    if depto != "Todos" and 'Departamento' in df.columns:
                        df_f = df_f[df_f['Departamento'] == depto]
                    if riesgo != "Todos" and 'Nivel de Riesgo' in df.columns:
                        df_f = df_f[df_f['Nivel de Riesgo'] == riesgo]
                    if analista_f != "Todos" and 'Analista' in df.columns:
                        df_f = df_f[df_f['Analista'] == analista_f]

                    st.subheader(f"📋 Resultados ({len(df_f)} casos)")
                    st.dataframe(df_f, use_container_width=True)

                    csv = df_f.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        f"📥 Descargar CSV {tipo}",
                        data=csv,
                        file_name=f"casos_{tipo}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        key=f"download_{tipo}"
                    )
                else:
                    st.info(f"📭 No hay casos {tipo}s registrados")
            except Exception as e:
                st.error(f"Error al cargar datos: {str(e)}")

# ============================================================================
# PANEL GESTIÓN USUARIOS (Admin)
# ============================================================================

def panel_gestion_usuarios():
    st.title("👥 Gestión de Usuarios")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["➕ Crear Usuario", "📋 Ver Usuarios", "🔑 Ver Hashes"])

    with tab1:
        st.subheader("➕ Crear Nuevo Usuario")
        with st.form("crear_usuario_form"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_username = st.text_input("Usuario *", placeholder="nombre.apellido")
                nuevo_nombre = st.text_input("Nombre Completo *", placeholder="Juan Pérez")
            with col2:
                password_default = st.text_input("Contraseña por Defecto *", value="ISMR2024")
                es_admin_nuevo = st.checkbox("¿Es Administrador?", value=False)

            st.info("💡 El usuario deberá cambiar la contraseña en su primer acceso")
            submit_crear = st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary")

            if submit_crear:
                if nuevo_username and nuevo_nombre and password_default:
                    password_hash = hashlib.sha256(password_default.encode()).hexdigest()
                    if crear_usuario(nuevo_username, password_hash, nuevo_nombre, es_admin_nuevo, debe_cambiar=True):
                        st.success(f"✅ Usuario '{nuevo_username}' creado exitosamente!")
                        st.info(f"Usuario: **{nuevo_username}** | Contraseña temporal: **{password_default}**")
                    else:
                        st.error("❌ El usuario ya existe o hubo un problema al crearlo")
                else:
                    st.warning("⚠️ Completa todos los campos")

    with tab2:
        st.subheader("📋 Lista de Usuarios")
        usuarios = listar_usuarios()
        if usuarios:
            df = pd.DataFrame(usuarios)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(df))
            admins = df[df['es_admin'].astype(str).str.upper() == 'TRUE'].shape[0] if 'es_admin' in df.columns else 0
            c2.metric("Admins", admins)
            c3.metric("Analistas", len(df) - admins)
            st.dataframe(df[['username', 'nombre_completo', 'es_admin', 'debe_cambiar_password']], use_container_width=True)
        else:
            st.info("📭 No hay usuarios")

    with tab3:
        st.subheader("🔑 Hashes de Contraseñas")
        st.warning("⚠️ Información sensible — solo visible para administradores")
        if st.checkbox("Mostrar hashes"):
            usuarios = listar_usuarios()
            for u in usuarios:
                with st.expander(f"👤 {u.get('nombre_completo','?')} (@{u.get('username','?')})"):
                    st.code(u.get('password_hash', 'N/A'), language=None)
                    st.caption(f"Debe cambiar: {u.get('debe_cambiar_password', 'N/A')}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    # 1. No autenticado → Login
    if not st.session_state.autenticado:
        login_page()
        return

    # 2. Debe cambiar contraseña → Forzar
    if st.session_state.debe_cambiar_password:
        pantalla_cambiar_password()
        return

    # 3. Admin → sidebar con menú completo
    if st.session_state.es_admin:
        st.sidebar.title("📊 Sistema ISMR")
        st.sidebar.success(f"👤 {st.session_state.nombre_completo}")
        st.sidebar.markdown("---")

        opcion = st.sidebar.radio(
            "Menú",
            ["🏠 Inicio", "👤 Individual", "👥 Colectivo", "📊 Ver Datos", "👥 Gestionar Usuarios"]
        )

        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()

        if opcion == "🏠 Inicio":
            pantalla_selector()
        elif opcion == "👤 Individual":
            formulario_casos("individual")
        elif opcion == "👥 Colectivo":
            formulario_casos("colectivo")
        elif opcion == "📊 Ver Datos":
            panel_visualizacion()
        else:
            panel_gestion_usuarios()
        return

    # 4. Analista → Selector o formulario
    vista = st.session_state.vista

    if vista is None:
        pantalla_selector()
    elif vista == "individual":
        formulario_casos("individual")
    elif vista == "colectivo":
        formulario_casos("colectivo")


if __name__ == "__main__":
    main()
