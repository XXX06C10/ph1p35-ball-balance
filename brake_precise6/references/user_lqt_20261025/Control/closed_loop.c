/**
  ******************************************************************************
  * @file    closed_loop.c
  * @brief   增量式分段位置闭环 + 编码器反馈验证
  ******************************************************************************
  *
  * ======== 控制流程 ========
  *
  * 本模块通过 TIMG8 硬件 QEI 获取编码器当前位置，与目标位置比较得到误差，
 * 将误差转化为一小段 STEP 脉冲爆发(每次最多 2 微步)，发出一段后等待电机
  * 完成，再读取编码器验证运动方向与幅度，然后计算下一段爆发。如此循环直到
  * 到达目标位置并稳定。
  *
  * 该"分段逼近+反馈验证"的方式避免了传统开环步进控制因丢步导致的位置累积
  * 误差，同时在不使用编码器速度反馈的情况下也能保证到位精度。
  *
  * ======== 脉冲爆发分段策略 ========
  *
 *   每段最多发 CL_MAX_BURST_STEPS (2 微步) 个脉冲。
  *   频率由误差大小决定(CL_SelectFrequency):
  *     远距离 → 高频快速接近(3000 Hz)
  *     中距离 → 中等频率(1800 / 900 Hz)
  *     近距离 → 低频精确到位(450 / 400 Hz)
  *
  * 这样设计的好处:
  *   - 每个爆发段都能在 5ms 控制周期内完成
  *   - 高频下 8 步耗时约 2.7ms，低频下约 20ms
  *   - 每段完成后立即检查编码器反馈，最快发现异常
  *
  * ======== 到位判断 ========
  *
  * 当 |编码器位置 - 目标位置| ≤ CL_TOLERANCE_COUNTS 时，
  * 计数器 settle_cycles 递增；连续稳定 CL_SETTLE_CYCLES (3) 个周期后，
  * reached 标志置 1，CL_Process 不再发出新脉冲。
  *
  * 如果误差再次超出容差则 settle_cycles 清零，重新逼近。
  *
  * ======== 编码器反馈验证 ========
  *
  * CL_CheckFeedback() 在每段脉冲爆发完成后调用，检查编码器是否
  * 在期望方向上产生了足够的运动(counts ≥ CL_MOVE_CONFIRM):
  *
  *   - 有正向运动(与指令方向一致) → 计数器清零，正常继续
  *   - 编码器反向运动               → 累计到 reverse_steps，超限报 CL_FAULT_DIRECTION
  *   - 累计脉冲数达标但无运动        → 报 CL_FAULT_NO_ENCODER
  *
  * ======== 故障分类 ========
  *
 *   CL_FAULT_NO_ENCODER : 累计发出 CL_CHECK_STEP_LIMIT (16) 个脉冲后
  *                         编码器仍未检测到有效运动。可能原因:
  *                         a) 编码器 A/B 相接线断开
  *                         b) 电机堵转(电流不足或机械卡死)
  *                         c) 编码器损坏
  *
  *   CL_FAULT_DIRECTION  : 编码器检测到反向运动，且累计反向步数
 *                         超过 CL_REVERSE_LIMIT (16)。可能原因:
  *                         a) DIR 引脚极性接反
  *                         b) AXIS_X_POSITIVE_DIR_LEVEL 配置错误
  *                         c) A/B 相接线对调
  *
  *   CL_FAULT_DRIVER     : Motor_Start 或 Motor_SetDirection 返回错误。
  *                         可能原因: 驱动器忙、硬件故障。
  ******************************************************************************
  */
#include "closed_loop.h"
#include "encoder.h"
#include "demo_config.h"

/*
 * 连续 CL_SETTLE_CYCLES 个周期位置误差在容差内才判定"到位"。
 * 避免因瞬时经过目标位置而误判到达。
 */
#define CL_SETTLE_CYCLES    3U

