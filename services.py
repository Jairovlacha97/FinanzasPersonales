import pandas as pd
import datetime
import streamlit as st
from supabase import create_client, Client
import requests
from models import (
    Gasto, Deuda, PagoDeuda, Ahorro, MovimientoAhorro,
    ActivoInversion, TransaccionInversion, Ingreso,
    Categoria, Presupuesto, ItemRecurrente, ItemPlaneado,
)

# --- CONFIGURACIÓN DE SUPABASE ---
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
    primer_dia = hoy.replace(day=1)
    if hoy.month == 12:
        proximo_mes = hoy.replace(year=hoy.year + 1, month=1, day=1)
    else:
        proximo_mes = hoy.replace(month=hoy.month + 1, day=1)

    respuesta = supabase.table("gastos").select("*") \
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
            'tarjeta': 'Tarjeta'
        })
        df = df.drop(columns=['id'])
    else:
        df = pd.DataFrame(columns=['Fecha', 'Categoría', 'Descripción', 'Valor', 'Tarjeta'])
    return df

def obtener_descripciones_unicas() -> list:
    """Consulta Supabase y devuelve una lista alfabética de descripciones (locales) únicas."""
    respuesta = supabase.table("gastos").select("descripcion").execute()
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
    datos = {
        "nombre": deuda.nombre,
        "monto_inicial": deuda.monto_inicial,
        "cuotas_totales": deuda.cuotas_totales,
        "activa": deuda.activa
    }
    supabase.table("deudas").insert(datos).execute()

def obtener_deudas() -> pd.DataFrame:
    respuesta = supabase.table("deudas").select("*").execute()
    return pd.DataFrame(respuesta.data)

def registrar_pago_deuda(pago: PagoDeuda):
    datos = {
        "deuda_id": pago.deuda_id,
        "fecha": str(pago.fecha),
        "abono_capital": pago.abono_capital,
        "intereses_seguros": pago.intereses_seguros,
        "cuenta_origen": pago.cuenta_origen
    }
    supabase.table("pagos_deuda").insert(datos).execute()

def obtener_pagos_deudas() -> pd.DataFrame:
    respuesta = supabase.table("pagos_deuda").select("*, deudas(nombre)").execute()
    datos_aplanados = []
    for item in respuesta.data:
        fila = item.copy()
        fila['nombre_deuda'] = item['deudas']['nombre'] if item.get('deudas') else 'Desconocida'
        del fila['deudas']
        datos_aplanados.append(fila)
    return pd.DataFrame(datos_aplanados)


# --- AHORROS ---
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


# --- INVERSIONES ---
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


# --- INGRESOS ---
def registrar_ingreso(ingreso: Ingreso):
    datos = {
        "fecha": str(ingreso.fecha),
        "categoria": ingreso.categoria,
        "descripcion": ingreso.descripcion,
        "valor": ingreso.valor,
        "cuenta_destino": ingreso.cuenta_destino
    }
    supabase.table("ingresos").insert(datos).execute()

def obtener_ingresos_mes_actual() -> pd.DataFrame:
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


# --- TIPO DE CAMBIO ---
def obtener_trm_actual() -> float:
    """Obtiene la TRM actual de USD a COP."""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        respuesta = requests.get(url, timeout=5)
        datos = respuesta.json()
        trm = datos["rates"]["COP"]
        return float(trm)
    except Exception:
        st.sidebar.warning("⚠️ No se pudo obtener la TRM en vivo. Usando tasa de contingencia.")
        return 3900.0


# =====================================================================
# UTILIDADES DE FECHAS PARA PRESUPUESTOS Y PREVISIÓN
# =====================================================================
def _ym(d: datetime.date) -> str:
    return d.strftime("%Y-%m")

def _ym_to_first_day(year_month: str) -> datetime.date:
    y, m = year_month.split("-")
    return datetime.date(int(y), int(m), 1)

def _next_ym(year_month: str) -> str:
    d = _ym_to_first_day(year_month)
    if d.month == 12:
        return f"{d.year + 1}-01"
    return f"{d.year}-{d.month + 1:02d}"

def _prev_ym(year_month: str) -> str:
    d = _ym_to_first_day(year_month)
    if d.month == 1:
        return f"{d.year - 1}-12"
    return f"{d.year}-{d.month - 1:02d}"

def _ym_actual() -> str:
    return _ym(datetime.date.today())

