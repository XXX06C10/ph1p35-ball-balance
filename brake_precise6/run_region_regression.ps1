param([string]$StartAt='tb_full')
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
 $started=$false
 foreach($bench in @('tb_full','tb_detector','tb_camera','tb_motion','tb_center','tb_large','tb_follow','tb_plant','tb_loss','tb_response','tb_neutral','tb_hold','tb_outer','tb_fast','tb_cascade','tb_cascade_config','tb_cascade_plant','tb_easy','tb_easy_plant','tb_checkpoint','tb_replay','tb_braking','tb_braking_plant','tb_region_probe','tb_probe_guards','tb_probe_events')) {
  if($bench -eq $StartAt){$started=$true};if(!$started){continue}
  & powershell -NoProfile -ExecutionPolicy Bypass -File ./run_sim.ps1 -Testbench $bench *> ("sim/results/"+$bench+".region_runner.log")
  if($LASTEXITCODE -ne 0){Get-Content ("sim/results/"+$bench+".region_runner.log") -Tail 18;throw "Failed $bench"}
  Write-Output "REGION_REGRESSION_PASS $bench"
 }
}finally{Pop-Location}
