"""Publish only the verified response firmware, paired panel and rollback."""
from pathlib import Path
import hashlib,json,zipfile,difflib,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads(read(root/'verification.json'))
assert r['status']=='SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_RESPONSE_TEST'
lineage=json.loads(read(root/'response_lineage.json'));archive=Path(lineage['archive']);before=archive/'project'
bit=Path(r['delivery_bit']);assert sha(bit)==r['sha256'];digest=r['sha256']
assert sha(root/'output/vision_follow_20261022_loss500.bit')==lineage['old_bit_sha256']
metrics=f"{r['resources']['slice']} Slice；SWNS {r['timing_ns']['SWNS']:+.3f}ns，HWNS {r['timing_ns']['HWNS']:+.3f}ns，STNS/HTNS均0，STA覆盖{r['STA_coverage_percent']:.2f}%"
doc=f'''# VIS5快速纠偏：response（2026-10-23）

已完成十一套仿真、中文面板自检/渲染、完整TD综合布线。**新bit已生成；新节奏的实板响应、摆动和纠偏效果待验证。**

- [新bit]({bit.as_posix()})
- [配套中文面板]({(root/'host/start_panel.cmd').as_posix()})
- [旧loss500恢复入口]({(archive/'恢复说明.md').as_posix()})

## 这次真正改变了什么

| 项目 | 原loss500默认 | 本版默认 |
|---|---|---|
| 连续外环更新间隔 | 100ms | 20ms |
| 连续每步节奏 | 准备20+高2.5+低2.5+反馈50≈75ms | 准备5+高2.5+低2.5+反馈10≈20ms |
| 手动单次/回参考节奏 | 约75ms/步 | 保持约75ms/步 |
| 控制衰减G | 4 | 3（与已确认方向一致，方向位0） |
| 视觉死区DZ | 20像素 | 5像素 |
| 目标限幅L | 12计数≈1.05电机度 | 32计数≈2.81电机度 |
| 缓变SL | 2计数/100ms | 8计数/100ms，使用20ms分数累计 |
| 会话RU | 30秒 | 60秒，可设置0～300秒 |

SL报文单位仍是计数/100ms，没有偷换成每20ms；SL=1也能累计到每100ms一步参考，不会因整数除法卡住。只有收到真正有效新结果后才建立参考，之后在两帧之间继续有界缓变；短丢则冻结T/AT并清掉待处理参考及速率余数，恢复第一帧重新建立速度基准，不积攒突然加速额度。

连续目标改为死区外向远离0的方向取整，最小2计数后再按L夹取；死区内仍为0。它避免小目标落进内环±1计数到位带而完全没有动作。例如G3/DZ5、零速时，偏差31像素原T=3，新T=4；刚离开死区时T至少2。L=0/1仍服从限幅。该改动不是积分补偿，不能宣称消除了机构摩擦或全部稳态误差。

用户2026-10-23确认方向正确，本版保持正常方向，不再要求反转。最新旧固件日志显示G3/DZ5/L24改善后，SL仍为2、RU仍为30；现有两个参数“应用”按钮提交不同报文，新bit启动默认即是表中的新版参数，不必靠两个按钮同时调整才得到提速。

## 保留内容

VIS=5、429字节报告、P/V/S长度/字段及XOR、K1保持使能、K2开始/停止、K3只定视觉中心、K4直接停机均保留。曝光3600、增益143、ROI、真实RGB检测与局部续检全部不改。连续短丢保持500ms，相机断流200ms，恢复后不自动续跑。

全部F1～F8、每活动段64脉冲/5秒、MC±64净指令脉冲、P±64反馈计数、目标硬限±60、连续到位带±1/手动±2保留。只在CHECK更新目标，不随视觉帧重置活动段预算或计时。手动执行器`vision_move_core.v`、编码器、使能保持模块逐字节保留；连续执行器仅增加AUTO准备/等待时长选择，保护逻辑用精确差异合同核对。

本版默认32计数约±2.81电机度，没有扩大到10度。原软件参考P=0不保证机械水平，K3不改变电机原点。丢球、故障、K4之后仍不自动回参考。

## 实板操作和预期

1. 停止电机、松开按键，按原成功方法加载`response.bit`至SRAM。**本版bit已改变**，旧诊断面板对应的loss500 bit并没有提速。器件仍PH1P35MDG324，接线、000细分和原STEP/DIR/EN双口镜像不变。本次未自动下载或写Flash。
2. 关闭旧面板，启动上面的配套中文面板并连接原串口。先确认回读G3、DZ5、L32、SL8、RU60；尚未K2前电机不应自动运行。若手动填入参数，仍分别应用视觉和运行两组，等回读完成后重新K2。
3. 机构置于希望的软件参考位置；球放实际中心按K3，K1使能就绪后按K2。方向保持已确认的设置。先从中心两侧小扰动比较回中，再看较大偏差；不需要重做GPIO或整圈测试。
4. 预期电机启动、反转和目标追赶明显加快；中心附近更早产生细调。电机“到位”不等于球稳定回中；面板会显示球偏差、实际电机角度、“限幅保持：球未回中”和停止原因。新L32到限幅后仍不会无限追加步数。
5. 如果出现明显反复摆动，用K2停会话或K4关闭使能。可先把G提高到4、SL降为4、L降为24后应用并重新K2，或直接恢复旧loss500 bit与其归档面板。不要用扩大硬保护范围来解决摆动。
6. 球回中心和电机回参考是两个目标。“准备电机回参考”只选模式2；应用运行设置后仍需K2启动有限返回，且真实视觉新鲜有效、无故障。相机无效时不自动回零救球。
7. 面板连接后自动记录到本工程`host/logs/`。测试结束用右下角“复制日志路径”或“打开日志文件夹”，无需记文件名。观察误差曲线、T/AT/P是否跟上、AR停止原因；60秒正常结束为SR8。

## 验证证据与限制

十一套当前源码仿真通过：原八类故障、手动±60/0、按键/参数取消、相机I2C/ROI跨域、真实RGB/完整720p检测、连续会话、500/200ms精确边界、真实429字节UART、真实1.28计数/脉冲AB反馈、三个假设球运动模型；新增20ms提速与全八类快速AUTO故障回归、方向准备和STEP高宽、手动回参考仍75ms/步、SL1/SL8单位兼容、细调取整/方向位/小限幅及恢复无速率积攒。

在同样的±16计数目标、生产时长比例的仿真中，旧节奏正向到位1025ms，新节奏280ms；反转1975ms→739ms。加入12ms编码器反馈延迟仍通过。这是模型中的参考到位时间，不是实板钢球回中时间。

三种假设模型采用本版实际默认参数，末端球偏差约-5.90/-6.05/-2.66像素，末100帧RMS约3.83/4.74/3.09像素，满足原速度/偏差门槛。早先用旧G4/DZ20/SL2设置复测时末端仍存在小幅振荡，不能把它标为精密验收；新固件建议从配套默认参数开始。模型不是机构标定，实板摩擦、水平零点、光照及稳定性仍待新日志确认。

{metrics}。器件、全部引脚、双口输出、原时钟及CDC约束逐项核对，未放宽时序、未新增假路径。当前源码和bit哈希配套，详见`verification.json`、`build_sources.json`、`delivery_manifest.json`。

新bit SHA256：`{digest}`。

恢复旧loss500 SHA256：`{lineage['old_bit_sha256']}`。旧bit仍保存在`output/vision_follow_20261022_loss500.bit`，完整旧源码/面板/日志归档见上方入口；需要恢复开发时先复制归档project到独立工作目录，勿改归档。

重建：`build.ps1`；验证：`python verify.py`；发布：`python publish_response.py`。本版只用这个发布脚本，旧脚本保留作历史溯源。
'''
for n in ['测试说明.md','实现与协议.md']:(root/n).write_text(doc,encoding='utf-8')
(root/'README.md').write_text(f'# VIS5 response：快速连续纠偏\n\n当前bit `{bit.name}`，SHA256 `{digest}`。20ms外环、仅连续模式约20ms/步；G3/DZ5/L32/KD12/SL8/RU60。方向按用户确认保持，手动和回参考75ms/步、全部行程/故障/500ms丢球及200ms断流保护不改。\n\n[完整操作与恢复]({(root/"测试说明.md").as_posix()}) · [中文面板]({(root/"host/start_panel.cmd").as_posix()})\n\n十一套仿真与完整布线通过：{metrics}。新实板稳定性待确认，不把仿真模型当作机械标定。仅使用publish_response.py发布。\n',encoding='utf-8')
source_paths=[]
for folder,pattern in [('rtl','*.v'),('host','*.ps1'),('sim','*.v')]:source_paths+=list((root/folder).glob(pattern))
source_paths+=list(root.glob('*.py'))+list(root.glob('*.ps1'))
changes=[p.relative_to(root).as_posix() for p in sorted(set(source_paths)) if not (before/p.relative_to(root)).exists() or sha(p)!=sha(before/p.relative_to(root))]
(root/'response_changed_files.json').write_text(json.dumps({'source_files_changed_or_added':changes},ensure_ascii=False,indent=2),encoding='utf-8')
diff=[]
for rel in changes:
 old=read(before/rel) if (before/rel).exists() else ''
 diff.extend(difflib.unified_diff(old.splitlines(True),read(root/rel).splitlines(True),fromfile='loss500/'+rel,tofile='response/'+rel))
