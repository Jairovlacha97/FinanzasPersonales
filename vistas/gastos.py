import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv
from models import Gasto, Presupuesto

st.title("💸 Gastos")

ym_actual = srv._ym_actual()

# --- SELECTOR DE MES ---
opciones_meses = []
cursor = ym_actual
for _ in range(13):   # mes actual + 12 meses atrás
    opciones_meses.append(cursor)
    cursor = srv._prev_ym(cursor)

col_mes, col_info = st.columns([2, 3])
ym_sel = col_mes.selectbox("📅 Mes", opciones_meses, index=0, key="gastos_mes_sel")
es_mes_actual = (ym_sel == ym_actual)

if not es_mes_actual:
    col_info.info(f"📂 Consultando historial de **{ym_sel}**. El formulario de registro está disponible al final de la página.")

# --- CARGA DE DATOS MAESTROS Y MAPEO ---
df_cuentas_maestras = srv.obtener_cuentas()
if not df_cuentas_maestras.empty:
    mapa_cuentas = {f"{row['nombre']} ({row['tipo']})": row['nombre'] for _, row in df_cuentas_maestras.iterrows()}
else:
    mapa_cuentas = {"Efectivo (Débito)": "Efectivo"}
lista_opciones_tarjetas = list(mapa_cuentas.keys())

# Cargamos categorías de gasto desde la tabla maestra
categorias_gasto = srv.obtener_categorias_por_tipo("gasto")
if not categorias_gasto:
    # Fallback: la tabla está vacía. Usamos las hardcoded antiguas.
    categorias_gasto = [
        "Accesorios", "Alcohol", "Chapamovil", "Cuota Rappi", "Deporte",
        "Entretenimiento", "Facturas", "Gasolina", "Gatos",
        "Mercado", "Negocios", "Parqueadero", "Regalos",
        "Restaurantes", "Ropa", "Salud", "Snacks",
        "Suscripciones", "Transporte", "Varios", "Viajes",
        "Videojuegos"
    ]

# --- BARRA LATERAL: Presupuestos del mes (persistentes) ---
st.sidebar.header("⚙️ Presupuestos")
st.sidebar.caption(f"Mes seleccionado: **{ym_sel}**")

df_presupuestos = srv.obtener_presupuestos(ym_sel, tipo="gasto")
mapa_presupuesto = {row["categoria"]: float(row["monto"]) for _, row in df_presupuestos.iterrows()} if not df_presupuestos.empty else {}

# --- Botón estrella: generar presupuestos desde historial ---
st.sidebar.markdown("##### 🤖 Generar desde historial")
st.sidebar.caption("Calcula el promedio de tus gastos reales de los últimos meses y los guarda como presupuesto inicial.")
meses_hist_sidebar = st.sidebar.selectbox("Meses de historial", [3, 6, 9], index=0, key="meses_hist_gen")
if st.sidebar.button("📊 Poblar presupuestos automáticamente", use_container_width=True, type="primary"):
    try:
        prev = srv.calcular_prevision_mes(ym_sel, meses_historico=meses_hist_sidebar)
        detalle_prev = prev["detalle"]
        creados = 0
        for item in detalle_prev:
            if item["tipo"] != "gasto":
                continue
            srv.guardar_presupuesto(Presupuesto(
                year_month=ym_sel,
                categoria=item["categoria"],
                tipo="gasto",
                monto=float(item["monto"]),
                nota=f"Auto desde historial {meses_hist_sidebar}m ({item['origen']})",
            ))
            creados += 1
        st.sidebar.success(f"✅ {creados} presupuestos generados para {ym_sel}.")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error al generar: {e}")

st.sidebar.divider()

with st.sidebar.expander("✏️ Editar presupuesto por categoría", expanded=False):
    cat_pres = st.selectbox("Categoría", categorias_gasto, key="cat_pres_sidebar")
    valor_actual_pres = mapa_presupuesto.get(cat_pres, 0.0)
    monto_pres = st.number_input(
        "Monto presupuestado ($)", min_value=0.0, value=float(valor_actual_pres),
        step=50000.0, key="monto_pres_sidebar"
    )
    if st.button("Guardar", use_container_width=True, key="btn_guardar_pres"):
        srv.guardar_presupuesto(Presupuesto(
            year_month=ym_sel, categoria=cat_pres, tipo="gasto", monto=monto_pres
        ))
        st.success(f"Presupuesto de '{cat_pres}' guardado.")
        st.rerun()

