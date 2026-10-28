$script:PhysicalScale=Get-Content (Join-Path $PSScriptRoot 'physical_scale_precise4.json') -Raw | ConvertFrom-Json
$script:MmPerPixel=[double]$script:PhysicalScale.length_mm/($script:PhysicalScale.right.x-$script:PhysicalScale.left.x)
function Convert-XToMm([double]$X){return ($X-$script:PhysicalScale.left.x)*$script:MmPerPixel}
function Convert-ErrorToMm([double]$Pixels){return $Pixels*$script:MmPerPixel}
function Test-PhysicalScale {
 if([Math]::Abs((Convert-XToMm 262)) -gt 0.000001 -or [Math]::Abs((Convert-XToMm 1693)-125) -gt 0.000001 -or [Math]::Abs((Convert-XToMm 977.5)-62.5) -gt 0.000001 -or [Math]::Abs((Convert-ErrorToMm 35)-3.0573025856) -gt 0.000001 -or [Math]::Abs((Convert-ErrorToMm -70)+6.1146051712) -gt 0.000001){throw 'Physical scale regression'}
 Write-Output 'PHYSICAL_SCALE_PRECISE4_PASS endpoints0_125mm midpoint62_5mm signed_error'
}
