import streamlit as st
import pandas as pd
import datetime
import services as srv
from models import ItemRecurrente, Categoria, Presupuesto

st.title("🔁 Items Recurrentes y Categorías")
st.caption(
    "Aquí registras todo lo que se repite mes a mes: nómina, suscripciones, aportes a fondos, **y las cuotas de tus deudas**. "
    "Estos items son la base del pronóstico de la página **Planificador del Mes**."
)

tab_rec, tab_cat = st.tabs(["🔁 Items Recurrentes", "🏷️ Categorías"])

# =====================================================================
# TAB 1: ITEMS RECURRENTES
# =====================================================================
with tab_rec:
    df_cuentas = srv.obtener_cuentas()
    mapa_cuentas_disp = (
        [f"{r['nombre']} ({r['tipo']})" for _, r in df_cuentas.iterrows()]
        if not df_cuentas.empty else []
    )

    # Obtenemos las deudas activas para usarlas como opciones cuando tipo = pago_deuda
    df_deudas_activas = srv.obtener_deudas()
    if not df_deudas_activas.empty:
        df_deudas_activas = df_deudas_activas[df_deudas_activas['activa'] == True]
    nombres_deudas = df_deudas_activas['nombre'].tolist() if not df_deudas_activas.empty else []

    col_form, col_lista = st.columns([1, 2])

    with col_form:
        st.subheader("➕ Nuevo item recurrente")

        # El selector de tipo va FUERA del form para que al cambiar actualice
        # inmediatamente las opciones de categoría/deuda.
        tipo = st.selectbox(
            "Tipo",
            ["ingreso", "gasto", "ahorro", "inversion", "pago_deuda"],
            key="rec_tipo_selector",
            help="Usa **pago_deuda** para registrar la cuota mensual de cualquier crédito o deuda."
        )

        # Calculamos las opciones de categoría según el tipo elegido
        if tipo == "pago_deuda":
            if nombres_deudas:
                opciones_cat = nombres_deudas
                label_cat = "¿A qué deuda corresponde?"
                help_cat = "El nombre debe coincidir exactamente con la deuda registrada en la sección Deudas."
            else:
                st.warning("⚠️ No tienes deudas activas. Ve primero a la sección **Deudas** y crea la deuda.")
                opciones_cat = ["— sin deudas registradas —"]
                label_cat = "Deuda"
                help_cat = ""
        else:
            cats_disp = srv.obtener_categorias_por_tipo(tipo)
            opciones_cat = cats_disp if cats_disp else ["Otros"]
            label_cat = "Categoría"
            help_cat = ""

        with st.form("form_nuevo_recurrente", clear_on_submit=True):
            nombre = st.text_input("Nombre", placeholder="Ej: Nómina, Netflix, Cuota crédito vehículo")

            categoria = st.selectbox(label_cat, opciones_cat, help=help_cat)

            monto = st.number_input(
                "Monto estimado ($)",
                min_value=0.0,
                step=50000.0,
                help="Para pago_deuda: escribe el valor total de la cuota (capital + intereses)."
            )
            frecuencia = st.selectbox("Frecuencia", ["mensual", "quincenal", "anual"])
            dia_mes = st.number_input("Día del mes (opcional)", min_value=0, max_value=31, value=0)
            cuenta_rel = st.selectbox(
                "Cuenta relacionada (opcional)", ["—"] + mapa_cuentas_disp
            )

            col_f1, col_f2 = st.columns(2)
            fecha_inicio = col_f1.date_input("Fecha inicio", datetime.date.today().replace(day=1))
            fecha_fin = col_f2.date_input("Fecha fin (opcional)", value=None, format="YYYY-MM-DD")

            # Opción de sincronización automática con presupuesto (solo para gasto)
            sincronizar_presupuesto = False
            if tipo == "gasto":
                sincronizar_presupuesto = st.checkbox(
                    "📋 Sincronizar como presupuesto del mes actual",
                    value=True,
                    help="Crea o actualiza automáticamente el presupuesto de esta categoría para el mes en curso con el impacto mensual estimado."
                )

            submitted = st.form_submit_button("Crear item recurrente", use_container_width=True)
            if submitted:
                if not nombre.strip() or monto <= 0:
                    st.warning("Necesitas un nombre y un monto > 0.")
                elif tipo == "pago_deuda" and (not categoria.strip() or categoria == "— sin deudas registradas —"):
                    st.warning("Debes indicar a qué deuda corresponde.")
                else:
                    cuenta_real = None
                    if cuenta_rel != "—" and "(" in cuenta_rel:
                        cuenta_real = cuenta_rel.split(" (")[0]

                    # Calcular impacto mensual según frecuencia
                    if frecuencia == "quincenal":
                        impacto_mes = monto * 2
                    elif frecuencia == "anual":
                        impacto_mes = monto / 12
                    else:
                        impacto_mes = monto

                    srv.registrar_item_recurrente(ItemRecurrente(
                        nombre=nombre.strip(),
                        tipo=tipo,
                        categoria=categoria,
                        monto_estimado=monto,
                        frecuencia=frecuencia,
                        dia_mes=int(dia_mes) if dia_mes > 0 else None,
                        cuenta_relacionada=cuenta_real,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin if fecha_fin else None,
                        activo=True,
                    ))

                    # Sincronizar con presupuesto si el usuario lo eligió
                    if tipo == "gasto" and sincronizar_presupuesto:
                        ym_actual = srv._ym_actual()
                        srv.guardar_presupuesto(Presupuesto(
                            year_month=ym_actual,
                            categoria=categoria,
                            tipo="gasto",
                            monto=impacto_mes,
                            nota=f"Sync desde recurrente: {nombre.strip()}",
                        ))
                        st.success(f"✅ Item recurrente creado y presupuesto de **{categoria}** actualizado a **${impacto_mes:,.0f}** para {ym_actual}.")
                    else:
                        st.success("✅ Item recurrente creado.")
                    st.rerun()

    with col_lista:
        st.subheader("📋 Items activos")
        df_rec = srv.obtener_items_recurrentes(solo_activos=True)
        if df_rec.empty:
            st.info("No hay items recurrentes registrados todavía.")
        else:
            etq = {
                'ingreso': '💵 Ingreso',
                'gasto': '🛍️ Gasto',
                'ahorro': '💰 Ahorro',
                'inversion': '📈 Inversión',
                'pago_deuda': '💳 Cuota deuda',
            }
            df_rec_show = df_rec.copy()
            df_rec_show['Tipo'] = df_rec_show['tipo'].map(etq).fillna(df_rec_show['tipo'])

            def impacto_mensual(row):
                m = float(row['monto_estimado'])
                if row['frecuencia'] == 'quincenal':
                    return m * 2
                if row['frecuencia'] == 'anual':
                    return m / 12
                return m
            df_rec_show['Impacto mensual'] = df_rec_show.apply(impacto_mensual, axis=1)

            # Separar deudas del resto para mostrarlas destacadas
            df_deudas_rec = df_rec_show[df_rec_show['tipo'] == 'pago_deuda']
            df_otros_rec = df_rec_show[df_rec_show['tipo'] != 'pago_deuda']

            # --- Sección cuotas de deuda ---
            if not df_deudas_rec.empty:
                st.markdown("##### 💳 Cuotas de deuda registradas")
                st.caption("Estos montos se usarán en el Planificador para calcular cuánto se va en deuda cada mes.")
                for _, item in df_deudas_rec.iterrows():
                    col_a, col_b, col_c, col_d = st.columns([4, 2, 2, 1])
                    col_a.write(f"💳 **{item['nombre']}** → {item['categoria']}")
                    col_b.write(f"${float(item['monto_estimado']):,.0f} {item['frecuencia']}")
                    col_c.write(f"Mensual: **${item['Impacto mensual']:,.0f}**")
                    if col_d.button("🗑️", key=f"del_rec_deuda_{item['id']}"):
                        srv.eliminar_item_recurrente(int(item['id']))
                        st.rerun()
                st.divider()

            # --- Tabla del resto ---
            if not df_otros_rec.empty:
                st.markdown("##### Ingresos, gastos y aportes")
                cols_mostrar = ['Tipo', 'nombre', 'categoria', 'monto_estimado', 'frecuencia', 'Impacto mensual']
                renombrar = {
                    'nombre': 'Nombre',
                    'categoria': 'Categoría',
                    'monto_estimado': 'Monto base',
                    'frecuencia': 'Frecuencia',
                }
                st.dataframe(
                    df_otros_rec[cols_mostrar].rename(columns=renombrar).style.format({
                        'Monto base': '${:,.0f}',
                        'Impacto mensual': '${:,.0f}',
                    }),
                    use_container_width=True, hide_index=True,
                )

            # Resumen mensual
            tot_ing = df_rec_show[df_rec_show['tipo'] == 'ingreso']['Impacto mensual'].sum()
            tot_gas = df_rec_show[df_rec_show['tipo'] == 'gasto']['Impacto mensual'].sum()
            tot_aho = df_rec_show[df_rec_show['tipo'] == 'ahorro']['Impacto mensual'].sum()
            tot_inv = df_rec_show[df_rec_show['tipo'] == 'inversion']['Impacto mensual'].sum()
            tot_deu = df_rec_show[df_rec_show['tipo'] == 'pago_deuda']['Impacto mensual'].sum()

            st.markdown("##### Resumen mensual de recurrentes")
            r1, r2, r3, r4, r5 = st.columns(5)
            r1.metric("💵 Ingresos", f"${tot_ing:,.0f}")
            r2.metric("🛍️ Gastos", f"${tot_gas:,.0f}")
            r3.metric("💰 Ahorros", f"${tot_aho:,.0f}")
            r4.metric("📈 Inversiones", f"${tot_inv:,.0f}")
            r5.metric("💳 Cuotas deuda", f"${tot_deu:,.0f}")

            total_salidas = tot_gas + tot_aho + tot_inv + tot_deu
            if tot_ing > 0:
                saldo_rec = tot_ing - total_salidas
                if saldo_rec >= 0:
                    st.success(f"✅ Con tus recurrentes, te sobran **${saldo_rec:,.0f}** al mes para gastos variables.")
                else:
                    st.error(f"🚨 Tus recurrentes ya generan un déficit de **${abs(saldo_rec):,.0f}** antes de gastos variables.")

            # Eliminar otros items
            if not df_otros_rec.empty:
                st.markdown("##### Eliminar items")
                for _, item in df_otros_rec.iterrows():
                    col_a, col_b, col_c = st.columns([5, 2, 1])
                    col_a.write(f"**{item['nombre']}** — {item['tipo']}/{item['categoria']}")
                    col_b.write(f"${float(item['monto_estimado']):,.0f} {item['frecuencia']}")
                    if col_c.button("🗑️", key=f"del_rec_{item['id']}"):
                        srv.eliminar_item_recurrente(int(item['id']))
                        st.rerun()

