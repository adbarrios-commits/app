"""
TABLE - Servicio a la mesa para Food Parks (interfaz Streamlit)
-----------------------------------------------------------------
Misma logica y mismas estructuras de datos propias que foodtrack_v2.py
(Nodo, ListaEnlazada, Cola, Pila, NodoArbol, Grafo, TablaHash).
Diseño inspirado en apps de delivery: header de color, carrito funcional
en un popover, tarjetas de categoria, barra de navegacion abajo.

Para correrlo:
    pip install streamlit
    streamlit run foodtrack_streamlit.py

IMPORTANTE: subir tambien la carpeta .streamlit/config.toml junto a este
archivo (misma estructura de carpetas en el repo) - fuerza colores claros
y vivos sin importar si el celular esta en modo oscuro.
"""

import json
import os
from datetime import datetime

import streamlit as st

ARCHIVO_HISTORIAL = "facturas_historial.json"

ICONOS_CATEGORIA = {
    "Menu": "🍽️",
    "Comidas": "🍴",
    "Bebidas": "🥤",
    "Rapidas": "🍔",
    "Saludables": "🥗",
    "Frias": "🧊",
}
ICONOS_PUESTO = {
    "Puesto Burger": "🍔",
    "Puesto Pizza": "🍕",
    "Puesto Saludable": "🥗",
    "Puesto Bebidas": "🥤",
}


# ============================================================
# ESTRUCTURAS DE DATOS BASE (identicas a foodtrack_v2.py)
# ============================================================
class Nodo:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente = None


class ListaEnlazada:
    def __init__(self):
        self.cabeza = None
        self.cantidad = 0

    def agregar(self, dato):
        nuevo = Nodo(dato)
        if self.cabeza is None:
            self.cabeza = nuevo
        else:
            actual = self.cabeza
            while actual.siguiente:
                actual = actual.siguiente
            actual.siguiente = nuevo
        self.cantidad += 1

    def eliminar_ultimo(self):
        if self.cabeza is None:
            return None
        if self.cabeza.siguiente is None:
            dato = self.cabeza.dato
            self.cabeza = None
            self.cantidad -= 1
            return dato
        actual = self.cabeza
        while actual.siguiente.siguiente:
            actual = actual.siguiente
        dato = actual.siguiente.dato
        actual.siguiente = None
        self.cantidad -= 1
        return dato

    def recorrer(self):
        items, actual = [], self.cabeza
        while actual:
            items.append(actual.dato)
            actual = actual.siguiente
        return items

    def calcular_total(self):
        return sum(item.subtotal() for item in self.recorrer())

    def __len__(self):
        return self.cantidad


class Cola:
    def __init__(self):
        self.cabeza = None
        self.cola = None
        self.cantidad = 0

    def encolar(self, dato):
        nuevo = Nodo(dato)
        if self.cola is None:
            self.cabeza = self.cola = nuevo
        else:
            self.cola.siguiente = nuevo
            self.cola = nuevo
        self.cantidad += 1

    def desencolar(self):
        if self.cabeza is None:
            return None
        dato = self.cabeza.dato
        self.cabeza = self.cabeza.siguiente
        if self.cabeza is None:
            self.cola = None
        self.cantidad -= 1
        return dato

    def esta_vacia(self):
        return self.cabeza is None

    def __len__(self):
        return self.cantidad


class Pila:
    def __init__(self):
        self.tope = None

    def apilar(self, dato):
        nuevo = Nodo(dato)
        nuevo.siguiente = self.tope
        self.tope = nuevo

    def desapilar(self):
        if self.tope is None:
            return None
        dato = self.tope.dato
        self.tope = self.tope.siguiente
        return dato

    def esta_vacia(self):
        return self.tope is None


class NodoArbol:
    def __init__(self, nombre, producto=None):
        self.nombre = nombre
        self.producto = producto
        self.hijos = []

    def agregar_hijo(self, hijo):
        self.hijos.append(hijo)
        return hijo

    def es_hoja(self):
        return len(self.hijos) == 0


