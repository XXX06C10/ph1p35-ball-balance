param([string]$StartAt='tb_full')
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try{
 $taskStarted=$false
 foreach($bench in @('tb_full','tb_detector','tb_camera','tb_motion','tb_center','tb_large','tb_follow','tb_plant','tb_loss','tb_response','tb_neutral','tb_hold','tb_outer','tb_fast','tb_cascade','tb_cascade_config','tb_cascade_plant','tb_easy','tb_easy_plant','tb_checkpoint','tb_replay','tb_braking','tb_braking_plant','tb_region_policy','tb_tail_checkpoint','tb_region_return','tb_region_faults','tb_region_plant','tb_region_noise','tb_region_nonzero','tb_asym_limits','tb_asym_policy','tb_asym_edges','tb_asym_faults','tb_asym_range','tb_brake_hold','tb_settle_policy','tb_settle_runtime','tb_settle_plant')){
  if($bench -eq $StartAt){$taskStarted=$true};if(!$taskStarted){continue}
  $ErrorActionPreference='Continue'
  & powershell -NoProfile -ExecutionPolicy Bypass -File ./run_sim.ps1 -Testbench $bench *> ("sim/results/"+$bench+".runner.log")
  $taskExit=$LASTEXITCODE;$ErrorActionPreference='Stop'
  if($taskExit -ne 0){Get-Content -LiteralPath ("sim/results/"+$bench+".runner.log") -Tail 16;throw "Failed $bench"}
  Write-Output "SETTLE_REGRESSION_PASS $bench"
 }
}finally{Pop-Location}
