/**
  ******************************************************************************
  * @file    app_demo.c
  * @brief   四个电机教学实验的实现和串口交互处理
  ******************************************************************************
  *
  * ======== 四个实验的功能 ========
  *
  * 实验1 (DEMO_SELECT=1): 开环正反转验证
  *   - 验证电机驱动器硬件接线 (STEP/DIR/EN) 是否正确
  *   - 电机每 1 秒自动切换方向, 转动固定步数
  *   - 不需要编码器, 纯开环
  *
  * 实验2 (DEMO_SELECT=2): 编码器信号验证
  *   - 通过串口(115200-8-N-1)发送单字符指令控制电机:
  *       1 = 顺时针连续转, 2 = 逆时针连续转, 0 = 停止
  *   - 电机保持使能(上电锁轴), 可用于手动拨动转子观察编码器反馈
  *   - 每 200ms 打印一次: A/B 计数值、角度、速度、PWM 绝对角度、Z 相圈数
  *
  * 实验3 (DEMO_SELECT=3): 闭环自动演示
  *   - 电机在每个目标角度停留 4 秒后自动切换到下一个目标
  *   - 目标切换顺序: +DEMO3_TARGET_DEG → 0 → -DEMO3_TARGET_DEG → 0 (循环)
  *   - 用于观察闭环控制过程: 分段脉冲爆发 → 编码器反馈 → 误差缩小 → 稳定到位
  *
  * 实验4 (DEMO_SELECT=4): 串口角度指令闭环控制
  *   - 通过串口发送 ASCII 指令(以回车结束)控制电机:
  *       A1 <角度>  — 转至指定角度(如 A1 90 或 A1 -45.5)
  *       S          — 查询当前状态和目标
  *       Z          — 当前位置设为零点
  *       X          — 紧急停止
  *       C1         — 清除故障
  *       D1         — 翻转正向方向极性(仅在电机停止时)
  *       H          — 重新打印指令说明
  *   - 闭环在 5ms ISR 中自动运行, 主循环仅响应串口指令
  *
  * ======== 架构说明 ========
  *
  *   实时层(在 TIMER_0 的 5ms ISR 中):
  *     Demo_Tick5ms() → Encoder_Tick(5) → CL_Process()
  *     (编码器更新 + 闭环计算, < 1ms 完成)
  *
  *   非实时层(在 main() while(1) 中):
  *     Demo_Process() → Demo_PollUart() + 实验状态机更新 + 数据打印
  *     (串口交互、格式化输出, 允许阻塞数百微秒)
  ******************************************************************************
  */
#include <stdio.h>
#include <string.h>
#include "board.h"
#include "app_demo.h"
#include "closed_loop.h"
#include "demo_config.h"
#include "encoder.h"
#include "motor.h"

/*
 * ── 模块内部状态 ──
 *
 * s_ms           : 自启动以来的累计毫秒数(5ms 中断每次递增)
 * s_line         : 串口指令行缓冲区(实验4用, 以回车为结束符)
 * s_line_len     : 当前指令行的已接收字符数
 * s_last_action  : 上一次实验动作的时间戳(ms), 用于动作间延时
 * s_last_output  : 上一次数据打印的时间戳(ms), 用于控制打印频率
 * s_demo1_state  : 实验1 的方向状态 (0=正向, 1=反向)
 * s_demo2_state  : 实验2 的当前运动状态 (0=停止, 1=顺时针, 2=逆时针)
 * s_demo3_state  : 实验3 的目标序号 (0→1→2→3 循环, 对应四个目标角度)
 */
static volatile uint32_t s_ms;
static char     s_line[40];
static uint8_t  s_line_len;
static uint32_t s_last_action;
static uint32_t s_last_output;
static uint8_t  s_demo1_state;
static uint8_t  s_demo3_state;
static uint8_t  s_demo2_state;

