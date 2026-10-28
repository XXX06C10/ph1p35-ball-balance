"""Publish bounded three-stage firmware;never program the board or open UART."""
from pathlib import Path
import json,hashlib,zipfile,shutil,difflib,sys
sys.stdout.reconfigure(encoding='utf-8')
r=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from easy3_contract import check_easy3
check_easy3()
v=json.loads(read(r/'verification.json'));assert v['status']=='SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_EASY3_TEST'
bit=Path(v['delivery_bit']);assert sha(bit)==v['sha256'];digest=v['sha256']
lineage=json.loads(read(r/'easy3_lineage.json'));archive=Path(lineage['archive']);parent=next((archive/'published').rglob('delivery_manifest.json')).parent
metrics=f"SWNS {v['timing_ns']['SWNS']:+.3f}ns / HWNS {v['timing_ns']['HWNS']:+.3f}ns，STNS/HTNS 0；Slice {v['resources']['slice']}/21216、DSP {v['resources']['DSP']}/40"
guide=f'''# easy3：三段预判制动 / 更大幅度

## 仍然只需按键

1. 支撑机构，加载 [easy3新bit]({bit.as_posix()})，重开 [配套中文面板]({(r/'host/start_panel.cmd').as_posix()})。
2. K1使能；调平机构、把球放在实际中心，按K3。
3. 按K2开始回中。面板显示“加速送回→预判制动→中心微调”，控制会根据实际运动状态来回切换，到中心后仍保持。
4. 再按K2停止并保持使能；K4立即停步并释放使能。

不需要打开标定工具或填写控制参数。首次先给左右小扰动，每次轻推后松手，整段不要扶球或碰杆，这样新日志才方便继续评估停车速度。

本版软件、模型与布线检查通过。**真实快速停车和稳球效果仍需无手扶的实板日志确认。**

## 变化

- 默认相对K3中立幅度±48→±60编码器计数；绝对目标仍为±60，P/MC仍为±64。中立不为0时，左右可用幅度会受绝对边界裁剪。约60/4096×360=5.27°电机轴角，不等于杆倾角。
- 预置电机频率上限100→200Hz，参考缓变102→200计数/秒，STEP高/低仍各至少2.5ms，方向准备及真实编码器检查保持。
- **送回**：按距离生成有上限的目标球速，远处更积极推动；目标球速最大400串口像素/秒。
- **制动**：根据实测帧间球速与杆当前位置，估算到可用反向制动角还需多久。预看时间为80ms＋5ms×剩余编码器计数（最多约680ms），预测将越过中心或速度超过允许值时，提前反向制动。
- **微调**：靠近中心时目标球速随距离减小；位置与速度同时较小时回到中立附近保持。中心线附近仍有较大速度时继续制动，不因“碰到中心线”就停。
- 新预置用较快的帧时间速度滤波，减少制动信息滞后；速度误差增益为64/256=0.25，慢积分仍有原来的限幅。目标球速是像素单位，不是毫米标定。

不把带外力日志拟合成已确认的物理模型。此预看是有界近似，不是已测定的精确停车距离。速度包络由连续分段线性函数实现，未增加整帧缓存或端侧AI。

中心噪声抑制：只有当前误差在死区内、且连续四个真实有效帧的坐标范围不超过4像素，才将微小速度变化视为识别抖动。快速穿过中心不会满足这个窗口条件。真实±2像素噪声帧的整机仿真4秒没有STEP，离开窗口后立即恢复控制。

高速换向：真实STEP上升沿后至少20ms、且待检查反馈排空后才能反转DIR，避免上一批延迟反馈混入新方向。F1/F2检查和全部阈值没有放宽。

## 保留

easy2的48脉冲/3.5秒检查点继续使用：停发至少40ms，真实反馈排空且净位移比例核对通过后换段。没有清除原点、MC或故障，没有按帧刷新预算。底层64脉冲/5秒、F1～F8、P/MC±64、绝对目标±60、故障保持EN、500ms丢球/200ms断流保护都保留。故障不自动清除或重试。

K1/K2/K3/K4、曝光3600/增益143、蓝框、VIS5 429字节、D1 94字节、P/V/S/C报文及XOR格式不变。只使用D1原保留标志：bit11=预判预置有效；bit10:9=0送回/1制动/2微调，仅bit11=1时解释。旧解析器可以继续按原位掩码读取。显式C自定义参数会退出新预置，仍用原来的PD整定语义，避免旧标定文件被误用于新控制。

## 参考仓库

按用户提供的[仓库](https://github.com/user-lqt/mspm0g3507-ball-balance-car)读取了实际入口[empty.c](https://github.com/user-lqt/mspm0g3507-ball-balance-car/blob/main/empty.c)、独立[串级控制器](https://github.com/user-lqt/mspm0g3507-ball-balance-car/blob/main/BSP/ball_cascade_pid.c)及电机/反馈实现。

实际入口是倾斜、短暂保持、回平和再次观察；独立串级模块包含目标球速限制、位置/速度共同判稳及抗积分饱和。我们借鉴这些控制思路，结合现有编码器内环增加预判。没有照搬其毫米参数、不同的编码器4000计数基准、约900Hz动作频率、上电流程或GPIO驱动。

参考文件、MIT许可证、树对象和逐文件SHA256保存在`references/user_lqt_20261025/`，只作数据参考，没有执行或编译其代码。

## 验证与恢复

23套当前源码RTL回归、7项主机测试、面板SelfTest/SmokeTest及阶段显示检查通过；含八类故障、真实AB12ms反馈、完整UART、检查点、61秒中心保持、旧自定义PD回归、快速过中心与双向提前制动。

五组独立假设球杆/初状态包含400/800像素每秒初速度，均通过5秒内收敛及后续保持。实际RTL指标在`sim/results/tb_braking_plant.log`；这些结果不代表真实机构验收。未改的视频链路沿用冻结的完整RGB回归证明，没有计作本轮RGB重跑。

TD：{metrics}。器件PH1P35MDG324、全部引脚及约束不变；未放宽时钟或增加假路径。

bit SHA256：`{digest}`。

用户确认“还不错”的easy2完整源码/bit/面板和这两份有手扶的日志归档在 `{archive.as_posix()}`。旧bit仍是`output/vision_follow_20261022_easy2.bit`，SHA256 `{lineage['parent_bit_sha256']}`。软件未自动下载或写Flash，加载/重新加载前支撑机构。

构建：`build.ps1 -Release easy3`；回归：`run_easy3_regression.ps1`；校验：`python verify.py`；当前发布：`python publish_easy3.py`。旧发布脚本是沿革，不用于覆盖本版。
'''
(r/'测试说明.md').write_text(guide,encoding='utf-8')
(r/'README.md').write_text(f'''# easy3：送回 / 提前制动 / 中心微调

[新bit]({bit.as_posix()}) · [中文面板]({(r/'host/start_panel.cmd').as_posix()}) · [步骤与恢复]({(r/'测试说明.md').as_posix()})

K1使能，调平放球后K3定中心，K2运行。默认幅度60、频率上限200Hz；位置/速度/当前杆角共同决定制动时机，不需要额外参数操作。保护及检查点保留。23套RTL/7项主机测试、面板、布线通过；{metrics}。真实效果待新无手扶日志，模型结果不能作为实板验收。

SHA256 `{digest}`。本版仅用publish_easy3.py发布；已确认的easy2保留。
''',encoding='utf-8')
(r/'实现与协议.md').write_text('''# easy3增量

以测试说明为当前算法、阶段标志和参数定义。检查点/手动FSM/共用保护/协议序列化逐字节保留，执行器仅增加高速换向前20ms反馈排空等待，新增的是预置外环和默认参数。D1仅使用原保留标志11及10:9，不改变字段/长度/XOR。下面是easy2沿革，其中默认48/100Hz和无分段速度包络的描述属于旧版。

'''+read(parent/'实现与协议.md'),encoding='utf-8')
e=r/'evidence/easy3_before';e.mkdir(parents=True,exist_ok=True)
for p in (archive/'physical').iterdir():shutil.copy2(p,e/p.name)
shutil.copy2(archive/'human_feedback.json',e/'human_feedback.json')
changed=[];diff=[]
for p in list((r/'rtl').glob('*.v'))+list((r/'host').glob('*.ps1'))+list((r/'sim').glob('tb_*.v'))+[r/'user_source/hdl_source/design_top_wrapper.v',r/'build.ps1']:
 rel=p.relative_to(r).as_posix();old=parent/rel
 if not old.exists() or sha(old)!=sha(p):
  changed.append(rel);diff.extend(difflib.unified_diff(read(old).splitlines(True) if old.exists() else [],read(p).splitlines(True),fromfile='easy2/'+rel,tofile='easy3/'+rel))
