import streamlit as st
import services as srv

# Configuración global para todas las páginas
st.set_page_config(page_title="Mis Finanzas", layout="wide", page_icon="📊")

if 'usuario_autenticado' not in st.session_state:
    st.session_state.usuario_autenticado = False

def mostrar_login():
    st.title("🔐 Acceso Seguro")
    st.write("Por favor, inicia sesión para acceder a tus finanzas.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            email = st.text_input("Correo Electrónico")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit:
                try:
                    respuesta = srv.iniciar_sesion(email, password)
                    st.session_state.usuario_autenticado = True
                    st.success("Acceso concedido. Cargando...")
                    st.rerun() 
                except Exception as e:
                    st.error("Credenciales incorrectas. Intenta de nuevo.")

def cerrar_sesion():
    srv.cerrar_sesion()
    st.session_state.usuario_autenticado = False
    st.rerun()

# --- LÓGICA DE ENRUTAMIENTO ---
if not st.session_state.usuario_autenticado:
    mostrar_login()
else:
    st.sidebar.title("Navegación")
    st.sidebar.button("Cerrar Sesión", on_click=cerrar_sesion, use_container_width=True)
    st.sidebar.divider()
    
    # Definimos TODAS nuestras páginas
    pg_dashboard = st.Page("vistas/dashboard_global.py", title="Dashboard Principal", icon="🏠")
    pg_previsiones = st.Page("vistas/previsiones.py", title="Previsiones", icon="🔮")
    pg_ingresos = st.Page("vistas/ingresos.py", title="Ingresos", icon="💵")
    pg_gastos = st.Page("vistas/gastos.py", title="Gastos", icon="💸")
    pg_deudas = st.Page("vistas/deudas.py", title="Deudas", icon="💳")
    pg_ahorros = st.Page("vistas/ahorros.py", title="Ahorros", icon="💰")
    pg_inversiones = st.Page("vistas/inversiones.py", title="Inversiones", icon="📈")
    pg_recurrentes = st.Page("vistas/recurrentes.py", title="Recurrentes y Categorías", icon="🔁")

    # El orden aquí dicta cómo aparecen en el menú izquierdo (El primero es el Home)
    pg = st.navigation([
        pg_dashboard,
        pg_previsiones,
        pg_ingresos,
        pg_gastos,
        pg_deudas,
        pg_ahorros,
        pg_inversiones,
        pg_recurrentes,
    ])
    pg.run()