"""Publish paired preset firmware/panel; never program hardware or open serial."""
from pathlib import Path
import json,hashlib,zipfile,difflib
r=Path(__file__).resolve().parent
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads(read(r/'verification.json'));assert v['status']=='SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_EASY_TEST'
from easy_contract import check_easy
check_easy()
bit=Path(v['delivery_bit']);assert sha(bit)==v['sha256'];digest=v['sha256']
lineage=json.loads(read(r/'easy_lineage.json'));a=Path(lineage['archive'])
parent=next((a/'published').rglob('delivery_manifest.json')).parent
metrics=f"SWNS {v['timing_ns']['SWNS']:+.3f}ns，HWNS {v['timing_ns']['HWNS']:+.3f}ns，STNS/HTNS 0；Slice {v['resources']['slice']}/21216，DSP {v['resources']['DSP']}/40"
guide=f'''# easy：K3定中心，K2持续回中

## 只需要做这些

1. 支撑机构，按此前成功方法加载 [easy新bit]({bit.as_posix()})。不是旧cascade.bit；接线不变，设备PH1P35MDG324。
2. K1使能后，将机构调平、球放在你要的中心位置，按一下K3。K3只记录中心与机构中立，不运动。
3. 按一下K2，松手观察。电机持续把球送回中心，到中心后也不结束会话，继续抵抗扰动。
4. 再按一下K2，停止纠偏、保持使能。K4立即停止并释放使能。

**不需要先做电机标定、球标定、分析或应用参数。电脑可以只用来查看和记录。**

[配套中文面板]({(r/'host/start_panel.cmd').as_posix()})默认打开“日常操作”，参数移到高级/标定工具。曝光3600、增益143及蓝框编辑保留；打开面板或连接串口不发送动作。

请先用较小的左右扰动，松开手观察回中。查看“正在持续回中/保持”、球偏差及故障即可。尚无该预置在真实机构上的验收日志，不能把仿真结果当成实板保证。

## “持续尝试”的范围

正常视觉、编码器与行程范围内，没有60秒会话倒计时，也不会因某一次电机到位或球到中心而自动退出。小偏差仍可修正。

持续丢球500ms、相机断流200ms、限位或F1～F8仍停止发步。故障锁存并保留已经建立的使能，不自动重试；K1可释放，K4/复位/断电会释放。单活动段64脉冲/5秒、MC±64、P±64、绝对目标±60均保留。若触发保护，需要先查清原因；不能靠重复按K2绕过保护。

K3须在停止状态、真实有效识别、相机设置完成且无故障时按。运行时重定中心先按K2停止；不重置编码器原点。曝光/蓝框/参数提交仍会停止会话，新的真实结果到来后需重新K2。

## 给开发者的预置记录（平时不用填写）

- 外环KP=819/4096≈0.200，速度阻尼KV=40/256=0.15625，小积分KI=131/65536≈0.002；积分±4计数。
- 内环KP=32Hz/计数，参考速度前馈200/256，最大100Hz，缓变102计数/秒，延迟预测20ms。
- 视觉死区3像素（原5），相对K3限幅32计数，绝对±60；方向沿用已确认正确的原方向。
- 同一预置在B=-5/-10/-20三组假设模型中通过恢复/保持测试，并非实际机构辨识结果；没有扩大保护范围来获得通过。
- 原C01/D1与P/V/S/VIS5协议不变。默认预置可在K3/曝光调整后继续使用，但真正的设置改变仍停步并要求新帧。若主动使用高级C配置，则沿用自定义模型的重新确认规则；恢复默认预置可重新加载easy.bit。

## 验证与恢复

19套当前源码RTL测试通过，含不用UART配置的K3/K2、中心保持61秒、真实AB扰动、K2/K4、短丢/持续丢失、显式C覆盖规则、三种同参数球杆模型及原八类故障、相机、429/94字节完整UART回归。未修改的视频链路沿用归档中完整18帧RGB通过记录，并通过源码冻结与默认旧控制路径检查；本轮完整RGB重跑提前停止，不计为本轮通过。7项上位机协议/拟合测试及中文面板SelfTest/SmokeTest通过。

完整TD综合布线通过：{metrics}。时钟、引脚、原运动算法均未修改。自动稳球仍待真实日志确认，没有自动烧录或写Flash。

easy bit SHA256：`{digest}`。

旧cascade SHA256：`{lineage['parent_bit_sha256']}`。旧bit仍是`output/vision_follow_20261022_cascade.bit`；之前完整交付包未覆盖，改前源码及最新实测日志归档在 `{a.as_posix()}`。旧版需要标定工具；仅想使用当前简单操作请加载easy。

构建：`build.ps1 -Release easy`；验证：`python verify.py`；发布：`python publish_easy.py`。不要运行旧发布脚本覆盖当前说明。
'''
(r/'测试说明.md').write_text(guide,encoding='utf-8')
(r/'README.md').write_text(f'''# 一键回中 easy（2026-10-24）

[新bit]({bit.as_posix()}) · [中文面板]({(r/'host/start_panel.cmd').as_posix()}) · [简明步骤与恢复]({(r/'测试说明.md').as_posix()})

K1先使能；调平放球按K3定中心，K2持续回中，到中心仍保持纠偏。无需标定面板。K2停止保持，K4释放；持续丢球、限位与故障仍停止。

19套RTL、7项上位机测试、面板与完整布线通过；未修改的RGB链路沿用归档完整回归证明。{metrics}。真实机构效果待新日志，未自动烧录。

SHA256 `{digest}`。当前只用publish_easy.py发布；旧cascade包与bit保留。
''',encoding='utf-8')
tech=read(parent/'实现与协议.md')
(r/'实现与协议.md').write_text('# easy预置变更\n\n默认内置回中参数，不再等待外部标定文件。K1使能/K3中心/K2持续；完整参数和范围见测试说明。生产默认诊断开启，模型就绪位表示“可运行预置/自定义”，不再表示一定已实测辨识。显式C配置覆盖预置后仍按旧模型确认规则。以下为串级算法/协议沿革，旧文的“默认必须先标定”仅适用于旧cascade.bit。\n\n'+tech,encoding='utf-8')
changed=[];diff=[]
for folder in ['rtl','host','sim']:
 for p in (r/folder).glob('*'):
  if not p.is_file() or p.suffix not in ['.v','.py','.ps1']:continue
  rel=p.relative_to(r).as_posix();old=parent/rel
  if not old.exists() or sha(p)!=sha(old):
   changed.append(rel);diff.extend(difflib.unified_diff(read(old).splitlines(True) if old.exists() else [],read(p).splitlines(True),fromfile='cascade/'+rel,tofile='easy/'+rel))
