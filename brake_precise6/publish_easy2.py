"""Publish the verified F5 repair, keeping all older releases immutable."""
from pathlib import Path
import json,hashlib,zipfile,shutil,difflib,re,sys
sys.stdout.reconfigure(encoding='utf-8')
r=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from easy2_contract import check_easy2
check_easy2()
v=json.loads(read(r/'verification.json'));assert v['status']=='SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_EASY2_TEST'
bit=Path(v['delivery_bit']);assert sha(bit)==v['sha256'];digest=v['sha256']
lineage=json.loads(read(r/'easy2_lineage.json'));archive=Path(lineage['archive']);parent=next((archive/'published').rglob('delivery_manifest.json')).parent
metrics=f"SWNS {v['timing_ns']['SWNS']:+.3f}ns / HWNS {v['timing_ns']['HWNS']:+.3f}ns，STNS/HTNS 0；Slice {v['resources']['slice']}/21216、DSP {v['resources']['DSP']}/40"
guide=f'''# easy2：修复连续纠偏F5，增大调节幅度

## 使用：仍然只按这几个键

1. 支撑机构，按此前成功的方法加载 [easy2新bit]({bit.as_posix()})。旧easy.bit不会得到这次修复。
2. K1使能，把机构调平、球放在实际中心，按一下K3。
3. 按K2开始持续回中，松手观察。不需要操作标定工具或填写参数。
4. 再按K2停止并保持锁定；K4立即停止并释放使能。

[配套中文面板]({(r/'host/start_panel.cmd').as_posix()})默认打开“日常操作”。曝光3600、增益143、蓝框操作保留，串口和接线不变。

本次默认上下调节幅度由相对K3中立的**±32增至±48编码器计数**，约±4.22°电机轴角；它不等于杆的倾角。绝对目标仍夹在±60，编码器实际P±64、MC±64没有扩大，因此中立靠近边界时可用幅度会缩小。

## 已确认的故障原因及本次修复

最新213354日志：有效球、AB错误0，P在−33～+32间往返，约5.76秒、累计145步后，某活动段SP64触发F5并保持EN。此时球并未回中心，旧版把连续往返累计当成短程超预算。

新版仅在连续串级模式使用正常检查点：达到48脉冲，或有发步且本段达到3.5秒时，暂停发步和参考缓变，等待至少40ms真实静止；原执行器先处理未完成的反馈检查，再要求该段净位移与1.28125计数/脉冲的差不超过±4计数，且无反向标志，才能完成一段并继续。会话AR保持，不标记球或电机已经到位，不清原点/MC/故障，也不按视觉帧清预算。

如果反馈不一致、无反馈、反向、限位或超时，仍锁存故障并停步。底层64脉冲/5秒、F1～F8、K4直停和500ms丢球/200ms断流保护保留。检查点不是故障清除或故障自动重试，短暂停步也不是会话结束。

同时将速度观察器的跳变重置门槛从32增至128像素，避免实际快速滚动超过32像素/帧时反复归零，保留速度制动。更大的瞬跳、坏帧、持续丢失仍按原规则处理。未改变识别阈值、曝光、ROI和视频时序。

## 这次如何判断

先给左右小扰动并松手，查看“正在持续回中/保持”、球偏差和故障。正常情况下即使累计总步数超过64，也不应因为正常往返而变成F5；“段脉冲”会在核对换段后重新计数，累计TS不清零。

本次是有日志依据的软件修复与更大幅度测试版，**实际回中精度和稳球效果仍需新实板日志确认**。轨迹回放中的球坐标来自实测，但电机AB反馈由模型生成，不能据此宣称实板稳球成功。

## 验证

- 21套当前源码RTL回归通过，含八类故障、K1/K2/K3/K4、相机/检测、真实AB、完整429/94字节UART、61秒中心保持、六组假设球杆模型。
- 旧easy源码回放同一实测坐标轨迹可复现F5；新版重复回放累计超过200脉冲、正常换段且不触发F5，并测试换段中K4立即停止。
- 专项测试累计192脉冲、四次换段，原点和MC连续保留；反馈比例错误时不能换段，最终F4超时停步并保持EN。
- 45像素/帧的高速移动能维持非零速度估计。未改视频链路沿用归档的完整18帧RGB证明，并核对源码冻结；未计为本轮完整RGB重跑。
- 7项主机测试、面板SelfTest/SmokeTest通过。完整TD：{metrics}。器件PH1P35MDG324及全部引脚/时钟不变，未放宽约束。

## 文件与恢复

bit SHA256：`{digest}`。

此前easy源码、bit、面板和本次三份实测日志完整归档在 `{archive.as_posix()}`；旧bit仍为`output/vision_follow_20261022_easy.bit`，SHA256 `{lineage['parent_bit_sha256']}`。旧版会重复已发现的F5问题，仅作为恢复基线保留。加载/重新加载会释放使能，先支撑机构。

开发入口：`build.ps1 -Release easy2`、`run_easy2_regression.ps1`、`python verify.py`、`python publish_easy2.py`。没有自动烧录或写Flash。
'''
(r/'测试说明.md').write_text(guide,encoding='utf-8')
(r/'README.md').write_text(f'''# 一键回中easy2：连续F5修复 / 幅度48

[新bit]({bit.as_posix()}) · [中文面板]({(r/'host/start_panel.cmd').as_posix()}) · [测试与恢复]({(r/'测试说明.md').as_posix()})

K1使能、K3定中心、K2持续回中。连续纠偏通过真实反馈检查点换段；默认相对幅度±48。故障/限位保护保留。21套RTL及旧版F5复现、7项主机测试、面板与完整布线通过；{metrics}。真实稳球仍待新日志。

SHA256 `{digest}`。当前仅用publish_easy2.py发布；旧easy包和bit不覆盖。
''',encoding='utf-8')
(r/'实现与协议.md').write_text('# easy2增量\n\n检查点时序、反馈比例、幅度与观察器变更以测试说明为准。P/V/S/C与429字节VIS5、94字节D1和XOR均不变；AC/DC包含已核对的动作段，检查点不置到位OK。以下为旧easy沿革，旧文的连续SP64直接锁存描述已由正常检查点取代，底层超预算F5仍保留。\n\n'+read(parent/'实现与协议.md'),encoding='utf-8')
e=r/'evidence/easy2_before';e.mkdir(parents=True,exist_ok=True)
for p in (archive/'physical').iterdir():shutil.copy2(p,e/p.name)
for rel in ['sim/results/tb_replay_old.log','sim/replay_old_all.v','sim/easy2_recorded_frames.json']:
 shutil.copy2(r/rel,e/Path(rel).name)
