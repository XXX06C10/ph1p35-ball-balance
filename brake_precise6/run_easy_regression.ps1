param([string]$StartAt='tb_full')
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
 $started=$false
 foreach($bench in @('tb_full','tb_detector','tb_camera','tb_motion','tb_center','tb_large','tb_follow','tb_plant','tb_loss','tb_rgb','tb_response','tb_neutral','tb_hold','tb_outer','tb_fast','tb_cascade','tb_cascade_config','tb_cascade_plant')){
  if($bench -eq $StartAt){$started=$true};if(!$started){continue}
  $ErrorActionPreference='Continue'
  & powershell -NoProfile -ExecutionPolicy Bypass -File ./run_sim.ps1 -Testbench $bench *> ("sim/results/"+$bench+".runner.log")
  $taskExitCode=$LASTEXITCODE;$ErrorActionPreference='Stop'
  if($taskExitCode -ne 0){Get-Content -LiteralPath ("sim/results/"+$bench+".runner.log") -Tail 14;throw "Regression failed: $bench"}
  Write-Output "REGRESSION_PASS $bench"
 }
}finally{Pop-Location}
