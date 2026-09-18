"""
FoodTrack v2 - Version mejorada
Novedades respecto a la version anterior:
  - Soporta VARIAS MESAS abiertas al mismo tiempo (tabla hash de mesas activas)
  - La cocina es una cola COMPARTIDA por puesto (no se reinicia por mesa)
  - El menu se navega por categorias reales (recorriendo el arbol, no una lista plana)
  - Las facturas se guardan en un archivo JSON -> historial persistente entre ejecuciones
  - Manejo de errores: no se rompe si el usuario escribe cualquier cosa

Estructuras propias: Nodo, ListaEnlazada, Cola, Pila, NodoArbol, Grafo, TablaHash.
"""

import json
import os
from datetime import datetime

ARCHIVO_HISTORIAL = "facturas_historial.json"


# ============================================================
# ESTRUCTURAS DE DATOS BASE
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
# CLASES DE NEGOCIO
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
# DATOS INICIALES
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
# ENTRADA DE DATOS ROBUSTA
# ============================================================
def pedir_entero(mensaje, minimo=None):
    while True:
        valor = input(mensaje).strip()
        if not valor.isdigit():
            print("  > Ingresa solo numeros.")
            continue
        valor = int(valor)
        if minimo is not None and valor < minimo:
            print(f"  > Debe ser al menos {minimo}.")
            continue
        return valor


# ============================================================
# NAVEGACION DEL MENU POR ARBOL (categorias reales)
# ============================================================
def navegar_menu(nodo):
    """Permite bajar por las categorias del arbol hasta elegir un producto.
    Devuelve el Producto elegido, o None si el usuario cancela."""
    while True:
        print(f"\n-- {nodo.nombre} --")
        for i, hijo in enumerate(nodo.hijos, start=1):
            etiqueta = hijo.nombre
            if hijo.producto:
                etiqueta += f" (Gs. {hijo.producto.precio:,})"
            print(f"  {i}) {etiqueta}")
        print("  0) Volver / Cancelar")

        opcion = input("Elegi una opcion: ").strip()
        if opcion == "0":
            return None
        if not opcion.isdigit() or not (1 <= int(opcion) <= len(nodo.hijos)):
            print("  > Opcion invalida.")
            continue

        seleccionado = nodo.hijos[int(opcion) - 1]
        if seleccionado.producto:
            return seleccionado.producto
        # si no es hoja, seguimos bajando por el arbol
        resultado = navegar_menu(seleccionado)
        if resultado:
            return resultado
        # si volvio con None, se queda en este mismo nivel (continua el while)


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================
def main():
    catalogo, menu = construir_catalogo_y_menu()
    mapa = construir_mapa()
    mesas_activas = TablaHash()
    colas_cocina = {}          # puesto -> Cola (COMPARTIDA entre todas las mesas)
    historial_facturas = cargar_historial()

    print("=" * 60)
    print(" FOODTRACK v2 - Sistema multi-mesa para Food Park")
    print("=" * 60)

    while True:
        print("\n===== MENU PRINCIPAL =====")
        print("1) Abrir / seleccionar mesa")
        print("2) Ver mesas activas")
        print("3) Ver historial de facturas")
        print("0) Salir")
        opcion = input("Elegi una opcion: ").strip()

        if opcion == "1":
            numero = pedir_entero("Numero de mesa: ", minimo=1)
            mesa = mesas_activas.buscar(numero)
            if mesa is None:
                mesa = Mesa(numero)
                mesas_activas.insertar(numero, mesa)
                print(f"  > Mesa {numero} abierta.")
            gestionar_mesa(mesa, catalogo, menu, mapa, colas_cocina,
                            mesas_activas, historial_facturas)

        elif opcion == "2":
            activas = mesas_activas.valores()
            if not activas:
                print("  No hay mesas activas.")
            else:
                print("\n--- Mesas activas ---")
                for m in activas:
                    print(f"  Mesa {m.numero}: carrito {len(m.carrito)} item(s), "
                          f"confirmados Gs. {m.total_cuenta():,}")

        elif opcion == "3":
            if not historial_facturas:
                print("  Aun no hay facturas registradas.")
            else:
                print("\n--- Historial de facturas ---")
                for f in historial_facturas[-10:]:
                    print(f"  [{f['fecha']}] Mesa {f['mesa']} - Gs. {f['total']:,}")

        elif opcion == "0":
            guardar_historial(historial_facturas)
            print("Historial guardado. Hasta luego!")
            break

        else:
            print("  > Opcion invalida.")


