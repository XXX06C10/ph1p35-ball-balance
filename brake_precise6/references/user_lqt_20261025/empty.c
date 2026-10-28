#include "board.h"
#include "encoder.h"
#include "motor.h"
#include "k230_uart_rx.h"
#include "demo_config.h"

#include <stdbool.h>
#include <stdint.h>
#include <math.h>

#ifndef CPUCLK_FREQ
#define CPUCLK_FREQ (32000000UL)
#endif

/* ================================================================
 *  步进滑行策略（无 PID）
 * ================================================================ */

#define CFG_K230_OFFLINE_MS     200U
#define CFG_MIN_CONFIDENCE      25U
#define CFG_STARTUP_DELAY_MS    500U
#define CFG_TILT_ANGLE_DEG      14.0f
#define CFG_ANGLE_LIMIT_DEG     20.0f   /* 电机转角硬限位 ±20° */
#define CFG_TILT_DEG_PER_SQRT   1.0f    /* sqrt(mm) × 此值 = 倾角°（远区） */
#define CFG_TILT_MIN_ANGLE_DEG  16.0f    /* 最少倾斜角 */
#define CFG_TILT_MAX_ANGLE_DEG  16.0f    /* 最多倾斜角 */
#define CFG_TILT_MS_PER_SQRT    40U     /* sqrt(mm) × 此值 = 倾斜 ms（远区） */
#define CFG_TILT_MIN_MS         10U     /* 最少倾斜时间 */
#define CFG_TILT_MAX_MS         10U     /* 最多倾斜时间 */
#define CFG_DEADBAND_MM         8.0f
#define CFG_NEAR_ZONE_MM        20.0f   /* 近区范围 ±2cm */
#define CFG_NEAR_ANGLE_DEG      15.0f    /* 近区倾角 */
#define CFG_NEAR_TILT_MS        10U     /* 近区倾斜时间 */
#define CFG_NEAR_COAST_MS       800U    /* 近区停留时间 */
#define CFG_TILT_FREQ_HZ        1000U   /* 倾斜速度 */
#define CFG_RETURN_FREQ_HZ      900U    /* 回平速度 (统一不低于900) */
#define CFG_IDLE_COOLDOWN_MS    600U   /* 每次动作后固定冷却 */
#define CFG_POS_FILTER_ALPHA    0.90f

typedef enum {
    STATE_STOPPED, STATE_STARTUP, STATE_IDLE, STATE_TILTING,
    STATE_COASTING, STATE_RETURNING, STATE_SETTLED
} CtrlState_t;

volatile uint32_t g_system_ms         = 0U;
volatile uint32_t g_uart_rx_bytes     = 0U;
volatile uint32_t g_uart_last_byte_ms = 0U;

static CtrlState_t g_state          = STATE_STARTUP;
static float    g_ball_pos          = 0.0f;
static float    g_ball_pos_filtered = 0.0f;
static bool     g_filter_inited     = false;
static float    g_tilt_dir          = 0.0f;
static float    g_start_pos         = 0.0f;
static float    g_last_idle_pos     = 0.0f;
static float    g_prev_pos          = 0.0f;
static uint32_t g_jump_count        = 0U;     /* 连续大跳变帧数 */
static float    g_jump_target       = 0.0f;   /* 跳变目标值 */
static uint32_t g_tilt_duration_ms  = 0U;
static uint32_t g_coast_wait_ms     = 0U;
static uint32_t g_ball_still_cnt    = 0U;
static uint32_t g_tilt_freq_hz      = 0U;     /* 本周期倾斜频率 */
static int32_t  g_last_freq         = 0;
static uint8_t  g_last_dir          = 0;
static uint32_t g_state_enter_ms    = 0U;
static uint32_t g_startup_start_ms  = 0U;
static bool     g_k230_was_online   = false;

volatile float    g_dbg_state       = 0U;
volatile float    g_dbg_target_angle = 0.0f;
volatile float    g_dbg_angle_now    = 0.0f;
volatile int32_t  g_dbg_freq         = 0;
volatile uint8_t  g_dbg_settled      = 0U;
volatile uint8_t  g_dbg_k230_online  = 0U;

volatile float    g_target_pos_mm    = 0.0f;   /* 目标位置（默认 0=中心），CCS 可改 */
volatile float    g_zero_bias_deg    = 0.0f;   /* 零点自动补偿角（自动积累） */