(root/'response_changes.diff').write_text(''.join(diff),encoding='utf-8')
(root/'改动清单_response.md').write_text('连续控制：vision_follow_control.v（20ms/分数缓变/细调）；vision_servo_core.v（仅AUTO时长选择）；vision_monitor.v（新默认/参数连接）；vision_config_rx.v（仅参数默认，解析/校验不改）。生成vision_monitor_all.v同步。\n\n面板合并独立诊断版：区分球/电机到位、角度、限幅提示、回参考准备和日志定位；更新新版默认。新增tb_response.v、response_contract.py及归档/发布脚本；verify.py保留所有原核对再加提速验证。tb_loss、tb_plant验证配套新默认，其余特定旧模式用例显式保留旧配置，未放宽验收门槛。tb_follow改为等待指定DS3/RU0的真实新UART报告，避免把上次会话快照拿来验证新配置。所有检测/视频/引脚/时钟/有限动作基线不改。完整源文件清单见response_changed_files.json，逐行差异见response_changes.diff。',encoding='utf-8')
(root/'output/response_sha256.txt').write_text(digest+'  '+bit.name+'\n',encoding='ascii')
contract=json.loads(read(root/'baseline_contract.json'));contract.update(status=r['status'],next_milestone='physical response speed, braking and ball-center stability with new VIS5 capture')
(root/'baseline_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
agent=root/'AGENTS.md';s=read(agent)
if not s.startswith('# response delivery status'):
 agent.write_text(f'# response delivery status (2026-10-23)\n\nCurrent bit output/{bit.name} SHA256 `{digest}`. Eleven current-source suites, exact AUTO-only servo timing mux and default-only parser adaptation, all8fast faults,6/12ms trueAB,>=2x16count step/reversal benchmark,SL100ms-unit compatibility,RGB/loss500/stream200/429byte UART,host self/smoke and full routing pass. {metrics}. Defaults G3/DZ5/L32/KD12/SL8/60s,20ms control/AUTO pulse; manual/return75ms. Direction normal confirmed by human, preserved. New physical dynamics pending. Only publish_response.py may publish; previous scripts historical. response_lineage archive immutable; old loss500 bit preserved. No auto-download/Flash.\n\n'+s,encoding='utf-8')
progress=root.parent/'D36A_STEPPER_调试进度总结.md'
if 'VIS5 response快速纠偏交付' not in read(progress):
 with progress.open('a',encoding='utf-8') as f:f.write(f'\n\n## 2026-10-23 VIS5 response快速纠偏交付\n\n用户确认方向正确、G3/DZ5/L24稍有改善但慢，真实日志仍SL2/30s。新增20ms外环/AUTO20ms节奏、细调取整，默认G3/DZ5/L32/KD12/SL8/60s；手动回参考时长及所有保护保留。十一套仿真/面板/完整布线通过：{metrics}。新bit `{digest}`，[测试与恢复]({(root/"测试说明.md").as_posix()})。新固件实板稳定性待确认，未自动烧录。\n')
(look/'下一步_连续视觉闭环.md').write_text(f'# 当前交付：VIS5 response快速纠偏\n\n[新bit]({bit.as_posix()}) · [中文面板]({(root/"host/start_panel.cmd").as_posix()}) · [操作与恢复]({(root/"测试说明.md").as_posix()})\n\n20ms外环/连续约20ms一步，G3/DZ5/L32/KD12/SL8/60s。方向保持；全部保护、协议及检测不改。十一套仿真/面板/布线通过，实板稳定性待确认。{metrics}。SHA256 `{digest}`。\n',encoding='utf-8')
files=[]
for folder in ['rtl','user_source','host','sim','td_project']:
 for p in (root/folder).rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(root)
  if any(x in ('__pycache__','logs') or x.endswith('_Runs') for x in rel.parts):continue
  if p.suffix in ('.vvp','.vcd','.db') or p.name.endswith(('.combined.v','_runner.txt')) or 'probe' in p.name:continue
  if folder=='td_project' and p.suffix not in ('.al','.sdc'):continue
  files.append(p)
for pattern in ['*.py','*.ps1','*.tcl','*.md','*.diff','*.json']:files+=list(root.glob(pattern))
files=[p for p in files if p.name!='delivery_manifest.json']
files+=[root/'build.log',root/'routed_netlist.v']
files+=list((root/'output').glob('*.bit'))+list((root/'output').glob('*.txt'))
run=root/f'{root.name}_Runs/phy_1';files+=[run/f'{root.name}{s}' for s in ['_phy.area','_phy.ts','_pr.timing']]
files=sorted(set(files));manifest={'status':r['status'],'bit_sha256':digest,'bit':bit.relative_to(root).as_posix(),'files':{p.relative_to(root).as_posix():sha(p) for p in files}}
(root/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
bundle=look/'VIS5_快速纠偏_response_20261023.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files+[root/'delivery_manifest.json']:z.write(p,p.relative_to(root).as_posix())
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None
 for rel,d in manifest['files'].items():assert hashlib.sha256(z.read(rel)).hexdigest()==d,rel
print(json.dumps({'bit':str(bit),'sha256':digest,'bundle':str(bundle),'paired_files':len(files),'bundle_sha256':sha(bundle)},ensure_ascii=False,indent=2))
