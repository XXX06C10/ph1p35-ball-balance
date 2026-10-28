`timescale 1ns/1ps
module fast_guard #(parameter CODE=1)(output reg done=0);
 reg clk=0;always #5 clk=~clk;reg rst=0,request=0;reg signed [31:0] enc=0;reg [15:0] errs=0;
 wire en,dir,step,ready,busy;wire [3:0] fault;wire [7:0] spent;integer pulses=0;
 vision_servo_core #(.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.FAST_CAPABLE(1),.FAST_MS_CYCLES(10),.ENABLE_CYCLES(20),.DEBOUNCE_CYCLES(2),
 .SETUP_CYCLES(50),.FOLLOW_SETUP_CYCLES(50),.HALF_CYCLES(25),.SETTLE_CYCLES(100),.TIMEOUT_CYCLES(CODE==4 ? 800 : 50000)) dut(
 .clk(clk),.rst_n(rst),.enable_request(1'b1),.k4_n(1'b1),.k2_n(1'b1),.request(request),.following(1'b1),.external_cancel(1'b0),.external_cancel_reason(4'd0),
 .fast_mode(1'b1),.fast_rate_hz(CODE==4 ? 16'sd20 : 16'sd200),.encoder_count(enc),.encoder_errors(errs),
 .visual_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.config_changed(1'b0),.visual_target(8'sd60),
 .motor_en(en),.motor_dir(dir),.motor_step(step),.ready(ready),.busy(busy),.fault(fault),.spent(spent));
 always @(posedge step)begin pulses=pulses+1;if(CODE==2)enc<=enc+1;else if(CODE==5 && pulses%2==0)enc<=enc-1;end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 initial begin
  tick(5);rst=1;wait(ready);tick(20);if(CODE==6)dut.command_position=64;request=1;tick(1);request=0;wait(busy);
  if(CODE==3)errs=1;if(CODE==7)enc=-65;if(CODE==8)begin force dut.state=15;tick(1);release dut.state;end
  wait(fault!=0);#1;if(fault!=CODE || !en || step)$fatal(1,"fast fault%0d got%0d en%b",CODE,fault,en);
  if(CODE==1 && spent<3)$fatal(1,"fast no response fewer than3");
  if(CODE==5 && spent!=64)$fatal(1,"fast budget not64");
  tick(1000);if(!en || step || fault!=CODE)$fatal(1,"fast fault hold failed");
  $display("FAST_FAULT_PASS code=%0d spent=%0d hold=1",CODE,spent);done=1;
 end
endmodule
module tb_fast;
 wire [8:1] done;genvar j;generate for(j=1;j<=8;j=j+1)begin: guards fast_guard #(.CODE(j)) g(done[j]);end endgenerate
 initial begin wait(&done);$display("FAST_ALL_PASS: all8faults actual fast path,64pulse budget andholding EN");$finish;end
 initial begin #2000000;$fatal(1,"fast guard timeout %b",done);end
endmodule
