import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv

st.title("🏠 Mi Panorama Financiero")
st.write("Bienvenido a tu centro de comando. Aquí tienes la fotografía completa de tu dinero.")

# --- OBTENCIÓN DE DATOS Y TRM ---
trm_hoy = srv.obtener_trm_actual()
st.caption(f"💱 **TRM de hoy (USD a COP):** ${trm_hoy:,.2f}")

df_ingresos_mes = srv.obtener_ingresos_mes_actual()
df_gastos_mes = srv.obtener_gastos_mes_actual()
df_deudas = srv.obtener_deudas()
df_pagos_deudas = srv.obtener_pagos_deudas()
df_movs_ahorro = srv.obtener_movimientos_ahorro()
df_trans_inv = srv.obtener_transacciones_inversion()

# --- 1. SECCIÓN MENSUAL: FLUJO DE CAJA ---
st.header(f"📅 Flujo de Caja - {datetime.date.today().strftime('%B %Y').capitalize()}")

ingresos_mes = df_ingresos_mes['Valor'].sum() if not df_ingresos_mes.empty else 0.0
gastos_mes = df_gastos_mes['Valor'].sum() if not df_gastos_mes.empty else 0.0
flujo_neto = ingresos_mes - gastos_mes

tasa_ahorro = (flujo_neto / ingresos_mes * 100) if ingresos_mes > 0 else 0.0

col_f1, col_f2, col_f3, col_f4 = st.columns(4)
col_f1.metric("Ingresos del Mes", f"${ingresos_mes:,.0f}")
col_f2.metric("Gastos del Mes", f"${gastos_mes:,.0f}")

if flujo_neto >= 0:
    col_f3.metric("Flujo Libre (Sobrante)", f"${flujo_neto:,.0f}")
    col_f4.metric("Tasa de Ahorro", f"{tasa_ahorro:.1f}%")
else:
    col_f3.metric("Sobregiro", f"${flujo_neto:,.0f}", delta_color="inverse")
    col_f4.metric("Tasa de Ahorro", "0.0%")

if ingresos_mes > 0:
    st.write("**Uso de tus ingresos este mes:**")
    st.progress(min(gastos_mes / ingresos_mes, 1.0))

st.divider()

# --- 2. CÁLCULOS PARA PATRIMONIO NETO ---

# A. Calcular Ahorros (En COP)
total_ahorros = 0.0
if not df_movs_ahorro.empty:
    ingresos_ahorro = df_movs_ahorro[df_movs_ahorro['tipo'] == 'Ingreso']['monto'].sum()
    retiros_ahorro = df_movs_ahorro[df_movs_ahorro['tipo'] == 'Retiro']['monto'].sum()
    total_ahorros = ingresos_ahorro - retiros_ahorro

# B. Calcular Inversiones y CONVERTIR A COP
total_inversiones_usd = 0.0
if not df_trans_inv.empty:
    df_trans_inv['monto_total'] = df_trans_inv['cantidad'] * df_trans_inv['precio_unitario']
    compras_inv = df_trans_inv[df_trans_inv['tipo_operacion'] == 'Compra']['monto_total'].sum()
    ventas_inv = df_trans_inv[df_trans_inv['tipo_operacion'] == 'Venta']['monto_total'].sum()
    total_inversiones_usd = compras_inv - ventas_inv

# ¡Aquí ocurre la magia de la conversión!
total_inversiones_cop = total_inversiones_usd * trm_hoy

activos_totales = total_ahorros + total_inversiones_cop

# C. Calcular Pasivos (Deudas Activas - Abonos a Capital en COP)
pasivos_totales = 0.0
if not df_deudas.empty:
    deudas_activas = df_deudas[df_deudas['activa'] == True]
    total_prestado = deudas_activas['monto_inicial'].sum()
    
    total_abonado = 0.0
    if not df_pagos_deudas.empty:
        ids_activas = deudas_activas['id'].tolist()
        pagos_validos = df_pagos_deudas[df_pagos_deudas['deuda_id'].isin(ids_activas)]
        total_abonado = pagos_validos['abono_capital'].sum()
        
    pasivos_totales = total_prestado - total_abonado

# D. PATRIMONIO NETO
patrimonio_neto = activos_totales - pasivos_totales

# --- 3. SECCIÓN HISTÓRICA: PATRIMONIO NETO ---
st.header("💎 Tu Patrimonio Neto (Net Worth)")

col_p1, col_p2, col_p3 = st.columns(3)
col_p1.metric("🟢 Activos (Lo que tienes)", f"${activos_totales:,.0f}")
col_p2.metric("🔴 Pasivos (Lo que debes)", f"${pasivos_totales:,.0f}")
col_p3.metric("🔵 Patrimonio Neto Real", f"${patrimonio_neto:,.0f}")

st.subheader("📊 Composición de tu Riqueza")

datos_composicion = pd.DataFrame({
    'Categoría': ['Ahorros (COP)', 'Inversiones Bursátiles (Convertidas a COP)', 'Deudas Pendientes (COP)'],
    'Monto': [total_ahorros, total_inversiones_cop, pasivos_totales],
    'Tipo': ['Activo', 'Activo', 'Pasivo']
})

datos_composicion = datos_composicion[datos_composicion['Monto'] > 0]

if not datos_composicion.empty:
    base_comp = alt.Chart(datos_composicion).encode(
        x=alt.X('Monto:Q', title='', axis=None),
        y=alt.Y('Categoría:N', sort='-x', title=''),
        color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Activo', 'Pasivo'], range=['#2ca02c', '#d62728']), legend=None)
    )
    
    barras_comp = base_comp.mark_bar()
    texto_comp = base_comp.mark_text(
        align='left',
        baseline='middle',
        dx=3
    ).encode(
        text=alt.Text('Monto:Q', format='$,.0f')
    )
    
    st.altair_chart(barras_comp + texto_comp, use_container_width=True)
else:
    st.info("A medida que registres ahorros, inversiones y deudas, aquí verás la radiografía de tu patrimonio.")