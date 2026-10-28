`timescale 1ns/1ps
module tb_hold;
 wire [8:1] done;
 genvar j;generate for(j=1;j<=8;j=j+1)begin: guards hold_fault_case #(.CASE(j)) f(done[j]);end endgenerate
 initial begin wait(&done);$display("HOLD_ALL_PASS: all8guards,established EN retained,K1 release-only,K4 immediate,no replay");$finish;end
 initial begin #1000000;$fatal(1,"hold timeout %b",done);end
endmodule
module hold_fault_case #(parameter CASE=1)(output reg finished=0);
 reg clk=0;always #5 clk=~clk;
 reg rst=0,k1=1,k4=1,k2=1;reg signed [31:0] encoder=0;reg [15:0] errors=0;
 wire [3:0] fault;wire en_req;
 enable_latch #(.DEBOUNCE_CYCLES(3),.HOLD_ON_FAULT(1)) latch(clk,rst,k1,k4,fault!=0,en_req);
 wire en,dir,step,ready,busy;wire [7:0] spent;
 vision_servo_core #(.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.DEBOUNCE_CYCLES(3),.ENABLE_CYCLES(8),.SETUP_CYCLES(6),.HALF_CYCLES(4),.SETTLE_CYCLES(5),.FOLLOW_SETUP_CYCLES(2),.FOLLOW_SETTLE_CYCLES(2),
 .TIMEOUT_CYCLES(CASE==4 ? 1 : 2000),.MOVE_BUDGET(CASE==5 ? 1 : 64)) dut(
 .clk(clk),.rst_n(rst),.enable_request(en_req),.k4_n(k4),.k2_n(k2),.request(~k2),.following(1'b1),.external_cancel(1'b0),.external_cancel_reason(4'd0),.encoder_count(encoder),.encoder_errors(errors),
 .visual_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.config_changed(1'b0),.visual_target(8'sd5),
 .motor_en(en),.motor_dir(dir),.motor_step(step),.ready(ready),.busy(busy),.fault(fault),.spent(spent));
 always @(posedge step)begin
  if(CASE==2)encoder<=encoder+(dir ? 1 : -1);
  else if(CASE==5)encoder<=encoder+(dir ? -1 : 1);
 end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 initial begin
  tick(4);rst=1;tick(20);k1=0;tick(12);k1=1;tick(60);wait(ready);tick(12);
  if(CASE==6)dut.command_position=64;
  k2=0;tick(15);k2=1;
  if(CASE==3)begin wait(busy);errors=1;end
  if(CASE==7)begin wait(busy);encoder=-65;end
  if(CASE==8)begin wait(busy);force dut.state=15;tick(1);release dut.state;end
  wait(fault!=0);#1;
  if(fault!=CASE || !en || step)$fatal(1,"fault fixture %0d got fault=%0d en=%b",CASE,fault,en);
  if(CASE==1 && spent!=3)$fatal(1,"no-response budget changed");
  if(CASE==2 && spent!=2)$fatal(1,"wrong direction threshold changed");
  tick(100);if(!en || step || fault!=CASE)$fatal(1,"hold lost after fault %0d",CASE);
  k2=0;tick(30);if(!en || step || fault!=CASE)$fatal(1,"fault request bypass %0d",CASE);
  k1=0;tick(12);k1=1;tick(20);if(en || en_req)$fatal(1,"K1 failed to release fault hold");
  k1=0;tick(12);k1=1;tick(20);if(en || en_req || fault!=CASE)$fatal(1,"K1 re-enabled fault");
  k4=0;#1;if(en || step)$fatal(1,"K4 not immediate");tick(10);k4=1;tick(30);
  if(en || step)$fatal(1,"fault K4 replay");
  rst=0;tick(3);if(fault!=0)$fatal(1,"reset did not clear fault");
  $display("HOLD_FAULT_PASS code=%0d EN retained until explicit release,STEP inhibited,no fault restart",CASE);finished=1;
 end
endmodule