/*
 * 每次脉冲爆发的最大步数(16 细分模式下等于 2 微步)。
 * 限制每次发出的脉冲数量，确保在 5ms 控制周期内完成，
 * 使得每段爆发后都能检查编码器反馈。
 */
#define CL_MAX_BURST_STEPS  ((2U * D36A_MICROSTEP) / 16U)

/*
 * 反馈检查阈值:
 *   CL_CHECK_STEP_LIMIT : 累计发出这么多脉冲仍无有效运动 → 报无编码器故障
 *   CL_MOVE_CONFIRM     : 编码器计数变化 >= 此值 → 确认有有效运动
 *   CL_REVERSE_LIMIT    : 累计反向步数超过此值 → 报方向故障
 *   CL_REVERSE_COUNTS   : 编码器反向变化 >= 此值 → 判定为反向运动
 */
#define CL_CHECK_STEP_LIMIT 16U
#define CL_MOVE_CONFIRM     2
#define CL_REVERSE_LIMIT    16U
#define CL_REVERSE_COUNTS   3

/*
 * ── 闭环内部状态 ──
 *
 * target_count      : 目标编码器计数值(由 CL_SetTargetAngle 写入)
 * active            : 1 = 闭环激活, 正在追踪目标
 * reached           : 1 = 已到达目标且稳定
 * fault             : 当前故障类型
 * settle_cycles     : 连续在容差内的周期计数(用于到位稳定判定)
 * feedback_pending  : 1 = 上一次爆发已完成, 需要在下次 Process 中检查反馈
 * expected_sign     : +1 期望编码器正向计数, -1 期望反向计数, 0 待定
 * check_steps       : 自上次反馈成功以来累计发出的脉冲数
 * reverse_steps     : 累计检测到的反向运动脉冲数
 * check_start_pos   : 反馈检查的起始编码器位置(爆发前的快照)
 * positive_dir_level: 使编码器正向计数的 DIR 引脚电平(0或1)
 */
typedef struct {
    volatile int32_t target_count;
    volatile uint8_t active;
    volatile uint8_t reached;
    volatile CL_Fault_t fault;
    uint8_t  settle_cycles;
    uint8_t  feedback_pending;
    int8_t   expected_sign;
    uint32_t check_steps;
    uint32_t reverse_steps;
    int32_t  check_start_pos;
    uint8_t  positive_dir_level;
} CL_State_t;

static CL_State_t s_cl;
static uint8_t    s_initialized;

/*
 * ── CL_AngleToCount ──
 * 将角度(度)转换为编码器计数值。
 *
 * 公式: count = angle × ENCODER_COUNTS_PER_REV / 360°
 * 结果四舍五入到最接近的整数。
 */
static int32_t CL_AngleToCount(float angle)
{
    float scaled = angle * ENCODER_COUNTS_PER_REV / 360.0f;
    return (scaled >= 0.0f) ? (int32_t)(scaled + 0.5f) :
                              (int32_t)(scaled - 0.5f);
}

/*
 * ── CL_CountToAngle ──
 * 将编码器计数值转换为角度(度)。
 *
 * 公式: angle = count × 360° / ENCODER_COUNTS_PER_REV
 * 例: count = 4000, CPR = 4000 → angle = 360.0°
 */
static float CL_CountToAngle(int32_t count)
{
    return (float)count * 360.0f / ENCODER_COUNTS_PER_REV;
}

/*
 * ── CL_SelectFrequency ──
 * 根据位置误差绝对值选择 STEP 脉冲频率。
 *
 * 分段逻辑:
 *   |误差| > 800 → 3000 Hz   (粗调, 快速接近)
 *   |误差| > 200 → 1800 Hz
 *   |误差| > 50  →  900 Hz
 *   |误差| > 15  →  450 Hz   (细调)
 *   否则        →  400 Hz   (精确定位)
 *
 * 误差越大频率越高, 接近目标时自动减速, 避免过冲和振荡。
 */
