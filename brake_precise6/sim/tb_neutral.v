`timescale 1ns/1ps
module neutral_motion #(parameter LEVEL=31)(output reg done=0);
 reg clk=0;always #5 clk=~clk;
 reg rst=0,frame=0;reg [3:0] keys=15;reg [10:0] bx=1021;reg [1:0] enc=0,phase=0;
 wire tx,en,dir,step;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 vision_monitor #(.MS_CYCLES(50),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(500),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(20000),
 .SETUP_CYCLES(1000),.HALF_CYCLES(125),.SETTLE_CYCLES(2500),.TIMEOUT_CYCLES(250000)) dut(
 clk,rst,keys,enc,2'b0,frame,bx,11'd460,1'b1,1'b0,4'd15,1'b1,tx,en,dir,step,led,16'd0,16'd0,1'b0,cs,ae,ag,rl,rt,rr,rb);
 integer fc=0,pulses=0,commands=0,encoded=0,goal=0,diff=0,j=0,saved_pulses=0,clipped=0;
 reg signed [31:0] saved_origin,saved_command;
 always @(negedge clk)begin frame<=0;if(fc==1649)begin fc=0;frame<=1;end else fc=fc+1;
  if(rst && dut.fault!=0)$fatal(1,"neutral motion false fault LEVEL=%0d F=%0d P=%d MC=%d",LEVEL,dut.fault,dut.position,dut.command_position);
 end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task click(input integer key);begin keys[key]=0;tick(30);keys[key]=1;tick(40);end endtask
 task ab_count(input integer positive);begin
  repeat(25)@(negedge clk);phase=phase+(positive ? 2'd3 : 2'd1);
  case(phase)0:enc=0;1:enc=1;2:enc=3;3:enc=2;endcase
 end endtask
 task manual_move(input integer delta);integer n;begin
  for(n=0;n<(delta<0 ? -delta : delta);n=n+1)ab_count(delta>0);
  tick(40);
 end endtask
 always @(posedge step)begin
  pulses=pulses+1;commands=commands+(dir ? 1 : -1);goal=commands*32/25;diff=goal-encoded;
  repeat(300)@(negedge clk); // real AB feedback after6ms
  for(j=0;j<(diff<0 ? -diff : diff);j=j+1)ab_count(diff>0);
  encoded=goal;
 end
 task arrive(input integer target);begin
  wait(dut.target==target && dut.drive_target==target && !dut.busy && dut.position<=target+1 && dut.position>=target-1);
  tick(100);if(dut.errors1!=0 || !dut.auto_run || dut.spent>64 || dut.position>64 || dut.position< -64)$fatal(1,"neutral arrival/guards");
 end endtask
 initial begin
  tick(5);rst=1;tick(2000);click(0);wait(dut.ready);saved_origin=dut.motor_core.origin;
  click(0);wait(!en);manual_move(LEVEL);click(0);wait(dut.ready);tick(100);
  if(dut.position!=LEVEL || dut.command_position!=0 || dut.motor_core.origin!=saved_origin)$fatal(1,"fixture must preserve old origin while moved off-enable");
  saved_pulses=pulses;click(2);wait(dut.center_confirmed && dut.settings_ready);tick(100);
  if(LEVEL>60 || LEVEL< -60)begin
   if(dut.center_status!=8 || dut.request_ready || pulses!=saved_pulses)$fatal(1,"out-of-range neutral cannot indicate ready");
   click(1);tick(200);if(dut.auto_run || dut.supervisor_reject!=11 || pulses!=saved_pulses || dut.command_position!=0 || dut.motor_core.origin!=saved_origin)$fatal(1,"invalid neutral start/rebase guard");
   $display("NEUTRAL_INVALID_PASS LEVEL=%0d KC8/RD0/AJ11,no motion or rebase",LEVEL);done=1;wait(1'b0);
  end
  if(dut.center!=1021 || dut.target!=LEVEL || dut.drive_target!=LEVEL || pulses!=saved_pulses || dut.command_position!=0 || dut.motor_core.origin!=saved_origin)
   $fatal(1,"K3 must record separate neutral without movement or encoder/MC reset LEVEL=%0d T=%d AT=%d P=%d",LEVEL,dut.target,dut.drive_target,dut.position);
  click(1);tick(15000);
  if(!dut.auto_run || pulses!=saved_pulses || dut.target!=LEVEL || dut.position!=LEVEL)$fatal(1,"centered ball must not drag leveled P toward old0");
  $display("NEUTRAL_START_PASS LEVEL=%0d centered_no_motion_ms=300 origin=%0d MC=%0d",LEVEL,dut.motor_core.origin,dut.command_position);
  bx=1149;arrive(LEVEL+16);bx=1021;arrive(LEVEL);bx=893;arrive(LEVEL-16);bx=1021;arrive(LEVEL);
  bx=1621;clipped=LEVEL+32;if(clipped>60)clipped=60;arrive(clipped);
  bx=1021;arrive(LEVEL);bx=421;clipped=LEVEL-32;if(clipped< -60)clipped=-60;arrive(clipped);
  bx=1021;arrive(LEVEL);saved_pulses=pulses;saved_command=dut.command_position;
  click(2);if(dut.center_status!=4 || dut.center_count!=1)$fatal(1,"running K3 must remain rejected");
  click(1);if(dut.auto_run || !en)$fatal(1,"K2 stop unchanged");
  click(2);wait(dut.center_count==2 && dut.settings_ready);tick(100);
  if(dut.motor_core.origin!=saved_origin || dut.command_position!=saved_command || pulses!=saved_pulses)$fatal(1,"recapture must not erase safety history");
  if(dut.target!=dut.position || dut.drive_target!=dut.position)$fatal(1,"new idle K3 captures current neutral exactly");
  click(1);tick(2000);if(pulses!=saved_pulses)$fatal(1,"recaptured center causes drift");
  keys[3]=0;#1;if(en || step)$fatal(1,"K4 immediate stop");tick(10);keys[3]=1;tick(100);if(en || dut.auto_run)$fatal(1,"no auto resume after K4");
  if(dut.motor_core.origin!=saved_origin || dut.command_position!=saved_command)$fatal(1,"K4 cannot rebase safety coordinates");
  $display("NEUTRAL_MOTION_PASS LEVEL=%0d: true1.28AB,relative +/-16 and +/-32,absolute60 clamp,center return,K3 busy/idle,K2/K4,no rebase",LEVEL);
  done=1;
 end
 initial begin : capture
  reg [7:0] b;integer n;string line;reg emitted;line="";emitted=0;
  forever begin @(negedge tx);repeat(6)@(posedge clk);#1;for(n=0;n<8;n=n+1)begin b[n]=tx;repeat(4)@(posedge clk);#1;end
   if(tx!=1)$fatal(1,"neutral UART stop bit");line={line,b};
   if(b==10)begin if(line.len()!=429)$fatal(1,"neutral changed VIS5 wire length");if(!emitted && line.substr(349,349)=="1")begin $display("UART_NEUTRAL %s",line);emitted=1;end line="";end
  end
 end
endmodule

module neutral_arithmetic(output reg done=0);
 reg clk=0;always #5 clk=~clk;reg rst=0,key=0,capture=0;
 reg signed [31:0] pos=31;reg [7:0] gain=3,limit=32;reg [10:0] x=960;
 wire signed [7:0] candidate,at;wire run,request;wire [3:0] rejected;
 vision_follow_control #(.MS_CYCLES(1),.CONTROL_MS(20)) dut(
 .clk(clk),.rst_n(rst),.key_event(key),.k4_n(1'b1),.enable_request(1'b1),.config_changed(1'b0),
 .visual_valid(1'b1),.follow_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.center_confirmed(1'b1),.frame(1'b0),.neutral_capture(capture),
 .x(x),.center(16'd960),.deadzone(16'd5),.runtime_seconds(16'd0),.gain(gain),.limit(limit),.mode(8'd1),.damping(8'd0),.slew(8'd8),
 .manual_target(8'sd0),.core_ready(1'b1),.core_busy(1'b0),.fault(4'd0),.step(1'b0),.position(pos),.candidate(candidate),.drive_target(at),.run(run),.request(request),.reject_reason(rejected));
 task tick;begin @(negedge clk);end endtask
 task snap(input integer p);begin @(negedge clk);pos=p;capture=1;tick;capture=0;tick;end endtask
 initial begin
  tick;rst=1;tick;snap(31);x=960;#1;if(candidate!=31 || at!=31 || run || request)$fatal(1,"separate neutral capture/zero error");
  x=1088;#1;if(candidate!=47)$fatal(1,"positive relative target");gain=131;#1;if(candidate!=15)$fatal(1,"invert correction only, not neutral");
  gain=3;x=1900;#1;if(candidate!=60)$fatal(1,"positive absolute clamp");x=0;#1;if(candidate!=-1)$fatal(1,"negative relative limit");
  limit=0;x=1088;#1;if(candidate!=31)$fatal(1,"zero amplitude means neutral");limit=1;#1;if(candidate!=32)$fatal(1,"relative L1 clamp");
  limit=32;snap(-31);x=0;#1;if(candidate!=-60)$fatal(1,"negative absolute clamp: T=%d N=%d sum=%d rel=%d pos=%d valid=%b",candidate,dut.neutral_reference,dut.neutral_sum,dut.pd_target,pos,dut.neutral_in_range);x=1088;#1;if(candidate!=-15)$fatal(1,"negative neutral plus correction");
  snap(63);key=1;tick;key=0;tick;if(run || request || rejected!=11)$fatal(1,"out-of-range neutral must reject start without wrapping");
  snap(-63);key=1;tick;key=0;tick;if(run || request || rejected!=11)$fatal(1,"negative out-of-range neutral");
  x=960;snap(31);key=1;tick;key=0;tick;if(!run || rejected!=0 || at!=31)$fatal(1,"valid recapture re-arms only after fresh K2");
  $display("NEUTRAL_ARITHMETIC_PASS: signed offset,inversion around level,L0/L1,absolute60 clamp,out-of-range reject11,no request on capture");done=1;
 end
endmodule

module tb_neutral;
 wire p,n,a,ip,in;
 neutral_motion #(.LEVEL(31)) positive_level(p);
 neutral_motion #(.LEVEL(-31)) negative_level(n);
 neutral_motion #(.LEVEL(63)) invalid_positive(ip);
 neutral_motion #(.LEVEL(-63)) invalid_negative(in);
 neutral_arithmetic arithmetic(a);
 initial begin wait(p && n && a && ip && in);$display("NEUTRAL_ALL_PASS: recorded level!=encoder0,center startup no motion,offset correction/clamping,origin/MC preserved,trueAB/429byte UART");$finish;end
 initial begin #30000000;$fatal(1,"neutral timeout p=%b n=%b a=%b",p,n,a);end
endmodule
