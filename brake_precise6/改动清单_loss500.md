# loss500修改清单

像素检测：steel_ball_detect.v增加局部弱红色判据和独立换行坐标；steel_ball_stream_bbox.v增加2帧跟踪历史；design_top_wrapper.v连接真实跟踪中心。

控制：新增vision_result_guard.v的500ms有效球计时；vision_follow_control.v冻结AT/T、恢复重建速度、保持会话计时；vision_monitor.v统一执行器/会话许可，原始V/Q/B/AGE及严格启动/K3保留。compose.py包含新模块。

上位机vision_panel_cn.ps1显示短丢保持并增加自检；decode_serial.py区分保持与错误非零目标。analyze_follow.py未改变有效样本口径。

测试：新增tb_loss.v和tb_rgb.v；tb_follow.v延长持续无效测试并连接新门控端口；tb_detector.v更新短丢快速恢复预期；run_sim.ps1加入两套测试及无缓冲日志。

构建与核对：build.ps1产生loss500交付副本；verify.py保留基线和所有器件/引脚/时序检查，检测路径仅放行三份明确文件，新增真实RGB与保持波形检查。新增prepare_loss500.py、publish_loss500.py及loss500_lineage.json。

原运动核心vision_servo_core.v、vision_move_core.v、enable_latch.v、encoder_ab_counter.v、vision_shadow_target.v、vision_config_rx.v、vision_report_tx.v、UART生成器、P/V/S格式、ADC/SDC及器件工程文件保持逐字节不变。详见loss500_changes.diff和verification.json。
