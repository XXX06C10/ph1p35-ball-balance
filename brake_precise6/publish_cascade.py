"""Publish the verified cascade package; never open a serial port or program hardware."""
from pathlib import Path
import hashlib,json,shutil,zipfile,difflib,sys
sys.stdout.reconfigure(encoding='utf-8')
r=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads(read(r/'verification.json'));assert v['status']=='SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_CASCADE_CALIBRATION'
bit=Path(v['delivery_bit']);assert sha(bit)==v['sha256'];digest=v['sha256']
lineage=json.loads(read(r/'cascade_lineage.json'));old=Path(lineage['archive']);before=old/'project'
assert sha(r/'output/vision_follow_20261022_neutral.bit')==lineage['old_bit_sha256']
metrics=f"{v['resources']['slice']}/21216 Slice，{v['resources']['DSP']}/40 DSP，SWNS {v['timing_ns']['SWNS']:+.3f}ns / HWNS {v['timing_ns']['HWNS']:+.3f}ns，STNS/HTNS均0，STA覆盖{v['STA_coverage_percent']:.2f}%"
hold=look/'交付_20261024_保护保持锁定'
refs=[Path('D:/AAAProject/TI123/B站 球杆平衡系统2026.07.29/球杆平衡控制系统/WHEELTEC_APP/RobotControl_task.c'),Path('D:/AAAProject/TI123/ballance-ball/System/System.c')]
lineage['algorithm_references']={str(p):sha(p) for p in refs};lineage['reference_role']='algorithm references only; motor origin/IO/guards follow passed FPGA lineage';lineage['hold_release']=str(hold)
(r/'cascade_lineage.json').write_text(json.dumps(lineage,ensure_ascii=False,indent=2),encoding='utf-8')
e=r/'evidence/cascade_before';e.mkdir(parents=True,exist_ok=True)
for p in (old/'physical').iterdir():
 if p.is_file():shutil.copy2(p,e/p.name)
