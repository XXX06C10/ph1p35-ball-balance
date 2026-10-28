`timescale 1ns/1ps
module replay_case #(parameter OLD=0)(output reg done=0);
 reg clk=0;always #5 clk=~clk;
 reg rst=0,rx=1,frame=0,auto_frames=1,confirmed=1;reg [10:0] bx=960;
 reg [3:0] keys=15;reg [1:0] enc=0,phase=0;
 wire en,dir,step,tx;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 vision_monitor #(.MS_CYCLES(50),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(5000),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(50000),
 .SETUP_CYCLES(1000),.HALF_CYCLES(125),.SETTLE_CYCLES(2500),.TIMEOUT_CYCLES(250000),.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1),.CASCADE_PRESET(1),.DEFAULT_DEADZONE(3),.DEFAULT_LIMIT(OLD ? 32 : 48)) dut(
 clk,rst,keys,enc,2'b0,frame,bx,11'd500,confirmed,1'b0,4'd15,rx,tx,en,dir,step,led,16'd0,16'd0,1'b0,cs,ae,ag,rl,rt,rr,rb);
 integer cyc=0,fc=0,commands=0,encoded=0,goal=0,qw=0,qr=0,pulses=0,delay_ms=12,base_encoder=0;
 integer times[0:4095];integer goals[0:4095];integer saved;
 always @(negedge clk)begin
  cyc=cyc+1;frame<=0;
  if(auto_frames)begin if(fc==1649)begin fc=0;frame<=1;end else fc=fc+1;end
  if(qr<qw && cyc>=times[qr])begin goal=goals[qr];qr=qr+1;end
  if(cyc%3==0 && encoded!=goal)begin
   phase=phase+(goal>encoded ? 2'd1 : 2'd3);encoded=encoded+(goal>encoded ? 1 : -1);
   case(phase)0:enc=0;1:enc=1;2:enc=3;3:enc=2;endcase
  end
 end
 always @(posedge step)begin
  pulses=pulses+1;commands=commands+(dir ? 1 : -1);
  times[qw]=cyc+delay_ms*50;goals[qw]=base_encoder-(commands*32/25);qw=qw+1;
 end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task click(input integer k);begin keys[k]=0;tick(40);keys[k]=1;tick(45);end endtask
 task sendbyte(input [7:0] v);integer i;begin rx=0;tick(4);for(i=0;i<8;i=i+1)begin rx=v[i];tick(4);end rx=1;tick(4);end endtask
 task send_config(input integer seq,sel,hz,amp,corrupt);
  reg [199:0] payload;reg [7:0] sum;integer i;string line;
  begin
   payload={8'd1,seq[15:0],sel[7:0],8'd1,16'd512,16'd64,16'd0,16'd0,16'd8192,16'd200,hz[15:0],8'd0,amp[7:0],16'd256,8'd0,8'd0};
   sum=0;for(i=0;i<25;i=i+1)sum=sum^payload[i*8+:8];if(corrupt)sum=sum^1;
   line=$sformatf("C%050h%02h",payload,sum);if(line.len()!=53)$fatal(1,"C length");
   for(i=0;i<line.len();i=i+1)sendbyte(line[i]);sendbyte(10);tick(2000);$display("C_DEBUG seq=%d sel=%d errors=%d digits=%d good=%b packet=%h",dut.c_sequence,dut.c_selection,dut.c_errors,dut.cascade_config.digits,dut.cascade_config.good,dut.cascade_config.packet);
  end
 endtask
 task check(input integer ok,input string s);begin if(!ok)$fatal(1,"CASCADE FAIL %s F=%d P=%d phase=%d stat=%d freq=%d",s,dut.fault,dut.position,dut.n_cal_phase,dut.n_cal_status,dut.n_frequency);end endtask
 task moved_level(input integer level,input integer seqnum);
 integer before_steps;reg signed [31:0] old_origin;
 begin
  goal=-level;wait(encoded==goal);tick(30);base_encoder=encoded+(commands*32/25);
  click(2);click(0);wait(dut.ready);tick(50);check(dut.n_neutral==level && dut.position==level,"new separate neutral accepts disabled trueAB move");
  old_origin=dut.motor_core.origin;send_config(seqnum,2,100,8,0);before_steps=pulses;click(1);tick(1000);
  check(pulses==before_steps,"nonzero neutral motor calibration initial dwell0STEP");
  wait(dut.n_cal_status==2 || dut.n_cal_status==4 || dut.fault!=0);
  check(dut.fault==0 && dut.n_cal_status==2 && dut.position>=level-2 && dut.position<=level+2 && dut.motor_core.origin==old_origin,"trueAB nonzero calibration preserves origin");
  $display("CASCADE_NEUTRAL_PASS level=%0d P=%d",level,dut.position);click(0);tick(1000);
 end
 endtask

 reg [47:0] trajectory[0:161];integer idx=0,elapsed=0,j=0,boundaries=0,max_spent=0,old_dc=0;reg replaying=0,prev_busy=0;
 wire checkpoint_seen;wire signed [18:0] debug_checkpoint_ratio;
 generate if(OLD)begin assign checkpoint_seen=0;assign debug_checkpoint_ratio=0;end else begin assign checkpoint_seen=dut.n_checkpoint;assign debug_checkpoint_ratio=dut.motor_core.checkpoint_difference;end endgenerate
 always @(negedge clk)begin
  if(dut.spent>max_spent)max_spent=dut.spent;
  if(replaying)begin
   if(dut.fault!=0 && !OLD)$fatal(1,"REPLAY unexpected F=%0d elapsed=%0d SP=%0d P=%0d MC=%0d fast_count=%0d fast_delta=%0d fast_commands=%0d ratio=%0d wrong=%0d checkpoint=%b",dut.fault,elapsed,dut.spent,dut.position,dut.command_position,dut.motor_core.fast_count,dut.motor_core.fast_displacement,dut.motor_core.fast_commands,debug_checkpoint_ratio,dut.motor_core.wrong_direction,checkpoint_seen);
   if(checkpoint_seen && dut.ready)boundaries=boundaries+1;
  end
 end
 initial begin
  $readmemh("sim/easy2_recorded_frames.mem",trajectory);
  bx=1041;tick(5);rst=1;tick(2500);click(0);wait(dut.ready);click(2);tick(2500);click(1);wait(dut.auto_run);replaying=1;
  for(j=0;j<3;j=j+1)begin
   idx=0;elapsed=0;
   while(elapsed<5772 && dut.fault==0)begin
    while(idx<162 && trajectory[idx][47:16]<=elapsed)begin bx=trajectory[idx][15:0];idx=idx+1;end
    tick(50);elapsed=elapsed+1;
   end
  end
  if(OLD)begin check(dut.fault==5 && dut.spent==64,"old version reproduces SP64 F5");$display("REPLAY_OLD_F5_PASS pulses=%0d P=%0d",pulses,dut.position);end
  else begin
   check(dut.auto_run && dut.fault==0 && en && pulses>200 && boundaries>=3 && max_spent<64,"new continuous trajectory crosses200 pulses with verified boundaries");
   $display("REPLAY_NEW_PASS pulses=%0d checkpoints=%0d max_segment=%0d",pulses,boundaries,max_spent);
   fork
    begin wait(dut.cascade_control.quiescing);keys[3]=0;#1;check(!step && !en,"K4 during checkpoint immediate stop");end
    begin repeat(20)begin bx=1400;tick(5000);bx=600;tick(5000);end end
   join
   tick(100);keys[3]=1;tick(1000);check(!dut.auto_run && !en,"K4 checkpoint no restart");
  end
  done=1;
 end
endmodule
module tb_replay;
 wire done;replay_case #(.OLD(0)) c(done);
 initial begin wait(done);$display("REPLAY_ALL_PASS");$finish;end
 initial begin #120000000;$fatal(1,"replay timeout");end
endmodule
