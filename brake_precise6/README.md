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

当前使用 output/brake_precise2.bit 与 host/start_brake_precise2.cmd。212005日志证明静摩擦脱困目标已到48计数，但执行器在CHECK停留约2秒、SP不再增长；PWM/Z未接线与这个问题无关。新版本在服务器运动核心增加20ms独立CHECK重试，不重置原64脉冲/5秒、真实反馈、F1/F2、MC/P或安全范围；脱困阶段改用50Hz起步。19项回归、八组模型、面板测试及完整布线通过。PH1P35MDG324、引脚、镜像和−16°/+32°窗口不变。SWNS +0.101ns、HWNS +0.020ns。bit SHA256 bb0844ff70ea6b50eaf363b488435dbc6ad0f0167449f97e86751ac60ecb3560。实机待确认，未自动烧录。说明精准回中2_测试说明.md；核验verify_brake_precise2.py；发布publish_brake_precise2.py。brake_precise、brake_fast及更早版本原哈希保留。

# 历史交付：brake_precise 精确停准与静摩擦脱困

当前使用 output/brake_precise.bit 与 host/start_brake_precise.cmd。204902日志显示上一版高速停下较快，但90px就进入保持；球在约375px偏差、速度接近0时又被静摩擦卡住，随后短促回转触发F2。新版本保留高速200px/s目标与前馈制动，把真正回平区域收窄到±35px，超过±70px重新纠偏；偏离35px且16帧速度≤4px/s时施加有限脱困倾角（近区8、80px外24、160px外40、240px外48计数），一旦运动立即交回速度制动。18项回归、八组模型、原时钟比例复核、面板测试及完整布线通过；PH1P35MDG324、引脚、镜像和−16°/+32°窗口不变。SWNS +0.118ns、HWNS +0.020ns。bit SHA256 7af27eaff6fa0aed02878896e0621b7fb06f1bd6f5a3412382a51f174953acc4。实机待确认，未自动烧录。当前说明精准回中_测试说明.md；核验verify_brake_precise.py；发布publish_brake_precise.py。brake_fast及更早版本原哈希保留。

# 历史交付：brake_fast 高速提前制动与检查点限额收尾

当前使用 output/brake_fast.bit 与 host/start_brake_fast.cmd。195545日志暴露两类问题：高速穿中心时近区50Hz制动不足，以及48脉冲检查点整段反馈残差未通过后冻结到F4。新版本保留100px区域和完整−16°～+32°工作窗口；低速仍20Hz柔和微调，高速改用200px/s目标球速和125ms前视提前制动。检查点核对60ms仍未结束时，仅用该段原剩余64脉冲预算完成已冻结目标，原真实反馈、5秒计时、F1～F8及故障锁存不变。18项当前源码回归和八组假设模型通过，模型另用原时钟比例复核弱响应和1500px/s工况。PH1P35MDG324、全部原引脚、双口镜像及时序通过；SWNS +0.130ns、HWNS +0.020ns。bit SHA256 1067730ad36deff177b4e7be87fa45b08b53c1582b24bc015e4772645ef69711。实机效果待新日志确认，未自动烧录。当前依据brake_fast_verification.json；说明高速制动与检查点收尾_测试说明.md；核验verify_brake_fast.py；发布publish_brake_fast.py。region100、asym_smooth与asym_range恢复版本原哈希保留。

# 历史交付：region100 100px稳区与柔和微调

当前使用 output/region100.bit 与 host/start_region100.cmd，实际顶层REGION100=1、DEFAULT_DEADZONE=100。同一中立姿态K1/静止球K3/K2。默认偏差≤90px且速度≤12px/s连续3次有效结果进入回平保持，持续越过100px等条件恢复；附近位置项削弱、8px/s速度死带、小角度20Hz/12计数每秒，已有大倾角仍允许50Hz/80计数每秒回平。完整固定−16°～+32°窗口与原F1-F8/反馈/MC/64脉冲5秒/500ms丢球200ms断流全部保留，不新增P.L或按中立限幅。检测、HDMI预测、运动内环/核心、原协议和时钟/引脚均按父版本哈希冻结。原版本bit和面板保留。