guide=f'''# 串级标定版 cascade：首次实板步骤（2026-10-24）

**本次bit已经修改并重新构建。软件验证完成；还没有这套真实机构的新标定数据，不宣称已经实板稳球成功。**

- [新bit]({bit.as_posix()})
- [配套中文面板]({(r/'host/start_panel.cmd').as_posix()})
- [旧neutral恢复说明]({(old/'恢复说明.md').as_posix()})
- [仅保持锁定版本]({(hold/'使用说明.md').as_posix()})

## 先解决原先的自行松开

新日志20261023_224008_535.txt约运行8秒出现F5/SP64/EN0；用户确认没有手动转动，是失去使能后机构掉落。旧软件在故障时停止STEP并释放EN。新版F1～F8仍锁存、仍停止发步，但**保留此前已经建立的通电锁定**。K1可释放，故障中不能再开启；K4、复位、加载bit或断电仍会释放。因此加载/重新加载前先支撑机构。通电锁定不能替代断电时的机械支撑。

K2停止、丢球、参数变化或会话时限到达只停步保持，不自动回零、不自动续跑。F1～F8仍须重新加载才能清除。故障不是通过应用参数或反复按K1清除的。

## 本次从这里开始

1. 支撑机构，按原成功方法加载`vision_follow_20261022_cascade.bit`至SRAM，打开配套`host/start_panel.cmd`。器件PH1P35MDG324、全部接线、000细分不变。本次未自动下载或写Flash。
2. 连接串口115200/8N1。曝光3600、增益143、蓝框调节保留。先保持死区5、限幅32。先将机构调平，再把球放实际中心，按K3记录球中心/机构中立，K1使能。K3不重置编码器原点或MC。
3. 新bit默认等待标定，直接K2不会开启连续控制，可能显示拒绝12。这是预期状态；先进入左侧“标定 / 新串级”。只有收到匹配D1配置确认后才按K2。
4. 点“① 电机标定50Hz/±8”，等配置确认，再按一次板上K2。测试有限执行`中立→+8→中立→−8→中立`，到位允许±2计数，每段250ms检查，完成即停并保持使能。球可以在K3后移开；不碰转轴或机构。主要看P、标定状态和故障，不要求肉眼看清小转角。
5. ①通过且无故障后，可依次做②100Hz/±16、③200Hz/±16。每次均需选择、回读、再K2，程序不会自行升级。任一步失败便停下保留日志；软件超时终止不会自动重复。至少完成一次成功的电机标定，拟合才会接纳相应频率。
6. 重新把球放中心，必要时停止/关闭使能后重新调平并K3，再K1；此后不要再碰机构。点“④ 球响应±4”，回读后K2。程序正反各三次：中立200ms、+4保持250ms、中立300ms、−4保持250ms、中立300ms。丢失真实识别、接近ROI边缘、限位或其他异常都会终止，不自动回中；不是拿旧坐标伪造测量。
7. 标定结束、AR=0后点“⑤ 分析当前日志”。电脑在后台拟合方向、增益、偏置和延迟，再搜索有限参数，串口继续记录。完整三次试验、方向/增益重复性与交叉验证R²≥0.70不满足时拒绝生成参数；信号太弱时可在无故障下改用±8重复球标定。**分析不会自动运动或自动应用参数。**
8. 显示合格参数后，点“⑥ 应用”，等回读，再K2开始连续稳球。保持死区5/限幅32；若曾改动，界面会填回默认值并要求先在“闭环控制”页应用确认。新控制不使用旧G/KD来调力度，标定页运行时相应旧控件禁用；限幅、中心与相机功能仍保留。
9. 先给左右小扰动并松手。验收目标：5秒内误差进入±max(死区,10串口像素)、球速≤15像素/秒，再保持10秒；左右各三次。左侧“球已稳定3秒”与电机到位分开显示，控制不会因到位而关闭。该指标是本轮目标，尚未以实板日志通过；像素也不是毫米。
10. 测试后点“复制日志路径”。保留同名`.txt`和`.commands.jsonl`两份文件，自动分析结果为`.cascade.json`。前者包含真实VIS5/D1测量，后者记录配置与频率资格；缺少匹配配置记录时不会擅自推测频率。异常先用K2停步保持；使用K1/K4释放前注意机构支撑。

## 重要状态

- 标定状态1=运行，2=有限试验完成，4=终止；“完成电机标定”不等于“球已稳定”。
- K3中立可以是P31或−31，T/AT/P不必归零。中立超过±60或标定幅度碰到绝对边界会拒绝，不偷偷重置原点或扩大行程。
- 新bit默认连续会话时限0（不限）；用户选择的有限时长仍可用。单活动段64脉冲/5秒、MC±64、P±64、绝对目标±60不变，真正静止到位100ms才结束活动段，不能每帧刷新预算。
- 手动单次及回初始软件零点保留原约75ms/步时序。回初始P0不是回K3中立，更不是机械回零。需要旧连续算法时有明确的“切回旧控制”按钮。
- 相机配置、P/V/S报文和429字节VIS5不变。新增C配置及94字节D1诊断；旧bit不会确认这些新配置，不能仅凭VIS=5判断固件正确。

## 验证与恢复

18套当前RTL仿真、7项上位机拟合/协议测试、中文面板SelfTest/SmokeTest以及完整综合布线通过。涵盖新快速路径八类故障、真实1.28计数/脉冲AB及6/12ms延迟、±31中立、C/K3同拍优先、有限标定、500/200ms保护、RGB全链路、完整429/94字节UART。三种独立假设球模型在真实RTL中通过5秒恢复及扰动后10秒保持；它们不是实测机构参数。

构建结果：{metrics}。没有放宽时钟或增加假路径；完整报告在`verification.json`。

本版SHA256：`{digest}`。

旧neutral SHA256：`{lineage['old_bit_sha256']}`，仍保留在`output/vision_follow_20261022_neutral.bit`及归档。旧版故障会释放，恢复前同样支撑机构。保持锁定单独版本SHA256：`225207c02be42f3aa150e7891321ce4103ac08594c24143696dee8b9906d5a0f`。

开发入口：`build.ps1 -Release cascade`、`run_sim.ps1`、`python verify.py`、`python publish_cascade.py`。历史发布脚本不用于本版。若模型方向/增益不可重复或没有合格参数，保留拒绝结果，检查传动/杆角度代理；不以扩大保护范围代替排查。
'''
(r/'测试说明.md').write_text(guide,encoding='utf-8')
tech=f'''# cascade实现与接口

## 控制与安全

参考TI123中WHEELTEC的位置外环/角度内环思路，不照搬毫米/ADC/Hz系数；舵机ballance-ball仅作参考。电机GPIO、编码器原点、MC、手动序列与保护来自历次实板通过的FPGA脚本。当前摄像头/ISP/检测、曝光增益、ROI、全部引脚和时钟逐字节保留；顶层只显式更改启动默认RU0和未标定串级模式。

外环按真实帧时间使用alpha-beta位置/速度观察器（alpha1/2、beta1/16）。>32像素创新重新建立速度基准，D项3px/s噪声带，中心死区不关闭高速制动。保留VIS5中VE的Q4像素/帧含义，D1另报Q4像素/秒。P/D、偏置、积分、相对限幅、中立相加及绝对限幅分12级流水；0.24微秒运算不改变50MHz约束。积分只在有效、低速、未饱和时更新，限±4计数；与偏置合计限±8，再受相对L和绝对60限制。短丢冻结参考，恢复重建速度，连续500ms无有效球或200ms断流停止。

5ms内环采用位置反馈及参考速度前馈；已发指令按实测1.28计数/脉冲作最长20ms的有界预测，静止后回到真实编码器校正。预测不重置实际P/MC，不代替F1～F8。进入0.5计数停步带，超过0.75计数才重新启动，小于5Hz指令停发、需要运行时最低20Hz，最大只允许已测试的50/100/200Hz。方向改变时准备5ms；保留STEP高/低各至少2.5ms，20ms物理响应窗口检查实际编码器。无反馈最少3个指令脉冲并满足响应等待，反向反馈仍两次观察锁存。单段64脉冲/5秒和净MC/P64保留；转向/改目标/短丢不刷新它们。静止100ms内目标只在到位带轻微变化，不再错误清掉静止计时。

生产启动是未标定串级：无合格C配置不能K2启动。修改P/V/S、K3或相机等待会撤销模型就绪，需要重新确认；恢复识别与重新使能不会自动续跑。故障只停步、保留已建立锁定，不能让原来未使能的电机自动通电；K1故障时只允许释放，K4/复位释放。

## C01配置：新增，不修改P/V/S

`C`后按下列顺序编码为大端HEX，最后XOR8和LF。25字节数据加1字节XOR，线上共54字节。XOR覆盖数据字节，不含C和LF，只有完整LF和全部范围通过才原子提交。100ms超时，非行首C不接纳。

|字段|字节|单位与限制|
|---|---:|---|
|version|1|固定1|
|sequence|2|0..65535，D1回读|
|selection|1|0旧控制，1整定串级，2电机标定，3球标定|
|diagnostics|1|0/1，20ms诊断机会|
|kp|2|无符号Q12，计数/像素，0..16384|
|kv|2|无符号Q8，计数/(像素/秒)，0..2048|
|ki|2|无符号Q16，计数/(像素·秒)，0..3277|
|bias|2|有符号Q8计数，±2048原始值|
|inner_kp|2|无符号Q8 Hz/计数，256..32768|
|feedforward|2|无符号Q8 Hz/(计数/秒)，0..256；默认200即0.78125|
|max_hz|2|只接纳50、100、200|
|delay_ms|1|0..120|
|amplitude|1|电机4/8/16，球4/8|
|slew_rate|2|8..256计数/秒，定点步进有小量量化误差|
|polarity|1|0表示正P使球向负X加速，1相反；由标定决定|
|reserved|1|固定0|
|XOR|1|以上25字节异或|

P/V/S及旧HEX校验、范围和字段含义不变；C只配置/选择有限动作，物理K2才启动。新旧解析器按整行隔离，串口提交优先于K3。

## D1诊断

字段顺序/位宽以`diagnostic_schema.json`为准：D1前缀、44字节数据的HEX、XOR8的HEX、CRLF，共94字节。含FPGA毫秒时间、真实帧时间、C序号、选择、标志、标定阶段/状态、球X/中心、实际P、Q8参考、Q4像素/秒速度、带符号Hz、故障、段脉冲、MC、帧号、中立、C错误计数。标志位0=原点有效、1=实际EN、2=会话、3=真实视觉有效、4=过期、5=球稳定、6=执行器忙、7=K3确认、8=模型就绪。

唯一TX通过包级仲裁输出VIS5与D1，不拼接半行。最坏名义流量429×4+94×50=6416字节/秒，小于115200/10；VIS整包期间D1采样机会合并，不积压追发。主机使用帧时间和去重后的真实坐标拟合，不拿重复诊断当作新相机帧。

## 自动整定

以三次连续有限轨迹拟合`x''=b(P-N)+d-c·x'`：积分位置模型避免对像素两次差分，不给每圈虚构独立速度重置。阻尼与0..120ms延迟联合搜索（2ms网格），留一圈交叉验证最低R²≥0.70，正反增益重复性0.5..2倍且同号，开始速度超过30px/s拒绝。只使用最新完整且未故障的球标定；最后一次中止不能悄悄退回老成功数据。只选择有配套命令元数据且电机标定完成的频率。

从模型求有限P、速度阻尼和静态补偿，离线搜索自然频率/阻尼组合；含帧率、增益、延迟、量化与间隙模型变化。没有合格候选就输出拒绝结果。参数只在人工点击应用后提交，K2仍是运动入口；默认以DZ5/L32验算。PC不承担实时控制，分析无numpy等外部依赖。模型通过不是实板验收。

## 验证记录

18套RTL、7项主机测试、面板SelfTest/SmokeTest及完整TD通过。{metrics}。初版占满40DSP且出现较大建立路径压力，已停止交付；通过窄位宽/分级流水减到35DSP并重新布线。失败尝试资料在`evidence/cascade_attempt1/`，当前bit哈希`{digest}`。当前实板模型/稳球验收待新日志；未自动烧录。
'''
(r/'实现与协议.md').write_text(tech,encoding='utf-8')
(r/'README.md').write_text(f'''# VIS5 cascade：保护保持、有限标定和串级稳球

[新bit]({bit.as_posix()}) · [配套面板]({(r/'host/start_panel.cmd').as_posix()}) · [首次测试与恢复]({(r/'测试说明.md').as_posix()})

已生成新bit，18套RTL/7项主机测试及完整布线通过；实际机构标定与稳球效果待新实板数据。先按测试说明完成K3/K1、电机50Hz有限标定，再做球响应与自动整定。配置不启动运动，只有板上K2启动。故障停STEP并保持已建立EN，K4/复位释放。

{metrics}。SHA256 `{digest}`。

当前发布仅使用publish_cascade.py；历史脚本是旧版本。保留旧neutral与独立hold恢复包，不自动烧录。
''',encoding='utf-8')
changed=[];source_paths=list((r/'rtl').glob('*.v'))+list((r/'host').glob('*.ps1'))+list((r/'host').glob('*.py'))+list((r/'sim').glob('*.v'))+list((r/'sim').glob('*.py'))+list(r.glob('*.py'))+list(r.glob('*.ps1'))+[r/'user_source/hdl_source/design_top_wrapper.v']
diff=[]
for p in sorted(set(source_paths)):
 rel=p.relative_to(r).as_posix();q=before/rel
 if not q.exists() or sha(p)!=sha(q):
  changed.append(rel);diff.extend(difflib.unified_diff(read(q).splitlines(True) if q.exists() else [],read(p).splitlines(True),fromfile='neutral/'+rel,tofile='cascade/'+rel))
