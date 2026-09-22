# Generates installer/app.ico: a small mark showing a fade towards the edges.
#
#   pwsh -NoProfile -File tools/make-icon.ps1
#
# Written as a script rather than committed as an opaque binary so the icon can
# be changed and regenerated instead of being hand-edited.

[CmdletBinding()]
param([string] $Out = 'installer\app.ico')

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$outPath = Join-Path $root $Out
New-Item -ItemType Directory -Force -Path (Split-Path $outPath -Parent) | Out-Null

Add-Type -AssemblyName System.Drawing

# OBS-ish dark background with a blue-to-transparent square: the filter's job.
function New-IconBitmap([int] $size) {
    $bitmap = New-Object System.Drawing.Bitmap($size, $size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)

    $graphics.Clear([System.Drawing.Color]::FromArgb(255, 28, 30, 34))

    # A square that fades out towards its own edges, drawn as concentric rings so
    # no alpha blending trickery is needed.
    $margin = [math]::Max(1, [int]($size * 0.14))
    $inner = $size - 2 * $margin
    $steps = [math]::Max(4, [int]($inner / 2))

    for ($i = $steps; $i -ge 1; $i--) {
        $fraction = $i / $steps
        $alpha = [int](255 * [math]::Pow($fraction, 1.6))
        $inset = [int]($margin + ($inner / 2) * (1 - $fraction))
        $rect = New-Object System.Drawing.Rectangle($inset, $inset, ($size - 2 * $inset), ($size - 2 * $inset))

        $color = [System.Drawing.Color]::FromArgb($alpha, 47, 150, 255)
        $brush = New-Object System.Drawing.SolidBrush($color)
        $graphics.FillRectangle($brush, $rect)
        $brush.Dispose()
    }

    $graphics.Dispose()
    return $bitmap
}

# An .ico file is a header plus PNG payloads for each size.
$sizes = @(16, 24, 32, 48, 64, 128, 256)
$images = @()
foreach ($size in $sizes) {
    $bitmap = New-IconBitmap $size
    $stream = New-Object System.IO.MemoryStream
    $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
    $images += , @{ Size = $size; Bytes = $stream.ToArray() }
    $stream.Dispose()
    $bitmap.Dispose()
}

$file = [System.IO.File]::Create($outPath)
$writer = New-Object System.IO.BinaryWriter($file)

$writer.Write([UInt16]0)                    # reserved
$writer.Write([UInt16]1)                    # type: icon
$writer.Write([UInt16]$images.Count)        # image count

$offset = 6 + 16 * $images.Count
foreach ($image in $images) {
    $dimension = if ($image.Size -ge 256) { 0 } else { $image.Size }
    $writer.Write([Byte]$dimension)          # width
    $writer.Write([Byte]$dimension)          # height
    $writer.Write([Byte]0)                   # palette colours
    $writer.Write([Byte]0)                   # reserved
    $writer.Write([UInt16]1)                 # colour planes
    $writer.Write([UInt16]32)                # bits per pixel
    $writer.Write([UInt32]$image.Bytes.Length)
    $writer.Write([UInt32]$offset)
    $offset += $image.Bytes.Length
}

foreach ($image in $images) { $writer.Write($image.Bytes) }

$writer.Flush()
$writer.Close()
$file.Close()

Write-Host "icon: $outPath ($((Get-Item $outPath).Length) bytes, $($images.Count) sizes)"
