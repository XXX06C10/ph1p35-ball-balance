$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try{
 foreach($bench in (Get-Content ./brake_precise4_required_suites.json -Raw|ConvertFrom-Json)){
  $ErrorActionPreference='Continue'
  & powershell -NoProfile -ExecutionPolicy Bypass -File ./run_sim.ps1 -Testbench $bench *> ("sim/results/"+$bench+".brake_fast_runner.log")
  $benchExit=$LASTEXITCODE;$ErrorActionPreference='Stop'
  if($benchExit -ne 0){Get-Content ("sim/results/"+$bench+".brake_fast_runner.log") -Tail 12;throw "Failed $bench"}
  Write-Output "BRAKE_FAST_REGRESSION_PASS $bench"
 }
}finally{Pop-Location}
