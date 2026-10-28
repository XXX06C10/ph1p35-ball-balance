param([ValidateSet('tb_full','tb_detector','tb_camera','tb_motion','tb_center','tb_large','tb_follow','tb_plant','tb_loss','tb_rgb','tb_response','tb_neutral','tb_hold','tb_cascade','tb_outer','tb_fast','tb_cascade_config','tb_cascade_plant','tb_easy','tb_easy_plant','tb_checkpoint','tb_replay','tb_replay_old','tb_braking','tb_braking_plant','tb_region_probe','tb_probe_guards','tb_probe_events','tb_region_policy','tb_tail_checkpoint','tb_region_return','tb_region_faults','tb_region_plant','tb_region_noise','tb_region_nonzero','tb_asym_limits','tb_asym_range','tb_asym_faults','tb_asym_edges','tb_asym_policy','tb_asym_plant','tb_brake_hold','tb_settle_policy','tb_settle_runtime','tb_settle_plant','tb_full_window_policy','tb_smooth_policy','tb_smooth_runtime','tb_smooth_plant','tb_overlay_lead','tb_overlay_rgb','tb_region100_policy','tb_region100_runtime','tb_region100_plant','tb_brake_fast_policy','tb_brake_fast_runtime','tb_brake_fast_plant','tb_checkpoint_finish','tb_brake_fast_clock50','tb_core_fallback','tb_reversal_recovery','tb_precise3_policy','tb_precise4_noise','tb_precise5_escape','tb_precise6_jitter')][string]$Testbench='tb_full',[switch]$Force)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
$taskProjectId=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($PSScriptRoot)))).Replace('-','').Substring(0,16)
$taskBenchMutex=New-Object Threading.Mutex($false,('Local\FpgaSim_'+$taskProjectId+'_'+$Testbench))
$taskComposeMutex=New-Object Threading.Mutex($false,('Local\FpgaCompose_'+$taskProjectId))
$taskBenchOwned=$false;$taskComposeOwned=$false
try {
    while(!$taskBenchOwned){try{$taskBenchOwned=$taskBenchMutex.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$taskBenchOwned=$true}}
    while(!$taskComposeOwned){try{$taskComposeOwned=$taskComposeMutex.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$taskComposeOwned=$true}}

    python compose.py
    if ($LASTEXITCODE -ne 0) { throw 'Source composition failed' }
    $iverilogPath = (Get-Command iverilog -ErrorAction Stop).Source
    $vvpPath = (Get-Command vvp -ErrorAction Stop).Source
    $ivlBase = Join-Path (Split-Path (Split-Path $iverilogPath -Parent) -Parent) 'lib/ivl'
    $ivlPath = Join-Path $ivlBase 'ivl.exe'
    if (-not (Test-Path -LiteralPath $ivlPath)) { throw "Icarus compiler engine missing: $ivlPath" }
    New-Item -ItemType Directory -Force -Path sim/results | Out-Null

    $inputs=@('rtl/vision_monitor_all.v', "sim/$Testbench.v")
    if($Testbench -eq 'tb_replay_old'){$inputs=@('sim/replay_old_all.v','sim/tb_replay.v','sim/tb_replay_old.v')}
    if($Testbench -eq 'tb_brake_fast_clock50'){$inputs+='sim/tb_brake_fast_plant.v'}
    if($Testbench -eq 'tb_smooth_policy'){$inputs+='sim/asym_golden_region.v'}
    if($Testbench -eq 'tb_overlay_rgb'){$inputs+='user_source/hdl_source/steel_ball_stream_bbox.v';$inputs+='user_source/hdl_source/steel_ball_detect.v';$inputs+='sim/steel_ball_detect_before_overlay_fix.v'}
    if($Testbench -eq 'tb_easy_plant'){$inputs+='sim/tb_cascade_plant.v'}
    if($Testbench -eq 'tb_braking_plant'){$inputs+='sim/tb_cascade_plant.v'}
    if($Testbench -in @('tb_detector','tb_rgb')){$inputs+='user_source/hdl_source/steel_ball_stream_bbox.v'}
    if($Testbench -eq 'tb_rgb'){$inputs+='user_source/hdl_source/steel_ball_detect.v'}
    if($Testbench -eq 'tb_camera'){
        foreach($source in @('uicfgcs500.v','uics500reg.v','uics500regAE.v','SC500GainTbl.v','uii2c.v')){
            $inputs+='user_source/hdl_source/uics500_cfg/'+$source
        }
    }
    $sourceParts = foreach ($sourcePath in $inputs) {
        $content=Get-Content -LiteralPath $sourcePath -Raw
        # TD accepts this reference implicit wire; declare it before use for Icarus.
        # No logic or register sequence changes in this simulation-only adapter.
        if($sourcePath -like '*/uicfgcs500.v'){$content=$content.Replace('wire ic_busy;', 'wire iic_busy;')}
        # This board uses the real RGB mask/overlay plus stream_bbox; the old
        # in-module CCL diagnostic engine has no connected outputs and TD trims
        # it. Exclude only that unobserved tail from the RGB simulation adapter.
        if($Testbench -in @('tb_rgb','tb_overlay_rgb') -and ($sourcePath -like '*/steel_ball_detect.v' -or $sourcePath -like '*/steel_ball_detect_before_overlay_fix.v')){
            $cut=$content.IndexOf('    // Synchronous BRAM FIFO')
            if($cut -lt 0){throw 'RGB adapter boundary not found'}
            $content=$content.Substring(0,$cut)+[Environment]::NewLine+'endmodule'+[Environment]::NewLine
        }
        '`line 1 "' + $sourcePath + '" 0' + [Environment]::NewLine + $content
    }
    if($Testbench -eq 'tb_region_noise'){$sourceParts+=('// noise SHA256 '+(Get-FileHash -LiteralPath sim/region_noise.mem -Algorithm SHA256).Hash)}
    $taskComposeMutex.ReleaseMutex();$taskComposeOwned=$false
    # Reuse only completed PASS evidence for the exact same complete inputs.
    # Partial/failing logs and stale executables never qualify; -Force reruns.
    $taskCombined=[string]::Join([Environment]::NewLine,$sourceParts)
    $taskSnapshot=Join-Path $PSScriptRoot "sim/results/$Testbench.combined.v"
    $taskLog=Join-Path $PSScriptRoot "sim/results/$Testbench.log"
    $taskExecutable=Join-Path $PSScriptRoot "sim/results/$Testbench.vvp"
    $taskMarkers=@{tb_precise6_jitter='PRECISE6_JITTER_PASS';tb_precise5_escape='PRECISE5_ESCAPE_PASS';tb_precise4_noise='PRECISE4_NOISE_PASS';tb_reversal_recovery='REVERSAL_RECOVERY_PASS';tb_precise3_policy='PRECISE3_POLICY_PASS';tb_core_fallback='CORE_FALLBACK_PASS';tb_brake_fast_clock50='BRAKE_FAST_CLOCK50_PASS';tb_brake_fast_policy='BRAKE_FAST_POLICY_PASS';tb_brake_fast_runtime='BRAKE_FAST_RUNTIME_PASS';tb_brake_fast_plant='BRAKE_FAST_PLANT_PASS';tb_checkpoint_finish='CHECKPOINT_FINISH_PASS';tb_region100_policy='REGION100_POLICY_PASS';tb_region100_runtime='REGION100_RUNTIME_PASS';tb_region100_plant='REGION100_PLANT_PASS';tb_smooth_policy='SMOOTH_POLICY_PASS';tb_smooth_runtime='SMOOTH_RUNTIME_PASS';tb_smooth_plant='SMOOTH_PLANT_PASS';tb_overlay_lead='OVERLAY_LEAD_PASS';tb_overlay_rgb='OVERLAY_RGB_PASS';tb_full_window_policy='FULL_WINDOW_POLICY_PASS';tb_settle_policy='SETTLE_POLICY_PASS';tb_settle_runtime='SETTLE_RUNTIME_PASS';tb_settle_plant='SETTLE_PLANT_PASS';tb_brake_hold='BRAKE_HOLD_PASS';tb_asym_plant='ASYM_PLANT_PASS';tb_asym_edges='ASYM_EDGES_PASS';tb_asym_policy='ASYM_POLICY_PASS';tb_asym_faults='ASYM_FAULTS_PASS';tb_asym_limits='ASYM_LIMITS_PASS';tb_asym_range='ASYM_RANGE_PASS';tb_region_nonzero='REGION_NONZERO_PASS';tb_region_noise='REGION_NOISE_PASS';tb_region_return='REGION_RETURN_PASS';tb_region_faults='REGION_FAULTS_PASS';tb_region_plant='REGION_PLANT_PASS';tb_region_policy='REGION_POLICY_PASS';tb_tail_checkpoint='TAIL_CHECKPOINT_PASS';tb_probe_events='PROBE_EVENTS_PASS';tb_probe_guards='PROBE_GUARDS_PASS';tb_region_probe='REGION_PROBE_ALL_PASS';tb_full='ALL_TESTS_PASS';tb_detector='DETECTOR_INTEGRATION_PASS';tb_camera='CAMERA_CONTROL_PASS';tb_motion='MOTION_GUARDS_PASS';tb_center='CENTER_CAPTURE_PASS';tb_large='LARGE_TARGET_PASS';tb_follow='FOLLOW_ALL_PASS';tb_plant='PLANT_ALL_PASS';tb_loss='LOSS_CONTROL_PASS';tb_response='RESPONSE_ALL_PASS';tb_neutral='NEUTRAL_ALL_PASS';tb_hold='HOLD_ALL_PASS';tb_outer='OUTER_ALL_PASS';tb_fast='FAST_ALL_PASS';tb_cascade='CASCADE_ALL_PASS';tb_cascade_config='CASCADE_CONFIG_PASS';tb_cascade_plant='CASCADE_PLANT_ALL_PASS';tb_easy='EASY_ALL_PASS';tb_easy_plant='EASY_PLANT_ALL_PASS';tb_checkpoint='CHECKPOINT_ALL_PASS';tb_replay='REPLAY_ALL_PASS';tb_braking='BRAKING_ALL_PASS';tb_braking_plant='BRAKING_PLANT_ALL_PASS';tb_rgb='RGB_INTEGRATION_PASS';tb_replay_old='REPLAY_OLD_ALL_PASS';}
    if(!$Force -and (Test-Path -LiteralPath $taskSnapshot) -and (Test-Path -LiteralPath $taskLog) -and (Test-Path -LiteralPath $taskExecutable)){
        $taskOldLog=Get-Content -LiteralPath $taskLog -Raw
        $taskFresh=(Get-Item -LiteralPath $taskLog).LastWriteTimeUtc -ge (Get-Item -LiteralPath $taskExecutable).LastWriteTimeUtc -and
                   (Get-Item -LiteralPath $taskExecutable).LastWriteTimeUtc -ge (Get-Item -LiteralPath $taskSnapshot).LastWriteTimeUtc
        if($taskFresh -and [IO.File]::ReadAllText($taskSnapshot) -ceq $taskCombined -and $taskOldLog.Contains($taskMarkers[$Testbench]) -and $taskOldLog -notmatch 'FATAL|FAIL:'){
            Write-Output "REUSE_VERIFIED_PASS $Testbench (identical full input snapshot and completed PASS)";return
        }
    }
    [System.IO.File]::WriteAllText(
        (Join-Path $PSScriptRoot "sim/results/$Testbench.combined.v"),
        $taskCombined,
        (New-Object System.Text.UTF8Encoding($false)))

    $configLines = @("root:$Testbench", "basedir:$ivlBase", 'generation:2012', 'generation:xtypes', 'generation:icarus-misc', "out:sim/results/$Testbench.vvp", 'iwidth:32', 'widthcap:65536')
    foreach ($moduleName in @('system', 'v2005_math', 'v2009', 'va_math')) {
        $configLines += 'module:' + (Join-Path $ivlBase "$moduleName.vpi")
    }
    [System.IO.File]::WriteAllText(
        (Join-Path $PSScriptRoot "sim/results/$Testbench.config"),
        ([string]::Join([Environment]::NewLine, $configLines) + [Environment]::NewLine),
        (New-Object System.Text.UTF8Encoding($false)))

    & $ivlPath -C "sim/results/$Testbench.config" -C (Join-Path $ivlBase 'vvp.conf') -- "sim/results/$Testbench.combined.v"
    if ($LASTEXITCODE -ne 0) { throw 'Compilation failed' }
    & $vvpPath -i "sim/results/$Testbench.vvp" | Tee-Object -FilePath "sim/results/$Testbench.log"
    if ($LASTEXITCODE -ne 0) { throw 'Simulation failed' }
} finally {
    if($taskComposeOwned){$taskComposeMutex.ReleaseMutex()};$taskComposeMutex.Dispose()
    if($taskBenchOwned){$taskBenchMutex.ReleaseMutex()};$taskBenchMutex.Dispose()
    Pop-Location
}
