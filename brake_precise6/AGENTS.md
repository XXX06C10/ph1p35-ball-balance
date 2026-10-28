# 当前迭代precise6：2026-10-27

用户反馈precise5成功率提高，要求继续按211211日志优化。直接父7351ea595865f90f68caaf37781fb5541ff0508c；认可precise3基准d9b9dc415ac109f39bb50d708ca5157c1607d021不变。旧bit/标签/面板归档保留。

本次确认主要停滞在保持区外，抖动导致脱困反复撤回；不是HOLD宽度的主要证据。只在取得原静止资格且稳定坐标历史中正负各至少2次超过24px/s原速度估计后维持脱困：固定本次原始X/均值参考，raw位移>12px或mean位移>3px且同向raw>6px退出，真实运动优先且清除旧静止累计，丢球/断流/停止/K3/进入35px亦清除。保持连续均值滤波。其余precise5各级幅度/到位后30帧加级/64和96上限、正常移动/35-70HOLD/全部内核保护/限位/IO时钟协议不变。新日志开头已有F2，重启后169.660秒新F2；不绕过故障，也不以日志推断硬件原因。

24项RTL回归、模型与面板/器件引脚/布局布线通过，时序{'SWNS': 0.103, 'STNS': 0.0, 'HWNS': 0.02, 'HTNS': 0.0}，bit SHA256 f86441586081166212696fe3914a27fc522889ec9d2a684833e76c5ad2998934。坐标回放脱困有效帧133对62，只是策略测试，实机成功率待测。使用output/brake_precise6.bit、host/start_brake_precise6.cmd，verify_brake_precise6.py与publish_brake_precise6.py为当前工具。不自动烧录。以下历史。

# 当前迭代precise5：2026-10-27

用户授权根据155804日志修复静止窗口失效及脱困24计数到位后球仍不动。认可基准仍为precise3 Git d9b9dc415ac109f39bb50d708ca5157c1607d021；直接父precise4 Git c6aca5857e336a77aeb4ca74521a9a32be887528已归档，不覆盖旧bit或标签。

precise5仅改vision_region100：静止窗口30帧后均值漂移超过2px则重新累计；保留初始8/16/24近区、最高48远区，初始阶段完成且电机距目标≤2计数、球仍静止时，连续30新视觉帧后增加8计数，近区最高64/远区96。运动退出或失效/断流/停机/K3清除新增状态。正常移动P/D/预判/速度/±35保持±70退出、内环及F1-F8/限位/预算/引脚时钟均冻结。相同毫米标定与K3语义。不得把电机到位当作球回中；上限仍不能克服静摩擦的情况仍可能存在，不无限加力。

23项RTL回归、模型与面板/布局布线通过。时序{'SWNS': 0.107, 'STNS': 0.0, 'HWNS': 0.02, 'HTNS': 0.0}，bit SHA256 f1305658cd415ab805f7fdd5a34f43ebfe5c63197dafb1297875793946978b1e。仅软件通过，实机待测，不自动烧录。使用output/brake_precise5.bit和host/start_brake_precise5.cmd，verify_brake_precise5.py/publish_brake_precise5.py为本轮工具。以下历史。

# 当前迭代与固定认可基准：2026-10-27

用户明确认可precise3成功时的停准效果，估计40%成功/60%卡在其他位置，要求以此为基准迭代。固定Git提交d9b9dc415ac109f39bb50d708ca5157c1607d021，标签/分支baseline/brake-precise3-accepted-20261027，bit4878031b5703a9e0d1f17f36258dfc2e48ecc45594f6fc5443229d185f30fbdb；见认可基准_20261027.md。不得覆盖该bit/标签，不要将用户反馈写成全面验收。原仓库无提交，基准通过独立索引创建，保留用户暂存区。

当前候选brake_precise4，仅改变静止资格/速度降噪：原始X30帧范围8px，Q4位置均值(alpha1/4)相对第8帧基准漂移≤2px才确认静止；静止时控制速度为0，真实移动退出。其余执行内核、移动P/D/预判/制动、各级脱困幅度和速度、F1-F8/64步5秒/限位/原始坐标/协议/时钟/引脚与认可基准一致。102218日志中−45px、−210px处坐标仅抖动数像素但估计速度几十px/s，旧脱困反复被撤。日志末尾656.42s有F2，P从0到−19而MC只+2；本版不绕过F2，不能从日志断言外力或硬件原因。22回归和模型/面板/布局布线通过，时序{'SWNS': 0.11, 'STNS': 0.0, 'HWNS': 0.02, 'HTNS': 0.0}，bit SHA256 36192ca2f4624a53b49f7d9f033ec96159fae465fabd16fbab2976fcc4b147e2；实机成功率改善待新日志，不自动烧录。

用户2026-10-27提供两端球心(262,489)/(1693,513)，跨度约125mm。precise4配套面板已加入X线性毫米读数和端点/几何中点977.5标记；摄像头或缩放改变需重标。K3中心和控制增益不自动替换。

使用output/brake_precise4.bit、host/start_brake_precise4.cmd；核验verify_brake_precise4.py，发布publish_brake_precise4.py。回退precise3。以下为历史记录。

# 当前交付：brake_precise3 换向反馈恢复与渐进脱困

