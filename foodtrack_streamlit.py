"""
TABLE - Servicio a la mesa para Food Parks (interfaz Streamlit)
-----------------------------------------------------------------
Misma logica y mismas estructuras de datos propias que foodtrack_v2.py
(Nodo, ListaEnlazada, Cola, Pila, NodoArbol, Grafo, TablaHash).
Esta version tiene un diseño visual vivo tipo app de delivery.

Para correrlo:
    pip install streamlit
    streamlit run foodtrack_streamlit.py

IMPORTANTE: subir tambien la carpeta .streamlit/config.toml junto a este
archivo (mismo repo, misma estructura de carpetas) - fuerza colores claros
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


st.set_page_config(page_title="TABLE", page_icon="🍽️", layout="wide")
init_state()

# ============================================================
# ESTILO VISUAL - colores vivos tipo app de delivery
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
}

.stApp { background: #FFFFFF; }
.block-container { padding-top: 0.8rem; padding-bottom: 4rem; max-width: 1050px; }

/* ---- Carrito flotante arriba a la derecha ---- */
.cart-fab {
    position: fixed;
    top: 12px;
    right: 16px;
    z-index: 999999;
    background: white;
    border-radius: 50%;
    width: 52px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    box-shadow: 0 4px 14px rgba(0,0,0,0.18);
    border: 2px solid var(--brand-light);
}
.cart-badge {
    position: fixed;
    top: 4px;
    right: 8px;
    z-index: 1000000;
    background: var(--brand);
    color: white;
    font-weight: 800;
    font-size: 0.72rem;
    border-radius: 50%;
    min-width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    animation: popIn 0.25s ease;
}

/* ---- Botones ---- */
button[kind="primary"] {
    background: var(--brand) !important;
    border: none !important;
    border-radius: 16px !important;
    font-weight: 700 !important;
    color: white !important;
    padding: 0.6rem 1.3rem !important;
    box-shadow: 0 6px 16px rgba(255,45,85,0.35);
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

/* ---- Chips de mesa ---- */
.mesa-chip button {
    background: var(--accent) !important;
    border: none !important;
    color: var(--text-dark) !important;
    font-weight: 700 !important;
}

/* ---- Tabs ---- */
button[data-baseweb="tab"] { font-weight: 700; font-size: 0.95rem; color: var(--text-dark) !important; }
div[data-baseweb="tab-highlight"] { background-color: var(--brand) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--brand) !important; }

/* ---- Cards ---- */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 20px !important;
    box-shadow: 0 3px 12px rgba(0,0,0,0.07);
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
    box-shadow: 0 10px 22px rgba(255,45,85,0.18);
    transform: translateY(-3px);
}

/* ---- Badges de precio / puesto ---- */
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

/* ---- Animacion para alertas (agregado correctamente, etc) ---- */
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
</style>
""", unsafe_allow_html=True)

# ---- Header / logo ----
st.markdown("""
<div style="text-align:center; padding: 0.3rem 0 0.1rem 0;">
  <div style="font-family:'Fredoka',sans-serif; font-weight:700; font-size:2.6rem; color:#FF2D55; letter-spacing:1px;">
    🍽️ TABLE
  </div>
  <div style="color:#767680; font-size:0.95rem; margin-top:-6px;">
    Del pedido a la mesa, sin esperas innecesarias
  </div>
</div>
""", unsafe_allow_html=True)

# ---- Carrito flotante (arriba a la derecha) ----
mesa_para_badge = st.session_state.mesa_actual
cantidad_carrito = len(mesa_para_badge.carrito) if mesa_para_badge else 0
badge_html = "<div class='cart-fab'>🛒</div>"
if cantidad_carrito > 0:
    badge_html += f"<div class='cart-badge'>{cantidad_carrito}</div>"
st.markdown(badge_html, unsafe_allow_html=True)

st.write("")

