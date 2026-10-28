$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
 @'
from pathlib import Path
import json
root=Path('.');before=Path(json.loads((root/'neutral_lineage.json').read_text(encoding='utf-8'))['archive'])/'project'
motion=(root/'sim/tb_neutral.v').read_text(encoding='utf-8').split('module neutral_arithmetic')[0]
top='\nmodule tb_neutral_before;wire done;neutral_motion #(.LEVEL(31)) test(done);initial begin wait(done);$finish;end initial begin #30000000;$fatal(1,"before fixture timeout");end endmodule\n'
(root/'sim/results/before_neutral.combined.v').write_text((before/'rtl/vision_monitor_all.v').read_text(encoding='utf-8')+'\n'+motion+top,encoding='utf-8')
'@ | python -
 if($LASTEXITCODE -ne 0){throw 'Before fixture generation failed'}
 $ivlBase=Join-Path (Split-Path (Split-Path (Get-Command iverilog).Source -Parent) -Parent) 'lib/ivl'
 $lines=@('root:tb_neutral_before',"basedir:$ivlBase",'generation:2012','generation:xtypes','generation:icarus-misc','out:sim/results/before_neutral.vvp','iwidth:32','widthcap:65536')
 foreach($name in @('system','v2005_math','v2009','va_math')){$lines+='module:'+(Join-Path $ivlBase ($name+'.vpi'))}
 [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'sim/results/before_neutral.config'),([string]::Join([Environment]::NewLine,$lines)+[Environment]::NewLine),(New-Object Text.UTF8Encoding($false)))
 & (Join-Path $ivlBase 'ivl.exe') -C sim/results/before_neutral.config -C (Join-Path $ivlBase 'vvp.conf') -- sim/results/before_neutral.combined.v
 if($LASTEXITCODE -ne 0){throw 'Before fixture did not compile; cannot claim reproduction'}
 & (Get-Command vvp).Source -i sim/results/before_neutral.vvp | Tee-Object -FilePath sim/results/before_neutral.log
 if($LASTEXITCODE -eq 0){throw 'Old response unexpectedly passed the neutral regression'}
 $text=Get-Content -LiteralPath sim/results/before_neutral.log -Raw
 if($text -notmatch 'K3 must record separate neutral.*LEVEL=31 T=\s*0 AT=\s*0 P=\s*31'){throw 'Old code failed for a different reason'}
 @'
from pathlib import Path
import json
Path('before_neutral_reproduction.json').write_text(json.dumps({'status':'EXPECTED_OLD_REFERENCE_FAILURE_REPRODUCED','old_target':0,'actual_level':31,'fixture':'actual monitor/real AB off-enable movement/re-enable, same neutral regression','log':'sim/results/before_neutral.log'},indent=2),encoding='utf-8')
'@ | python -
 Write-Output 'OLD_ZERO_REFERENCE_REPRODUCED: old T/AT0 at leveledP31; same regression passes new code'
}finally{Pop-Location}
