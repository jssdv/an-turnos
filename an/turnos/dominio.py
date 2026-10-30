"""Modelo del servicio: turnos (catálogo editable), personal, novedades, festivos y contexto de reglas."""
from collections import namedtuple
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

# Ventanas del día en minutos desde las 00:00 (la noche cruza medianoche).
FRANJAS = {"M": (360, 720), "T": (720, 1080), "N": (1080, 1800)}
TIPOS_NOVEDAD = ("Vacaciones", "Incapacidad", "Licencia", "Libre solicitado")
TIPOS_SOLICITUD = ("libre", "quiero", "evitar")
PRIORIDADES = ("normal", "alta")
TIPOS_COLAB = ("regular", "restringido", "estudiante", "refuerzo")
DESCANSO_MIN = 12 * 60
DIAS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


@dataclass
class Turno:
    codigo: str
    nombre: str
    inicio: int  # minutos desde las 00:00
    fin: int  # si fin <= inicio el turno cruza medianoche
    color: str = "FFFFFF"
    cubre: tuple = ()  # subconjunto de ("M", "T", "N") que cuenta para la cobertura
    pausas: tuple = ()  # dicts {"ini": min desde inicio de turno, "min": duración, "pagada": bool}
    dom_fest: bool = True  # se permite en domingo/festivo
    solver: bool = True  # el solver puede usarlo
    activo: bool = True

    @property
    def duracion(self):
        return (self.fin - self.inicio) % 1440 or 1440

    def tramos(self):
        """Tramos pagados (minutos relativos al inicio): el turno menos las pausas no pagadas."""
        tr = [(0, self.duracion)]
        for p in self.pausas:
            if p.get("pagada"):
                continue
            a, b = p["ini"], p["ini"] + p["min"]
            tr = [t for x, y in tr for t in ((x, min(y, a)), (max(x, b), y)) if t[0] < t[1]]
        return tr

    @property
    def horas(self):
        return sum(b - a for a, b in self.tramos()) / 60


def intervalo(turno, fecha):
    ini = datetime.combine(fecha, datetime.min.time()) + timedelta(minutes=turno.inicio)
    return ini, ini + timedelta(minutes=turno.duracion)


def solape_min(turno, fecha, franja, fecha_franja):
    """Minutos en que el turno de `fecha` se cruza con la franja M/T/N de `fecha_franja`."""
    a, b = intervalo(turno, fecha)
    f0 = datetime.combine(fecha_franja, datetime.min.time())
    fa, fb = f0 + timedelta(minutes=FRANJAS[franja][0]), f0 + timedelta(minutes=FRANJAS[franja][1])
    return max(0, (min(b, fb) - max(a, fa)).total_seconds() / 60)


def turnos_base():
    pa = 360
    return [
        Turno("M", "Mañana", pa, pa + 360, "FFF2CC", ("M",), dom_fest=True),
        Turno("T", "Tarde", pa + 360, pa + 720, "DDEBF7", ("T",), dom_fest=True),
        Turno("C", "Corrido", pa, pa + 720, "E2EFDA", ("M", "T"), dom_fest=False),
        Turno("NC", "Noche corrida", pa + 720, pa, "D9D2E9", ("N",), dom_fest=True),
    ]


COBERTURA_BASE = {"LS": {"M": 4, "T": 4, "N": 2}, "DF": {"M": 2, "T": 2, "N": 2}}


