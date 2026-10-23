# Herramientas de documentos

Utilidades pequeñas para dos trabajos que se repiten: **escribir un documento en Markdown y entregarlo
en Word y PDF** sin perder nada por el camino, y **transcribir grabaciones en local** y dejarlas
legibles.

Salen del pipeline que se montó para el Máster de IA Generativa (entregas del capstone BOND y apuntes
de las clases). Aquí están sin rutas fijas, con opciones y con pruebas.

## Documentos: de Markdown a Word y PDF

```
documento.md ──md_a_docx.js──► documento.docx ──docx_a_pdf.ps1──► documento.pdf
                                     │                                  │
                             comparar_docx_md.py                  revisar_pdf.py
                         (¿se ha perdido algo?)            (¿hay huecos, títulos sueltos,
                                                            figuras sin pie?)
```

| Herramienta | Qué hace |
|---|---|
| `documentos/md_a_docx.js` | Convierte el .md a .docx con estilo propio: títulos en color, tablas con cabecera, figuras centradas con su pie, pie de página numerado. Títulos `##` y `###` como Título 1 y 2 de Word, así que el PDF sale con marcadores |
| `documentos/comparar_docx_md.py` | Compara el texto del .docx con el del .md, bloque a bloque. Sirve para comprobar el conversor y para ver qué se cambió a mano en Word. Sale con código 1 si hay diferencias |
| `documentos/docx_a_pdf.ps1` | Exporta a PDF con Word, con marcadores a partir de los títulos |
| `documentos/revisar_pdf.py` | Cuenta páginas (y cuántas son de cuerpo, antes de los anexos), avisa de títulos al final de página, huecos grandes e imágenes sin su pie, y saca hojas de miniaturas |

### Instalar

```bash
npm install
pip install -r requirements.txt
```

`docx_a_pdf.ps1` necesita Microsoft Word.

### Usar

```bash
node documentos/md_a_docx.js informe.md informe.docx --pie "Mi informe" --salto-antes "Anexo A" --autor "Iker"
python documentos/comparar_docx_md.py informe.docx informe.md
powershell -ExecutionPolicy Bypass -File documentos/docx_a_pdf.ps1 informe.docx
python documentos/revisar_pdf.py informe.pdf miniaturas --anexos "Anexo A"
```

Opciones de `md_a_docx.js`:

| Opción | Para qué | Por defecto |
|---|---|---|
| `--pie TEXTO` | Texto del pie de página, delante del número | Solo "Página N" |
| `--salto-antes PREFIJO` | Salto de página antes de cada `##` que empiece por eso. Se puede repetir | Ninguno |
| `--color HEX` / `--color-subtitulo HEX` | Color de los títulos y de las cabeceras de tabla / de los `###` | `4F46E5` / `3730A3` (los de BOND) |
| `--autor NOMBRE` | Autor en las propiedades del documento | El título (`# ...`) |

**Qué Markdown entiende:** `#`, `##`, `###`, párrafos, viñetas y listas numeradas con un segundo nivel
(dos espacios), tablas, `**negrita**` (también con `` `código` `` dentro), `*cursiva*`, `` `código` ``,
bloques ```` ``` ````, enlaces `[texto](url)` y `<url>`, e imágenes `![pie](ruta)` con la ruta relativa
al .md. Un enlace a un fichero local se queda en texto.

**Trampas:**

- **Solo imágenes PNG y JPEG.** Una captura en WEBP (las que guardan muchos móviles y navegadores) hay
  que convertirla antes; el conversor lo dice con un error claro.
- **El pie de una figura tiene que empezar por "Captura" o "Figura"** para que `revisar_pdf.py` lo
  reconozca (configurable con `--pies`).
- **Una lista numerada que se corta con una tabla vuelve a empezar en 1.** Si una lista lleva una tabla
  en medio, pon la tabla después del último elemento.
- **Una imagen ocupa todo el ancho útil** si es más ancha de 600 px. Una captura de móvil, alta y con letra
  grande, puede llevarse una página entera: recórtala o redúcela antes.
- **Con el documento abierto en Word**, el conversor no puede escribir el .docx.

## Transcripción: de una grabación a un texto legible

| Herramienta | Qué hace |
|---|---|
| `transcripcion/transcribir.py` | Transcribe audio o vídeo con faster-whisper en CPU. Deja un `.txt` (una línea por segmento) y un `.srt` junto a cada fichero. Salta lo ya hecho, así que se puede cortar y relanzar |
| `transcripcion/legibles.py` | Monta un `.legible.md` con párrafos y títulos a partir del `.txt` y de los cortes que propone un LLM en un `.legible.json`. **El texto no lo toca el modelo**: sale siempre de las líneas originales, y se comprueba al final |
| `transcripcion/auditar_idioma.py` | Marca las transcripciones que han salido en otro idioma. Whisper con detección automática transcribió una vez un vídeo en inglés entero en galés |

### Instalar

faster-whisper y sus dependencias pesan; mejor en un entorno aparte:

```bash
python -m venv .venv-transcripcion
.venv-transcripcion/Scripts/pip install -r requirements-transcripcion.txt
```

La primera ejecución descarga el modelo (medium, unos 1,5 GB).

### Usar

```bash
python transcripcion/transcribir.py "Grabaciones" --idioma es --prompt "Clase sobre agentes de IA: RAG, MCP, A2A, embeddings."
python transcripcion/auditar_idioma.py "Grabaciones" --esperado es --ingles-si-contiene "inglés"
python transcripcion/legibles.py "Grabaciones"
```

- **`--prompt` da contexto y vocabulario** (siglas, nombres propios) y mejora mucho la transcripción
  técnica. Solo se usa con el idioma fijo: con `--idioma auto` sesgaría la detección.
- **Fija el idioma siempre que lo sepas.** La detección automática decide con los primeros segundos.
- El `.legible.json` lo escribe un LLM a partir del `.txt` numerado por líneas. Formato:
  `[{"s": 1, "e": 14, "t": "Título"}, ...]`, con líneas desde 1 e inclusivas.

## Pruebas

```bash
python -m unittest discover -s pruebas
```

Las de documentos convierten `pruebas/datos/ejemplo.md` (con un PNG y un JPEG) y comprueban que el Word
tiene el mismo texto; se saltan si no hay Node o falta `npm install`. Las de transcripción no necesitan
el modelo.
