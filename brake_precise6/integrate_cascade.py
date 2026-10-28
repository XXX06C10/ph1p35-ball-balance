from pathlib import Path
r=Path.cwd();before=Path('D:/AAAProject/FPGA/AAA_LookHere/交付_20261024_保护保持锁定/project')
newmods=['vision_cascade_config.v','vision_cascade_outer.v','vision_cascade_control.v','vision_cascade_diag.v']
for name in newmods+['vision_servo_core.v','vision_report_tx.v']:(r/'rtl'/name).write_text((r/'cascade_work'/name).read_text(encoding='utf-8-sig'),encoding='utf-8')
s=(before/'compose.py').read_text(encoding='utf-8-sig').replace("parts=['enable_latch.v'","parts="+repr(newmods)+"+['enable_latch.v'")
(r/'compose.py').write_text(s,encoding='utf-8')
s=(before/'rtl/vision_monitor.v').read_text(encoding='utf-8-sig').replace('DEFAULT_RUNTIME=60,','DEFAULT_RUNTIME=60,CASCADE_DEFAULT=0,')
# Existing declarations stay at their original locations; new wires precede use.
anchor='    wire [15:0] accepted_count,completed_count;'
insert='''
    wire c_applied,c_commit,c_diagnostics,c_polarity;
    wire [15:0] c_sequence,c_errors,c_kp,c_kv,c_ki,c_inner_kp,c_ff,c_max_hz,c_slew;
    wire signed [15:0] c_bias;
    wire [7:0] c_selection,c_delay,c_amplitude;
    wire c_selected=c_selection!=0 && operating_mode==1;
    wire effective_settings_ready=c_selected && c_selection==2 ? !settings_busy : settings_ready;
    wire l_run,l_request,l_following,l_external_cancel,l_neutral_ready;
    wire [3:0] l_external_reason,l_stop,l_reject;
    wire signed [7:0] l_target,l_drive;
    wire signed [15:0] l_velocity;
    wire [15:0] l_elapsed;wire [31:0] l_pulses;
    wire n_run,n_request,n_following,n_external_cancel,n_neutral_ready,n_updated,n_stable;
    wire [3:0] n_external_reason,n_stop,n_reject,n_cal_status,n_cal_phase;
    wire signed [7:0] n_target,n_drive,n_neutral;
    wire signed [15:0] n_velocity_legacy,n_frequency;
    wire signed [31:0] n_raw_q8,n_reference_q8,n_velocity;
    wire [15:0] n_elapsed;wire [31:0] n_pulses,n_time,n_frame_time;
    wire legacy_tx,legacy_busy,legacy_wants,diag_tx,diag_busy;
    reg c_fresh=0,c_profile_ready=0;
    always @(posedge clk)begin
      if(!rst_n || applied || center_request || settings_busy)c_profile_ready<=0;
      else if(c_applied)c_profile_ready<=c_selection==1 && (c_kp!=0 || c_kv!=0);
      if(!rst_n || c_applied || applied || settings_busy)c_fresh<=0;
      else if(result_frame && valid && !incoming_bad)c_fresh<=1;
    end
    assign auto_run=c_selected ? n_run : l_run;
    assign request=c_selected ? n_request : l_request;
    assign following=c_selected ? n_following : l_following;
    assign external_cancel=c_selected ? n_external_cancel : l_external_cancel;
    assign external_cancel_reason=c_selected ? n_external_reason : l_external_reason;
    assign neutral_ready=c_selected ? n_neutral_ready : l_neutral_ready;
    assign stop_reason=c_selected ? n_stop : l_stop;
    assign supervisor_reject=c_selected ? n_reject : l_reject;
    assign drive_target=c_selected ? n_drive : l_drive;
    assign target=c_selected ? ((valid || n_run || c_selection==2) ? n_target : 8'sd0) : l_target;
    assign velocity=c_selected ? n_velocity_legacy : l_velocity;
    assign elapsed_seconds=c_selected ? n_elapsed : l_elapsed;
    assign total_pulses=c_selected ? n_pulses : l_pulses;
    assign tx=legacy_busy ? legacy_tx : diag_tx;
'''
s=s.replace(anchor,anchor+insert)
# incoming_bad declaration must precede new freshness always block in this Verilog toolchain.
s=s.replace('else if(result_frame && valid && !incoming_bad)c_fresh<=1;','else if(result_frame && valid)c_fresh<=1;')
s=s.replace('wire executor_valid=(auto_run && operating_mode==1) ? hold_valid : (valid && !incoming_bad);',"wire executor_valid=(c_selected && c_selection==2 && n_run) ? 1'b1 : ((auto_run && operating_mode==1) ? hold_valid : (valid && !incoming_bad));")
a=s.index('    vision_follow_control #');b=s.index('    vision_servo_core #',a)
block=s[a:b]
mp={'key_event(key2_event)':'key_event(key2_event && !c_selected)','config_changed(applied || center_request)':'config_changed(applied || center_request || c_applied)',
 'request(request)':'request(l_request)','following(following)':'following(l_following)','neutral_ready(neutral_ready)':'neutral_ready(l_neutral_ready)',
 'external_cancel(external_cancel)':'external_cancel(l_external_cancel)','external_cancel_reason(external_cancel_reason)':'external_cancel_reason(l_external_reason)',
 'run(auto_run)':'run(l_run)','stop_reason(stop_reason)':'stop_reason(l_stop)','reject_reason(supervisor_reject)':'reject_reason(l_reject)',
 'drive_target(drive_target)':'drive_target(l_drive)','candidate(target)':'candidate(l_target)','velocity(velocity)':'velocity(l_velocity)',
 'elapsed_seconds(elapsed_seconds)':'elapsed_seconds(l_elapsed)','total_pulses(total_pulses)':'total_pulses(l_pulses)'}
