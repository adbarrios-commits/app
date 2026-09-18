"""
TABLE - Servicio a la mesa para Food Parks (interfaz Streamlit)
-----------------------------------------------------------------
Misma logica y mismas estructuras de datos propias que foodtrack_v2.py
(Nodo, ListaEnlazada, Cola, Pila, NodoArbol, Grafo, TablaHash).
Esta version le suma un diseño visual tipo app de delivery (PedidosYa/Monchis).

Para correrlo:
    pip install streamlit
    streamlit run foodtrack_streamlit.py
"""

import json
import os
from datetime import datetime

import streamlit as st

ARCHIVO_HISTORIAL = "facturas_historial.json"

# Iconos usados solo para la parte visual (no afectan la logica)
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
        self.carrito = ListaEnlazada()       # items aun no enviados a cocina
        self.confirmados = ListaEnlazada()   # items ya enviados, para la factura
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


st.set_page_config(page_title="TABLE", page_icon="🍽️", layout="wide")
init_state()

# ============================================================
# ESTILO VISUAL (look de app de delivery)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

:root {
    --brand: #FF4B3E;
    --brand-dark: #E0392D;
    --brand-light: #FFF0EE;
    --ok: #2EC4B6;
    --text-dark: #1D1D1F;
    --text-muted: #767680;
}

.block-container { padding-top: 1rem; padding-bottom: 3rem; max-width: 1050px; }

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1D1D1F 0%, #29292C 100%);
}
section[data-testid="stSidebar"] * { color: #F2F2F4 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12); }
section[data-testid="stSidebar"] .stButton>button {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 12px;
    font-weight: 500;
    padding: 0.5rem 0.9rem;
}
section[data-testid="stSidebar"] .stButton>button:hover {
    background: var(--brand);
    border-color: var(--brand);
    color: white !important;
}
section[data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    color: white !important;
}

/* ---- Buttons (main area) ---- */
button[kind="primary"] {
    background: var(--brand) !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.2rem !important;
    box-shadow: 0 6px 16px rgba(255,75,62,0.30);
}
button[kind="primary"]:hover { background: var(--brand-dark) !important; }

button[kind="secondary"] {
    border-radius: 14px !important;
    border: 1.5px solid #ECECEE !important;
    font-weight: 500 !important;
    color: var(--text-dark) !important;
}
button[kind="secondary"]:hover {
    border-color: var(--brand) !important;
    color: var(--brand) !important;
}

/* ---- Tabs ---- */
button[data-baseweb="tab"] { font-weight: 600; font-size: 0.95rem; }
div[data-baseweb="tab-highlight"] { background-color: var(--brand) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--brand) !important; }

/* ---- Cards (bordered containers = productos / mesas) ---- */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 18px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    transition: box-shadow 0.15s ease, transform 0.15s ease;
    padding: 0.4rem;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
    box-shadow: 0 8px 20px rgba(0,0,0,0.10);
    transform: translateY(-2px);
}

/* ---- Badges ---- */
.badge-precio {
    display: inline-block;
    background: var(--brand-light);
    color: var(--brand);
    font-weight: 700;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.82rem;
}
.badge-puesto {
    display: inline-block;
    background: #F2F2F4;
    color: var(--text-muted);
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    margin-left: 6px;
}
</style>
""", unsafe_allow_html=True)

# ---- Header / logo ----
st.markdown("""
<div style="text-align:center; padding: 0.5rem 0 0.2rem 0;">
  <div style="font-family:'Fredoka',sans-serif; font-weight:700; font-size:2.8rem; color:#FF4B3E; letter-spacing:1px;">
    🍽️ TABLE
  </div>
  <div style="color:#767680; font-size:1rem; margin-top:-6px;">
    Del pedido a la mesa, sin esperas innecesarias
  </div>
</div>
""", unsafe_allow_html=True)
st.write("")

# ------------------------------------------------------------
# BARRA LATERAL
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏠 Panel")

    numero = st.number_input("Numero de mesa", min_value=1, step=1, value=1)
    if st.button("➕ Abrir / seleccionar mesa", use_container_width=True):
        mesa = st.session_state.mesas_activas.buscar(numero)
        if mesa is None:
            mesa = Mesa(numero)
            st.session_state.mesas_activas.insertar(numero, mesa)
        st.session_state.mesa_actual = mesa
        st.session_state.ruta_menu = [st.session_state.menu]
        st.rerun()

    st.divider()
    st.markdown("### 🪑 Mesas activas")
    activas = st.session_state.mesas_activas.valores()
    if not activas:
        st.caption("No hay mesas activas.")
    else:
        for m in activas:
            etiqueta = f"Mesa {m.numero} · 🛒 {len(m.carrito)}"
            if st.button(etiqueta, key=f"sel_mesa_{m.numero}", use_container_width=True):
                st.session_state.mesa_actual = m
                st.session_state.ruta_menu = [st.session_state.menu]
                st.rerun()

    st.divider()
    st.markdown("### 🧾 Historial")
    if not st.session_state.historial_facturas:
        st.caption("Aun no hay facturas registradas.")
    else:
        for f in st.session_state.historial_facturas[-10:][::-1]:
            st.caption(f"[{f['fecha']}] Mesa {f['mesa']} — Gs. {f['total']:,}")


# ------------------------------------------------------------
# AREA PRINCIPAL
# ------------------------------------------------------------
mesa = st.session_state.mesa_actual

if mesa is None:
    st.info("👋 Abri o seleccioná una mesa desde el panel para empezar a pedir.")
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
                        if st.button("Agregar al carrito", key=f"add_{p.codigo}",
                                     use_container_width=True, type="primary"):
                            mesa.agregar_al_carrito(p, cantidad)
                            st.toast(f"Agregado: {cantidad}x {p.nombre}", icon="✅")
                            st.rerun()
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
                    st.toast(f"Se quitó: {quitado.producto.nombre}", icon="↩️")
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
                    st.toast("Pedido enviado a cocina", icon="🍳")
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