static uint32_t CL_SelectFrequency(uint32_t error)
{
    if (error > 800U) return 3000U;
    if (error > 200U) return 1800U;
    if (error > 50U)  return 900U;
    if (error > 15U)  return 450U;
    return 400U;
}

/*
 * ── CL_ErrorToSteps ──
 * 将编码器计数值误差转换为本次应发出的 STEP 脉冲数。
 *
 * 换算公式:
 *   steps = error × MOTOR_STEPS_PER_REV / ENCODER_COUNTS_PER_REV
 *
 * 为避免单次发出过多脉冲导致在 5ms 周期内来不及完成,
 * 结果被限制在 CL_MAX_BURST_STEPS 以内(最小 1 步)。
 *
 * 使用 uint64_t 中间计算防止 32 位乘法溢出。
 */
static uint32_t CL_ErrorToSteps(uint32_t error)
{
    uint64_t numerator = (uint64_t)error * MOTOR_STEPS_PER_REV;
    uint32_t steps = (uint32_t)((numerator + ENCODER_COUNTS_PER_REV - 1U) /
                                ENCODER_COUNTS_PER_REV);
    if (steps == 0U) steps = 1U;
    if (steps > CL_MAX_BURST_STEPS) steps = CL_MAX_BURST_STEPS;
    return steps;
}

/*
 * ── CL_SetFault ──
 * 设置故障状态并立即停止电机。
 *
 * 内部调用 Motor_Stop 确保不会有残留脉冲继续发出。
 * 故障期间 active 和 reached 清零, CL_Process 不执行任何运动。
 */
static void CL_SetFault(CL_Fault_t fault)
{
    s_cl.fault            = fault;
    s_cl.active           = 0U;
    s_cl.reached          = 0U;
    s_cl.feedback_pending = 0U;
    s_cl.check_steps      = 0U;
    s_cl.reverse_steps    = 0U;
    Motor_Stop(MOTOR_AXIS_X);
}

/*
 * ── CL_CheckFeedback ──
 * 一次脉冲爆发完成后的编码器反馈验证。
 *
 * 通过比较爆发前后的编码器位置(current - check_start_pos)判断运动结果:
 *
 *   情况1: 运动方向与 expected_sign 一致且幅度 ≥ CL_MOVE_CONFIRM
 *          → 反馈正常, 清零 check_steps 和 reverse_steps
 *
 *   情况2: 运动方向与 expected_sign 相反且幅度 ≥ CL_REVERSE_COUNTS
 *          → 反向运动, 将本次发出的 check_steps 累计到 reverse_steps
 *            若 reverse_steps ≥ CL_REVERSE_LIMIT → 报方向故障
 *
 *   情况3: 累计发出的 check_steps ≥ CL_CHECK_STEP_LIMIT 但无有效运动
 *          → 报无编码器故障
 *
 * 注意: 本函数在 CL_Process 中被调用, 且仅在 Motor_IsBusy == 0 (爆发完成)
 *       的条件下执行, 保证编码器读数反映的是最新一次爆发后的稳态位置。
 */
static void CL_CheckFeedback(int32_t current)
{
    int32_t movement;

    if (s_cl.feedback_pending == 0U) return;
    s_cl.feedback_pending = 0U;

    movement = current - s_cl.check_start_pos;

    /* 情况1: 编码器在期望方向有足够运动 → 正常 */
    if ((s_cl.expected_sign > 0 && movement >= CL_MOVE_CONFIRM) ||
        (s_cl.expected_sign < 0 && movement <= -CL_MOVE_CONFIRM)) {
        s_cl.check_steps   = 0U;
        s_cl.reverse_steps = 0U;
        return;
    }

    /* 情况2: 编码器反向运动 → 累计反向步数, 超限报方向故障 */
    if ((s_cl.expected_sign > 0 && movement <= -CL_REVERSE_COUNTS) ||
        (s_cl.expected_sign < 0 && movement >= CL_REVERSE_COUNTS)) {
        s_cl.reverse_steps += s_cl.check_steps;
        s_cl.check_steps    = 0U;
        s_cl.expected_sign  = 0;
        if (s_cl.reverse_steps >= CL_REVERSE_LIMIT)
            CL_SetFault(CL_FAULT_DIRECTION);
        return;
    }

    /* 情况3: 无有效运动, 累计脉冲数达标 → 报无编码器故障 */
    if (s_cl.check_steps >= CL_CHECK_STEP_LIMIT)
        CL_SetFault(CL_FAULT_NO_ENCODER);
}

