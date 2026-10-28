/**
  ******************************************************************************
  * @file    motor.c
  * @brief   基于 TIMA1 硬件 PWM 的 D36A 步进电机 STEP 脉冲发生器
  ******************************************************************************
  *
  * ======== 概述 ========
  *
  * 本模块利用 MSPM0 TIMA1 的硬件 PWM 功能生成 50% 占空比的 STEP 脉冲，
  * 驱动 D36A 步进电机驱动器。通过自动重装载值调节 STEP 频率，通过
  * ZERO 中断精确统计定步数模式下已发出的脉冲数。
  *
  * 两种工作模式：
  *
  *   1) 定步数模式 (Motor_Start):
  *      使能 ZERO 中断并在 ISR 中递减剩余步数计数器，
  *      计数归零时自动调用 Motor_StopUnsafe 停止。
  *
  *   2) 连续模式 (Motor_StartContinuous):
  *      关闭 ZERO 计数中断，仅靠硬件 PWM 持续输出 STEP 脉冲，
  *      需调用 Motor_Stop 或 Motor_SetDirection 主动停止或换向。
  *
  * ======== 安全设计 ========
  *
  * - 停止时强制 CCP 输出为低电平（Motor_ForceLow），确保 STEP 引脚
  *   在电机停止时保持稳定低电平，不会产生毛刺或意外脉冲。
  * - Motor_Stop / Motor_Start 内部使用 __disable_irq() 保护临界区，
  *   防止 ISR 和主循环同时修改 busy / remaining 状态变量。
  * - Motor_StopUnsafe 仅为内部使用，调用者需自行确保原子性。
  *
  * ======== 频率范围 ========
  *
  * 定时器时钟 1 MHz (BUSCLK 分频得到)，16 位自动重装载值。
  * 最低频率 16 Hz（周期 1/16 s ≈ 62500 个 timer tick，仍在 65535 内）。
  * 最高频率 5 kHz（周期 1/5000 s = 200 tick）。
  * 为防止极端值导致波形异常，内部对计算出的 period 做了 [100, 65535] 限幅。
  ******************************************************************************
  */
#include "motor.h"

/*
 * ── 模块内部状态（volatile 保证 ISR 与主循环可见） ──
 * s_remaining_steps : 定步数模式下剩余未发出的脉冲数
 * s_busy            : 电机是否正在运行（1 = 运行中, 0 = 空闲）
 * s_continuous      : 是否为连续模式（1 = 连续, 0 = 定步数）
 * s_direction       : 当前 DIR 引脚电平（0 = 低, 1 = 高）
 */
static volatile uint32_t s_remaining_steps;
static volatile uint8_t  s_busy;
static volatile uint8_t  s_continuous;
static volatile uint8_t  s_direction;

/*
 * ── Motor_ForceLow ──
 * 将 STEP 引脚的 CCP 输出强制设为低电平。
 * 用于停止电机后确保 STEP 引脚稳定为低，避免毛刺导致误动作。
 */
static void Motor_ForceLow(void)
{
    DL_TimerA_setCCPOutputDisabled(MOTOR_STEP_TIMER,
        DL_TIMER_CCP_DIS_OUT_LOW, DL_TIMER_CCP_DIS_OUT_LOW);
}

/*
 * ── Motor_UsePWM ──
 * 恢复 CCP 输出由定时器 OCTL 寄存器控制（即正常 PWM 模式）。
 * 在起动前调用，使 STEP 引脚输出 50% 占空比脉冲。
 */
static void Motor_UsePWM(void)
{
    DL_TimerA_setCCPOutputDisabled(MOTOR_STEP_TIMER,
        DL_TIMER_CCP_DIS_OUT_SET_BY_OCTL, DL_TIMER_CCP_DIS_OUT_SET_BY_OCTL);
}

/*
 * ── Motor_StopUnsafe ──
 * 停止电机的底层实现（非原子操作，调用者需自行关中断保护临界区）。
 *
 * 执行步骤：
 *   1. 关闭 ZERO 计数中断
 *   2. 停止定时器计数器
 *   3. 清零 CCP 比较值（避免下次启动时误触发）
 *   4. 强制 STEP 引脚为低电平
 *   5. 复位所有状态变量
 */
