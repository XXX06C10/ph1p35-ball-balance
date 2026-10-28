# Dedicated wizard. No serial command is sent while importing or connecting.
. (Join-Path $PSScriptRoot 'region_probe_protocol.ps1')
$form.Text='PH1P35 实机诊断｜region_probe.bit · K2开始/中止'
$details.Visible=$false;$ack.Visible=$false;$roiCenter.Visible=$false
$probeSummary=Label-At '测量说明：单腿目标误差≤2计数并稳定100ms；超过1秒中止。记录无效时不生成控制参数。' 360 748 800 80
$cameraTab.Text='画面 / 蓝框';$simpleTab=New-Object Windows.Forms.TabPage('一分钟诊断')
$leftTabs.TabPages.Clear();$leftTabs.TabPages.AddRange([Windows.Forms.TabPage[]]@($simpleTab,$cameraTab));$leftTabs.SelectedIndex=0
function Probe-Label([string]$Text,[int]$Y,[int]$H=55){$v=New-Object Windows.Forms.Label;$v.Text=$Text;$v.SetBounds(12,$Y,300,$H);$simpleTab.Controls.Add($v);return $v}
function Probe-Button([string]$Text,[int]$Y){$v=New-Object Windows.Forms.Button;$v.Text=$Text;$v.SetBounds(12,$Y,300,40);$simpleTab.Controls.Add($v);return $v}
Probe-Label '独立测量固件，不执行连续回中。每一步先点准备，再按板上K2。连接串口不会启动运动。' 10 76 | Out-Null
$probeStatic=Probe-Button '① 准备静态观察：10秒，不发步' 90
Probe-Label '固定球但不遮挡识别区。静态观察可不使能电机。按K2开始；完成后再做下一步。' 138 65 | Out-Null
$probeNeutral=Probe-Button '② 准备中立观察：10秒，不发步' 208
Probe-Label '先调平，K1锁住电机；放球到中心按K3。松手后按K2观察。' 256 65 | Out-Null
$probeMotion=Probe-Button '③ 准备±8计数往返：三对' 326
Probe-Label '球静止在中心，再按K2开始，全程不扶球。每次倾斜400ms、回中立600ms。约0.7°为电机轴角。' 374 78 | Out-Null
$probeAnalyze=Probe-Button '④ 分析本次日志（不下发控制参数）' 458
$simpleState=Probe-Label '等待region_probe.bit事件。此面板不能作为回中面板使用。' 510 100
$probeDetails=Probe-Label 'K2再次按下：中止并保持使能。K4立即停止并释放。丢球、边缘、偏差>120px或速度>150px/s均中止。' 618 110
$script:lastCascade=$null;$script:cascadeSequence=0;$script:cascadeFit=$null;$script:probeEvent=$null;$script:probeEventAt=[DateTime]::MinValue;$script:probeSequence=$null;$script:probeGap=$false;$script:probePending=$null
function Show-ProbeEvent($E){
 if($null -ne $script:probeSequence -and (($E.sequence-$script:probeSequence+65536) -band 65535) -ne 1){$script:probeGap=$true}
 $script:probeSequence=$E.sequence;$script:probeEvent=$E;$script:probeEventAt=[DateTime]::Now
 if($E.diagnostic_flags -band 128){$script:probeGap=$true}
}
function Prepare-Probe([int]$Kind){
 Require-Link
 if(!$script:probeEvent -or ([DateTime]::Now-$script:probeEventAt).TotalSeconds -gt 1.5){throw '未收到E1事件；请先烧入region_probe.bit，勿用easy3.bit'}
 if($script:lastRecord.F -ne 0){throw '故障已锁存，请排查并重新加载固件，不能通过参数清除'}
 if($script:probeGap){throw '事件记录有丢失，请重新加载固件、重新连接后从静态观察开始'}
 if($script:lastRecord.AR){throw '先按K2中止当前测量，或等待完成'}
 $p=New-CascadeDefault;$p.selection=$Kind;$p.amplitude=8;$p.diagnostics=1
 $base=if($script:lastCascade){[int]$script:lastCascade.sequence}else{0};$script:cascadeSequence=([Math]::Max($base,$script:cascadeSequence)+1) -band 65535;$p.sequence=$script:cascadeSequence
 $script:serial.Write((New-CascadePacket $p));$script:probePending=$p.sequence
 $simpleState.Text='设置已发送，等待本轮配置回读；尚未开始。'
}
foreach($pair in @(@($probeStatic,2),@($probeNeutral,3),@($probeMotion,1))){$kind=[int]$pair[1];$pair[0].Tag=$kind;$pair[0].Add_Click({param($sender,$e);try{Prepare-Probe ([int]$sender.Tag)}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'实机诊断')}})}
function Show-CascadeDiagnostic($D){
 $script:lastCascade=$D
 $name=@('未选择','三对小幅往返','静态观察','中立观察')[$D.selection]
 $state=@('等待K2','采集中','完成','保留','中止')[[Math]::Min(4,[int]$D.cal_status)]
 if($null -ne $script:probePending){if($D.sequence -eq $script:probePending -and $D.cal_status -eq 0){$script:probePending=$null}else{$state='等待本轮配置回读'}}
 if($script:probeGap){$state='数据无效：事件丢失/溢出'}
 $simpleState.Text=('{0}：{1}' -f $name,$state)+"`r`n"+('P={0}；目标={1:N0}；故障={2}' -f $D.position,($D.reference_q8/256.0),$D.fault)+"`r`n"+($(if($D.selection -eq 1){'往返腿={0}/12；中心={1}px' -f ($D.cal_phase+1),$D.center}else{'观察10秒；中心={0}px' -f $D.center}))
 if($script:probeEvent){$e=$script:probeEvent;$why=@('无','K1关闭','K4停机','识别无效','断流','配置改变','故障','K2中止','保留','球偏差超限','完成','单腿超过1秒','保持位置漂移','接近ROI边缘','事件溢出','球速过高')[$e.reason]
  $probeDetails.Text=('原因：{0}；核心状态={1}，待确认脉冲={2}，反馈增量={3}，净指令={4}' -f $why,$e.state,$e.pending,$e.delta,$e.commands)+"`r`n"+'K2中止保持使能；K4停止并释放。中止不自动回中立，不自动续跑。'
 }
}
$probeAnalyze.Add_Click({try{
 Require-Link;if($script:lastRecord.AR){throw '先停止测量'};if($script:cascadeFit){throw '正在分析'}
 $script:writer.Flush();$log=Find-LatestLog;$out=[IO.Path]::ChangeExtension($log,'.probe.json')
 $start=New-Object Diagnostics.ProcessStartInfo;$start.FileName=(Get-Command python -ErrorAction Stop).Source
 $start.Arguments=('"{0}" "{1}" --output "{2}"' -f (Join-Path $PSScriptRoot 'region_probe.py'),$log,$out);$start.UseShellExecute=$false;$start.CreateNoWindow=$true
 # Analyzer writes its complete report directly; no redirected pipe can block the UI.
 $proc=New-Object Diagnostics.Process;$proc.StartInfo=$start;[void]$proc.Start();$script:cascadeFit=@{Process=$proc;Output=$out};$simpleState.Text='正在分析日志，不会下发参数。'
}catch{[void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'分析实机记录')}})
function Poll-CascadeFit{
 if($script:cascadeFit -and $script:cascadeFit.Process.HasExited){try{
  $r=Get-Content -LiteralPath $script:cascadeFit.Output -Raw -Encoding UTF8|ConvertFrom-Json
  $simpleState.Text=if($r.status -eq 'INVALID'){'测量未合格：'+($r.errors -join '；')}else{'测量质量合格，等待区域控制设计；尚未验证稳定保持。'}
  $probeDetails.Text=('坐标噪声σ={0:N2}px；中立漂移={1:N2}px/s；编码器延迟中位数={2}ms。完整结果：{3}' -f $r.static_noise.x_std_px,$r.neutral_drift.drift_px_s,$r.motor_response.latency_ms_median,$script:cascadeFit.Output)
 }catch{$simpleState.Text='分析失败：'+$_.Exception.Message}finally{$script:cascadeFit.Process.Dispose();$script:cascadeFit=$null}}
}
function Test-RegionPanel{
 Test-ProbeProtocol
 if($script:serial -or $leftTabs.TabCount -ne 2){throw '采集向导不得自动连接/发送'}
 foreach($s in @(0,1,2,4)){Show-CascadeDiagnostic @{selection=1;cal_status=$s;cal_phase=0;position=0;reference_q8=2048;fault=0;center=960;sequence=0}}
 if(!$simpleState.Text.Contains('中止')){throw '中止状态未显示'}
 Show-CascadeDiagnostic @{selection=2;cal_status=0;cal_phase=0;position=0;reference_q8=0;fault=0;center=960;sequence=1}
 if(!$simpleState.Text.Contains('等待K2')){throw '新配置不得继承DONE'}
 $form.Opacity=0;$form.ShowInTaskbar=$false;$form.Show();[Windows.Forms.Application]::DoEvents()
 $b=New-Object Drawing.Bitmap($form.Width,$form.Height);$form.DrawToBitmap($b,(New-Object Drawing.Rectangle(0,0,$form.Width,$form.Height)));$b.Save((Join-Path $PSScriptRoot 'region_probe_preview.png'));$b.Dispose();$form.Close()
 Write-Output 'REGION_PANEL_SMOKE_PASS: wait/run/done/abort, no serial side effects'
}