(r/'cascade_changes.diff').write_text(''.join(diff),encoding='utf-8')
(r/'cascade_changed_files.json').write_text(json.dumps({'source_changes':changed},ensure_ascii=False,indent=2),encoding='utf-8')
(r/'改动清单_cascade.md').write_text('# cascade改动清单\n\n'+''.join('- '+p+'\n' for p in changed)+'\n新增C/D1、观察器/内环/有限标定、主机拟合和验证。既有P/V/S、VIS5字节函数、手动FSM、编码器原点、相机/检测/IP、引脚/时钟均有静态冻结检查。完整差异见cascade_changes.diff。\n',encoding='utf-8')
(r/'output/cascade_sha256.txt').write_text(digest+'  vision_follow_20261022_cascade.bit\n',encoding='ascii')
a=r/'AGENTS.md';s=read(a)
if not s.startswith('# cascade delivery status'):
 a.write_text(f'# cascade delivery status (2026-10-24)\n\nCurrent bit output/vision_follow_20261022_cascade.bit SHA256 `{digest}`. 18current-source suites,7host tests,actual94/429UART,all8fast/hold guards,6/12msAB,nonzero31/-31,camera/RGB and full routing pass. {metrics}. C01/D1 additive;PVS/VIS5 serializer/manual FSM/camera/pins/clocks frozen. Faults stopSTEP/retain establishedEN;K1release-only,K4/reset release. Production RU0/defaultunqualifiedCASCADE1;no automatic motion or restart. PhysicalK2 calibration/model/centering still pending. Only publish_cascade.py current;old publishers historical. cascade_lineage/hold release immutable. No automatic programming.\n\n'+s,encoding='utf-8')
