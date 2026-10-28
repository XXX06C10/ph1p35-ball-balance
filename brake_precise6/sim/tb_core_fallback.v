`timescale 1ns/1ps
// Force the legacy credit path to remain zero. The independent CHECK retry must
// still emit bounded pulses, while real no-feedback protection must latch F1.
module tb_core_fallback;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,enable=1,k4=1,req=0,following=1,cancel=0,fastmode=1;
 reg signed [15:0] rate=200;reg signed [31:0] enc=0;
 wire en,step,ready,busy,reached;
 wire [3:0] fault;
 wire signed [31:0] pos,error,cmd;
 wire [7:0] spent,pending;
 vision_servo_core #(.TARGET_BITS(16),.ASYM_LIMITS(1),.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.FAST_CAPABLE(1),.CHECKPOINT_CAPABLE(1),.TAIL_CHECKPOINT(1),.FAST_MS_CYCLES(50),.ENABLE_CYCLES(20),.FOLLOW_SETUP_CYCLES(2),.HALF_CYCLES(2),.FOLLOW_SETTLE_CYCLES(2),.TIMEOUT_CYCLES(10000),.DEBOUNCE_CYCLES(2)) dut(
 .clk(clk),.rst_n(rst),.enable_request(enable),.k4_n(k4),.k2_n(1'b1),.request(req),.following(following),.external_cancel(cancel),.external_cancel_reason(4'd0),.fast_mode(fastmode),.fast_rate_hz(rate),.checkpoint(1'b0),.encoder_count(enc),.encoder_errors(16'd0),.visual_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.config_changed(1'b0),.visual_target(16'sd48),.target_min(-32'sd182),.target_max(32'sd364),.feedback_min(-32'sd204),.feedback_max(32'sd398),.command_min(-32'sd159),.command_max(32'sd310),.motor_en(en),.motor_dir(),.motor_step(step),.command_position(cmd),.locked_target(),.position(pos),.error(error),.state(),.fault(fault),.cancel_reason(),.reject_reason(),.spent(spent),.origin_valid(),.ready(ready),.busy(busy),.reached(reached),.accepted_count(),.completed_count(),.diag_pending(pending),.diag_commands(),.diag_delta(),.diag_consistent(),.diag_wrong());
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 initial begin
  tick(3);rst=1;enc=-15;wait(ready);tick(3);
  force dut.fast_credit=0;
  req=1;tick(1);req=0;
  wait(fault!=0);
  if(fault!=1 || spent<3 || spent>8)$fatal(1,"fallback guard failed F=%0d SP=%0d",fault,spent);
  $display("CORE_FALLBACK_PASS forcedzeroCredit emitsSTEP,F1realnoresponse,SP=%0d",spent);
  release dut.fast_credit;$finish;
 end
 initial begin #1000000;$fatal(1,"fallback timeout F=%0d SP=%0d",fault,spent);end
endmodule
