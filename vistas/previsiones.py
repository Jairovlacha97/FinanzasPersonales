import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv
from models import Presupuesto, ItemPlaneado

st.title("🗓️ Planificador del Mes")
st.caption("Aquí planeas tu mes antes de que llegue: ves si los ingresos cubren todo lo que tienes comprometido y ajustas lo que haga falta.")

# --- SELECTOR DE MES ---
ym_actual = srv._ym_actual()
opciones_meses = []
cursor = srv._prev_ym(srv._prev_ym(srv._prev_ym(ym_actual)))
for _ in range(16):
    opciones_meses.append(cursor)
    cursor = srv._next_ym(cursor)

ym_default = srv._ym_proximo()
col_sel1, col_sel2 = st.columns([2, 1])
ym_objetivo = col_sel1.selectbox(
    "📅 Mes a planear",
    opciones_meses,
    index=opciones_meses.index(ym_default) if ym_default in opciones_meses else 0,
)
ventana_historico = col_sel2.selectbox("Histórico para promedios", [3, 6, 9], index=0,
    help="Cuántos meses atrás usar para estimar categorías sin item recurrente ni planeado")

st.divider()

# =====================================================================
# CÁLCULO CENTRAL
# =====================================================================
prevision = srv.calcular_prevision_mes(ym_objetivo, meses_historico=ventana_historico)
totales = prevision["totales"]
detalle = pd.DataFrame(prevision["detalle"])

ingresos = totales["ingresos"]
gastos = totales["gastos"]
ahorros = totales["ahorros"]
inversiones = totales["inversiones"]
pagos_capital = totales["pagos_deuda"]
pagos_intereses = totales["intereses_deuda"]
total_comprometido = gastos + ahorros + inversiones + pagos_capital + pagos_intereses
flujo = totales["flujo_neto"]

# =====================================================================
# SECCIÓN 1: ¿ME ALCANZA?
# =====================================================================
st.subheader(f"💡 ¿Me alcanza en {ym_objetivo}?")

if ingresos == 0:
    st.warning("⚠️ No hay ingresos proyectados para este mes. Revisa tus items recurrentes de tipo ingreso.")
else:
    pct_comprometido = min(total_comprometido / ingresos * 100, 100) if ingresos > 0 else 100

    if flujo >= 0:
        st.success(f"✅ **¡Sí alcanza!** Te sobrarían **${flujo:,.0f}** después de cubrir todo.")
    else:
        st.error(f"🚨 **¡No alcanza!** Hay un déficit de **${abs(flujo):,.0f}**. Necesitas recortar o buscar ingresos adicionales.")

    c1, c2 = st.columns(2)
    c1.metric("💵 Ingresos esperados", f"${ingresos:,.0f}")
    c2.metric(
        "💸 Total comprometido",
        f"${total_comprometido:,.0f}",
        delta=f"{'Sobran' if flujo >= 0 else 'Faltan'} ${abs(flujo):,.0f}",
        delta_color="normal" if flujo >= 0 else "inverse",
    )

    bar_val = min(pct_comprometido / 100, 1.0)
    barra_texto = f"{pct_comprometido:.0f}% de tus ingresos ya están comprometidos"
    st.progress(bar_val, text=barra_texto)

st.divider()

# =====================================================================
# SECCIÓN 2: ¿EN QUÉ SE VA EL DINERO?
# =====================================================================
st.subheader("🗂️ ¿En qué se va el dinero?")
st.caption("Desglose de lo que tienes comprometido este mes.")

col_g, col_d, col_a, col_i = st.columns(4)

with col_g:
    st.markdown("#### 🛍️ Gastos")
    st.metric("Total gastos", f"${gastos:,.0f}")
    if ingresos > 0:
        st.caption(f"{gastos/ingresos*100:.0f}% de tus ingresos")

with col_d:
    st.markdown("#### 💳 Cuotas deuda")
    st.metric("Capital + intereses", f"${pagos_capital + pagos_intereses:,.0f}")
    if pagos_intereses > 0:
        st.caption(f"⚠️ ${pagos_intereses:,.0f} en puro interés")

with col_a:
    st.markdown("#### 💰 Ahorro")
    st.metric("Aportes ahorro", f"${ahorros:,.0f}")
    if ingresos > 0:
        st.caption(f"{ahorros/ingresos*100:.0f}% de tus ingresos")