/*
 * ── Demo_FaultName ──
 * 将闭环故障码转为可读的中文字符串。
 * 用于实验3/4 的故障状态打印, 方便用户快速定位问题。
 */
static const char *Demo_FaultName(CL_Fault_t fault)
{
    if (fault == CL_FAULT_NONE)         return "正常";
    if (fault == CL_FAULT_NO_ENCODER)   return "无编码器反馈! 检查接线/编码器/堵转";
    if (fault == CL_FAULT_DIRECTION)    return "方向错误! 检查 AXIS_X_POSITIVE_DIR_LEVEL 或接线";
    return "驱动器故障";
}

/*==========================================================================*/
/*                          实验4: 串口指令闭环控制                            */
/*==========================================================================*/
/**
  * 实验4 控制方式: PC 通过串口(115200-8-N-1)发送 ASCII 指令,
  * 驱动电机1 转到指定角度, 也可查询状态、设零、停止、清除故障和翻转方向极性。
  *
  * 支持的指令列表:
  *   "A1 <角度>" — 电机1 转到指定角度, 可带负号和小数, 如 "A1 90" 或 "A1 -45.5"
  *   "S"        — 查询电机1 的当前状态: 目标角度、实际角度、偏差、到位/运动中/空闲、
  *                故障原因、PWM 绝对角度、Z 相有符号圈数
  *   "Z"        — 将电机1 当前位置设为坐标零点
  *   "X"        — 紧急停止电机1
  *   "C1"       — 清除电机1 的故障(故障修复后将当前位置作为目标, 不会意外运动)
  *   "D1"       — 翻转电机1 的正向方向电平(可用于纠正 DIR 极性, 仅电机停止时有效)
  *   "H" / "?"  — 重新打印指令说明
  *
  * 观察要点:
  *   1. 目标角度是多圈 A/B 累计角度, 可以超过 ±360°;
  *      PWM 角度是 0~360° 绝对角度, 两者含义不同
  *   2. 设定新目标后, 闭环将自动分段发出 STEP 脉冲,
  *      编码器实际角度逐步逼近目标, 到位后稳定在容差内
  *   3. 有故障时拒绝新目标, 需先排查问题再清除故障
  */

/*
 * ── Demo4_PrintHelp ──
 * 打印实验4 的所有串口指令说明。
 * 在 Demo_Init 和用户输入 'H' 指令时调用。
 */
static void Demo4_PrintHelp(void)
{
    printf("\r\n================ 实验4 串口指令说明 ================\r\n");
    printf("使用串口发送字符指令(末尾加回车发送):\r\n");
    printf("  A1 <角度>  电机1转到指定角度, 如: A1 90 或 A1 -45.5\r\n");
    printf("  S          查询电机1状态(含PWM绝对角度和有符号Z圈数)\r\n");
    printf("  Z          电机1当前位置设为零点\r\n");
    printf("  X          紧急停止电机1\r\n");
    printf("  C1         清除电机1故障\r\n");
    printf("  D1         翻转电机1方向电平(需电机停止时)\r\n");
    printf("  H          重新打印此说明\r\n");
    printf("====================================================\r\n\r\n");
}

/*
 * ── Demo4_PrintAxis ──
 * 打印一次电机1 的完整状态快照。
 *
 * 包含: 目标角度、实际角度、偏差、到位/运动/空闲状态、故障原因、
 *       PWM 绝对角度(若信号有效)、Z 相有符号圈数。
 *
 * 使用 CL_GetSnapshot 确保所有数据在同一时刻读取, 避免不一致。
 */
