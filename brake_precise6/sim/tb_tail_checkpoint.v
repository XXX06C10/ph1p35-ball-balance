`timescale 1ns/1ps
module tail_case #(parameter CASE=0)(output reg done=0);
 reg clk=0;always #5 clk=~clk;reg rst=0,request=0,checkpoint=0;reg signed [31:0] enc=0;
 wire en,step,ready,busy;wire [3:0] fault;
 vision_servo_core #(.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),.FAST_CAPABLE(1),.CHECKPOINT_CAPABLE(1),.TAIL_CHECKPOINT(1),.FAST_MS_CYCLES(10),.ENABLE_CYCLES(20),.DEBOUNCE_CYCLES(2),.TIMEOUT_CYCLES(50000)) dut(
 .clk(clk),.rst_n(rst),.enable_request(1'b1),.k4_n(1'b1),.k2_n(1'b1),.request(request),.following(1'b1),.external_cancel(1'b0),.external_cancel_reason(4'd0),
 .fast_mode(1'b1),.fast_rate_hz(16'sd0),.checkpoint(checkpoint),.encoder_count(enc),.encoder_errors(16'd0),.visual_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.config_changed(1'b0),.visual_target(8'sd59),
 .motor_en(en),.motor_step(step),.ready(ready),.busy(busy),.fault(fault));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 initial begin
  tick(5);rst=1;wait(ready);tick(4);request=1;tick(1);request=0;wait(busy);tick(5);
  // Exact old-like F4 snapshot: MC43, P54, pending1/no new edge, net residual-1.09.
  dut.command_position=43;enc=-54;dut.fast_count=1;dut.fast_commands=1;dut.fast_anchor=54;dut.fast_age=0;dut.fast_quiet_age=0;
  if(CASE==1)begin enc=0;dut.fast_anchor=0;end
  if(CASE==2)begin dut.fast_count=3;dut.fast_commands=3;end
  if(CASE==3)begin enc=-49;dut.fast_anchor=49;end
  if(CASE==4)dut.wrong_direction=1;
  if(CASE==6)begin dut.command_position=-30;dut.checkpoint_p=-1;enc=40;dut.fast_anchor=-40;dut.fast_commands=-1;end
  if(CASE==5)begin dut.command_position=0;enc=0;dut.fast_anchor=0;end
  tick(100);checkpoint=1;
  if(CASE==0 || CASE==6)begin
   tick(290);if(ready || !busy)$fatal(1,"tail accepted before40ms quiet");
   tick(40);if(!ready || fault || dut.done || dut.command_position!=(CASE==6 ? -30 : 43) || dut.origin!=0)$fatal(1,"trusted tail failed or fake arrival F%d",fault);
  end else begin
   wait(fault!=0);if(!en || step || (CASE==2 ? fault!=1 : fault!=4))$fatal(1,"tail bypass case%0d F%d",CASE,fault);
  end
  $display("TAIL_CASE_PASS case=%0d F=%0d",CASE,fault);done=1;
 end
 initial begin #1000000;$fatal(1,"tail timeout case%0d state=%d active=%b ready=%b enabled=%b timer=%d",CASE,dut.state,dut.active,ready,en,dut.action_timer);end
endmodule
module tb_tail_checkpoint;
 wire [6:0] done;genvar i;generate for(i=0;i<7;i=i+1)begin:c tail_case #(.CASE(i)) t(done[i]);end endgenerate
 initial begin wait(&done);$display("TAIL_CHECKPOINT_PASS:40msquiet,tightmeasuredratio,1tailsettled,3noresponse/nofeedback/badratio/wrong/netzero refused");$finish;end
endmodule
