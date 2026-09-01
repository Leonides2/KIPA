# KDE Icon Package Assistant (KIPA)

Aplicación de escritorio (Python + PySide6) para crear, configurar y
empaquetar temas de iconos personalizados para KDE, siguiendo la
especificación [freedesktop Icon Theme](https://specifications.freedesktop.org/icon-theme-spec/icon-theme-spec-latest.html).

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

- Python 3.11+
- Linux/KDE (no es objetivo multiplataforma)

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Dependencias principales: `PySide6` (interfaz gráfica) y `Pillow`
(redimensionado de PNG). El rasterizado de SVG a tamaños fijos usa
opcionalmente `cairosvg` si está instalado; si no, sube también una
versión PNG del icono para generar tamaños fijos, o usa solo `scalable/`.

### Verificación automática de dependencias

Al arrancar, la app comprueba las dependencias del sistema **antes** de
importar PySide6/Pillow (`src/core/dependency_checker.py`):

- **Obligatorias** (Python ≥ 3.11, PySide6, Pillow): si falta alguna, la
  app no arranca y muestra por terminal el comando exacto para instalarla
  según tu distro (`apt`/`dnf`/`pacman`/`zypper`) o vía `pip` — y, si hay
  entorno gráfico pero no PySide6, también lo intenta mostrar en un
  diálogo (usando `tkinter` como respaldo).
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

Para construirlo localmente:

```bash
pip install ".[build]"   # instalación NO editable: PyInstaller necesita
                          # que "src" exista físicamente en site-packages
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
4. **Exportar**: botón "Exportar…" en la barra de herramientas. Elige el
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
├── ui/                       # PySide6: nunca toca el filesystem directamente
│   ├── main_window.py
│   ├── icon_grid.py
│   ├── size_config_panel.py
│   ├── metadata_panel.py
│   └── export_dialog.py
├── core/                      # lógica desacoplada de la UI, testeable
│   ├── icon_manager.py
│   ├── theme_builder.py
│   ├── packager.py
│   └── dependency_checker.py  # verificación de dependencias del SO al arrancar
└── models/
    ├── icon_item.py
    └── theme_metadata.py
```

Flujo: `IconManager` (estado en memoria) → `ThemeBuilder` (genera la
estructura del tema + `index.theme` en un directorio temporal) →
`Packager` (empaqueta en modo A o B).

## Tests

```bash
pytest
```

Los tests cubren `core/` (icon_manager, theme_builder, packager) sin
necesidad de levantar Qt.