class Grafo:
    def __init__(self):
        self.adyacencia = {}

    def agregar_arista(self, a, b, distancia):
        self.adyacencia.setdefault(a, []).append((b, distancia))
        self.adyacencia.setdefault(b, []).append((a, distancia))

    def camino_mas_corto(self, inicio, fin):
        if inicio not in self.adyacencia or fin not in self.adyacencia:
            return None, None
        distancias = {n: float("inf") for n in self.adyacencia}
        distancias[inicio] = 0
        anteriores = {n: None for n in self.adyacencia}
        no_visitados = set(self.adyacencia.keys())

        while no_visitados:
            actual = min(no_visitados, key=lambda n: distancias[n])
            no_visitados.remove(actual)
            if actual == fin:
                break
            for vecino, peso in self.adyacencia[actual]:
                nueva_dist = distancias[actual] + peso
                if nueva_dist < distancias[vecino]:
                    distancias[vecino] = nueva_dist
                    anteriores[vecino] = actual

        camino, actual = [], fin
        while actual is not None:
            camino.append(actual)
            actual = anteriores[actual]
        camino.reverse()
        return camino, distancias[fin]


class TablaHash:
    def __init__(self, tamano=16):
        self.tamano = tamano
        self.buckets = [[] for _ in range(tamano)]

    def _hash(self, clave):
        return sum(ord(c) for c in str(clave)) % self.tamano

    def insertar(self, clave, valor):
        i = self._hash(clave)
        for idx, (k, _) in enumerate(self.buckets[i]):
            if k == clave:
                self.buckets[i][idx] = (clave, valor)
                return
        self.buckets[i].append((clave, valor))

    def buscar(self, clave):
        i = self._hash(clave)
        for k, v in self.buckets[i]:
            if k == clave:
                return v
        return None

    def eliminar(self, clave):
        i = self._hash(clave)
        for idx, (k, _) in enumerate(self.buckets[i]):
            if k == clave:
                del self.buckets[i][idx]
                return True
        return False

    def valores(self):
        return [v for bucket in self.buckets for (_, v) in bucket]


# ============================================================
# CLASES DE NEGOCIO (identicas a foodtrack_v2.py)
# ============================================================
class Producto:
    def __init__(self, codigo, nombre, precio, puesto, tiempo_prep_seg):
        self.codigo = codigo
        self.nombre = nombre
        self.precio = precio
        self.puesto = puesto
        self.tiempo_prep_seg = tiempo_prep_seg


class ItemPedido:
    def __init__(self, producto, cantidad):
        self.producto = producto
        self.cantidad = cantidad

    def subtotal(self):
        return self.producto.precio * self.cantidad

    def __str__(self):
        return (f"{self.cantidad}x {self.producto.nombre} "
                f"(Gs. {self.producto.precio:,}) = Gs. {self.subtotal():,}")


class Mesa:
    def __init__(self, numero):
        self.numero = numero
        self.carrito = ListaEnlazada()
        self.confirmados = ListaEnlazada()
        self.historial_acciones = Pila()

    def agregar_al_carrito(self, producto, cantidad):
        self.carrito.agregar(ItemPedido(producto, cantidad))
        self.historial_acciones.apilar("carrito")

    def deshacer(self):
        if self.historial_acciones.esta_vacia():
            return None
        self.historial_acciones.desapilar()
        return self.carrito.eliminar_ultimo()

    def total_cuenta(self):
        return self.confirmados.calcular_total()


class Factura:
    def __init__(self, numero_mesa, items_texto, total, fecha):
        self.numero_mesa = numero_mesa
        self.items_texto = items_texto
        self.total = total
        self.fecha = fecha

    def to_dict(self):
        return {
            "mesa": self.numero_mesa,
            "items": self.items_texto,
            "total": self.total,
            "fecha": self.fecha,
        }