p=r/'baseline_contract.json';b=json.loads(read(p));b['status']=v['status'];p.write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf-8')
progress=r.parent/'D36A_STEPPER_调试进度总结.md'
if progress.exists() and '20261024_cascade' not in read(progress):
 with progress.open('a',encoding='utf-8') as f:f.write(f'\n\n## 20261024_cascade：保护保持与串级标定\n\n用户确认F5失能后机构自行下落。已交付故障停步保留锁定、物理K2有限标定/串级方案，18套RTL和7项主机测试及布线通过。bit SHA256 {digest}。实板标定和稳球待新日志，不将三种假设模型通过视为实际成功。入口：{r}/测试说明.md。\n')
(look/'下一步_连续视觉闭环.md').write_text('# 当前入口：cascade（2026-10-24）\n\n'+f'[新测试与恢复]({(r/'测试说明.md').as_posix()})\n\n软件/bit已完成，下一步由板上K2完成有限电机及球标定。参数尚非实际机构标定结果，不宣称已实板稳球。\n',encoding='utf-8')
# Freeze paired source,host,bit and evidence. Exclude live captures and regenerable executables/snapshots.
paths=set()
for folder in ['rtl','user_source','td_project','host','sim','evidence']:
 for p in (r/folder).rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(r).as_posix()
  if '/__pycache__/' in rel or rel.startswith('host/logs/') or p.suffix.lower() in ['.vvp','.vcd','.pyc','.db'] or p.name.endswith('.combined.v') or '_runner' in p.name or p.name.startswith('synthetic_'):continue
  if folder=='td_project' and p.suffix not in ['.al','.sdc']:continue
  paths.add(p)
