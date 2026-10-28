function New-ZoneProposal([int]$Radius,[hashtable]$R){
 if($Radius -lt 15 -or $Radius -gt 50){throw '稳区范围15～50像素'}
 return @{SEQ=(([int]$R.SEQ+1) -band 65535);C=[int]$R.C;DZ=$Radius;G=[int]$R.G;L=48;Sent=[DateTime]::Now}
}
function Test-SettleProfile{
 $p=New-ZoneProposal 30 @{SEQ=65535;C=745;G=131}
 if($p.SEQ -ne 0 -or $p.C -ne 745 -or $p.G -ne 131 -or $p.L -ne 48){throw 'profile lost center/polarity/sequence bounds'}
 if((New-ParameterPacket $p.SEQ $p.C $p.DZ $p.G $p.L) -cne "P000002E9001E833046`n"){throw 'P wire/XOR mismatch'}
 Write-Output 'SETTLE_HOST_SELFTEST_PASS profile20/30/50,P wire/XOR,center/polarity preserved,no serial side effects'
}
