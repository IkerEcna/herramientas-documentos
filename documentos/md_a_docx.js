// Convierte un .md a .docx con un estilo sobrio: títulos en color, tablas con cabecera de color, pie de
// página con número y figuras con su pie en cursiva.
//
// Uso:
//   node md_a_docx.js entrada.md salida.docx [--pie "Texto del pie"] [--color 4F46E5]
//                     [--color-subtitulo 3730A3] [--salto-antes "Anexo A"]... [--autor "Nombre"]
//
// Admite: # título, ## y ### (Título 1 y 2 de Word, con marcadores en el PDF), párrafos, viñetas y
// listas numeradas con un segundo nivel (dos espacios), tablas, **negrita** (con `código` dentro),
// *cursiva*, `código`, bloques ```, enlaces [texto](url) y <url>, e imágenes ![pie](ruta) en PNG o JPEG,
// con la ruta relativa al .md. Un enlace a un fichero local se queda en texto.
// --salto-antes inserta un salto de página antes de cada título ## que empiece por ese texto
// (se puede repetir). --autor va a las propiedades del documento; sin él se usa el título (# ...).
// Los colores por defecto son los de las entregas de BOND.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, LevelFormat, Footer, PageNumber, ImageRun, ExternalHyperlink,
  PageBreak,
} = require("docx");