def _ym_proximo() -> str:
    return _next_ym(_ym_actual())

def _rango_meses_atras(year_month: str, n: int) -> list:
    """Devuelve los n meses anteriores a year_month (sin incluirlo)."""
    meses = []
    cursor = year_month
    for _ in range(n):
        cursor = _prev_ym(cursor)
        meses.append(cursor)
    meses.reverse()
    return meses


# =====================================================================
# CRUD: CATEGORÍAS
# =====================================================================
def obtener_categorias(tipo: str = None, solo_activas: bool = True) -> pd.DataFrame:
    q = supabase.table("categorias").select("*")
    if solo_activas:
        q = q.eq("activa", True)
    if tipo:
        q = q.eq("tipo", tipo)
    respuesta = q.order("nombre").execute()
    return pd.DataFrame(respuesta.data)

def obtener_categorias_por_tipo(tipo: str) -> list:
    df = obtener_categorias(tipo=tipo, solo_activas=True)
    if df.empty:
        return []
    return sorted(df['nombre'].tolist())

def registrar_categoria(cat: Categoria):
    datos = {"nombre": cat.nombre, "tipo": cat.tipo, "activa": cat.activa}
    supabase.table("categorias").upsert(datos, on_conflict="nombre,tipo").execute()

def desactivar_categoria(id_categoria: int):
    supabase.table("categorias").update({"activa": False}).eq("id", id_categoria).execute()


# =====================================================================
# CRUD: PRESUPUESTOS (por mes y categoría)
# =====================================================================
def obtener_presupuestos(year_month: str, tipo: str = None) -> pd.DataFrame:
    q = supabase.table("presupuestos").select("*").eq("year_month", year_month)
    if tipo:
        q = q.eq("tipo", tipo)
    respuesta = q.execute()
    return pd.DataFrame(respuesta.data)

def guardar_presupuesto(p: Presupuesto):
    datos = {
        "year_month": p.year_month,
        "categoria": p.categoria,
        "tipo": p.tipo,
        "monto": float(p.monto),
        "nota": p.nota,
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }
    supabase.table("presupuestos").upsert(
        datos, on_conflict="year_month,categoria,tipo"
    ).execute()

def eliminar_presupuesto(id_presupuesto: int):
    supabase.table("presupuestos").delete().eq("id", id_presupuesto).execute()

def copiar_presupuestos_de_mes(year_month_origen: str, year_month_destino: str):
    df = obtener_presupuestos(year_month_origen)
    if df.empty:
        return 0
    filas = []
    for _, r in df.iterrows():
        filas.append({
            "year_month": year_month_destino,
            "categoria": r["categoria"],
            "tipo": r["tipo"],
            "monto": float(r["monto"]),
            "nota": r.get("nota"),
        })
    supabase.table("presupuestos").upsert(
        filas, on_conflict="year_month,categoria,tipo"
    ).execute()
    return len(filas)


# =====================================================================
# CRUD: ITEMS RECURRENTES
# =====================================================================
def obtener_items_recurrentes(solo_activos: bool = True) -> pd.DataFrame:
    q = supabase.table("items_recurrentes").select("*")
    if solo_activos:
        q = q.eq("activo", True)
    respuesta = q.order("tipo").order("nombre").execute()
    return pd.DataFrame(respuesta.data)

def registrar_item_recurrente(item: ItemRecurrente):
    datos = {
        "nombre": item.nombre,
        "tipo": item.tipo,
        "categoria": item.categoria,
        "monto_estimado": float(item.monto_estimado),
        "frecuencia": item.frecuencia,
        "dia_mes": item.dia_mes,
        "cuenta_relacionada": item.cuenta_relacionada,
        "fecha_inicio": str(item.fecha_inicio),
        "fecha_fin": str(item.fecha_fin) if item.fecha_fin else None,
        "activo": item.activo,
    }
    supabase.table("items_recurrentes").insert(datos).execute()

def actualizar_item_recurrente(id_item: int, campos: dict):
    supabase.table("items_recurrentes").update(campos).eq("id", id_item).execute()

def eliminar_item_recurrente(id_item: int):
    """Soft delete: marca como inactivo."""
    supabase.table("items_recurrentes").update({"activo": False}).eq("id", id_item).execute()

