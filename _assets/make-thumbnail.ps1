Add-Type -AssemblyName System.Drawing
# ASCII ONLY (UTF-8 punctuation here is read back as ANSI -> mojibake).
# PowerShell variables are case-INSENSITIVE: never $W and $w in one script.

$CanvasW = 1200; $CanvasH = 800   # 3:2, confirmed on the Devpost page
$TF = New-Object System.Drawing.StringFormat([System.Drawing.StringFormat]::GenericTypographic)
# GenericTypographic drops glyph padding (good) but measures a space as ZERO width,
# which silently welds words together in any per-character tracking loop.
$TF.FormatFlags = $TF.FormatFlags -bor [System.Drawing.StringFormatFlags]::MeasureTrailingSpaces

$bmp = New-Object System.Drawing.Bitmap($CanvasW, $CanvasH)
$g   = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'; $g.TextRenderingHint = 'ClearTypeGridFit'

# 1. Base gradient
$full = New-Object System.Drawing.Rectangle(0,0,$CanvasW,$CanvasH)
$g.FillRectangle((New-Object System.Drawing.Drawing2D.LinearGradientBrush(
    $full,
    [System.Drawing.Color]::FromArgb(255,8,10,15),
    [System.Drawing.Color]::FromArgb(255,27,31,44), 55)), $full)

# 2. Heat glow, low-left. Depth without ornament.
$gp = New-Object System.Drawing.Drawing2D.GraphicsPath
$gp.AddEllipse(-280, 190, 1240, 940)
$glow = New-Object System.Drawing.Drawing2D.PathGradientBrush($gp)
$glow.CenterColor    = [System.Drawing.Color]::FromArgb(78,255,124,32)
$glow.SurroundColors = @([System.Drawing.Color]::FromArgb(0,255,124,32))
$glow.CenterPoint    = New-Object System.Drawing.PointF(230, 660)
$g.FillPath($glow, $gp)

# 3. Vignette
$vp = New-Object System.Drawing.Drawing2D.GraphicsPath
$vp.AddEllipse(-400,-300,2000,1400)
$vig = New-Object System.Drawing.Drawing2D.PathGradientBrush($vp)
$vig.CenterColor    = [System.Drawing.Color]::FromArgb(0,0,0,0)
$vig.SurroundColors = @([System.Drawing.Color]::FromArgb(196,0,0,0))
$g.FillPath($vig, $vp)

# 4. Scanlines, near-threshold alpha. Material, not pattern.
$scan = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(9,255,255,255))
for ($y=0; $y -lt $CanvasH; $y+=4) { $g.FillRectangle($scan,0,$y,$CanvasW,1) }

$left = 156.0
$black = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,0,0,0))

# 5. Wordmark: hard offset shadow, then ink. Brutalist weight.
$fMark = New-Object System.Drawing.Font('Franklin Gothic Heavy',112,[System.Drawing.FontStyle]::Bold,'Pixel')
$ink   = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,247,249,253))
$yMark = 250.0
foreach ($p in @(@{b=$black;d=7},@{b=$ink;d=0})) {
    $x = $left + $p.d
    foreach ($ch in 'CRUCIBLE'.ToCharArray()) {
        $g.DrawString([string]$ch,$fMark,$p.b,$x,$yMark+$p.d,$TF)
        $x += $g.MeasureString([string]$ch,$fMark,[System.Drawing.PointF]::new(0,0),$TF).Width + 4
    }
}
$markBottom = $yMark + $g.MeasureString('CRUCIBLE',$fMark,[System.Drawing.PointF]::new(0,0),$TF).Height

# 6. Subhead. Demi-condensed bold survives the 3.5x downscale to a gallery card.
$fSub = New-Object System.Drawing.Font('Franklin Gothic Demi Cond',52,[System.Drawing.FontStyle]::Regular,'Pixel')
$subInk = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,224,231,242))
$ySub = $markBottom + 24
$sub  = 'A pen test that writes itself.'
$g.DrawString($sub,$fSub,$black,$left+3,$ySub+3,$TF)   # faint drop so it lifts off the glow
$g.DrawString($sub,$fSub,$subInk,$left,$ySub,$TF)
$subH = $g.MeasureString($sub,$fSub,[System.Drawing.PointF]::new(0,0),$TF).Height

# 7. Rule + footer. Both brightened; the footer was the element that died on the card.
$yRule = $ySub + $subH + 50
$g.DrawLine((New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255,86,62,50),3)),$left,$yRule,1060,$yRule)

$fFoot = New-Object System.Drawing.Font('Consolas',31,[System.Drawing.FontStyle]::Bold,'Pixel')
$footInk = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255,226,196,166))
$x = $left
foreach ($ch in 'ADK / VERTEX AI / CLOUD RUN / FIRESTORE'.ToCharArray()) {
    $g.DrawString([string]$ch,$fFoot,$footInk,$x,$yRule+24,$TF)
    $x += $g.MeasureString([string]$ch,$fFoot,[System.Drawing.PointF]::new(0,0),$TF).Width + 3
}
$footBottom = $yRule + 24 + $g.MeasureString('A',$fFoot,[System.Drawing.PointF]::new(0,0),$TF).Height

# 8. Accent slab LAST, spanning the measured text block rather than a hardcoded guess.
$slabTop = [int]($yMark + 14)
$slabH   = [int]($footBottom - $slabTop)
$slabRect = New-Object System.Drawing.Rectangle(96,$slabTop,14,$slabH)
$g.FillRectangle((New-Object System.Drawing.Drawing2D.LinearGradientBrush(
    $slabRect,
    [System.Drawing.Color]::FromArgb(255,255,150,36),
    [System.Drawing.Color]::FromArgb(255,196,26,26), 90)), $slabRect)

$out = 'C:\dev\crucible\_assets\crucible-thumbnail.png'
$bmp.Save($out,[System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

$img = [System.Drawing.Image]::FromFile($out)
'{0}  {1}x{2}  ratio {3:N3}  {4:N0} bytes' -f $out,$img.Width,$img.Height,($img.Width/$img.Height),(Get-Item $out).Length
$img.Dispose()