用户授权依据215118实测数据修改并交付新bit。原precise2存在CHECK SP1死锁的RTL复现：反向要求pending0，原向1～2步无反馈不足F1。新REGION_FAST专用REVERSAL_RECOVERY在40ms真实静默后补有限原方向脉冲，用真实反馈解除等待或累计3步F1；不重置pending/MC/origin/fault/64步5秒。保持所有公共/手动保护、硬工作范围、引脚时钟和旧协议。D2保留bit15用于恢复等待/MS10诊断。停滞30帧位置跨度≤4px，增倾角仅速度≤8px/s；8/16/24近区，远区逐级48，40counts/s建立，运动后100Hz/160counts/s撤倾。±35入口/±70退出，高速200Hz，全−16/+32不变。21项回归、8模型、2时钟比例及实际50MHz恢复通过；模型门槛±100px/25px_s，不保证实际35px。PH1P35MDG324与时序通过{'SWNS': 0.108, 'STNS': 0.0, 'HWNS': 0.02, 'HTNS': 0.0}。bit SHA256 4878031b5703a9e0d1f17f36258dfc2e48ecc45594f6fc5443229d185f30fbdb。

当前output/brake_precise3.bit、host/start_brake_precise3.cmd、精准回中3_测试说明.md；只使用verify_brake_precise3.py/finalize_precise3.py/publish_brake_precise3.py。父precise2及归档不可变。未自动烧录，实机待验。以下为历史记录。

# 当前交付：brake_precise2 CHECK重试与精准回中

212005 user trace: desired stall target reached48 counts, but core stayed CHECK with SP8 about2s and no new STEP; F1 did not fire because earlier AB response existed. PWM/Z unconnected is irrelevant. Current output/brake_precise2.bit + start_brake_precise2.cmd. Add independent20ms CHECK retry in vision_servo_core; preserve original64pulse/5sec/timeout/real feedback/F1/F2/MC/P/origin. Stall assist now50Hz/80counts_s; high-speed braking stays200Hz. Precision capture35/outward70, coarse100, full−16/+32. ForcedzeroCredit test proves STEP then F1 on true noresponse. 19 suites and8 plants pass. Device/pins/mirrors/timing pass SWNS+0.101/HWNS+0.020; bit SHA256bb0844ff70ea6b50eaf363b488435dbc6ad0f0167449f97e86751ac60ecb3560. Physical pending; no auto programming. brake_precise/fast and earlier rollback preserved.

# Historical delivery: brake_precise 精确停准与静摩擦脱困

User reports brake_fast stops quickly but inaccurately. Latest204902 trace also shows ball parked >300px while actual tilt remained−19counts for~4s then short reversal triggeredF2. Current output/brake_precise.bit and host/start_brake_precise.cmd. Preserve brake_fast parent. Outer policy: high-speed200px_s lookahead braking stays; precision capture35px/outward70, coarse100; after16 valid frames speed<=4px_s beyond35 apply bounded stall tilt8/24/40/48counts by distance; motion immediately returns speed servo. Exact core/timer/budget/guards/bounds/detector/HDMI/clocks/pins/wires frozen. 18 suites including fatal stall replay and models pass. Device/pins/mirrors/timing pass SWNS+0.118/HWNS+0.020; bit SHA2567af27eaff6fa0aed02878896e0621b7fb06f1bd6f5a3412382a51f174953acc4. Physical pending; no auto program. Current precise verify/publish only; brake_fast and earlier rollback preserved.

# Historical delivery: brake_fast 高速提前制动与检查点限额收尾

User-supplied195545 trace proves transient candidate saturation and actual angle −8.61/+13.18deg are not an angle-window reduction; logged near-center crossings show motor not centered at500–1500px/s. Checkpoint telemetry freezes from SP48 until F4, so recovery must preserve original core guards. Current output/brake_fast.bit + host/start_brake_fast.cmd; REGION_FAST=1, REGION100=1,DZ100. Fine static control remains20Hz/12counts_s,HOLD recovery at100px; BRAKE_FAST desired ball speed cap200px_s,125ms control-only lookahead, two-frame velocity,200Hz/200counts_s while speed≥160px_s. After60ms unresolved quiet checkpoint, finalize only frozen target with original remaining64pulse/5sec/core feedback and100ms arrival; no rebase/guard relaxation. HOLD exits on persistent24px_s speed or12px_s outward trend. 18 current suites incl checkpoint noresponse/reverse faults and8 plant models, plus original-rate50-clock crosscheck weak/1500px_s. Exact core/detector/HDMI/pins/clocks/wire formats hashed. Device pins mirrors timing pass SWNS+0.130/HWNS+0.020; bit SHA2561067730ad36deff177b4e7be87fa45b08b53c1582b24bc015e4772645ef69711. Physical pending; no auto programming. Current contract/verify/publish brake_fast only; region100/asym_smooth/asym_range rollback preserved.

# Historical delivery: region100 100px稳区与柔和微调

当前使用 output/region100.bit 与 host/start_region100.cmd，实际顶层REGION100=1、DEFAULT_DEADZONE=100。同一中立姿态K1/静止球K3/K2。默认偏差≤90px且速度≤12px/s连续3次有效结果进入回平保持，持续越过100px等条件恢复；附近位置项削弱、8px/s速度死带、小角度20Hz/12计数每秒，已有大倾角仍允许50Hz/80计数每秒回平。完整固定−16°～+32°窗口与原F1-F8/反馈/MC/64脉冲5秒/500ms丢球200ms断流全部保留，不新增P.L或按中立限幅。检测、HDMI预测、运动内环/核心、原协议和时钟/引脚均按父版本哈希冻结。原版本bit和面板保留。

15项当前源码RTL回归、10项上位机测试、新旧面板自检/界面检查及完整布线通过；PH1P35MDG324、全部原引脚与双口镜像通过。SWNS +0.115ns，HWNS +0.020ns，STNS/HTNS 0。Slice 20763/21216，DSP 34/40。bit SHA256 c96596084cabab4dbf9aceb701308650acccf89b8917d7595a426ec01bcd4a85。五组假设模型通过100px产品条件，实机效果尚待新日志确认；未自动烧录。当前依据region100_verification.json，核验verify_region100.py，发布publish_region100.py，说明100px稳区_测试说明.md。以下仅为历史版本，旧脚本不用于覆盖本轮交付。