static float ClampFloat(float v, float lo, float hi)
{
    if (v > hi) return hi;
    if (v < lo) return lo;
    return v;
}

void SysTick_Handler(void) { g_system_ms++; }

void vision_INST_IRQHandler(void)
{
    uint32_t idx = DL_UART_Main_getPendingInterrupt(vision_INST);
    if (idx == DL_UART_MAIN_IIDX_RX) {
        while (!DL_UART_Main_isRXFIFOEmpty(vision_INST)) {
            uint8_t b = (uint8_t)DL_UART_Main_receiveData(vision_INST);
            g_uart_rx_bytes++;
            g_uart_last_byte_ms = g_system_ms;
            K230_RxFeedByte(b, g_system_ms);
        }
    }
}

void TIMER_0_INST_IRQHandler(void)
{
    if (DL_TimerG_getPendingInterrupt(TIMER_0_INST) ==
        DL_TIMERG_IIDX_ZERO) {
        Encoder_Tick(CL_PERIOD_MS);
    }
}

static void Motor_SetFreq(int32_t freq_hz, uint8_t dir)
{
    if (freq_hz == 0) {
        Motor_Stop(MOTOR_AXIS_X);
        g_last_freq = 0; g_dbg_freq = 0; return;
    }
    if (freq_hz == g_last_freq && dir == g_last_dir) return;
    Motor_StartContinuous((uint32_t)freq_hz, dir);
    g_last_freq = freq_hz; g_last_dir = dir;
    g_dbg_freq  = (dir == AXIS_X_POSITIVE_DIR_LEVEL) ? freq_hz : -freq_hz;
}

static void Beam_TiltToAngle(float target_deg, uint32_t freq_hz)
{
    float now = Encoder_GetAngle(ENCODER_AXIS_X);
    /* 硬限位 ±CFG_ANGLE_LIMIT_DEG */
    if (target_deg >  CFG_ANGLE_LIMIT_DEG) target_deg =  CFG_ANGLE_LIMIT_DEG;
    if (target_deg < -CFG_ANGLE_LIMIT_DEG) target_deg = -CFG_ANGLE_LIMIT_DEG;
    float err = target_deg - now;
    g_dbg_target_angle = target_deg;
    g_dbg_angle_now    = now;
    /* 1.5° 滞回，高频下也不容易过冲振荡 */
    if (err > 1.5f)
        Motor_SetFreq((int32_t)freq_hz, AXIS_X_POSITIVE_DIR_LEVEL);
    else if (err < -1.5f)
        Motor_SetFreq((int32_t)freq_hz, (uint8_t)!AXIS_X_POSITIVE_DIR_LEVEL);
    else
        Motor_SetFreq(0, 0);
}

