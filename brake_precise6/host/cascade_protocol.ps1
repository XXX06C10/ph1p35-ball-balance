# Pure protocol helpers; no serial access or movement on import.
$script:CascadeFields=@(@('version',1),@('sequence',2),@('selection',1),@('diagnostics',1),@('kp',2),@('kv',2),@('ki',2),@('bias',2),@('inner_kp',2),@('feedforward',2),@('max_hz',2),@('delay_ms',1),@('amplitude',1),@('slew_rate',2),@('polarity',1),@('reserved',1))
function New-CascadeDefault{
 return @{version=1;sequence=0;selection=0;diagnostics=1;kp=512;kv=128;ki=0;bias=0;inner_kp=8192;feedforward=200;max_hz=50;delay_ms=0;amplitude=4;slew_rate=256;polarity=0;reserved=0}
}
function New-CascadePacket($P){
 foreach($k in @('version','sequence','selection','diagnostics','kp','kv','ki','bias','inner_kp','feedforward','max_hz','delay_ms','amplitude','slew_rate','polarity','reserved')){if($null -eq $P[$k]){throw ('缺少串级参数 '+$k)}}
 if($P.version -ne 1 -or $P.sequence -lt 0 -or $P.sequence -gt 65535 -or $P.selection -lt 0 -or $P.selection -gt 3 -or $P.diagnostics -notin @(0,1)){throw '串级版本/序号/模式错误'}
 if($P.kp -lt 0 -or $P.kp -gt 16384 -or $P.kv -lt 0 -or $P.kv -gt 2048 -or $P.ki -lt 0 -or $P.ki -gt 3277 -or $P.bias -lt -2048 -or $P.bias -gt 2048){throw '外环系数越界'}
 if($P.inner_kp -lt 256 -or $P.inner_kp -gt 32768 -or $P.feedforward -lt 0 -or $P.feedforward -gt 256 -or $P.max_hz -notin @(50,100,200)){throw '内环参数越界'}
 if($P.delay_ms -lt 0 -or $P.delay_ms -gt 120 -or $P.amplitude -notin @(4,8,16) -or ($P.selection -eq 3 -and $P.amplitude -eq 16) -or $P.slew_rate -lt 8 -or $P.slew_rate -gt 256 -or $P.polarity -notin @(0,1) -or $P.reserved -ne 0){throw '延迟/标定幅度/方向参数越界'}
 $body='';$xor=0
 foreach($field in $script:CascadeFields){$n=$field[1];$v=[long]$P[$field[0]];$mask=if($n -eq 1){255}else{65535};$v=$v -band $mask;$body+=($v.ToString('X'+($n*2)));for($j=0;$j -lt $n;$j++){$xor=$xor -bxor (($v -shr ($j*8)) -band 255)}}
 return 'C'+$body+('{0:X2}' -f $xor)+"`n"
}
$script:CascadeSchema=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../diagnostic_schema.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function Convert-CascadeDiagnostic([string]$Line){
 $line=$Line.Trim();if($line.Length -ne 92 -or $line -cnotmatch '^D1[0-9A-F]{90}$'){return $null}
 $xor=0;for($j=2;$j -lt $line.Length;$j+=2){$xor=$xor -bxor [Convert]::ToInt32($line.Substring($j,2),16)};if($xor -ne 0){return $null}
 $r=@{};$at=2
 foreach($field in $script:CascadeSchema.fields){$name=$field[0];$bits=[int]$field[1];$n=[int]($bits/4);$v=[Convert]::ToInt64($line.Substring($at,$n),16);$at+=$n
  if($name -in $script:CascadeSchema.signed -and $v -ge [Math]::Pow(2,$bits-1)){$v-=[long][Math]::Pow(2,$bits)};$r[$name]=$v
 };if($r.selection -gt 3){return $null};return $r
}
function Test-CascadeProtocol{
 $p=New-CascadeDefault;$p.sequence=1;$p.selection=2;$p.amplitude=8
 $packet=New-CascadePacket $p;if($packet.Length -ne 54){throw 'C54长度错误'}
 $vectors=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'cascade_vectors.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 foreach($v in $vectors.commands){$p=@{};$v.parameters.psobject.Properties|ForEach-Object{$p[$_.Name]=[int]$_.Value};if((New-CascadePacket $p) -cne $v.packet){throw 'C与Python/FPGA协议不一致'}}
 foreach($v in $vectors.diagnostics){$r=Convert-CascadeDiagnostic $v.line;if(!$r -or $r.position -ne $v.position -or $r.velocity_q4 -ne $v.velocity_q4){throw 'D1真实串口解码错误'}}
 if(Convert-CascadeDiagnostic ('D1'+('0'*90)+'X')){throw 'D1截断/多字节未拒绝'}
 $bad=New-CascadeDefault;$bad.max_hz=201;$rejected=$false;try{New-CascadePacket $bad|Out-Null}catch{$rejected=$true};if(!$rejected){throw 'C边界未拒绝'}
 Write-Output 'CASCADE_HOST_PROTOCOL_PASS C54/D94 XOR,signed,real UART fixtures'
}