# 当前交付：asym_smooth 恢复平稳回正与显示框校正

使用 output/asym_smooth.bit 与 host/start_asym_smooth.cmd。运动阶段恢复用户认可的 asym_range 四帧速度平均、原分段P/D、50/100/200Hz限速；近中心保留30px进入/45px退出、K3相位保持与20/30/50px稳区选择。完整−16°～+32°工作窗口保留，没有额外±48计数限制。HDMI修正行末6像素错位并增加有界一帧显示预测；真实检测、UART、控制目标不使用显示预测。

45项当前源码RTL回归、10项上位机测试及配套新旧面板自检/界面检查通过；PH1P35MDG324、原引脚和双口镜像核对通过。SWNS +0.128ns，HWNS +0.020ns，STNS/HTNS 0；Slice 20721/21216，DSP 32/40。bit SHA256 e05a0ae7e29bd28fc95948f379dcd6f449f5f4afa35dbaa85bd62395bf60a37c。实板回正和显示效果待新日志确认，未自动烧录。

当前依据 asym_smooth_verification.json；核验 verify_asym_smooth.py，发布 publish_asym_smooth.py，说明 asym恢复与显示延迟_测试说明.md。原asym_range.bit及full_range.bit原哈希保留。以下记录仅为历史版本，旧验证/发布脚本不用于覆盖本轮交付。

# asym_smooth work authorization (2026-10-26)

User prefers originalasym_range46a2... middle return, reports HDMI trailing and supplies120008log. Restore moving-law viaASYM_SMOOTH=1/RECOVER_ASYM:exact original4frame/P-D/50-100-200Hz/80-100-160slew proven300update golden comparison; preserve LIVE30/45near-HOLD,K3phase,full fixed−16/+32 (no extra amplitude),all core/guards/pins/clocks/raw protocols. New display-only lead never routes torawUART/control/tracking; capmin(actualhalfobject,24sensorpx),delta48,jitter2,reversal/gap/bad resets. Fix only overlay video_base x/y/EOL rollover; actualRGB comparison reproduces archived6pixel shift and proves raw masks/meta identical. First timing attemptfailed−1.466ns,notdelivered;pipeline then rebuild under unchanged clocks.45suites including active new mode andRGB required. Current verify_asym_smooth.py/publish_asym_smooth.py; physical effects pending. No automatic programming.

# Full working range delivery status

39项当前源码仿真、10项上位机测试及新旧面板自检/界面检查通过；PH1P35MDG324器件、引脚及双口镜像核对通过。SWNS +0.107ns，HWNS +0.02ns，STNS/HTNS 0；Slice 20131/21216，DSP 32/40。bit SHA256 b60f23a56a79740d850b928adfe9d584db8c66540c229a4597baa35e31fdc91d。实机效果待新日志确认，未自动烧录。 Current output/full_range.bit and host/start_full_range.cmd; only verify_full_range.py/publish_full_range.py current. User-prescribed−16/+32deg is the only native target amplitude window. Do not reintroduce a per-neutral/P.L amplitude cap as an oscillation fix; preserve this range in future tuning unless user changes it. Existing fault/pulse/feedback safeguards still apply.

# Full working range correction in progress (2026-10-26)

User explicitly rejects added±48count cap and requires full−16/+32deg working window. Archive full_range_lineage immutable. Only remove native LIVE_ZONE48/P.L cap,keep settle30 damping/zone/K3 phase/core/F1-F8/hard work-feedback-MC bounds/pins/clocks/UART. New full_range_panel removes48hint and preservesL when changing zone,requiresfull_range.bit.39suites replace previous48policy test with full-window/no-P.L-cap test;all remaining assertions/model criteria unchanged. Only verify_full_range.py/publish_full_range.py current. No automatic programming;physical validation pending.

# settle30 delivery status

39项当前源码仿真、10项上位机测试及新旧面板自检/界面检查通过；PH1P35MDG324器件、全部引脚及双口镜像核对通过。SWNS +0.104ns，HWNS +0.02ns，STNS/HTNS 0；Slice 20150/21216，DSP 32/40。bit SHA256 8480c2f5d91b70dfce855df36b90357a4eb305f3f55643fb549cf8385513c94a。模型为区域保持目标，实机效果待日志确认，未自动烧录。 Current guide稳区与目标整形_测试说明.md; only verify_settle30.py/publish_settle30.py current. Archived prior brake_hold.bit preserved. No physical success claim or automatic board programming.

# settle30 authorization in progress (2026-10-26)

User revoked literal50px request and explicitly asks autonomous log-based analysis/implementation. Parent brake_hold bit/archive immutable in settle30_lineage.json. Live native controller: normal relative target capped min(P.L,48),D half,parent P/filter/MC-phase retained. P.DZ runtime radius15..50 with old3 default30; default30/45hysteresis,entry speed4,trend35/outward8/twoframes. Exact core/F1-F8/bounds/pins/clocks/manual/UART unchanged;no automatic motion/programming. New settle_panel supports20/30/50 P profiles with matching readback,retains center/polarity;requires pairedsettle30.bit. New39-suite roster replaces old15/25 model ±26 precision with explicit30/45 product-region ±46 model criterion (not physical precision); five assumed models include350px/250pxs. Old benchmark assertion preserved. Only verify_settle30.py/publish_settle30.py current;physical results pending.

# Brake/hold delivery status

