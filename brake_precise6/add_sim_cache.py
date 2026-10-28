"""Reuse a completed PASS only for byte-identical full simulator input snapshots."""
from pathlib import Path
import ast,re
r=Path(__file__).resolve().parent;p=r/'run_sim.ps1';s=p.read_text(encoding='utf-8-sig')
assert 'REUSE_VERIFIED_PASS' not in s
v=(r/'verify.py').read_text(encoding='utf-8-sig');markers=ast.literal_eval(re.search(r'benches=(\{[\s\S]*?\})\nfor bench',v)[1]);markers.update(tb_rgb='RGB_INTEGRATION_PASS',tb_replay_old='REPLAY_OLD_ALL_PASS')
psmap='@{'+''.join(f"{k}='{value}';" for k,value in markers.items())+'}'
s=s.replace("$Testbench='tb_full')","$Testbench='tb_full',[switch]$Force)",1)
block='''    # Reuse only completed PASS evidence for the exact same complete inputs.
    # Partial/failing logs and stale executables never qualify; -Force reruns.
    $taskCombined=[string]::Join([Environment]::NewLine,$sourceParts)
    $taskSnapshot=Join-Path $PSScriptRoot "sim/results/$Testbench.combined.v"
    $taskLog=Join-Path $PSScriptRoot "sim/results/$Testbench.log"
    $taskExecutable=Join-Path $PSScriptRoot "sim/results/$Testbench.vvp"
    $taskMarkers=MARKERS
    if(!$Force -and (Test-Path -LiteralPath $taskSnapshot) -and (Test-Path -LiteralPath $taskLog) -and (Test-Path -LiteralPath $taskExecutable)){
        $taskOldLog=Get-Content -LiteralPath $taskLog -Raw
        $taskFresh=(Get-Item -LiteralPath $taskLog).LastWriteTimeUtc -ge (Get-Item -LiteralPath $taskExecutable).LastWriteTimeUtc -and
                   (Get-Item -LiteralPath $taskExecutable).LastWriteTimeUtc -ge (Get-Item -LiteralPath $taskSnapshot).LastWriteTimeUtc
        if($taskFresh -and [IO.File]::ReadAllText($taskSnapshot) -ceq $taskCombined -and $taskOldLog.Contains($taskMarkers[$Testbench]) -and $taskOldLog -notmatch 'FATAL|FAIL:'){
            Write-Output "REUSE_VERIFIED_PASS $Testbench (identical full input snapshot and completed PASS)";return
        }
    }
'''.replace('MARKERS',psmap)
anchor='    [System.IO.File]::WriteAllText('
s=s.replace(anchor,block+anchor,1).replace('[string]::Join([Environment]::NewLine, $sourceParts)','$taskCombined',1)
p.write_text(s,encoding='utf-8-sig');print('SIM_EXACT_INPUT_CACHE_READY')
