$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try{
 foreach($bench in @('tb_full','tb_detector','tb_camera','tb_motion','tb_center','tb_large','tb_follow','tb_plant','tb_loss','tb_response','tb_neutral','tb_hold','tb_outer','tb_fast','tb_cascade','tb_cascade_config','tb_cascade_plant','tb_easy','tb_easy_plant','tb_checkpoint','tb_replay')){
  $ErrorActionPreference='Continue'
  & powershell -NoProfile -ExecutionPolicy Bypass -File ./run_sim.ps1 -Testbench $bench *> ("sim/results/"+$bench+".runner.log")
  $taskExit=$LASTEXITCODE;$ErrorActionPreference='Stop'
  if($taskExit -ne 0){Get-Content -LiteralPath ("sim/results/"+$bench+".runner.log") -Tail 15;throw "Failed $bench"}
  Write-Output "REGRESSION_PASS $bench"
 }
}finally{Pop-Location}