static void Demo4_PrintAxis(void)
{
    CL_Snapshot_t snap;
    float pwm_angle = 0.0f;
    uint8_t pwm_ok;

    CL_GetSnapshot(MOTOR_AXIS_X, &snap);
    pwm_ok = Encoder_GetPwmAngle(ENCODER_AXIS_X, &pwm_angle);

    printf("电机1: 目标=%.2f° 实际=%.2f° 偏差=%.2f° [%s] 故障:%s ",
        snap.target_angle_deg, snap.current_angle_deg,
        snap.target_angle_deg - snap.current_angle_deg,
        (snap.reached != 0U) ? "已到位" :
            ((snap.active != 0U) ? "运动中" : "空闲"),
        Demo_FaultName(snap.fault));

    if (pwm_ok != 0U)
        printf("PWM绝对角度=%.2f° ", pwm_angle);
    else
        printf("PWM无信号 ");

    printf("Z圈数=%ld\r\n", (long)Encoder_GetZCount(ENCODER_AXIS_X));
}

/*
 * ── Demo4_HandleCommand ──
 * 解析并执行一行串口指令。
 *
 * 处理流程:
 *   1. 将整行小写字母转为大写, 实现大小写不敏感
 *   2. 用 sscanf 和 strcmp 匹配各指令
 *   3. 调用 closed_loop API 执行对应操作
 *   4. 打印执行结果(OK/失败原因)
 *
 * 指令 "A1 <角度>" 的解析:
 *   sscanf(line, "A1 %f", &angle) → 提取浮点角度值
 *   CL_SetTargetAngle → 转为编码器计数值, 激活闭环跟踪
 *
 * 注意: 不识别的非空指令行会提示 "未知指令" 并引导用户输入 H 查看帮助。
 */
static void Demo4_HandleCommand(char *line)
{
    char *p;
    float angle;

    /* 大小写转换: 全部转为大写 */
    for (p = line; *p != '\0'; p++) {
        if (*p >= 'a' && *p <= 'z') *p = (char)(*p - 'a' + 'A');
    }

    if (sscanf(line, "A1 %f", &angle) == 1) {
        /* ── A1 角度指令 ── */
        if (CL_SetTargetAngle(MOTOR_AXIS_X, angle) == MOTOR_OK)
            printf("OK: 电机1 目标角度 %.2f°\r\n", angle);
        else
            printf("失败! 参数错误或有故障, 先发 C1 清除故障\r\n");
    } else if (strcmp(line, "S") == 0) {
        /* ── 状态查询 ── */
        Demo4_PrintAxis();
    } else if (strcmp(line, "Z") == 0) {
        /* ── 设为零点 ── */
        CL_SetZeroAll();
        printf("OK: 电机1已在当前位置设零\r\n");
    } else if (strcmp(line, "X") == 0) {
        /* ── 紧急停止 ── */
        CL_StopAll();
        printf("OK: 电机1已停止\r\n");
    } else if (strcmp(line, "C1") == 0) {
        /* ── 清除故障 ── */
        CL_ClearFault(MOTOR_AXIS_X);
        printf("OK: 电机1故障已清除\r\n");
    } else if (strcmp(line, "D1") == 0) {
        /* ── 翻转方向极性 ── */
        if (CL_TogglePositiveDirLevel(MOTOR_AXIS_X) == MOTOR_OK)
            printf("OK: 电机1方向电平已翻转\r\n");
        else
            printf("失败! 电机运动中不能翻转方向\r\n");
    } else if (strcmp(line, "H") == 0 || strcmp(line, "?") == 0) {
        /* ── 打印帮助 ── */
        Demo4_PrintHelp();
    } else if (line[0] != '\0') {
        /* ── 未知指令 ── */
        printf("未知指令: %s (发 H 查看指令说明)\r\n", line);
    }
}

