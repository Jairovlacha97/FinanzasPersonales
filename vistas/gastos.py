import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv
from models import Gasto

# --- INICIALIZACIÓN DE VARIABLES (Específicas de esta vista) ---
if 'limite_variables' not in st.session_state:
    st.session_state.limite_variables = 1500000.0
if 'limite_facturas' not in st.session_state:
    st.session_state.limite_facturas = 1000000.0
if 'limite_transporte' not in st.session_state:
    st.session_state.limite_transporte = 300000.0
if 'limite_gatos' not in st.session_state:
    st.session_state.limite_gatos = 350000.0

st.title("💸 Registro de Gastos - Mes Actual")

# --- BARRA LATERAL (Presupuestos) ---
st.sidebar.header("⚙️ Presupuestos Mensuales")
st.session_state.limite_variables = st.sidebar.number_input("Gastos Variables ($)", value=st.session_state.limite_variables, step=100000.0)
st.session_state.limite_facturas = st.sidebar.number_input("Facturas ($)", value=st.session_state.limite_facturas, step=50000.0)
st.session_state.limite_transporte = st.sidebar.number_input("Transporte ($)", value=st.session_state.limite_transporte, step=50000.0)
st.session_state.limite_gatos = st.sidebar.number_input("Gatos ($)", value=st.session_state.limite_gatos, step=50000.0)

# --- CARGA DE DATOS MAESTROS Y MAPEO ---
df_cuentas_maestras = srv.obtener_cuentas()
if not df_cuentas_maestras.empty:
    mapa_cuentas = {f"{row['nombre']} ({row['tipo']})": row['nombre'] for _, row in df_cuentas_maestras.iterrows()}
else:
    mapa_cuentas = {"Efectivo (Débito)": "Efectivo"} 
lista_opciones_tarjetas = list(mapa_cuentas.keys())

# --- FORMULARIO DE REGISTRO ---
st.header("📝 Registrar Nuevo Gasto")