changed=[];diff=[]
paths0=list((r/'rtl').glob('*.v'))+list((r/'host').glob('*.ps1'))+list((r/'sim').glob('tb_*.v'))+[r/'user_source/hdl_source/design_top_wrapper.v',r/'build.ps1']
for p in paths0:
 rel=p.relative_to(r).as_posix();old=parent/rel
 if not old.exists() or sha(old)!=sha(p):
  changed.append(rel);diff.extend(difflib.unified_diff(read(old).splitlines(True) if old.exists() else [],read(p).splitlines(True),fromfile='easy/'+rel,tofile='easy2/'+rel))
(r/'easy2_changes.diff').write_text(''.join(diff),encoding='utf-8')
(r/'easy2_changed_files.json').write_text(json.dumps({'changes':changed,'manual_FSM_changed':False,'common_guards_changed':False,'checkpoint_budget':48,'relative_limit':48,'observer_reset_pixels':128},ensure_ascii=False,indent=2),encoding='utf-8')
(r/'output/easy2_sha256.txt').write_text(digest+'  vision_follow_20261022_easy2.bit\n',encoding='ascii')
p=r/'AGENTS.md';s=read(p)
if not s.startswith('# easy2 delivery status'):
 p.write_text(f'# easy2 delivery status (2026-10-24)\n\nCurrent easy2 bit `{digest}`;21 current suites+old F5 replay/7host/panel/routing pass;{metrics}. Inherited fullRGB frozen legacy path. AUTO checkpoint at48pulses/3.5s,quiet40ms,drained feedback,net ratio1.28125±4counts;not arrived,no fault/origin/MC clear. Relative48,absolute60,P/MC64. Observer reset128px. K1/K3/K2 unchanged. Physical return pending. Only publish_easy2.py current.\n\n'+s,encoding='utf-8')
p=r/'baseline_contract.json';b=json.loads(read(p));b['status']=v['status'];p.write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf-8')
(look/'下一步_连续视觉闭环.md').write_text('# 当前入口：easy2\n\n'+f'[测试与恢复]({(r/'测试说明.md').as_posix()})\n\n修复连续段SP64误停，幅度48；K1使能、K3定中心、K2持续回中。真实效果待确认。\n',encoding='utf-8')
paths=set()
for folder in ['rtl','user_source','td_project','host','sim','evidence']:
 for p in (r/folder).rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(r).as_posix()
  if '/__pycache__/' in rel or rel.startswith('host/logs/') or rel=='sim/results/tb_rgb.log' or p.suffix.lower() in ['.vvp','.vcd','.pyc','.db'] or p.name.endswith(('.combined.v','.runner.log')) or p.name.startswith('synthetic_'):continue
  if folder=='td_project' and p.suffix not in ['.al','.sdc']:continue
  paths.add(p)
for p in r.iterdir():
 if p.is_file() and (p.suffix.lower() in ['.py','.ps1','.tcl','.md','.json','.diff'] or p.name in ['build.log','routed_netlist.v']):paths.add(p)
for p in (r/'output').iterdir():
 if p.is_file() and p.suffix in ['.bit','.txt']:paths.add(p)
for pattern in ['*.area','*.ts','*_pr.timing']:paths.update((r/f'{r.name}_Runs/phy_1').glob(pattern))
paths.discard(r/'delivery_manifest.json');manifest={p.relative_to(r).as_posix():sha(p) for p in sorted(paths)}
(r/'delivery_manifest.json').write_text(json.dumps({'status':v['status'],'bit':'output/vision_follow_20261022_easy2.bit','bit_sha256':digest,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
bundle=look/'VIS5_连续纠偏修复_easy2_20261024.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for rel in manifest:z.write(r/rel,rel)
 z.write(r/'delivery_manifest.json','delivery_manifest.json')
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None
 for rel,h in manifest.items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,rel
print(json.dumps({'bit':str(bit),'sha256':digest,'bundle':str(bundle),'bundle_sha256':sha(bundle),'paired_files':len(manifest)},ensure_ascii=False,indent=2))
