# Invoked after the existing camera/control widgets are built. No serial side effects.
$cascadeTab=New-Object Windows.Forms.TabPage('标定工具');$cascadeTab.AutoScroll=$true;[void]$leftTabs.TabPages.Add($cascadeTab);$leftTabs.SelectedIndex=0
function Cascade-Label([string]$Text,[int]$Y,[int]$H=40){$v=New-Object Windows.Forms.Label;$v.Text=$Text;$v.SetBounds(10,$Y,302,$H);$cascadeTab.Controls.Add($v);return $v}
function Cascade-Button([string]$Text,[int]$Y){$v=New-Object Windows.Forms.Button;$v.Text=$Text;$v.SetBounds(10,$Y,302,34);$cascadeTab.Controls.Add($v);return $v}
Cascade-Label '日常只用板上按键：K1使能、K3定中心、K2持续回中。下列工具仅供进阶标定，不需要逐项操作。' 12 78 | Out-Null
$cal50=Cascade-Button '① 电机标定：50Hz / ±8计数' 98
$cal100=Cascade-Button '② 通过后：100Hz / ±16计数' 140
$cal200=Cascade-Button '③ 通过后：200Hz / ±16计数' 182
Cascade-Label '电机标定可先移开球；不手动碰轴。球响应标定时重新放球，保持同一水平/中心。' 224 58 | Out-Null
$calBall4=Cascade-Button '④ 球响应：±4计数，正反各三次' 286
$calBall8=Cascade-Button '信号不足时：改用±8计数球标定' 328
$fitCascade=Cascade-Button '⑤ 分析当前日志，自动计算参数' 370
$loadCascade=Cascade-Button '加载已有标定参数文件' 412
$applyCascade=Cascade-Button '⑥ 应用合格参数，等待K2启动' 454;$applyCascade.Enabled=$false
$legacyCascade=Cascade-Button '切回旧控制（设置后仍需K2）' 496
$cascadeAck=Cascade-Label 'easy3.bit已内置回中参数，无需标定即可K3后K2。自定义参数仍可用；故障停步保持。' 540 66
$cascadeDetails=Cascade-Label '等待D1诊断。到中心后仍持续纠偏；球暂时不到中心不会结束会话。限位、丢球与故障仍停步。' 612 112
# Everyday operation has no tuning controls or automatic serial commands.
$cameraTab.Text='画面';$controlTab.Text='高级'
$simpleTab=New-Object Windows.Forms.TabPage('日常操作');$leftTabs.TabPages.Clear();$leftTabs.TabPages.AddRange([Windows.Forms.TabPage[]]@($simpleTab,$cameraTab,$controlTab,$cascadeTab));$leftTabs.SelectedIndex=0
$simpleHelp=New-Object Windows.Forms.Label;$simpleHelp.Font=New-Object Drawing.Font('Microsoft YaHei UI',13)
$simpleHelp.Text="① 先调平，再K1使能`r`n`r`n② 调平、放球到中心`r`n    首次K3记录中心和限位基准`r`n`r`n③ 按 K2：持续送回中心`r`n    到中心后继续保持`r`n`r`n再按 K2：停止、保持锁定"
$simpleHelp.SetBounds(15,20,285,300);$simpleTab.Controls.Add($simpleHelp)
$simpleState=New-Object Windows.Forms.Label;$simpleState.SetBounds(15,330,285,95);$simpleState.Text='未连接。参数已内置easy3.bit，无需操作标定工具。';$simpleTab.Controls.Add($simpleState)
$simpleNote=New-Object Windows.Forms.Label;$simpleNote.SetBounds(15,580,285,160)
$simpleNote.Text="运行中不用扶球；左右轻推后松手观察回中。`r`n`r`n持续丢球、限位或故障仍会停步。K4会释放使能。`r`n`r`n曝光和蓝框调节在「画面」页。"
$simpleTab.Controls.Add($simpleNote)
$script:lastCascade=$null;$script:cascadeSequence=0;$script:cascadePending=$null;$script:cascadeModel=$null;$script:cascadeFit=$null
function Send-CascadeSettings($P){
 Require-Link
 if($script:lastRecord.F -ne 0){throw '故障已锁存：先支撑机构并排查原因，不能通过应用参数清除'}
 $wantedRuntime=if($P.selection -ge 2){0}else{[int]$runtime.Value}
 if($script:lastRecord.MD -ne 1 -or $script:lastRecord.RU -ne $wantedRuntime){
  $s=@{DS=(($script:lastRecord.DS+1) -band 65535);MD=1;KD=$script:lastRecord.KD;SL=$script:lastRecord.SL;RU=$wantedRuntime;Sent=[DateTime]::Now}
  $script:serial.Write((New-FollowPacket $s.DS 1 $s.KD $s.SL $s.RU));$script:followPending=$s
 }
 $base=if($script:lastCascade){[int]$script:lastCascade.sequence}else{$script:cascadeSequence}
 $script:cascadeSequence=([Math]::Max($base,$script:cascadeSequence)+1) -band 65535
 $P.sequence=$script:cascadeSequence;$P.diagnostics=1
 $packet=New-CascadePacket $P
 $meta=[IO.Path]::ChangeExtension($script:lastLogPath,'.commands.jsonl')
 $entry=@{time=[DateTime]::Now.ToString('o');packet=$packet;center=$script:lastRecord.C;note='配置/选择有限标定；板上K2才启动'}|ConvertTo-Json -Compress
 Add-Content -LiteralPath $meta -Value $entry -Encoding UTF8
 $script:serial.Write($packet);$script:cascadePending=@{sequence=$P.sequence;Sent=[DateTime]::Now;selection=$P.selection}
 $cascadeAck.Text=('设置已发送，序号{0}；等待D1确认。修改会停止当前会话，保持使能。' -f $P.sequence)
}
function Select-CascadeCalibration([int]$Kind,[int]$Hz,[int]$Amp){
 $p=New-CascadeDefault;$p.selection=$Kind;$p.max_hz=$Hz;$p.amplitude=$Amp
 Send-CascadeSettings $p
}
$cal50.Add_Click({try{Select-CascadeCalibration 2 50 8}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'电机标定')}})
$cal100.Add_Click({try{Select-CascadeCalibration 2 100 16}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'电机标定')}})
$cal200.Add_Click({try{Select-CascadeCalibration 2 200 16}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'电机标定')}})
$calBall4.Add_Click({try{Select-CascadeCalibration 3 50 4}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'球响应标定')}})
$calBall8.Add_Click({try{Select-CascadeCalibration 3 50 8}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'球响应标定')}})
$legacyCascade.Add_Click({try{$p=New-CascadeDefault;$p.selection=0;Send-CascadeSettings $p}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'旧控制')}})
function Load-CascadeModel([string]$Path){
 $m=Get-Content -LiteralPath $Path -Raw -Encoding UTF8|ConvertFrom-Json
 if($m.status -ne 'ACCEPTED_PENDING_PHYSICAL_VALIDATION' -or !$m.parameters){$applyCascade.Enabled=$false;throw ('未生成合格参数：'+$m.reason)}
 $p=@{};$m.parameters.psobject.Properties|ForEach-Object{$p[$_.Name]=[int]$_.Value};New-CascadePacket $p|Out-Null
 $script:cascadeModel=$m;$applyCascade.Enabled=$true
 $cascadeAck.Text=('参数通过模型检查，尚未应用/实板验收。频率上限{0}Hz，延迟预测{1}ms。' -f $p.max_hz,$p.delay_ms)
}
$loadCascade.Add_Click({
 $dialog=New-Object Windows.Forms.OpenFileDialog;$dialog.Filter='标定参数 (*.cascade.json)|*.cascade.json|JSON (*.json)|*.json'
 try{if($dialog.ShowDialog() -eq 'OK'){Load-CascadeModel $dialog.FileName}}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'加载标定')}
 finally{$dialog.Dispose()}
})
$applyCascade.Add_Click({
 try{
  Require-Link;if(!$script:lastCascade -or !$script:cascadeModel){throw '需要当前D1诊断及合格标定文件'}
  $m=$script:cascadeModel
  if($script:lastRecord.L -ne 32 -or $script:lastRecord.DZ -ne 5){$limit.Value=32;$deadzone.Value=5;throw '本次自动整定以限幅32/死区5验证，已填入默认值。请在闭环控制页应用并确认，再应用本参数。'}
  if($script:lastCascade.neutral -ne $m.model.neutral -or $script:lastRecord.C -ne $m.model.center){throw '当前K3中立位或球中心与标定不同，请重新标定'}
  foreach($k in @('AE','AG','RL','RT','RR','RB')){if($m.camera_context -and $script:lastRecord[$k] -ne $m.camera_context.$k){throw '相机或蓝框已改变，请重新标定'}}
  $p=@{};$m.parameters.psobject.Properties|ForEach-Object{$p[$_.Name]=[int]$_.Value};Send-CascadeSettings $p
 }catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'应用串级参数')}
})
$fitCascade.Add_Click({
 try{
  Require-Link;if($script:lastRecord.AR -ne 0){throw '先用K2停止会话，或等有限标定完成，再分析日志'}
  if($script:cascadeFit){throw '已有分析正在运行'}
  $log=Find-LatestLog;if(!$log){throw '尚无日志'};$script:writer.Flush()
  $out=[IO.Path]::ChangeExtension($log,'.cascade.json');$python=(Get-Command python -ErrorAction Stop).Source
  $start=New-Object Diagnostics.ProcessStartInfo;$start.FileName=$python
  $start.Arguments=('-u "{0}" "{1}" --output "{2}" --quiet' -f (Join-Path $PSScriptRoot 'fit_cascade.py'),$log,$out)
  $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
  $proc=New-Object Diagnostics.Process;$proc.StartInfo=$start;[void]$proc.Start()
  $script:cascadeFit=@{Process=$proc;Output=$out};$cascadeAck.Text='正在后台分析日志，串口继续记录；不会自动下发参数。'
 }catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'自动整定')}
})
function Poll-CascadeFit{
 if($script:cascadeFit -and $script:cascadeFit.Process.HasExited){
  $p=$script:cascadeFit.Process;$path=$script:cascadeFit.Output
  try{if(Test-Path -LiteralPath $path){Load-CascadeModel $path}else{throw ('分析未生成文件：'+$p.StandardError.ReadToEnd())}}
  catch{$cascadeAck.Text=$_.Exception.Message;$applyCascade.Enabled=$false}
  finally{$p.Dispose();$script:cascadeFit=$null}
 }
 if($script:cascadePending -and ([DateTime]::Now-$script:cascadePending.Sent).TotalSeconds -gt 2){$cascadeAck.Text='未收到匹配D1回读：请核对cascade.bit及串口RX；未自动重发。';$script:cascadePending=$null}
}
function Show-CascadeDiagnostic($D){
 $script:lastCascade=$D
 if(!($D.flags -band 4096)){$simpleState.Text='当前不是内置回中模式，请重新加载brake_precise6.bit。';return}
 $phase=@('送回中心','减速制动','柔和微调','中心区域保持／回平')[($D.flags -shr 9) -band 3]
 $error=[int]$D.x-[int]$D.center
 $state=if($D.fault){'故障停步，不能自动重试'}elseif(!($D.flags -band 2)){'先调平、K1使能'}elseif(!($D.flags -band 8192)){'放球到中心，首次K3建立安全基准'}elseif(!($D.flags -band 4)){'准备好，按K2回中'}else{$phase}
 $at=$D.reference_q8/256.0
 $activeRadius=100;if($script:lastRecord){$activeRadius=[int]$script:lastRecord.DZ;if($activeRadius -lt 60){$activeRadius=100};if($activeRadius -gt 100){$activeRadius=100}}
 $saturated=($D.flags -band 4) -and [Math]::Abs($error) -gt $activeRadius -and ([Math]::Abs($at-$D.work_min) -le 1 -or [Math]::Abs($at-$D.work_max) -le 1) -and [Math]::Abs($D.position-$at) -le 2
 if($saturated){$state='纠偏角度已到限幅，球仍未回中'}
 if(($D.flags -band 16384) -and ($D.flags -band 4) -and !$D.fault){$state=if($D.frequency_hz -ne 0){'检查点：限额收尾到位'}else{'检查点：反馈核对／等待到位'}}
 if(($D.flags -band 4) -and !($D.flags -band 16384) -and !$D.fault -and !$saturated -and [Math]::Abs($error) -gt 35){$state='精准回中：尚未进入±35px保持区'}
 if(($D.flags -band 32768) -and !$D.fault){$state='换向前反馈确认：有限补步，等待编码器响应'}
 $angle=($D.position-$D.limit_anchor)*360.0/4096
 $simpleState.Text=$state+"`r`n"+('球偏差：{0}px ≈ {1:+0.0;-0.0;0.0}mm' -f $error,(Convert-ErrorToMm $error))+"`r`n"+('电机：{0:N2}°；故障：{1}' -f $angle,$D.fault)
 $regionSummary.Text=('状态：{0}。工作−16°～+32°；反馈保护约−17.93°～+34.98°；均相对首次K3基准。中心附近限制的是微调速度，完整角度窗口保留。' -f $state)
}

