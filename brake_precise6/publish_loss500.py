"""Publish verified VIS5 loss tolerance and paired host; never program hardware."""
from pathlib import Path
import hashlib,json,zipfile,difflib,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere');base=root.as_posix()
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads(read(root/'verification.json'));assert r['status']=='SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_LOSS500_TEST'
lineage=json.loads(read(root/'loss500_lineage.json'));archive=Path(lineage['archive']);before=archive/'project'
bit=Path(r['delivery_bit']);digest=r['sha256'];assert sha(bit)==digest
(root/'output/loss500_sha256.txt').write_text(digest+'  '+bit.name+'\n',encoding='ascii')
res=r['resources'];t=r['timing_ns']
metrics=f"{res['slice']} Slice、{res['register']}寄存器、{res['IO']} IO、{res['DSP']} DSP、{res['ERAM']} ERAM；SWNS {t['SWNS']:+.3f}ns、HWNS {t['HWNS']:+.3f}ns，STNS/HTNS 0，STA覆盖{r['STA_coverage_percent']:.2f}%"
links=f'''- [新bit：loss500]({bit.as_posix()})
- [配套中文面板]({base}/host/start_panel.cmd)
- [恢复修改前VIS5]({archive.as_posix()}/恢复说明.md)
'''
doc=f'''# VIS5短丢容忍：局部续检＋500ms连续控制保持

2026-10-22，已按选定方案完成软件和完整布线验证；**新bit已生成，实板恢复效果和背景误识别率待本轮日志确认**。

{links}
## 实际阈值与行为

当前顶层`COLOR_MODE=1`识别红色优势，`Y_THRESHOLD=200`亮度分支没有启用，本轮未改它。真实生效的参数为：

| 项目 | 本版值 |
|---|---|
| 全ROI获取 | R≥45，R>2G、R>2B |
| 已确认球附近局部跟踪 | R≥35，2R>3G、2R>3B（比例严格大于1.5） |
| 弱阈值范围 | 最后有效球中心X/Y各±48传感器像素，裁剪到ROI和画面 |
| 局部续检历史 | 连续1～2个无效帧保留；第3帧撤销，恢复全ROI两帧确认 |
| 连续AUTO有效球保持 | 最后真正有效球结果起500ms，约15帧；以时间为准 |
| 相机结果断流 | 最后任意结果起200ms停止，保持原保护 |

局部位置使用实际球中心，未使用蓝框中心或放大的显示框。像素局部计数独立处理行末5/5/6拼包边界；显示流水不改。弱红色不能在没有已确认历史时直接获取球。面积、形状、主区域占比、跳变、置信度等原判据保留。短丢期间不伪造有效识别。

只有已经启动的连续模式享受500ms保持：AR=1、V=0时，T/AT冻结，电机继续向最后有效参考到位；不使用无效坐标更新控制。恢复第一帧重建速度基准，避免速度尖峰，然后仍经原缓变限制更新。持续无效到500ms为SR3，断流到200ms为SR4，停止后恢复也不会自动续跑。

## 本轮实板步骤

1. 停止电机、松开按键，按原成功方法将上面的`loss500.bit`加载SRAM，器件仍为PH1P35MDG324。原接线与000拨码保持，不需要补接PWM/Z。本轮未自动下载、未写Flash。
2. 关闭旧串口程序，启动本工程中文面板，连接原COM，115200/8N1；协议仍VIS=5。默认曝光3600、传感器增益143、G4/L12、阻尼12、缓变2计数/100ms、会话30秒保持。
3. 机构先放在希望的软件参考位置；球放实际中心，K3确认CZ=1，K1使能就绪，再K2启动。仍按此前方向：电机向下→球向右；P方向按日志默认，可在停止后反转配置。
4. 先保持原照明和蓝框，做一次30秒连续测试。偶发短丢应可看到“短丢保持，最长500ms”，V/Q仍反映真实结果，AR不掉到0，T/AT保持。恢复后继续控制，无需重按K2。不要把单条V0当作新故障，也不要要求每次短丢都恰好被250ms串口报告采到。
5. 做一次持续离开识别区的测试，应在最后有效球结果起约500ms停止（SR3）。将球移回也不自动启动，须新的K2。遮挡与离开蓝框都会使视觉无效；真实相机断流仍200ms停止（SR4），这项已仿真，无需为了本轮重复拆线。
6. 短丢期间再按K2也应停止并保持使能（SR7）；K4直接关闭使能。改参数仍立即取消，不延迟500ms。K3、初次K2、单次模式0和返回模式2仍要求真实有效新结果，不接受历史保持坐标。

## 看日志判断

429字节VIS5格式、P20字节/V32字节/S18字节与XOR均不变。V/Q/B/AGE保留原语义：AGE是任意检测结果的帧龄，不是最后有效球的年龄。短丢时V0/AR1且T/AT非零是正常保持；SR记录会话停止原因。面板误差曲线留缺口，统计只用真正有效结果。

连接自动保存到`host/logs/`。测试后在工程目录运行`python analyze_follow.py`分析最新日志，或直接发新日志。比较SR3误停次数、连续AR运行长度、有效报告占比以及有效样本的偏差RMS。当前会话仍默认30秒，SR8是正常到时停止；修改时限使用原运行设置，0可持续运行。

## 保留的保护与验证结果

F1～F8、单活动段64脉冲/5秒、MC±64净指令脉冲、P±64反馈计数、到位带连续±1/手动±2及所有限幅不改。短丢不会暂停会话计时、重置脉冲预算或动作超时。原运动执行器源码逐字节核对不变。丢球停止不回零、不续跑，K3不重置编码器参考或清除故障。

十套仿真全部通过：原八类故障、±60/0、真实AB反馈、中心/取消/停止、相机I2C/ROI跨域、完整720p二值检测、连续会话及三种假设模型；新增真实1280×720 RGB→实际阈值→局部恢复→CDC→AUTO/1.28AB，以及500ms/200ms精确边界和真实429字节保持状态串口波形。RGB另有2560像素阈值/比例/±48邻域/ROI跨行边界测试，覆盖白色/暗背景和稀疏红噪声。

RGB仿真保留实际像素分类和视频流水，以及实际stream_bbox；只排除原模块内所有输出均未接线、TD也会裁剪的旧CCL诊断尾段。生产源码该尾段未改，校验器核对实际RGB前缀和bbox源码，未用二值掩码替代新阈值测试。

完整TD构建：{metrics}。器件、全部引脚和双口STEP/DIR/EN、原时钟与CDC约束、源码和bit一致性均通过；未放宽时钟。中文启动器SelfTest/SmokeTest和保持状态渲染通过。详见[verification.json]({base}/verification.json)。

新bit SHA256：`{digest}`。

修改前bit SHA256：`{lineage['old_bit_sha256']}`，已完整归档源码、面板、报告、实测日志与哈希。恢复源码和上位机时，先将归档project复制到独立工作目录，归档本身只读保存。恢复入口见上方。本版模型/布线通过不替代真实光照和机构稳定性验收。
'''
(root/'测试说明.md').write_text(doc,encoding='utf-8')
(root/'README.md').write_text(f'''# VIS5 loss500：局部续检与短丢保持

当前交付已更新为loss500。保持当前红色识别，全ROI45/比例2，局部35/比例1.5、球中心±48传感器像素，2帧恢复历史；仅已启动连续控制容忍最后有效结果500ms，断流200ms。原单次/返回/K3/启动与运动保护保持严格。

{links}
- [本轮步骤和现象]({base}/测试说明.md)
- [修改清单]({base}/改动清单_loss500.md)

默认K3定中心→K1使能→K2连续启动/停止，K4立即停机。曝光3600/增益143，G4/L12/KD12/缓变2/会话30秒保持。VIS5和P/V/S协议格式不变；短丢允许V0/AR1和非零历史T/AT，面板明确显示保持。

十套仿真、中文面板与完整布线验证通过：{metrics}。实板短丢恢复与误识别率待确认。SHA256 `{digest}`。

重建`./build.ps1`，完整验证`python verify.py`，发布`python publish_loss500.py`。仿真仍用`./run_sim.ps1 tb_名称`，新增tb_loss、tb_rgb。只使用当前发布脚本，旧迁移/发布脚本是历史溯源。面板自检`host/start_panel.cmd -SelfTest`、`-SmokeTest`；自动日志统计`python analyze_follow.py`。
''',encoding='utf-8')
(root/'实现与协议.md').write_text(doc,encoding='utf-8')
sources=['user_source/hdl_source/steel_ball_detect.v','user_source/hdl_source/steel_ball_stream_bbox.v','user_source/hdl_source/design_top_wrapper.v',
 'rtl/vision_result_guard.v','rtl/vision_follow_control.v','rtl/vision_monitor.v','compose.py','host/vision_panel_cn.ps1','decode_serial.py',
 'run_sim.ps1','build.ps1','verify.py','sim/tb_detector.v','sim/tb_follow.v','sim/tb_loss.v','sim/tb_rgb.v']
