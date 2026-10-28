function Convert-ProbeEvent([string]$Line){
 $line=$Line.Trim();if($line -cnotmatch '^E1[0-9A-F]{54}$'){return $null}
 $xor=0;for($j=2;$j -lt $line.Length;$j+=2){$xor=$xor -bxor [Convert]::ToInt32($line.Substring($j,2),16)};if($xor -ne 0){return $null}
 $r=@{};$at=2
 foreach($f in @(@('sequence',2),@('time_ms',4),@('events',1),@('position',4),@('command_position',4),@('state',1),@('pending',1),@('commands',2),@('delta',2),@('diagnostic_flags',1),@('phase',1),@('status',1),@('selection',1),@('reason',1))){
  $bits=$f[1]*8;$v=[Convert]::ToInt64($line.Substring($at,$f[1]*2),16);$at+=$f[1]*2
  if($f[0] -in @('position','command_position','commands','delta') -and $v -ge [Math]::Pow(2,$bits-1)){$v-=[long][Math]::Pow(2,$bits)};$r[$f[0]]=$v
 };if($r.selection -gt 3 -or $r.phase -gt 11 -or $r.status -notin @(0,1,2,4)){return $null};return $r
}
function Test-ProbeProtocol{
 $zero='E1'+('00'*27);$e=Convert-ProbeEvent $zero
 if(!$e -or $e.position -ne 0 -or (Convert-ProbeEvent ($zero.Substring(0,54)+'01'))){throw 'E1长度或XOR自检失败'}
 Write-Output 'PROBE_PROTOCOL_PASS E58 XOR'
}
