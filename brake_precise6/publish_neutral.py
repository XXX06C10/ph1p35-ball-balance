"""Publish verified separate K3 AUTO neutral; never program the board."""
from pathlib import Path
import hashlib,json,zipfile,difflib,shutil,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads(read(root/'verification.json'));assert r['status']=='SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_NEUTRAL_TEST'
lineage=json.loads(read(root/'neutral_lineage.json'));archive=Path(lineage['archive']);before=archive/'project'
bit=Path(r['delivery_bit']);digest=sha(bit);assert digest==r['sha256']
assert sha(root/'output/vision_follow_20261022_response.bit')==lineage['old_bit_sha256']
metrics=f"{r['resources']['slice']} Slice，SWNS {r['timing_ns']['SWNS']:+.3f}ns、HWNS {r['timing_ns']['HWNS']:+.3f}ns，STNS/HTNS均0，STA覆盖{r['STA_coverage_percent']:.2f}%"
evidence=root/'evidence/neutral_before';evidence.mkdir(parents=True,exist_ok=True)
for p in (archive/'physical').iterdir():
 if p.is_file():shutil.copy2(p,evidence/p.name)
doc=f'''# VIS5中立位纠偏修正：neutral（2026-10-23）

已完成十二套当前源码仿真、中文面板自检/渲染及完整TD综合布线。**新bit已生成；机械中立位与球回中效果仍待本次实板确认。**

- [新neutral bit]({bit.as_posix()})
- [配套中文面板]({(root/'host/start_panel.cmd').as_posix()})
- [旧response恢复入口]({(archive/'恢复说明.md').as_posix()})

## 这份实板日志发现的问题

`20261023_213642_531.txt`有405条完整记录。实际连续会话156条均视觉有效，无故障、无AB错误；116条目标在±32限幅。末端BX=1672，C=1021，偏差651像素，而DZ仅5；AR=1、T=AT=MT=32、P=31。它不是“已进入死区所以停”。本份日志中DZ始终5、参数SEQ始终0，不能用它比较其他死区设置的效果。

启动K2之前，机构已由用户调到水平、球也在所定中心，日志P却为31、MC=0：之前关使能时调整过机构，重新使能保留了原始编码器参考。K3只更新球中心，没有更新控制中立位。旧AUTO在球居中时给T=0，随后把机构由真实水平P31拉向旧参考0，纠偏范围还固定在旧零点±32。新日志同时确认运行中有手动移动/扶球，故不能把全部往返轨迹归因于自主振荡，不能用来直接整定阻尼。

## 本版修复

**K3在原来的有效新帧、配置完成、无故障、会话/执行器空闲条件下，同时记录两件事：球横坐标中心，以及当前P作为独立的AUTO控制中立位。** K3不请求动作，不重置编码器原点、MC、脉冲历史、保护范围或故障。UART提交与K3冲突时仍由提交优先，忙时K3仍拒绝。

连续目标为：`绝对目标 = clamp(中立位 + 有界PD纠偏量, -60, +60)`。方向反转位只反转纠偏量，不翻转中立位。L仍用编码器计数，在AUTO中表示相对中立位的纠偏幅度；T/AT/MT/P仍是原始编码器参考下的绝对坐标。例：K3中立P31、L32时，居中静止目标31；右侧小偏差目标47、左侧小偏差目标15；最大范围受绝对±60裁剪为约-1～60，不是无限平移保护界限。

K2启动先向执行器提交当前P的同步请求，若已经在位则0脉冲完成，使MT/ME也反映本次参考；随后只有真实有效结果才更新连续纠偏。中立位置不为0时，居中且T/AT/MT/P接近31是正确结果，不应再要求T为0。

K3时若P超出目标允许的±60，中立位不进行8位截断，不清零原点或扩大保护。KC=8表示球中心已记但控制中立越界；RD=0，K2拒绝AJ/RJ=11。需停机后重新建立合适的初始参考，再调平并K3。P±64与故障锁存仍有效，K3不能清除或绕过故障。

## 明确保留的内容

- 方向保持用户确认正确的正常方向；20ms外环、AUTO约20ms/步不变；G3、DZ5、L32、阻尼12、SL8计数/100ms、RU60秒不变。本轮不再用扩大行程、增大PID或新增积分来代替中立基准修复。
- 原运动执行器、编码器、使能模块、配置解析器、检测/视频/ROI、引脚和时钟逐字节保持response版本；只有控制器和K3连接/就绪状态改变。
- F1～F8、单活动段64脉冲/5秒、MC±64净指令、P±64反馈、绝对目标±60、连续到位±1/手动±2均保留；不按帧重置预算。
- 500ms连续短丢保持与200ms断流停止、恢复不自动续跑、K1/K2/K4停止及参数提交取消保持。
- VIS=5、429字节报告、P/V/S格式、长度及XOR不变。不借用原字段伪报中立值；中立位没有新增独立串口字段。面板不再用`|T|>=L`把带偏置的绝对目标误判为相对幅度饱和，只在绝对60边界给出可靠的硬限幅提示。
- 手动模式0及模式2仍以初始软件零点为基准，时长仍约75ms/步；模式2不是回到K3中立。K3记录的控制中立位和初始编码器原点是两件事。

## 实板步骤与预期

1. 停止电机，松开按键，按原成功方法加载本次`neutral.bit`至SRAM。**本次bit已改变。** PH1P35MDG324、接线、000细分和双口STEP/DIR/EN保持。本次未自动下载或写Flash。
2. 打开本工程配套面板，连接原串口。默认仍G3/DZ5/L32/KD12/SL8/60秒，不必继续改小死区。
3. 先将机构调到水平/中立，再把球放实际中心，按K3并等一次回读确认。K1使能就绪后按K2；若K1已经使能且电机空闲，也可直接调平、放球、K3、K2。K3后不要再挪机构；若挪过，停止会话后重新K3。
4. **先看启动：** 球就在中心、机构就在刚才记录的位置时，启动不应再主动把P31拉到0。T/AT/MT应接近K3时的P，ME接近0。无需为了让数字归零而重按或改变编码器参考。
5. **再看纠偏：** 给左右两侧小扰动后松手，观察是否向所定球中心返回。尽量留一段不扶球、不碰机构的记录，才能区分自主控制和手动干预。若明显跑向边缘或反复大摆，K2停止或K4停机，保留日志，不扩大硬保护范围。
6. 断开串口前后都可以用右下角“复制日志路径”定位新记录；日志自动保存在`host/logs/`。本轮首先验证基准修复，之后才根据无手动干预的数据决定阻尼、力度或摩擦补偿。
7. 若需要回初始P=0，须明确选择模式2并应用、再K2；这可能与当前机械水平不同。丢球、故障和K4后不会自动回任何参考。中立与视觉中心都不是断电保存的机械标定。

## 验证结果

新增回归完整重现：先使能建立原始参考，关闭使能后用真实AB把位置移到+31/-31，重新使能保留旧原点，K3记录当前位置；居中K2启动300ms不发STEP。随后验证相对±16、相对±32、绝对60裁剪、回到中立、反向位只翻转纠偏量、L0/L1、忙时K3、重复空闲K3、K2/K4、原点和MC保留。±63用真实AB验证KC8/RD0/AJ11，无动作、不包装截断。实际UART的P/T/AT/MT为±31、ME=0、MC/TS=0，帧长仍429。

原十一套回归全部重跑：八类故障与快速AUTO保护、手动±60/0、真实1.28计数/脉冲与6/12ms延迟、500/200ms边界、配置/取消/按键、相机I2C/ROI、真实RGB检测和全720p链路、三种假设球模型、20ms提速及UART兼容。模型通过不代表这套真实机构已精密回中；这次实板日志手动干预的轨迹不作精度验收。

完整构建：{metrics}。原器件、全部引脚、双口输出及约束通过，未放宽时钟或增加假路径。源码/bit配套见`verification.json`、`build_sources.json`、`delivery_manifest.json`。

首次布线发现PD乘法、取整、中立位相加与缓变串在同周期，建立时序差0.023ns；该次bit被构建门禁拒绝，未交付。加入一级50MHz目标流水，将PD/中立运算与缓变分开；有效标记在丢球/改参/K3时清除，避免旧目标释放。重跑全部回归后再完整构建，时钟和约束未改。失败路径记录保存在`evidence/neutral_timing_attempt1/`。

归档旧response源码在同一个真实AB回归中明确复现“P31但T/AT0”，修正版同场景通过。`before_neutral.log`中的FATAL是刻意复现旧缺陷的预期失败，不是本次十二套回归失败。

新bit SHA256：`{digest}`。

## 恢复与开发入口

旧response bit SHA256：`{lineage['old_bit_sha256']}`，保留于`output/vision_follow_20261022_response.bit`；源码、面板、本次实板日志与人工确认已归档，上方有恢复入口。原loss500 bit也保留。恢复开发时复制归档project内容到独立、名为vision_follow_20261022的目录，勿直接改归档。

重建`build.ps1`；验证`python verify.py`；发布只用`python publish_neutral.py`。旧发布脚本是历史版本，不用于当前交付。
'''
for name in ['测试说明.md','实现与协议.md']:(root/name).write_text(doc,encoding='utf-8')
(root/'README.md').write_text(f'# VIS5 neutral：连续控制中立位修正\n\n[新bit]({bit.as_posix()}) · [配套面板]({(root/"host/start_panel.cmd").as_posix()}) · [测试与恢复]({(root/"测试说明.md").as_posix()})\n\nK3现在同时记录球中心与独立AUTO中立位。连续目标围绕这个位置，编码器原点/MC/硬保护不改。VIS5/P/V/S/429字节、方向、response节奏和全部保护保留。手动/模式2仍基于初始软件零点。十二套仿真和完整布线通过，实板新中立位回中待验证。{metrics}。\n\nSHA256 `{digest}`。仅使用publish_neutral.py发布。\n',encoding='utf-8')
source_paths=[]
for folder,pattern in [('rtl','*.v'),('host','*.ps1'),('sim','*.v')]:source_paths+=list((root/folder).glob(pattern))
source_paths+=list(root.glob('*.py'))+list(root.glob('*.ps1'))
changed=[p.relative_to(root).as_posix() for p in sorted(set(source_paths)) if not (before/p.relative_to(root)).exists() or sha(p)!=sha(before/p.relative_to(root))]
(root/'neutral_changed_files.json').write_text(json.dumps({'source_files_changed_or_added':changed},ensure_ascii=False,indent=2),encoding='utf-8')
diff=[]
for rel in changed:
 old=read(before/rel) if (before/rel).exists() else ''
 diff.extend(difflib.unified_diff(old.splitlines(True),read(root/rel).splitlines(True),fromfile='response/'+rel,tofile='neutral/'+rel))
