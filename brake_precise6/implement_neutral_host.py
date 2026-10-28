from pathlib import Path
import json,re
root=Path(__file__).resolve().parent
before=Path(json.loads((root/'neutral_lineage.json').read_text(encoding='utf-8'))['archive'])/'project'
s=(before/'host/vision_panel_cn.ps1').read_text(encoding='utf-8-sig')
s=s.replace('PH1P35 快速纠偏｜20ms外环·AUTO20ms/步｜G3/L32/SL8','PH1P35 中立位纠偏｜K3记录球中心与控制中立｜20ms')
s=s.replace('配套response新bit；方向保持。K3定球中心→K1使能→K2开始；K4停机。丢球500ms/断流200ms停止。','配套neutral新bit。先调平机构、放球到中心，再K3记录中心/中立位→K1使能→K2开始；K4停机。')
s=s.replace('视觉目标参数（连续模式实时更新）','连续纠偏：围绕K3记录的中立位')
s=s.replace('目标限幅（编码器计数）','纠偏幅度（计数）')
s=s.replace("@('单次视觉动作','连续PD控制','回软件参考位')", "@('单次（初始零点基准）','连续PD（K3中立）','回初始软件零点')")
s=s.replace("@('0 单次视觉动作','1 连续PD控制','2 回软件参考位')", "@('0 单次（初始零点基准）','1 连续PD（K3中立）','2 回初始软件零点')")
s=s.replace("'先用板上K3确认中心')", "'先用板上K3确认中心','K3中立位越界，请重建初始参考')")
s=s.replace("'与串口提交冲突，请重按')", "'与串口提交冲突，请重按','球中心已记，中立位越界')")
s=s.replace("$R.L -gt 0 -and [Math]::Abs($R.T) -ge $R.L -and [Math]::Abs($R.AT-$R.P) -le 1 -and [Math]::Abs($R.AT) -ge $R.L", "[Math]::Abs($R.T) -eq 60 -and [Math]::Abs($R.AT-$R.P) -le 1 -and [Math]::Abs($R.AT) -eq 60")
s=s.replace('限幅保持：球未回中','绝对限幅保持：球未回中')
s=s.replace('$edge.P=11;$edge.T=12;$edge.AT=12;$edge.L=12', '$edge.P=59;$edge.T=60;$edge.AT=60;$edge.L=32')
s=s.replace("$details.Text -notlike '*限幅保持*'", "$details.Text -notlike '*电机已到位*'")
s=s.replace('准备电机回参考（非球回中）','准备回初始零点（非K3中立）')
s=s.replace('仅选回参考模式，未发送。应用运行设置后按K2；P=0是原使能参考，未必是机械水平。','仅选回初始零点，未发送。应用后按K2；目标P=0不是K3记录的水平位置。')
s=s.replace('默认：G3/DZ5/L32，阻尼12/SL8，60秒。20ms外环；仅连续动作提速。','默认G3/DZ5/幅度32/SL8，60秒。K3同时记录控制中立位；不重置编码器原点。')
s=s.replace('方向已确认，分别应用两组参数；读回后按K2。限幅32约2.81度。','方向保持，分别应用两组参数；读回后K2。幅度相对K3中立，绝对硬限±60。')
s=s.replace("$centerAck.Text=('已确认中心 X：{0}　K3：{1}　记录次数：{2}；连续中心确认：{3}' -f $R.C,(Center-Text $R.KC),$R.CC,$R.CZ)", "$centerAck.Text=('球中心X：{0}　K3：{1}　次数：{2}；本版K3同时记录控制中立位，不清零P/MC' -f $R.C,(Center-Text $R.KC),$R.CC)")
s=s.replace('候选T：{0}　缓变AT：{1}', '绝对T：{0}　绝对AT：{1}')
s=s.replace('演示：新版G3/DZ5/L32/SL8/60s，未连接串口','演示：球居中时，T/AT围绕K3中立位，不一定为0；未连接串口')
extra=""" $offset=Convert-Record $sample;$offset.C=1021;$offset.BX=1027;$offset.P=32;$offset.T=33;$offset.AT=33;$offset.L=32;$offset.MB=0;$offset.OK=1
 if((Motion-Text $offset) -like '*限幅*'){throw '非零中立位下不能用绝对T与相对L误判饱和'}
 if((Reject-Text 11) -notlike '*越界*' -or (Center-Text 8) -notlike '*越界*'){throw '中立位越界状态未映射'}
"""
s=s.replace(" Write-Output 'HOST_SELF_TEST_PASS:",extra+" Write-Output 'HOST_SELF_TEST_PASS:")
fixture=root/'sim/results/tb_neutral.log'
if fixture.exists():
 raw=fixture.read_bytes();log=raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else raw.decode('utf-8-sig')
 lines=[x.split(' ',1)[1] for x in log.splitlines() if x.startswith('UART_NEUTRAL ') and ' P=0000001F ' in x]
 if lines:s=re.sub(r"\$responseSample='[^']*'",lambda m:"$responseSample='"+lines[0]+"'",s)
# The UI cannot infer a stored neutral from an arbitrary running429byte report.
# Do not label |T|>=L as relative saturation when the neutral can be nonzero.
(root/'host/vision_panel_cn.ps1').write_text(s,encoding='utf-8-sig')
print('Neutral host prepared; VIS5/P/V/S and parser functions unchanged')
