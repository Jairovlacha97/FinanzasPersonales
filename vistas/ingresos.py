import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv
from models import Ingreso

st.title("💵 Ingresos")

ym_actual = srv._ym_actual()

# --- SELECTOR DE MES ---
opciones_meses = []
cursor = ym_actual
for _ in range(13):
    opciones_meses.append(cursor)
    cursor = srv._prev_ym(cursor)

col_mes, col_info = st.columns([2, 3])
ym_sel = col_mes.selectbox("📅 Mes", opciones_meses, index=0, key="ingresos_mes_sel")
es_mes_actual = (ym_sel == ym_actual)

if not es_mes_actual:
    col_info.info(f"📂 Consultando historial de **{ym_sel}**. El formulario de registro está disponible al final de la página.")

# --- CARGA DE DATOS MAESTROS ---
df_cuentas_maestras = srv.obtener_cuentas()
if not df_cuentas_maestras.empty:
    mapa_cuentas = {f"{row['nombre']} ({row['tipo']})": row['nombre'] for _, row in df_cuentas_maestras.iterrows()}
else:
    mapa_cuentas = {"Efectivo (Débito)": "Efectivo"}
lista_opciones_cuentas = list(mapa_cuentas.keys())

categorias_ingreso = srv.obtener_categorias_por_tipo("ingreso")
if not categorias_ingreso:
    categorias_ingreso = [
        "Nómina Pricesmart",
        "Dividendos Galvanoplast J & N",
        "Rendimientos Financieros",
        "Ventas Libres",
        "Regalos / Devoluciones",
        "Otros Ingresos"
    ]

# --- DATOS DEL MES SELECCIONADO ---
df_mes = srv.obtener_ingresos_por_mes(ym_sel)
total_ingresos = df_mes['Valor'].sum() if not df_mes.empty else 0

# --- RESUMEN RÁPIDO ---
st.header(f"📊 Resumen de {ym_sel}")
st.metric("Total ingresado en el mes", f"${total_ingresos:,.0f}")
st.write("")

# --- GRÁFICOS Y TABLA ---
col_grafico, col_tabla = st.columns([1, 1])

with col_grafico:
    st.subheader("📈 Por Categoría")
    if not df_mes.empty:
        df_agrupado = df_mes.groupby('Categoría')['Valor'].sum().reset_index()
        base = alt.Chart(df_agrupado).encode(
            x=alt.X('Valor:Q', title='', axis=None),
            y=alt.Y('Categoría:N', sort='-x', title='')
        )
        barras = base.mark_bar(color='#2ca02c')
        texto = base.mark_text(align='left', baseline='middle', dx=3).encode(
            text=alt.Text('Valor:Q', format='$,.0f')
        )
        st.altair_chart(barras + texto, use_container_width=True)
    else:
        st.write("No hay ingresos registrados para este mes.")

with col_tabla:
    st.subheader("🗂️ Historial de entradas")
    if not df_mes.empty:
        st.dataframe(df_mes.sort_values(by='Fecha', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.write("No hay transacciones registradas este mes.")

st.divider()

# --- FORMULARIO DE REGISTRO (colapsado cuando se ve un mes anterior) ---
with st.expander("📥 Registrar nuevo ingreso", expanded=es_mes_actual):
    with st.form("form_registro_ingreso", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            primer_dia_sel = srv._ym_to_first_day(ym_sel)
            fecha_input = st.date_input("Fecha", datetime.date.today() if es_mes_actual else primer_dia_sel)
            categoria_input = st.selectbox("Categoría de Ingreso", categorias_ingreso)

        with col2:
            descripcion_input = st.text_input("Descripción / Concepto", placeholder="Ej: Quincena 1, Utilidades Q1...")

        with col3:
            valor_input = st.number_input("Valor ($)", min_value=0.0, step=50000.0)
            cuenta_input_display = st.selectbox("¿A qué cuenta entró?", lista_opciones_cuentas)

        if st.form_submit_button("Registrar Ingreso"):
            if valor_input > 0 and descripcion_input.strip() != "":
                srv.registrar_ingreso(Ingreso(
                    fecha=fecha_input,
                    categoria=categoria_input,
                    descripcion=descripcion_input,
                    valor=valor_input,
                    cuenta_destino=mapa_cuentas[cuenta_input_display]
                ))
                st.success("✅ Ingreso registrado correctamente.")
                st.rerun()
            else:
                st.warning("⚠️ Debes ingresar una descripción válida y un valor mayor a 0.")
