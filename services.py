import pandas as pd
import datetime
import streamlit as st
from supabase import create_client, Client
import requests
from models import Gasto, Deuda, PagoDeuda, Ahorro, MovimientoAhorro, ActivoInversion, TransaccionInversion, Ingreso

# --- CONFIGURACIÓN DE SUPABASE ---
# Nos conectamos a Supabase leyendo los secretos de Streamlit
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)


# --- FUNCIONES DE AUTENTICACIÓN ---
def iniciar_sesion(email, password):
    """Verifica las credenciales en Supabase Auth."""
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def cerrar_sesion():
    """Cierra la sesión en el servidor de Supabase."""
    supabase.auth.sign_out()


# --- FUNCIONES DE ESCRITURA ---
def registrar_gasto(gasto: Gasto):
    """Envía el registro a la base de datos de Supabase."""
    datos = {
        "fecha": str(gasto.fecha),
        "categoria": gasto.categoria,
        "descripcion": gasto.descripcion,
        "valor": gasto.valor,
        "tarjeta": gasto.tarjeta
    }
    supabase.table("gastos").insert(datos).execute()


# --- FUNCIONES DE LECTURA ---
def obtener_gastos_mes_actual() -> pd.DataFrame:
    """Consulta Supabase filtrando por el rango del mes actual."""
    hoy = datetime.date.today()
    
    # Calculamos el primer día del mes actual
    primer_dia = hoy.replace(day=1)
    
    # Calculamos el primer día del próximo mes
    if hoy.month == 12:
        proximo_mes = hoy.replace(year=hoy.year + 1, month=1, day=1)
    else:
        proximo_mes = hoy.replace(month=hoy.month + 1, day=1)
    
    # Consulta a Supabase
    respuesta = supabase.table("gastos").select("*") \
        .gte("fecha", str(primer_dia)) \
        .lt("fecha", str(proximo_mes)) \
        .order("fecha", desc=True) \
        .execute()
    
    df = pd.DataFrame(respuesta.data)
    
    if not df.empty:
        # Renombramos las columnas para que la tabla y gráficos de Streamlit se vean bien
        df = df.rename(columns={
            'fecha': 'Fecha', 
            'categoria': 'Categoría', 
            'descripcion': 'Descripción', 
            'valor': 'Valor', 
            'tarjeta': 'Tarjeta'
        })
        # Ocultamos el ID autogenerado
        df = df.drop(columns=['id'])
    else:
        df = pd.DataFrame(columns=['Fecha', 'Categoría', 'Descripción', 'Valor', 'Tarjeta'])
        
    return df

def obtener_descripciones_unicas() -> list:
    """Consulta Supabase y devuelve una lista alfabética de descripciones (locales) únicas."""
    respuesta = supabase.table("gastos").select("descripcion").execute()
    
    # Extraemos los textos y usamos set() para eliminar duplicados
    lista_descripciones = [item['descripcion'] for item in respuesta.data]
    descripciones_unicas = sorted(list(set(lista_descripciones)))
    
    return descripciones_unicas

def obtener_cuentas() -> pd.DataFrame:
    """Consulta Supabase y devuelve todas las cuentas y sus tipos."""
    respuesta = supabase.table("cuentas").select("*").execute()
    df = pd.DataFrame(respuesta.data)
    return df

# --- FUNCIONES DE DEUDAS Y PAGOS ---

def registrar_deuda(deuda: Deuda):
    """Crea un nuevo crédito en la base de datos."""
    datos = {
        "nombre": deuda.nombre,
        "monto_inicial": deuda.monto_inicial,
        "cuotas_totales": deuda.cuotas_totales,
        "activa": deuda.activa
    }
    supabase.table("deudas").insert(datos).execute()

def obtener_deudas() -> pd.DataFrame:
    """Obtiene el catálogo de todas las deudas."""
    respuesta = supabase.table("deudas").select("*").execute()
    df = pd.DataFrame(respuesta.data)
    return df

def registrar_pago_deuda(pago: PagoDeuda):
    """Registra una cuota pagada."""
    datos = {
        "deuda_id": pago.deuda_id,
        "fecha": str(pago.fecha),
        "abono_capital": pago.abono_capital,
        "intereses_seguros": pago.intereses_seguros,
        "cuenta_origen": pago.cuenta_origen
    }
    supabase.table("pagos_deuda").insert(datos).execute()

def obtener_pagos_deudas() -> pd.DataFrame:
    """Obtiene el historial de pagos cruzando con el nombre de la deuda."""
    # En Supabase, usamos la relación creada con la foreign key para traer el nombre
    respuesta = supabase.table("pagos_deuda").select("*, deudas(nombre)").execute()
    
    # Aplanamos la respuesta porque Supabase devuelve el nombre anidado
    datos_aplanados = []
    for item in respuesta.data:
        fila = item.copy()
        fila['nombre_deuda'] = item['deudas']['nombre'] if item.get('deudas') else 'Desconocida'
        del fila['deudas']
        datos_aplanados.append(fila)
        
    df = pd.DataFrame(datos_aplanados)
    return df