# Region release shows only everyday use and the existing camera controls.
$form.Text='PH1P35 精准回中6｜抗抖脱困与提前制动 · K2运行'
$leftTabs.TabPages.Remove($controlTab);$leftTabs.TabPages.Remove($cascadeTab)
$roiCenter.Visible=$false;$details.Visible=$false;$ack.Visible=$false
$regionSummary=Label-At 'K1使能；调平放球K3定中心；K2送回中心区域。无需采集或手填控制参数。' 360 748 800 80
$simpleHelp.Text="① 先调平，再K1使能`r`n`r`n② 调平，放球到实际中心`r`n    首次K3记录中心和限位基准`r`n`r`n③ 按 K2：送回中心区域`r`n    回到附近后回平、保持`r`n`r`n再按 K2：停止、保持锁定"
$simpleNote.Text="默认±35px低速回平保持；超过±70px恢复纠偏。高速仍提前200Hz制动；球静止在外面时抗抖脱困；每级电机到位且球仍静止约1秒后再加力。运动后恢复制动。`r`n`r`n运行中不用扶球。K4立即停止并释放。`r`n`r`n首次K3建立限位基准；之后K3只重设中心，不挪动安全窗口。曝光和蓝框在「画面」页。"
$simpleState.Text='等待brake_precise6.bit。连接不会自动运动。'

