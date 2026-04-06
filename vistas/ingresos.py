import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv
from models import Ingreso

st.title("💵 Registro de Ingresos - Mes Actual")

# --- CARGA DE DATOS MAESTROS ---
df_cuentas_maestras = srv.obtener_cuentas()
if not df_cuentas_maestras.empty:
    mapa_cuentas = {f"{row['nombre']} ({row['tipo']})": row['nombre'] for _, row in df_cuentas_maestras.iterrows()}
else:
    mapa_cuentas = {"Efectivo (Débito)": "Efectivo"} 
lista_opciones_cuentas = list(mapa_cuentas.keys())

# --- FORMULARIO DE REGISTRO ---
st.header("📥 Registrar Nuevo Ingreso")

with st.form("form_registro_ingreso", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_input = st.date_input("Fecha", datetime.date.today())
        categoria_input = st.selectbox(
            "Categoría de Ingreso", 
            [
                "Nómina Pricesmart", 
                "Dividendos Galvanoplast J & N", 
                "Rendimientos Financieros", 
                "Ventas Libres",
                "Regalos / Devoluciones",
                "Otros Ingresos"
            ]
        )
        
    with col2:
        descripcion_input = st.text_input("Descripción / Concepto", placeholder="Ej: Quincena 1, Utilidades Q1...")
        
    with col3:
        valor_input = st.number_input("Valor ($)", min_value=0.0, step=50000.0)
        cuenta_input_display = st.selectbox("¿A qué cuenta entró el dinero?", lista_opciones_cuentas)
        
    submit_btn = st.form_submit_button("Registrar Ingreso")

    if submit_btn:
        if valor_input > 0 and descripcion_input.strip() != "":
            cuenta_real = mapa_cuentas[cuenta_input_display]

            nuevo_ingreso = Ingreso(
                fecha=fecha_input,
                categoria=categoria_input,
                descripcion=descripcion_input,
                valor=valor_input,
                cuenta_destino=cuenta_real
            )
            
            srv.registrar_ingreso(nuevo_ingreso)
            st.success("✅ Ingreso registrado correctamente.")
            st.rerun() 
        else:
            st.warning("⚠️ Debes ingresar una descripción válida y un valor mayor a 0.")

st.divider()

# --- DATOS Y CÁLCULOS DEL MES ---
st.header(f"📊 Resumen de {datetime.date.today().strftime('%B %Y').capitalize()}")

df_mes = srv.obtener_ingresos_mes_actual()
total_ingresos = df_mes['Valor'].sum() if not df_mes.empty else 0

st.metric("Total Ingresado en el Mes", f"${total_ingresos:,.0f}")
st.write("")

# --- GRÁFICOS Y TABLA DE HISTORIAL ---
col_grafico, col_tabla = st.columns([1, 1])

with col_grafico:
    st.subheader("📈 Ingresos por Categoría")
    if not df_mes.empty:
        df_agrupado_cat = df_mes.groupby('Categoría')['Valor'].sum().reset_index()
        
        # Gráfico de barras horizontales Altair
        base_cat = alt.Chart(df_agrupado_cat).encode(
            x=alt.X('Valor:Q', title='', axis=None),
            y=alt.Y('Categoría:N', sort='-x', title='')
        )
        barras_cat = base_cat.mark_bar(color='#2ca02c') # Color verde para ingresos
        texto_cat = base_cat.mark_text(
            align='left',
            baseline='middle',
            dx=3
        ).encode(
            text=alt.Text('Valor:Q', format='$,.0f')
        )
        st.altair_chart(barras_cat + texto_cat, use_container_width=True)
        
    else:
        st.write("Aún no hay ingresos registrados este mes.")

with col_tabla:
    st.subheader("🗂️ Historial de Entradas")
    if not df_mes.empty:
        df_mes_sorted = df_mes.sort_values(by='Fecha', ascending=False)
        st.dataframe(df_mes_sorted, use_container_width=True, hide_index=True)
    else:
        st.write("No hay transacciones registradas este mes.")