static void Motor_StopUnsafe(void)
{
    DL_TimerA_disableInterrupt(MOTOR_STEP_TIMER, DL_TIMERA_INTERRUPT_ZERO_EVENT);
    DL_TimerA_stopCounter(MOTOR_STEP_TIMER);
    DL_TimerA_setCaptureCompareValue(MOTOR_STEP_TIMER, 0U, MOTOR_STEP_CC_INDEX);
    Motor_ForceLow();
    s_remaining_steps = 0U;
    s_busy            = 0U;
    s_continuous      = 0U;
}

/*
 * ── Motor_FrequencyToPeriod ──
 * 将目标 STEP 频率转换为定时器周期值 (LOAD = period - 1)。
 *
 * 计算公式: period = (TIMER_CLK_HZ + freq/2) / freq   (四舍五入)
 *
 * 1 MHz 时钟下:
 *   freq = 1000 Hz → period = 1000 → LOAD = 999
 *   freq = 16 Hz   → period = 62500 → LOAD = 62499
 *
 * 返回值限制在 [100, 65535] 范围内：
 *   - 最小 100 (对应最高频率 10 kHz，防止 period 过小导致波形异常)
 *   - 最大 65535 (16 位定时器的极限)
 */
static uint16_t Motor_FrequencyToPeriod(uint32_t frequency_hz)
{
    uint32_t period = (MOTOR_STEP_TIMER_CLK_HZ + frequency_hz / 2U) / frequency_hz;
    if (period < 100U)   period = 100U;
    if (period > 65535U) period = 65535U;
    return (uint16_t)period;
}

/*
 * ── Motor_ConfigurePWM ──
 * 根据目标频率配置 TIMA1 的 PWM 参数。
 *
 *   1. 计算周期值 period → LOAD = period - 1
 *   2. 停止计数器
 *   3. 恢复 PWM 输出模式（Motor_UsePWM）
 *   4. 写入 LOAD 值和当前计数值
 *   5. 设置 CCR = period/2 产生 50% 占空比
 *
 * 注意：必须先 stop 再改 LOAD，否则可能产生异常脉宽的过渡周期。
 */
static void Motor_ConfigurePWM(uint32_t frequency_hz)
{
    uint32_t period = Motor_FrequencyToPeriod(frequency_hz);
    uint32_t load   = period - 1U;

    DL_TimerA_stopCounter(MOTOR_STEP_TIMER);
    Motor_UsePWM();
    DL_TimerA_setLoadValue(MOTOR_STEP_TIMER, load);
    DL_TimerA_setTimerCount(MOTOR_STEP_TIMER, load);
    DL_TimerA_setCaptureCompareValue(MOTOR_STEP_TIMER, period / 2U,
                                     MOTOR_STEP_CC_INDEX);
}

/*
 * ── Motor_Init ──
 * 电机模块初始化。
 *
 * 上电默认状态:
 *   EN  = 高电平 (使能驱动器, 电机上电即锁轴)
 *   DIR = 低电平 (正向)
 *   STEP = 低电平 (无脉冲, CCP 输出被强制拉低)
 *
 * 同时清除并使能 TIMA1 NVIC 中断。
 */
void Motor_Init(void)
{
    /* EN 引脚初始化为数字输出，默认高电平使能驱动器 */
    DL_GPIO_initDigitalOutputFeatures(IOMUX_PINCM34,
        DL_GPIO_INVERSION_DISABLE,
        DL_GPIO_RESISTOR_NONE, DL_GPIO_DRIVE_STRENGTH_LOW,
        DL_GPIO_HIZ_DISABLE);
    DL_GPIO_enableOutput(MOTOR_EN_PORT, MOTOR_EN_PIN);
    DL_GPIO_setPins(MOTOR_EN_PORT, MOTOR_EN_PIN);

    /* DIR 引脚初始化为低电平（正向） */
    DL_GPIO_clearPins(MOTOR_DIR_PORT, MOTOR_DIR_PIN);
    s_direction = 0U;

    /* 停止所有运动，强制 STEP 引脚为低 */
    Motor_StopUnsafe();

    /* 使能 TIMA1 中断（ISR 中统计脉冲数） */
    NVIC_ClearPendingIRQ(PWM_0_INST_INT_IRQN);
    NVIC_EnableIRQ(PWM_0_INST_INT_IRQN);
}

