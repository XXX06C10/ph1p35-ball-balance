from pathlib import Path
r=Path(__file__).resolve().parent;p=r/'run_sim.ps1';s=p.read_text(encoding='utf-8-sig')
assert '$taskBenchMutex' not in s
s=s.replace('Push-Location $PSScriptRoot\ntry {', '''Push-Location $PSScriptRoot
$taskProjectId=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($PSScriptRoot)))).Replace('-','').Substring(0,16)
$taskBenchMutex=New-Object Threading.Mutex($false,('Local\\FpgaSim_'+$taskProjectId+'_'+$Testbench))
$taskComposeMutex=New-Object Threading.Mutex($false,('Local\\FpgaCompose_'+$taskProjectId))
$taskBenchOwned=$false;$taskComposeOwned=$false
try {
    while(!$taskBenchOwned){try{$taskBenchOwned=$taskBenchMutex.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$taskBenchOwned=$true}}
    while(!$taskComposeOwned){try{$taskComposeOwned=$taskComposeMutex.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$taskComposeOwned=$true}}
''',1)
s=s.replace('    # Reuse only completed PASS evidence', '''    $taskComposeMutex.ReleaseMutex();$taskComposeOwned=$false
    # Reuse only completed PASS evidence''',1)
s=s.replace('} finally { Pop-Location }', '''} finally {
    if($taskComposeOwned){$taskComposeMutex.ReleaseMutex()};$taskComposeMutex.Dispose()
    if($taskBenchOwned){$taskBenchMutex.ReleaseMutex()};$taskBenchMutex.Dispose()
    Pop-Location
}''')
p.write_text(s,encoding='utf-8-sig')
p=r/'run_easy3_regression.ps1';s=p.read_text(encoding='utf-8-sig')
s="param([string]$StartAt='tb_full')\n"+s
s=s.replace('try{\n foreach(', 'try{\n $taskStarted=$false\n foreach(',1)
s=s.replace("  $ErrorActionPreference='Continue'", "  if($bench -eq $StartAt){$taskStarted=$true};if(!$taskStarted){continue}\n  $ErrorActionPreference='Continue'",1)
p.write_text(s,encoding='utf-8-sig');print('SIM_MUTEX_AND_RESUME_READY')