37项当前源码仿真、10项上位机测试、新旧面板自检/界面检查、PH1P35MDG324器件及引脚/镜像核对均通过。SWNS +0.154ns，HWNS +0.02ns，STNS/HTNS 0；Slice 20030/21216，DSP 32/40。bit SHA256 d154db29a045e10609425aa2d7e6ad45e86cc3f3a666ce7f8fb0c5a55389773e。实机刹车及稳区效果待确认，未自动烧录。 Current bit output/brake_hold.bit, paired unchanged host/start_asym_range.cmd; current verify_brake_hold.py/publish_brake_hold.py only. Parent asym_range.bit remains unchanged rollback.

# Brake/hold revision in progress (2026-10-26)

User reports asymmetric revision usable but slow braking/near-center twitch, supplies actual log20261026_100831_893. Archive brake_hold_lineage immutable. Only WIDE_RANGE region damping/filter/gain blending/speed cap/entry-trend gates and controller K3 STEP-phase neutral adaptation authorized. No mechanical identification from disturbed trace. Preserve F1-F8,all limits/core/manual/IO/clocks/UART and no auto programming. Test37 current suites, host/GUI and full timing before publish_brake_hold.py; current guide 制动与稳区_测试说明.md. Previous asymmetric build/bit is rollback, not overwritten. Actual physical improvement pending.

# Asymmetric range delivery status

36项当前源码仿真、10项上位机测试、新旧面板自检/界面检查通过；PH1P35MDG324和全部引脚/镜像核对通过。SWNS +0.075ns / HWNS +0.020ns，STNS/HTNS 0；Slice 20147/21216、DSP 30/40。bit SHA256 `46a2b676a6bfeaa3168620aaedd53e40e95128d16a1af6c9f081f5b90be49f7c`。实板扩大范围与稳区效果待确认，未自动烧录。 Only native-mode unused branch selections optimized; exact contract comparison uses evidence/asym_dense_attempt1. Current report asym_range_verification.json and publisher publish_asym_range.py. No physical acceptance claim.

# Current asymmetric motor-range authorization (2026-10-25)

User measured motor display angles -18/+35 relative to same neutral and explicitly requested adjusting limits. ASYM_RANGE=1/TW16; working P relative fixed firstK3anchor -182/+364 counts (~-16/+32deg); feedback -204/+398 counts(inward -17.93/+34.98deg); MC separate pulse bounds -159/+310 around captured MC. FirstK3 only enabled+ready, within initial64 window; latches mechanical anchor once per reload. SubsequentK3 cannot shift safety envelope. No origin/MC/fault rebasing. Generic default8-bit/legacy paths retained. Expand referenceQ8/command prediction/checkpoint width; no8-bit alias beyond127/255. Endpoints may stop within1count outside HOLD; HOLD keeps originaltight innerband. Preserve64pulse5s/48pulse3.5s/40msquiet/tailratio/F1-F8/500msloss200msstream/K4raw/direct K1K3K2. VIS6=441 bytes T/AT signed32;D2=148bytes XOR,newneutral/anchor/bounds; oldVIS5/D1/PVS/C01 formats preserved in default branches. Native region controller ignoreslegacy8bitL for fixed window;no external config can move bounds. PWM/Z not enabled;no new wiring. New output/asym_range.bit + host/start_asym_range.cmd. Archive asym_range_lineage immutable;only publish_asym_range.py current,verify_asym_range.py/run_asym_regression.ps1. First level to same measured neutral before initialK3;software reference is not mechanical homing. No auto programming;physical enlarged-range control still pending. Earlier exact symmetric limit restrictions are superseded only for this user-authorized range revision.

# Current region return authorization (2026-10-25)

User rejects probe workflow after E1 corruption; explicitly requests direct K3/K2 improved return. Current top REGION_RETURN=1,REGION_PROBE=0,CASCADE1/PRESET1. New region_return.bit and start_region_return.cmd; no calibration prerequisite or automatic serial/motion. Three valid frames within15px/speed15pxs enter HOLD at K3 neutral;2frames outside25px/highspeed or>45px exit. Four-frame velocity average,disable old quiet-velocity gate only for this mode. Far/mid/near gains and200/100/50Hz caps;absolute60 and original F1-F8/64pulse5s/MC/P64 retain. Original inner+manual FSM frozen. Optional TAIL_CHECKPOINT only:real40msquiet,pending1or2/nonzero command,net>=4pulses and>=2realcounts,wrong0,segment1.28125ratio residual<=1.5counts permits non-arrival segment close;no no-feedback/3noresponse/zero-net forgiveness,no origin/MC/fault reset. Region_return_contract freezes exact adaptation. All other modes keep prior observer/core behavior. VIS5/PVS/C01/D1 lengths/XOR frozen;D1 reservedbit12 active,phase3 hold. E1 disabled/no event-gap gate. Archive region_return_lineage immutable;latest probe logs have no STEP,not physical identification. Only publish_region_return.py current;verify_region_return.py/run_region_return_regression.ps1. Actual stable region not yet physically accepted;no automatic programming. Previous measurements-only restrictions superseded by this new user request.

# Current region_probe measurement authorization (2026-10-25)

User explicitly approved measurement before region hold. Current hardware top REGION_PROBE=1/CASCADE_DEFAULT=0/PRESET=0. New independent output/region_probe.bit and host/start_region_probe.cmd only. Three physical-K2 profiles: selection2 static10s,3 neutral10s,1 finite12leg +8/0/-8/0,-8/0/+8/0,+8/0/-8/0; original slow manual core,2count/100ms stable,1s deadline,400/600ms dwell. K2 abort/K4raw release,invalid/stale/ROI24px/error120px/speed150pxs/config/fault/FIFO loss stop without return/restart. F1-F8,64pulse5s/MC/P64/target60 frozen. Core/controller read-only diagnostics only;E1 additive58byte HEX/XOR FIFO128, sequence loss invalidates measurement. Existing VIS5/D1/PVS/C01 layouts exact;probe D1 opportunity25ms. Source freeze region_probe_contract.py; verify_region_probe.py/run_region_regression.ps1; only publish_region_probe.py current. Archive region_probe_lineage immutable. Measurement not physical region-hold acceptance;F4 root cause unconfirmed;do not relax guards or auto program. Future hold15px/restart25px gains await real logs. Historical paragraphs below describe earlier releases.