/*
 * ── Motor_SetDirection ──
 * 设置 DIR 引脚电平以控制电机转向。
 *
 * 仅电机空闲时有效（s_busy == 0）：
 *   - 运行中返回 MOTOR_BUSY，防止运动中突然换向造成堵转
 *   - 参数错误返回 MOTOR_ERROR
 *   - 成功返回 MOTOR_OK
 *
 * high_level = 0 → DIR 低电平（正向）
 * high_level = 1 → DIR 高电平（反向）
 */
MotorStatus_t Motor_SetDirection(MotorAxis_t axis, uint8_t high_level)
{
    if (axis != MOTOR_AXIS_X || high_level > 1U) return MOTOR_ERROR;
    if (s_busy != 0U) return MOTOR_BUSY;

    if (high_level != 0U)
        DL_GPIO_setPins(MOTOR_DIR_PORT, MOTOR_DIR_PIN);
    else
        DL_GPIO_clearPins(MOTOR_DIR_PORT, MOTOR_DIR_PIN);

    s_direction = high_level;
    return MOTOR_OK;
}

/*
 * ── Motor_GetDirection ──
 * 返回当前 DIR 引脚状态（0=低/正向, 1=高/反向）。
 * 仅支持 MOTOR_AXIS_X。
 */
uint8_t Motor_GetDirection(MotorAxis_t axis)
{
    return (axis == MOTOR_AXIS_X) ? s_direction : 0U;
}

/*
 * ── Motor_Start ──
 * 定步数模式：以指定频率发出 steps 个 STEP 脉冲后自动停止。
 *
 * 参数检查:
 *   - axis 必须为 MOTOR_AXIS_X
 *   - frequency_hz 必须在 [MOTOR_MIN_FREQ_HZ, MOTOR_MAX_FREQ_HZ] 范围内
 *   - steps == 0 则等价于调用 Motor_Stop
 *
 * 临界区保护:
 *   使用 __disable_irq() / __enable_irq() 保护 s_busy 和
 *   s_remaining_steps 的写操作，防止 ISR 中断导致状态不一致。
 *
 * 返回值:
 *   MOTOR_OK   — 启动成功
 *   MOTOR_BUSY — 电机正在运行中（需先停止再启动）
 *   MOTOR_ERROR— 参数非法
 */
MotorStatus_t Motor_Start(MotorAxis_t axis, uint32_t steps,
                          uint32_t frequency_hz)
{
    uint32_t primask;

    if (axis != MOTOR_AXIS_X ||
        frequency_hz < MOTOR_MIN_FREQ_HZ ||
        frequency_hz > MOTOR_MAX_FREQ_HZ)
        return MOTOR_ERROR;

    if (steps == 0U) { Motor_Stop(axis); return MOTOR_OK; }

    /* ── 临界区开始 ── */
    primask = __get_PRIMASK();
    __disable_irq();

    if (s_busy != 0U) {
        if (primask == 0U) __enable_irq();
        return MOTOR_BUSY;
    }

    /* 配置 PWM 参数并写入初始状态 */
    Motor_ConfigurePWM(frequency_hz);
    s_remaining_steps = steps;
    s_continuous      = 0U;
    s_busy            = 1U;

    /* 清除残留中断标志，使能 ZERO 计数中断，启动定时器 */
    DL_TimerA_clearInterruptStatus(MOTOR_STEP_TIMER,
                                   DL_TIMERA_INTERRUPT_ZERO_EVENT);
    DL_TimerA_enableInterrupt(MOTOR_STEP_TIMER, DL_TIMERA_INTERRUPT_ZERO_EVENT);
    DL_TimerA_startCounter(MOTOR_STEP_TIMER);

    if (primask == 0U) __enable_irq();
    /* ── 临界区结束 ── */

    return MOTOR_OK;
}

/*
 * ── Motor_StartContinuous ──
 * 连续模式：以指定频率和方向持续输出 STEP 脉冲，直到主动停止。
 *
 * 与 Motor_Start 的区别:
 *   - 不使能 ZERO 计数中断（无需统计脉冲数）
 *   - s_remaining_steps 设为 UINT32_MAX 作为占位符
 *   - s_continuous = 1 标记为连续模式
 *
 * 停止方法:
 *   - 调用 Motor_Stop(axis)
 *   - 再次调用本函数（内部先 stop 再重新启动）
 *
 * 典型用途:
 *   - 实现匀速连续旋转（如传送带、风扇）
 *   - 需要外部传感器信号触发停止的场景
 */