$zoneLabel=New-Object Windows.Forms.Label;$zoneLabel.Text='稳区大小（改后按K2重新启动）';$zoneLabel.SetBounds(15,433,285,24);$simpleTab.Controls.Add($zoneLabel)
$zoneChoice=New-Object Windows.Forms.ComboBox;$zoneChoice.DropDownStyle='DropDownList';[void]$zoneChoice.Items.AddRange(@('较紧：±80像素','标准：±100像素（推荐）'));$zoneChoice.SelectedIndex=1;$zoneChoice.SetBounds(15,461,285,30);$simpleTab.Controls.Add($zoneChoice)
$zoneApply=New-Object Windows.Forms.Button;$zoneApply.Text='应用稳区（无需新bit）';$zoneApply.SetBounds(15,500,285,30);$simpleTab.Controls.Add($zoneApply)
$zoneAck=New-Object Windows.Forms.Label;$zoneAck.Text='默认100像素；无需发送配置。';$zoneAck.SetBounds(15,536,285,42);$simpleTab.Controls.Add($zoneAck)
$script:zonePending=$null
$zoneApply.Add_Click({try{
 Require-Link;if($script:pending -or $script:zonePending){throw '上一组参数尚待确认'}
 if(!$script:lastRecord -or ([DateTime]::Now-$script:lastRx).TotalSeconds -gt 1.5){throw '需要新鲜的VIS6回读'}
 if($script:lastRecord.F -ne 0){throw '故障锁存，不能通过参数清除'}
 $r=@(80,100)[$zoneChoice.SelectedIndex];$p=New-Region100ZoneProposal $r $script:lastRecord
 $script:serial.Write((New-ParameterPacket $p.SEQ $p.C $p.DZ $p.G $p.L));$script:pending=$p;$script:zonePending=$p;$script:zoneFailure=$false
 $zoneAck.Text='发送中；参数提交会停止当前会话，等待回读确认。'
 }catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'稳区设置')}})