def gestionar_mesa(mesa, catalogo, menu, mapa, colas_cocina,
                    mesas_activas, historial_facturas):
    while True:
        print(f"\n===== MESA {mesa.numero} =====")
        print("1) Ver menu y agregar producto")
        print("2) Deshacer ultimo agregado")
        print("3) Ver carrito actual")
        print("4) Enviar carrito a cocina")
        print("5) Ver estado de cocina (preparar siguiente de cada puesto)")
        print("6) Ver ruta de entrega a un puesto")
        print("7) Cerrar cuenta (facturar y liberar mesa)")
        print("0) Volver al menu principal")
        opcion = input("Elegi una opcion: ").strip()

        if opcion == "1":
            producto = navegar_menu(menu)
            if producto:
                cantidad = pedir_entero("Cantidad: ", minimo=1)
                mesa.agregar_al_carrito(producto, cantidad)
                print(f"  > Agregado: {cantidad}x {producto.nombre}")

        elif opcion == "2":
            quitado = mesa.deshacer()
            print(f"  > Se quito: {quitado}" if quitado else "  Nada para deshacer.")

        elif opcion == "3":
            items = mesa.carrito.recorrer()
            print("\n--- Carrito (sin confirmar) ---")
            if not items:
                print("  (vacio)")
            else:
                for it in items:
                    print(f"  - {it}")
                print(f"  Subtotal: Gs. {mesa.carrito.calcular_total():,}")

        elif opcion == "4":
            items = mesa.carrito.recorrer()
            if not items:
                print("  El carrito esta vacio.")
                continue
            for item in items:
                puesto = item.producto.puesto
                colas_cocina.setdefault(puesto, Cola())
                colas_cocina[puesto].encolar((mesa.numero, item))
                mesa.confirmados.agregar(item)
            mesa.carrito = ListaEnlazada()  # vaciar carrito ya enviado
            print("  > Pedido enviado a cocina.")

        elif opcion == "5":
            if not colas_cocina or all(c.esta_vacia() for c in colas_cocina.values()):
                print("  No hay pedidos pendientes en cocina.")
            for puesto, cola in colas_cocina.items():
                if not cola.esta_vacia():
                    numero_mesa_item, item = cola.desencolar()
                    print(f"  [{puesto}] Preparando para Mesa {numero_mesa_item}: "
                          f"{item.producto.nombre} (~{item.producto.tiempo_prep_seg}s)")

        elif opcion == "6":
            destino = input("Nombre del puesto (ej: Puesto Burger): ").strip()
            camino, distancia = mapa.camino_mas_corto("Mesas", destino)
            if camino is None:
                print("  > Puesto no encontrado en el mapa.")
            else:
                print(f"  Ruta: {' -> '.join(camino)}  ({distancia} m)")

        elif opcion == "7":
            if len(mesa.confirmados) == 0:
                print("  No hay items confirmados para facturar.")
                continue
            items_texto = [str(it) for it in mesa.confirmados.recorrer()]
            total = mesa.total_cuenta()
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
            factura = Factura(mesa.numero, items_texto, total, fecha)
            historial_facturas.append(factura.to_dict())
            guardar_historial(historial_facturas)

            print("\n--- FACTURA ---")
            for texto in items_texto:
                print(f"  {texto}")
            print(f"  TOTAL: Gs. {total:,}")
            print(f"  (Guardada en {ARCHIVO_HISTORIAL})")

            mesas_activas.eliminar(mesa.numero)
            print(f"  Mesa {mesa.numero} liberada.")
            return  # vuelve al menu principal, la mesa ya no existe

        elif opcion == "0":
            return

        else:
            print("  > Opcion invalida.")


if __name__ == "__main__":
    main()