(r/'easy3_changes.diff').write_text(''.join(diff),encoding='utf-8')
(r/'easy3_changed_files.json').write_text(json.dumps({'changes':changed,'motor_core_changed_only_for_fast_direction_drain':True,'checkpoint_changed':False,'reference_executed':False,'relative_limit':60,'max_hz':200,'predictive_only_builtin':True},ensure_ascii=False,indent=2),encoding='utf-8')
(r/'output/easy3_sha256.txt').write_text(digest+'  vision_follow_20261022_easy3.bit\n',encoding='ascii')
p=r/'AGENTS.md';s=read(p)
if not s.startswith('# easy3 delivery status'):
 p.write_text(f'# easy3 delivery status (2026-10-25)\n\nCurrent easy3 bit `{digest}`;23 current suites/7host/phase UI/routing pass;{metrics}. Accepted manual/checkpoint/common guards/camera/pins/clocks/serializers exact;only fast DIR20ms feedback drain added. Builtin only fast frame velocity,80ms+5ms/count reversal lookahead,piecewise target-speed envelope,13stage outer. DefaultsL60/KV64/200Hz/slew200. D1 reserved11/10:9 active/phase. K1/K3/K2 UX preserved;Ccustom keepsoldPD. Latest logs include manual intervention,not physical identification. Physical stopping pending. Only publish_easy3.py current.\n\n'+s,encoding='utf-8')
