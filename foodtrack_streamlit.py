"""
FoodTrack - Version Streamlit (interfaz clickeable)
-----------------------------------------------------
Misma logica y mismas estructuras de datos propias que foodtrack_v2.py
(Nodo, ListaEnlazada, Cola, Pila, NodoArbol, Grafo, TablaHash), pero con
una interfaz web con botones en vez de menus de texto por consola.

Para correrlo:
    pip install streamlit
    streamlit run foodtrack_streamlit.py
"""

import json
import os
from datetime import datetime

import streamlit as st

ARCHIVO_HISTORIAL = "facturas_historial.json"


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
# ESTADO DE LA APP (reemplaza a las variables locales de main())
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
    st.session_state.colas_cocina = {}          # puesto -> Cola (compartida)
    st.session_state.historial_facturas = cargar_historial()
    st.session_state.mesa_actual = None
    st.session_state.ruta_menu = [menu]          # breadcrumb para navegar el arbol
    st.session_state.log_cocina = []             # ultimos eventos de cocina


init_state()

st.set_page_config(page_title="FoodTrack", page_icon="🍔", layout="wide")
st.title("🍔 FoodTrack — Servicio a la mesa para Food Park")

# ------------------------------------------------------------
# BARRA LATERAL: equivalente al "MENU PRINCIPAL" de la consola
# ------------------------------------------------------------
with st.sidebar:
    st.header("Menu principal")

    numero = st.number_input("Numero de mesa", min_value=1, step=1, value=1)
    if st.button("Abrir / seleccionar mesa", use_container_width=True):
        mesa = st.session_state.mesas_activas.buscar(numero)
        if mesa is None:
            mesa = Mesa(numero)
            st.session_state.mesas_activas.insertar(numero, mesa)
        st.session_state.mesa_actual = mesa
        st.session_state.ruta_menu = [st.session_state.menu]
        st.rerun()

    st.divider()
    st.subheader("Mesas activas")
    activas = st.session_state.mesas_activas.valores()
    if not activas:
        st.caption("No hay mesas activas.")
    else:
        for m in activas:
            etiqueta = f"Mesa {m.numero} — carrito {len(m.carrito)} item(s)"
            if st.button(etiqueta, key=f"sel_mesa_{m.numero}", use_container_width=True):
                st.session_state.mesa_actual = m
                st.session_state.ruta_menu = [st.session_state.menu]
                st.rerun()

    st.divider()
    st.subheader("Historial de facturas")
    if not st.session_state.historial_facturas:
        st.caption("Aun no hay facturas registradas.")
    else:
        for f in st.session_state.historial_facturas[-10:][::-1]:
            st.caption(f"[{f['fecha']}] Mesa {f['mesa']} — Gs. {f['total']:,}")


# ------------------------------------------------------------
# AREA PRINCIPAL: equivalente a gestionar_mesa()
# ------------------------------------------------------------
mesa = st.session_state.mesa_actual

if mesa is None:
    st.info("Abri o seleccioná una mesa desde la barra lateral para empezar.")