# easy3 delivery status (2026-10-25)

Current easy3 bit `3dd2dcd015b9607753f99933919fd81f27313154d5f370da4969461b2327fe97`;23 current suites/7host/phase UI/routing pass;SWNS +0.056ns / HWNS +0.021ns，STNS/HTNS 0；Slice 19753/21216、DSP 36/40. Accepted manual/checkpoint/common guards/camera/pins/clocks/serializers exact;only fast DIR20ms feedback drain added. Builtin only fast frame velocity,80ms+5ms/count reversal lookahead,piecewise target-speed envelope,13stage outer. DefaultsL60/KV64/200Hz/slew200. D1 reserved11/10:9 active/phase. K1/K3/K2 UX preserved;Ccustom keepsoldPD. Latest logs include manual intervention,not physical identification. Physical stopping pending. Only publish_easy3.py current.

# easy3 final regression refinements

A real replay failure at200Hz showed F4 SP48 with fast_count1,delta0,net ratio-0.9375count: old-direction feedback could cancel a new-direction window. Add only20ms since actual STEP rising edge before DIR reversal;retain all response checks/thresholds and manual/common guard bytes. Do not forgive/clear pending feedback. Center noise:four real frames within4pixels AND current error inside deadzone may zero velocity estimate,prevent derivative jitter;fast crossing does not qualify. Attempt1 evidence saved,not delivered. Rebuild final bit.

# easy3 predictive braking authorization (2026-10-25)

User confirms easy2 qualitatively improved;requests larger amplitude,anticipatory three-stage stopping,and review of user-lqt GitHub repository. Latest logs have manual intervention;do not identify physical dynamics from them. Preserve accepted easy2 checkpoint,all core F1-F8/64pulse5s/MC/P64/absolute60/manual/IO/clocks. Relative60,preset200Hz/slew200,fast frame velocity and bounded actuator-reversal lookahead/speed envelope;explicit C custom keeps legacy PD. D1 reserved flags11/10:9 indicate predictive active/phase;wire sizes/XOR unchanged. K1/K3/K2 UX unchanged. Archive easy3_lineage immutable. Real acceptance pending. Only publish_easy3.py current.

# easy2 delivery status (2026-10-24)

Current easy2 bit `ae08951c63f5ca2111097d5da47f06c4bd424637a8a6f852cd28bf404df8f1c9`;21 current suites+old F5 replay/7host/panel/routing pass;SWNS +0.113ns / HWNS +0.020ns，STNS/HTNS 0；Slice 19600/21216、DSP 35/40. Inherited fullRGB frozen legacy path. AUTO checkpoint at48pulses/3.5s,quiet40ms,drained feedback,net ratio1.28125±4counts;not arrived,no fault/origin/MC clear. Relative48,absolute60,P/MC64. Observer reset128px. K1/K3/K2 unchanged. Physical return pending. Only publish_easy2.py current.

# easy2 continuous segment repair authorization

User reports immediate F5 at SP64 and requests larger up/down range. Explicit change: AUTO selection1 cooperatively yields at48pulses or3.5s with real40ms quiet,feedback drained and net1.28ratio within4counts; no fault reset, no per-frame budget reset. F1-F8/core64pulse5s/MC/P64/absolute60 retained. Relative preset32->48; high-speed observer innovation reset32->128px. Manual/calibration paths unchanged. K1/K3/K2 UX preserved. Archive easy2_lineage immutable. Only publish_easy2.py current. Real centering still pending.

# easy delivery status (2026-10-24)

Current easy bit `c2939bdf187d2623c995c61483f27291c51b015488e1e28a61c9be015df4aea2`;19 current suites/7host/panel/routing pass;inherited fullRGB18frames frozen-video/legacy-path proof (current fullRGB rerun interrupted);SWNS +0.030ns，HWNS +0.020ns，STNS/HTNS 0；Slice 19397/21216，DSP 35/40. K1 establishedEN,K3 center,K2 persistent return;built-in bounded preset,no calibration prerequisite. All prior guards retained. Physical return pending,not guaranteed. Old cascade archived and unchanged. Only publish_easy.py current.

# Easy return preset authorization (2026-10-24)

User explicitly requests K3 center / K2 persistent return without multi-parameter calibration. Enable bounded built-in cascade preset, retain K1 established enable, all F1-F8 and limits; no fault auto retry. K3 and camera configuration do not invalidate this built-in preset, but fresh-result gating/cancel still applies; explicit C replaces preset and retains prior requalification semantics. Runtime0. No physical success claim. Parent cascade bit/package archived in easy_lineage.json. Only publish_easy.py may publish this revision; do not overwrite prior cascade bit.

# cascade delivery status (2026-10-24)

Current bit output/vision_follow_20261022_cascade.bit SHA256 `40f7f6c07e8726bc6dda9ad7141376dcddbfc88d4947d266981557a3b4a359c9`. 18current-source suites,7host tests,actual94/429UART,all8fast/hold guards,6/12msAB,nonzero31/-31,camera/RGB and full routing pass. 19283/21216 Slice，35/40 DSP，SWNS +0.104ns / HWNS +0.020ns，STNS/HTNS均0，STA覆盖97.65%. C01/D1 additive;PVS/VIS5 serializer/manual FSM/camera/pins/clocks frozen. Faults stopSTEP/retain establishedEN;K1release-only,K4/reset release. Production RU0/defaultunqualifiedCASCADE1;no automatic motion or restart. PhysicalK2 calibration/model/centering still pending. Only publish_cascade.py current;old publishers historical. cascade_lineage/hold release immutable. No automatic programming.

