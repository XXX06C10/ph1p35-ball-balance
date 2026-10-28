param([ValidateSet('hold','cascade','easy','easy2','easy3','region_probe','region_return','asym_range','brake_hold','settle30','full_range','asym_smooth','region100','brake_fast','brake_precise','brake_precise2','brake_precise3','brake_precise4','brake_precise5','brake_precise6')][string]$Release='easy3',[string]$TdShell = 'D:/Anlogic/TD_6.2.1_Engineer_6.2.168.116/bin/td_commands_prompt.exe')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python record_contract.py
    if ($LASTEXITCODE -ne 0) { throw 'Baseline lineage changed' }
    python compose.py
    if ($LASTEXITCODE -ne 0) { throw 'Source composition failed' }
    python source_manifest.py --capture
    if ($LASTEXITCODE -ne 0) { throw 'Build source manifest failed' }
    if (-not (Test-Path -LiteralPath $TdShell)) { throw "TD command shell not found: $TdShell" }
    'source build.tcl' | & $TdShell *> build.log
    if ($LASTEXITCODE -ne 0) { throw 'TD failed; inspect build.log' }
    if (-not (Select-String -LiteralPath build.log -Pattern '^VISION_FOLLOW_20261022_BUILD_COMPLETE$' -Quiet)) {
        throw 'Build completion marker missing; inspect build.log (TD can exit 0 after a Tcl error)'
    }
    $bitPath = 'vision_follow_20261022_Runs/phy_1/vision_follow_20261022.bit'
    $bitHeader = Get-Content -LiteralPath $bitPath -TotalCount 8
    if ($bitHeader -notcontains '# Package: PH1P35MDG324') { throw 'Bitstream device mismatch' }
    python source_manifest.py --check
    if ($LASTEXITCODE -ne 0) { throw 'Sources changed during TD build; do not deliver this bit' }
    if (Select-String -LiteralPath build.log -Pattern 'Undriven net:.*(?:u_camera_control|u_vision_monitor|S_roi_|S_detect_rst)' -Quiet) {
        throw 'Integration has implicit re-declarations or undriven controls; do not deliver this bit'
    }
    foreach($line in (Get-Content -LiteralPath build.log | Where-Object {$_ -match 'CRITICAL-WARNING'})){
        # These camera/IP clock-routing notices also occur in the archived V1.
        $known=$line -match '^PHY-5060 CRITICAL-WARNING: Clock net candidate (u_uicfgcs500/uii2c_inst/scl_clk|O_cam_24m_syn_\d+) has mixed fanouts' -or
               $line -match '^PHY-5079 CRITICAL-WARNING: Marked \d+ clock net\(s\) utilize the local routing resources'
        if(!$known){throw "Unreviewed critical diagnostic; do not deliver this bit: $line"}
    }
    $timing=Get-Content -LiteralPath "vision_follow_20261022_Runs/phy_1/vision_follow_20261022_phy.ts" -Raw
    foreach($key in @('SWNS','STNS','HWNS','HTNS')){
        $match=[regex]::Match($timing,"$key`:\s*([-\d.]+)ns")
        if(!$match.Success -or [double]$match.Groups[1].Value -lt 0){throw "Routed timing failed: $key; do not deliver this bit"}
    }
    New-Item -ItemType Directory -Force -Path output | Out-Null
    Copy-Item -LiteralPath $bitPath -Destination output/vision_follow_20261022.bit -Force
    Copy-Item -LiteralPath $bitPath -Destination ("output/vision_follow_20261022_"+$Release+".bit") -Force
    Get-FileHash -LiteralPath output/vision_follow_20261022.bit -Algorithm SHA256 |
        Format-List | Out-File output/bitstream_sha256.txt -Encoding utf8
    Write-Output 'Build complete: output/vision_follow_20261022.bit (PH1P35MDG324)'
} finally { Pop-Location }