else:
    st.subheader(f"Mesa {mesa.numero}")

    tab_menu, tab_carrito, tab_cocina, tab_ruta, tab_factura = st.tabs(
        ["📋 Menu", "🛒 Carrito", "👨‍🍳 Cocina", "🗺️ Ruta de entrega", "🧾 Cerrar cuenta"]
    )

    # --- Tab 1: navegar el arbol de categorias y agregar productos ---
    with tab_menu:
        nodo_actual = st.session_state.ruta_menu[-1]
        st.write("📍 " + " > ".join(n.nombre for n in st.session_state.ruta_menu))

        if len(st.session_state.ruta_menu) > 1:
            if st.button("⬅️ Volver"):
                st.session_state.ruta_menu.pop()
                st.rerun()

        cols = st.columns(3)
        for i, hijo in enumerate(nodo_actual.hijos):
            with cols[i % 3]:
                if hijo.producto:
                    st.markdown(f"**{hijo.producto.nombre}**")
                    st.caption(f"Gs. {hijo.producto.precio:,} · {hijo.producto.puesto}")
                    cantidad = st.number_input(
                        "Cantidad", min_value=1, value=1, step=1,
                        key=f"cant_{hijo.producto.codigo}",
                    )
                    if st.button("Agregar al carrito", key=f"add_{hijo.producto.codigo}"):
                        mesa.agregar_al_carrito(hijo.producto, cantidad)
                        st.success(f"Agregado: {cantidad}x {hijo.producto.nombre}")
                        st.rerun()
                else:
                    if st.button(f"📂 {hijo.nombre}", key=f"nav_{hijo.nombre}_{i}"):
                        st.session_state.ruta_menu.append(hijo)
                        st.rerun()

    # --- Tab 2: carrito, deshacer, enviar a cocina ---
    with tab_carrito:
        items = mesa.carrito.recorrer()
        if not items:
            st.caption("El carrito esta vacio.")
        else:
            for it in items:
                st.write(f"- {it}")
            st.write(f"**Subtotal: Gs. {mesa.carrito.calcular_total():,}**")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("↩️ Deshacer ultimo agregado", use_container_width=True):
                quitado = mesa.deshacer()
                if quitado:
                    st.success(f"Se quito: {quitado}")
                else:
                    st.warning("Nada para deshacer.")
                st.rerun()
        with c2:
            if st.button("✅ Enviar carrito a cocina", use_container_width=True, type="primary"):
                if not items:
                    st.warning("El carrito esta vacio.")
                else:
                    for item in items:
                        puesto = item.producto.puesto
                        st.session_state.colas_cocina.setdefault(puesto, Cola())
                        st.session_state.colas_cocina[puesto].encolar((mesa.numero, item))
                        mesa.confirmados.agregar(item)
                    mesa.carrito = ListaEnlazada()
                    st.success("Pedido enviado a cocina.")
                    st.rerun()

        if len(mesa.confirmados) > 0:
            st.divider()
            st.write("**Ya confirmados (para la factura):**")
            for it in mesa.confirmados.recorrer():
                st.write(f"- {it}")

    # --- Tab 3: estado de cocina (colas FIFO compartidas por puesto) ---
    with tab_cocina:
        colas = st.session_state.colas_cocina
        st.write("**Pedidos pendientes por puesto:**")
        if not colas or all(c.esta_vacia() for c in colas.values()):
            st.caption("No hay pedidos pendientes en cocina.")
        else:
            for puesto, cola in colas.items():
                st.write(f"- {puesto}: {len(cola)} pedido(s) en cola")

        if st.button("👨‍🍳 Preparar siguiente de cada puesto"):
            eventos = []
            for puesto, cola in colas.items():
                if not cola.esta_vacia():
                    numero_mesa_item, item = cola.desencolar()
                    eventos.append(
                        f"[{puesto}] Preparando para Mesa {numero_mesa_item}: "
                        f"{item.producto.nombre} (~{item.producto.tiempo_prep_seg}s)"
                    )
            if not eventos:
                st.warning("No hay nada para preparar.")
            else:
                st.session_state.log_cocina = eventos + st.session_state.log_cocina
            st.rerun()

        if st.session_state.log_cocina:
            st.divider()
            st.write("**Ultimos eventos de cocina:**")
            for ev in st.session_state.log_cocina[:10]:
                st.write(ev)

    # --- Tab 4: ruta mas corta (Dijkstra sobre el grafo del food park) ---
    with tab_ruta:
        destinos = sorted(k for k in st.session_state.mapa.adyacencia.keys() if k != "Mesas")
        destino = st.selectbox("Puesto de destino", destinos)
        if st.button("Calcular ruta"):
            camino, distancia = st.session_state.mapa.camino_mas_corto("Mesas", destino)
            if camino is None:
                st.error("Puesto no encontrado en el mapa.")
            else:
                st.success(f"Ruta: {' → '.join(camino)}  ({distancia} m)")

    # --- Tab 5: cerrar cuenta / facturar ---
    with tab_factura:
        if len(mesa.confirmados) == 0:
            st.caption("No hay items confirmados para facturar todavia.")
        else:
            items_texto = [str(it) for it in mesa.confirmados.recorrer()]
            total = mesa.total_cuenta()
            for texto in items_texto:
                st.write(f"- {texto}")
            st.write(f"**TOTAL: Gs. {total:,}**")

            if st.button("🧾 Facturar y liberar mesa", type="primary"):
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                factura = Factura(mesa.numero, items_texto, total, fecha)
                st.session_state.historial_facturas.append(factura.to_dict())
                guardar_historial(st.session_state.historial_facturas)
                st.session_state.mesas_activas.eliminar(mesa.numero)
                st.session_state.mesa_actual = None
                st.success(f"Factura guardada. Mesa {mesa.numero} liberada.")
                st.rerun()