/*==========================================================================*/
/*                          实验2: 编码器数据采集                              */
/*==========================================================================*/
/**
  * 实验2 控制方式: 通过串口发送单个字符 (不需要回车) 控制电机:
  *   '1' = 顺时针连续转
  *   '2' = 逆时针连续转
  *   '0' = 停止
  *
  * 无论电机转或停, 始终处于使能锁轴状态, 可以手动拨动转子
  * 来观察编码器数据是否变化。
  *
  * 为什么可以手动转动:
  *   D36A 上电使能(EN=高)后, 即使 STEP 无脉冲, 线圈仍然通电锁轴。
  *   用手施加足够力可以克服保持力矩转动电机, 从而观察编码器反馈。
  *
  * 观察要点:
  *   1. 发 '1' 和 '2' 时, A/B 计数值和速度的正负号应相反
  *   2. A/B 正交信号经硬件 4 倍频后, 电机转一圈计数值变化约 4000
  *      (取决于 ENCODER_COUNTS_PER_REV 配置)
  *   3. A/B 角度是无限累积的多圈角度, PWM 角度是 0~360° 单圈绝对角度
  *   4. Z 相(PA25)每经过一次 Z 脉冲, 根据 QEI 方向 ±1 累计到 Z 圈数
  *   5. 如果计数值变化方向与预期相反, 修改 ENCODER_AXIS_X_SIGN 或 D1 翻转
  *
  * 连续转动的实现方式:
  *   Motor_StartContinuous 内部开启 TIMA1 硬件 PWM 连续输出 STEP 脉冲,
  *   不使能 ZERO 计数中断, 脉冲无限持续直到调用 Motor_Stop。
  *   停止时强制 STEP 引脚输出低电平, 不会有残留毛刺。
  */

/*
 * ── Demo2_SetMotion ──
 * 设置电机连续转动状态。
 *
 * motion:
 *   0 — 停止 (Motor_StopAll)
 *   1 — 顺时针连续转 (Motor_StartContinuous, DIR=0)
 *   2 — 逆时针连续转 (Motor_StartContinuous, DIR=1)
 *
 * 如当前已处于目标状态则不重复操作, 避免频繁启停。
 */
static void Demo2_SetMotion(uint8_t motion)
{
    if (motion == 0U) {
        Motor_StopAll();
        s_demo2_state = 0U;
        printf("[实验2] 已停止(EN为高电平, 电机仍然使能/锁轴)\r\n");
    } else if (motion == s_demo2_state) {
        printf("[实验2] 已经在%s连续转动\r\n",
               motion == 1U ? "顺时针" : "逆时针");
    } else {
        Motor_StartContinuous(DEMO2_FREQ_HZ, motion == 1U ? 0U : 1U);
        s_demo2_state = motion;
        printf("[实验2] 开始%s连续转动, 频率=%u Hz, 发0停止\r\n",
               motion == 1U ? "顺时针" : "逆时针",
               (unsigned)DEMO2_FREQ_HZ);
    }
}

/*
 * ── Demo_PollUart ──
 * 轮询 UART0 RX FIFO, 处理串口接收。
 *
 * 实验2: 每个接收字符立即执行(0/1/2), 无需回车
 * 实验4: 按行缓冲, 以 '\r' 或 '\n' 为行结束符,
 *        收到完整行后调用 Demo4_HandleCommand 处理
 * 其他实验: 丢弃接收字符
 */
static void Demo_PollUart(void)
{
    while (!DL_UART_Main_isRXFIFOEmpty(UART_0_INST)) {
        char ch = (char)DL_UART_Main_receiveData(UART_0_INST);
#if (DEMO_SELECT == 2)
        /* ── 实验2: 单字符指令, 立即响应 ── */
        if (ch == '0')      Demo2_SetMotion(0U);
        else if (ch == '1') Demo2_SetMotion(1U);
        else if (ch == '2') Demo2_SetMotion(2U);
        else if (ch != '\r' && ch != '\n' && ch != ' ' && ch != '\t')
            printf("[实验2] 未知指令 '%c', 请发 1, 2 或 0\r\n", ch);
#elif (DEMO_SELECT == 4)
        /* ── 实验4: 行缓冲, 以回车为结束符 ── */
        if (ch == '\r' || ch == '\n') {
            if (s_line_len != 0U) {
                s_line[s_line_len] = '\0';
                Demo4_HandleCommand(s_line);
                s_line_len = 0U;
            }
        } else if (s_line_len < sizeof(s_line) - 1U) {
            s_line[s_line_len++] = ch;
        } else {
            s_line_len = 0U;   /* 行过长则丢弃 */
        }
#else
        (void)ch;   /* 其他实验不使用串口 */
#endif
    }
}

