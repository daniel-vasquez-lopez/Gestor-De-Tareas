# Mis tareas — app de escritorio

Aplicación local para organizar tareas. La interfaz, los gráficos y la lógica están escritos en Python con Tkinter; no utiliza HTML, JavaScript, servidor ni paquetes externos.

## Requisitos

- Python 3.10 o posterior.
- Tkinter, que suele venir incluido con Python.

## Abrir la app

1. Descomprime `gestor_tareas_escritorio.zip`.
2. Abre una terminal en la carpeta descomprimida.
3. Ejecuta `python app.py` (en algunos equipos, `python3 app.py` o `py app.py`).

La ventana de la app aparecerá en el escritorio. Para cerrarla, cierra la ventana.

## Datos y respaldos

Las tareas se guardan automáticamente en `tareas.json`, junto a `app.py`. Si ya tienes un archivo `tareas.json` de la versión original, colócalo en esa carpeta y la app lo cargará. Los botones **Importar** y **Exportar** permiten usar copias JSON.

La app incluye búsqueda, filtros, prioridades, estados, fechas límite, alertas, y gráficas de estado y prioridad. Todo se dibuja desde Python/Tkinter. Para asignar una fecha, pulsa **Elegir fecha** y selecciona un día en el calendario; puedes cambiar de mes, elegir **Hoy** o dejarla vacía con **Sin fecha**.

## Acceso directo en Linux

Se añadió `iniciar.sh` para abrir `app.py` desde esta carpeta y `Gestor de tareas.desktop` como lanzador. También hay una copia del acceso directo en el Escritorio. Si Linux pregunta si confías en el archivo, selecciona **Permitir iniciar** o **Allow Launching**. Mantén la carpeta en su ubicación actual para que el acceso directo siga funcionando.

## Cómo está organizado el código

- `app.py`: ventanas, formularios, lista de tareas y conexión entre las partes.
- `logica.py`: validación, filtros, reglas de tareas y lectura/escritura de `tareas.json`.
- `graficos.py`: colores, distintivo y dibujo de los gráficos.
- `iniciar.sh`: abre la aplicación desde esta carpeta.

Mantén los tres archivos Python en la misma carpeta para que la app pueda importar sus módulos.