for p in r.iterdir():
 if p.is_file() and (p.suffix.lower() in ['.py','.ps1','.tcl','.md','.json'] or p.name in ['build.log','routed_netlist.v','cascade_changes.diff']):paths.add(p)
for p in (r/'output').iterdir():
 if p.is_file() and p.suffix in ['.bit','.txt']:paths.add(p)
for pattern in ['*.area','*.ts','*_pr.timing']:
 paths.update(run for run in (r/f'{r.name}_Runs/phy_1').glob(pattern) if run.is_file())
paths.discard(r/'delivery_manifest.json')
manifest={p.relative_to(r).as_posix():sha(p) for p in sorted(paths)}
(r/'delivery_manifest.json').write_text(json.dumps({'status':v['status'],'bit':'output/vision_follow_20261022_cascade.bit','bit_sha256':digest,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
bundle=look/'VIS5_串级标定_cascade_20261024.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for rel in manifest:z.write(r/rel,rel)
 z.write(r/'delivery_manifest.json','delivery_manifest.json')
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None
 for rel,h in manifest.items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,rel
print(json.dumps({'bit':str(bit),'sha256':digest,'bundle':str(bundle),'bundle_sha256':sha(bundle),'paired_files':len(manifest)},ensure_ascii=False,indent=2))