// ---- argumentos ----
function leerArgumentos(argv) {
  const pos = [], opc = { pie: "", color: "4F46E5", colorSubtitulo: "3730A3", saltos: [], autor: "" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i], valor = () => {
      if (i + 1 >= argv.length) throw new Error(`Falta el valor de ${a}`);
      return argv[++i];
    };
    if (a === "--pie") opc.pie = valor();
    else if (a === "--color") opc.color = valor().replace(/^#/, "");
    else if (a === "--color-subtitulo") opc.colorSubtitulo = valor().replace(/^#/, "");
    else if (a === "--salto-antes") opc.saltos.push(valor());
    else if (a === "--autor") opc.autor = valor();
    else if (a.startsWith("--")) throw new Error(`Opción desconocida: ${a}`);
    else pos.push(a);
  }
  // compatibilidad con la versión anterior: el tercer argumento suelto es el pie
  if (pos.length === 3 && !opc.pie) opc.pie = pos.pop();
  if (pos.length !== 2) throw new Error("Uso: node md_a_docx.js entrada.md salida.docx [--pie TEXTO] [--color HEX] [--color-subtitulo HEX] [--salto-antes PREFIJO] [--autor NOMBRE]");
  return { entrada: pos[0], salida: pos[1], ...opc };
}

let ARGS;
try { ARGS = leerArgumentos(process.argv.slice(2)); } catch (e) { console.error(e.message); process.exit(2); }
const BASE = path.dirname(path.resolve(ARGS.entrada));
const BRAND = ARGS.color, GREY = "666666", ANCHO = 9026; // A4 con márgenes de 2,54 cm
const ANCHO_IMG = 600; // píxeles a 96 ppp: el ancho útil de la página

// ---- texto enriquecido: **negrita**, *cursiva*, `código`, [texto](url) y <url> ----
function rich(texto, base = {}) {
  const partes = texto.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|<https?:[^>]+>|\*[^*\s][^*]*\*)/).filter(Boolean);
  return partes.flatMap((t) => {
    let m;
    if (t.startsWith("**")) return rich(t.slice(2, -2), { ...base, bold: true }); // admite `código` dentro
    if (t.startsWith("`")) return new TextRun({ text: t.slice(1, -1), font: "Consolas", size: 19, ...base });
    if ((m = t.match(/^\[([^\]]+)\]\(([^)]+)\)$/))) {
      if (/^https?:/.test(m[2]))
        return new ExternalHyperlink({ link: m[2], children: [new TextRun({ text: m[1], style: "Hyperlink", ...base })] });
      return new TextRun({ text: m[1], ...base }); // enlace a un fichero local: solo el texto
    }
    if ((m = t.match(/^<(https?:[^>]+)>$/)))
      return new ExternalHyperlink({ link: m[1], children: [new TextRun({ text: m[1], style: "Hyperlink", ...base })] });
    if (/^\*[^*].*\*$/.test(t)) return new TextRun({ text: t.slice(1, -1), italics: true, ...base });
    return new TextRun({ text: t, ...base });
  });
}
const limpio = (t) => t.replace(/\*\*|`|\*/g, "").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

// ---- tablas ----
const bordes = {
  top: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
  bottom: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
  left: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
  right: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
  insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "DDDDDD" },
  insideVertical: { style: BorderStyle.SINGLE, size: 2, color: "DDDDDD" },
};
function anchos(filas) {
  const n = filas[0].length;
  const peso = Array.from({ length: n }, (_, c) =>
    Math.min(60, Math.max(5, ...filas.map((f) => limpio(f[c] || "").length))));
  const total = peso.reduce((a, b) => a + b, 0);
  const w = peso.map((p) => Math.max(800, Math.round((p / total) * ANCHO)));
  w[w.length - 1] += ANCHO - w.reduce((a, b) => a + b, 0);
  return w;
}
function tabla(filas) {
  const w = anchos(filas);
  const celda = (texto, i, cab) => new TableCell({
    width: { size: w[i], type: WidthType.DXA },
    margins: { top: 50, bottom: 50, left: 100, right: 100 },
    shading: cab ? { type: ShadingType.CLEAR, fill: BRAND, color: "auto" } : undefined,
    children: [new Paragraph({ children: rich(texto, cab ? { bold: true, color: "FFFFFF", size: 20 } : { size: 20 }) })],
  });
  return new Table({
    columnWidths: w, width: { size: ANCHO, type: WidthType.DXA }, borders: bordes,
    rows: filas.map((f, r) => new TableRow({ tableHeader: r === 0, children: f.map((t, i) => celda(t, i, r === 0)) })),
  });
}

// ---- imágenes: el tamaño sale de la cabecera del fichero ----
function tamanoImagen(datos, ruta) {
  if (datos.readUInt32BE(0) === 0x89504e47) // PNG: IHDR justo después de la firma
    return { tipo: "png", w: datos.readUInt32BE(16), h: datos.readUInt32BE(20) };
  if (datos[0] === 0xff && datos[1] === 0xd8) { // JPEG: buscar el marcador SOF
    let i = 2;
    while (i + 9 < datos.length) {
      if (datos[i] !== 0xff) { i++; continue; }
      const marca = datos[i + 1];
      if (marca >= 0xc0 && marca <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marca))
        return { tipo: "jpg", w: datos.readUInt16BE(i + 7), h: datos.readUInt16BE(i + 5) };
      i += 2 + datos.readUInt16BE(i + 2);
    }
  }
  throw new Error(`${ruta}: solo se admiten imágenes PNG o JPEG (una captura en WEBP, por ejemplo, hay que convertirla antes)`);
}
function imagen(ruta, pie) {
  const fichero = path.resolve(BASE, ruta);
  if (!fs.existsSync(fichero)) throw new Error(`No existe la imagen ${ruta} (se busca junto al .md, en ${fichero})`);
  const datos = fs.readFileSync(fichero);
  const { tipo, w, h } = tamanoImagen(datos, ruta);
  const ancho = Math.min(ANCHO_IMG, w), alto = Math.round((h / w) * ancho);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
                    children: [new ImageRun({ type: tipo, data: datos, transformation: { width: ancho, height: alto } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
                    children: [new TextRun({ text: pie, italics: true, color: GREY, size: 19 })] }),
  ];
}

// ---- parser del .md ----
const lineas = fs.readFileSync(ARGS.entrada, "utf-8").split(/\r?\n/);
const hijos = [];
let parrafo = [], lista = null, filas = [], codigo = null, nLista = 0;

function cerrar() {
  if (parrafo.length) {
    hijos.push(new Paragraph({ children: rich(parrafo.join(" ")), spacing: { after: 120, line: 276 } }));
    parrafo = [];
  }
  if (lista) {
    nLista += 1;
    for (const item of lista.items) {
      const numbering = lista.ref === "numeros"
        ? { reference: "numeros", level: item.nivel, instance: nLista }
        : { reference: "vinetas", level: item.nivel };
      hijos.push(new Paragraph({ children: rich(item.texto), numbering, spacing: { after: 60, line: 276 } }));
    }
    lista = null;
  }
  if (filas.length) {
    hijos.push(tabla(filas));
    hijos.push(new Paragraph({ text: "", spacing: { after: 80 } }));
    filas = [];
  }
}

try {
  for (const l of lineas) {
    let m;
    if (codigo) { // dentro de un bloque de código
      if (/^```/.test(l)) {
        hijos.push(...codigo.map((t, i) => new Paragraph({
          shading: { type: ShadingType.CLEAR, fill: "F3F4F6", color: "auto" },
          spacing: { before: i === 0 ? 80 : 0, after: i === codigo.length - 1 ? 160 : 0, line: 240 },
          children: [new TextRun({ text: t || " ", font: "Consolas", size: 16 })],
        })));
        codigo = null;
      } else codigo.push(l);
      continue;
    }
    if (/^```/.test(l)) { cerrar(); codigo = []; continue; }
    if (!l.trim()) { cerrar(); continue; }
    if ((m = l.match(/^# (.+)/))) {
      cerrar();
      hijos.push(new Paragraph({ children: [new TextRun({ text: m[1], bold: true, size: 34, color: BRAND })],
                                 spacing: { after: 160 } }));
    } else if ((m = l.match(/^## (.+)/))) {
      cerrar();
      if (ARGS.saltos.some((s) => m[1].startsWith(s))) hijos.push(new Paragraph({ children: [new PageBreak()] }));
      hijos.push(new Paragraph({ text: m[1], heading: HeadingLevel.HEADING_1 }));
    } else if ((m = l.match(/^### (.+)/))) {
      cerrar(); hijos.push(new Paragraph({ text: m[1], heading: HeadingLevel.HEADING_2 }));
    } else if ((m = l.match(/^!\[([^\]]*)\]\(([^)]+)\)/))) {
      cerrar(); hijos.push(...imagen(m[2], m[1]));
    } else if (l.startsWith("|")) {
      if (parrafo.length || lista) { const t = filas; filas = []; cerrar(); filas = t; }
      if (/^\|[\s|:-]+\|$/.test(l)) continue;
      filas.push(l.slice(1, -1).split("|").map((c) => c.trim()));
    } else if ((m = l.match(/^(\s*)- (.+)/))) {
      const nivel = m[1].length >= 2 ? 1 : 0;
      if (!lista || (nivel === 0 && lista.ref !== "vinetas")) { cerrar(); lista = { ref: "vinetas", items: [] }; }
      lista.items.push({ texto: m[2], nivel });
    } else if ((m = l.match(/^(\s*)\d+\. (.+)/))) {
      const nivel = m[1].length >= 2 ? 1 : 0;
      if (!lista || (nivel === 0 && lista.ref !== "numeros")) { cerrar(); lista = { ref: "numeros", items: [] }; }
      lista.items.push({ texto: m[2], nivel });
    } else if (lista && /^\s+\S/.test(l)) {
      lista.items[lista.items.length - 1].texto += " " + l.trim(); // continuación del elemento
    } else {
      parrafo.push(l.trim());
    }
  }
  cerrar();
} catch (e) {
  console.error("ERROR:", e.message);
  process.exit(1);
}

const nivelesVineta = [0, 1].map((n) => ({ level: n, format: LevelFormat.BULLET, text: n ? "◦" : "•",
  alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540 + n * 400, hanging: 270 } } } }));
const nivelesNumero = [0, 1].map((n) => ({ level: n, format: n ? LevelFormat.LOWER_LETTER : LevelFormat.DECIMAL,
  text: n ? "%2)" : "%1.", alignment: AlignmentType.LEFT,
  style: { paragraph: { indent: { left: 540 + n * 400, hanging: 360 } } } }));

const pie = ARGS.pie
  ? [new TextRun({ text: `${ARGS.pie} · página `, color: GREY, size: 18 }),
     new TextRun({ children: [PageNumber.CURRENT], color: GREY, size: 18 })]
  : [new TextRun({ children: ["Página ", PageNumber.CURRENT], color: GREY, size: 18 })];

const titulo = (lineas.find((l) => /^# /.test(l)) || "").replace(/^# /, "").trim();
const doc = new Document({
  creator: ARGS.autor || titulo || "md_a_docx",
  title: titulo || undefined,
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: BRAND }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 0, keepNext: true, keepLines: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: ARGS.colorSubtitulo }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 1, keepNext: true, keepLines: true } },
    ],
    characterStyles: [{ id: "Hyperlink", name: "Hyperlink", basedOn: "DefaultParagraphFont",
                        run: { color: "4338CA", underline: { type: "single" } } }],
  },
  numbering: { config: [
    { reference: "vinetas", levels: nivelesVineta },
    { reference: "numeros", levels: nivelesNumero },
  ] },
  sections: [{
    properties: {},
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: pie })] }) },
    children: hijos,
  }],
});

Packer.toBuffer(doc).then((b) => { fs.writeFileSync(ARGS.salida, b); console.log(`OK ${ARGS.salida} · ${b.length} bytes · ${hijos.length} bloques`); })
  .catch((e) => { console.error("ERROR:", e); process.exit(1); });