/*
 * ── CL_Init ──
 * 闭环初始化。
 *
 * 将上电位置设为坐标零点、清除所有状态、active=0 reached=1(初始状态
 * 视为"已在目标位置")、故障清零。DIR 极性由 demo_config.h 中的
 * AXIS_X_POSITIVE_DIR_LEVEL 宏决定。
 */
void CL_Init(void)
{
    s_cl.target_count       = 0;
    s_cl.active             = 0U;
    s_cl.reached            = 1U;
    s_cl.fault              = CL_FAULT_NONE;
    s_cl.settle_cycles      = 0U;
    s_cl.feedback_pending   = 0U;
    s_cl.expected_sign      = 0;
    s_cl.check_steps        = 0U;
    s_cl.reverse_steps      = 0U;
    s_cl.check_start_pos    = 0;
    s_cl.positive_dir_level = AXIS_X_POSITIVE_DIR_LEVEL;
    Encoder_SetZero(ENCODER_AXIS_X);
    s_initialized = 1U;
}

/*
 * ── CL_Process ──
 * 闭环核心: 每个控制周期(5ms)调用一次。
 *
 * 执行流程:
 *   1. 读取编码器当前位置
 *   2. 若电机空闲(上一次爆发已完成), 调用 CL_CheckFeedback 验证运动
 *   3. 若闭环非激活或有故障, 直接返回
 *   4. 计算位置误差, 若 ≤ 容差, 递增 settle_cycles;
 *      连续稳定 CL_SETTLE_CYCLES 个周期后 reached = 1
 *   5. 若误差超出容差, settle_cycles 清零, reached = 0
 *   6. 计算本次应发出的脉冲步数和频率
 *   7. 根据误差符号选择方向(DIR 电平)
 *   8. 调用 Motor_SetDirection + Motor_Start 发出一段脉冲爆发
 *   9. 记录 feedback_pending = 1, 等待下一次 Process 时检查反馈
 *
 * 关键设计:
 *   - 每次仅发出一小段脉冲(≤2步), 限制轨道单次角度变化
 *   - 发出前通过 Motor_IsBusy 等上一段完成, 避免多个爆发重叠
 *   - 每次爆发完成后在下一周期立即检查编码器, 保证反馈闭环的实时性
 */
