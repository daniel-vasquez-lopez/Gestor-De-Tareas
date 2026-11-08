"""Dibujo de los gráficos y recursos visuales del gestor."""

from __future__ import annotations

import math
import tkinter as tk

from logica import PRIORIDADES

COLORES = {
    "fondo": "#f5f6fa",
    "tarjeta": "#ffffff",
    "texto": "#25283d",
    "suave": "#777d92",
    "borde": "#e8eaf1",
    "morado": "#705be8",
    "morado_claro": "#f0edff",
    "verde": "#2b9a72",
    "naranja": "#d88b38",
    "rojo": "#d85968",
    "azul": "#5287d2",
    "gris": "#a2a7b6",
}

ESTADOS_GRAFICO = ("Pendiente", "En progreso", "Completada")


def crear_icono_marca(master: tk.Misc, tamano: int = 46) -> tk.PhotoImage:
    """Crea el distintivo circular suavizado junto al título."""
    escala = 4
    centro = tamano * escala / 2
    radio_exterior = centro - escala
    radio_interior = tamano * 0.39 * escala
    morado = (112, 91, 232)
    halo = (240, 237, 255)
    fondo = (245, 246, 250)
    puntos = ((0.33, 0.51), (0.45, 0.63), (0.69, 0.37))
    grosor = tamano * 0.075

    def color_pixel(px: float, py: float) -> tuple[int, int, int]:
        x, y = px / escala, py / escala
        distancia = math.hypot(px - centro, py - centro)
        if distancia <= radio_interior:
            color = morado
        elif distancia <= radio_exterior:
            color = halo
        else:
            return fondo
        for (ax, ay), (bx, by) in zip(puntos, puntos[1:]):
            ax, ay, bx, by = ax * tamano, ay * tamano, bx * tamano, by * tamano
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            if math.hypot(x - (ax + t * dx), y - (ay + t * dy)) <= grosor / 2:
                if distancia <= radio_interior:
                    return (255, 255, 255)
        return color

    filas = []
    muestras = escala * escala
    for y in range(tamano):
        fila = []
        for x in range(tamano):
            suma = [0, 0, 0]
            for sy in range(escala):
                for sx in range(escala):
                    rgb = color_pixel(x * escala + sx + 0.5, y * escala + sy + 0.5)
                    for canal in range(3):
                        suma[canal] += rgb[canal]
            fila.append("#%02x%02x%02x" % tuple(canal // muestras for canal in suma))
        filas.append("{" + " ".join(fila) + "}")
    imagen = tk.PhotoImage(master=master, width=tamano, height=tamano)
    imagen.put(" ".join(filas))
    return imagen


def dibujar_donut(canvas: tk.Canvas, tareas: list[dict]) -> tk.PhotoImage | None:
    """Dibuja el gráfico de estado suavizado y devuelve la imagen del anillo."""
    canvas.delete("all")
    ancho = max(canvas.winfo_width(), 300)
    alto = max(canvas.winfo_height(), 170)
    x0, y0, diametro = 18, 14, min(142, alto - 22)
    x1, y1 = x0 + diametro, y0 + diametro
    colores = {
        "Pendiente": COLORES["gris"],
        "En progreso": COLORES["morado"],
        "Completada": COLORES["verde"],
    }
    conteos = {estado: sum(t["estado"] == estado for t in tareas) for estado in ESTADOS_GRAFICO}
    total = len(tareas)
    centro_x, centro_y = (x0 + x1) / 2, (y0 + y1) / 2
    imagen = _crear_donut_suave(canvas, diametro, conteos, total, colores)
    canvas.create_image(centro_x, centro_y, image=imagen)
    canvas.create_text(centro_x, centro_y - 5, text=str(total), fill=COLORES["texto"], font=("Segoe UI", 20, "bold"))
    canvas.create_text(centro_x, centro_y + 17, text="en total", fill=COLORES["suave"], font=("Segoe UI", 8))
    leyenda_x = min(x1 + 26, ancho - 130)
    for indice, estado in enumerate(ESTADOS_GRAFICO):
        y = 43 + indice * 31
        canvas.create_oval(leyenda_x, y, leyenda_x + 9, y + 9, fill=colores[estado], outline="")
        canvas.create_text(leyenda_x + 17, y + 4, text=estado, anchor="w", fill=COLORES["suave"], font=("Segoe UI", 8))
        canvas.create_text(ancho - 19, y + 4, text=str(conteos[estado]), anchor="e", fill=COLORES["texto"], font=("Segoe UI", 9, "bold"))
    return imagen


def _crear_donut_suave(master: tk.Misc, diametro: int, conteos: dict, total: int, colores: dict) -> tk.PhotoImage:
    """Rasteriza el anillo con sobremuestreo para evitar bordes dentados."""
    escala = 4
    tamano = max(1, diametro) * escala
    centro = tamano / 2
    radio_exterior = centro - 1
    radio_interior = centro * 0.61
    fondo = (255, 255, 255)

    def rgb(color: str) -> tuple[int, int, int]:
        valor = color.lstrip("#")
        return tuple(int(valor[i:i + 2], 16) for i in (0, 2, 4))

    if total:
        segmentos = []
        acumulado = 0.0
        for estado in ESTADOS_GRAFICO:
            cantidad = conteos[estado]
            if cantidad:
                acumulado += cantidad / total * 360
                segmentos.append((acumulado, rgb(colores[estado])))
    else:
        segmentos = [(360.0, rgb("#e5e7ee"))]

    colores_salida = []
    for y in range(diametro):
        fila = []
        for x in range(diametro):
            suma_r = suma_g = suma_b = 0
            for sy in range(escala):
                py = y * escala + sy + 0.5 - centro
                for sx in range(escala):
                    px = x * escala + sx + 0.5 - centro
                    distancia = px * px + py * py
                    tono = fondo
                    if radio_interior * radio_interior <= distancia <= radio_exterior * radio_exterior:
                        if total:
                            angulo = (math.degrees(math.atan2(-py, px)) - 90) % 360
                            for limite, color in segmentos:
                                if angulo < limite:
                                    tono = color
                                    break
                        else:
                            tono = segmentos[0][1]
                    suma_r += tono[0]
                    suma_g += tono[1]
                    suma_b += tono[2]
            muestras = escala * escala
            fila.append("#%02x%02x%02x" % (suma_r // muestras, suma_g // muestras, suma_b // muestras))
        colores_salida.append("{" + " ".join(fila) + "}")
    imagen = tk.PhotoImage(master=master, width=diametro, height=diametro)
    imagen.put(" ".join(colores_salida))
    return imagen


def dibujar_barras(canvas: tk.Canvas, tareas: list[dict]) -> None:
    """Dibuja la distribución de tareas por prioridad."""
    canvas.delete("all")
    ancho = max(canvas.winfo_width(), 280)
    conteos = {prioridad: sum(t["prioridad"] == prioridad for t in tareas) for prioridad in PRIORIDADES}
    maximo = max(conteos.values(), default=0) or 1
    colores = {"Alta": COLORES["rojo"], "Media": COLORES["naranja"], "Baja": COLORES["azul"]}
    x_etiqueta, x_barra, derecha = 18, 82, ancho - 22
    ancho_barra = max(80, derecha - x_barra - 28)
    for indice, prioridad in enumerate(PRIORIDADES):
        y = 43 + indice * 40
        canvas.create_text(x_etiqueta, y + 5, text=prioridad, anchor="w", fill=COLORES["suave"], font=("Segoe UI", 9))
        canvas.create_rectangle(x_barra, y, x_barra + ancho_barra, y + 11, fill="#f0f1f6", outline="")
        cantidad = conteos[prioridad]
        if cantidad:
            relleno = max(5, ancho_barra * cantidad / maximo)
            canvas.create_rectangle(x_barra, y, x_barra + relleno, y + 11, fill=colores[prioridad], outline="")
        canvas.create_text(derecha, y + 5, text=str(cantidad), anchor="e", fill=COLORES["texto"], font=("Segoe UI", 9, "bold"))
