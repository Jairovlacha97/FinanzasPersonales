import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv

st.title("🏠 Mi Panorama Financiero")
st.write("Bienvenido a tu centro de comando. Aqui tienes la fotografia completa de tu dinero.")

# --- OBTENCIÓN DE DATOS Y TRM ---
trm_hoy = srv.obtener_trm_actual()
st.caption(f"💱 **TRM de hoy (USD a COP):** ${trm_hoy:,.2f}")

df_ingresos_mes = srv.obtener_ingresos_mes_actual()
df_gastos_mes   = srv.obtener_gastos_mes_actual()
df_deudas       = srv.obtener_deudas()
df_pagos_deudas = srv.obtener_pagos_deudas()
df_movs_ahorro  = srv.obtener_movimientos_ahorro()
df_trans_inv    = srv.obtener_transacciones_inversion()

ym_actual = srv._ym_actual()

# =====================================================================
# SECCIÓN 0: PLAN DEL MES — directo desde recurrentes (sin promedios históricos)
# =====================================================================
st.header(f"🎯 Plan del mes — {datetime.date.today().strftime('%B %Y').capitalize()}")
st.caption("Basado exactamente en tus items recurrentes activos y presupuestos del mes.")

try:
    df_rec = srv.obtener_items_recurrentes(solo_activos=True)

    def impacto_mensual(row):
        m = float(row['monto_estimado'])
        if row['frecuencia'] == 'quincenal':
            return m * 2
        if row['frecuencia'] == 'anual':
            return m / 12
        return m

    ing_plan = 0.0
    gas_plan = 0.0
    aho_plan = 0.0
    inv_plan = 0.0
    deu_plan = 0.0

    if not df_rec.empty:
        df_rec['impacto'] = df_rec.apply(impacto_mensual, axis=1)
        ing_plan = df_rec[df_rec['tipo'] == 'ingreso'   ]['impacto'].sum()
        gas_plan = df_rec[df_rec['tipo'] == 'gasto'     ]['impacto'].sum()
        aho_plan = df_rec[df_rec['tipo'] == 'ahorro'    ]['impacto'].sum()
        inv_plan = df_rec[df_rec['tipo'] == 'inversion' ]['impacto'].sum()
        deu_plan = df_rec[df_rec['tipo'] == 'pago_deuda']['impacto'].sum()

    # Gastos no esperados = presupuestos cuya categoria NO esta en recurrentes tipo gasto
    df_presupuestos_mes = srv.obtener_presupuestos(ym_actual, tipo="gasto")
    cats_rec_gasto = set(
        df_rec[df_rec["tipo"] == "gasto"]["categoria"].tolist()
    ) if not df_rec.empty else set()

    gas_no_esp = 0.0
    if not df_presupuestos_mes.empty:
        df_vars = df_presupuestos_mes[~df_presupuestos_mes["categoria"].isin(cats_rec_gasto)]
        gas_no_esp = float(df_vars["monto"].sum()) if not df_vars.empty else 0.0

    total_comprometido = gas_plan + gas_no_esp + aho_plan + inv_plan + deu_plan
    flujo_plan = ing_plan - total_comprometido

    # --- Fila 1: ingresos | gastos esperados | gastos no esperados | cuotas deuda ---
    cp1, cp2, cp3, cp4 = st.columns(4)
    cp1.metric("💵 Ingresos esperados",  f"${ing_plan:,.0f}")
    cp2.metric("🛍️ Gastos esperados",    f"${gas_plan:,.0f}",
               help="Recurrentes de tipo gasto")
    cp3.metric("💸 Gastos no esperados", f"${gas_no_esp:,.0f}",
               help="Presupuestos del mes cuya categoria no esta en recurrentes")
    cp4.metric("💳 Cuotas deuda",        f"${deu_plan:,.0f}",
               help="Recurrentes de tipo pago_deuda")

    # --- Fila 2: ahorro | inversiones | superavit/deficit ---
    cp5, cp6, cp7 = st.columns(3)
    cp5.metric("💰 Ahorro esperado",       f"${aho_plan:,.0f}")
    cp6.metric("📈 Inversiones esperadas", f"${inv_plan:,.0f}")
    cp7.metric(
        "🟢 Superávit proyectado" if flujo_plan >= 0 else "🚨 Déficit proyectado",
        f"${flujo_plan:,.0f}" if flujo_plan >= 0 else f"-${abs(flujo_plan):,.0f}",
        delta_color="normal" if flujo_plan >= 0 else "inverse",
        delta=None,
    )

    if ing_plan > 0:
        pct_plan = min(total_comprometido / ing_plan, 1.0)
        st.progress(pct_plan,
            text=f"{pct_plan*100:.0f}% de los ingresos esperados ya comprometidos este mes")

    if flujo_plan < 0:
        st.error(f"⚠️ Según tu plan, este mes te faltarian **${abs(flujo_plan):,.0f}**. Ve al **Planificador** para ajustar.")
    elif flujo_plan > 0:
        st.success(f"✅ Con tu plan actual te sobran **${flujo_plan:,.0f}** este mes. Puedes destinarlo a ahorro extra o amortizacion.")

