from dataclasses import dataclass
from datetime import date

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