if st.sidebar.button("📋 Copiar presupuestos del mes anterior", use_container_width=True):
    n = srv.copiar_presupuestos_de_mes(srv._prev_ym(ym_sel), ym_sel)
    if n > 0:
        st.success(f"Se copiaron {n} presupuestos del mes anterior.")
        st.rerun()
    else:
        st.warning("No hay presupuestos en el mes anterior para copiar.")

# Lista de presupuestos actuales editables
if mapa_presupuesto:
    st.sidebar.markdown("**Presupuestos actuales:**")
    for _, row in df_presupuestos.sort_values("categoria").iterrows():
        st.sidebar.write(f"• {row['categoria']}: ${float(row['monto']):,.0f}")

st.sidebar.divider()
st.sidebar.caption(
    "💡 Para ver la previsión de meses futuros ve al **Planificador del Mes**."
)

# --- FORMULARIO DE REGISTRO (siempre disponible, colapsado al ver meses anteriores) ---
with st.expander("📝 Registrar nuevo gasto", expanded=es_mes_actual):
    with st.form("form_registro", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            primer_dia_sel = srv._ym_to_first_day(ym_sel)
            fecha_input = st.date_input("Fecha", datetime.date.today() if es_mes_actual else primer_dia_sel)
            categoria_input = st.selectbox("Categoría", categorias_gasto)

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
                srv.registrar_gasto(Gasto(
                    fecha=fecha_input,
                    categoria=categoria_input,
                    descripcion=descripcion_final,
                    valor=valor_input,
                    tarjeta=mapa_cuentas[tarjeta_input_display]
                ))
                st.success("✅ Gasto registrado correctamente.")
                st.rerun()
            else:
                st.warning("⚠️ Debes ingresar una descripción válida y un valor mayor a 0.")

st.divider()

# --- DATOS Y CÁLCULOS DEL MES SELECCIONADO ---
st.header(f"📊 Resumen de {ym_sel}")

df_mes = srv.obtener_gastos_por_mes(ym_sel)
total_general = df_mes['Valor'].sum() if not df_mes.empty else 0

st.metric("Total Gastado en el Mes (Consolidado)", f"${total_general:,.0f}")
st.write("")

# --- SECCIÓN DE PRESUPUESTOS DINÁMICOS ---
st.subheader("🎯 Control por Presupuestos")

# Consumo real por categoría (lo necesitamos en ambas secciones)
if not df_mes.empty:
    consumo_por_cat = df_mes.groupby('Categoría')['Valor'].sum().to_dict()
else:
    consumo_por_cat = {}

if df_presupuestos.empty:
    st.info(
        "Aún no tienes presupuestos para este mes. "
        "Usa el botón **📊 Poblar presupuestos automáticamente** en la barra lateral para generarlos desde tu historial."
    )
else:
    # Renderizamos una tarjeta por presupuesto, máximo 4 por fila
    presupuestos_orden = df_presupuestos.sort_values("categoria").to_dict('records')
    for i in range(0, len(presupuestos_orden), 4):
        grupo = presupuestos_orden[i:i + 4]
        cols = st.columns(len(grupo))
        for col, p in zip(cols, grupo):
            cat = p["categoria"]
            limite = float(p["monto"])
            gastado = float(consumo_por_cat.get(cat, 0))
            saldo = limite - gastado
            with col:
                st.markdown(f"**{cat}**")
                st.write(f"**Presupuesto:** ${limite:,.0f}")
                st.write(f"**Gastado:** ${gastado:,.0f}")
                if saldo >= 0:
                    st.success(f"Disponible: ${saldo:,.0f}")
                else:
                    st.error(f"Sobregiro: -${abs(saldo):,.0f}")
                if limite > 0:
                    st.progress(min(gastado / limite, 1.0))

    # --- FILA DE TOTALES ---
    st.divider()
    total_presupuestado = sum(float(p["monto"]) for p in presupuestos_orden)
    total_gastado_pres = sum(float(consumo_por_cat.get(p["categoria"], 0)) for p in presupuestos_orden)
    total_saldo = total_presupuestado - total_gastado_pres
    pct_ejecucion = (total_gastado_pres / total_presupuestado * 100) if total_presupuestado > 0 else 0.0

    st.markdown("#### 📊 Totales del presupuesto")
    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.metric("💼 Total presupuestado", f"${total_presupuestado:,.0f}")
    tc2.metric("🧾 Total gastado (en categorías)", f"${total_gastado_pres:,.0f}")
    if total_saldo >= 0:
        tc3.metric("✅ Margen disponible", f"${total_saldo:,.0f}")
    else:
        tc3.metric("🚨 Sobregiro total", f"-${abs(total_saldo):,.0f}", delta="Por encima del presupuesto", delta_color="inverse")
    tc4.metric("📈 % Ejecutado", f"{pct_ejecucion:.1f}%")

    if total_presupuestado > 0:
        st.progress(min(total_gastado_pres / total_presupuestado, 1.0), text=f"${total_gastado_pres:,.0f} de ${total_presupuestado:,.0f} presupuestados")

# --- GASTOS HORMIGA: categorías SIN presupuesto donde sí estás gastando ---
cats_presupuestadas = {p["categoria"] for p in df_presupuestos.to_dict('records')} if not df_presupuestos.empty else set()
if not df_mes.empty:
    df_fuera = df_mes[~df_mes['Categoría'].isin(cats_presupuestadas)]
    if not df_fuera.empty:
        resumen_fuera = df_fuera.groupby('Categoría')['Valor'].sum().sort_values(ascending=False).reset_index()
        total_fuera = resumen_fuera['Valor'].sum()
        st.divider()
        st.subheader("🐜 Gastos sin presupuesto asignado")
        st.caption(
            f"Estas categorías suman **${total_fuera:,.0f}** este mes pero no tienen presupuesto — "
            "son el origen típico de los gastos hormiga. Ponles un límite para controlarlos."
        )
        cols_fuera = st.columns(min(len(resumen_fuera), 4))
        for i, (col, (_, row)) in enumerate(zip(
            (cols_fuera * ((len(resumen_fuera) // 4) + 1))[:len(resumen_fuera)],
            resumen_fuera.iterrows()
        )):
            with col:
                st.markdown(f"**{row['Categoría']}**")
                st.metric("Gastado", f"${row['Valor']:,.0f}")
                if st.button("➕ Fijar presupuesto", key=f"add_pres_{row['Categoría']}"):
                    srv.guardar_presupuesto(Presupuesto(
                        year_month=ym_sel,
                        categoria=row['Categoría'],
                        tipo="gasto",
                        monto=float(row['Valor']),
                        nota="Fijado desde gastos hormiga",
                    ))
                    st.rerun()

st.divider()

# --- ANALISIS DE MEDIOS DE PAGO ---
if not df_mes.empty and not df_cuentas_maestras.empty:
    st.subheader("💳 Detalle por Medio de Pago")

    df_merge = df_mes.merge(df_cuentas_maestras, left_on='Tarjeta', right_on='nombre', how='left')

    col_cred, col_deb = st.columns(2)

    with col_cred:
        st.markdown("#### 🔴 Tarjetas de Crédito (Deuda)")
        df_c = df_merge[df_merge['tipo'] == 'Credito']

        if not df_c.empty:
            resumen_c = df_c.groupby(['Tarjeta', 'Categoría'])['Valor'].sum().reset_index()
            for tarjeta in resumen_c['Tarjeta'].unique():
                df_tarjeta = resumen_c[resumen_c['Tarjeta'] == tarjeta]
                total_t = df_tarjeta['Valor'].sum()
                with st.expander(f"**{tarjeta}**: ${total_t:,.0f}", expanded=True):
                    st.dataframe(
                        df_tarjeta[['Categoría', 'Valor']].rename(columns={'Valor': 'Monto'}),
                        use_container_width=True, hide_index=True
                    )
        else:
            st.info("No hay gastos a credito registrados.")

    with col_deb:
        st.markdown("#### 🔵 Cuentas de Débito / Efectivo")
        df_d = df_merge[df_merge['tipo'] == 'Debito']

        if not df_d.empty:
            resumen_d = df_d.groupby(['Tarjeta', 'Categoría'])['Valor'].sum().reset_index()
            for cuenta in resumen_d['Tarjeta'].unique():
                df_cuenta = resumen_d[resumen_d['Tarjeta'] == cuenta]
                total_c = df_cuenta['Valor'].sum()
                with st.expander(f"**{cuenta}**: ${total_c:,.0f}", expanded=False):
                    st.dataframe(
                        df_cuenta[['Categoría', 'Valor']].rename(columns={'Valor': 'Monto'}),
                        use_container_width=True, hide_index=True
                    )
        else:
            st.info("No hay gastos a debito registrados.")

st.divider()

# --- GRAFICOS Y TABLA DE HISTORIAL ---
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
        texto_cat = base_cat.mark_text(align='left', baseline='middle', dx=3).encode(
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
        texto_cta = base_cta.mark_text(align='left', baseline='middle', dx=3).encode(
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
