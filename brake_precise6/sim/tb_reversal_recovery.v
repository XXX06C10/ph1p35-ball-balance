`timescale 1ns/1ps
module reversal_case #(parameter CASE=0,LEGACY=0,CPM=10)(output reg done=0);
 reg clk=0;always #10 clk=~clk;
 reg rst=0,req=0,k4=1,valid=1;reg signed [15:0] rate=-50,target=-48;
 reg signed [31:0] enc=0;wire en,step,dir,ready,busy;wire [3:0] fault,state;
 wire [7:0] spent;wire signed [31:0] pos,cmd;integer pulses=0,age=0,rev=0,cycle=0,lastpulse=0;reg lastdir=0;
 always @(negedge clk)cycle=cycle+1;
 vision_servo_core #(.REVERSAL_RECOVERY(!LEGACY),.TARGET_BITS(16),.ASYM_LIMITS(1),.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.FAST_CAPABLE(1),.TAIL_CHECKPOINT(1),.FAST_MS_CYCLES(CPM),.ENABLE_CYCLES(20),.FOLLOW_SETUP_CYCLES(CPM*5),.HALF_CYCLES(CPM*5/2),.TIMEOUT_CYCLES(CPM*5000)) dut(
 .clk(clk),.rst_n(rst),.enable_request(1'b1),.k4_n(k4),.k2_n(1'b1),.request(req),.following(1'b1),.external_cancel(1'b0),.external_cancel_reason(4'd0),
 .fast_mode(1'b1),.fast_rate_hz(rate),.checkpoint(1'b0),.encoder_count(enc),.encoder_errors(16'd0),.visual_valid(valid),.visual_stale(1'b0),.settings_ready(1'b1),.config_changed(1'b0),.visual_target(target),
 .target_min(-32'sd182),.target_max(32'sd364),.feedback_min(-32'sd204),.feedback_max(32'sd398),.command_min(CASE==4 ? -32'sd1 : -32'sd159),.command_max(32'sd310),
 .motor_en(en),.motor_dir(dir),.motor_step(step),.command_position(cmd),.position(pos),.state(state),.fault(fault),.spent(spent),.ready(ready),.busy(busy));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 always @(posedge step)begin
  pulses=pulses+1;
  if(pulses==2 && !dir && cycle-lastpulse<CPM*40)$fatal(1,"recovery pulse before40ms quiet");
  if(pulses>1 && dir!=lastdir && cycle-lastpulse<CPM*20)$fatal(1,"DIR feedback drain violated");
  lastpulse=cycle;lastdir=dir;
  if(pulses==1)begin rate=50;target=48;end
  if(CASE==1 && pulses>=2)begin
   if(dir)begin rev=rev+1;enc<=enc-2;end else enc<=enc+2;
  end
  if(CASE==2 && pulses>=2)enc<=dir ? enc+1 : enc-1;
 end
 initial begin
  tick(3);rst=1;wait(ready);tick(3);req=1;tick(1);req=0;
  wait(pulses==1);tick(CPM*6);
  if(CASE==3)k4=0;
  if(CASE==5)valid=0;
  if(CASE==6)dut.spent=64;
  if(LEGACY)begin
   tick(CPM*300);if(spent!=1 || state!=7 || fault!=0)$fatal(1,"legacy reproduction missing");
   $display("REVERSAL_LEGACY_REPRO_PASS SP1 CHECK nonzeroRate pending1 for300ms");
  end else if(CASE==1)begin
   wait(rev>=3);if(fault || pos<=0 || pulses>12)$fatal(1,"responsive recovery failed");
   $display("REVERSAL_RESPONSE_PASS pulse2 responds then requested DIR resumes P=%0d SP=%0d",pos,spent);
  end else if(CASE==3 || CASE==5)begin
   tick(2000);if(spent!=1 || step || busy || (CASE==3 && en))$fatal(1,"cancel recovery emitted pulse");
  end else begin
   wait(fault!=0);
   if(fault!=(CASE==0 ? 1 : CASE==2 ? 2 : CASE==4 ? 6 : 5))$fatal(1,"recovery fault case%0d F%0d",CASE,fault);
   if(CASE==0 && spent!=3)$fatal(1,"noresponse must stop at3 real pulses");
   tick(500);if(step || !en)$fatal(1,"fault hold changed");
  end
  $display("REVERSAL_CASE_PASS case=%0d SP=%0d F=%0d",CASE,spent,fault);done=1;
 end
endmodule
module tb_reversal_clock50;
 wire [1:0] done;
 reversal_case #(.CASE(0),.CPM(50000)) a(done[0]);
 reversal_case #(.CASE(1),.CPM(50000)) b(done[1]);
 initial begin wait(&done);$display("REVERSAL_CLOCK50_PASS actual50MHz,40msquiet,5msDIR,2p5mshalf,F1,response");$finish;end
 initial begin #1000000000;$fatal(1,"50MHz recovery timeout");end
endmodule
module tb_reversal_recovery;
 wire [6:0] done;genvar i;generate for(i=0;i<7;i=i+1)begin:g reversal_case #(.CASE(i)) c(done[i]);end endgenerate
 initial begin wait(&done);$display("REVERSAL_RECOVERY_PASS boundedpending,realfeedback,F1,F2,F5,F6,K4,loss");$finish;end
 initial begin #1000000;$fatal(1,"recovery timeout %b",done);end
endmodule
module tb_reversal_legacy;
 wire done;reversal_case #(.LEGACY(1)) c(done);
 initial begin wait(done);$finish;end
 initial begin #1000000;$fatal(1,"legacy timeout");end
endmodule