# ============================================================
# DATOS INICIALES (identicos a foodtrack_v2.py)
# ============================================================
def construir_catalogo_y_menu():
    catalogo = TablaHash()
    raiz = NodoArbol("Menu")
    comidas = raiz.agregar_hijo(NodoArbol("Comidas"))
    bebidas = raiz.agregar_hijo(NodoArbol("Bebidas"))
    rapidas = comidas.agregar_hijo(NodoArbol("Rapidas"))
    saludables = comidas.agregar_hijo(NodoArbol("Saludables"))
    frias = bebidas.agregar_hijo(NodoArbol("Frias"))

    datos_productos = [
        ("1", "Hamburguesa Clasica", 25000, "Puesto Burger", 6, rapidas),
        ("2", "Pizza Muzzarella", 45000, "Puesto Pizza", 8, rapidas),
        ("3", "Papas Fritas", 12000, "Puesto Burger", 4, rapidas),
        ("4", "Ensalada Cesar", 22000, "Puesto Saludable", 5, saludables),
        ("5", "Gaseosa 500ml", 8000, "Puesto Bebidas", 1, frias),
        ("6", "Jugo Natural", 10000, "Puesto Bebidas", 2, frias),
    ]

    for codigo, nombre, precio, puesto, tiempo, categoria in datos_productos:
        producto = Producto(codigo, nombre, precio, puesto, tiempo)
        catalogo.insertar(codigo, producto)
        categoria.agregar_hijo(NodoArbol(nombre, producto=producto))

    return catalogo, raiz


def construir_mapa():
    grafo = Grafo()
    grafo.agregar_arista("Mesas", "Puesto Burger", 10)
    grafo.agregar_arista("Mesas", "Puesto Pizza", 18)
    grafo.agregar_arista("Mesas", "Puesto Saludable", 14)
    grafo.agregar_arista("Puesto Burger", "Puesto Bebidas", 6)
    grafo.agregar_arista("Puesto Pizza", "Puesto Bebidas", 9)
    grafo.agregar_arista("Puesto Saludable", "Puesto Bebidas", 7)
    grafo.agregar_arista("Puesto Bebidas", "Mesas", 12)
    return grafo


def cargar_historial():
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def guardar_historial(historial):
    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)


# ============================================================
# ESTADO DE LA APP
# ============================================================
def init_state():
    if "iniciado" in st.session_state:
        return
    catalogo, menu = construir_catalogo_y_menu()
    st.session_state.iniciado = True
    st.session_state.catalogo = catalogo
    st.session_state.menu = menu
    st.session_state.mapa = construir_mapa()
    st.session_state.mesas_activas = TablaHash()
    st.session_state.colas_cocina = {}
    st.session_state.historial_facturas = cargar_historial()
    st.session_state.mesa_actual = None
    st.session_state.ruta_menu = [menu]
    st.session_state.log_cocina = []
    st.session_state.flash_add = None
    st.session_state.cambiar_mesa = False


st.set_page_config(page_title="TABLE", page_icon="🍽️", layout="wide")
init_state()

# ============================================================
# ESTILO VISUAL
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

:root {
    --brand: #FF2D55;
    --brand-dark: #D81B4F;
    --brand-light: #FFE5EC;
    --accent: #FFC400;
    --text-dark: #1D1D1F;
    --muted: #767680;
    --tile-bg: #F2F2F5;
}

.stApp { background: #FFFFFF; }
.block-container { padding-top: 0 !important; padding-bottom: 6rem; max-width: 1050px; }

.stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp p, .stApp li, .stApp label, .stApp .stMarkdown { color: var(--text-dark); }

/* ---- Header de color, ancho completo ---- */
div.st-key-topbar {
    background: linear-gradient(135deg, var(--brand) 0%, var(--brand-dark) 100%);
    margin: 0 -1rem 1.1rem -1rem;
    padding: 1.1rem 1.2rem 1.4rem 1.2rem;
    border-radius: 0 0 26px 26px;
}
div.st-key-topbar * { color: white !important; }
div.st-key-topbar button {
    background: rgba(255,255,255,0.18) !important;
    border: none !important;
    border-radius: 50% !important;
    font-weight: 700 !important;
    width: 46px; height: 46px;
}
div.st-key-topbar button:hover { background: rgba(255,255,255,0.32) !important; }
div.st-key-topbar button p { color: white !important; }

/* ---- Buscador ---- */
div.st-key-buscador input {
    border-radius: 16px !important;
    border: none !important;
    padding: 0.7rem 1rem !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.10);
}

