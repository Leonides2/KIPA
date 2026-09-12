# KDE Icon Package Assistant (KIPA)

Aplicación de escritorio (Python + Qt, PySide6/Qt6 o PySide2/Qt5) para
crear, configurar y empaquetar temas de iconos personalizados para KDE,
siguiendo la especificación [freedesktop Icon Theme](https://specifications.freedesktop.org/icon-theme-spec/icon-theme-spec-latest.html).

Permite añadir iconos (SVG/PNG), definir tamaños y contextos, generar la
metadata (`index.theme`) y exportar el resultado en dos formatos:

- **Modo A — Distribución privada**: un `.tar.gz` con la estructura completa
  del tema más un script `install.sh` para instalar manualmente en
  `~/.local/share/icons/`.
- **Modo B — Paquete KDE**: un paquete compatible con
  `kpackagetool6 -t Icons` (incluye `metadata.json` en formato KPackage)
  para instalación con un único comando.

No requiere conexión a internet ni genera `.deb`: el objetivo es un paquete
de **personalización** (tema de iconos), no un paquete de software.

## Requisitos

- Python 3.9+ (3.11+ recomendado si usas Qt6/PySide6)
- Linux/KDE (no es objetivo multiplataforma)

## Instalación

El binding de Qt no viene fijado como dependencia: se elige uno de los
dos extras según tu Plasma.

```bash
python3 -m venv .venv
source .venv/bin/activate

# Plasma 6 / Qt6 (recomendado)
pip install -e ".[dev,qt6]"

# Plasma 5 / Qt5 (sistemas más antiguos)
pip install -e ".[dev,qt5]"
```

Dependencias principales: `PySide6` o `PySide2` (interfaz gráfica) y
`Pillow` (redimensionado de PNG). El rasterizado de SVG a tamaños fijos
usa opcionalmente `cairosvg` si está instalado; si no, sube también una
versión PNG del icono para generar tamaños fijos, o usa solo `scalable/`.

### ⚠️ Aspecto visual "genérico" (Fusion) en vez de nativo de KDE/Breeze

`pip install PySide6` trae su **propio** Qt6 embebido (aislado del Qt6
del sistema). Ese Qt6 embebido no puede cargar el plugin de estilo Breeze
del sistema (incompatibilidad de ABI entre builds de Qt6), así que la app
cae al estilo `Fusion` genérico — se nota especialmente en los
desplegables (`QComboBox`), que no se ven como el resto de KDE.

No es un bug de la app; es una limitación conocida de instalar PySide6
vía pip en Linux. Alternativas:

- **Recomendado**: instala PySide6 con el paquete de tu distro (el mismo
  que sugiere el chequeo de dependencias al arrancar, p. ej.
  `sudo apt install python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets`)
  y crea el venv con `python3 -m venv --system-site-packages .venv` para
  que pueda verlo — así usa el mismo Qt6 que el resto de KDE y se integra
  con Breeze de forma nativa.
- Si necesitas el PySide6 de pip (p. ej. para el binario standalone de
  PyInstaller), puedes forzar el estilo con
  `QT_STYLE_OVERRIDE=Breeze python -m src.main` si tienes el estilo Qt6
  de Breeze instalado a nivel de sistema — con la misma limitación de ABI,
  puede que tampoco cargue.

### Soporte Qt5 (PySide2) además de Qt6 (PySide6)

Todo el código de `src/ui/` importa Qt a través de
[`src/ui/qt_compat.py`](src/ui/qt_compat.py), que prueba PySide6 primero
y usa PySide2 como alternativa, y solo enums en la sintaxis "plana"
(`Qt.Horizontal`, `QDialogButtonBox.Ok`...) compatible con ambos.
`dependency_checker.py` acepta cualquiera de los dos como binding
obligatorio.

⚠️ **Aviso**: PySide2 no tiene wheels oficiales para Python 3.11+; en un
sistema Plasma 5 típico (Python 3.9/3.10) debería funcionar, pero este
shim **no se ha podido validar visualmente** en un entorno con Plasma 5
real (solo se verificó que PySide6/Qt6 sigue funcionando con la sintaxis
de enums usada). Si lo usas en Qt5, repórtalo si algo no se ve/comporta
bien.

El workflow de CI/build (`build-release.yml`) solo compila el binario
standalone con Qt6 — Qt5 es soporte "úsalo en tu propio entorno", no
tiene binario precompilado.

### Verificación automática de dependencias

Al arrancar, la app comprueba las dependencias del sistema **antes** de
importar PySide6/PySide2/Pillow (`src/core/dependency_checker.py`):

- **Obligatorias** (Python ≥ 3.9, PySide6 *o* PySide2, Pillow): si falta
  alguna, la app no arranca y muestra por terminal el comando exacto para
  instalarla según tu distro (`apt`/`dnf`/`pacman`/`zypper`) o vía `pip`
  — y, si hay entorno gráfico pero no hay binding de Qt, también lo
  intenta mostrar en un diálogo (usando `tkinter` como respaldo).
- **Opcionales** (`cairosvg`, librerías Qt/XCB del sistema, `kpackagetool6`):
  si faltan, la app arranca igual pero avisa por terminal de la
  funcionalidad reducida (p. ej. sin `cairosvg` no se pueden rasterizar
  SVG a tamaños fijos; sin `kpackagetool6` no podrás instalar paquetes en
  Modo B).

## Ejecución

```bash
python -m src.main
```

o, tras instalar el paquete:

```bash
icon-packager-kde
```

### Ejecutable standalone (sin instalar Python ni dependencias)

Cada push a `main` y cada tag `vX.Y.Z` disparan el workflow
[`.github/workflows/build-release.yml`](.github/workflows/build-release.yml),
que compila un binario único con [PyInstaller](https://pyinstaller.org/)
(`icon-packager-kde`, Linux x86_64) que incluye su propio intérprete de
Python y todas las dependencias — no requiere que el usuario final tenga
Python, PySide6 ni Pillow instalados. El binario queda disponible como
artefacto de cada ejecución del workflow, y además se adjunta
automáticamente al [GitHub Release](../../releases) cuando se publica un
tag.

Para construirlo localmente (Qt6):

```bash
pip install ".[build,qt6]"   # instalación NO editable: PyInstaller
                              # necesita que "src" exista físicamente en
                              # site-packages
pyinstaller --onefile --name icon-packager-kde \
  "$(command -v icon-packager-kde)"
# binario resultante: dist/icon-packager-kde (~70 MB, autocontenido)
```

## Uso

1. **Añadir iconos**: arrastra archivos SVG/PNG al grid o usa "Añadir
   iconos…". Cada icono aparece con su preview, nombre editable y
   contexto.
2. **Configurar tamaños y contexto**: usa el panel lateral para aplicar
   tamaños/contexto a todos los iconos, o el botón "Configurar…" de cada
   fila para ajustarlo individualmente (incluye la opción "Escalable
   (SVG)").
3. **Completar la metadata**: nombre del tema, comentario, autor, versión
   y de qué tema hereda (`Inherits=`, por ejemplo `breeze`).
4. **(Opcional) Partir de un tema instalado**: junto al campo `Inherits`,
   el botón "Examinar iconos…" abre un buscador de los iconos del tema
   indicado (busca en `~/.local/share/icons`, `~/.icons` y las rutas del
   sistema — `/usr/share/icons`, `/usr/local/share/icons`, `XDG_DATA_DIRS` —
   ya que temas como Breeze u Oxygen casi siempre están instalados a nivel
   de sistema); permite filtrar por nombre/contexto y elegir cuáles importar al grid para
   modificarlos. No hace falta importar el tema completo: KDE ya resuelve
   en tiempo de ejecución, vía `Inherits=`, cualquier icono que no
   sobrescribas — esto es solo para clonar puntualmente los que sí quieres
   personalizar.
5. **Exportar**: botón "Exportar…" en la barra de herramientas. Elige el
   modo (A o B) y la ubicación de salida. La app valida que haya al menos
   un tamaño generado y un `index.theme` bien formado antes de exportar.

### Instalar un tema exportado en modo A

```bash
tar xzf mi-tema.tar.gz
cd mi-tema
./install.sh
```

### Instalar un tema exportado en modo B

```bash
kpackagetool6 -t Icons -i mi-tema-kpkg.tar.gz
```

## Arquitectura

```
src/
├── main.py                  # entry point, arranca QApplication
├── ui/                       # Qt (vía qt_compat): nunca toca el filesystem directamente
│   ├── qt_compat.py          # PySide6 con fallback a PySide2 + enums "planos"
│   ├── main_window.py
│   ├── icon_grid.py
│   ├── size_config_panel.py
│   ├── metadata_panel.py
│   ├── export_dialog.py
│   └── theme_import_dialog.py  # buscador de iconos de un tema instalado
├── core/                      # lógica desacoplada de la UI, testeable
│   ├── icon_manager.py
│   ├── theme_builder.py
│   ├── packager.py
│   ├── theme_catalog.py       # descubre temas instalados y cataloga sus iconos
│   └── dependency_checker.py  # verificación de dependencias del SO al arrancar
└── models/
    ├── icon_item.py
    └── theme_metadata.py
```

Flujo: `IconManager` (estado en memoria) → `ThemeBuilder` (genera la
estructura del tema + `index.theme` en un directorio temporal) →
`Packager` (empaqueta en modo A o B). `theme_catalog` es un camino
alternativo para poblar el `IconManager` a partir de iconos ya
existentes en un tema instalado, en vez de partir de cero.

## Tests

```bash
pytest
```

Los tests cubren `core/` (icon_manager, theme_builder, packager,
theme_catalog, dependency_checker) sin necesidad de levantar Qt.