def _pascua(a):
    g = a % 19
    c, d = divmod(a, 100)
    h = (19 * g + c - c // 4 - (c - (c + 8) // 25 + 1) // 3 + 15) % 30
    i, k = divmod(d, 4)
    l = (32 + 2 * (c % 4) + 2 * i - h - k) % 7
    m = (g + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(a, mes, dia + 1)


def festivos(a):
    """Festivos de Colombia (Ley Emiliani, Ley 51/1983): fijos, trasladados al lunes y de Semana Santa."""
    sig_lunes = lambda f: f + timedelta(days=(7 - f.weekday()) % 7)
    p = _pascua(a)
    r = {date(a, m, d): n for m, d, n in [(1, 1, "Año Nuevo"), (5, 1, "Día del Trabajo"), (7, 20, "Independencia"),
                                         (8, 7, "Batalla de Boyacá"), (12, 8, "Inmaculada Concepción"), (12, 25, "Navidad")]}
    for m, d, n in [(1, 6, "Reyes Magos"), (3, 19, "San José"), (6, 29, "San Pedro y San Pablo"), (8, 15, "Asunción"),
                    (10, 12, "Día de la Raza"), (11, 1, "Todos los Santos"), (11, 11, "Independencia de Cartagena")]:
        r[sig_lunes(date(a, m, d))] = n
    r[p - timedelta(days=3)] = "Jueves Santo"
    r[p - timedelta(days=2)] = "Viernes Santo"
    for dias, n in [(39, "Ascensión"), (60, "Corpus Christi"), (68, "Sagrado Corazón")]:
        r[sig_lunes(p + timedelta(days=dias))] = n
    return r


AsignacionPuesto = namedtuple("AsignacionPuesto", "fecha colab_id puesto_id desde hasta pausa")
"""Una persona en un puesto durante [desde, hasta) minutos del día `fecha`; puesto_id 0 = apoyo (sin puesto)."""


@dataclass
class Puesto:
    id: int
    numero: int
    nombre: str
    color: str = "FFFFFF"
    activo: bool = True


@dataclass
class Demanda:
    """Regla: `personas` en el puesto durante la ventana [inicio, fin) de los días de tipo `tipo_dia` (LS o DF; sin puestos: "0"…"6" día de la semana o "F" festivo).
    Minutos desde las 00:00; si fin <= inicio la ventana cruza medianoche."""
    puesto_id: int
    tipo_dia: str
    inicio: int
    fin: int
    personas: int
    obligatorio: bool = True
    id: int = None


@dataclass
class Colaborador:
    id: int
    nombre: str
    tipo: str = "regular"
    horas_sem: float = 42
    pct: float = 1.0
    permitidos: tuple = None  # códigos de turno permitidos; None = todos
    puesto_fijo: int = None
    estudio: tuple = ()  # ((día 0-6, "M"|"T"), ...) bloques en que no está disponible
    activo: bool = True
    puestos_permitidos: tuple = None  # ids de puesto que puede ocupar; None = todos

    @property
    def en_solver(self):
        return self.activo and self.tipo != "refuerzo"


@dataclass
class Novedad:
    colab_id: int
    tipo: str
    desde: date
    hasta: date
    nota: str = ""
    id: int = None


@dataclass
class Solicitud:
    """Deseo de una persona (libre, quiero un turno, evitar un turno) que el solver intenta cumplir sin garantía."""
    colab_id: int
    tipo: str
    desde: date
    hasta: date
    turno: str = ""
    prioridad: str = "normal"
    nota: str = ""
    id: int = None


@dataclass
class Contexto:
    """Todo lo que necesitan reglas, solver y recargos para un conjunto de fechas."""
    turnos: dict  # código -> Turno (activos)
    colabs: list
    novedades: list
    cobertura: dict
    fest: dict  # fecha -> nombre
    libre_tras_noche: int = 1  # días libres obligatorios después de una noche (0 = sin regla)
    libres_semana: int = 1  # días libres mínimos en cada semana completa
    fines_libres: int = 1  # fines de semana completos (sábado y domingo) libres por periodo y persona (0 = sin regla)
    max_noches: int = 2  # noches seguidas del tipo NC-L-NC-L… (separadas por el libre posterior); 0 = sin tope
    max_c: int = 2  # turnos corridos (de 12 h de día) en días consecutivos; 0 = sin tope
    max_igual: int = 3  # mismo turno de 6 h (M, T…) en días consecutivos; 0 = sin tope
    puestos: dict = field(default_factory=dict)  # id -> Puesto
    demandas: list = field(default_factory=list)  # reglas de demanda de los puestos activos
    solicitudes: list = field(default_factory=list)  # deseos blandos del solver
    usa_puestos: bool = True  # False: la necesidad son personas por franja y día de la semana (demanda con puesto 0)
    max_horas_semana: int = 0  # tope duro de horas por persona en cada semana lunes–domingo completa; 0 = sin tope
    max_c_semana: int = 0  # tope duro de corridos por persona en cada semana lunes–domingo completa; 0 = sin tope
    _nov: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        for n in self.novedades:
            d = n.desde
            while d <= n.hasta:
                self._nov.setdefault((n.colab_id, d), n)
                d += timedelta(days=1)

    def tipo_dia(self, f):
        return "DF" if f.weekday() == 6 or f in self.fest else "LS"

    def codigo_dia(self, f):
        """Día de la semana ("0" lunes … "6") o "F" si es festivo: clave del requerimiento de un área sin puestos."""
        return "F" if f in self.fest else str(f.weekday())

    def novedad(self, cid, f):
        return self._nov.get((cid, f))

    def bloqueo(self, colab, turno, f):
        """Motivo por el que `colab` no puede hacer `turno` el día `f`, o None."""
        n = self.novedad(colab.id, f)
        if n:
            return n.tipo
        if colab.permitidos is not None and turno.codigo not in colab.permitidos:
            return "turno no permitido"
        if not turno.dom_fest and self.tipo_dia(f) == "DF":
            return "turno no permitido en domingo/festivo"
        for fd in (f, f + timedelta(days=1)):
            for dia, fr in colab.estudio:
                if dia == fd.weekday() and solape_min(turno, f, fr, fd) > 0:
                    return "estudio"
        return None


def texto_estudio(estudio):
    por_dia = {}
    for dia, fr in estudio:
        por_dia.setdefault(dia, []).append(fr)
    return ", ".join(DIAS[d] if len(f) == 2 else f"{DIAS[d]} {f[0]}" for d, f in sorted(por_dia.items()))
