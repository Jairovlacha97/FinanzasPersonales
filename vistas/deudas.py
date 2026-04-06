import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv
from models import Deuda, PagoDeuda

st.title("💳 Control de Deudas y Créditos")

# --- CARGA DE DATOS MAESTROS ---
df_deudas = srv.obtener_deudas()
df_pagos = srv.obtener_pagos_deudas()

# --- SECCIÓN A: RESUMEN GLOBAL ---
st.header("📊 Resumen General")

total_prestado = df_deudas['monto_inicial'].sum() if not df_deudas.empty else 0
total_capital_pagado = df_pagos['abono_capital'].sum() if not df_pagos.empty else 0
total_intereses_pagados = df_pagos['intereses_seguros'].sum() if not df_pagos.empty else 0
saldo_pendiente = total_prestado - total_capital_pagado

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Total Deuda Actual (Saldo)", f"${saldo_pendiente:,.0f}")
col_m2.metric("Capital Abonado (Histórico)", f"${total_capital_pagado:,.0f}")
# Usamos inverse en intereses para recordar que es plata "quemada"
col_m3.metric("Intereses y Seguros Pagados", f"${total_intereses_pagados:,.0f}", delta_color="inverse")

st.divider()

# --- SECCIÓN B: GESTIÓN (PESTAÑAS) ---
st.header("⚙️ Gestión de Créditos")

tab_pagar, tab_nueva = st.tabs(["📝 Registrar Pago de Cuota", "➕ Agregar Nueva Deuda"])

with tab_nueva:
    st.subheader("Dar de alta un nuevo crédito")
    with st.form("form_nueva_deuda", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre_deuda = st.text_input("Nombre del Crédito (Ej: Carro, Libre Inversión)")
            monto_inicial = st.number_input("Monto Total Prestado ($)", min_value=0.0, step=1000000.0)
        with col2:
            cuotas_totales = st.number_input("Número total de cuotas pactadas", min_value=1, step=1)
        
        submit_deuda = st.form_submit_button("Guardar Crédito")
        if submit_deuda:
            if nombre_deuda.strip() != "" and monto_inicial > 0:
                nueva_deuda = Deuda(nombre=nombre_deuda, monto_inicial=monto_inicial, cuotas_totales=cuotas_totales)
                srv.registrar_deuda(nueva_deuda)
                st.success("✅ Crédito registrado. Ya puedes registrarle pagos.")
                st.rerun()
            else:
                st.warning("Revisa que el nombre no esté vacío y el monto sea mayor a 0.")

with tab_pagar:
    st.subheader("Registrar abono mensual")
    if df_deudas.empty:
        st.info("Primero debes registrar una deuda en la pestaña de al lado.")
    else:
        # Preparamos los diccionarios para los Selectbox
        deudas_activas = df_deudas[df_deudas['activa'] == True]
        mapa_deudas = {row['nombre']: row['id'] for _, row in deudas_activas.iterrows()}
        
        df_cuentas = srv.obtener_cuentas()
        mapa_cuentas = {f"{r['nombre']} ({r['tipo']})": r['nombre'] for _, r in df_cuentas.iterrows()} if not df_cuentas.empty else {"Efectivo (Débito)": "Efectivo"}
        
        with st.form("form_nuevo_pago", clear_on_submit=True):
            col_p1, col_p2 = st.columns(2)
            
            with col_p1:
                deuda_seleccionada = st.selectbox("Selecciona el Crédito", list(mapa_deudas.keys()))
                fecha_pago = st.date_input("Fecha de Pago", datetime.date.today())
                cuenta_display = st.selectbox("¿Desde qué cuenta pagaste?", list(mapa_cuentas.keys()))
                
            with col_p2:
                abono_cap = st.number_input("Abono a Capital ($) - Reduce deuda", min_value=0.0, step=10000.0)
                int_seg = st.number_input("Intereses y Seguros ($) - Gasto del banco", min_value=0.0, step=10000.0)
                
            submit_pago = st.form_submit_button("Registrar Cuota")
            if submit_pago:
                if abono_cap > 0 or int_seg > 0:
                    nuevo_pago = PagoDeuda(
                        deuda_id=mapa_deudas[deuda_seleccionada],
                        fecha=fecha_pago,
                        abono_capital=abono_cap,
                        intereses_seguros=int_seg,
                        cuenta_origen=mapa_cuentas[cuenta_display]
                    )
                    srv.registrar_pago_deuda(nuevo_pago)
                    st.success("✅ Pago registrado correctamente.")
                    st.rerun()
                else:
                    st.warning("La suma del abono a capital e intereses debe ser mayor a 0.")

st.divider()

# --- SECCIÓN C: PROGRESO E HISTORIAL ---
st.header("📈 Progreso de tus Créditos")

if not df_deudas.empty and not df_pagos.empty:
    # Agrupamos los pagos por deuda para saber cuánto se ha abonado a cada una
    pagos_agrupados = df_pagos.groupby('deuda_id')['abono_capital'].sum().reset_index()
    
    # Cruzamos esta suma con la tabla maestra de deudas
    df_progreso = df_deudas.merge(pagos_agrupados, left_on='id', right_on='deuda_id', how='left')
    df_progreso['abono_capital'] = df_progreso['abono_capital'].fillna(0) # Si no hay pagos, es 0
    df_progreso['porcentaje'] = (df_progreso['abono_capital'] / df_progreso['monto_inicial']) * 100

    # Mostramos el progreso visual para cada crédito activo
    for _, fila in df_progreso[df_progreso['activa'] == True].iterrows():
        st.write(f"**{fila['nombre']}** - Progreso de pago: {fila['porcentaje']:.1f}%")
        st.progress(min(fila['porcentaje'] / 100, 1.0))
        st.caption(f"Abonado: ${fila['abono_capital']:,.0f} / Total: ${fila['monto_inicial']:,.0f}")
        st.write("")
        
    st.divider()
    
    st.subheader("🗂️ Historial Detallado de Pagos")
    
    # Formateamos la tabla para que se vea bonita
    df_pagos_mostrar = df_pagos.copy()
    df_pagos_mostrar['Pago Total Cuota'] = df_pagos_mostrar['abono_capital'] + df_pagos_mostrar['intereses_seguros']
    df_pagos_mostrar = df_pagos_mostrar.rename(columns={
        'nombre_deuda': 'Crédito', 'fecha': 'Fecha', 
        'abono_capital': 'Abono a Capital', 'intereses_seguros': 'Intereses/Seguros',
        'cuenta_origen': 'Pagado Desde'
    })
    
    # Ordenamos del más reciente al más antiguo y quitamos columnas de IDs técnicos
    df_pagos_mostrar = df_pagos_mostrar.sort_values(by='Fecha', ascending=False)
    columnas_visibles = ['Fecha', 'Crédito', 'Abono a Capital', 'Intereses/Seguros', 'Pago Total Cuota', 'Pagado Desde']
    st.dataframe(df_pagos_mostrar[columnas_visibles], use_container_width=True, hide_index=True)

else:
    st.info("Aún no hay suficiente información para mostrar el progreso. Agrega una deuda y registra pagos.")