def _items_recurrentes_vigentes(year_month: str) -> pd.DataFrame:
    df = obtener_items_recurrentes(solo_activos=True)
    if df.empty:
        return df
    primer_dia = _ym_to_first_day(year_month)
    ultimo_dia = _ym_to_first_day(_next_ym(year_month)) - datetime.timedelta(days=1)

    def parse_fecha(v):
        if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
            return None
        if isinstance(v, datetime.date):
            return v
        try:
            return datetime.date.fromisoformat(str(v)[:10])
        except Exception:
            return None

    df = df.copy()
    df["fecha_inicio_d"] = df["fecha_inicio"].apply(parse_fecha)
    if "fecha_fin" in df.columns:
        df["fecha_fin_d"] = df["fecha_fin"].apply(parse_fecha)
    else:
        df["fecha_fin_d"] = None

    def cubre(row):
        fi = row["fecha_inicio_d"]
        ff = row["fecha_fin_d"]
        if fi is None:
            return False
        if fi > ultimo_dia:
            return False
        if ff is not None and ff < primer_dia:
            return False
        return True

    return df[df.apply(cubre, axis=1)].copy()

def _monto_mensual_recurrente(row) -> float:
    monto = float(row["monto_estimado"])
    frecuencia = row.get("frecuencia", "mensual")
    if frecuencia == "quincenal":
        return monto * 2
    if frecuencia == "anual":
        return monto / 12
    return monto


# =====================================================================
# CRUD: ITEMS PLANEADOS
# =====================================================================
def obtener_items_planeados(year_month: str) -> pd.DataFrame:
    respuesta = supabase.table("items_planeados").select("*") \
        .eq("year_month", year_month).order("tipo").execute()
    return pd.DataFrame(respuesta.data)

def registrar_item_planeado(item: ItemPlaneado):
    datos = {
        "year_month": item.year_month,
        "nombre": item.nombre,
        "tipo": item.tipo,
        "categoria": item.categoria,
        "monto": float(item.monto),
        "nota": item.nota,
    }
    supabase.table("items_planeados").insert(datos).execute()

def eliminar_item_planeado(id_item: int):
    supabase.table("items_planeados").delete().eq("id", id_item).execute()


