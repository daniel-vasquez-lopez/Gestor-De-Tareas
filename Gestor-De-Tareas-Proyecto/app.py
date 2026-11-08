"""Gestor de tareas de escritorio en Python y Tkinter.

No necesita servidor ni paquetes externos. Las tareas se guardan junto a este
archivo, en tareas.json, y conservan el formato de la versión original.
"""

from __future__ import annotations

import json
import calendar
import tkinter as tk
from datetime import date, datetime
from pathlib import Path

from graficos import COLORES, crear_icono_marca, dibujar_barras as dibujar_barras_canvas, dibujar_donut as dibujar_donut_canvas
from logica import (
    DATA_FILE, ESTADOS, PRIORIDADES, alternar_estado, cargar_tareas, categoria_fecha,
    eliminar_tarea, filtrar_tareas, guardar_archivo, guardar_tarea, normalizar_lista,
    resumen_tareas, siguiente_id, validar_fecha,
)
from tkinter import filedialog, messagebox, ttk

class GestorTareas:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.ready = False
        self.tasks: list[dict] = []
        self.filtered_tasks: list[dict] = []
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="Todos los estados")
        self.priority_filter_var = tk.StringVar(value="Todas las prioridades")

        try:
            self.tasks = cargar_tareas()
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showerror(
                "No se pudieron abrir las tareas",
                f"No se modificó tu archivo. Revisa {DATA_FILE.name} e inténtalo otra vez.\n\n{error}",
                parent=root,
            )
            root.destroy()
            return

        self.configurar_ventana()
        self.configurar_estilos()
        self.crear_interfaz()
        self.vincular_eventos()
        self.actualizar()
        self.ready = True

    def configurar_ventana(self) -> None:
        self.root.title("Mis tareas · Gestor personal")
        self.root.geometry("1120x790")
        self.root.minsize(900, 680)
        self.root.configure(bg=COLORES["fondo"])

    def configurar_estilos(self) -> None:
        estilo = ttk.Style(self.root)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("TFrame", background=COLORES["fondo"])
        estilo.configure("Card.TFrame", background=COLORES["tarjeta"])
        estilo.configure("TLabel", background=COLORES["fondo"], foreground=COLORES["texto"])
        estilo.configure("Card.TLabel", background=COLORES["tarjeta"], foreground=COLORES["texto"])
        estilo.configure("Muted.TLabel", background=COLORES["tarjeta"], foreground=COLORES["suave"])
        estilo.configure("Title.TLabel", background=COLORES["fondo"], foreground=COLORES["texto"], font=("Segoe UI", 22, "bold"))
        estilo.configure("Subtitle.TLabel", background=COLORES["fondo"], foreground=COLORES["suave"], font=("Segoe UI", 10))
        estilo.configure("StatValue.TLabel", background=COLORES["tarjeta"], foreground=COLORES["texto"], font=("Segoe UI", 24, "bold"))
        estilo.configure("StatCaption.TLabel", background=COLORES["tarjeta"], foreground=COLORES["suave"], font=("Segoe UI", 9, "bold"))
        estilo.configure("TButton", padding=(12, 8), font=("Segoe UI", 9, "bold"))
        estilo.configure("Primary.TButton", background=COLORES["morado"], foreground="white", borderwidth=0)
        estilo.map("Primary.TButton", background=[("active", "#5e49d1"), ("disabled", "#b8b1ed")], foreground=[("disabled", "#f6f5ff")])
        estilo.configure("Treeview", rowheight=36, background="white", fieldbackground="white", foreground=COLORES["texto"], borderwidth=0, font=("Segoe UI", 9))
        estilo.configure("Treeview.Heading", background="#f7f7fb", foreground=COLORES["suave"], relief="flat", font=("Segoe UI", 9, "bold"), padding=(8, 9))
        estilo.map("Treeview", background=[("selected", COLORES["morado_claro"])], foreground=[("selected", COLORES["texto"])])
        estilo.configure("TCombobox", padding=6)
        estilo.configure("Date.TEntry", padding=6)
        estilo.map(
            "Date.TEntry",
            fieldbackground=[("readonly", "white")],
            foreground=[("readonly", COLORES["texto"])],
        )

    def crear_interfaz(self) -> None:
        self.main = ttk.Frame(self.root, padding=(24, 20, 24, 17))
        self.main.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(3, weight=1)

        self.crear_encabezado()
        self.crear_resumen()
        self.crear_graficas()
        self.crear_lista()
        self.crear_pie()

    def crear_encabezado(self) -> None:
        header = ttk.Frame(self.main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 17))
        header.grid_columnconfigure(0, weight=1)
        identidad = ttk.Frame(header)
        identidad.grid(row=0, column=0, sticky="w")
        self.brand_icon = crear_icono_marca(self.root)
        marca = tk.Label(identidad, image=self.brand_icon, bg=COLORES["fondo"], bd=0)
        marca.pack(side="left", padx=(0, 12))
        textos = ttk.Frame(identidad)
        textos.pack(side="left")
        ttk.Label(textos, text="Mis tareas", style="Title.TLabel").pack(anchor="w")
        ttk.Label(textos, text="Organiza lo importante, un paso a la vez", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        acciones = ttk.Frame(header)
        acciones.grid(row=0, column=1, sticky="e")
        ttk.Button(acciones, text="Importar", command=self.importar).pack(side="left", padx=(0, 7))
        ttk.Button(acciones, text="Exportar", command=self.exportar).pack(side="left", padx=(0, 7))
        ttk.Button(acciones, text="＋  Nueva tarea", style="Primary.TButton", command=self.nueva_tarea).pack(side="left")

    def crear_resumen(self) -> None:
        self.stat_values: dict[str, ttk.Label] = {}
        contenedor = ttk.Frame(self.main)
        contenedor.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        for columna in range(4):
            contenedor.grid_columnconfigure(columna, weight=1, uniform="stats")
        definiciones = (
            ("total", "TOTAL DE TAREAS", COLORES["morado"]),
            ("active", "TAREAS ACTIVAS", COLORES["azul"]),
            ("overdue", "VENCIDAS", COLORES["rojo"]),
            ("soon", "PRÓXIMAS A VENCER", COLORES["naranja"]),
        )
        for columna, (clave, titulo, acento) in enumerate(definiciones):
            card = tk.Frame(contenedor, bg=COLORES["tarjeta"], highlightbackground=COLORES["borde"], highlightthickness=1)
            card.grid(row=0, column=columna, sticky="nsew", padx=(0 if columna == 0 else 7, 0 if columna == 3 else 7))
            tk.Label(card, text=titulo, bg=COLORES["tarjeta"], fg=COLORES["suave"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=15, pady=(13, 4))
            valor = ttk.Label(card, text="0", style="StatValue.TLabel")
            valor.pack(anchor="w", padx=14, pady=(0, 2))
            tk.Frame(card, bg=acento, height=3).pack(fill="x", side="bottom")
            self.stat_values[clave] = valor

    def crear_graficas(self) -> None:
        fila = ttk.Frame(self.main)
        fila.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        fila.grid_columnconfigure(0, weight=1, uniform="charts")
        fila.grid_columnconfigure(1, weight=1, uniform="charts")
        self.donut_card = tk.Frame(fila, bg="white", highlightbackground=COLORES["borde"], highlightthickness=1)
        self.donut_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.bar_card = tk.Frame(fila, bg="white", highlightbackground=COLORES["borde"], highlightthickness=1)
        self.bar_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        for card, titulo, subtitulo in (
            (self.donut_card, "Estado de las tareas", "Distribución de tu trabajo"),
            (self.bar_card, "Prioridad", "Tareas por nivel de importancia"),
        ):
            tk.Label(card, text=titulo, bg="white", fg=COLORES["texto"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
            tk.Label(card, text=subtitulo, bg="white", fg=COLORES["suave"], font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(2, 0))
        self.donut_canvas = tk.Canvas(self.donut_card, height=176, bg="white", highlightthickness=0)
        self.donut_canvas.pack(fill="both", expand=True, padx=6, pady=(3, 8))
        self.bar_canvas = tk.Canvas(self.bar_card, height=176, bg="white", highlightthickness=0)
        self.bar_canvas.pack(fill="both", expand=True, padx=10, pady=(3, 8))
        self.donut_canvas.bind("<Configure>", lambda _event: self.dibujar_donut())
        self.bar_canvas.bind("<Configure>", lambda _event: self.dibujar_barras())

    def crear_lista(self) -> None:
        card = tk.Frame(self.main, bg="white", highlightbackground=COLORES["borde"], highlightthickness=1)
        card.grid(row=3, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        toolbar = tk.Frame(card, bg="white")
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        title_row = tk.Frame(toolbar, bg="white")
        title_row.grid(row=0, column=0, sticky="w")
        tk.Label(title_row, text="Tu lista", bg="white", fg=COLORES["texto"], font=("Segoe UI", 12, "bold")).pack(side="left")
        self.visible_label = tk.Label(title_row, text="0", bg=COLORES["morado_claro"], fg=COLORES["morado"], font=("Segoe UI", 8, "bold"), padx=8, pady=2)
        self.visible_label.pack(side="left", padx=8)

        filtros = tk.Frame(toolbar, bg="white")
        filtros.grid(row=0, column=1, sticky="e")
        self.search_entry = ttk.Entry(filtros, textvariable=self.search_var, width=24)
        self.search_entry.pack(side="left", padx=(0, 7), ipady=4)
        self.search_entry.insert(0, "")
        self.status_filter = ttk.Combobox(
            filtros, textvariable=self.status_filter_var, state="readonly", width=17,
            values=("Todos los estados", *ESTADOS),
        )
        self.status_filter.pack(side="left", padx=(0, 7))
        self.priority_filter = ttk.Combobox(
            filtros, textvariable=self.priority_filter_var, state="readonly", width=17,
            values=("Todas las prioridades", *PRIORIDADES),
        )
        self.priority_filter.pack(side="left")

        tabla_frame = tk.Frame(card, bg="white")
        tabla_frame.grid(row=1, column=0, sticky="nsew", padx=12)
        card.grid_rowconfigure(1, weight=1)
        tabla_frame.grid_rowconfigure(0, weight=1)
        tabla_frame.grid_columnconfigure(0, weight=1)
        columnas = ("nombre", "estado", "prioridad", "fecha")
        self.tabla = ttk.Treeview(tabla_frame, columns=columnas, show="headings", selectmode="browse")
        self.tabla.heading("nombre", text="TAREA")
        self.tabla.heading("estado", text="ESTADO")
        self.tabla.heading("prioridad", text="PRIORIDAD")
        self.tabla.heading("fecha", text="FECHA LÍMITE")
        self.tabla.column("nombre", width=460, minwidth=220, anchor="w")
        self.tabla.column("estado", width=145, minwidth=110, anchor="w")
        self.tabla.column("prioridad", width=105, minwidth=85, anchor="w")
        self.tabla.column("fecha", width=145, minwidth=120, anchor="w")
        self.tabla.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tabla.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tabla.configure(yscrollcommand=scroll.set)
        self.tabla.tag_configure("vencida", foreground=COLORES["rojo"])
        self.tabla.tag_configure("proxima", foreground=COLORES["naranja"])
        self.tabla.tag_configure("completada", foreground="#9297a5")
        self.tabla.tag_configure("normal", foreground=COLORES["texto"])

        botones = tk.Frame(card, bg="white")
        botones.grid(row=2, column=0, sticky="ew", padx=16, pady=(9, 12))
        self.selection_hint = tk.Label(botones, text="Selecciona una tarea para ver sus acciones", bg="white", fg=COLORES["suave"], font=("Segoe UI", 8))
        self.selection_hint.pack(side="left")
        self.delete_button = ttk.Button(botones, text="Eliminar", command=self.eliminar_seleccionada, state="disabled")
        self.delete_button.pack(side="right", padx=(7, 0))
        self.edit_button = ttk.Button(botones, text="Editar", command=self.editar_seleccionada, state="disabled")
        self.edit_button.pack(side="right", padx=(7, 0))
        self.complete_button = ttk.Button(botones, text="Completar", command=self.alternar_completada, state="disabled")
        self.complete_button.pack(side="right")

    def crear_pie(self) -> None:
        pie = ttk.Frame(self.main)
        pie.grid(row=4, column=0, sticky="ew", pady=(9, 0))
        pie.grid_columnconfigure(0, weight=1)
        self.status_message = ttk.Label(pie, text="Los cambios se guardan en tareas.json", style="Subtitle.TLabel")
        self.status_message.grid(row=0, column=0, sticky="w")
        ttk.Label(pie, text="Aplicación local · Python + Tkinter", style="Subtitle.TLabel").grid(row=0, column=1, sticky="e")

    def vincular_eventos(self) -> None:
        self.search_var.trace_add("write", lambda *_args: self.actualizar_lista())
        self.status_filter.bind("<<ComboboxSelected>>", lambda _event: self.actualizar_lista())
        self.priority_filter.bind("<<ComboboxSelected>>", lambda _event: self.actualizar_lista())
        self.tabla.bind("<<TreeviewSelect>>", lambda _event: self.actualizar_botones())
        self.tabla.bind("<Double-1>", lambda _event: self.editar_seleccionada())
        self.root.bind("<Control-n>", lambda _event: self.nueva_tarea())
        self.root.bind("<Control-f>", lambda _event: self.search_entry.focus_set())

    def categoria_fecha(self, tarea: dict) -> str:
        return categoria_fecha(tarea)

    def dibujar_donut(self) -> None:
        if hasattr(self, "donut_canvas"):
            self.donut_photo = dibujar_donut_canvas(self.donut_canvas, self.tasks)

    def dibujar_barras(self) -> None:
        if hasattr(self, "bar_canvas"):
            dibujar_barras_canvas(self.bar_canvas, self.tasks)

    def actualizar(self) -> None:
        self.actualizar_resumen()
        self.actualizar_lista()

    def actualizar_resumen(self) -> None:
        resumen = resumen_tareas(self.tasks)
        for clave, valor in resumen.items():
            self.stat_values[clave].configure(text=str(valor))
        self.dibujar_donut()
        self.dibujar_barras()

    def tareas_filtradas(self) -> list[dict]:
        return filtrar_tareas(
            self.tasks, self.search_var.get(),
            self.status_filter_var.get(), self.priority_filter_var.get(),
        )

    def actualizar_lista(self) -> None:
        if not hasattr(self, "tabla"):
            return
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        self.filtered_tasks = self.tareas_filtradas()
        self.visible_label.configure(text=str(len(self.filtered_tasks)))
        for tarea in self.filtered_tasks:
            categoria = self.categoria_fecha(tarea)
            fecha = tarea["fecha_limite"] or "Sin fecha"
            self.tabla.insert(
                "", "end", iid=str(tarea["id"]),
                values=(tarea["nombre"], tarea["estado"], tarea["prioridad"], fecha),
                tags=(categoria or "normal",),
            )
        if not self.tasks:
            mensaje = "Tu lista está despejada. Agrega una tarea para empezar."
        elif not self.filtered_tasks:
            mensaje = "No hay tareas que coincidan con la búsqueda o los filtros."
        else:
            mensaje = f"Mostrando {len(self.filtered_tasks)} de {len(self.tasks)} tareas · Guardado automático"
        self.status_message.configure(text=mensaje)
        self.actualizar_botones()

    def tarea_seleccionada(self) -> dict | None:
        seleccion = self.tabla.selection()
        if not seleccion:
            return None
        identificador = int(seleccion[0])
        return next((tarea for tarea in self.tasks if tarea["id"] == identificador), None)

    def actualizar_botones(self) -> None:
        tarea = self.tarea_seleccionada()
        estado = "normal" if tarea else "disabled"
        self.edit_button.configure(state=estado)
        self.delete_button.configure(state=estado)
        self.complete_button.configure(state=estado)
        if tarea:
            texto = "Reabrir tarea" if tarea["estado"] == "Completada" else "Marcar completada"
            self.complete_button.configure(text=texto)
            self.selection_hint.configure(text=f"Seleccionada: {tarea['nombre'][:48]}")
        else:
            self.selection_hint.configure(text="Selecciona una tarea para ver sus acciones")

    def persistir(self) -> bool:
        try:
            guardar_archivo(self.tasks)
            self.actualizar()
            return True
        except OSError as error:
            messagebox.showerror("No se pudo guardar", f"No se guardaron los cambios en {DATA_FILE}.\n\n{error}", parent=self.root)
            return False

    def nueva_tarea(self) -> None:
        self.abrir_editor()

    def editar_seleccionada(self) -> None:
        tarea = self.tarea_seleccionada()
        if tarea:
            self.abrir_editor(tarea)

    def abrir_editor(self, tarea: dict | None = None) -> None:
        ventana = tk.Toplevel(self.root)
        ventana.title("Editar tarea" if tarea else "Nueva tarea")
        ventana.configure(bg="white")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()
        ventana.geometry("500x535")

        contenido = tk.Frame(ventana, bg="white", padx=24, pady=22)
        contenido.pack(fill="both", expand=True)
        tk.Label(contenido, text="Editar tarea" if tarea else "Nueva tarea", bg="white", fg=COLORES["texto"], font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(contenido, text="Agrega detalles para mantenerla organizada.", bg="white", fg=COLORES["suave"], font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 17))

        def etiqueta(texto: str) -> None:
            tk.Label(contenido, text=texto, bg="white", fg="#565b70", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 5))

        etiqueta("Nombre")
        nombre_var = tk.StringVar(value=tarea["nombre"] if tarea else "")
        nombre_entry = ttk.Entry(contenido, textvariable=nombre_var, font=("Segoe UI", 10))
        nombre_entry.pack(fill="x", ipady=5)

        etiqueta("Descripción")
        descripcion = tk.Text(contenido, height=4, wrap="word", relief="solid", borderwidth=1, highlightthickness=1, highlightbackground=COLORES["borde"], highlightcolor=COLORES["morado"], font=("Segoe UI", 9), padx=8, pady=7)
        descripcion.pack(fill="x")
        if tarea:
            descripcion.insert("1.0", tarea["descripcion"])

        columnas = tk.Frame(contenido, bg="white")
        columnas.pack(fill="x", pady=(2, 0))
        columnas.grid_columnconfigure(0, weight=1)
        columnas.grid_columnconfigure(1, weight=1)
        tk.Label(columnas, text="Prioridad", bg="white", fg="#565b70", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(8, 5))
        tk.Label(columnas, text="Estado", bg="white", fg="#565b70", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(8, 5))
        prioridad_var = tk.StringVar(value=tarea["prioridad"] if tarea else "Media")
        estado_var = tk.StringVar(value=tarea["estado"] if tarea else "Pendiente")
        ttk.Combobox(columnas, textvariable=prioridad_var, values=PRIORIDADES, state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 6))
        ttk.Combobox(columnas, textvariable=estado_var, values=ESTADOS, state="readonly").grid(row=1, column=1, sticky="ew", padx=(6, 0))

        etiqueta("Fecha límite · opcional")
        fecha_var = tk.StringVar(value=tarea["fecha_limite"] if tarea else "")
        fila_fecha = tk.Frame(contenido, bg="white")
        fila_fecha.pack(fill="x")
        fila_fecha.grid_columnconfigure(0, weight=1)
        fecha_entry = ttk.Entry(fila_fecha, textvariable=fecha_var, state="readonly", style="Date.TEntry")
        fecha_entry.grid(row=0, column=0, sticky="ew", ipady=3)

        def abrir_calendario(_evento=None) -> None:
            try:
                fecha_actual = datetime.strptime(fecha_var.get(), "%d/%m/%Y").date()
            except ValueError:
                fecha_actual = date.today()
            mes_visible = [date(fecha_actual.year, fecha_actual.month, 1)]

            calendario_popup = tk.Toplevel(ventana)
            calendario_popup.title("Elegir fecha")
            calendario_popup.configure(bg="white")
            calendario_popup.resizable(False, False)
            calendario_popup.transient(ventana)

            panel = tk.Frame(calendario_popup, bg="white", padx=10, pady=9)
            panel.pack(fill="both", expand=True)
            cabecera = tk.Frame(panel, bg="white")
            cabecera.pack(fill="x", pady=(0, 5))
            cabecera.grid_columnconfigure(1, weight=1)
            dias_panel = tk.Frame(panel, bg="white")
            dias_panel.pack(fill="both", expand=True)
            pie_calendario = tk.Frame(panel, bg="white")
            pie_calendario.pack(fill="x", pady=(7, 0))

            meses_es = (
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
            )
            titulo_mes = tk.Label(
                cabecera, bg="white", fg=COLORES["texto"],
                font=("Segoe UI", 10, "bold"), anchor="center",
            )
            titulo_mes.grid(row=0, column=1, sticky="ew")

            def cerrar_calendario() -> None:
                if calendario_popup.winfo_exists():
                    try:
                        calendario_popup.grab_release()
                    except tk.TclError:
                        pass
                    calendario_popup.destroy()
                if ventana.winfo_exists():
                    ventana.grab_set()

            def elegir(fecha_elegida: date | None) -> None:
                fecha_var.set(fecha_elegida.strftime("%d/%m/%Y") if fecha_elegida else "")
                cerrar_calendario()

            def mover_mes(cambio: int) -> None:
                mes = mes_visible[0].month - 1 + cambio
                mes_visible[0] = date(mes_visible[0].year + mes // 12, mes % 12 + 1, 1)
                dibujar_dias()

            tk.Button(
                cabecera, text="‹", command=lambda: mover_mes(-1),
                bg="white", fg=COLORES["texto"], activebackground=COLORES["morado_claro"],
                relief="flat", bd=0, font=("Segoe UI", 15), width=2, cursor="hand2",
            ).grid(row=0, column=0)
            tk.Button(
                cabecera, text="›", command=lambda: mover_mes(1),
                bg="white", fg=COLORES["texto"], activebackground=COLORES["morado_claro"],
                relief="flat", bd=0, font=("Segoe UI", 15), width=2, cursor="hand2",
            ).grid(row=0, column=2)

            for columna, nombre_dia in enumerate(("L", "M", "X", "J", "V", "S", "D")):
                tk.Label(
                    dias_panel, text=nombre_dia, width=4, pady=3, bg="white",
                    fg=COLORES["suave"], font=("Segoe UI", 8, "bold"),
                ).grid(row=0, column=columna, sticky="nsew")
                dias_panel.grid_columnconfigure(columna, weight=1)

            def dibujar_dias() -> None:
                for hijo in dias_panel.grid_slaves():
                    if int(hijo.grid_info().get("row", 0)) > 0:
                        hijo.destroy()
                mes = mes_visible[0]
                titulo_mes.configure(text=f"{meses_es[mes.month - 1].capitalize()} {mes.year}")
                semanas = calendar.Calendar(firstweekday=0).monthdayscalendar(mes.year, mes.month)
                semanas.extend([[0] * 7 for _ in range(6 - len(semanas))])
                try:
                    seleccionado = datetime.strptime(fecha_var.get(), "%d/%m/%Y").date()
                except ValueError:
                    seleccionado = None
                for fila, semana in enumerate(semanas, start=1):
                    for columna, numero in enumerate(semana):
                        if numero == 0:
                            tk.Label(dias_panel, text="", bg="white", width=4).grid(row=fila, column=columna, padx=1, pady=1)
                            continue
                        fecha_dia = date(mes.year, mes.month, numero)
                        activo = fecha_dia == seleccionado
                        es_hoy = fecha_dia == date.today()
                        color_fondo = COLORES["morado"] if activo else COLORES["morado_claro"] if es_hoy else "white"
                        color_texto = "white" if activo else COLORES["morado"] if es_hoy else COLORES["texto"]
                        tk.Button(
                            dias_panel, text=str(numero), width=4, pady=3,
                            command=lambda f=fecha_dia: elegir(f),
                            bg=color_fondo, fg=color_texto,
                            activebackground=COLORES["morado_claro"], activeforeground=COLORES["texto"],
                            relief="flat", bd=0, highlightthickness=0,
                            font=("Segoe UI", 9, "bold" if activo or es_hoy else "normal"),
                            cursor="hand2",
                        ).grid(row=fila, column=columna, padx=1, pady=1, sticky="nsew")

            ttk.Button(pie_calendario, text="Sin fecha", command=lambda: elegir(None)).pack(side="left")
            ttk.Button(pie_calendario, text="Hoy", style="Primary.TButton", command=lambda: elegir(date.today())).pack(side="right")
            dibujar_dias()
            calendario_popup.bind("<Escape>", lambda _e: cerrar_calendario())
            calendario_popup.protocol("WM_DELETE_WINDOW", cerrar_calendario)
            calendario_popup.update_idletasks()
            x = ventana.winfo_rootx() + ventana.winfo_width() + 6
            y = fecha_entry.winfo_rooty()
            ancho_popup = calendario_popup.winfo_reqwidth()
            alto_popup = calendario_popup.winfo_reqheight()
            ancho_pantalla = calendario_popup.winfo_screenwidth()
            alto_pantalla = calendario_popup.winfo_screenheight()
            if x + ancho_popup > ancho_pantalla:
                x = max(4, fecha_entry.winfo_rootx() + fecha_entry.winfo_width() - ancho_popup)
            if y + alto_popup > alto_pantalla - 36:
                y = max(4, fecha_entry.winfo_rooty() - alto_popup - 4)
            calendario_popup.geometry(f"+{x}+{y}")
            calendario_popup.grab_set()

        ttk.Button(fila_fecha, text="Elegir fecha", command=abrir_calendario).grid(row=0, column=1, padx=(8, 0), sticky="ns")
        fecha_entry.bind("<Button-1>", abrir_calendario)
        fecha_entry.bind("<space>", abrir_calendario)
        tk.Label(contenido, text="Elige una fecha en el calendario. Déjala vacía si no tiene fecha.", bg="white", fg="#999daf", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        acciones = tk.Frame(contenido, bg="white")
        acciones.pack(fill="x", side="bottom", pady=(18, 0))

        def guardar() -> None:
            nombre = nombre_var.get().strip()
            if not nombre:
                messagebox.showwarning("Falta el nombre", "Escribe un nombre para la tarea.", parent=ventana)
                nombre_entry.focus_set()
                return
            try:
                fecha = validar_fecha(fecha_var.get())
            except ValueError as error:
                messagebox.showwarning("Revisa la fecha", str(error), parent=ventana)
                return
            datos = {
                "id": tarea["id"] if tarea else siguiente_id(self.tasks),
                "nombre": nombre[:200],
                "descripcion": descripcion.get("1.0", "end-1c").strip()[:2000],
                "prioridad": prioridad_var.get(),
                "estado": estado_var.get(),
                "fecha_limite": fecha,
            }
            self.tasks = guardar_tarea(self.tasks, datos)
            if self.persistir():
                ventana.destroy()

        ttk.Button(acciones, text="Cancelar", command=ventana.destroy).pack(side="right", padx=(7, 0))
        ttk.Button(acciones, text="Guardar cambios" if tarea else "Guardar tarea", style="Primary.TButton", command=guardar).pack(side="right")
        ventana.bind("<Escape>", lambda _event: ventana.destroy())
        ventana.bind("<Control-Return>", lambda _event: guardar())
        nombre_entry.focus_set()

    def alternar_completada(self) -> None:
        tarea = self.tarea_seleccionada()
        if not tarea:
            return
        tarea["estado"] = alternar_estado(tarea)
        if self.persistir():
            self.status_message.configure(text="Tarea actualizada y guardada")

    def eliminar_seleccionada(self) -> None:
        tarea = self.tarea_seleccionada()
        if not tarea:
            return
        confirmar = messagebox.askyesno(
            "Eliminar tarea",
            f"¿Quieres eliminar “{tarea['nombre']}”?\nEsta acción no se puede deshacer.",
            parent=self.root,
        )
        if not confirmar:
            return
        self.tasks = eliminar_tarea(self.tasks, tarea["id"])
        if self.persistir():
            self.status_message.configure(text="Tarea eliminada")

    def exportar(self) -> None:
        ruta = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar tareas",
            defaultextension=".json",
            initialfile=f"tareas-{date.today().isoformat()}.json",
            filetypes=(("Archivo JSON", "*.json"), ("Todos los archivos", "*.*")),
        )
        if not ruta:
            return
        try:
            guardar_archivo(self.tasks, Path(ruta))
            messagebox.showinfo("Respaldo creado", f"Se guardaron {len(self.tasks)} tareas en el archivo elegido.", parent=self.root)
        except OSError as error:
            messagebox.showerror("Error al exportar", str(error), parent=self.root)

    def importar(self) -> None:
        ruta = filedialog.askopenfilename(
            parent=self.root,
            title="Importar tareas",
            filetypes=(("Archivo JSON", "*.json"), ("Todos los archivos", "*.*")),
        )
        if not ruta:
            return
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            importadas = normalizar_lista(datos)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showerror("No se pudo importar", str(error), parent=self.root)
            return
        confirmar = messagebox.askyesno(
            "Reemplazar lista",
            f"Se reemplazarán tus {len(self.tasks)} tareas por las {len(importadas)} del archivo. ¿Continuar?",
            parent=self.root,
        )
        if confirmar:
            self.tasks = importadas
            if self.persistir():
                self.status_message.configure(text=f"Se importaron {len(importadas)} tareas")


def main() -> None:
    root = tk.Tk()
    app = GestorTareas(root)
    if app.ready:
        root.mainloop()


if __name__ == "__main__":
    main()