function Poll-ZoneProfile{
 if(!$script:zonePending){
  if($script:lastRecord -and !$script:zoneFailure){$r=[int]$script:lastRecord.DZ;if($r -lt 60){$r=100};if($r -gt 100){$r=100};$zoneAck.Text=('回读稳区：±{0}px；下拉选择须点击应用。' -f $r)}
  return
 }
 $p=$script:zonePending
 if($script:lastRecord -and (Test-Readback $script:lastRecord $p)){
  $zoneAck.Text=('已确认±{0}px；按板上K2重新启动。' -f $p.DZ);$script:zonePending=$null
 }elseif(([DateTime]::Now-$p.Sent).TotalSeconds -gt 2){$zoneAck.Text='未确认，未自动重发；请核对新固件和RX连接。';$script:zonePending=$null;$script:zoneFailure=$true}
}

function Test-BrakePrecise6Panel{
 if($script:zonePending -or $zoneChoice.SelectedIndex -ne 1 -or $script:serial -or $leftTabs.TabCount -ne 2){throw 'unexpected serial/UI side effect'}
 $d=Convert-CascadeDiagnostic (Get-Content (Join-Path $PSScriptRoot 'asym_diag_fixture.txt') -Raw)
 $d.flags=8192 -bor 4096 -bor 2048 -bor 128 -bor 2 -bor 4 -bor (3 -shl 9);$d.x=960;$d.center=960;$d.position=0;$d.reference_q8=0;Show-CascadeDiagnostic $d
 if(!$simpleState.Text.Contains('中心区域保持')){throw 'wide HOLD not shown'}
 $d.x=1663;$d.center=1077;$d.position=364;$d.reference_q8=364*256;Show-CascadeDiagnostic $d
 if(!$simpleState.Text.Contains('限幅') -or !$simpleState.Text.Contains('31.99')){throw 'saturation/relative angle not shown'}
 $d.flags=8192 -bor 4096 -bor 2048 -bor 128 -bor 2 -bor 4 -bor (3 -shl 9);$d.x=1050;$d.center=960;$d.position=0;$d.reference_q8=0;Show-CascadeDiagnostic $d
 $script:lastRecord=Convert-Record ($sample.Replace('DZ=0014','DZ=0064').Replace('BX=01C2','BX=041A').Replace(' P=00000004 ',' P=00000000 ').Replace(' T=FFFFFFFB ',' T=00000000 ').Replace(' AT=FFFFFFFB ',' AT=00000000 '));$script:lastRx=[DateTime]::Now
 $d.flags=$d.flags -bor 16384;$d.frequency_hz=100;Show-CascadeDiagnostic $d;if(!$simpleState.Text.Contains('限额收尾')){throw 'checkpoint finishing status missing'};$d.flags=$d.flags -band (-bnot 16384);$d.frequency_hz=0;Show-CascadeDiagnostic $d
 $d.flags=$d.flags -bor 32768;Show-CascadeDiagnostic $d;if(!$simpleState.Text.Contains('有限补步')){throw 'recovery status missing'};$d.flags=$d.flags -band (-bnot 32768);Show-CascadeDiagnostic $d
 $form.Opacity=0;$form.ShowInTaskbar=$false;$form.Show();[Windows.Forms.Application]::DoEvents()
 $b=New-Object Drawing.Bitmap($form.Width,$form.Height);$form.DrawToBitmap($b,(New-Object Drawing.Rectangle(0,0,$form.Width,$form.Height)));$b.Save((Join-Path $PSScriptRoot 'brake_precise6_preview.png'));$b.Dispose()
 $script:history.Clear();for($i=0;$i -lt 240;$i++){$p=-182+$i*546.0/239;$script:history.Enqueue(@{Error=-900+$i*1800.0/239;P=$p;AT=$p+2;MT=$p+4;Anchor=0;Valid=($i -lt 115 -or $i -gt 125)})}
 $plotTabs.SelectedIndex=1;[Windows.Forms.Application]::DoEvents();$form.Refresh();$b=New-Object Drawing.Bitmap($form.Width,$form.Height);$form.DrawToBitmap($b,(New-Object Drawing.Rectangle(0,0,$form.Width,$form.Height)));$b.Save((Join-Path $PSScriptRoot 'brake_precise6_curve_preview.png'));$b.Dispose();$form.Close()
 Write-Output 'BRAKE_PRECISE6_PANEL_SMOKE_PASS wide angles,fixed limits,saturation,HOLD,no serial side effects'
}