with st.form("form_registro", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_input = st.date_input("Fecha", datetime.date.today())
        categoria_input = st.selectbox(
            "Categoría", 
            [
                "Accesorios", "Alcohol","Chapamovil", "Cuota Rappi", "Deporte", 
                "Entretenimiento", "Facturas", "Gasolina", "Gatos", 
                "Mercado", "Negocios", "Parqueadero", "Regalos", 
                "Restaurantes", "Ropa", "Salud", "Snacks", 
                "Suscripciones", "Transporte", "Varios", "Viajes", 
                "Videojuegos"
            ]
        )
        
    with col2:
        historial_locales = srv.obtener_descripciones_unicas()
        opciones_local = ["➕ Escribir nuevo local..."] + historial_locales
        local_seleccionado = st.selectbox("Descripción / Local", opciones_local)
        local_nuevo = st.text_input("Nombre del nuevo local (Si elegiste ➕)")
        
    with col3:
        valor_input = st.number_input("Valor ($)", min_value=0.0, step=5000.0)
        tarjeta_input_display = st.selectbox("Medio de pago", lista_opciones_tarjetas)
        
    submit_btn = st.form_submit_button("Registrar Gasto")

    if submit_btn:
        descripcion_final = local_nuevo if local_seleccionado == "➕ Escribir nuevo local..." else local_seleccionado

        if valor_input > 0 and descripcion_final.strip() != "":
            tarjeta_real = mapa_cuentas[tarjeta_input_display]

            nuevo_gasto = Gasto(
                fecha=fecha_input,
                categoria=categoria_input,
                descripcion=descripcion_final,
                valor=valor_input,
                tarjeta=tarjeta_real
            )
            
            srv.registrar_gasto(nuevo_gasto)
            st.success("✅ Gasto registrado en Supabase correctamente.")
            st.rerun() 
        else:
            st.warning("⚠️ Debes ingresar una descripción válida y un valor mayor a 0.")

st.divider()

# --- DATOS Y CÁLCULOS DEL MES ---
st.header(f"📊 Resumen de {datetime.date.today().strftime('%B %Y').capitalize()}")

df_mes = srv.obtener_gastos_mes_actual()

total_general = df_mes['Valor'].sum() if not df_mes.empty else 0

if not df_mes.empty:
    total_facturas = df_mes[df_mes['Categoría'] == 'Facturas']['Valor'].sum()
    total_transporte = df_mes[df_mes['Categoría'] == 'Transporte']['Valor'].sum()
    total_gatos = df_mes[df_mes['Categoría'] == 'Gatos']['Valor'].sum()
    
    categorias_excluidas = ['Facturas', 'Transporte', 'Gatos']
    total_variables = df_mes[~df_mes['Categoría'].isin(categorias_excluidas)]['Valor'].sum()
else:
    total_facturas = total_transporte = total_gatos = total_variables = 0

st.metric("Total Gastado en el Mes (Consolidado)", f"${total_general:,.0f}")
st.write("")

# --- SECCIÓN DE PRESUPUESTOS (SOBRES) ---
st.subheader("🎯 Control por Presupuestos")
col_v, col_f, col_t, col_g = st.columns(4)

def renderizar_tarjeta_presupuesto(columna, titulo, total_gastado, limite):
    with columna:
        st.markdown(f"**{titulo}**")
        saldo = limite - total_gastado
        st.write(f"**Presupuesto:** ${limite:,.0f}")
        st.write(f"**Gastado:** ${total_gastado:,.0f}")
        
        if saldo >= 0:
            st.success(f"Disponible: ${saldo:,.0f}")
        else:
            st.error(f"Sobregiro: -${abs(saldo):,.0f}")
        
        if limite > 0:
            st.progress(min(total_gastado / limite, 1.0))

renderizar_tarjeta_presupuesto(col_v, "🛍️ Gastos Variables", total_variables, st.session_state.limite_variables)
renderizar_tarjeta_presupuesto(col_f, "🧾 Facturas", total_facturas, st.session_state.limite_facturas)
renderizar_tarjeta_presupuesto(col_t, "🚗 Transporte", total_transporte, st.session_state.limite_transporte)
renderizar_tarjeta_presupuesto(col_g, "🐾 Gatos", total_gatos, st.session_state.limite_gatos)

st.divider()

# --- ANÁLISIS DE MEDIOS DE PAGO (ACTUALIZADO) ---
if not df_mes.empty and not df_cuentas_maestras.empty:
    st.divider()
    st.subheader("💳 Detalle por Medio de Pago y Presupuesto")
    
    # 1. Cruzamos datos y categorizamos el presupuesto
    df_merge = df_mes.merge(df_cuentas_maestras, left_on='Tarjeta', right_on='nombre', how='left')
    
    def asignar_presupuesto(cat):
        if cat in ['Facturas', 'Transporte', 'Gatos']:
            return cat
        return 'Variables'
        
    df_merge['Presupuesto'] = df_merge['Categoría'].apply(asignar_presupuesto)

    # 2. Creamos dos columnas: una para Crédito y otra para Débito
    col_cred, col_deb = st.columns(2)

    with col_cred:
        st.markdown("#### 🔴 Tarjetas de Crédito (Deuda)")
        df_c = df_merge[df_merge['tipo'] == 'Credito']
        
        if not df_c.empty:
            # Agrupamos por Tarjeta y Presupuesto
            resumen_c = df_c.groupby(['Tarjeta', 'Presupuesto'])['Valor'].sum().reset_index()
            
            # Iteramos por cada tarjeta para mostrar su desglose individual
            for tarjeta in resumen_c['Tarjeta'].unique():
                df_tarjeta = resumen_c[resumen_c['Tarjeta'] == tarjeta]
                total_t = df_tarjeta['Valor'].sum()
                
                with st.expander(f"**{tarjeta}**: ${total_t:,.0f}", expanded=True):
                    # Mostramos una pequeña tabla con el desglose por presupuesto
                    st.dataframe(
                        df_tarjeta[['Presupuesto', 'Valor']].rename(columns={'Valor': 'Monto'}),
                        use_container_width=True,
                        hide_index=True
                    )
        else:
            st.info("No hay gastos a crédito registrados.")

    with col_deb:
        st.markdown("#### 🔵 Cuentas de Débito / Efectivo")
        df_d = df_merge[df_merge['tipo'] == 'Debito']
        
        if not df_d.empty:
            # Agrupamos por Cuenta y Presupuesto
            resumen_d = df_d.groupby(['Tarjeta', 'Presupuesto'])['Valor'].sum().reset_index()
            
            for cuenta in resumen_d['Tarjeta'].unique():
                df_cuenta = resumen_d[resumen_d['Tarjeta'] == cuenta]
                total_c = df_cuenta['Valor'].sum()
                
                with st.expander(f"**{cuenta}**: ${total_c:,.0f}", expanded=False):
                    st.dataframe(
                        df_cuenta[['Presupuesto', 'Valor']].rename(columns={'Valor': 'Monto'}),
                        use_container_width=True,
                        hide_index=True
                    )
        else:
            st.info("No hay gastos a débito registrados.")

st.divider()

# --- GRÁFICOS Y TABLA DE HISTORIAL ---
col_grafico, col_tabla = st.columns([1, 1])

with col_grafico:
    st.subheader("📈 Gastos por Categoría")
    if not df_mes.empty:
        df_agrupado_cat = df_mes.groupby('Categoría')['Valor'].sum().reset_index()
        
        base_cat = alt.Chart(df_agrupado_cat).encode(
            x=alt.X('Valor:Q', title='', axis=None),
            y=alt.Y('Categoría:N', sort='-x', title='')
        )
        barras_cat = base_cat.mark_bar()
        texto_cat = base_cat.mark_text(
            align='left',
            baseline='middle',
            dx=3
        ).encode(
            text=alt.Text('Valor:Q', format='$,.0f')
        )
        st.altair_chart(barras_cat + texto_cat, use_container_width=True)
        
        st.subheader("💳 Gastos por Cuenta")
        df_agrupado_cuenta = df_mes.groupby('Tarjeta')['Valor'].sum().reset_index()
        
        base_cta = alt.Chart(df_agrupado_cuenta).encode(
            x=alt.X('Valor:Q', title='', axis=None),
            y=alt.Y('Tarjeta:N', sort='-x', title='')
        )
        barras_cta = base_cta.mark_bar(color='#ff7f0e')
        texto_cta = base_cta.mark_text(
            align='left',
            baseline='middle',
            dx=3
        ).encode(
            text=alt.Text('Valor:Q', format='$,.0f')
        )
        st.altair_chart(barras_cta + texto_cta, use_container_width=True)
    else:
        st.write("Aún no hay datos para graficar este mes.")

with col_tabla:
    st.subheader("🗂️ Historial de Transacciones del Mes")
    if not df_mes.empty:
        df_mes_sorted = df_mes.sort_values(by='Fecha', ascending=False)
        st.dataframe(df_mes_sorted, use_container_width=True, hide_index=True)
    else:
        st.write("No hay transacciones registradas este mes.")