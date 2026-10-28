param([Parameter(Mandatory=$true)][string]$Benches,[string]$Group='manual')
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
 foreach($bench in $Benches.Split(',')) {
  $ErrorActionPreference='Continue'
  & powershell -NoProfile -ExecutionPolicy Bypass -File ./run_sim.ps1 $bench *> ("sim/results/"+$bench+".asym_"+$Group+".log")
  $taskExit=$LASTEXITCODE;$ErrorActionPreference='Stop'
  if($taskExit -ne 0){Get-Content ("sim/results/"+$bench+".asym_"+$Group+".log") -Tail 16;throw "Failed $bench"}
  Write-Output "ASYM_GROUP_PASS $bench"
 }
} finally {Pop-Location}
