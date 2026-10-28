`timescale 1ns/1ps
module checkpoint_finish_case #(parameter FIX=1,FAIL=0)(output reg done=0);
 reg clk=0;always #5 clk=~clk;reg rst=0,frame=0;reg [3:0] keys=15;reg [10:0] bx=960;reg [1:0] enc=0,phase=0;
 wire en,dir,step,tx;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 vision_monitor #(.REGION_RETURN(1),.ASYM_RANGE(1),.REGION100(1),.REGION_FAST(FIX),.MS_CYCLES(50),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(5000),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(50000),.SETUP_CYCLES(1000),.HALF_CYCLES(125),.SETTLE_CYCLES(2500),.TIMEOUT_CYCLES(250000),.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1),.CASCADE_PRESET(1),.DEFAULT_DEADZONE(100),.DEFAULT_LIMIT(60)) dut(
 clk,rst,keys,enc,2'b0,frame,bx,11'd500,1'b1,1'b0,4'd15,1'b1,tx,en,dir,step,led,16'd0,16'd0,1'b0,cs,ae,ag,rl,rt,rr,rb);
 integer cyc=0,fc=0,commands=0,encoded=0,goal=0,qw=0,qr=0,bias=0;
 integer times[0:4095];integer goals[0:4095];integer maxspent=0;reg armed=0,finish_seen=0;integer wait_ms=0;
 always @(negedge clk)begin
  cyc=cyc+1;frame<=0;if(fc==1649)begin fc=0;frame<=1;end else fc=fc+1;
  if(armed && bias<6 && dut.spent>=(bias+1)*6)bias=bias+1;
  if(dut.cascade_control.checkpoint_finish)finish_seen=1;
  if(qr<qw && cyc>=times[qr])begin goal=goals[qr];qr=qr+1;end
  if(cyc%3==0 && encoded!=goal && !(FAIL==1 && finish_seen))begin phase=phase+(goal>encoded ? 2'd1 : 2'd3);encoded=encoded+(goal>encoded ? 1 : -1);case(phase)0:enc=0;1:enc=1;2:enc=3;3:enc=2;endcase end
  if(dut.spent>maxspent)maxspent=dut.spent;
  if(dut.spent>64)$fatal(1,"original64pulse budget bypassed");
 end
 always @(posedge step)begin
  commands=commands+(dir ? 1 : -1);times[qw]=cyc+600;
  goals[qw]=(FAIL==2 && finish_seen) ? encoded+(dir ? 2 : -2) : bias-(commands*32/25);qw=qw+1;
 end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task click(input integer k);begin keys[k]=0;tick(40);keys[k]=1;tick(45);end endtask
 initial begin
  tick(5);rst=1;tick(3000);click(0);wait(dut.ready);click(2);tick(3000);bx=1400;tick(3000);
  force dut.n_region_raw=32'sd300*256;force dut.n_region_hz=16'd200;force dut.n_region_slew=16'd256;force dut.c_slew=16'd256;
  click(1);armed=1;
  if(!FIX)begin
   wait(dut.fault!=0);if(dut.fault!=4 || dut.spent!=48)$fatal(1,"legacy residual stall not reproduced F=%d SP=%d",dut.fault,dut.spent);
   $display("CHECKPOINT_LEGACY_REPRO_PASS 48pulse residual rejection waits5s thenF4");
  end else if(FAIL!=0)begin
   wait(dut.fault!=0);if(!finish_seen || dut.fault!=(FAIL==1 ? 1 : 2))$fatal(1,"finish guard missing FAIL=%0d F=%d seen=%b",FAIL,dut.fault,finish_seen);
   $display("CHECKPOINT_FINISH_GUARD_PASS failure=%0d fault=%0d originalguardlatched",FAIL,dut.fault);
  end else begin
   wait_ms=0;
   while((dut.position<299 || dut.position>301 || dut.n_frequency!=0) && wait_ms<16000 && dut.fault==0)begin tick(50);wait_ms=wait_ms+1;end
   if(!finish_seen || dut.fault!=0 || wait_ms>=16000 || dut.motor_core.origin!=0 || dut.command_position<230 || maxspent<49 || maxspent>64)$fatal(1,"bounded finish FAIL F=%d P=%d ms=%0d spent=%0d finish=%b",dut.fault,dut.position,wait_ms,maxspent,finish_seen);
   $display("CHECKPOINT_FINISH_RECOVERY_PASS realAB,bias6,remainingbudget,actualarrival,NOREBASE,maxspent=%0d,ms=%0d",maxspent,wait_ms);
  end
  done=1;
 end
endmodule
module tb_checkpoint_finish;
 wire [3:0] done;
 checkpoint_finish_case #(.FIX(0)) old(done[0]);checkpoint_finish_case #(.FIX(1)) fixed_run(done[1]);
 checkpoint_finish_case #(.FIX(1),.FAIL(1)) jam(done[2]);checkpoint_finish_case #(.FIX(1),.FAIL(2)) reverse_run(done[3]);
 initial begin wait(&done);$display("CHECKPOINT_FINISH_PASS legacyF4reproduced,boundedrealarrival,noresponse/reverseguards,budget/time/originpreserved");$finish;end
 initial begin #140000000;$fatal(1,"checkpoint fixture timeout %b",done);end
endmodule