15项当前源码RTL回归、10项上位机测试、新旧面板自检/界面检查及完整布线通过；PH1P35MDG324、全部原引脚与双口镜像通过。SWNS +0.115ns，HWNS +0.020ns，STNS/HTNS 0。Slice 20763/21216，DSP 34/40。bit SHA256 c96596084cabab4dbf9aceb701308650acccf89b8917d7595a426ec01bcd4a85。五组假设模型通过100px产品条件，实机效果尚待新日志确认；未自动烧录。当前依据region100_verification.json，核验verify_region100.py，发布publish_region100.py，说明100px稳区_测试说明.md。以下仅为历史版本，旧脚本不用于覆盖本轮交付。

# 当前交付：asym_smooth 恢复平稳回正与显示框校正

使用 output/asym_smooth.bit 与 host/start_asym_smooth.cmd。运动阶段恢复用户认可的 asym_range 四帧速度平均、原分段P/D、50/100/200Hz限速；近中心保留30px进入/45px退出、K3相位保持与20/30/50px稳区选择。完整−16°～+32°工作窗口保留，没有额外±48计数限制。HDMI修正行末6像素错位并增加有界一帧显示预测；真实检测、UART、控制目标不使用显示预测。

45项当前源码RTL回归、10项上位机测试及配套新旧面板自检/界面检查通过；PH1P35MDG324、原引脚和双口镜像核对通过。SWNS +0.128ns，HWNS +0.020ns，STNS/HTNS 0；Slice 20721/21216，DSP 32/40。bit SHA256 e05a0ae7e29bd28fc95948f379dcd6f449f5f4afa35dbaa85bd62395bf60a37c。实板回正和显示效果待新日志确认，未自动烧录。

当前依据 asym_smooth_verification.json；核验 verify_asym_smooth.py，发布 publish_asym_smooth.py，说明 asym恢复与显示延迟_测试说明.md。原asym_range.bit及full_range.bit原哈希保留。以下记录仅为历史版本，旧验证/发布脚本不用于覆盖本轮交付。

# 当前交付：full_range 完整工作范围修正

使用output/full_range.bit与host/start_full_range.cmd。已撤销额外±48计数限制；连续纠偏只按首次K3固定工作目标边界−182/+364计数（约−16/+32度）夹取，原硬反馈/MC/F1-F8保护保持。最新30/45稳区、速度项、K3相位保持不变，可在线20/30/50。不要用旧settle30面板显示48计数限幅。

39项当前源码仿真、10项上位机测试及新旧面板自检/界面检查通过；PH1P35MDG324器件、引脚及双口镜像核对通过。SWNS +0.107ns，HWNS +0.02ns，STNS/HTNS 0；Slice 20131/21216，DSP 32/40。bit SHA256 b60f23a56a79740d850b928adfe9d584db8c66540c229a4597baa35e31fdc91d。实机效果待新日志确认，未自动烧录。

详见完整工作范围_测试说明.md；当前验证full_range_verification.json，发布publish_full_range.py。以下保留历史记录。

# 当前交付：settle30 稳区与目标整形

使用output/settle30.bit与host/start_settle30.cmd，K1/首次K3/K2流程不变。默认30px捕获、45px退出、速度低才回平保持，正常目标相对中立±48计数、速度项减半，原固定硬限位/故障保护保留。在线可切换20/30/50px，不必重编bit；应用后仍须K2启动。仅配套新bit。详见稳区与目标整形_测试说明.md；当前校验settle30_verification.json，发布publish_settle30.py。

39项当前源码仿真、10项上位机测试及新旧面板自检/界面检查通过；PH1P35MDG324器件、全部引脚及双口镜像核对通过。SWNS +0.104ns，HWNS +0.02ns，STNS/HTNS 0；Slice 20150/21216，DSP 32/40。bit SHA256 8480c2f5d91b70dfce855df36b90357a4eb305f3f55643fb549cf8385513c94a。模型为区域保持目标，实机效果待日志确认，未自动烧录。

以下为历史版本记录。

# 当前交付：brake_hold 制动与稳区改良版

使用 output/brake_hold.bit 与原 host/start_asym_range.cmd；同一中立姿态K1/首次K3/K2。保持原不对称角度限幅，新增球速门控制动、平滑增益和K3 STEP相位中立保持。详见 制动与稳区_测试说明.md；当前验证报告 brake_hold_verification.json，发布入口 publish_brake_hold.py。

