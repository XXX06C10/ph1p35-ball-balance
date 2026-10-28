#ifndef BALL_CASCADE_PID_H
#define BALL_CASCADE_PID_H

#include <stdbool.h>
#include <stdint.h>

/*
 * 小球串级 PID 控制器
 *
 * 外环：位置误差 -> 目标速度
 * 内环：速度误差 -> 有符号电机指令
 *
 * 单位约定：
 *   position_mm        : mm
 *   velocity_mm_s      : mm/s
 *   target_position_mm : mm
 *
 * 调用周期必须基本固定。若直接使用 K230 的新数据帧，建议每收到一帧
 * 有效数据调用一次（当前发送周期约为 30 ms）。
 */

typedef struct
{
    /* 外环：位置式 PID 参数。默认 Ki=0，即先使用 PD。 */
    float position_kp;
    float position_ki;
    float position_kd;

    /* 外环积分累计值限幅，单位为“位置误差采样点”。 */
    float position_integral_limit;

    /* 外环输出，即目标小球速度的绝对值上限，单位 mm/s。 */
    float target_speed_limit_mm_s;

    /* 内环：增量式 PID 参数。 */
    float velocity_kp;
    float velocity_ki;
    float velocity_kd;

    /* 内环输出，即有符号电机指令的绝对值上限。 */
    float motor_command_limit;

    /* 进入稳定区后停止电机，用于减小中心附近抖动。 */
    float position_deadband_mm;
    float velocity_deadband_mm_s;

    /*
     * 机械方向系数，只允许设为 +1 或 -1。
     * 若小球误差越来越大而不是减小，将它由 +1 改为 -1。
     */
    int8_t motor_polarity;
} BallCascadePIDConfig;

typedef struct
{
    BallCascadePIDConfig config;

    float target_position_mm;

    float position_integral;
    float position_last_error;

    float velocity_last_error;
    float velocity_last_last_error;
    float velocity_output;

    bool position_initialized;
    bool velocity_initialized;
} BallCascadePID;

typedef struct
{
    /* false 表示视觉数据无效，此时 motor_command 恒为 0。 */
    bool valid;

    /* true 表示位置和速度均进入设定的稳定死区。 */
    bool settled;

    float position_error_mm;
    float target_velocity_mm_s;
    float velocity_error_mm_s;

    /*
     * 有符号电机指令：
     *   正负号 -> 电机方向
     *   绝对值 -> PWM、脉冲频率或驱动函数的速度参数
     */
    int32_t motor_command;
} BallCascadePIDOutput;

/* 载入与用户原始代码相对应的一组初始参数。 */
void BallCascadePID_GetDefaultConfig(BallCascadePIDConfig *config);

/* 初始化控制器并设置目标位置。 */
void BallCascadePID_Init(BallCascadePID *controller,
                         const BallCascadePIDConfig *config,
                         float target_position_mm);

/* 清除 PID 历史状态，但保留参数和目标位置。 */
void BallCascadePID_Reset(BallCascadePID *controller);

/* 在线修改目标位置，不会清除控制器历史状态。 */
void BallCascadePID_SetTarget(BallCascadePID *controller,
                              float target_position_mm);

/*
 * 每收到一组新的位置/速度数据时调用一次。
 *
 * measurement_valid 应同时满足：
 *   1. UART 帧 status == 1；
 *   2. position_mm != 32767（无效位置哨兵值）；
 *   3. UART 异或校验正确。
 */
BallCascadePIDOutput BallCascadePID_Update(
    BallCascadePID *controller,
    float position_mm,
    float velocity_mm_s,
    bool measurement_valid);

/*
 * 速度环单独整定接口。
 *
 * 调节速度环时暂时不要调用 BallCascadePID_Update()，而是直接给定一个
 * 较小的 target_velocity_mm_s，通过本函数观察速度响应。速度环稳定后，
 * 先调用 BallCascadePID_Reset()，再切回完整串级控制。
 */
BallCascadePIDOutput BallCascadePID_UpdateVelocityOnly(
    BallCascadePID *controller,
    float target_velocity_mm_s,
    float current_velocity_mm_s,
    bool measurement_valid);

#endif /* BALL_CASCADE_PID_H */