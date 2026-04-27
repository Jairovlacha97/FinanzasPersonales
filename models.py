from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class Gasto:
    fecha: date
    categoria: str
    descripcion: str
    valor: float
    tarjeta: str
    id: int = None

    def __post_init__(self):
        """Este método se ejecuta automáticamente al instanciar la clase."""
        # Forzamos que la descripción siempre se guarde en mayúsculas
        if self.descripcion:
            self.descripcion = self.descripcion.upper()

@dataclass
class Deuda:
    nombre: str
    monto_inicial: float
    cuotas_totales: int
    activa: bool = True
    id: int = None

@dataclass
class PagoDeuda:
    deuda_id: int
    fecha: date
    abono_capital: float
    intereses_seguros: float
    cuenta_origen: str
    id: int = None

@dataclass
class Ahorro:
    nombre: str
    meta: float = 0
    id: int = None

@dataclass
class MovimientoAhorro:
    ahorro_id: int
    fecha: date
    tipo: str # 'Ingreso' o 'Retiro'
    monto: float
    cuenta_relacionada: str
    id: int = None

# --- NUEVOS MODELOS PARA INVERSIONES ---
@dataclass
class ActivoInversion:
    ticker: str
    nombre: str
    tipo: str
    id: int = None

@dataclass
class TransaccionInversion:
    activo_id: int
    fecha: date
    tipo_operacion: str # 'Compra' o 'Venta'
    cantidad: float
    precio_unitario: float
    cuenta_origen: str
    id: int = None

# --- NUEVO MODELO PARA INGRESOS ---
@dataclass
class Ingreso:
    fecha: date
    categoria: str
    descripcion: str
    valor: float
    cuenta_destino: str
    id: int = None


# --- MODELOS PARA PRESUPUESTOS Y PREVISIÓN ---

@dataclass
class Categoria:
    """Catálogo editable de categorías. tipo: 'ingreso' | 'gasto' | 'ahorro' | 'inversion'."""
    nombre: str
    tipo: str
    activa: bool = True
    id: int = None

@dataclass
class Presupuesto:
    """Monto objetivo para una categoría en un mes específico (YYYY-MM).
    Para tipo='gasto' representa límite máximo; para 'ahorro' e 'inversion' es meta mínima.
    """
    year_month: str          # 'YYYY-MM'
    categoria: str
    tipo: str                # 'gasto' | 'ahorro' | 'inversion'
    monto: float
    nota: Optional[str] = None
    id: int = None

@dataclass
class ItemRecurrente:
    """Item que se repite mes a mes y alimenta la previsión automática
    (nómina, suscripciones, aportes recurrentes a fondos, etc.).
    """
    nombre: str
    tipo: str                # 'ingreso' | 'gasto' | 'ahorro' | 'inversion'
    categoria: str
    monto_estimado: float
    frecuencia: str          # 'mensual' | 'quincenal' | 'anual'
    fecha_inicio: date
    dia_mes: Optional[int] = None
    cuenta_relacionada: Optional[str] = None
    fecha_fin: Optional[date] = None
    activo: bool = True
    id: int = None

@dataclass
class ItemPlaneado:
    """Ajuste puntual para un mes específico (un viaje, una prima, un regalo).
    Se suma encima de los recurrentes y promedios históricos.
    """
    year_month: str
    nombre: str
    tipo: str                # 'ingreso' | 'gasto' | 'ahorro' | 'inversion'
    categoria: str
    monto: float
    nota: Optional[str] = None
    id: int = None