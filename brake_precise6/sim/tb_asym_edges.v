`timescale 1ns/1ps
module asym_edge #(parameter CASE=0)(output reg done=0);
 reg clk=0;always #5 clk=~clk;reg rst=0,request=0;reg signed [31:0] enc=0;
 wire en,step,ready;wire [3:0] fault,reject;
 vision_servo_core #(.TARGET_BITS(16),.ASYM_LIMITS(1),.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.FAST_CAPABLE(1),.FAST_MS_CYCLES(10),.ENABLE_CYCLES(20),.FOLLOW_SETUP_CYCLES(50),.HALF_CYCLES(25),.TIMEOUT_CYCLES(50000)) dut(
 .clk(clk),.rst_n(rst),.enable_request(1'b1),.k4_n(1'b1),.k2_n(1'b1),.request(request),.following(1'b1),.external_cancel(1'b0),.external_cancel_reason(4'd0),.fast_mode(1'b1),.fast_rate_hz(-16'sd200),.encoder_count(enc),.encoder_errors(16'd0),
 .visual_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.config_changed(1'b0),.visual_target(CASE==3 ? 16'sd365 : -16'sd182),
 .target_min(-32'sd182),.target_max(32'sd364),.feedback_min(-32'sd204),.feedback_max(32'sd398),.command_min(-32'sd159),.command_max(32'sd310),
 .motor_en(en),.motor_step(step),.ready(ready),.fault(fault),.reject_reason(reject));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 initial begin
  tick(5);rst=1;wait(ready);tick(5);
  if(CASE<2)begin
   enc=CASE==0 ? 204 : -398;tick(10);if(fault || !en)$fatal(1,"inclusive feedback boundary rejected");
   enc=CASE==0 ? 205 : -399;tick(10);if(fault!=7 || step || !en)$fatal(1,"feedback outside boundary not stopped");
  end else begin
   if(CASE==2)dut.command_position=-159;request=1;tick(1);request=0;
   if(CASE==2)begin wait(fault!=0);if(fault!=6 || step)$fatal(1,"negative command boundary bypass");end
   else begin tick(1000);if(fault || !ready || reject!=7 || step || dut.spent!=0)$fatal(1,"outside work target accepted");end
  end
  $display("ASYM_EDGE_CASE_PASS case=%0d F=%0d reject=%0d",CASE,fault,reject);done=1;
 end
endmodule
module tb_asym_edges;
 wire [3:0] done;genvar i;generate for(i=0;i<4;i=i+1)begin:g asym_edge #(.CASE(i)) c(done[i]);end endgenerate
 initial begin wait(&done);$display("ASYM_EDGES_PASS both measured edges inclusive/outside,negativeMC bound,work target rejection");$finish;end
 initial begin #2000000;$fatal(1,"edge timeout %b",done);end
endmodule