with col_i:
    st.markdown("#### 📈 Inversión")
    st.metric("Aportes inversión", f"${inversiones:,.0f}")
    if ingresos > 0:
        st.caption(f"{inversiones/ingresos*100:.0f}% de tus ingresos")

# Gráfico de torta del desglose
if total_comprometido > 0:
    datos_torta = []
    if gastos > 0:
        datos_torta.append({"Concepto": "🛍️ Gastos", "Monto": gastos})
    if pagos_capital > 0:
        datos_torta.append({"Concepto": "💳 Cuota deuda (capital)", "Monto": pagos_capital})
    if pagos_intereses > 0:
        datos_torta.append({"Concepto": "💳 Intereses deuda", "Monto": pagos_intereses})
    if ahorros > 0:
        datos_torta.append({"Concepto": "💰 Ahorro", "Monto": ahorros})
    if inversiones > 0:
        datos_torta.append({"Concepto": "📈 Inversión", "Monto": inversiones})
    if flujo > 0:
        datos_torta.append({"Concepto": "✅ Libre (flujo neto)", "Monto": flujo})

    df_torta = pd.DataFrame(datos_torta)
    torta = alt.Chart(df_torta).mark_arc(innerRadius=60).encode(
        theta=alt.Theta("Monto:Q"),
        color=alt.Color("Concepto:N", legend=alt.Legend(orient="right")),
        tooltip=["Concepto", alt.Tooltip("Monto:Q", format="$,.0f")],
    ).properties(height=260)
    st.altair_chart(torta, use_container_width=True)

# Detalle expandible por categoría
with st.expander("🔍 Ver detalle completo por categoría", expanded=False):
    if detalle.empty:
        st.info("No hay datos para mostrar.")
    else:
        detalle_agrupado = detalle.groupby(['tipo', 'categoria'], as_index=False).agg(
            monto_pronosticado=('monto', 'sum'),
            origen=('origen', lambda x: ' + '.join(sorted(set(x)))),
            fuentes=('nombre', lambda x: ', '.join(sorted(set(x)))),
        )
        etiquetas_tipo = {
            'ingreso': '💵 Ingreso',
            'gasto': '🛍️ Gasto',
            'ahorro': '💰 Ahorro',
            'inversion': '📈 Inversión',
            'pago_deuda': '💳 Deuda (capital)',
            'pago_deuda_intereses': '💳 Deuda (intereses)',
        }
        detalle_agrupado['Tipo'] = detalle_agrupado['tipo'].map(etiquetas_tipo).fillna(detalle_agrupado['tipo'])
        detalle_agrupado = detalle_agrupado.sort_values(['tipo', 'categoria'])
        st.dataframe(
            detalle_agrupado[['Tipo', 'categoria', 'monto_pronosticado', 'origen', 'fuentes']].rename(columns={
                'categoria': 'Categoría', 'monto_pronosticado': 'Monto pronosticado',
                'origen': 'Origen', 'fuentes': 'Fuentes',
            }).style.format({'Monto pronosticado': '${:,.0f}'}),
            use_container_width=True, hide_index=True,
        )

st.divider()

# =====================================================================
# SECCIÓN 3: CUOTAS DE DEUDA PROYECTADAS
# =====================================================================
st.subheader("💳 Cuotas de deuda proyectadas")
st.caption("Calculadas automáticamente con base en tus últimos pagos registrados.")

df_cuotas = srv.proyectar_cuotas_todas_las_deudas()
if df_cuotas.empty:
    st.info("No tienes deudas activas registradas. Si tienes créditos, regístralos en la sección **Deudas**.")
else:
    for _, c in df_cuotas.iterrows():
        col_n, col_cap, col_int, col_tot = st.columns([3, 2, 2, 2])
        col_n.markdown(f"**{c['nombre']}**")
        col_cap.metric("Capital", f"${float(c['capital_estimado']):,.0f}")
        col_int.metric("Intereses/seguros", f"${float(c['intereses_estimados']):,.0f}")
        col_tot.metric("Cuota total", f"${float(c['total_estimado']):,.0f}")

    total_cuotas = df_cuotas['total_estimado'].sum()
    total_intereses_cuotas = df_cuotas['intereses_estimados'].sum()
    st.markdown(f"**Total cuotas del mes: ${total_cuotas:,.0f}**")
    if total_intereses_cuotas > 0:
        pct_int = total_intereses_cuotas / total_cuotas * 100 if total_cuotas > 0 else 0
        st.warning(f"⚠️ **${total_intereses_cuotas:,.0f} ({pct_int:.1f}%)** de tus cuotas se van en intereses y seguros — dinero que no construye patrimonio.")