for x,y in mp.items():block=block.replace('.'+x,'.'+y)
s=s[:a]+block+s[b:]
s=s.replace('vision_servo_core #(.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),','vision_servo_core #(.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.FAST_CAPABLE(1),.FAST_MS_CYCLES(MS_CYCLES),')
s=s.replace('.encoder_count(count1),.encoder_errors(errors1),.visual_valid(executor_valid),.visual_stale(age>=STALE_MS),',".fast_mode(c_selected && (n_run || busy)),.fast_rate_hz(n_frequency),\n        .encoder_count(count1),.encoder_errors(errors1),.visual_valid(executor_valid),.visual_stale(c_selected && c_selection==2 ? 1'b0 : age>=STALE_MS),")
s=s.replace('.config_changed(applied || center_request),.visual_target(drive_target)', '.config_changed(applied || center_request || c_applied),.visual_target(drive_target)')
a=s.index('    wire request_ready=');b=s.index('\n    assign led=',a)
s=s[:a]+'''    wire request_ready=(c_selected ? (ready && (c_selection==2 || (valid && !incoming_bad && age<STALE_MS && c_fresh))) : (auto_run || (ready && valid && !incoming_bad && age<STALE_MS))) && effective_settings_ready && !applied && !c_applied && !center_request && fault==0 && (operating_mode!=1 || (center_confirmed && neutral_ready && (!c_selected || c_selection!=1 || c_profile_ready)));'''+s[b:]
s=s.replace('vision_report_tx #(.UART_DIV(UART_DIV),.REPORT_CYCLES(REPORT_CYCLES))','vision_report_tx #(.UART_DIV(UART_DIV),.REPORT_CYCLES(REPORT_CYCLES),.SHARED_TX(1))')
s=s.replace('.total_pulses(total_pulses),.tx(tx));','.total_pulses(total_pulses),.grant(!diag_busy),.busy(legacy_busy),.wants(legacy_wants),.tx(legacy_tx));')
newinst='''
    vision_cascade_config #(.UART_DIV(UART_DIV),.TIMEOUT_CYCLES(PACKET_TIMEOUT_CYCLES),.DEFAULT_SELECTION(CASCADE_DEFAULT)) cascade_config(
     .clk(clk),.rst_n(rst_n),.rx(rx),.applied(c_applied),.commit_now(c_commit),.config_seq(c_sequence),.errors(c_errors),.selection(c_selection),
     .diagnostics(c_diagnostics),.polarity(c_polarity),.kp(c_kp),.kv(c_kv),.ki(c_ki),.inner_kp(c_inner_kp),.feedforward(c_ff),
     .max_hz(c_max_hz),.slew_rate(c_slew),.bias(c_bias),.delay_ms(c_delay),.amplitude(c_amplitude));
    vision_cascade_outer #(.MS_CYCLES(MS_CYCLES)) cascade_outer(
     .clk(clk),.rst_n(rst_n),.run(n_run && c_selected),.frame(result_frame),.valid(valid && !incoming_bad),.stale(age>=STALE_MS),
     .clear(applied || c_applied || settings_busy),.neutral_capture(center_applied),.polarity(c_polarity),.x(x),.center(center),.deadzone(deadzone),
     .kp(c_kp),.kv(c_kv),.ki(c_ki),.limit(limit),.delay_ms(c_delay),.bias(c_bias),.position(position),.target_q8(n_raw_q8),
     .velocity_q4(n_velocity),.legacy_velocity_q4(n_velocity_legacy),.neutral(n_neutral),.neutral_ready(n_neutral_ready),
     .updated(n_updated),.stable(n_stable),.time_ms(n_time),.frame_time_ms(n_frame_time));
    vision_cascade_control #(.MS_CYCLES(MS_CYCLES)) cascade_control(
     .clk(clk),.rst_n(rst_n),.key_event(key2_event && c_selected),.k4_n(key_n[3]),.enable_request(enable_request),
     .settings_ready(effective_settings_ready && (c_selection==2 || c_fresh)),.center_confirmed(center_confirmed),
     .valid(valid && !incoming_bad),.hold_valid(hold_valid),.stale(age>=STALE_MS),.frame(result_frame),
     .config_changed(applied || c_applied || center_request || !c_selected),.neutral_capture(center_applied),
     .profile_ready(c_profile_ready),.selection(c_selection),.amplitude(c_amplitude),.limit(limit),.max_hz(c_max_hz),.inner_kp(c_inner_kp),.feedforward(c_ff),
     .slew_rate(c_slew),.runtime_seconds(runtime_seconds),.kp(c_kp),.kv(c_kv),.roi_left(roi_left),.roi_right(roi_right),.center(center),.x(x),
     .position(position),.command_position(command_position),.raw_target_q8(n_raw_q8),.outer_updated(n_updated),.neutral_ready(n_neutral_ready),.neutral(n_neutral),
     .core_ready(ready),.core_busy(busy),.fault(fault),.step(motor_step),.run(n_run),.request(n_request),.following(n_following),
     .external_cancel(n_external_cancel),.external_cancel_reason(n_external_reason),.stop_reason(n_stop),.reject_reason(n_reject),
     .cal_status(n_cal_status),.cal_phase(n_cal_phase),.reference_q8(n_reference_q8),.frequency_hz(n_frequency),.target(n_target),.drive_target(n_drive),
     .elapsed_seconds(n_elapsed),.total_pulses(n_pulses));
    vision_cascade_diag #(.UART_DIV(UART_DIV),.MS_CYCLES(MS_CYCLES)) cascade_diag(
     .clk(clk),.rst_n(rst_n),.enabled(c_diagnostics),.grant(!legacy_busy && !legacy_wants),.tx(diag_tx),.busy(diag_busy),
     .time_ms(n_time),.frame_ms(n_frame_time),.config_seq(c_sequence),.selection(c_selection),
     .flags({7'd0,c_profile_ready,center_confirmed,busy,n_stable,age>=STALE_MS,valid,auto_run,motor_en,origin_valid}),
     .cal_phase({4'd0,n_cal_phase}),.cal_status({4'd0,n_cal_status}),.x({5'd0,x}),.center(center),.position(position),
     .reference_q8(n_reference_q8),.velocity_q4(n_velocity),.frequency_hz(n_frequency),.fault({4'd0,fault}),.spent(spent),
     .command_position(command_position),.frame_number(frames),.neutral(n_neutral),.config_errors(c_errors));
'''
s=s.replace('.settings_ready(settings_ready),.config_changed(applied || center_request || c_applied)', '.settings_ready(effective_settings_ready),.config_changed(applied || center_request || c_applied)')
s=s.replace('assign center_request=center_event && key_n[3]', 'assign center_request=center_event && !c_commit && key_n[3]')
s=s.replace('else if(center_conflict)center_status<=7;', 'else if(center_conflict || (center_event && c_commit))center_status<=7;')
s=s.replace('endmodule',newinst+'endmodule')
(r/'rtl/vision_monitor.v').write_text(s,encoding='utf-8')
p=r/'user_source/hdl_source/design_top_wrapper.v';s=p.read_text(encoding='utf-8-sig').replace('vision_monitor u_vision_monitor(', 'vision_monitor #(.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1)) u_vision_monitor(');s=s.replace('vision_monitor #(.DEFAULT_RUNTIME(0)) u_vision_monitor(', 'vision_monitor #(.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1)) u_vision_monitor(');p.write_text(s,encoding='utf-8')
(r/'diagnostic_schema.json').write_text((r/'cascade_work/diagnostic_schema.json').read_text(encoding='utf-8'),encoding='utf-8')
print('CASCADE_INTEGRATION_APPLIED')
