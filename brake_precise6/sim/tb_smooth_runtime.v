`timescale 1ns/1ps
module tb_smooth_runtime;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,rx=1,frame=0,auto_frames=1,confirmed=1;reg [10:0] bx=960;reg noise=0;reg [1:0] noise_phase=0;
 reg [3:0] keys=15;reg [1:0] enc=0,phase=0;
 wire en,dir,step,tx;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 vision_monitor #(.REGION_RETURN(1),.ASYM_RANGE(1),.ASYM_SMOOTH(1),.MS_CYCLES(50),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(5000),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(50000),
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

 always @(posedge clk)if(dut.request)$display("REQ state=%d target=%d lo=%d hi=%d cmp=%b/%b permit=%b core_ready=%b reject=%d",dut.motor_core.state,dut.drive_target,dut.motor_core.tmin,dut.motor_core.tmax,dut.motor_core.visual_target>=dut.motor_core.tmin,dut.motor_core.visual_target<=dut.motor_core.tmax,dut.motor_core.permit,dut.ready,dut.core_reject);
 integer dlines=0,vlines=0;integer phase_count=0;
 initial begin : uart
  reg [7:0] b;integer i;string line;line="";
  forever begin @(negedge tx);repeat(6)@(posedge clk);#1;
   for(i=0;i<8;i=i+1)begin b[i]=tx;repeat(4)@(posedge clk);#1;end
   if(!tx)$fatal(1,"wide UART stop");line={line,b};
   if(b==10)begin
    if(line.substr(0,1)=="D2")begin check(line.len()==148,"D2 length");dlines=dlines+1;end
    else begin check(line.len()==441 && line.substr(0,4)=="VIS=6","VIS6/arbiter");vlines=vlines+1;end
    $display("ASYM_WIRE %s",line);line="";
   end
  end
 end
 task travel(input integer endpoint);
 integer deadline;
 begin
  force dut.n_region_raw=endpoint*256;
  deadline=0;
  while((dut.position<endpoint-1 || dut.position>endpoint+1 || dut.n_frequency!=0) && deadline<8000 && dut.fault==0)begin tick(50);deadline=deadline+1;end
  check(dut.fault==0 && deadline<8000,"large endpoint arrival without wrap/fault");
  check(dut.position>=dut.feedback_min && dut.position<=dut.feedback_max,"real feedback inside hard envelope");
  $display("ASYM_ENDPOINT_PASS endpoint=%0d P=%0d MC=%0d ms=%0d",endpoint,dut.position,dut.command_position,deadline);
  tick(20000);check(dut.fault==0,"endpoint dwell has no tail timeout");release dut.n_region_raw;
 end
 endtask
 task send_zone(input integer seq,radius,bad);
 reg [63:0] packet;reg [7:0] sum;integer j;string line;
 begin
  packet={16'(seq),16'd960,16'(radius),8'd3,8'd48};sum=0;for(j=0;j<8;j=j+1)sum=sum^packet[j*8+:8];if(bad)sum=sum^1;
  line=$sformatf("P%016h%02h",packet,sum);for(j=0;j<line.len();j=j+1)sendbyte(line[j]);sendbyte(10);tick(1000);
 end endtask
 initial begin
  tick(10);rst=1;tick(5000);click(0);wait(dut.ready);tick(100);click(1);check(!dut.auto_run,"no motion before K3 qualification");
  click(2);tick(2000);check(dut.limits_ready && dut.limit_anchor==0 && dut.work_min==-182 && dut.work_max==364,"first K3 fixed envelope");
  click(1);tick(20000);check(dut.auto_run && dut.n_region_holding && pulses==0,"initial hold no STEP");
  bx=1800;tick(8000);travel(364);travel(0);bx=100;tick(8000);travel(-182);travel(0);bx=960;tick(50000);
  check(dut.auto_run && dut.n_region_holding && dut.motor_core.origin==0,"return original center without rebasing");
  click(1);tick(100);check(!dut.auto_run && en,"K2 stop holds enable");
  goal=-200;base_encoder=encoded+(commands*32/25);wait(encoded==goal);base_encoder=encoded+(commands*32/25);tick(100);click(2);tick(100000);
  check(dut.n_neutral==200 && dut.limit_anchor==0 && dut.work_max==364,"later K3 wide neutral does not move envelope");
  saved=pulses;click(1);tick(30000);check(dut.auto_run && dut.n_region_holding && pulses==saved && dut.position==200,"wide neutral restart has no8bit jump");
  check(dut.region_hold.hold_radius==30 && dut.region_hold.hold_exit==45,"default live radius30/45");
  send_zone(1,50,0);check(!dut.auto_run && en && dut.region_hold.hold_radius==50 && dut.region_hold.hold_exit==75,"real P50 atomically cancels/retains enable and updates radius");
  tick(2000);saved=pulses;tick(5000);check(!dut.auto_run && pulses==saved,"configuration never auto starts motion");
  click(1);tick(2000);check(dut.auto_run,"K2 restarts only after config confirmation/fresh frames");
  send_zone(2,20,1);check(dut.auto_run && dut.region_hold.hold_radius==50,"bad XOR cannot change live radius/cancel run");
  send_zone(3,20,0);check(!dut.auto_run && dut.region_hold.hold_radius==20 && dut.region_hold.hold_exit==30,"real P20 radius restored");
  check(dut.limit_anchor==0 && dut.work_min==-182 && dut.work_max==364 && dut.n_neutral==200,"P profile preserves fixed safety window and K3 neutral");
  check(dlines>20 && vlines>2,"wide wire sources alive");
  $display("SMOOTH_RUNTIME_PASS realAB1.28,0/+364/0/-182/0,multi64pulse segments,wide K3 neutral,UART441/148");$finish;
 end
 initial begin #250000000;$fatal(1,"asym timeout P=%d F=%d",dut.position,dut.fault);end
endmodule