(root/'neutral_changes.diff').write_text(''.join(diff),encoding='utf-8')
(root/'改动清单_neutral.md').write_text('RTL：vision_follow_control.v新增K3控制中立、相对纠偏→绝对目标裁剪、无动作的启动目标同步及中立越界拒绝；vision_monitor.v只连接K3采样并反馈KC8/RD；vision_monitor_all.v重生成。执行器、编码器、解析器、相机、引脚、时钟均不改。\n\n面板：解释两种参考和相对L/绝对T，增加越界映射，删除不可靠的|T|>=L饱和推断。协议函数和解析器不改。新增tb_neutral及精确合同/归档/发布脚本，原直接控制器测试显式连接neutral_capture=0；验证脚本保留全部核对并增加非零中立回归。完整清单neutral_changed_files.json，差异neutral_changes.diff。',encoding='utf-8')
(root/'output/neutral_sha256.txt').write_text(digest+'  '+bit.name+'\n',encoding='ascii')
contract=json.loads(read(root/'baseline_contract.json'));contract.update(status=r['status'],next_milestone='physical neutral reference and unassisted ball-center recovery with new capture')
(root/'baseline_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
agent=root/'AGENTS.md';s=read(agent)
if not s.startswith('# neutral delivery status'):
 agent.write_text(f'# neutral delivery status (2026-10-23)\n\nCurrent bit output/{bit.name} SHA256 `{digest}`. Twelve suites including trueAB disabled-move/re-enable P±31,K3 neutral and centered0STEP/429byte targets,relative±16/32,hard60,invalid±63 KC8/RD0/AJ11,all previous response/RGB/loss/guards and full routing pass. {metrics}. Core/encoder/origin/MC/parser/camera/pins/clocks exact response baseline. K3 adds separate AUTO neutral, not encoder rebase. L relative in AUTO; T/AT/MT/P absolute. Mode0/2 retain initial-reference semantics. New physical neutral response pending; old trace has manual intervention and cannot certify dynamics. Only publish_neutral.py current; no auto-download/Flash. neutral_lineage immutable.\n\n'+s,encoding='utf-8')
progress=root.parent/'D36A_STEPPER_调试进度总结.md'
if 'VIS5 neutral中立位修正交付' not in read(progress):
 with progress.open('a',encoding='utf-8') as f:f.write(f'\n\n## 2026-10-23 VIS5 neutral中立位修正交付\n\n用户日志405条，机械已调平对应P31、MC0，旧AUTO居中目标0；末端651像素误差但目标32限幅，无故障。用户确认中途有手动干预，不能由往返轨迹整定PID。K3新增独立AUTO中立采样，原点/MC/硬保护保持；T等绝对、L相对中立。十二套回归及完整构建通过：{metrics}。新bit `{digest}`，[步骤与恢复]({(root/"测试说明.md").as_posix()})。新实板回中待确认，未自动烧录。\n')
(look/'下一步_连续视觉闭环.md').write_text(f'# 当前交付：VIS5 neutral中立位纠偏\n\n[新bit]({bit.as_posix()}) · [面板]({(root/"host/start_panel.cmd").as_posix()}) · [步骤与恢复]({(root/"测试说明.md").as_posix()})\n\n先调平、放球，再K3记录视觉中心与AUTO中立，K1就绪后K2。围绕K3位置控制，旧编码器原点及保护不改；协议/方向/速度保持。十二套回归和布线通过，实板效果待确认。{metrics}。SHA256 `{digest}`。\n',encoding='utf-8')
files=[]
for folder in ['rtl','user_source','host','sim','td_project','evidence']:
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
bundle=look/'VIS5_中立位纠偏_neutral_20261023.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files+[root/'delivery_manifest.json']:z.write(p,p.relative_to(root).as_posix())
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None
 for rel,h in manifest['files'].items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,rel
print(json.dumps({'bit':str(bit),'sha256':digest,'bundle':str(bundle),'paired_files':len(files),'bundle_sha256':sha(bundle)},ensure_ascii=False,indent=2))