/*
 * ── Demo_Init ──
 * 初始化实验状态。
 *
 * 清零所有计数器和状态变量, 根据 DEMO_SELECT 打印对应的:
 *   - 标题横幅(MS42CG + D36A 步进电机闭环控制)
 *   - 当前细分倍数 D36A_MICROSTEP
 *   - 当前实验编号和功能简介
 *   - 实验4 额外打印串口指令说明
 * 实验3/4 额外调用 CL_Init() 初始化闭环。
 */
void Demo_Init(void)
{
    s_ms           = 0U;
    s_last_action  = 0U;
    s_last_output  = 0U;
    s_demo1_state  = 0U;
    s_demo2_state  = 0U;
    s_demo3_state  = 0U;

#if (DEMO_SELECT == 3) || (DEMO_SELECT == 4)
    CL_Init();
#endif

    printf("\r\n\r\n");
    printf("****************************************************\r\n");
    printf("*  MS42CG + D36A 步进电机闭环控制 小型实验          *\r\n");
    printf("*  主控: MSPM0G3507  串口: 115200-8-N-1             *\r\n");
    printf("****************************************************\r\n");
    printf("当前细分设置 D36A_MICROSTEP = %u (需和开关一致!)\r\n",
           (unsigned)D36A_MICROSTEP);
    printf("配置电机数 MOTOR_COUNT = 1 (只使用电机1)\r\n");
    printf("当前实验: 实验%d ", DEMO_SELECT);

#if (DEMO_SELECT == 1)
    /* ── 实验1: 开环正反转 ── */
    printf("- 开环正反转实验\r\n");
    printf("电机将自动正反转, 注意: 装于滑台时请减小DEMO1_STEPS!\r\n\r\n");
#elif (DEMO_SELECT == 2)
    /* ── 实验2: 编码器采集 ── */
    printf("- 编码器读取实验\r\n");
    printf("默认停止, 发1=顺时针连续转, 2=逆时针连续转, 0=停止。\r\n");
    printf("实验2使用单字符指令, 不需要回车发送, 每200ms自动打印数据。\r\n\r\n");
#elif (DEMO_SELECT == 3)
    /* ── 实验3: 闭环自动演示 ── */
    printf("- 闭环自动演示实验\r\n");
    printf("电机1将在 0 <-> ±%.1f° 间自动往复。\r\n", DEMO3_TARGET_DEG);
#if (DEMO3_OUTPUT_MODE == 1)
    printf("数据以{B目标:实际:偏差}$格式输出, 供上位机绘图查看。\r\n\r\n");
#else
    printf("\r\n");
#endif
#else
    /* ── 实验4: 串口角度指令 ── */
    printf("- 串口指令实验\r\n");
    Demo4_PrintHelp();
#endif
}

/*
 * ── Demo_Tick5ms ──
 * 5ms 实时核心任务(在 TIMG0 ISR 中调用)。
 *
 * 每 5ms 执行一次:
 *   1. s_ms 递增 5 (累计毫秒计时器)
 *   2. Encoder_Tick(5) — 更新 32 位编码器累计计数 + PWM 超时检测
 *   3. CL_Process() (实验3/4) — 闭环控制: 检查反馈、计算误差、发出脉冲爆发
 *
 * 注意: 此函数的执行时间必须远小于 5ms。
 */
void Demo_Tick5ms(void)
{
    s_ms += CL_PERIOD_MS;
    Encoder_Tick(CL_PERIOD_MS);
#if (DEMO_SELECT == 3) || (DEMO_SELECT == 4)
    CL_Process();
#endif
}