diffs=[]
for rel in sources:
    old=read(before/rel) if (before/rel).exists() else ''
    diffs.append(''.join(difflib.unified_diff(old.splitlines(True),read(root/rel).splitlines(True),fromfile='before/'+rel,tofile='loss500/'+rel)))
(root/'loss500_changes.diff').write_text(''.join(diffs),encoding='utf-8')
(root/'改动清单_loss500.md').write_text('''# loss500修改清单

像素检测：steel_ball_detect.v增加局部弱红色判据和独立换行坐标；steel_ball_stream_bbox.v增加2帧跟踪历史；design_top_wrapper.v连接真实跟踪中心。

控制：新增vision_result_guard.v的500ms有效球计时；vision_follow_control.v冻结AT/T、恢复重建速度、保持会话计时；vision_monitor.v统一执行器/会话许可，原始V/Q/B/AGE及严格启动/K3保留。compose.py包含新模块。

上位机vision_panel_cn.ps1显示短丢保持并增加自检；decode_serial.py区分保持与错误非零目标。analyze_follow.py未改变有效样本口径。

测试：新增tb_loss.v和tb_rgb.v；tb_follow.v延长持续无效测试并连接新门控端口；tb_detector.v更新短丢快速恢复预期；run_sim.ps1加入两套测试及无缓冲日志。

构建与核对：build.ps1产生loss500交付副本；verify.py保留基线和所有器件/引脚/时序检查，检测路径仅放行三份明确文件，新增真实RGB与保持波形检查。新增prepare_loss500.py、publish_loss500.py及loss500_lineage.json。

原运动核心vision_servo_core.v、vision_move_core.v、enable_latch.v、encoder_ab_counter.v、vision_shadow_target.v、vision_config_rx.v、vision_report_tx.v、UART生成器、P/V/S格式、ADC/SDC及器件工程文件保持逐字节不变。详见loss500_changes.diff和verification.json。
''',encoding='utf-8')
(look/'下一步_连续视觉闭环.md').write_text(f'# 当前交付：VIS5短丢容忍loss500\n\n{links}\n[测试说明]({base}/测试说明.md)。局部红色45→35（比例2→1.5），中心±48传感器像素，保留2帧跟踪历史；连续会话最后有效球结果500ms保持、断流200ms。其余控制/协议/保护不变。\n\n{metrics}。SHA256 `{digest}`。实板恢复和误识别率待新日志，未自动烧录或写Flash。\n',encoding='utf-8')
contract=json.loads(read(root/'baseline_contract.json'));contract.update(status=r['status'],next_milestone='physical loss500 recovery/false detection and continuous tuning from raw VIS5 logs')
(root/'baseline_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
agent=root/'AGENTS.md';s=read(agent)
if '# loss500 delivery status' not in s:
    agent.write_text(f'''# loss500 delivery status

Current bit output/vision_follow_20261022_loss500.bit SHA256 `{digest}`. Ten suites including actual RGB classifier/bbox/CDC/AUTO and1.28AB,2560-pixel boundary checks,500/200ms deadlines, raw-invalid429byte coasting UART, old8fault guards and exact preserved executor/protocol, Chinese launcher/render and full routing pass. {metrics}. Physical recovery/false positives remain pending. Only current publish_loss500.py may publish; prior scripts are history. Immutable pre-change archive in loss500_lineage.json. Raw V/Q/B/AGE semantics preserved; only already running AUTO may coast. No automatic restart/homing/programming/Flash.

'''+s,encoding='utf-8')
progress=root.parent/'D36A_STEPPER_调试进度总结.md'
if 'VIS5 loss500短丢容忍软件交付' not in read(progress):
    with progress.open('a',encoding='utf-8') as f:f.write(f'\n\n## 2026-10-22 VIS5 loss500短丢容忍软件交付\n\n保留实际红色检测，局部35/比例1.5、中心±48像素，2帧续检历史；连续会话500ms最后有效球保持，断流200ms。原运动核心及协议不改。十套仿真和完整构建通过，{metrics}。新bit `{digest}`，[步骤]({base}/测试说明.md)。旧VIS5归档见loss500_lineage.json；实板恢复/误识别率待验证，未自动烧录。\n')
# Exact archive + current deliverables/source pairing. Avoid unrelated live captures,
# stale runner logs and generated probe/snapshot binaries in the release ZIP.
files=[]
for folder in ['rtl','user_source','host','sim','td_project']:
    for p in (root/folder).rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(root)
        if any(x in ('__pycache__','logs') or x.endswith('_Runs') for x in rel.parts):continue
        if p.suffix in ('.vvp','.vcd','.db') or p.name.endswith(('.combined.v','_runner.txt')) or 'probe' in p.name:continue
        if folder=='td_project' and p.suffix not in ('.al','.sdc'):continue
        files.append(p)
files+=list(root.glob('*.py'))+list(root.glob('*.ps1'))+list(root.glob('*.tcl'))+list(root.glob('*.md'))+list(root.glob('*.diff'))
files+=[root/n for n in ['verification.json','loss500_lineage.json','follow_lineage.json','baseline_contract.json','camera_lineage.json','center_lineage.json','large60_lineage.json','motion_lineage.json','build_sources.json','frame_layout.json','build.log']]
files.append(root/'routed_netlist.v')
files+=list((root/'output').glob('*.bit'))+list((root/'output').glob('*.txt'))
run=root/f'{root.name}_Runs/phy_1';files+=[run/f'{root.name}{s}' for s in ['_phy.area','_phy.ts','_pr.timing']]
files=sorted(set(files));manifest={'status':r['status'],'bit_sha256':digest,'bit':bit.relative_to(root).as_posix(),'files':{p.relative_to(root).as_posix():sha(p) for p in files}}
(root/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
bundle=look/'VIS5_短丢500ms_20261022.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files+[root/'delivery_manifest.json']:z.write(p,p.relative_to(root).as_posix())
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None
    for rel,h in manifest['files'].items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,rel
print(json.dumps({'bit':str(bit),'sha256':digest,'bundle':str(bundle),'paired_files':len(files),'bundle_sha256':sha(bundle)},ensure_ascii=False,indent=2))
