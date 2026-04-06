import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv
from models import Ahorro, MovimientoAhorro

st.title("💰 Gestión de Ahorros e Inversiones")

# --- CARGA DE DATOS ---
df_ahorros = srv.obtener_ahorros()
df_movs = srv.obtener_movimientos_ahorro()

# --- CÁLCULO DE SALDOS REALES ---
saldos_dict = {}
if not df_movs.empty:
    for _, mov in df_movs.iterrows():
        nombre = mov['nombre_ahorro']
        valor = mov['monto'] if mov['tipo'] == 'Ingreso' else -mov['monto']
        saldos_dict[nombre] = saldos_dict.get(nombre, 0) + valor

# --- RESUMEN ---
total_ahorrado = sum(saldos_dict.values())
st.metric("Patrimonio Total en Ahorros", f"${total_ahorrado:,.0f}")

st.divider()

# --- GESTIÓN DE MOVIMIENTOS Y FONDOS ---
tab_mov, tab_nuevo = st.tabs(["🔄 Registrar Movimiento", "🆕 Nuevo Fondo/Fiducia"])

with tab_nuevo:
    with st.form("form_nuevo_ahorro"):
        nombre = st.text_input("Nombre del Fondo (Ej: Fiducia, Emergencias)")
        meta = st.number_input("Meta de ahorro (Opcional)", min_value=0.0)
        if st.form_submit_button("Crear Fondo"):
            srv.registrar_ahorro(Ahorro(nombre=nombre, meta=meta))
            st.success("Fondo creado exitosamente.")
            st.rerun()

with tab_mov:
    if df_ahorros.empty:
        st.warning("Crea un fondo primero en la pestaña de al lado.")
    else:
        mapa_ahorros = {r['nombre']: r['id'] for _, r in df_ahorros.iterrows()}
        
        with st.form("form_mov_ahorro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre_seleccionado = st.selectbox("Fondo", list(mapa_ahorros.keys()))
                tipo = st.radio("Tipo de movimiento", ["Ingreso", "Retiro"])
                monto = st.number_input("Monto ($)", min_value=0.0, step=50000.0)
            with col2:
                fecha = st.date_input("Fecha", datetime.date.today())
                df_c = srv.obtener_cuentas()
                cta = st.selectbox("Cuenta relacionada", df_c['nombre'].tolist() if not df_c.empty else ["Efectivo"])
            
            if st.form_submit_button("Registrar Movimiento"):
                if monto > 0:
                    id_real = mapa_ahorros[nombre_seleccionado]
                    mov = MovimientoAhorro(ahorro_id=id_real, fecha=fecha, tipo=tipo, monto=monto, cuenta_relacionada=cta)
                    srv.registrar_movimiento_ahorro(mov)
                    st.success("Movimiento registrado correctamente.")
                    st.rerun()
                else:
                    st.warning("El monto debe ser mayor a 0.")

st.divider()

# --- VISUALIZACIÓN: LÍNEAS DE TENDENCIA Y RESUMEN ---
st.subheader("📈 Evolución de tus Ahorros")

if not df_movs.empty:
    # 1. Preparar datos para la tendencia
    df_tendencia = df_movs.copy()
    df_tendencia['fecha'] = pd.to_datetime(df_tendencia['fecha'])
    
    # 2. Asignar signo positivo a Ingresos y negativo a Retiros
    df_tendencia['monto_real'] = df_tendencia.apply(
        lambda x: x['monto'] if x['tipo'] == 'Ingreso' else -x['monto'], axis=1
    )
    
    # 3. Ordenar cronológicamente y calcular el acumulado por fondo
    df_tendencia = df_tendencia.sort_values(by=['nombre_ahorro', 'fecha'])
    df_tendencia['Saldo Acumulado'] = df_tendencia.groupby('nombre_ahorro')['monto_real'].cumsum()

    # 4. Crear el gráfico de líneas con Altair
    grafico_tendencia = alt.Chart(df_tendencia).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X('fecha:T', title='Fecha de Movimiento'),
        y=alt.Y('Saldo Acumulado:Q', title='Saldo Disponible ($)'),
        color=alt.Color('nombre_ahorro:N', title='Bolsillo/Fondo', legend=alt.Legend(orient='bottom')),
        tooltip=[
            alt.Tooltip('fecha:T', title='Fecha'), 
            alt.Tooltip('nombre_ahorro:N', title='Fondo'), 
            alt.Tooltip('Saldo Acumulado:Q', title='Saldo', format='$,.0f')
        ]
    ).interactive() # Hace que el gráfico permita hacer zoom y desplazarse

    st.altair_chart(grafico_tendencia, use_container_width=True)

    st.write("")
    
    # --- SALDOS ACTUALES EN TEXTO ---
    st.subheader("📋 Resumen de Saldos Actuales")
    for nombre, saldo in saldos_dict.items():
        col_n, col_s = st.columns([3, 1])
        col_n.write(f"**{nombre}**")
        col_s.write(f"${saldo:,.0f}")
        st.divider()
else:
    st.info("No hay movimientos registrados para graficar tu progreso. ¡Empieza a ahorrar!")