st.divider()

# =====================================================================
# SECCIÓN 4: EVENTOS PUNTUALES DEL MES
# =====================================================================
st.subheader(f"🎯 Eventos puntuales de {ym_objetivo}")
st.caption("Cosas que sabes que van a pasar **solo este mes**: un viaje, una prima, un regalo, una factura extraordinaria.")

df_planeados = srv.obtener_items_planeados(ym_objetivo)

col_lista, col_form = st.columns([2, 1])

with col_lista:
    if df_planeados.empty:
        st.info("No has registrado eventos puntuales para este mes.")
    else:
        tipo_iconos = {'ingreso': '💵', 'gasto': '🛍️', 'ahorro': '💰', 'inversion': '📈'}
        for _, p in df_planeados.iterrows():
            icono = tipo_iconos.get(p['tipo'], '📌')
            cc = st.columns([3, 2, 2, 1])
            cc[0].write(f"{icono} **{p['nombre']}**")
            cc[1].caption(p['categoria'])
            cc[2].write(f"${float(p['monto']):,.0f}")
            if cc[3].button("🗑️", key=f"del_plan_{p['id']}"):
                srv.eliminar_item_planeado(int(p['id']))
                st.rerun()

with col_form:
    with st.form(f"form_planeado_{ym_objetivo}", clear_on_submit=True):
        st.markdown("**➕ Añadir evento**")
        nombre_p = st.text_input("Nombre")
        tipo_p = st.selectbox("Tipo", ["gasto", "ingreso", "ahorro", "inversion"])
        cats_disp = srv.obtener_categorias_por_tipo(tipo_p)
        if not cats_disp:
            cats_disp = ["Otros"]
        categoria_p = st.selectbox("Categoría", cats_disp)
        monto_p = st.number_input("Monto ($)", min_value=0.0, step=50000.0)
        nota_p = st.text_input("Nota (opcional)")
        if st.form_submit_button("Añadir", use_container_width=True):
            if nombre_p.strip() and monto_p > 0:
                srv.registrar_item_planeado(ItemPlaneado(
                    year_month=ym_objetivo,
                    nombre=nombre_p.strip(),
                    tipo=tipo_p,
                    categoria=categoria_p,
                    monto=monto_p,
                    nota=nota_p or None,
                ))
                st.success("✅ Evento añadido.")
                st.rerun()
            else:
                st.warning("Necesitas un nombre y un monto mayor a 0.")

st.divider()

# =====================================================================
# SECCIÓN 5: GUARDAR COMO PRESUPUESTO
# =====================================================================
st.subheader("💾 Convertir previsión en presupuesto")

ym_actual_prev = srv._ym_actual()
if ym_objetivo != ym_actual_prev:
    st.warning(
        f"⚠️ Estás planeando **{ym_objetivo}** pero el mes en curso es **{ym_actual_prev}**. "
        f"Al guardar, los presupuestos se crearán para **{ym_objetivo}** — "
        f"para verlos en la sección Gastos tendrás que estar en ese mes, o cambia el selector de arriba a {ym_actual_prev}."
    )
else:
    st.caption(
        f"Guarda los montos pronosticados como presupuesto oficial de **{ym_objetivo}** para gastos, ahorros e inversiones. "
        "Después los verás como límites/metas en la sección de **Gastos**."
    )

df_pres_guardados = srv.obtener_presupuestos(ym_objetivo)
if not df_pres_guardados.empty:
    st.success(f"✅ Ya tienes **{len(df_pres_guardados)} presupuestos guardados** para {ym_objetivo}. Puedes sobreescribirlos.")