static void StepControl_Run(uint32_t now_ms)
{
    bool has_new, online, meas_valid;
    float pos_now;

    has_new = K230_RxUpdateCache(vision_INST_INT_IRQN);
    online  = K230_RxIsOnline(now_ms, CFG_K230_OFFLINE_MS);
    g_dbg_k230_online = online ? 1U : 0U;

    if (!online) {
        if (g_k230_was_online) {
            Motor_Stop(MOTOR_AXIS_X); g_last_freq = 0;
            g_state = STATE_STARTUP; g_filter_inited = false;
            g_k230_was_online = false;
        }
        return;
    }
    g_k230_was_online = true;

    meas_valid = (g_last_status == 1U) &&
                 (g_last_confidence >= CFG_MIN_CONFIDENCE) &&
                 (g_last_position != K230_INVALID_POSITION_MM);
    if (!meas_valid) { g_filter_inited = false; return; }

    if (!g_filter_inited) {
        g_ball_pos_filtered = (float)g_last_position;
        g_prev_pos = g_ball_pos_filtered;
        g_filter_inited = true;
    } else {
        float raw = (float)g_last_position;
        float jump = raw - g_ball_pos_filtered;
        float aj   = (jump >= 0.0f) ? jump : -jump;
        if (aj < 100.0f) {
            g_jump_count = 0U;
            g_ball_pos_filtered += CFG_POS_FILTER_ALPHA *
                (raw - g_ball_pos_filtered);
        } else {
            /* 大跳变：连续 3 帧同方向才信任（排除偶发毛刺） */
            float jdir = raw - g_jump_target;
            float jd   = (jdir >= 0.0f) ? jdir : -jdir;
            if (g_jump_count == 0U || jd < 20.0f) {
                g_jump_count++;
                g_jump_target = raw;
                if (g_jump_count >= 3U) {
                    g_ball_pos_filtered = raw;
                    g_jump_count = 0U;
                }
            } else {
                g_jump_count = 1U;
                g_jump_target = raw;
            }
        }
    }
    pos_now = g_ball_pos_filtered;
    g_ball_pos = pos_now;
    g_dbg_state = (uint8_t)g_state;

    switch (g_state) {

    case STATE_STOPPED:
        Motor_Stop(MOTOR_AXIS_X); g_last_freq = 0;
        break;

    case STATE_STARTUP:
        Motor_Stop(MOTOR_AXIS_X); g_last_freq = 0;
        if (g_startup_start_ms == 0U) g_startup_start_ms = now_ms;
        if ((uint32_t)(now_ms - g_startup_start_ms) >= CFG_STARTUP_DELAY_MS) {
            g_state = STATE_IDLE; g_state_enter_ms = now_ms;
        }
        break;

    case STATE_IDLE: {
        float err = pos_now - g_target_pos_mm;
        float ap  = (err >= 0.0f) ? err : -err;
        g_dbg_settled = (ap <= CFG_DEADBAND_MM) ? 1U : 0U;
        if (ap <= CFG_DEADBAND_MM) {
            g_state = STATE_SETTLED; g_state_enter_ms = now_ms;
            Motor_Stop(MOTOR_AXIS_X); g_last_freq = 0;
        } else {
            /* 进入 2.5cm 内先等球停稳再动作 */
            if (ap <= 25.0f) {
                float mv = pos_now - g_prev_pos;
                float md = (mv >= 0.0f) ? mv : -mv;
                g_prev_pos = pos_now;
                if (md < 8.0f) {          /* 阈值放宽, 容忍 K230 ±2mm 噪声 */
                    if (g_ball_still_cnt < 255U) g_ball_still_cnt++;
                } else {
                    g_ball_still_cnt = 0U;
                }
                /* 停稳 5 帧才动作; 但等待超过 500ms 强制动作,
                   避免球小幅振荡时电机一直不响应 */
                if (g_ball_still_cnt < 5U &&
                    (uint32_t)(now_ms - g_state_enter_ms) < 500U) {
                    break;
                }
                g_ball_still_cnt = 0U;
            } else {
                /* 远区同样刷新 prev，避免 RETURNING 的球静止检测
                   拿到几秒前的旧值而永远判为运动、只能等满 2s 超时 */
                g_prev_pos = pos_now;
            }
            g_start_pos = pos_now;
            g_tilt_dir  = (err < 0.0f) ? -1.0f : 1.0f;
            if (ap <= CFG_NEAR_ZONE_MM) {
                float ang = (g_tilt_dir > 0.0f) ? 8.0f : 12.0f;
                g_dbg_target_angle = -g_tilt_dir * ang;
                g_tilt_duration_ms = CFG_NEAR_TILT_MS;
                g_coast_wait_ms    = CFG_IDLE_COOLDOWN_MS;
                g_tilt_freq_hz     = 900U;
            } else {
                float ang = (g_tilt_dir > 0.0f) ? 10.0f : 15.0f;
                g_dbg_target_angle = -g_tilt_dir * ang;
                g_tilt_duration_ms = CFG_NEAR_TILT_MS;
                g_coast_wait_ms    = CFG_IDLE_COOLDOWN_MS;
                g_tilt_freq_hz     = 900U;
            }
            g_state = STATE_TILTING; g_state_enter_ms = now_ms;
        }
        break;
    }

    case STATE_TILTING:
        Beam_TiltToAngle(g_dbg_target_angle, g_tilt_freq_hz);
        {   float na = Encoder_GetAngle(ENCODER_AXIS_X);
            float t  = g_dbg_target_angle;
            float ae = (t - na >= 0.0f) ? t - na : na - t;
            if (ae < 1.5f || (uint32_t)(now_ms - g_state_enter_ms) > 500U) {
                Motor_SetFreq(0, 0);
                g_state = STATE_COASTING; g_state_enter_ms = now_ms;
            }
        }
        break;

    case STATE_COASTING: {
        /* 倾斜保持时间到 → 回平 */
        if ((uint32_t)(now_ms - g_state_enter_ms) >= g_tilt_duration_ms) {
            g_state = STATE_RETURNING; g_state_enter_ms = now_ms;
        }
        break;
    }

    case STATE_RETURNING:
        Beam_TiltToAngle(0.0f, CFG_RETURN_FREQ_HZ);
        {   float na = Encoder_GetAngle(ENCODER_AXIS_X);
            float ae = (na >= 0.0f) ? na : -na;
            if (ae < 1.5f || (uint32_t)(now_ms - g_state_enter_ms) > 1500U) {
                Motor_SetFreq(0, 0);
                /* 球速检测：帧间 < 6mm 算静止（K230 有 ±2mm 噪声, 放宽防误判） */
                float mv = pos_now - g_prev_pos;
                float md = (mv >= 0.0f) ? mv : -mv;
                g_prev_pos = pos_now;
                if (md < 6.0f) {
                    if (g_ball_still_cnt < 255U) g_ball_still_cnt++;
                } else {
                    g_ball_still_cnt = 0U;
                }
                /* 冷却期满 + 静止 3 帧，或超 2 秒强制放行 */
                if (((uint32_t)(now_ms - g_state_enter_ms) >= g_coast_wait_ms &&
                     g_ball_still_cnt >= 3U) ||
                    (uint32_t)(now_ms - g_state_enter_ms) > 2000U) {
                    g_ball_still_cnt = 0U;
                    g_state = STATE_IDLE; g_state_enter_ms = now_ms;
                }
            }
        }
        break;

    case STATE_SETTLED:
        Motor_Stop(MOTOR_AXIS_X); g_last_freq = 0;
        {   float err = pos_now - g_target_pos_mm;
            float ap  = (err >= 0.0f) ? err : -err;
            if (ap > CFG_DEADBAND_MM) {
                g_state = STATE_IDLE; g_state_enter_ms = now_ms;
            }
        }
        break;
    }
}

