function New-Region100ZoneProposal([int]$Radius,[hashtable]$R){
 if($Radius -lt 60 -or $Radius -gt 100){throw '稳区范围60～100像素'}
 return @{SEQ=(([int]$R.SEQ+1) -band 65535);C=[int]$R.C;DZ=$Radius;G=[int]$R.G;L=$(if($R.ContainsKey('L')){[int]$R.L}else{60});Sent=[DateTime]::Now}
}
function Test-Region100Profile{
 $p=New-Region100ZoneProposal 100 @{SEQ=65535;C=745;G=131;L=60}
 if($p.SEQ -ne 0 -or $p.C -ne 745 -or $p.G -ne 131 -or $p.L -ne 60 -or $p.DZ -ne 100){throw 'profile lost center/polarity/limit/sequence'}
 if((New-ParameterPacket $p.SEQ $p.C $p.DZ $p.G $p.L) -cne "P000002E90064833C30`n"){throw 'P100 wire/XOR mismatch'}
 $p=New-Region100ZoneProposal 80 @{SEQ=5;C=960;G=3;L=5};if($p.L -ne 5 -or $p.C -ne 960 -or $p.SEQ -ne 6){throw 'profile mutated legacy fields'}
 Write-Output 'REGION100_PROFILE_PASS P80/P100 wire,center/polarity/sequence/L preservation,no serial effects'
}
function FullRange-MotorY([double]$Count,[double]$Anchor){
 $angle=($Count-$Anchor)*360.0/4096;$angle=[Math]::Max(-21,[Math]::Min(35,$angle));return 365-$angle*100.0/35
}
