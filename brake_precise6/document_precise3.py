from pathlib import Path
import json,hashlib,csv,sys
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'host'))
from asym_protocol import parse_diag,parse_record
out=R/'evidence/brake_precise3_measurement';out.mkdir(exist_ok=True)
path=R/'host/logs/20261026_215118_541.txt'
rows=[];vis=[]
for line in path.read_text().splitlines():
 if line.startswith('D2'):
  r=parse_diag(line)
  if r:rows.append(r)
 elif line.startswith('VIS=6'):
  r=parse_record(line)
  if r:vis.append(r)
stuck=[r for r in rows if 146291<=r['time_ms']<=156900 and r['spent']==1 and r['position']==-5 and r['command_position']==-4 and r['frequency_hz']!=0 and r['fault']==0]
summary={'trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'D2_records':len(rows),'VIS6_records':len(vis),'stuck_nonzero_rate_count':len(stuck),'stuck_first_last_ms':[stuck[0]['time_ms'],stuck[-1]['time_ms']] if stuck else [],'VIS_CHECK_SP1_Pminus5_count':sum(r['MS']==7 and r['SP']==1 and r['P']==-5 and r['F']==0 for r in vis),'qualification':'Actual trace proves no progression; pending direction is inferred, reproduced separately in RTL, not directly recorded in old D2.'}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
with (out/'stuck.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(stuck)
print(json.dumps(summary,ensure_ascii=False))
guide='''# brake_precise3：换向反馈等待修复与渐进回中

## 本次数据与定位

依据用户确认已烧录brake_precise2的20261026_215118_541.txt。日志显示一轮停在中心右侧44～47px；另一轮SP=1、P=-5、MC=-4、CHECK不再发步，最终F4。旧遥测没有待确认方向，不能仅凭日志断言唯一原因。RTL独立复现了同样停顿：一个旧方向脉冲未产生编码器计数后，请求换向；换向要求pending=0，而F1要求累计3个无反馈脉冲，造成互相等待。旧20ms重试未越过这一门槛。

## 本次修改

- 新增独立恢复建立状态MS=10。仅在换向受1～2个无响应旧方向脉冲阻塞、真实静默已达40ms、无反向反馈时，沿原DIR补一个确认脉冲。并非立即按新方向发步。每个补步仍等待反馈，最多累计3步；无响应走原F1，有响应后排空再按原20ms静默及DIR建立时间换向。
- 此过程最多增加2个旧方向脉冲，占用同一64步预算和5秒计时；不清pending、不重置编码器/MC/故障，也不自动重启故障。MC、实际位置边界、K4和丢球取消持续有效。
- 真正静止采用至少16个真实检测结果中位置跨度不超过4px且当前滤波速度不超过24px/s，30fps时约0.53秒。静止在35px外时从8计数开始，每约10帧增加8计数；100px内上限24，远区逐级到48。位移跨度超4px或速度超过24px/s即撤回脱困，恢复制动。此上限仅约束脱困增量，不限制正常控制完整工作范围。
- 保持入口仍是±35px；稳定位置趋势允许容忍导数抖动。保留原3帧低速入口、±70px退出和高速200Hz制动。固定−16°～+32°工作范围不变。
- D2长度/XOR/VIS6格式不变，D2 flags bit15表示换向反馈确认等待或恢复建立；新面板显示此状态。旧bit与面板完整保留。

## 板上步骤

1. 烧录output/brake_precise3.bit，配套启动host/start_brake_precise3.cmd。
2. 保持与此前相同机械中立姿态：调平→K1→球静止在实际中心时K3→K2。
3. 首先看第二次启动或换向时SP是否继续增加、P是否有真实响应；无响应应及时F1而不是空等F4。其次看44～47px停点是否分级靠近±35px，球开始移动后是否及时制动。
4. K2停止并保持锁定，K4立即停步并释放。故障不自动重启。PWM/Z仍不使用。
5. 回退使用output/brake_precise2.bit和host/start_brake_precise2.cmd，父bit SHA256 bb0844ff70ea6b50eaf363b488435dbc6ad0f0167449f97e86751ac60ecb3560。

## 验证范围

新增旧RTL死锁复现、真实STEP恢复/F1/F2/F5/F6/K4/无效视觉取消、44～47px抖动停车、8/16/24分级及运动退出测试；保留其他全部回归和模型门槛。模型只是控制链路检查，不代表这套实际机构已达到35px精度。完整构建结果和SHA见brake_precise3_verification.json。本次未自动烧录。
'''
(R/'精准回中3_测试说明.md').write_text(guide,encoding='utf8')
for name in ['brake_precise3_controls.ps1','brake_precise3_panel_cn.ps1']:
 p=R/'host'/name;s=p.read_text(encoding='utf-8-sig').replace('Test-BrakePrecise2Panel','Test-BrakePrecise3Panel')
 if name.endswith('controls.ps1'):
  key=" $form.Opacity=0;$form.ShowInTaskbar=$false;"
  s=s.replace(key," $d.flags=$d.flags -bor 32768;Show-CascadeDiagnostic $d;if(!$simpleState.Text.Contains('有限补步')){throw 'recovery status missing'};$d.flags=$d.flags -band (-bnot 32768);Show-CascadeDiagnostic $d\n"+key)
 p.write_text(s,encoding='utf-8-sig')
