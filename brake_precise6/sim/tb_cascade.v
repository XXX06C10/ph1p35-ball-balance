`timescale 1ns/1ps
module tb_cascade;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,rx=1,frame=0,auto_frames=1,confirmed=1;reg [10:0] bx=960;
 reg [3:0] keys=15;reg [1:0] enc=0,phase=0;
 wire en,dir,step,tx;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 vision_monitor #(.MS_CYCLES(50),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(5000),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(50000),
 .SETUP_CYCLES(1000),.HALF_CYCLES(125),.SETTLE_CYCLES(2500),.TIMEOUT_CYCLES(250000),.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1)) dut(
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
  tick(5);rst=1;tick(2500);click(2);click(0);wait(dut.ready);check(dut.center_confirmed,"K3 accepted");click(1);check(!dut.auto_run && dut.supervisor_reject==12 && pulses==0,"production boot requires qualified C profile");
  send_config(1,2,50,8,0);check(dut.c_sequence==1 && dut.c_selection==2 && pulses==0,"C apply no motion");
  click(1);wait(dut.n_cal_status==2 || dut.n_cal_status==4 || dut.fault!=0);check(dut.n_cal_status==2 && dut.fault==0 && en,"50Hz motor calibration");
  saved=pulses;tick(3000);check(pulses==saved && !dut.auto_run,"finite calibration no replay");
  $display("CASCADE_CAL_MOTOR_PASS hz=50 amp=8 delay12 P=%d pulses=%d",dut.position,pulses);
  send_config(2,2,100,16,0);click(1);wait(dut.n_cal_status==2 || dut.n_cal_status==4 || dut.fault!=0);check(dut.n_cal_status==2 && dut.fault==0,"100Hz motor calibration");
  $display("CASCADE_CAL_MOTOR_PASS hz=100 amp=16 delay12 P=%d pulses=%d",dut.position,pulses);
  delay_ms=6;send_config(3,2,200,16,0);confirmed=0;tick(2000);click(1);wait(dut.n_cal_status==2 || dut.n_cal_status==4 || dut.fault!=0);check(dut.n_cal_status==2 && dut.fault==0,"200Hz empty motor calibration");
  $display("CASCADE_CAL_MOTOR_PASS hz=200 amp=16 empty/invalid-camera delay6 P=%d pulses=%d",dut.position,pulses);
  confirmed=1;tick(2500);send_config(4,1,200,4,0);click(1);check(dut.auto_run,"continuous starts only K2");bx=1000;
  wait(dut.position>=3 && dut.position<=7);check(dut.fault==0,"continuous encoder follow");
  confirmed=0;tick(5000);check(dut.auto_run,"short loss100ms keeps session");confirmed=1;tick(5000);check(dut.auto_run && dut.fault==0,"recovery no restart");
  auto_frames=0;tick(10500);check(!dut.auto_run && dut.stop_reason==4 && en,"stream200ms stops but holds");auto_frames=1;bx=960;tick(2500);check(!dut.auto_run,"no auto resume");
  send_config(5,1,100,4,0);click(1);confirmed=0;tick(25500);check(!dut.auto_run && dut.stop_reason==3 && en,"persistent invalid500ms stops but holds");confirmed=1;tick(2500);check(!dut.auto_run,"loss recovery no resume");
  send_config(6,3,100,4,0);click(1);wait(dut.n_cal_status==2 || dut.n_cal_status==4 || dut.fault!=0);check(dut.n_cal_status==2 && dut.fault==0,"three-repeat finite ball profile");
  $display("CASCADE_CAL_BALL_PASS three symmetric4count profiles");
  send_config(7,3,100,4,0);click(1);bx=1400;tick(2000);check(!dut.auto_run && dut.n_cal_status==4 && en,"ball calibration edge abort holds/no return");bx=960;tick(2500);
  saved=dut.c_errors;send_config(8,1,200,4,1);check(dut.c_sequence==7 && dut.c_errors==saved+1,"C XOR reject");
  send_config(9,1,200,4,0);click(1);send_config(10,1,100,4,0);check(!dut.auto_run && en,"C commit cancels no restart");click(1);click(1);check(!dut.auto_run && en,"K2 holds");
  click(1);keys[3]=0;#1;check(!en && !step,"K4 raw override");tick(100);keys[3]=1;tick(1000);check(!dut.auto_run && !en,"K4 no replay");
  saved=dut.center_count;
  fork
   begin wait(dut.c_commit);force dut.center_event=1'b1;@(posedge clk);#1;release dut.center_event;end
   begin send_config(11,1,100,4,0);end
  join
  check(dut.center_count==saved && dut.center_status==7,"C UART commit wins K3 collision");
  $display("C_K3_COLLISION_PASS actual UART commit priority");
  moved_level(31,12);moved_level(-31,13);
  check(dut.errors1==0 && dlines>2 && vlines>0,"real AB and mixed UART observed");
  $display("CASCADE_ALL_PASS: real C UART,50/100/200Hz calibration,6/12ms1.28AB,finite ball profile,edge/loss/stream/send_config/K2/K4,94/429byte mixed UART");$finish;
 end
 initial begin #150000000;$fatal(1,"cascade timeout cyc=%d F=%d P=%d run=%b phase=%d stat=%d hz=%d state=%d",cyc,dut.fault,dut.position,dut.auto_run,dut.n_cal_phase,dut.n_cal_status,dut.n_frequency,dut.state);end
endmodule