# =====================================================================
# DATOS HISTÓRICOS PARA PROMEDIOS (rolling)
# =====================================================================
def obtener_gastos_por_categoria_mensual(meses: list) -> pd.DataFrame:
    if not meses:
        return pd.DataFrame(columns=["year_month", "categoria", "valor"])
    primer_mes = sorted(meses)[0]
    ultimo_mes = sorted(meses)[-1]
    fecha_desde = _ym_to_first_day(primer_mes)
    fecha_hasta = _ym_to_first_day(_next_ym(ultimo_mes))

    respuesta = supabase.table("gastos").select("fecha,categoria,valor") \
        .gte("fecha", str(fecha_desde)) \
        .lt("fecha", str(fecha_hasta)).execute()

    df = pd.DataFrame(respuesta.data)
    if df.empty:
        return pd.DataFrame(columns=["year_month", "categoria", "valor"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["year_month"] = df["fecha"].dt.strftime("%Y-%m")
    return df.groupby(["year_month", "categoria"], as_index=False)["valor"].sum()

def obtener_ingresos_por_categoria_mensual(meses: list) -> pd.DataFrame:
    if not meses:
        return pd.DataFrame(columns=["year_month", "categoria", "valor"])
    primer_mes = sorted(meses)[0]
    ultimo_mes = sorted(meses)[-1]
    fecha_desde = _ym_to_first_day(primer_mes)
    fecha_hasta = _ym_to_first_day(_next_ym(ultimo_mes))

    respuesta = supabase.table("ingresos").select("fecha,categoria,valor") \
        .gte("fecha", str(fecha_desde)) \
        .lt("fecha", str(fecha_hasta)).execute()

    df = pd.DataFrame(respuesta.data)
    if df.empty:
        return pd.DataFrame(columns=["year_month", "categoria", "valor"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["year_month"] = df["fecha"].dt.strftime("%Y-%m")
    return df.groupby(["year_month", "categoria"], as_index=False)["valor"].sum()

def promedio_gastos_por_categoria(meses_historico: int = 3, hasta_year_month: str = None) -> pd.DataFrame:
    if hasta_year_month is None:
        hasta_year_month = _ym_actual()
    meses = _rango_meses_atras(hasta_year_month, meses_historico)
    df = obtener_gastos_por_categoria_mensual(meses)
    if df.empty:
        return pd.DataFrame(columns=["categoria", "promedio"])
    agg = df.groupby("categoria", as_index=False)["valor"].sum()
    agg["promedio"] = agg["valor"] / meses_historico
    return agg[["categoria", "promedio"]]


# =====================================================================
# DEUDAS: cuotas proyectadas
# =====================================================================
def proyectar_cuota_deuda(deuda_id: int) -> dict:
    """Estima la próxima cuota de una deuda basándose en pagos anteriores."""
    respuesta_deuda = supabase.table("deudas").select("*").eq("id", deuda_id).execute()
    if not respuesta_deuda.data:
        return {"capital_estimado": 0.0, "intereses_estimados": 0.0, "total_estimado": 0.0}
    deuda = respuesta_deuda.data[0]

    respuesta_pagos = supabase.table("pagos_deuda").select("*") \
        .eq("deuda_id", deuda_id).order("fecha", desc=True).limit(3).execute()
    pagos = respuesta_pagos.data

    if pagos:
        n = len(pagos)
        cap = sum(float(p["abono_capital"]) for p in pagos) / n
        intr = sum(float(p["intereses_seguros"]) for p in pagos) / n
        return {
            "capital_estimado": cap,
            "intereses_estimados": intr,
            "total_estimado": cap + intr,
        }

    monto_inicial = float(deuda["monto_inicial"])
    cuotas = max(int(deuda["cuotas_totales"]), 1)
    cuota_aprox = monto_inicial / cuotas
    return {
        "capital_estimado": cuota_aprox,
        "intereses_estimados": 0.0,
        "total_estimado": cuota_aprox,
    }

def proyectar_cuotas_todas_las_deudas() -> pd.DataFrame:
    """Versión optimizada: 2 queries en total (antes era 2×N).
    1. Trae todas las deudas activas.
    2. Trae todos los pagos de esas deudas en una sola llamada.
    El resto se calcula en memoria.
    """
    df_deudas = obtener_deudas()
    if df_deudas.empty:
        return pd.DataFrame(columns=[
            "id", "nombre", "capital_estimado", "intereses_estimados", "total_estimado"
        ])
    df_deudas = df_deudas[df_deudas["activa"] == True].copy()
    if df_deudas.empty:
        return pd.DataFrame(columns=[
            "id", "nombre", "capital_estimado", "intereses_estimados", "total_estimado"
        ])

    # Una sola query para todos los pagos de las deudas activas
    ids_activas = [int(i) for i in df_deudas["id"].tolist()]
    resp_pagos = supabase.table("pagos_deuda").select("*") \
        .in_("deuda_id", ids_activas).order("fecha", desc=True).execute()
    df_pagos = pd.DataFrame(resp_pagos.data) if resp_pagos.data else pd.DataFrame()

    filas = []
    for _, d in df_deudas.iterrows():
        deuda_id = int(d["id"])

        if not df_pagos.empty and "deuda_id" in df_pagos.columns:
            ultimos = df_pagos[df_pagos["deuda_id"] == deuda_id].head(3)
        else:
            ultimos = pd.DataFrame()

        if not ultimos.empty:
            n = len(ultimos)
            cap = ultimos["abono_capital"].astype(float).sum() / n
            intr = ultimos["intereses_seguros"].astype(float).sum() / n
        else:
            cap = float(d["monto_inicial"]) / max(int(d["cuotas_totales"]), 1)
            intr = 0.0

        filas.append({
            "id": deuda_id,
            "nombre": d["nombre"],
            "capital_estimado": cap,
            "intereses_estimados": intr,
            "total_estimado": cap + intr,
        })
    return pd.DataFrame(filas)


def items_recurrentes_de_deuda(year_month: str) -> pd.DataFrame:
    """Recurrentes con tipo='pago_deuda' vigentes para el mes.
    Su 'categoria' debe ser el nombre exacto de una deuda existente.
    """
    df = _items_recurrentes_vigentes(year_month)
    if df.empty:
        return df
    return df[df["tipo"] == "pago_deuda"].copy()


def proyectar_cuotas_con_recurrentes(year_month: str) -> pd.DataFrame:
    """Variante que respeta la voluntad del usuario:
    - Si una deuda tiene un Item Recurrente vigente, usa ese monto como cuota
      total y reparte capital/intereses según el ratio histórico (si existe).
    - Si no, cae al promedio histórico (como antes).
    """
    base = proyectar_cuotas_todas_las_deudas()
    if base.empty:
        return pd.DataFrame(columns=[
            "id", "nombre", "capital_estimado", "intereses_estimados",
            "total_estimado", "fuente",
        ])
    base = base.copy()
    base["fuente"] = "histórico"

    df_rec_deuda = items_recurrentes_de_deuda(year_month)
    if df_rec_deuda.empty:
        return base

    mapa_rec = {}
    for _, r in df_rec_deuda.iterrows():
        nombre_deuda = r["categoria"]
        monto_mensual = _monto_mensual_recurrente(r)
        mapa_rec[nombre_deuda] = mapa_rec.get(nombre_deuda, 0.0) + monto_mensual

    rows = []
    for _, c in base.iterrows():
        nombre = c["nombre"]
        if nombre in mapa_rec:
            cap_h = float(c["capital_estimado"])
            int_h = float(c["intereses_estimados"])
            total_h = cap_h + int_h
            nuevo_total = float(mapa_rec[nombre])
            if total_h > 0:
                ratio_cap = cap_h / total_h
                nuevo_cap = nuevo_total * ratio_cap
                nuevo_int = nuevo_total - nuevo_cap
            else:
                nuevo_cap = nuevo_total
                nuevo_int = 0.0
            rows.append({
                "id": int(c["id"]),
                "nombre": nombre,
                "capital_estimado": nuevo_cap,
                "intereses_estimados": nuevo_int,
                "total_estimado": nuevo_total,
                "fuente": "recurrente",
            })
        else:
            rows.append({
                "id": int(c["id"]),
                "nombre": nombre,
                "capital_estimado": float(c["capital_estimado"]),
                "intereses_estimados": float(c["intereses_estimados"]),
                "total_estimado": float(c["total_estimado"]),
                "fuente": "histórico",
            })
    return pd.DataFrame(rows)


# =====================================================================
# CÁLCULO DE PREVISIÓN PARA UN MES
# =====================================================================
def calcular_prevision_mes(year_month: str, meses_historico: int = 3) -> dict:
    """Construye la previsión completa para un mes objetivo."""
    detalle = []

    # 1. Items recurrentes vigentes
    df_rec = _items_recurrentes_vigentes(year_month)
    cats_cubiertas_por_recurrente = set()
    if not df_rec.empty:
        for _, r in df_rec.iterrows():
            monto_mensual = _monto_mensual_recurrente(r)
            detalle.append({
                "tipo": r["tipo"],
                "categoria": r["categoria"],
                "monto": monto_mensual,
                "origen": "Recurrente",
                "nombre": r["nombre"],
            })
            if r["tipo"] == "gasto":
                cats_cubiertas_por_recurrente.add(r["categoria"])

    # 2. Items planeados del mes
    df_plan = obtener_items_planeados(year_month)
    cats_cubiertas_por_planeado = set()
    if not df_plan.empty:
        for _, p in df_plan.iterrows():
            detalle.append({
                "tipo": p["tipo"],
                "categoria": p["categoria"],
                "monto": float(p["monto"]),
                "origen": "Planeado",
                "nombre": p["nombre"],
            })
            if p["tipo"] == "gasto":
                cats_cubiertas_por_planeado.add(p["categoria"])

    # 3. Cuotas de deudas activas
    df_cuotas = proyectar_cuotas_todas_las_deudas()
    if not df_cuotas.empty:
        for _, c in df_cuotas.iterrows():
            if c["capital_estimado"] > 0:
                detalle.append({
                    "tipo": "pago_deuda",
                    "categoria": c["nombre"],
                    "monto": float(c["capital_estimado"]),
                    "origen": "Cuota proyectada (capital)",
                    "nombre": c["nombre"],
                })
            if c["intereses_estimados"] > 0:
                detalle.append({
                    "tipo": "pago_deuda_intereses",
                    "categoria": c["nombre"],
                    "monto": float(c["intereses_estimados"]),
                    "origen": "Cuota proyectada (intereses)",
                    "nombre": c["nombre"],
                })

    # 4. Promedios históricos para gastos sin recurrente ni planeado
    df_prom = promedio_gastos_por_categoria(meses_historico, year_month)
    if not df_prom.empty:
        for _, p in df_prom.iterrows():
            cat = p["categoria"]
            if cat in cats_cubiertas_por_recurrente or cat in cats_cubiertas_por_planeado:
                continue
            if p["promedio"] <= 0:
                continue
            detalle.append({
                "tipo": "gasto",
                "categoria": cat,
                "monto": float(p["promedio"]),
                "origen": f"Promedio {meses_historico}m",
                "nombre": cat,
            })

    # Totales
    df_det = pd.DataFrame(detalle)
    totales = {
        "ingresos": 0.0, "gastos": 0.0, "ahorros": 0.0,
        "inversiones": 0.0, "pagos_deuda": 0.0,
        "intereses_deuda": 0.0, "flujo_neto": 0.0,
    }
    if not df_det.empty:
        sumas = df_det.groupby("tipo")["monto"].sum().to_dict()
        totales["ingresos"] = float(sumas.get("ingreso", 0.0))
        totales["gastos"] = float(sumas.get("gasto", 0.0))
        totales["ahorros"] = float(sumas.get("ahorro", 0.0))
        totales["inversiones"] = float(sumas.get("inversion", 0.0))
        totales["pagos_deuda"] = float(sumas.get("pago_deuda", 0.0))
        totales["intereses_deuda"] = float(sumas.get("pago_deuda_intereses", 0.0))

    totales["flujo_neto"] = (
        totales["ingresos"]
        - totales["gastos"]
        - totales["ahorros"]
        - totales["inversiones"]
        - totales["pagos_deuda"]
        - totales["intereses_deuda"]
    )

    return {"year_month": year_month, "detalle": detalle, "totales": totales}


def calcular_prevision_rolling(year_month_inicio: str, n_meses: int,
                                meses_historico: int = 3) -> pd.DataFrame:
    """Previsiones consecutivas para n_meses empezando en year_month_inicio."""
    filas = []
    cursor = year_month_inicio
    for _ in range(n_meses):
        prev = calcular_prevision_mes(cursor, meses_historico)
        fila = {"year_month": cursor}
        fila.update(prev["totales"])
        filas.append(fila)
        cursor = _next_ym(cursor)
    return pd.DataFrame(filas)


# =====================================================================
# COMPARACIÓN PRESUPUESTO vs REAL
# =====================================================================
def consumo_real_por_categoria(year_month: str) -> pd.DataFrame:
    """Consolidado del consumo real por categoría y tipo en un mes."""
    primer_dia = _ym_to_first_day(year_month)
    proximo_mes = _ym_to_first_day(_next_ym(year_month))

    filas = []

    # Gastos
    r = supabase.table("gastos").select("categoria,valor") \
        .gte("fecha", str(primer_dia)).lt("fecha", str(proximo_mes)).execute()
    if r.data:
        df = pd.DataFrame(r.data).groupby("categoria", as_index=False)["valor"].sum()
        for _, row in df.iterrows():
            filas.append({"tipo": "gasto", "categoria": row["categoria"], "real": float(row["valor"])})

    # Ahorros
    r = supabase.table("movimientos_ahorro").select("tipo,monto,ahorros(nombre)") \
        .gte("fecha", str(primer_dia)).lt("fecha", str(proximo_mes)).execute()
    if r.data:
        ag = {}
        for item in r.data:
            nombre = item["ahorros"]["nombre"] if item.get("ahorros") else "Sin fondo"
            signo = 1 if item["tipo"] == "Ingreso" else -1
            ag[nombre] = ag.get(nombre, 0.0) + signo * float(item["monto"])
        for nombre, monto in ag.items():
            filas.append({"tipo": "ahorro", "categoria": nombre, "real": monto})

    # Inversiones
    r = supabase.table("transacciones_inversion") \
        .select("tipo_operacion,cantidad,precio_unitario,activos_inversion(nombre)") \
        .gte("fecha", str(primer_dia)).lt("fecha", str(proximo_mes)).execute()
    if r.data:
        ag = {}
        for item in r.data:
            nombre = item["activos_inversion"]["nombre"] if item.get("activos_inversion") else "N/A"
            signo = 1 if item["tipo_operacion"] == "Compra" else -1
            valor = signo * float(item["cantidad"]) * float(item["precio_unitario"])
            ag[nombre] = ag.get(nombre, 0.0) + valor
        for nombre, monto in ag.items():
            filas.append({"tipo": "inversion", "categoria": nombre, "real": monto})

    return pd.DataFrame(filas) if filas else pd.DataFrame(columns=["tipo", "categoria", "real"])