p=r/'baseline_contract.json';b=json.loads(read(p));b['status']=v['status'];p.write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf-8')
(look/'下一步_连续视觉闭环.md').write_text('# 当前入口：easy3预判制动\n\n'+f'[步骤与恢复]({(r/'测试说明.md').as_posix()})\n\nK1使能、K3定中心、K2三段回中。先小扰动松手观察，保留无手扶日志评估真实制动效果。\n',encoding='utf-8')
paths=set()
for folder in ['rtl','user_source','td_project','host','sim','evidence','references']:
 for p in (r/folder).rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(r).as_posix()
  if '/__pycache__/' in rel or rel.startswith('host/logs/') or rel=='sim/results/tb_rgb.log' or (rel.startswith('evidence/easy3_attempt1') and p.suffix=='.bit') or p.suffix.lower() in ['.vvp','.vcd','.pyc','.db'] or p.name.endswith(('.combined.v','.runner.log')) or p.name.startswith('synthetic_'):continue
  if folder=='td_project' and p.suffix not in ['.al','.sdc']:continue
  paths.add(p)
for p in r.iterdir():
 if p.is_file() and (p.suffix.lower() in ['.py','.ps1','.tcl','.md','.json','.diff'] or p.name in ['build.log','routed_netlist.v']):paths.add(p)
for p in (r/'output').iterdir():
 if p.is_file() and p.suffix in ['.bit','.txt']:paths.add(p)
for pattern in ['*.area','*.ts','*_pr.timing']:paths.update((r/f'{r.name}_Runs/phy_1').glob(pattern))
paths.discard(r/'delivery_manifest.json');manifest={p.relative_to(r).as_posix():sha(p) for p in sorted(paths)}
(r/'delivery_manifest.json').write_text(json.dumps({'status':v['status'],'bit':'output/vision_follow_20261022_easy3.bit','bit_sha256':digest,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
bundle=look/'VIS5_三段预判制动_easy3_20261025.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for rel in manifest:z.write(r/rel,rel)
 z.write(r/'delivery_manifest.json','delivery_manifest.json')
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None
 for rel,h in manifest.items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,rel
print(json.dumps({'bit':str(bit),'sha256':digest,'bundle':str(bundle),'bundle_sha256':sha(bundle),'paired_files':len(manifest)},ensure_ascii=False,indent=2))
