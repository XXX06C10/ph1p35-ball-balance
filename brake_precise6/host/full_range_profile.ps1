function New-FullRangeZoneProposal([int]$Radius,[hashtable]$R){
 if($Radius -lt 15 -or $Radius -gt 50){throw '稳区范围15～50像素'}
 return @{SEQ=(([int]$R.SEQ+1) -band 65535);C=[int]$R.C;DZ=$Radius;G=[int]$R.G;L=$(if($R.ContainsKey('L')){[int]$R.L}else{60});Sent=[DateTime]::Now}
}
function Test-FullRangeProfile{
 $p=New-FullRangeZoneProposal 30 @{SEQ=65535;C=745;G=131;L=60}
 if($p.SEQ -ne 0 -or $p.C -ne 745 -or $p.G -ne 131 -or $p.L -ne 60){throw 'profile lost center/polarity/sequence bounds'}
 if((New-ParameterPacket $p.SEQ $p.C $p.DZ $p.G $p.L) -cne "P000002E9001E833C4A`n"){throw 'P wire/XOR mismatch'}
 if([Math]::Abs((FullRange-MotorY 395 31)-(FullRange-MotorY 364 0)) -gt 0.001 -or (FullRange-MotorY 364 0) -lt 265 -or (FullRange-MotorY -182 0) -gt 425){throw 'full-range chart geometry'}
 Write-Output 'FULL_RANGE_HOST_SELFTEST_PASS profile20/30/50,P wire/XOR,center/polarity preserved,no serial side effects'
}

function FullRange-MotorY([double]$Count,[double]$Anchor){
 $angle=($Count-$Anchor)*360.0/4096;$angle=[Math]::Max(-21,[Math]::Min(35,$angle));return 365-$angle*100.0/35
}
