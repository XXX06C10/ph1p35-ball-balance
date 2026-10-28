`timescale 1ns/1ps
module tb_easy;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,rx=1,frame=0,auto_frames=1,confirmed=1;reg [10:0] bx=960;reg noise=0;reg [1:0] noise_phase=0;
 reg [3:0] keys=15;reg [1:0] enc=0,phase=0;
 wire en,dir,step,tx;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 vision_monitor #(.MS_CYCLES(50),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(5000),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(50000),
 .SETUP_CYCLES(1000),.HALF_CYCLES(125),.SETTLE_CYCLES(2500),.TIMEOUT_CYCLES(250000),.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1),.CASCADE_PRESET(1),.DEFAULT_DEADZONE(3),.DEFAULT_LIMIT(60)) dut(
 clk,rst,keys,enc,2'b0,frame,bx,11'd500,confirmed,1'b0,4'd15,rx,tx,en,dir,step,led,16'd0,16'd0,1'b0,cs,ae,ag,rl,rt,rr,rb);
 integer cyc=0,fc=0,commands=0,encoded=0,goal=0,qw=0,qr=0,pulses=0,delay_ms=12,base_encoder=0;
 integer times[0:4095];integer goals[0:4095];integer saved;
 always @(negedge clk)begin
  cyc=cyc+1;frame<=0;
  if(auto_frames)begin if(fc==1649)begin fc=0;frame<=1;if(noise)begin case(noise_phase)0:bx=958;1:bx=960;2:bx=962;3:bx=960;endcase noise_phase=noise_phase+1'b1;end end else fc=fc+1;end
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
 integer dlines=0,vlines=0;
 initial begin : uart
  reg [7:0] b;integer i;string line;line="";
  forever begin @(negedge tx);repeat(6)@(posedge clk);#1;
   for(i=0;i<8;i=i+1)begin b[i]=tx;repeat(4)@(posedge clk);#1;end
   if(!tx)$fatal(1,"mixed UART stop");line={line,b};
   if(b==10)begin
    if(line.substr(0,1)=="D1")begin check(line.len()==94,"D1 length");dlines=dlines+1;if(dlines<=5)$display("UART_DIAG %s",line);end
    else begin check(line.len()==429 && line.substr(0,4)=="VIS=5","VIS compatibility/arbitration");vlines=vlines+1;if(vlines<=2)$display("UART_CASCADE %s",line);end
    line="";
   end
  end
 end
 initial begin
  tick(5);rst=1;tick(2500);
  check(dut.c_kp==819 && dut.c_kv==64 && dut.c_ki==131 && dut.c_max_hz==200 && dut.c_slew==200 && dut.c_delay==20 && dut.deadzone==3 && dut.runtime_seconds==0,"built-in preset defaults");
  check(!en && !dut.auto_run && pulses==0,"no boot motion");
  click(2);check(dut.center_confirmed && dut.c_profile_ready && pulses==0,"K3 records center without erasing built-in profile");
  click(1);check(!dut.auto_run && dut.supervisor_reject==1,"K1 enable still required");
  click(0);wait(dut.ready);click(1);check(dut.auto_run && dut.c_sequence==0,"K3 then K2 starts without any C configuration");
  tick(3050100);check(dut.auto_run && dut.fault==0 && pulses==0 && dut.n_stable,"continuous hold exceeds61s without timeout/arrived stop");
  $display("EASY_HOLD_PASS 61s center hold,zero pulses,no UART configuration");
  saved=pulses;noise=1;tick(200000);noise=0;bx=960;check(pulses==saved && dut.n_stable && dut.auto_run,"center2pixel noise must not cause motor chatter");
  $display("EASY_NOISE_HOLD_PASS 4s actual noisy frames,no STEP");
  bx=1060;wait(dut.position>=8);check(dut.auto_run && dut.fault==0,"right disturbance drives positive correction");
  click(1);check(!dut.auto_run && en,"K2 stop retains enable");
  tick(4000);bx=980;tick(2500);click(2);tick(2500);check(dut.center==980 && dut.c_profile_ready,"second K3 directly rearms preset");
  saved=pulses;click(1);tick(1000);check(dut.auto_run && pulses==saved,"new center starts without initial reference jump");
  confirmed=0;tick(5000);check(dut.auto_run,"short loss keeps session");tick(21000);check(!dut.auto_run && dut.stop_reason==3 && en,"500ms invalid stops/holds");
  confirmed=1;tick(2500);check(!dut.auto_run,"no automatic restart after loss");
  click(1);check(dut.auto_run,"physical K2 resumes on real valid frame");
  keys[3]=0;#1;check(!step && !en,"K4 immediate release");tick(100);keys[3]=1;tick(1000);check(!dut.auto_run && !en,"no K4 replay");
  send_config(40,1,100,4,0);check(!dut.c_builtin && dut.c_profile_ready,"explicit C replaces builtin");
  click(2);tick(2500);check(!dut.c_profile_ready,"custom model still invalidates on K3");
  click(0);wait(dut.ready);click(1);check(!dut.auto_run && dut.supervisor_reject==12,"custom qualification semantics retained");
  check(dut.errors1==0 && dlines>2 && vlines>0,"actual AB and packet UART");
  $display("EASY_ALL_PASS: built-in preset,K3/K2,no C setup,61s center hold,disturbance,K2/K4,500ms loss,explicit C qualification");$finish;
 end
 initial begin #150000000;$fatal(1,"easy timeout F=%d run=%b",dut.fault,dut.auto_run);end
endmodule