if st.button(f"💾 Guardar previsión como presupuesto de {ym_objetivo}", type="primary", use_container_width=True):
    if detalle.empty:
        st.warning("No hay datos de previsión para guardar.")
    else:
        detalle_agrupado_save = detalle.groupby(['tipo', 'categoria'], as_index=False).agg(
            monto_pronosticado=('monto', 'sum'),
            origen=('origen', lambda x: ' + '.join(sorted(set(x)))),
        )
        creados = 0
        for _, r in detalle_agrupado_save.iterrows():
            if r['tipo'] not in ('gasto', 'ahorro', 'inversion'):
                continue
            srv.guardar_presupuesto(Presupuesto(
                year_month=ym_objetivo,
                categoria=r['categoria'],
                tipo=r['tipo'],
                monto=float(r['monto_pronosticado']),
                nota=f"Auto desde previsión ({r['origen']})",
            ))
            creados += 1
        st.success(f"✅ Se guardaron {creados} presupuestos para {ym_objetivo}.")
        st.rerun()

st.divider()

# =====================================================================
# SECCIÓN 6: PRONÓSTICO ROLLING (COLAPSABLE)
# =====================================================================
horizonte = st.selectbox("Horizonte del pronóstico (meses)", [3, 6, 9, 12], index=1,
    help="Cuántos meses hacia adelante proyectar")

with st.expander(f"📈 Ver pronóstico rolling — próximos {horizonte} meses", expanded=False):
    df_rolling = srv.calcular_prevision_rolling(
        year_month_inicio=ym_objetivo,
        n_meses=horizonte,
        meses_historico=ventana_historico,
    )

    if df_rolling.empty:
        st.info("No hay datos suficientes para el pronóstico rolling.")
    else:
        df_chart = df_rolling.melt(
            id_vars=['year_month'],
            value_vars=['ingresos', 'gastos', 'ahorros', 'inversiones', 'pagos_deuda', 'intereses_deuda'],
            var_name='tipo', value_name='monto',
        )
        map_tipo = {
            'ingresos': '💵 Ingresos', 'gastos': '🛍️ Gastos',
            'ahorros': '💰 Ahorros', 'inversiones': '📈 Inversiones',
            'pagos_deuda': '💳 Deuda capital', 'intereses_deuda': '💳 Deuda intereses',
        }
        df_chart['tipo'] = df_chart['tipo'].map(map_tipo)

        barras = alt.Chart(df_chart).mark_bar().encode(
            x=alt.X('year_month:N', title='Mes', sort=df_rolling['year_month'].tolist()),
            y=alt.Y('monto:Q', title='Monto ($)'),
            color=alt.Color('tipo:N', title='Concepto'),
            tooltip=['year_month', 'tipo', alt.Tooltip('monto:Q', format='$,.0f')],
            xOffset='tipo:N',
        )
        st.altair_chart(barras, use_container_width=True)

        df_show = df_rolling.rename(columns={
            'year_month': 'Mes', 'ingresos': 'Ingresos', 'gastos': 'Gastos',
            'ahorros': 'Ahorros', 'inversiones': 'Inversiones',
            'pagos_deuda': 'Deuda capital', 'intereses_deuda': 'Deuda intereses',
            'flujo_neto': 'Flujo neto',
        })
        st.dataframe(
            df_show.style.format({c: '${:,.0f}' for c in df_show.columns if c != 'Mes'}),
            use_container_width=True, hide_index=True,
        )

        df_acum = df_rolling[['year_month', 'flujo_neto']].copy()
        df_acum['Saldo acumulado'] = df_acum['flujo_neto'].cumsum()
        df_acum = df_acum.rename(columns={'year_month': 'Mes', 'flujo_neto': 'Flujo del mes'})
        st.markdown("**Saldo acumulado proyectado** — si nada cambia, esto es lo que sobra/falta acumulado mes a mes")
        line_acum = alt.Chart(df_acum).mark_line(point=True, strokeWidth=3).encode(
            x=alt.X('Mes:N', sort=df_acum['Mes'].tolist()),
            y=alt.Y('Saldo acumulado:Q', title='Saldo acumulado ($)'),
            tooltip=['Mes', alt.Tooltip('Saldo acumulado:Q', format='$,.0f')],
        )
        zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='red', strokeDash=[4, 4]).encode(y='y:Q')
        st.altair_chart(line_acum + zero_line, use_container_width=True)