void CL_Process(void)
{
    int32_t  current, error;
    uint32_t error_abs, steps, frequency;
    uint8_t  direction;
    int8_t   sign;

    if (s_initialized == 0U) return;

    current = Encoder_GetCount(ENCODER_AXIS_X);

    /* 等待上一段脉冲爆发完成 */
    if (Motor_IsBusy(MOTOR_AXIS_X) != 0U) return;

    /* 检查上一段爆发后的编码器反馈 */
    CL_CheckFeedback(current);

    /* 闭环未激活或有故障, 不进行运动控制 */
    if (s_cl.active == 0U || s_cl.fault != CL_FAULT_NONE) return;

    /* 计算位置误差 */
    error     = s_cl.target_count - current;
    error_abs = (error >= 0) ? (uint32_t)error : (uint32_t)(-error);

    /* 到位判断: 误差在容差内 → 稳定计数; 超出 → 清零重计 */
    if (error_abs <= CL_TOLERANCE_COUNTS) {
        if (s_cl.settle_cycles < CL_SETTLE_CYCLES) s_cl.settle_cycles++;
        if (s_cl.settle_cycles >= CL_SETTLE_CYCLES) s_cl.reached = 1U;
        return;
    }
    s_cl.settle_cycles = 0U;
    s_cl.reached       = 0U;

    /* 计算本次爆发参数: 步数 + 频率 */
    steps     = CL_ErrorToSteps(error_abs);
    frequency = CL_SelectFrequency(error_abs);

    /* 选择方向和期望编码器计数符号 */
    if (error > 0) {
        direction = s_cl.positive_dir_level;
        sign      = 1;
    } else {
        direction = (uint8_t)!s_cl.positive_dir_level;
        sign      = -1;
    }

    /* 发出脉冲爆发 */
    if (Motor_SetDirection(MOTOR_AXIS_X, direction) != MOTOR_OK ||
        Motor_Start(MOTOR_AXIS_X, steps, frequency) != MOTOR_OK) {
        CL_SetFault(CL_FAULT_DRIVER);
        return;
    }

    /* 期望符号变化或首次爆发 → 重新记录起始位置 */
    if (s_cl.check_steps == 0U || s_cl.expected_sign != sign) {
        s_cl.check_start_pos = current;
        s_cl.check_steps     = 0U;
        s_cl.expected_sign   = sign;
    }

    /* 累计已发出的脉冲数，标记待检查反馈 */
    s_cl.check_steps      += steps;
    s_cl.feedback_pending  = 1U;
}

/*
 * ── CL_SetTargetAngle ──
 * 设置绝对角度目标，激活闭环跟踪。
 *
 * 角度经过四舍五入转换为编码器计数值后存储为 target_count。
 * 闭环变为 active，在下一次 CL_Process 时开始运动。
 *
 * 保护条件:
 *   - target_deg 必须为有效浮点数(排除 NaN)
 *   - 目标范围 ±100000°
 *   - 有激活故障时拒绝新目标(必须先清除故障)
 */
MotorStatus_t CL_SetTargetAngle(MotorAxis_t axis, float target_deg)
{
    if (axis != MOTOR_AXIS_X || s_initialized == 0U ||
        target_deg != target_deg ||
        target_deg > 100000.0f || target_deg < -100000.0f ||
        s_cl.fault != CL_FAULT_NONE)
        return MOTOR_ERROR;

    s_cl.target_count  = CL_AngleToCount(target_deg);
    s_cl.active        = 1U;
    s_cl.reached       = 0U;
    s_cl.settle_cycles = 0U;
    return MOTOR_OK;
}

/*
 * ── CL_SetZero ──
 * 将当前位置设为零点。
 *
 * 停止电机、编码器归零、清除目标(闭环变为不活跃, reached=1)、
 * 清除所有反馈和故障统计。
 */
void CL_SetZero(MotorAxis_t axis)
{
    if (axis != MOTOR_AXIS_X || s_initialized == 0U) return;
    Motor_Stop(axis);
    Encoder_SetZero(ENCODER_AXIS_X);
    s_cl.target_count     = 0;
    s_cl.active           = 0U;
    s_cl.reached          = 1U;
    s_cl.fault            = CL_FAULT_NONE;
    s_cl.feedback_pending = 0U;
    s_cl.check_steps      = 0U;
    s_cl.reverse_steps    = 0U;
}

void CL_SetZeroAll(void) { CL_SetZero(MOTOR_AXIS_X); }

/*
 * ── CL_Stop ──
 * 紧急停止: 停止电机, 闭环变为不活跃, reached = 0。
 * 该停止不等同于"到位" — 下次设置目标时从当前位置重新开始逼近。
 */