/* ---- Botones generales ---- */
button[kind="primary"] {
    background: var(--brand) !important;
    border: none !important;
    border-radius: 16px !important;
    font-weight: 700 !important;
    color: white !important;
    padding: 0.6rem 1.3rem !important;
    box-shadow: 0 6px 16px rgba(255,45,85,0.30);
}
button[kind="primary"]:hover { background: var(--brand-dark) !important; }
button[kind="primary"] p { color: white !important; font-weight: 700 !important; }

button[kind="secondary"] {
    border-radius: 16px !important;
    border: 2px solid var(--brand-light) !important;
    font-weight: 600 !important;
    color: var(--text-dark) !important;
    background: white !important;
}
button[kind="secondary"]:hover {
    border-color: var(--brand) !important;
    color: var(--brand) !important;
}
button[kind="secondary"] p { color: inherit !important; font-weight: 600 !important; }

/* ---- Tarjetas de categoria (imitando tiles de delivery apps) ---- */
.cat-tile {
    background: var(--tile-bg);
    border-radius: 20px;
    padding: 1.6rem 0.5rem 0.9rem 0.5rem;
    text-align: center;
    margin-bottom: 0.4rem;
}
.cat-tile .emoji { font-size: 2.6rem; display:block; margin-bottom: 0.4rem; }
.cat-tile .label { font-weight: 700; color: var(--text-dark); font-size: 1rem; }
.cat-tile .sub { color: var(--muted); font-size: 0.78rem; }

/* ---- Cards con borde (productos) ---- */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 20px !important;
    box-shadow: 0 3px 12px rgba(0,0,0,0.07);
}

.badge-precio {
    display: inline-block;
    background: var(--brand);
    color: white;
    font-weight: 800;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
}
.badge-puesto {
    display: inline-block;
    background: var(--accent);
    color: var(--text-dark);
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    margin-left: 6px;
}

/* ---- Alertas con animacion ---- */
div[data-testid="stAlert"] {
    animation: popIn 0.3s ease;
    border-radius: 14px !important;
    font-weight: 600 !important;
}
@keyframes popIn {
    0% { transform: scale(0.85); opacity: 0; }
    70% { transform: scale(1.05); }
    100% { transform: scale(1); opacity: 1; }
}

