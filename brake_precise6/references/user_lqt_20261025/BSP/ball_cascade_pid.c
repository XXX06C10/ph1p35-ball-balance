#include "ball_cascade_pid.h"

#define BALL_PID_INVALID_POSITION_MM (32767.0f)

static float ClampFloat(float value, float lower, float upper)
{
    if (value > upper)
    {
        return upper;
    }
    if (value < lower)
    {
        return lower;
    }
    return value;
}

static float AbsFloat(float value)
{
    return (value >= 0.0f) ? value : -value;
}

static int32_t FloatToInt32Rounded(float value)
{
    if (value >= 0.0f)
    {
        return (int32_t)(value + 0.5f);
    }
    return (int32_t)(value - 0.5f);
}

void BallCascadePID_GetDefaultConfig(BallCascadePIDConfig *config)
{
    if (config == (BallCascadePIDConfig *)0)
    {
        return;
    }

    /*
     * 下面的初值来自用户给出的简略代码。
     * 它们只是调试起点，必须按照“先速度环、后位置环”的顺序整定。
     */
    config->position_kp = 2.6f;
    config->position_ki = 0.0f;
    config->position_kd = 1.3f;
    config->position_integral_limit = 3000.0f;
    config->target_speed_limit_mm_s = 300.0f;

    config->velocity_kp = 20.0f;
    config->velocity_ki = 20.0f;
    config->velocity_kd = 0.0f;
    config->motor_command_limit = 7000.0f;

    config->position_deadband_mm = 1.0f;
    config->velocity_deadband_mm_s = 5.0f;
    config->motor_polarity = 1;
}

void BallCascadePID_Reset(BallCascadePID *controller)
{
    if (controller == (BallCascadePID *)0)
    {
        return;
    }

    controller->position_integral = 0.0f;
    controller->position_last_error = 0.0f;

    controller->velocity_last_error = 0.0f;
    controller->velocity_last_last_error = 0.0f;
    controller->velocity_output = 0.0f;

    controller->position_initialized = false;
    controller->velocity_initialized = false;
}

void BallCascadePID_Init(BallCascadePID *controller,
                         const BallCascadePIDConfig *config,
                         float target_position_mm)
{
    BallCascadePIDConfig default_config;

    if (controller == (BallCascadePID *)0)
    {
        return;
    }

    if (config == (const BallCascadePIDConfig *)0)
    {
        BallCascadePID_GetDefaultConfig(&default_config);
        controller->config = default_config;
    }
    else
    {
        controller->config = *config;
    }

    /* 防止方向参数被误设为 0 或其他值。 */
    controller->config.motor_polarity =
        (controller->config.motor_polarity < 0) ? -1 : 1;

    controller->target_position_mm = target_position_mm;
    BallCascadePID_Reset(controller);
}

void BallCascadePID_SetTarget(BallCascadePID *controller,
                              float target_position_mm)
{
    if (controller == (BallCascadePID *)0)
    {
        return;
    }

    controller->target_position_mm = target_position_mm;
}

static float PositionPID_Update(BallCascadePID *controller,
                                float position_error_mm)
{
    float derivative;
    float integral_candidate;
    float output_without_integral;
    float output_candidate;
    float speed_limit;

    speed_limit = AbsFloat(controller->config.target_speed_limit_mm_s);

    if (!controller->position_initialized)
    {
        /*
         * 第一次进入控制时令微分项为 0，避免目标值或测量值突变造成
         * derivative kick。
         */
        controller->position_last_error = position_error_mm;
        controller->position_initialized = true;
    }

    derivative = position_error_mm - controller->position_last_error;

    integral_candidate =
        controller->position_integral + position_error_mm;
    integral_candidate = ClampFloat(
        integral_candidate,
        -AbsFloat(controller->config.position_integral_limit),
        AbsFloat(controller->config.position_integral_limit));

    output_without_integral =
        controller->config.position_kp * position_error_mm +
        controller->config.position_kd * derivative;

    output_candidate =
        output_without_integral +
        controller->config.position_ki * integral_candidate;

    /*
     * 条件积分抗饱和：
     * 当输出已经在上限且误差仍要推动其增大时，不继续积分；
     * 下限情况同理。
     */
    if (!((output_candidate > speed_limit && position_error_mm > 0.0f) ||
          (output_candidate < -speed_limit && position_error_mm < 0.0f)))
    {
        controller->position_integral = integral_candidate;
    }

    output_candidate =
        output_without_integral +
        controller->config.position_ki * controller->position_integral;

    controller->position_last_error = position_error_mm;

    return ClampFloat(output_candidate, -speed_limit, speed_limit);
}

