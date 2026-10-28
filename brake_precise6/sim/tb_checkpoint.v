`timescale 1ns/1ps
module checkpoint_case #(parameter BAD=0)(output reg done=0);
 reg clk=0;always #5 clk=~clk;reg rst=0,request=0,checkpoint=0;
 reg signed [31:0] enc=0;reg signed [15:0] rate=0;reg signed [7:0] target=48;
 wire en,dir,step,ready,busy;wire [3:0] fault;wire [7:0] spent;wire signed [31:0] mc,p;
 integer commands=0,pulses=0,j=0;reg [31:0] saved_origin;reg signed [31:0] start_mc;
 vision_servo_core #(.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.FAST_CAPABLE(1),.CHECKPOINT_CAPABLE(1),.FAST_MS_CYCLES(10),.ENABLE_CYCLES(20),
 .DEBOUNCE_CYCLES(2),.FOLLOW_SETUP_CYCLES(50),.HALF_CYCLES(25),.TIMEOUT_CYCLES(50000)) dut(
 .clk(clk),.rst_n(rst),.enable_request(1'b1),.k4_n(1'b1),.k2_n(1'b1),.request(request),.following(1'b1),.external_cancel(1'b0),.external_cancel_reason(4'd0),
 .fast_mode(1'b1),.fast_rate_hz(rate),.checkpoint(checkpoint),.encoder_count(enc),.encoder_errors(16'd0),.visual_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.config_changed(1'b0),.visual_target(target),
 .motor_en(en),.motor_dir(dir),.motor_step(step),.ready(ready),.busy(busy),.fault(fault),.spent(spent),.command_position(mc),.position(p));
 always @(posedge step)begin commands=commands+(dir ? 1 : -1);pulses=pulses+1;enc<=30-(BAD ? commands/2 : commands*32/25);end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 initial begin
  tick(5);rst=1;wait(ready);enc=30;tick(30);saved_origin=dut.origin;
  for(j=0;j<4 && fault==0;j=j+1)begin
   checkpoint=0;target=(j%2==0) ? 48 : -48;rate=(j%2==0) ? 100 : -100;
   request=1;tick(1);request=0;wait(busy);wait(spent>=48);rate=0;tick(400);checkpoint=1;
   if(BAD)begin wait(fault!=0);if(fault!=4 || !en || step)$fatal(1,"bad ratio checkpoint bypassed guard F=%0d",fault);end
   else begin wait(ready || fault!=0);if(fault!=0 || !en || dut.done || dut.origin!=saved_origin || spent>49)$fatal(1,"good checkpoint failed F=%0d",fault);tick(20);end
  end
  if(!BAD && (pulses<192 || fault!=0))$fatal(1,"checkpoint replay failed");
  $display("CHECKPOINT_PASS bad_ratio=%0d pulses=%0d F=%0d MC=%0d",BAD,pulses,fault,mc);done=1;
 end
 initial begin #3000000;$fatal(1,"checkpoint timeout bad%0d F%0d",BAD,fault);end
endmodule
module tb_checkpoint;
 wire [1:0] done;checkpoint_case #(.BAD(0)) good(done[0]);checkpoint_case #(.BAD(1)) bad(done[1]);
 initial begin wait(&done);$display("CHECKPOINT_ALL_PASS: real ratio gate,no false arrived,no origin/MC reset,bad ratio retains timeout/EN");$finish;end
endmodule