# Authorized cascade / fault-hold revision (2026-10-24)

User approved and requested implementation of the complete staged plan. Faults F1-F8 stop STEP/latch but retain previously established holding EN; K1 can release only during fault, K4/reset/power/configuration release; no fault restart. Preserve 64pulse/5s,MC/P64,absolute60,manual pulse timing,raw vision/VIS5/PVS. Add measured-frame outer controller,fast checked encoder inner loop,finite physical-K2 calibration,additive checked control/diagnostics,host fitting and regression. No invented physical success or online auto-tuning without measured data. Archive cascade_lineage immutable. Earlier exact servo/enable restrictions are superseded only for this authorized change. No automatic programming.

# neutral delivery status (2026-10-23)

Current bit output/vision_follow_20261022_neutral.bit SHA256 `3913b7eec4bbc473770272a9da1affe7a20817ba64f9aeb67295dbe7b546197c`. Twelve suites including trueAB disabled-move/re-enable P±31,K3 neutral and centered0STEP/429byte targets,relative±16/32,hard60,invalid±63 KC8/RD0/AJ11,all previous response/RGB/loss/guards and full routing pass. 18533 Slice，SWNS +0.101ns、HWNS +0.020ns，STNS/HTNS均0，STA覆盖97.10%. Core/encoder/origin/MC/parser/camera/pins/clocks exact response baseline. K3 adds separate AUTO neutral, not encoder rebase. L relative in AUTO; T/AT/MT/P absolute. Mode0/2 retain initial-reference semantics. New physical neutral response pending; old trace has manual intervention and cannot certify dynamics. Only publish_neutral.py current; no auto-download/Flash. neutral_lineage immutable.

# Authorized neutral-reference correction (2026-10-23)

User reports failed return to ball center and confirms leveling before K3, manual ball intervention during run. Trace shows levelP31 but AUTO center target0. Fix K3 idle capture to also record a separate AUTO neutral offset; do not reset encoder origin,MC,limits or faults. No motion from K3. Preserve normal direction,response timings,all safeguards,raw vision,VIS5 429byte and P/V/S formats. AUTO target is neutral+bounded relative PD, clamped absolute±60; manual/initial-reference return unchanged. K3 outside±60 cannot arm AUTO (new reject11), limits stay absolute±64. Archive neutral_lineage immutable. New paired bit/host/docs/tests required; only new neutral publisher current, no automatic download/Flash. Earlier K3-only-vision restrictions below describe older behavior; new control neutral must be documented distinctly from encoder origin.

# response delivery status (2026-10-23)

Current bit output/vision_follow_20261022_response.bit SHA256 `828b027854027223edee74cae75bd4df50d846f2cba7762b831ec9ede6f4a8da`. Eleven current-source suites, exact AUTO-only servo timing mux and default-only parser adaptation, all8fast faults,6/12ms trueAB,>=2x16count step/reversal benchmark,SL100ms-unit compatibility,RGB/loss500/stream200/429byte UART,host self/smoke and full routing pass. 18597 Slice；SWNS +0.112ns，HWNS +0.020ns，STNS/HTNS均0，STA覆盖97.11%. Defaults G3/DZ5/L32/KD12/SL8/60s,20ms control/AUTO pulse; manual/return75ms. Direction normal confirmed by human, preserved. New physical dynamics pending. Only publish_response.py may publish; previous scripts historical. response_lineage archive immutable; old loss500 bit preserved. No auto-download/Flash.

# Authorized response revision (2026-10-23)

User confirms direction correct and partial improvement but requests faster/stronger correction. Preserve normal direction (gain bit7=0) proven in current capture. Permit documented AUTO-only shorter setup/feedback waits,20ms control tick with SL retaining counts/100ms units, fine-target quantization and stronger bounded defaults. Manual/return pulse timing, all F1-F8,64pulse/5s,MC/P±64,loss500/stream200,protocol/device/pins/clocks unchanged. Immutable response_lineage archive is the rollback. New bit and paired host required. Do not run historical publication scripts or auto-program/Flash.

# loss500 delivery status

Current bit output/vision_follow_20261022_loss500.bit SHA256 `727f730203dfe59645003da2ee99fdb9fb0dd8e96c4ed4838d7a110fb5469ba8`. Ten suites including actual RGB classifier/bbox/CDC/AUTO and1.28AB,2560-pixel boundary checks,500/200ms deadlines, raw-invalid429byte coasting UART, old8fault guards and exact preserved executor/protocol, Chinese launcher/render and full routing pass. 18534 Slice、18165寄存器、76 IO、21 DSP、45 ERAM；SWNS +0.119ns、HWNS +0.020ns，STNS/HTNS 0，STA覆盖97.09%. Physical recovery/false positives remain pending. Only current publish_loss500.py may publish; prior scripts are history. Immutable pre-change archive in loss500_lineage.json. Raw V/Q/B/AGE semantics preserved; only already running AUTO may coast. No automatic restart/homing/programming/Flash.

# Authorized loss500 revision (2026-10-22)

The user explicitly approved local red tracking hysteresis,2 missing-frame recovery, and500ms valid-ball grace ONLY for an already running continuous session. Camera result watchdog remains200ms. Preserve raw V/Q/B/AGE and VIS5/P/V/S wire format, all motor bounds and fault guards. Initial K2/K3/manual/return still require real fresh vision. Archive recorded in loss500_lineage.json is immutable. This supersedes earlier immediate-loss AUTO stop language; never fake a valid frame or reset burst guards during coasting. Rebuild/deliver new loss500 bit and matching Chinese panel. No automatic board programming.