static float VelocityIncrementalPID_Update(BallCascadePID *controller,
                                           float velocity_error_mm_s)
{
    float proportional_delta;
    float integral_delta;
    float derivative_delta;
    float output_without_integral;
    float output_candidate;
    float command_limit;

    command_limit = AbsFloat(controller->config.motor_command_limit);

    if (!controller->velocity_initialized)
    {
        /*
         * 首次调用不使用误差差分项，避免输出突跳；积分项仍可立即起效。
         */
        controller->velocity_last_error = velocity_error_mm_s;
        controller->velocity_last_last_error = velocity_error_mm_s;
        controller->velocity_initialized = true;
    }

    /*
     * 标准增量式 PID：
     * Δu(k) = Kp[e(k)-e(k-1)] + Ki*e(k)
     *       + Kd[e(k)-2e(k-1)+e(k-2)]
     */
    proportional_delta =
        controller->config.velocity_kp *
        (velocity_error_mm_s - controller->velocity_last_error);

    integral_delta =
        controller->config.velocity_ki * velocity_error_mm_s;

    derivative_delta =
        controller->config.velocity_kd *
        (velocity_error_mm_s -
         2.0f * controller->velocity_last_error +
         controller->velocity_last_last_error);

    output_without_integral =
        controller->velocity_output +
        proportional_delta +
        derivative_delta;

    output_candidate = output_without_integral + integral_delta;

    /*
     * 条件积分抗饱和。若积分项只会让饱和进一步加重，则本周期舍弃积分项。
     */
    if ((output_candidate > command_limit && integral_delta > 0.0f) ||
        (output_candidate < -command_limit && integral_delta < 0.0f))
    {
        output_candidate = output_without_integral;
    }

    controller->velocity_output =
        ClampFloat(output_candidate, -command_limit, command_limit);

    controller->velocity_last_last_error =
        controller->velocity_last_error;
    controller->velocity_last_error = velocity_error_mm_s;

    return controller->velocity_output;
}

BallCascadePIDOutput BallCascadePID_UpdateVelocityOnly(
    BallCascadePID *controller,
    float target_velocity_mm_s,
    float current_velocity_mm_s,
    bool measurement_valid)
{
    BallCascadePIDOutput result = {0};
    float speed_limit;
    float raw_motor_command;

    if (controller == (BallCascadePID *)0)
    {
        return result;
    }

    if (!measurement_valid)
    {
        BallCascadePID_Reset(controller);
        return result;
    }

    speed_limit = AbsFloat(controller->config.target_speed_limit_mm_s);
    result.valid = true;
    result.target_velocity_mm_s =
        ClampFloat(target_velocity_mm_s, -speed_limit, speed_limit);
    result.velocity_error_mm_s =
        result.target_velocity_mm_s - current_velocity_mm_s;

    raw_motor_command =
        VelocityIncrementalPID_Update(controller,
                                      result.velocity_error_mm_s);
    raw_motor_command *= (float)controller->config.motor_polarity;
    result.motor_command = FloatToInt32Rounded(raw_motor_command);

    return result;
}

BallCascadePIDOutput BallCascadePID_Update(
    BallCascadePID *controller,
    float position_mm,
    float velocity_mm_s,
    bool measurement_valid)
{
    BallCascadePIDOutput result = {0};
    float raw_motor_command;

    if (controller == (BallCascadePID *)0)
    {
        return result;
    }

    /*
     * 视觉丢失、UART 校验失败或收到 32767 mm 哨兵值时立即安全停机，
     * 同时清除历史量，防止重新识别后沿用旧积分造成突跳。
     */
    if (!measurement_valid ||
        position_mm >= (BALL_PID_INVALID_POSITION_MM - 0.5f))
    {
        BallCascadePID_Reset(controller);
        return result;
    }

    result.valid = true;
    result.position_error_mm =
        controller->target_position_mm - position_mm;

    /*
     * 只有位置和速度同时足够接近目标，才认为已经稳定并停止。
     */
    if (AbsFloat(result.position_error_mm) <=
            AbsFloat(controller->config.position_deadband_mm) &&
        AbsFloat(velocity_mm_s) <=
            AbsFloat(controller->config.velocity_deadband_mm_s))
    {
        result.settled = true;
        BallCascadePID_Reset(controller);
        return result;
    }

    result.target_velocity_mm_s =
        PositionPID_Update(controller, result.position_error_mm);

    result.velocity_error_mm_s =
        result.target_velocity_mm_s - velocity_mm_s;

    raw_motor_command =
        VelocityIncrementalPID_Update(controller,
                                      result.velocity_error_mm_s);

    raw_motor_command *= (float)controller->config.motor_polarity;
    result.motor_command = FloatToInt32Rounded(raw_motor_command);

    return result;
}