# =====================================================================
# TAB 2: CATEGORÍAS
# =====================================================================
with tab_cat:
    st.subheader("🏷️ Catálogo de categorías")
    st.caption("Estas son las categorías disponibles en toda la app (gastos, ingresos, ahorros, inversiones).")

    col_a, col_b = st.columns([1, 2])

    with col_a:
        st.markdown("##### ➕ Nueva categoría")
        with st.form("form_nueva_cat", clear_on_submit=True):
            nombre_cat = st.text_input("Nombre")
            tipo_cat = st.selectbox("Tipo", ["gasto", "ingreso", "ahorro", "inversion"])
            if st.form_submit_button("Crear", use_container_width=True):
                if nombre_cat.strip():
                    srv.registrar_categoria(Categoria(
                        nombre=nombre_cat.strip(), tipo=tipo_cat, activa=True
                    ))
                    st.success("Categoría creada.")
                    st.rerun()
                else:
                    st.warning("El nombre no puede estar vacío.")

    with col_b:
        df_cats = srv.obtener_categorias(solo_activas=True)
        if df_cats.empty:
            st.info("No hay categorías. Crea la primera al lado.")
        else:
            for tipo_x in ["ingreso", "gasto", "ahorro", "inversion"]:
                df_t = df_cats[df_cats['tipo'] == tipo_x]
                if df_t.empty:
                    continue
                with st.expander(f"**{tipo_x.capitalize()}** ({len(df_t)})", expanded=False):
                    for _, c in df_t.iterrows():
                        cc = st.columns([5, 1])
                        cc[0].write(f"• {c['nombre']}")
                        if cc[1].button("🗑️", key=f"del_cat_{c['id']}"):
                            srv.desactivar_categoria(int(c['id']))
                            st.rerun()