# Follow release status (2026-10-22)

Current VIS5 bit SHA256 `1890c0545bd035ef84b0b8406653483c17826084f8b423d0f2ee671327f2c062`. Eight current-source suites, exact servo adaptation, inherited baseline/archive hashes, P/V compatibility, S bounds,429-byte actual UART, Chinese launcher/render, all routed IO/mirrors and nonnegative timing pass. 18132 Slice、18073寄存器、76 IO、21 DSP、45 ERAM；SWNS +0.011ns、HWNS +0.020ns，STNS/HTNS 0，STA覆盖97.03%. Default mode1/G4/L12/KD12/SL2/30s, VE signed Q4. Auto inner deadband1 is an explicit adaptation; manual/return deadband2 preserved. The user authorized log-based direction default; physical dynamic calibration and actual stability remain pending. No automatic board programming or Flash. Rebuild with build.ps1, verify.py and publish_follow_delivery.py; older scripts/history do not override current documented behavior.

# Current continuous-control authorization (2026-10-22)

User explicitly requested completing remaining vision-loop development. This independent project preserves the large60 parent and original actuator. Add default continuous PD mode, manual single-move and explicit software-reference-return modes, K2 start/stop, K4 raw stop, K3 visual center, Chinese configuration/curves/logging, finite burst guards and safe retargeting at CHECK only. No physical stability or mechanical homing claim from simulation. No per-frame resetting of actuator pulse budgets/timeouts. Loss/config/disable/fault stops the session without automatic resume or homing. Confirm visual center before AUTO. Keep the official PH1P35 pins/clocks and pulse timing lineage. Preserve 64 pulse/5s active-burst and +/-64 command/feedback guards. Older restrictions below describe parent stages; new automatic motion is explicitly authorized. Direction observation is motor down -> ball right; absolute target sign cannot replace actual P delta. Default feedback orientation must be documented from logs/human confirmation and remain configurable. Only hardware K2 starts motion; S packet configures settings only.

# Vision control integration rules

## Current authorized large-target revision (2026-10-22)

The user explicitly requested TARGET_LIMIT=60, MOVE_BUDGET=64, POSITION_LIMIT=64 and FEEDBACK_LIMIT=64, and gain range0..12 with limit0..60. These values supersede earlier +/-5 / +/-22 restrictions below. Preserve the protocol, debounce, K1/K2/K3/K4 roles, deadband2 and no-response3. Actual FPGA RX bounds must match the host; its old bounds were not absent as the user assumed. Existing 75ms/pulse phases require a 5-second timeout instead of2 seconds, at both the core and monitor override. Preserve the previous release in large60_lineage.json's immutable archive before editing in place. Targets remain absolute relative to the software origin; test0/+60/0/-60/0, and retain64-pulse protection for an oversized direct cross-end move. Default runtime gain7/limit5 remains unless the user applies new parameters. New bit, GUI, source hashes and full nonnegative routed timing must be delivered together. Do not run old one-time migration/publish scripts over this revision.

Large60 delivered bit SHA256 `2c4d1f78aea341f11e157d289467434596a03739af1769e3c8109b875f9099eb`, alias output/vision_k3_center_20261022_large60.bit. Six suites, launcher SelfTest/SmokeTest, exact parameter-only core comparison, P/V format/checksum comparison and full routing checks pass. 17528 Slice, SWNS +0.107ns / HWNS +0.020ns, no clock/ADC changes. Large-target physical test remains pending; no automatic programming/Flash occurred. Current publish script is publish_large60.py, current report verification.json and steps 测试说明.md. Earlier delivery paragraphs below are history, not the current parameter limits.

These rules record the user's explicit 2026-10-20 instruction: the old vision/motor/GUI project is reference material and its code is not a trusted working motor baseline. Development must follow the motor scripts and behavior established during this conversation.

## Trusted baselines

- `../d36a_autocal_latch_20261020`: user-confirmed K1 toggle / K4 stop behavior. Bit SHA256 `3c76cc6bed6f8219714435afb2aa3b23462b2408751be2fa0afd2a80ff323906`.
- `../d36a_position5_20261020`: physically observed small-range encoder feedback moves within +/-2 count deadband. Use its pulse phases, guards and error handling when adapting an external-target executor.
- `../d36a_autocal_20261020`: physically measured 4095/4097 counts per 3200-pulse leg, mean4096, return residual-2. This finite calibration sequencer is not a continuously driven visual servo.
- Golden archives are under `D:/AAAProject/FPGA/AAA_LookHere/成功版本归档/`. Do not edit the archived files.

## Implementation

1. Use the validated motor-side module/script lineage. Borrow camera/ISP/recognition and GUI ideas from `../lab_hd_1_mipi_hdmi_1080p_steel_ball_motor_manual`, but do not use its `steel_ball_motor_manual` implementation or old motor commands as a trusted control path.
2. Keep K1 debounced toggle, K4 immediate stop/clear, default disabled, no held-key auto-enable, no fault bypass or uncommanded restart. Camera exposure/gain must have a separate control path; K1/K4 must not simultaneously change exposure/gain.
3. Preserve known STEP/DIR/EN mirror roles C18/V2, D15/V1, E12/U2 and active E1 encoder E16/E17. Match the current proven ADC pull settings. Verify all integrated IO, including camera/HDMI/DDR IP resources, after routing.
4. Active feedback sign is `position = E0 - E1`. A software reference is not mechanical homing. Mean4096 counts/nominal revolution and1.28 counts/pulse are supported by the automatic ratio measurement, with nominal step/microstep assumptions; no independent Z/index calibration was performed.
5. First integrated milestone observes coherent ball coordinates, confidence/freshness, encoder position and proposed bounded target in one telemetry stream. Do not silently connect the old automatic 3200-pulse test to visual target updates. Enable motor motion only in the explicitly identified limited-motion milestone.
6. FPGA performs real-time control; the PC configures bounded parameters and displays/logs data. Validate parameter bounds on FPGA, apply atomically, echo sequence/readback; do not trust host range checks alone. One serial TX owner, and documented RX protocol.
7. Use per-frame coherent clock-domain transfer and a watchdog for missing frames. Existing valid bits are not sufficient if frames stop. Unconfirmed/lost/stale detections cannot keep issuing movement targets. Define stop/hold behavior explicitly.
8. Start with the previously validated small target/pulse bounds. Verify direction against mechanism response before closing the ball loop. Do not assume motor angle equals rod angle, or use old pixel/mm estimates as completed mechanical calibration.