void Motor_StartContinuous(uint32_t frequency_hz, uint8_t high_level)
{
    uint32_t primask;

    if (frequency_hz < MOTOR_MIN_FREQ_HZ ||
        frequency_hz > MOTOR_MAX_FREQ_HZ) return;

    /* 先停止当前运动，再设方向 */
    Motor_Stop(MOTOR_AXIS_X);
    (void)Motor_SetDirection(MOTOR_AXIS_X, high_level);

    /* ── 临界区开始 ── */
    primask = __get_PRIMASK();
    __disable_irq();

    Motor_ConfigurePWM(frequency_hz);
    s_remaining_steps = UINT32_MAX;   /* 占位：表示不计数 */
    s_continuous      = 1U;
    s_busy            = 1U;

    /* 连续模式关闭 ZERO 计数中断，仅靠硬件 PWM 输出 */
    DL_TimerA_disableInterrupt(MOTOR_STEP_TIMER, DL_TIMERA_INTERRUPT_ZERO_EVENT);
    DL_TimerA_startCounter(MOTOR_STEP_TIMER);

    if (primask == 0U) __enable_irq();
    /* ── 临界区结束 ── */
}

/*
 * ── Motor_Stop ──
 * 安全停止指定轴（关中断保护临界区）。
 *
 * 可在主循环或 ISR 中安全调用：
 *   - __disable_irq 确保 s_busy 等状态变量在当前函数内不会被修改
 *   - 恢复原始中断状态（primask），不乱开中断
 */
void Motor_Stop(MotorAxis_t axis)
{
    uint32_t primask;

    if (axis != MOTOR_AXIS_X) return;

    primask = __get_PRIMASK();
    __disable_irq();
    Motor_StopUnsafe();
    if (primask == 0U) __enable_irq();
}

/*
 * ── Motor_StopAll ──
 * 停止所有轴（当前仅 X 轴）。
 */
void Motor_StopAll(void) { Motor_Stop(MOTOR_AXIS_X); }

/*
 * ── Motor_IsBusy ──
 * 查询指定轴是否正在运行中。返回 1=运行, 0=空闲。
 */
uint8_t Motor_IsBusy(MotorAxis_t axis)
{
    return (axis == MOTOR_AXIS_X) ? s_busy : 0U;
}

/*
 * ── Motor_GetRemainingSteps ──
 * 查询指定轴剩余未发出的脉冲数。
 *
 * 注意：该值在 ISR 中递减，主循环读取时不是精确快照，
 *       但偏差不超过 1~2 个脉冲（一个 PWM 周期内）。
 */
uint32_t Motor_GetRemainingSteps(MotorAxis_t axis)
{
    return (axis == MOTOR_AXIS_X) ? s_remaining_steps : 0U;
}

/*
 * ── TIMA1_IRQHandler ──
 * STEP 定时器 ZERO 中断服务程序。
 *
 * 每个 ZERO 事件对应一个完整的 STEP 脉冲周期结束。
 * 定步数模式下 (s_continuous == 0)：
 *   每进入一次 ISR，剩余步数减 1；
 *   减到 0 时自动调用 Motor_StopUnsafe 停止。
 *
 * 连续模式下 (s_continuous != 0)：
 *   ISR 直接返回，不做处理（ZERO 中断本应被关闭，
 *   此处额外判断作为防御性检查）。
 */
void TIMA1_IRQHandler(void)
{
    /* 仅处理 ZERO 事件，其余中断忽略 */
    if (DL_TimerA_getPendingInterrupt(MOTOR_STEP_TIMER) != DL_TIMERA_IIDX_ZERO)
        return;

    /* 空闲状态或连续模式不处理 */
    if (s_busy == 0U || s_continuous != 0U) return;

    /* 递减剩余步数，归零则停止 */
    if (s_remaining_steps > 0U) s_remaining_steps--;
    if (s_remaining_steps == 0U) Motor_StopUnsafe();
}