for rel in ['build.ps1','user_source/hdl_source/design_top_wrapper.v']:
 changed.append(rel);diff.extend(difflib.unified_diff(read(parent/rel).splitlines(True),read(r/rel).splitlines(True),fromfile='cascade/'+rel,tofile='easy/'+rel))
(r/'easy_changes.diff').write_text(''.join(diff),encoding='utf-8')
(r/'easy_changed_files.json').write_text(json.dumps({'changes':changed,'motor_algorithms_changed':False,'pins_clocks_changed':False},ensure_ascii=False,indent=2),encoding='utf-8')
(r/'output/easy_sha256.txt').write_text(digest+'  vision_follow_20261022_easy.bit\n',encoding='ascii')
p=r/'AGENTS.md';s=read(p)
if not s.startswith('# easy delivery status'):
 p.write_text(f'# easy delivery status (2026-10-24)\n\nCurrent easy bit `{digest}`;19 current suites/7host/panel/routing pass;inherited fullRGB18frames frozen-video/legacy-path proof (current fullRGB rerun interrupted);{metrics}. K1 establishedEN,K3 center,K2 persistent return;built-in bounded preset,no calibration prerequisite. All prior guards retained. Physical return pending,not guaranteed. Old cascade archived and unchanged. Only publish_easy.py current.\n\n'+s,encoding='utf-8')
p=r/'baseline_contract.json';c=json.loads(read(p));c['status']=v['status'];p.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
look=Path('D:/AAAProject/FPGA/AAA_LookHere')
(look/'下一步_连续视觉闭环.md').write_text('# 当前入口：一键回中easy\n\n'+f'[简明步骤]({(r/'测试说明.md').as_posix()})\n\nK1使能、K3定中心、K2持续回中。无需手动标定。故障与限位保护保留，实板效果待确认。\n',encoding='utf-8')
e=r/'evidence/easy_before';e.mkdir(parents=True,exist_ok=True)
import shutil
for p in (a/'physical').iterdir():shutil.copy2(p,e/p.name)
video=r/'evidence/easy_inherited_rgb';video.mkdir(parents=True,exist_ok=True)
for rel in ['sim/results/tb_rgb.log','verification.json','build_sources.json']:
 shutil.copy2(parent/rel,video/Path(rel).name)
(video/'来源说明.md').write_text('本目录是旧cascade完整18帧RGB回归证明。本轮视频/像素检测/CDC及该测试使用的默认旧控制路径保持不变；easy_contract.py核对冻结。当前全RGB重跑提前停止，未计为本轮19套通过。',encoding='utf-8')
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
paths.discard(r/'delivery_manifest.json')
manifest={p.relative_to(r).as_posix():sha(p) for p in sorted(paths)}
(r/'delivery_manifest.json').write_text(json.dumps({'status':v['status'],'bit':'output/vision_follow_20261022_easy.bit','bit_sha256':digest,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
bundle=look/'VIS5_一键回中_easy_20261024.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for rel in manifest:z.write(r/rel,rel)
 z.write(r/'delivery_manifest.json','delivery_manifest.json')
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None
 for rel,h in manifest.items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,rel
print(json.dumps({'bit':str(bit),'sha256':digest,'bundle':str(bundle),'bundle_sha256':sha(bundle),'paired_files':len(manifest)},ensure_ascii=False,indent=2))