int main(void)
{
    uint32_t last_key_ms  = 0U;
    uint8_t  key_db_cnt   = 0U;
    uint8_t  key_was_down = 0U;
    uint8_t  task_running  = 0U;

    SYSCFG_DL_init();
    (void)SysTick_Config(CPUCLK_FREQ / 1000U);

    K230_RxInit();
    Motor_Init();
    Encoder_Init();
    Motor_Stop(MOTOR_AXIS_X);
    g_state = STATE_STOPPED;
    delay_ms(100);

    while (!DL_UART_Main_isRXFIFOEmpty(vision_INST))
        (void)DL_UART_Main_receiveData(vision_INST);
    NVIC_ClearPendingIRQ(vision_INST_INT_IRQN);
    NVIC_EnableIRQ(vision_INST_INT_IRQN);
    NVIC_ClearPendingIRQ(TIMER_0_INST_INT_IRQN);
    NVIC_EnableIRQ(TIMER_0_INST_INT_IRQN);
    DL_TimerG_startCounter(TIMER_0_INST);

    Motor_Stop(MOTOR_AXIS_X);  /* 最后一刻再停一次，确保无脉冲 */

    while (1) {
        uint32_t now = g_system_ms;

        if (task_running) {
            StepControl_Run(now);
        }

        if ((uint32_t)(now - last_key_ms) >= 20U) {
            last_key_ms = now;
            uint8_t pressed = (DL_GPIO_readPins(GPIOB, DL_GPIO_PIN_21) == 0U) ? 1U : 0U;
            if (pressed) {
                if (key_db_cnt < 255U) key_db_cnt++;
                if (key_db_cnt >= 3U && key_was_down == 0U) {
                    key_was_down = 1U;
                    if (task_running) {
                        task_running = 0U;
                        Motor_Stop(MOTOR_AXIS_X); g_last_freq = 0;
                        g_state = STATE_STOPPED;
                    } else {
                        task_running = 1U;
                        Encoder_SetZero(ENCODER_AXIS_X);
                        g_filter_inited = false;
                        g_state = STATE_STARTUP; g_startup_start_ms = 0U;
                    }
                }
            } else { key_db_cnt = 0U; key_was_down = 0U; }
        }
    }
}
