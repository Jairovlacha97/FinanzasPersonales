import streamlit as st
import pandas as pd
import datetime
import altair as alt
import services as srv
from models import ActivoInversion, TransaccionInversion

st.title("📈 Portafolio de Inversiones")

# --- CARGA DE DATOS ---
df_activos = srv.obtener_activos()
df_trans = srv.obtener_transacciones_inversion()

# --- PROCESAMIENTO DE PORTAFOLIO ---
portafolio = {}
capital_total_invertido = 0.0

if not df_trans.empty and not df_activos.empty:
    mapa_tipos = {row['id']: row['tipo'] for _, row in df_activos.iterrows()}

    for _, fila in df_trans.iterrows():
        ticker = fila['ticker']
        cantidad = fila['cantidad']
        monto_total_operacion = cantidad * fila['precio_unitario']
        tipo_activo = mapa_tipos.get(fila['activo_id'], 'Desconocido')
        
        if ticker not in portafolio:
            portafolio[ticker] = {
                'titulos': 0.0, 
                'capital_aportado': 0.0, 
                'nombre': fila['nombre_activo'],
                'tipo': tipo_activo
            }
            
        if fila['tipo_operacion'] == 'Compra':
            portafolio[ticker]['titulos'] += cantidad
            portafolio[ticker]['capital_aportado'] += monto_total_operacion
            capital_total_invertido += monto_total_operacion
        else: # Venta
            portafolio[ticker]['titulos'] -= cantidad
            portafolio[ticker]['capital_aportado'] -= monto_total_operacion
            capital_total_invertido -= monto_total_operacion

# --- MÉTRICAS PRINCIPALES ---
st.metric("Capital Total Invertido", f"${capital_total_invertido:,.0f} (USD)")
st.caption("*Nota: Este es el valor de compra histórico. El valor de mercado actual dependerá de la cotización en bolsa del día.*")
st.divider()

# --- GESTIÓN DE INVERSIONES ---
tab_op, tab_nuevo = st.tabs(["🛒 Registrar Compra/Venta", "🆕 Agregar Nuevo Activo"])

with tab_nuevo:
    st.subheader("Dar de alta un instrumento financiero")
    with st.form("form_nuevo_activo", clear_on_submit=True):
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            ticker = st.text_input("Ticker / Símbolo", placeholder="Ej: QQQ, URA, BTC").upper()
        with col_a2:
            nombre = st.text_input("Nombre de la empresa o fondo")
        with col_a3:
            tipo = st.selectbox("Tipo de Activo", ["ETF", "Acción", "Bono", "Criptomoneda", "Fondo Mutuo", "Finca Raíz"])
            
        if st.form_submit_button("Guardar Activo"):
            if ticker and nombre:
                srv.registrar_activo(ActivoInversion(ticker=ticker, nombre=nombre, tipo=tipo))
                st.success(f"Activo {ticker} agregado a tu catálogo.")
                st.rerun()
            else:
                st.warning("El ticker y el nombre son obligatorios.")

with tab_op:
    if df_activos.empty:
        st.warning("Primero debes agregar un activo en la pestaña de al lado.")
    else:
        mapa_activos = {f"{r['ticker']} - {r['nombre']}": r['id'] for _, r in df_activos.iterrows()}
        df_cuentas = srv.obtener_cuentas()
        opciones_cuentas = df_cuentas['nombre'].tolist() if not df_cuentas.empty else ["Broker / Efectivo"]

        with st.form("form_transaccion", clear_on_submit=True):
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                activo_seleccionado = st.selectbox("Selecciona el Activo", list(mapa_activos.keys()))
                tipo_op = st.radio("Operación", ["Compra", "Venta"], horizontal=True)
                fecha = st.date_input("Fecha de ejecución", datetime.date.today())
            with col_t2:
                cantidad = st.number_input("Cantidad de Títulos", min_value=0.0001, format="%.4f")
                precio_unitario = st.number_input("Precio por Título ($)", min_value=0.0)
                cuenta = st.selectbox("¿Desde dónde fondeaste / A dónde retiraste?", opciones_cuentas)
            
            if st.form_submit_button("Confirmar Operación"):
                if cantidad > 0 and precio_unitario > 0:
                    id_activo = mapa_activos[activo_seleccionado]
                    trans = TransaccionInversion(
                        activo_id=id_activo, fecha=fecha, tipo_operacion=tipo_op, 
                        cantidad=cantidad, precio_unitario=precio_unitario, cuenta_origen=cuenta
                    )
                    srv.registrar_transaccion_inversion(trans)
                    st.success("Operación registrada en el portafolio.")
                    st.rerun()
                else:
                    st.warning("La cantidad y el precio deben ser mayores a cero.")

