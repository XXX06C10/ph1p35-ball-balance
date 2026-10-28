$script:AsymSchema=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../wide_diagnostic_schema.json') -Raw -Encoding UTF8|ConvertFrom-Json
function Convert-CascadeDiagnostic([string]$Line){
 $line=$Line.Trim();if($line -cnotmatch '^D2[0-9A-F]{144}$'){return $null}
 $xor=0;for($i=2;$i -lt $line.Length;$i+=2){$xor=$xor -bxor [Convert]::ToInt32($line.Substring($i,2),16)};if($xor -ne 0){return $null}
 $r=@{};$at=2
 foreach($f in $script:AsymSchema.fields){$n=[int]($f[1]/4);$v=[Convert]::ToInt64($line.Substring($at,$n),16);$at+=$n;if($f[0] -in $script:AsymSchema.signed -and $v -ge [Math]::Pow(2,$f[1]-1)){$v-=[long][Math]::Pow(2,$f[1])};$r[$f[0]]=$v}
 if($r.selection -gt 3){return $null};return $r
}
function Test-AsymProtocol{
 $r=Convert-Record $sample
 if(!$r -or $r.T -ne -5 -or $r.AT -ne -5){throw 'VIS6 signed32 T/AT error'}
 $a=$sample.Replace(' T=FFFFFFFB ',' T=0000016C ').Replace(' AT=FFFFFFFB ',' AT=FFFFFF4A ');$r=Convert-Record $a
 if($r.T -ne 364 -or $r.AT -ne -182 -or ($a.Length+2) -ne 441){throw 'VIS6 wide bounds/length error'}
 if((New-ParameterPacket 1 960 20 7 5) -cne "P000103C000140705D4`n"){throw 'P compatibility error'}
 if((New-CameraPacket 1 3600 143 0 0 1279 719) -cne "V00010E10008F0000000004FF02CFA6`n"){throw 'V compatibility error'}
 $fixture=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'asym_diag_fixture.txt') -Raw
 $d=Convert-CascadeDiagnostic $fixture
 if(!$d -or $d.neutral -ne 200 -or $d.work_min -ne -182 -or $d.work_max -ne 364 -or $d.limit_anchor -ne 0){throw 'D2 fixture range/neutral error'}
 if(Convert-CascadeDiagnostic ($fixture.Trim().Substring(0,144)+'FF')){throw 'D2 bad XOR accepted'}
 Write-Output 'ASYM_HOST_SELFTEST_PASS VIS6=441,D2=148,signed widths,PVS preserved'
}