/*
 * ── Demo_Process ──
 * 主循环任务(在 while(1) 中调用)。
 *
 * 首先轮询串口(UART0 RX FIFO), 然后根据 DEMO_SELECT 执行实验逻辑:
 *
 *   实验1: 等待上次脉冲爆发完成 → 延时 1s → 换向 → 启动下一段爆发
 *          循环往复, 验证电机基本运动功能。
 *
 *   实验2: 每 DEMO2_PRINT_MS (200ms) 打印一次完整的编码器数据:
 *          运动状态、A/B 计数值和角度、当前速度、PWM 绝对角度、Z 相圈数。
 *
 *   实验3: 每 DEMO3_SWITCH_MS (4s) 自动切换一次闭环目标角度
 *          (顺序: +DEMO3_TARGET_DEG → 0 → -DEMO3_TARGET_DEG → 0 循环),
 *          每 DEMO3_OUTPUT_MS (20ms) 输出数据帧。
 *
 *   实验4: 仅轮询串口, 闭环由 5ms 中断中的 CL_Process() 自动处理。
 */
void Demo_Process(void)
{
    Demo_PollUart();

/*==========================================================================*/
/*                          实验1: 开环正反转                                 */
/*==========================================================================*/
/**
  * 电机1 开环正反转, 每次转动 DEMO1_STEPS 个脉冲, 延时 1s 后换向。
  * 仅在电机空闲且距离上次动作已过 1s 时才执行下一次。
  *
  * 观察要点:
  *   1. 修改 DEMO1_FREQ_HZ 可改变 STEP 频率(即电机转速)
  *   2. 修改 D36A 驱动器细分时需先断电, 同时修改 D36A_MICROSTEP 宏,
  *      软硬件不一致会导致实际转动角度与计算值不符
  *   3. 开环发脉冲不依赖编码器, 无法自行纠正丢步,
  *      如果转动距离和预期不符, 可能是脉冲频率过高或力矩不足导致丢步
  *   4. 实验3 的闭环控制可以自动检测并补偿丢步, 适合高精度场景
  *
  * 安全提示: 装于滑台上首次测试时应减小 DEMO1_STEPS, 防止撞击机械限位。
  */
#if (DEMO_SELECT == 1)
    if (Motor_IsBusy(MOTOR_AXIS_X) == 0U && (s_ms - s_last_action) >= 1000U) {
        uint8_t direction = (s_demo1_state == 0U) ? 0U : 1U;
        printf(s_demo1_state == 0U ? "[实验1] 正转 %u 步, 频率 %u Hz\r\n" :
                                     "[实验1] 反转 %u 步, 频率 %u Hz\r\n",
            (unsigned)DEMO1_STEPS, (unsigned)DEMO1_FREQ_HZ);
        (void)Motor_SetDirection(MOTOR_AXIS_X, direction);
        (void)Motor_Start(MOTOR_AXIS_X, DEMO1_STEPS, DEMO1_FREQ_HZ);
        s_demo1_state = (uint8_t)!s_demo1_state;
        s_last_action = s_ms;
    }
#elif (DEMO_SELECT == 2)
    /* ── 实验2: 周期性打印编码器数据 ── */
    if ((s_ms - s_last_output) >= DEMO2_PRINT_MS) {
        float pwm_angle = 0.0f;
        uint8_t pwm_ok = Encoder_GetPwmAngle(ENCODER_AXIS_X, &pwm_angle);
        printf("状态=%s | 电机1: AB计数=%ld 角度=%.2f° 速度=%.1f°/s ",
            s_demo2_state == 1U ? "顺时针" :
                (s_demo2_state == 2U ? "逆时针" : "停止"),
            (long)Encoder_GetCount(ENCODER_AXIS_X),
            Encoder_GetAngle(ENCODER_AXIS_X),
            Encoder_CalcSpeedDps(ENCODER_AXIS_X, DEMO2_PRINT_MS));
        if (pwm_ok != 0U) printf("PWM绝对角度=%.2f° ", pwm_angle);
        else printf("PWM无信号 ");
        printf("Z圈数=%ld\r\n\r\n", (long)Encoder_GetZCount(ENCODER_AXIS_X));
        s_last_output = s_ms;
    }
/*==========================================================================*/
/*                          实验3: 闭环自动演示                                 */
/*==========================================================================*/
/**
  * 电机1 每 DEMO3_SWITCH_MS (默认4秒) 自动切换一次闭环目标角度,
  * 按 +DEMO3_TARGET_DEG → 0 → -DEMO3_TARGET_DEG → 0 的顺序循环。
  *
  * 观察要点:
  *   1. 设定目标后, 报文打印的偏差值逐渐缩小,
  *      当偏差 ≤ CL_TOLERANCE_COUNTS 并持续稳定 CL_SETTLE_CYCLES 次后,
  *      电机到达目标, 状态显示为"已到位"
  *   2. DEMO3_OUTPUT_MODE=1 时, 数据以 {B目标:实际:偏差}$ 格式输出,
  *      可接入上位机绘图工具实时显示闭环收敛曲线
  *   3. 在安全范围内轻轻拨动转子制造干扰, 观察闭环如何自动纠正回目标位置
  *   4. 稍微按住转子阻止运动(模拟堵转), 累计算法会检测到无反馈
  *      并报"无编码器反馈"故障; 如果拨动方向与指令方向相反,
  *      会报"方向错误"故障
  *   5. 首次调试时可将 DEMO3_TARGET_DEG 设小(如 5°), 确认无障碍后再调大
  *
  * 闭环内部过程:
  *   每 5ms 读取 A/B 位置 → 等待上次脉冲爆发完成 → 检查编码器反馈 →
  *   计算偏差 → 选择方向和脉冲频率 → 发出一小段脉冲 → 重复,
  *   直到偏差稳定在容差内。
  */
#elif (DEMO_SELECT == 3)
    if ((s_ms - s_last_action) >= DEMO3_SWITCH_MS) {
        float target;
        if (CL_GetFault(MOTOR_AXIS_X) != CL_FAULT_NONE)
            printf("[实验3] 电机1故障: %s\r\n",
                Demo_FaultName(CL_GetFault(MOTOR_AXIS_X)));

        /* 循环选择四个目标角度之一 */
        if (s_demo3_state == 0U)        target = DEMO3_TARGET_DEG;
        else if (s_demo3_state == 1U)   target = 0.0f;
        else if (s_demo3_state == 2U)   target = -DEMO3_TARGET_DEG;
        else                            target = 0.0f;

        (void)CL_SetTargetAngle(MOTOR_AXIS_X, target);
        s_demo3_state = (uint8_t)((s_demo3_state + 1U) % 4U);
        s_last_action = s_ms;
    }

    if ((s_ms - s_last_output) >= DEMO3_OUTPUT_MS) {
        CL_Snapshot_t snap;
        CL_GetSnapshot(MOTOR_AXIS_X, &snap);
#if (DEMO3_OUTPUT_MODE == 1)
        /* ── 上位机绘图格式: {B目标:实际:偏差}$ ── */
        printf("{B%.2f:%.2f:%.2f}$", snap.target_angle_deg,
            snap.current_angle_deg,
            snap.target_angle_deg - snap.current_angle_deg);
#else
        /* ── 普通文本格式: 每 10 次打印一行 ── */
        static uint8_t s_div;
        if (++s_div >= 10U) {
            s_div = 0U;
            printf("电机1: 目标=%7.2f 实际=%7.2f 偏差=%6.2f %s\r\n",
                snap.target_angle_deg, snap.current_angle_deg,
                snap.target_angle_deg - snap.current_angle_deg,
                snap.reached != 0U ? "已到位" : "运动中");
        }
#endif
        s_last_output = s_ms;
    }
#endif
}
