# -*- coding: utf-8 -*-
"""Pruebas de extremo a extremo de md_a_docx.js y comparar_docx_md.py: convierte el ejemplo y comprueba
que el Word tiene el mismo texto y las dos imágenes. Se saltan si no hay Node o no está instalado docx."""
import os
import shutil
import subprocess
import sys
import unittest
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "pruebas", "datos")
SALIDA = os.path.join(RAIZ, "pruebas", "salida")
NODE = shutil.which("node")
DOCX_INSTALADO = os.path.isdir(os.path.join(RAIZ, "node_modules", "docx"))


def convertir(md, docx, *opciones):
    return subprocess.run([NODE, os.path.join(RAIZ, "documentos", "md_a_docx.js"), md, docx, *opciones],
                          capture_output=True, text=True, encoding="utf-8", cwd=RAIZ)


@unittest.skipUnless(NODE and DOCX_INSTALADO, "hace falta Node y npm install")
class TestMdADocx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(SALIDA, exist_ok=True)

    def test_el_word_tiene_el_mismo_texto_que_el_md(self):
        docx = os.path.join(SALIDA, "ejemplo.docx")
        r = convertir(os.path.join(DATOS, "ejemplo.md"), docx, "--pie", "Prueba", "--salto-antes", "Anexo")
        self.assertEqual(r.returncode, 0, r.stderr)
        c = subprocess.run([sys.executable, os.path.join(RAIZ, "documentos", "comparar_docx_md.py"), docx,
                            os.path.join(DATOS, "ejemplo.md")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(c.returncode, 0, c.stdout)
        self.assertIn("dibujos en el cuerpo: 2", c.stdout)   # el PNG y el JPEG
        xml = zipfile.ZipFile(docx).read("word/document.xml").decode("utf-8")
        self.assertEqual(xml.count('w:type="page"'), 1)        # el salto antes del anexo
        pie = "".join(zipfile.ZipFile(docx).read(n).decode("utf-8")
                      for n in zipfile.ZipFile(docx).namelist() if n.startswith("word/footer"))
        self.assertIn("Prueba · página", pie)

    def test_el_autor_es_el_dado_o_el_titulo(self):
        docx = os.path.join(SALIDA, "autor.docx")
        self.assertEqual(convertir(os.path.join(DATOS, "ejemplo.md"), docx, "--autor", "Iker").returncode, 0)
        self.assertIn("<dc:creator>Iker</dc:creator>", zipfile.ZipFile(docx).read("docProps/core.xml").decode("utf-8"))
        self.assertEqual(convertir(os.path.join(DATOS, "ejemplo.md"), docx).returncode, 0)
        core = zipfile.ZipFile(docx).read("docProps/core.xml").decode("utf-8")
        self.assertIn("<dc:creator>Documento de ejemplo</dc:creator>", core)
        self.assertIn("<dc:title>Documento de ejemplo</dc:title>", core)

    def test_una_imagen_que_no_existe_da_un_error_claro(self):
        md = os.path.join(SALIDA, "falta.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("# T\n\n![Figura](no_existe.png)\n")
        r = convertir(md, os.path.join(SALIDA, "falta.docx"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No existe la imagen no_existe.png", r.stderr)

    def test_una_imagen_webp_da_un_error_claro(self):
        webp = os.path.join(SALIDA, "captura.webp")
        with open(webp, "wb") as f:
            f.write(b"RIFF\x00\x00\x00\x00WEBPVP8 ")
        md = os.path.join(SALIDA, "webp.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("![Captura](captura.webp)\n")
        r = convertir(md, os.path.join(SALIDA, "webp.docx"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("solo se admiten imágenes PNG o JPEG", r.stderr)

    def test_una_opcion_desconocida_falla_sin_escribir_nada(self):
        r = convertir(os.path.join(DATOS, "ejemplo.md"), os.path.join(SALIDA, "x.docx"), "--colr", "FF0000")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Opción desconocida: --colr", r.stderr)


if __name__ == "__main__":
    unittest.main()