except Exception as e:
    st.info(f"Configura tus items recurrentes para ver la proyeccion del mes aqui. ({e})")

st.divider()

# =====================================================================
# SECCIÓN 1: FLUJO DE CAJA REAL DEL MES
# =====================================================================
st.header(f"📅 Flujo de Caja Real - {datetime.date.today().strftime('%B %Y').capitalize()}")

ingresos_mes = df_ingresos_mes['Valor'].sum() if not df_ingresos_mes.empty else 0.0
gastos_mes   = df_gastos_mes['Valor'].sum()   if not df_gastos_mes.empty   else 0.0
flujo_neto   = ingresos_mes - gastos_mes
tasa_ahorro  = (flujo_neto / ingresos_mes * 100) if ingresos_mes > 0 else 0.0

col_f1, col_f2, col_f3, col_f4 = st.columns(4)
col_f1.metric("Ingresos del Mes", f"${ingresos_mes:,.0f}")
col_f2.metric("Gastos del Mes",   f"${gastos_mes:,.0f}")

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

# =====================================================================
# SECCIÓN 2: PATRIMONIO NETO
# =====================================================================

# A. Ahorros
total_ahorros = 0.0
if not df_movs_ahorro.empty:
    ingresos_ahorro = df_movs_ahorro[df_movs_ahorro['tipo'] == 'Ingreso']['monto'].sum()
    retiros_ahorro  = df_movs_ahorro[df_movs_ahorro['tipo'] == 'Retiro']['monto'].sum()
    total_ahorros   = ingresos_ahorro - retiros_ahorro

# B. Inversiones en COP
total_inversiones_usd = 0.0
if not df_trans_inv.empty:
    df_trans_inv['monto_total'] = df_trans_inv['cantidad'] * df_trans_inv['precio_unitario']
    compras_inv = df_trans_inv[df_trans_inv['tipo_operacion'] == 'Compra']['monto_total'].sum()
    ventas_inv  = df_trans_inv[df_trans_inv['tipo_operacion'] == 'Venta']['monto_total'].sum()
    total_inversiones_usd = compras_inv - ventas_inv
total_inversiones_cop = total_inversiones_usd * trm_hoy
activos_totales = total_ahorros + total_inversiones_cop

# C. Pasivos
pasivos_totales = 0.0
if not df_deudas.empty:
    deudas_activas = df_deudas[df_deudas['activa'] == True]
    total_prestado = deudas_activas['monto_inicial'].sum()
    total_abonado  = 0.0
    if not df_pagos_deudas.empty:
        ids_activas   = deudas_activas['id'].tolist()
        pagos_validos = df_pagos_deudas[df_pagos_deudas['deuda_id'].isin(ids_activas)]
        total_abonado = pagos_validos['abono_capital'].sum()
    pasivos_totales = total_prestado - total_abonado

patrimonio_neto = activos_totales - pasivos_totales

st.header("💎 Tu Patrimonio Neto (Net Worth)")

col_p1, col_p2, col_p3 = st.columns(3)
col_p1.metric("🟢 Activos (Lo que tienes)", f"${activos_totales:,.0f}")
col_p2.metric("🔴 Pasivos (Lo que debes)",  f"${pasivos_totales:,.0f}")
col_p3.metric("🔵 Patrimonio Neto Real",    f"${patrimonio_neto:,.0f}")

st.subheader("📊 Composicion de tu Riqueza")

datos_composicion = pd.DataFrame({
    'Categoria': ['Ahorros (COP)', 'Inversiones Bursatiles (COP)', 'Deudas Pendientes (COP)'],
    'Monto': [total_ahorros, total_inversiones_cop, pasivos_totales],
    'Tipo':  ['Activo', 'Activo', 'Pasivo']
})
datos_composicion = datos_composicion[datos_composicion['Monto'] > 0]

if not datos_composicion.empty:
    base_comp = alt.Chart(datos_composicion).encode(
        x=alt.X('Monto:Q', title='', axis=None),
        y=alt.Y('Categoria:N', sort='-x', title=''),
        color=alt.Color('Tipo:N',
            scale=alt.Scale(domain=['Activo', 'Pasivo'], range=['#2ca02c', '#d62728']),
            legend=None)
    )
    barras_comp = base_comp.mark_bar()
    texto_comp  = base_comp.mark_text(align='left', baseline='middle', dx=3).encode(
        text=alt.Text('Monto:Q', format='$,.0f')
    )
    st.altair_chart(barras_comp + texto_comp, use_container_width=True)
else:
    st.info("A medida que registres ahorros, inversiones y deudas, aqui veras la radiografia de tu patrimonio.")