# ------------------------------------------------------------
# SELECTOR DE MESA (en la pantalla principal, no escondido)
# ------------------------------------------------------------
st.markdown("### 🪑 Elegí tu mesa")
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
        st.rerun()

activas = st.session_state.mesas_activas.valores()
if activas:
    st.caption("Mesas ya abiertas — tocá para volver a esa mesa:")
    chip_cols = st.columns(min(len(activas), 6))
    for i, m in enumerate(activas):
        with chip_cols[i % len(chip_cols)]:
            st.markdown('<div class="mesa-chip">', unsafe_allow_html=True)
            if st.button(f"Mesa {m.numero} 🛒{len(m.carrito)}", key=f"chip_{m.numero}",
                         use_container_width=True):
                st.session_state.mesa_actual = m
                st.session_state.ruta_menu = [st.session_state.menu]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ------------------------------------------------------------
# AREA PRINCIPAL: gestion de la mesa seleccionada
# ------------------------------------------------------------
mesa = st.session_state.mesa_actual

if mesa is None:
    st.info("👋 Elegí un numero de mesa arriba para empezar a pedir.")
else:
    st.markdown(f"## Mesa {mesa.numero}")

    tab_menu, tab_carrito, tab_cocina, tab_ruta, tab_factura = st.tabs(
        ["🍔  Menú", "🛒  Carrito", "👨‍🍳  Cocina", "🗺️  Ruta", "🧾  Cuenta"]
    )

    # --- Tab 1: navegar el arbol de categorias y agregar productos ---
    with tab_menu:
        nodo_actual = st.session_state.ruta_menu[-1]

        breadcrumb = " ➜ ".join(
            f"{ICONOS_CATEGORIA.get(n.nombre, '📂')} {n.nombre}"
            for n in st.session_state.ruta_menu
        )
        st.markdown(f"**{breadcrumb}**")

        if len(st.session_state.ruta_menu) > 1:
            if st.button("⬅️ Volver", key="volver_menu"):
                st.session_state.ruta_menu.pop()
                st.rerun()

        st.write("")
        cols = st.columns(3)
        for i, hijo in enumerate(nodo_actual.hijos):
            with cols[i % 3]:
                with st.container(border=True):
                    if hijo.producto:
                        p = hijo.producto
                        icono = ICONOS_PUESTO.get(p.puesto, "🍽️")
                        st.markdown(f"### {icono} {p.nombre}")
                        st.markdown(
                            f"<span class='badge-precio'>Gs. {p.precio:,}</span>"
                            f"<span class='badge-puesto'>{p.puesto}</span>",
                            unsafe_allow_html=True,
                        )
                        st.write("")
                        cantidad = st.number_input(
                            "Cantidad", min_value=1, value=1, step=1,
                            key=f"cant_{p.codigo}", label_visibility="collapsed",
                        )
                        if st.button("➕ Agregar al carrito", key=f"add_{p.codigo}",
                                     use_container_width=True, type="primary"):
                            mesa.agregar_al_carrito(p, cantidad)
                            st.session_state.flash_add = p.codigo
                            st.rerun()

                        # Confirmacion visible justo debajo del boton
                        if st.session_state.flash_add == p.codigo:
                            st.success("✅ ¡Agregado correctamente!")
                            st.session_state.flash_add = None
                    else:
                        icono = ICONOS_CATEGORIA.get(hijo.nombre, "📂")
                        st.markdown(f"### {icono} {hijo.nombre}")
                        st.caption(f"{len(hijo.hijos)} opciones")
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
# Historial (ya no en sidebar, va como seccion plegable al final)
# ------------------------------------------------------------
st.divider()
with st.expander("🧾 Ver historial de facturas"):
    if not st.session_state.historial_facturas:
        st.caption("Aun no hay facturas registradas.")
    else:
        for f in st.session_state.historial_facturas[-10:][::-1]:
            st.write(f"[{f['fecha']}] Mesa {f['mesa']} — Gs. {f['total']:,}")
