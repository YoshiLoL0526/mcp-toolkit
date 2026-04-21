# mcp-toolkit

Servidor MCP de propósito general para agentes de IA.  
Construido con **Python 3.13**, **FastMCP** y **Playwright**.

## Herramientas disponibles

| Herramienta     | Descripción                                                       |
|-----------------|-------------------------------------------------------------------|
| `web_search`    | Busca en DuckDuckGo y extrae contenido web con Playwright         |
| `memory_set`    | Guarda un valor persistente en SQLite                             |
| `memory_get`    | Recupera un valor guardado                                        |
| `memory_delete` | Elimina una clave                                                 |
| `memory_list`   | Lista todas las claves (con filtro por prefijo opcional)          |
| `memory_clear`  | Borra toda la memoria (¡irreversible!)                            |
| `run_python`    | Ejecuta código Python en un sandbox con timeout                   |
| `run_js`        | Ejecuta código JavaScript con Node.js en un sandbox con timeout   |

---

## Instalación

### Requisitos previos

- [UV](https://docs.astral.sh/uv/getting-started/installation/) instalado
- Python 3.13 (UV lo descarga automáticamente si no está)
- Node.js (opcional, solo para `run_js`)

### Opción A — Instalar desde carpeta local

```bash
git clone https://github.com/YoshiLoL0526/mcp-toolkit
cd mcp-toolkit
uv tool install --python 3.13 .
```

### Opción B — Instalar directamente desde GitHub

```bash
uv tool install --python 3.13 git+https://github.com/YoshiLoL0526/mcp-toolkit
```

### Paso obligatorio: instalar Chromium para Playwright

Después de instalar el paquete, ejecuta este comando **una sola vez**:

```bash
# Obtener la ruta del entorno virtual creado por uv tool
uv tool run --from mcp-toolkit python -m playwright install chromium
```

O alternativamente, si sabes la ruta del entorno:

```bash
~/.local/share/uv/tools/mcp-toolkit/bin/python -m playwright install chromium
```

---

## Configuración en clientes MCP

### Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "mcp-toolkit": {
      "command": "mcp-toolkit"
    }
  }
}
```

> En Windows la ruta es `%APPDATA%\Claude\claude_desktop_config.json`

### Cursor / VS Code (`.cursor/mcp.json` o `.vscode/mcp.json`)

```json
{
  "servers": {
    "mcp-toolkit": {
      "type": "stdio",
      "command": "mcp-toolkit"
    }
  }
}
```

### Servidor HTTP (para acceso remoto o múltiples clientes)

```bash
mcp-toolkit --transport http --host 0.0.0.0 --port 8080
```

El servidor quedará escuchando en `http://<host>:<port>/mcp` usando el transporte **streamable-http** (estándar MCP actual). Puedes cambiar la ruta con `--path /otra-ruta`.

> El transporte `--transport sse` se mantiene por compatibilidad con clientes antiguos, pero está deprecado desde FastMCP 2.3.

---

## Uso de las herramientas

### `web_search`

```
Parámetros:
  query        (str)  — texto a buscar
  max_results  (int)  — resultados a devolver, default 5, máximo 10
  deep         (bool) — si True, extrae el contenido completo de cada página
  language     (str)  — idioma para las cabeceras HTTP, default "es-ES"
```

**Ejemplo (agente):**

```
Busca las últimas noticias sobre Python 3.13 con deep=True
```

### `memory_set` / `memory_get`

```
memory_set(key="usuario_nombre", value="Carlos")
memory_get(key="usuario_nombre")
memory_list(prefix="usuario_")
```

Los datos se guardan en `~/.local/share/mcp-toolkit/memory.db`.

### `run_python`

```
Parámetros:
  code     (str) — código Python a ejecutar
  timeout  (int) — segundos máximos, default 10, máximo 60
  stdin    (str) — entrada estándar opcional
```

**Restricciones de seguridad:**

- Sin acceso a red (proxy bloqueado por variables de entorno)
- Límite de memoria: 256 MB (Linux/macOS)
- Timeout estricto: el proceso se mata al agotarse el tiempo

### `run_js`

Mismos parámetros que `run_python`. Requiere Node.js instalado en el sistema.

---

## Desarrollo

```bash
git clone https://github.com/YoshiLoL0526/mcp-toolkit
cd mcp-toolkit
uv sync
uv run python -m playwright install chromium

# Ejecutar en modo desarrollo
uv run mcp-toolkit

# Tests
uv run pytest
```

### Añadir una nueva herramienta

1. Crear `mcp_toolkit/tools/mi_tool.py` con una función `async def mi_tool(...) -> str`
2. Importarla y registrarla en `server.py` con `mcp.tool()(mi_tool)`
3. Reinstalar: `uv tool install --python 3.13 . --reinstall`

---

## Estructura del proyecto

```
mcp-toolkit/
├── pyproject.toml
├── README.md
├── mcp_toolkit/
│   ├── server.py              # FastMCP app + registro
│   ├── tools/
│   │   ├── web_search.py      # Playwright: buscar + extraer
│   │   ├── memory.py          # SQLite KV store
│   │   ├── run_python.py      # Sandbox Python
│   │   └── run_js.py          # Sandbox Node.js
│   └── utils/
│       ├── browser.py         # Singleton Playwright
│       └── sandbox.py         # Helpers de subprocess y timeout
└── tests/
```

---

## Licencia

MIT