void CL_Stop(MotorAxis_t axis)
{
    if (axis != MOTOR_AXIS_X) return;
    Motor_Stop(axis);
    s_cl.active           = 0U;
    s_cl.reached          = 0U;
    s_cl.feedback_pending = 0U;
    s_cl.check_steps      = 0U;
    s_cl.reverse_steps    = 0U;
}

void CL_StopAll(void) { CL_Stop(MOTOR_AXIS_X); }

/*
 * ── CL_ClearFault ──
 * 清除故障并将当前位置作为闭环目标。
 *
 * 故障恢复时以当前位置为锚点, 避免清除故障后电机突然冲向旧目标。
 * 调用后 closed_loop 处于 deactive 但 reached=1 的静止状态,
 * 需重新调用 CL_SetTargetAngle 发起运动。
 */
void CL_ClearFault(MotorAxis_t axis)
{
    if (axis != MOTOR_AXIS_X || s_initialized == 0U) return;
    Motor_Stop(axis);
    s_cl.target_count     = Encoder_GetCount(ENCODER_AXIS_X);
    s_cl.active           = 0U;
    s_cl.reached          = 1U;
    s_cl.fault            = CL_FAULT_NONE;
    s_cl.feedback_pending = 0U;
    s_cl.check_steps      = 0U;
    s_cl.reverse_steps    = 0U;
}

/*
 * ── CL_TogglePositiveDirLevel ──
 * 切换正向编码器计数对应的 DIR 电平极性。
 *
 * 用于在不确定 DIR 极性的情况下进行"试错":
 *   1. 发出正向脉冲 → 检查编码器方向
 *   2. 若编码器反向 → 调用本函数翻转极性
 *   3. 再次测试, 直到编码器方向与指令方向一致
 *
 * 仅在电机空闲时允许调用。
 */
MotorStatus_t CL_TogglePositiveDirLevel(MotorAxis_t axis)
{
    if (axis != MOTOR_AXIS_X || Motor_IsBusy(axis) != 0U) return MOTOR_ERROR;
    s_cl.positive_dir_level = (uint8_t)!s_cl.positive_dir_level;
    s_cl.reverse_steps      = 0U;
    return MOTOR_OK;
}

uint8_t CL_IsReached(MotorAxis_t axis)
{
    return (axis == MOTOR_AXIS_X && s_initialized != 0U) ? s_cl.reached : 0U;
}

CL_Fault_t CL_GetFault(MotorAxis_t axis)
{
    return (axis == MOTOR_AXIS_X && s_initialized != 0U) ? s_cl.fault
                                                          : CL_FAULT_DRIVER;
}

float CL_GetCurrentAngle(MotorAxis_t axis)
{
    return (axis == MOTOR_AXIS_X) ? Encoder_GetAngle(ENCODER_AXIS_X) : 0.0f;
}

/*
 * ── CL_GetSnapshot ──
 * 获取闭环状态的完整快照。
 *
 * 将所有关键字段一次性读取到结构体中, 避免多次单独 getter 调用间
 * (例如 ISR 中 CL_Process 执行后) 状态变化导致的数据不一致。
 *
 * 典型用途: 串口调试打印当前状态, OLED 显示闭环信息。
 */
void CL_GetSnapshot(MotorAxis_t axis, CL_Snapshot_t *snapshot)
{
    if (axis != MOTOR_AXIS_X || snapshot == 0 || s_initialized == 0U) return;
    snapshot->current_count    = Encoder_GetCount(ENCODER_AXIS_X);
    snapshot->target_count     = s_cl.target_count;
    snapshot->error_count      = snapshot->target_count - snapshot->current_count;
    snapshot->current_angle_deg = CL_CountToAngle(snapshot->current_count);
    snapshot->target_angle_deg  = CL_CountToAngle(snapshot->target_count);
    snapshot->active           = s_cl.active;
    snapshot->reached          = s_cl.reached;
    snapshot->fault            = s_cl.fault;
}
