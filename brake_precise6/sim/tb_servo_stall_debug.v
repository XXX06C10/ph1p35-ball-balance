`timescale 1ns/1ps
module tb_servo_stall_debug;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,enable=0,k4=1,req=0,following=0,cancel=0,fastmode=0,vis_valid=1,vis_stale=0,settings=1,changed=0;
 reg signed [15:0] rate=0;reg signed [31:0] enc=0;
 reg signed [15:0] target=48;
 wire en,step,ready,busy,reached;
 wire [3:0] fault,reject,cancel_reason;
 wire signed [31:0] pos,error,cmd;
 wire [7:0] spent,pending;
 vision_servo_core #(.TARGET_BITS(16),.ASYM_LIMITS(1),.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.FAST_CAPABLE(1),.CHECKPOINT_CAPABLE(1),.TAIL_CHECKPOINT(1),.FAST_MS_CYCLES(50),.ENABLE_CYCLES(20),.FOLLOW_SETUP_CYCLES(2),.HALF_CYCLES(2),.FOLLOW_SETTLE_CYCLES(2),.TIMEOUT_CYCLES(10000),.DEBOUNCE_CYCLES(2)) dut(
 .clk(clk),.rst_n(rst),.enable_request(enable),.k4_n(k4),.k2_n(1'b1),.request(req),.following(following),.external_cancel(cancel),.external_cancel_reason(4'd0),.fast_mode(fastmode),.fast_rate_hz(rate),.checkpoint(1'b0),.encoder_count(enc),.encoder_errors(16'd0),.visual_valid(vis_valid),.visual_stale(vis_stale),.settings_ready(settings),.config_changed(changed),.visual_target(target),.target_min(-32'sd182),.target_max(32'sd364),.feedback_min(-32'sd204),.feedback_max(32'sd398),.command_min(-32'sd159),.command_max(32'sd310),.motor_en(en),.motor_dir(),.motor_step(step),.command_position(cmd),.locked_target(),.position(pos),.error(error),.state(),.fault(fault),.cancel_reason(cancel_reason),.reject_reason(reject),.spent(spent),.origin_valid(),.ready(ready),.busy(busy),.reached(reached),.accepted_count(),.completed_count(),.diag_pending(pending),.diag_commands(),.diag_delta(),.diag_consistent(),.diag_wrong());
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 always @(negedge clk)if(busy)$display("DBG state=%0d fault=%0d sp=%0d pos=%0d cmd=%0d err=%0d fastms=%0d credit=%0d count=%0d age=%0d quiet=%0d rate=%0d",dut.state,fault,spent,pos,cmd,error,dut.fast_ms,dut.fast_credit,dut.fast_count,dut.fast_age,dut.fast_quiet_age,rate);
 initial begin
  tick(3);rst=1;enable=1;enc=-15;wait(ready);tick(3);
  following=1;fastmode=1;rate=200;req=1;tick(1);req=0;
  tick(5000);
  $display("RESULT state=%0d fault=%0d sp=%0d pos=%0d cmd=%0d err=%0d",dut.state,fault,spent,pos,cmd,error);
  $finish;
 end
endmodule