## Build and delivery

- Follow the working `build.ps1` -> `build.tcl` pipeline, TD executable, PH1P35MDG324 device check, completion-marker check, isolated output folder, SHA256 and verification report. Camera/DDR integration may require additional IP ADC/SDC reads; record these as explicit additions to the proven flow.
- Never bypass device mismatch, relax clocks or add false paths just to obtain a passing report. Recheck full integrated resource/timing results rather than adding separate project resource counts.
- Run meaningful simulation before building: retained motor guards, K1/K4/fault behavior, target bounds, stale/lost vision, CDC snapshots and parameter parser/ack tests. Adaptation differences from the physical baselines must be recorded and tested.
- Every new board test must include its corresponding bit, exact steps, expected results and recovery baseline. Say clearly whether the bit changed. Do not ask the user to repeat passed GPIO/round-trip tests without a new unresolved concern.
- Preserve the source project and successful bit. Work in this independent directory. Report hardware evidence only for what the user actually confirmed; don't extend K1/K4 confirmation to a repeated full automatic measurement.

## Authorized finite-motion milestone (2026-10-21)

The user explicitly approved unloaded K2-triggered single visual moves. Use the passed position_core lineage, K1 latch/K4 immediate stop, +/-5 targets, deadband2, pulse budget12, timeout2s and existing fault guards. No continuous follow or automatic resume. Loss/staleness or any parameter commit cancels without driving back to zero; a fresh released-then-pressed K2 is required. Keep exposure3600/gain143/ROI and the parameter packets. Deliver VIS=3 plus matching Chinese panel, bit and board steps. Motion is authorized in this independent project; prior observation-only restrictions describe the archived parent version. New physical motion validation remains pending.

## Current delivery status (2026-10-21)

VIS=3 single-move bit SHA256 `4f376faa5b81fbca71b774c2fb9081b7fca43354595a2c416f560815db486ca2`. Four simulation suites, eight fault fixtures, real quadrature feedback model, 329-byte serializer, Chinese host rendering, source lineage and full routing checks passed. Routed SWNS +0.103ns / HWNS +0.020ns, no clock relaxation. Both physical STEP/DIR/EN mirror pairs are active executor signals, rather than the archived parent's constants. The user confirmed the parent's brightness/ROI effect good; its source/bit/host/hash archive is immutable. This new K2 move release still awaits unloaded physical testing. See README.md, 测试说明.md, 实现与协议.md and verification.json. No automatic board programming or Flash write occurred.

## Archived parent milestone (2026-10-21)

Chinese camera-control observation release: bit SHA256 `32e2a18714fd050a9c2859e636d75e845a493d116b11ecd463e1dc4c7a4a85ba`. Source motor modules remain byte-identical. Startup exposure/gain is 3600/143. New checked V packets and VIS=2 telemetry configure exposure/gain/ROI and require both I2C-flow completion and frame-boundary ROI application. Legacy ae_set and steel_ball_roi_uart are no longer compiled. Both new camera clock-domain mailbox paths are bounded at10ns; the old24MHz->50MHz blanket false path was removed. Clock periods and reference clock groups are unchanged. Classify the documented reference PHY-5060/PHY-5079 clock-routing notices rather than hiding unreviewed critical errors. See verification.json and 相机蓝框实现说明.md.

Routed STEP/DIR pads remain constant zero. Control/UART/CDC, actual full-720p ROI exclusion, actual reference I2C configuration, and Chinese GUI draw/move/readback/render tests passed. Physical fusion/brightness/ROI/RX are pending user confirmation. Do not mark the release physically passed or silently enable automatic motion. The previous observation V1 is archived in releases/observation_v1_before_camera_controls.zip; it is not a physically passed golden. Golden motor archives remain immutable.

## Current K3 center milestone (2026-10-22)

The user explicitly requested and selected board K3 to record the current ball X as the visual control center. Work here independently; preserve the VIS=3 parent and archives. K3 accepts only fresh valid vision, completed settings, no fault, no K4 and idle motor; K1 may be off. K3 never moves the motor or changes the encoder origin/limits. Held-at-boot/long-held keys cannot replay. Parameter freshness and K2 release qualification remain mandatory. Valid UART commits win exact-cycle collisions. Deliver matching VIS=4 host/bit and board steps. User's parent confirmation is qualitative plus limited UART evidence, not full four-direction acceptance. Later F7 at P76 must not be erased by K3; do not loosen +/-22 protection.

K3 release now built and verified: SHA256 `31c95d3abc5c0cf1bca8078fc873818f8ef735f5e61e4b90c0865670c1e26efc`, 17599 Slice, 19 DSP, 45 ERAM, SWNS +0.185ns / HWNS +0.020ns. All five suites, source lineage, routed pins/mirrors and Chinese GUI tests pass. Physical K3 confirmation remains pending. No automatic programming or Flash write occurred. Current entry is 测试说明.md; report is verification.json, paired delivery hashes in delivery_manifest.json. The older delivery paragraphs above record parent history.
