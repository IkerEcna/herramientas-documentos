# Exporta un .docx a PDF con Microsoft Word (sin abrirlo en pantalla), con marcadores a partir de los
# títulos, que es lo que lee revisar_pdf.py.
#
#   powershell -ExecutionPolicy Bypass -File docx_a_pdf.ps1 documento.docx [documento.pdf]
#
# Necesita Word instalado. Si no se da la salida, deja el PDF junto al .docx.
param(
    [Parameter(Mandatory = $true)][string]$Docx,
    [string]$Pdf
)
$ErrorActionPreference = 'Stop'
$Docx = (Resolve-Path $Docx).Path
if (-not $Pdf) { $Pdf = [IO.Path]::ChangeExtension($Docx, '.pdf') }
$Pdf = [IO.Path]::GetFullPath($Pdf)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($Docx, $false, $true)   # sin conversión, solo lectura
    # ExportAsFixedFormat: 17 = PDF, 0 = calidad de impresión, todo el documento, sin marcas de revisión;
    # CreateBookmarks = 1: marcadores a partir de los títulos
    $doc.ExportAsFixedFormat($Pdf, 17, $false, 0, 0, 0, 0, 0, $true, $true, 1, $true, $true, $false)
    $doc.Close($false)
    Write-Output "OK $Pdf"
} finally {
    $word.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