/* ---- Barra de navegacion abajo (a partir de los tabs) ---- */
div[data-baseweb="tab-list"] {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background: white;
    box-shadow: 0 -3px 16px rgba(0,0,0,0.10);
    z-index: 999999;
    padding: 8px 4px calc(10px + env(safe-area-inset-bottom)) 4px;
    justify-content: space-around !important;
    border-radius: 22px 22px 0 0;
    gap: 0 !important;
}
button[data-baseweb="tab"] {
    flex: 1;
    justify-content: center;
    font-weight: 700;
    font-size: 0.82rem;
    color: var(--muted) !important;
}
button[data-baseweb="tab"][aria-selected="true"] { color: var(--brand) !important; }
div[data-baseweb="tab-highlight"] { display: none !important; }
div[data-baseweb="tab-border"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


def render_producto_card(mesa_obj, p):
    """Tarjeta de un producto (usada en la navegacion y en la busqueda)."""
    with st.container(border=True):
        icono = ICONOS_PUESTO.get(p.puesto, "🍽️")
        st.markdown(f"#### {icono} {p.nombre}")
        st.markdown(
            f"<span class='badge-precio'>Gs. {p.precio:,}</span>"
            f"<span class='badge-puesto'>{p.puesto}</span>",
            unsafe_allow_html=True,
        )
        cantidad = st.number_input(
            "Cantidad", min_value=1, value=1, step=1,
            key=f"cant_{p.codigo}", label_visibility="collapsed",
        )
        if st.button("➕ Agregar", key=f"add_{p.codigo}",
                     use_container_width=True, type="primary"):
            mesa_obj.agregar_al_carrito(p, cantidad)
            st.session_state.flash_add = p.codigo
            st.rerun()

        if st.session_state.flash_add == p.codigo:
            st.success("✅ ¡Agregado correctamente!")
            st.session_state.flash_add = None


# ---- Header de color con logo, mesas y carrito ----
mesa_actual_ref = st.session_state.mesa_actual
cantidad_carrito = len(mesa_actual_ref.carrito) if mesa_actual_ref else 0

with st.container(key="topbar"):
    c_logo, c_bell, c_cart = st.columns([5, 1, 1])
    with c_logo:
        estado = f"Mesa {mesa_actual_ref.numero}" if mesa_actual_ref else "Elegí tu mesa"
        st.markdown(
            f"<div style='font-family:Fredoka,sans-serif; font-weight:700; font-size:1.6rem;'>🍽️ TABLE</div>"
            f"<div style='opacity:0.9; font-size:0.85rem; margin-top:-4px;'>{estado} ▾</div>",
            unsafe_allow_html=True,
        )
    with c_bell:
        with st.popover("🪑"):
            st.markdown("**Mesas activas**")
            activas = st.session_state.mesas_activas.valores()
            if not activas:
                st.caption("No hay mesas abiertas todavia.")
            else:
                for m in activas:
                    if st.button(f"Mesa {m.numero} · 🛒{len(m.carrito)}",
                                 key=f"pop_mesa_{m.numero}", use_container_width=True):
                        st.session_state.mesa_actual = m
                        st.session_state.ruta_menu = [st.session_state.menu]
                        st.rerun()
            st.divider()
            if st.button("➕ Abrir otra mesa", use_container_width=True):
                st.session_state.cambiar_mesa = True
                st.rerun()
    with c_cart:
        with st.popover(f"🛒 {cantidad_carrito}" if cantidad_carrito else "🛒"):
            st.markdown("**Tu carrito**")
            if mesa_actual_ref is None:
                st.caption("Elegí una mesa primero.")
            else:
                items = mesa_actual_ref.carrito.recorrer()
                if not items:
                    st.caption("Todavia no agregaste nada.")
                else:
                    for it in items:
                        st.write(f"{it.cantidad}x {it.producto.nombre} — Gs. {it.subtotal():,}")
                    st.markdown(f"**Subtotal: Gs. {mesa_actual_ref.carrito.calcular_total():,}**")
                    if st.button("✅ Enviar a cocina", key="cart_pop_enviar",
                                 use_container_width=True, type="primary"):
                        for item in items:
                            puesto = item.producto.puesto
                            st.session_state.colas_cocina.setdefault(puesto, Cola())
                            st.session_state.colas_cocina[puesto].encolar((mesa_actual_ref.numero, item))
                            mesa_actual_ref.confirmados.agregar(item)
                        mesa_actual_ref.carrito = ListaEnlazada()
                        st.success("🍳 ¡Pedido enviado a cocina!")
                        st.rerun()

# ---- Selector de mesa (solo si no hay una elegida, o si pidieron cambiar) ----
if mesa_actual_ref is None or st.session_state.cambiar_mesa:
    st.markdown("##### 🪑 Numero de mesa")
    col_num, col_btn = st.columns([2, 1])
    with col_num:
        numero = st.number_input("Numero de mesa", min_value=1, step=1, value=1,
                                  label_visibility="collapsed")
    with col_btn:
        if st.button("Ir a mi mesa 🚀", use_container_width=True, type="primary"):
            mesa_existente = st.session_state.mesas_activas.buscar(numero)
            if mesa_existente is None:
                mesa_existente = Mesa(numero)
                st.session_state.mesas_activas.insertar(numero, mesa_existente)
            st.session_state.mesa_actual = mesa_existente
            st.session_state.ruta_menu = [st.session_state.menu]
            st.session_state.cambiar_mesa = False
            st.rerun()
    st.divider()

# ------------------------------------------------------------
# AREA PRINCIPAL
# ------------------------------------------------------------
mesa = st.session_state.mesa_actual

if mesa is None:
    st.info("👋 Elegí un numero de mesa arriba para empezar a pedir.")
else:
    tab_menu, tab_carrito, tab_cocina, tab_ruta, tab_factura = st.tabs(
        ["🍔 Menú", "🛒 Carrito", "👨‍🍳 Cocina", "🗺️ Ruta", "🧾 Cuenta"]
    )

    # --- Tab 1: buscador + navegar el arbol de categorias ---
    with tab_menu:
        with st.container(key="buscador"):
            query = st.text_input("Buscar", placeholder="🔍 Buscar producto...",
                                   label_visibility="collapsed")

        if query.strip():
            productos_todos = st.session_state.catalogo.valores()
            resultados = [p for p in productos_todos if query.strip().lower() in p.nombre.lower()]
            st.caption(f"{len(resultados)} resultado(s) para \"{query}\"")
            if not resultados:
                st.warning("No encontramos productos con ese nombre.")
            cols = st.columns(3)
            for i, p in enumerate(resultados):
                with cols[i % 3]:
                    render_producto_card(mesa, p)
        else:
            nodo_actual = st.session_state.ruta_menu[-1]
            breadcrumb = " ➜ ".join(
                f"{ICONOS_CATEGORIA.get(n.nombre, '📂')} {n.nombre}"
                for n in st.session_state.ruta_menu
            )
            col_bc, col_back = st.columns([4, 1])
            with col_bc:
                st.markdown(f"**{breadcrumb}**")
            with col_back:
                if len(st.session_state.ruta_menu) > 1:
                    if st.button("⬅️ Volver", key="volver_menu", use_container_width=True):
                        st.session_state.ruta_menu.pop()
                        st.rerun()

            cols = st.columns(3)
            for i, hijo in enumerate(nodo_actual.hijos):
                with cols[i % 3]:
                    if hijo.producto:
                        render_producto_card(mesa, hijo.producto)
                    else:
                        icono = ICONOS_CATEGORIA.get(hijo.nombre, "📂")
                        st.markdown(
                            f"<div class='cat-tile'>"
                            f"<span class='emoji'>{icono}</span>"
                            f"<span class='label'>{hijo.nombre}</span><br>"
                            f"<span class='sub'>{len(hijo.hijos)} opciones</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        if st.button("Ver más", key=f"nav_{hijo.nombre}_{i}",
                                     use_container_width=True):
                            st.session_state.ruta_menu.append(hijo)
                            st.rerun()

    # --- Tab 2: carrito, deshacer, enviar a cocina ---
    with tab_carrito:
        items = mesa.carrito.recorrer()
        if not items:
            st.caption("🛒 El carrito esta vacio. Agregá algo desde el Menú.")
        else:
            for it in items:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{it.cantidad}x** {it.producto.nombre}")
                c2.markdown(f"Gs. {it.subtotal():,}")
            st.markdown(f"### Subtotal: Gs. {mesa.carrito.calcular_total():,}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("↩️ Deshacer último", use_container_width=True):
                quitado = mesa.deshacer()
                if quitado:
                    st.success(f"↩️ Se quitó: {quitado.producto.nombre}")
                else:
                    st.warning("Nada para deshacer.")
                st.rerun()
        with c2:
            if st.button("✅ Enviar a cocina", use_container_width=True, type="primary"):
                if not items:
                    st.warning("El carrito esta vacio.")
                else:
                    for item in items:
                        puesto = item.producto.puesto
                        st.session_state.colas_cocina.setdefault(puesto, Cola())
                        st.session_state.colas_cocina[puesto].encolar((mesa.numero, item))
                        mesa.confirmados.agregar(item)
                    mesa.carrito = ListaEnlazada()
                    st.success("🍳 ¡Pedido enviado a cocina!")
                    st.rerun()

        if len(mesa.confirmados) > 0:
            st.divider()
            st.markdown("**Ya confirmados (van a la cuenta):**")
            for it in mesa.confirmados.recorrer():
                st.write(f"- {it}")

    # --- Tab 3: estado de cocina ---
    with tab_cocina:
        colas = st.session_state.colas_cocina
        st.markdown("**Pedidos pendientes por puesto**")
        if not colas or all(c.esta_vacia() for c in colas.values()):
            st.caption("No hay pedidos pendientes en cocina.")
        else:
            cols = st.columns(len(colas) or 1)
            for i, (puesto, cola) in enumerate(colas.items()):
                with cols[i % len(cols)]:
                    with st.container(border=True):
                        icono = ICONOS_PUESTO.get(puesto, "🍽️")
                        st.markdown(f"**{icono} {puesto}**")
                        st.markdown(f"<span class='badge-precio'>{len(cola)} en cola</span>",
                                    unsafe_allow_html=True)

        if st.button("👨‍🍳 Preparar siguiente de cada puesto", type="primary"):
            eventos = []
            for puesto, cola in colas.items():
                if not cola.esta_vacia():
                    numero_mesa_item, item = cola.desencolar()
                    eventos.append(
                        f"{ICONOS_PUESTO.get(puesto, '🍽️')} **{puesto}** → Mesa {numero_mesa_item}: "
                        f"{item.producto.nombre} (~{item.producto.tiempo_prep_seg}s)"
                    )
            if not eventos:
                st.warning("No hay nada para preparar.")
            else:
                st.session_state.log_cocina = eventos + st.session_state.log_cocina
            st.rerun()

        if st.session_state.log_cocina:
            st.divider()
            st.markdown("**Últimos eventos:**")
            for ev in st.session_state.log_cocina[:10]:
                st.markdown(f"- {ev}")

    # --- Tab 4: ruta mas corta ---
    with tab_ruta:
        destinos = sorted(k for k in st.session_state.mapa.adyacencia.keys() if k != "Mesas")
        destino = st.selectbox("Puesto de destino", destinos)
        if st.button("📍 Calcular ruta", type="primary"):
            camino, distancia = st.session_state.mapa.camino_mas_corto("Mesas", destino)
            if camino is None:
                st.error("Puesto no encontrado en el mapa.")
            else:
                iconos = " ".join(ICONOS_PUESTO.get(p, "📍") for p in camino)
                st.success(f"{' → '.join(camino)}  ({distancia} m)  {iconos}")

    # --- Tab 5: cerrar cuenta / facturar ---
    with tab_factura:
        if len(mesa.confirmados) == 0:
            st.caption("No hay items confirmados para facturar todavia.")
        else:
            items_texto = [str(it) for it in mesa.confirmados.recorrer()]
            total = mesa.total_cuenta()
            for texto in items_texto:
                st.write(f"- {texto}")
            st.markdown(f"## Total: Gs. {total:,}")

            if st.button("🧾 Facturar y liberar mesa", type="primary"):
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                factura = Factura(mesa.numero, items_texto, total, fecha)
                st.session_state.historial_facturas.append(factura.to_dict())
                guardar_historial(st.session_state.historial_facturas)
                st.session_state.mesas_activas.eliminar(mesa.numero)
                st.session_state.mesa_actual = None
                st.success(f"Factura guardada. Mesa {mesa.numero} liberada.")
                st.rerun()

# ------------------------------------------------------------
# Historial
# ------------------------------------------------------------
st.divider()
with st.expander("🧾 Ver historial de facturas"):
    if not st.session_state.historial_facturas:
        st.caption("Aun no hay facturas registradas.")
    else:
        for f in st.session_state.historial_facturas[-10:][::-1]:
            st.write(f"[{f['fecha']}] Mesa {f['mesa']} — Gs. {f['total']:,}")