def registrar_ahorro(ahorro: Ahorro):
    supabase.table("ahorros").insert({"nombre": ahorro.nombre, "meta": ahorro.meta}).execute()

def obtener_ahorros() -> pd.DataFrame:
    respuesta = supabase.table("ahorros").select("*").execute()
    return pd.DataFrame(respuesta.data)

def registrar_movimiento_ahorro(mov: MovimientoAhorro):
    datos = {
        "ahorro_id": mov.ahorro_id,
        "fecha": str(mov.fecha),
        "tipo": mov.tipo,
        "monto": mov.monto,
        "cuenta_relacionada": mov.cuenta_relacionada
    }
    supabase.table("movimientos_ahorro").insert(datos).execute()

def obtener_movimientos_ahorro() -> pd.DataFrame:
    respuesta = supabase.table("movimientos_ahorro").select("*, ahorros(nombre)").execute()
    datos = []
    for item in respuesta.data:
        f = item.copy()
        f['nombre_ahorro'] = item['ahorros']['nombre']
        datos.append(f)
    return pd.DataFrame(datos)

# --- FUNCIONES DE INVERSIONES ---
def registrar_activo(activo: ActivoInversion):
    datos = {"ticker": activo.ticker, "nombre": activo.nombre, "tipo": activo.tipo}
    supabase.table("activos_inversion").insert(datos).execute()

def obtener_activos() -> pd.DataFrame:
    respuesta = supabase.table("activos_inversion").select("*").execute()
    return pd.DataFrame(respuesta.data)

def registrar_transaccion_inversion(trans: TransaccionInversion):
    datos = {
        "activo_id": trans.activo_id,
        "fecha": str(trans.fecha),
        "tipo_operacion": trans.tipo_operacion,
        "cantidad": trans.cantidad,
        "precio_unitario": trans.precio_unitario,
        "cuenta_origen": trans.cuenta_origen
    }
    supabase.table("transacciones_inversion").insert(datos).execute()

def obtener_transacciones_inversion() -> pd.DataFrame:
    respuesta = supabase.table("transacciones_inversion").select("*, activos_inversion(ticker, nombre)").execute()
    datos = []
    for item in respuesta.data:
        f = item.copy()
        if item.get('activos_inversion'):
            f['ticker'] = item['activos_inversion']['ticker']
            f['nombre_activo'] = item['activos_inversion']['nombre']
        else:
            f['ticker'] = 'N/A'
            f['nombre_activo'] = 'Desconocido'
        del f['activos_inversion']
        datos.append(f)
    return pd.DataFrame(datos)

# --- FUNCIONES DE INGRESOS ---
def registrar_ingreso(ingreso: Ingreso):
    """Envía el registro de un nuevo ingreso a Supabase."""
    datos = {
        "fecha": str(ingreso.fecha),
        "categoria": ingreso.categoria,
        "descripcion": ingreso.descripcion,
        "valor": ingreso.valor,
        "cuenta_destino": ingreso.cuenta_destino
    }
    supabase.table("ingresos").insert(datos).execute()

def obtener_ingresos_mes_actual() -> pd.DataFrame:
    """Consulta los ingresos del mes actual."""
    hoy = datetime.date.today()
    primer_dia = hoy.replace(day=1)
    
    if hoy.month == 12:
        proximo_mes = hoy.replace(year=hoy.year + 1, month=1, day=1)
    else:
        proximo_mes = hoy.replace(month=hoy.month + 1, day=1)
    
    respuesta = supabase.table("ingresos").select("*") \
        .gte("fecha", str(primer_dia)) \
        .lt("fecha", str(proximo_mes)) \
        .order("fecha", desc=True) \
        .execute()
    
    df = pd.DataFrame(respuesta.data)
    
    if not df.empty:
        df = df.rename(columns={
            'fecha': 'Fecha', 
            'categoria': 'Categoría', 
            'descripcion': 'Descripción', 
            'valor': 'Valor', 
            'cuenta_destino': 'Cuenta Destino'
        })
        df = df.drop(columns=['id'])
    else:
        df = pd.DataFrame(columns=['Fecha', 'Categoría', 'Descripción', 'Valor', 'Cuenta Destino'])
        
    return df

# --- FUNCIONES DE TIPO DE CAMBIO ---
def obtener_trm_actual() -> float:
    """Obtiene la TRM actual de USD a COP conectándose a una API pública."""
    try:
        # API gratuita, sin necesidad de llaves o registros
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        respuesta = requests.get(url, timeout=5)
        datos = respuesta.json()
        trm = datos["rates"]["COP"]
        return float(trm)
    except Exception as e:
        # Si por alguna razón no hay internet o falla la API, devolvemos un valor de contingencia seguro
        st.sidebar.warning("⚠️ No se pudo obtener la TRM en vivo. Usando tasa de contingencia.")
        return 3900.0