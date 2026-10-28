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
$simpleHelp.Text="① K1：使能电机`r`n`r`n② 调平、放球到中心`r`n    按 K3 记录中心`r`n`r`n③ 按 K2：持续送回中心`r`n    到中心后继续保持`r`n`r`n再按 K2：停止、保持锁定"
$simpleHelp.SetBounds(15,20,285,340);$simpleTab.Controls.Add($simpleHelp)
$simpleState=New-Object Windows.Forms.Label;$simpleState.SetBounds(15,380,285,120);$simpleState.Text='未连接。参数已内置easy3.bit，无需操作标定工具。';$simpleTab.Controls.Add($simpleState)
$simpleNote=New-Object Windows.Forms.Label;$simpleNote.SetBounds(15,530,285,170)
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
 $live=if(($D.flags -band 4) -and $D.selection -ge 2){'正在有限标定'}elseif($D.flags -band 4){'正在持续回中 / 保持'}elseif($D.fault -ne 0){'故障停步（不能反复重试）'}elseif(!($D.flags -band 2)){'先按K1使能'}elseif(!($D.flags -band 128)){'放球到中心，按K3'}elseif(!($D.flags -band 8)){'等待真实有效识别'}elseif($D.selection -eq 1 -and !($D.flags -band 256)){'当前无可用预置，请加载easy新bit'}else{'已准备，按K2开始回中'}
 $phaseName=if($D.flags -band 2048){@('加速送回','预判制动','中心微调','保留')[($D.flags -shr 9) -band 3]}else{'原控制'}
 $simpleState.Text=$live+'｜'+$phaseName+"`r`n"+('球偏差：{0} 像素' -f ([int]$D.x-[int]$D.center))+"`r`n"+('电机位置：{0}；故障：{1}' -f $D.position,$D.fault)
 if($script:cascadePending -and $D.sequence -eq $script:cascadePending.sequence){
  $cascadeAck.Text=('配置已确认，序号{0}。仍需K1就绪/板上K2启动；K2再次按下停止，K4释放。' -f $D.sequence);$script:cascadePending=$null
 }
 $names=@('旧控制','回中串级（预置/自定义）','电机有限标定','球响应有限标定');$cal=@('未运行','运行中','有限测试完成','保留','测试终止')
 $hold=if($D.flags -band 2){'通电锁定'}else{'使能释放'};$stable=if($D.flags -band 32){'球已稳定3秒，继续保持'}else{'球尚未满足稳定条件'}
 $calName=if($D.cal_status -lt $cal.Count){$cal[$D.cal_status]}else{'未知状态'}
 $cascadeDetails.Text=('{0}｜{1}｜{2}' -f $names[$D.selection],$hold,$stable)+"`r`n"+
 ('P={0}，参考={1:N2}，球速={2:N1}px/s，脉冲指令={3}Hz' -f $D.position,($D.reference_q8/256.0),($D.velocity_q4/16.0),$D.frequency_hz)+"`r`n"+
 ('标定：{0}，阶段={1}，段脉冲={2}/64（连续模式48起核对换段），故障={3}' -f $calName,$D.cal_phase,$D.spent,$D.fault)
 $advanced=$D.selection -ne 0 -and (!$script:lastRecord -or $script:lastRecord.MD -eq 1)
 $gain.Enabled=!$advanced;$invert.Enabled=!$advanced;$damping.Enabled=!$advanced;$slew.Enabled=!$advanced
}
