`timescale 1ns/1ps
module tb_region_probe;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,rx=1,frame=0,confirmed=1,auto_frames=1,feedback=1;
 reg [10:0] bx=960;reg [3:0] keys=15;reg [1:0] enc=0,ab_phase=0;
 wire en,dir,step,tx;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 localparam MC=500;
 vision_monitor #(.REGION_PROBE(1),.MS_CYCLES(MC),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(MC*100),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(MC*250),
 .SETUP_CYCLES(MC*20),.HALF_CYCLES(MC*5/2),.SETTLE_CYCLES(MC*50),.TIMEOUT_CYCLES(MC*5000),.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(0),.CASCADE_PRESET(0),.DEFAULT_LIMIT(60)) dut(
 clk,rst,keys,enc,2'b0,frame,bx,11'd500,confirmed,1'b0,4'd15,rx,tx,en,dir,step,led,16'd0,16'd0,1'b0,cs,ae,ag,rl,rt,rr,rb);
 integer cyc=0,fc=0,commands=0,encoded=0,goal=0,qw=0,qr=0,pulses=0;
 integer times[0:4095],goals[0:4095];
 always @(negedge clk)begin
  cyc=cyc+1;frame<=0;
  if(auto_frames)begin if(fc==MC*33-1)begin fc=0;frame<=1;end else fc=fc+1;end
  if(qr<qw && cyc>=times[qr])begin goal=goals[qr];qr=qr+1;end
  if(cyc%3==0 && encoded!=goal)begin
   ab_phase=ab_phase+(goal>encoded ? 2'd1 : 2'd3);encoded=encoded+(goal>encoded ? 1 : -1);
   case(ab_phase)0:enc=0;1:enc=1;2:enc=3;3:enc=2;endcase
  end
 end
 always @(posedge step)begin
  pulses=pulses+1;commands=commands+(dir ? 1 : -1);
  if(feedback)begin times[qw]=cyc+MC*12;goals[qw]=-(commands*32/25);qw=qw+1;end
 end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task ms(input integer n);begin tick(n*MC);end endtask
 task click(input integer k);begin keys[k]=0;tick(40);keys[k]=1;tick(45);end endtask
 task check(input integer ok,input string s);begin if(!ok)$fatal(1,"PROBE FAIL %s status=%d phase=%d F=%d P=%d ov=%b",s,dut.p_status,dut.p_phase,dut.fault,dut.position,dut.event_overflow);end endtask
 task sendbyte(input [7:0] v);integer i;begin rx=0;tick(4);for(i=0;i<8;i=i+1)begin rx=v[i];tick(4);end rx=1;tick(4);end endtask
 task configure(input integer seq,sel);
  reg [199:0] p;reg [7:0] sum;integer i;string line;
  begin p={8'd1,seq[15:0],sel[7:0],8'd1,16'd512,16'd64,16'd0,16'd0,16'd8192,16'd200,16'd50,8'd0,8'd8,16'd256,8'd0,8'd0};
   sum=0;for(i=0;i<25;i=i+1)sum=sum^p[i*8+:8];line=$sformatf("C%050h%02h",p,sum);
   for(i=0;i<line.len();i=i+1)sendbyte(line[i]);sendbyte(10);ms(10);
   check(dut.c_sequence==seq && dut.p_status==0 && !dut.p_run,"new C clears DONE and does not start");
  end
 endtask
 integer dlines=0,vlines=0,elines=0;
 initial begin : uart
  reg [7:0] b;integer i;string line;line="";
  forever begin @(negedge tx);repeat(6)@(posedge clk);#1;
   for(i=0;i<8;i=i+1)begin b[i]=tx;repeat(4)@(posedge clk);#1;end
   if(!tx)$fatal(1,"UART stop/mixed packet");line={line,b};
   if(b==10)begin
    if(line.substr(0,1)=="D1")begin check(line.len()==94,"D1 length");dlines=dlines+1;$display("PROBE_WIRE %s",line);end
    else if(line.substr(0,1)=="E1")begin check(line.len()==58,"E1 length");elines=elines+1;$display("PROBE_WIRE %s",line);end
    else begin check(line.len()==429 && line.substr(0,4)=="VIS=5","VIS429 arbitration");vlines=vlines+1;if(vlines<=2)$display("PROBE_WIRE %s",line);end
    line="";
   end
  end
 end
 integer saved,leg;
 initial begin
  tick(10);rst=1;ms(100);click(1);ms(50);check(!dut.p_run && pulses==0,"boot unconfigured K2 never moves");
  configure(1,2);saved=pulses;click(1);wait(dut.p_status==2);check(pulses==saved && !en,"static10s no enable and no STEP");
  configure(2,3);click(1);check(!dut.p_run,"neutral needs K1 and K3");
  click(0);wait(dut.ready);click(2);ms(100);configure(3,3);click(1);wait(dut.p_status==2);check(pulses==saved,"neutral10s no STEP");
  configure(4,1);ms(100);check(pulses==saved,"configuration idle");click(1);
  for(leg=0;leg<12;leg=leg+1)begin
   wait(dut.p_phase==leg && dut.p_run);wait(dut.region_probe.holding || !dut.p_run);
   check(dut.p_run && dut.position>=dut.p_target-2 && dut.position<=dut.p_target+2,"all12 finite legs actualAB arrival");
   check(!dut.following && !dut.motor_core.fast_active,"slow manual path only");
   $display("PROBE_LEG_PASS leg=%0d P=%0d target=%0d",leg,dut.position,dut.p_target);
  end
  wait(dut.p_status==2);check(!dut.p_run && dut.fault==0 && !dut.event_overflow,"three paired profiles complete no overflow/fault");
  ms(500);configure(5,1);click(1);wait(step);click(1);ms(20);check(dut.p_status==4 && !dut.p_run && !step && en,"K2 abort hold");
  configure(6,1);click(1);wait(step);keys[3]=0;#1;check(!step && !en,"raw K4 immediate release");ms(10);keys[3]=1;ms(10);check(!dut.p_run,"K4 no restart");
  click(0);wait(dut.ready);click(2);ms(70);configure(7,1);click(1);ms(100);confirmed=0;ms(40);check(!dut.p_run && dut.p_status==4 && !step && en,"invalid frame abort holding EN");confirmed=1;ms(100);check(!dut.p_run,"vision restore never resumes");
  configure(8,1);click(1);ms(100);auto_frames=0;ms(250);check(!dut.p_run && !step,"stream timeout stops");auto_frames=1;ms(100);
  configure(9,1);click(1);ms(100);bx=1081;ms(40);check(!dut.p_run,"120pixel excursion/speed stops");bx=960;ms(100);
  configure(10,1);click(1);ms(100);configure(11,1);check(!dut.p_run && !step,"config cancels and clears complete");
  force dut.event_overflow=1;click(1);check(!dut.p_run && dut.p_reject==14,"overflow refuses measurement");release dut.event_overflow;
  check(elines>100 && dlines>100 && vlines>2,"all serial sources progress");
  $display("REGION_PROBE_ALL_PASS");$finish;
 end
 initial begin ms(70000);$fatal(1,"probe timeout");end
endmodule