37项当前源码仿真、10项上位机测试、新旧面板自检/界面检查、PH1P35MDG324器件及引脚/镜像核对均通过。SWNS +0.154ns，HWNS +0.02ns，STNS/HTNS 0；Slice 20030/21216，DSP 32/40。bit SHA256 d154db29a045e10609425aa2d7e6ad45e86cc3f3a666ce7f8fb0c5a55389773e。实机刹车及稳区效果待确认，未自动烧录。

以下为历史版本记录。

# 当前交付：asym_range 不对称角度范围

使用 `output/asym_range.bit` 和 `host/start_asym_range.cmd`。先回到测量时的中立姿态，K1使能、首次K3记录中心和固定限位基准，K2持续回中。工作约−16°～+32°，反馈保护在实测−18°～+35°范围内向内取整；再次K3不会挪动安全窗口。

详见[不对称角度测试说明](不对称角度_测试说明.md)。本版VIS6/D2，必须使用配套面板；A/B反馈，PWM/Z未启用，无需新接线。当前结果在 `asym_range_verification.json`；回归 `run_asym_regression.ps1`，构建 `build.ps1 -Release asym_range`，校验 `python verify_asym_range.py`，发布 `python publish_asym_range.py`。实板效果待确认；未自动烧录。

36项当前源码仿真、10项上位机测试、新旧面板自检/界面检查通过；PH1P35MDG324和全部引脚/镜像核对通过。SWNS +0.075ns / HWNS +0.020ns，STNS/HTNS 0；Slice 20147/21216、DSP 30/40。bit SHA256 `46a2b676a6bfeaa3168620aaedd53e40e95128d16a1af6c9f081f5b90be49f7c`。实板扩大范围与稳区效果待确认，未自动烧录。

下面保留历史说明，旧发布脚本不覆盖当前版本。

# 当前交付：region_return 区域回中

直接使用 `output/region_return.bit` 与 `host/start_region_return.cmd`。K1使能，调平放球按K3定中心，K2持续回中/保持，再按K2停止；K4停步释放。不需要采集向导或填写增益。

详见[区域回中说明](区域回中_测试说明.md)，当前验证报告为 `region_return_verification.json`。修改前完整归档在 `region_return_lineage.json`。回归 `run_region_return_regression.ps1`；构建 `build.ps1 -Release region_return`；校验 `python verify_region_return.py`；发布 `python publish_region_return.py`。软件/模型通过不等于实板稳定保持通过。

下文是历史版本说明；旧发布脚本不用于覆盖当前版本。

# 当前交付：region_probe 实机诊断

这是有限测量固件，不执行连续回中。入口：`host/start_region_probe.cmd`，配套 `output/region_probe.bit`。按向导完成静态10秒、中立10秒、三对±8计数往返；每次都需板上K2。详见[区域诊断测试说明](区域诊断_测试说明.md)。

构建 `build.ps1 -Release region_probe`；回归 `run_region_regression.ps1`；核对 `python verify_region_probe.py`；交付 `python publish_region_probe.py`。当前结果在 `region_probe_verification.json`，历史 `verification.json` 描述easy3。旧bit/面板仍留作恢复，不自动烧录。实际测量和区域保持验收均未完成。

下文保留历史版本说明，旧发布脚本不用于覆盖当前交付。

# easy3：送回 / 提前制动 / 中心微调

[新bit](D:/AAAProject/FPGA/HX1P35A_Contest_202606/exercise/vision_follow_20261022/output/vision_follow_20261022_easy3.bit) · [中文面板](D:/AAAProject/FPGA/HX1P35A_Contest_202606/exercise/vision_follow_20261022/host/start_panel.cmd) · [步骤与恢复](D:/AAAProject/FPGA/HX1P35A_Contest_202606/exercise/vision_follow_20261022/测试说明.md)

K1使能，调平放球后K3定中心，K2运行。默认幅度60、频率上限200Hz；位置/速度/当前杆角共同决定制动时机，不需要额外参数操作。保护及检查点保留。23套RTL/7项主机测试、面板、布线通过；SWNS +0.056ns / HWNS +0.021ns，STNS/HTNS 0；Slice 19753/21216、DSP 36/40。真实效果待新无手扶日志，模型结果不能作为实板验收。

SHA256 `3dd2dcd015b9607753f99933919fd81f27313154d5f370da4969461b2327fe97`。本版仅用publish_easy3.py发布；已确认的easy2保留。