st.divider()

# --- ANÁLISIS DE PORTAFOLIO (GRÁFICOS) ---
if portafolio:
    df_portafolio = pd.DataFrame([
        {
            'Ticker': t, 
            'Nombre': datos['nombre'],
            'Clase de Activo': datos['tipo'],
            'Capital Aportado': datos['capital_aportado'], 
            'Títulos': datos['titulos']
        }
        for t, datos in portafolio.items() if datos['titulos'] > 0
    ])
    
    if not df_portafolio.empty:
        
        # 1. Gráfico Macro: Distribución por Categoría (Movido arriba)
        st.subheader("🥧 Visión Macro (Asset Allocation)")
        df_categorias = df_portafolio.groupby('Clase de Activo')['Capital Aportado'].sum().reset_index()
        
        col_macro1, col_macro2, col_macro3 = st.columns([1, 2, 1])
        with col_macro2:
            grafico_cat = alt.Chart(df_categorias).mark_arc(innerRadius=60).encode(
                theta=alt.Theta(field="Capital Aportado", type="quantitative"),
                color=alt.Color(field="Clase de Activo", type="nominal", scale=alt.Scale(scheme='set2')),
                tooltip=['Clase de Activo', alt.Tooltip('Capital Aportado', format='$,.0f')]
            ).properties(title="Distribución Total de tu Patrimonio")
            
            st.altair_chart(grafico_cat, use_container_width=True)
            
        st.divider()

        # 2. Gráficos por Categoría Específica (Barras horizontales)
        st.subheader("📊 Composición Detallada por Categoría")
        categorias = df_portafolio['Clase de Activo'].unique()
        
        cols = st.columns(2)
        
        for index, categoria in enumerate(categorias):
            df_sub = df_portafolio[df_portafolio['Clase de Activo'] == categoria]
            
            # Construimos el gráfico base de barras horizontales
            base_sub = alt.Chart(df_sub).encode(
                x=alt.X('Capital Aportado:Q', title='', axis=None), # Ocultamos el eje X
                y=alt.Y('Ticker:N', sort='-x', title='')            # sort='-x' ordena de mayor a menor
            )
            
            # Dibujamos las barras (con colores distintos por ticker)
            barras_sub = base_sub.mark_bar().encode(
                color=alt.Color('Ticker:N', legend=None, scale=alt.Scale(scheme='tableau20'))
            )
            
            # Añadimos las etiquetas de texto
            texto_sub = base_sub.mark_text(
                align='left',
                baseline='middle',
                dx=3
            ).encode(
                text=alt.Text('Capital Aportado:Q', format='$,.0f')
            )
            
            # Juntamos barra + texto
            grafico_final_sub = (barras_sub + texto_sub).properties(title=f"{categoria}")
            
            with cols[index % 2]:
                st.altair_chart(grafico_final_sub, use_container_width=True)

        st.divider()

        # 3. Tabla de Posiciones
        st.subheader("🗂️ Posiciones Actuales Detalladas")
        st.dataframe(
            df_portafolio.style.format({'Capital Aportado': '${:,.2f}', 'Títulos': '{:,.4f}'}),
            use_container_width=True, hide_index=True
        )
else:
    st.info("Registra tu primera compra para ver el análisis de tu portafolio.")