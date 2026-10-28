`timescale 1ns/1ps
// Independent assumed rolling dynamics. A model PASS is not physical acceptance.
module asym_plant_case #(parameter ID=0,parameter real B=-20.0,parameter KP=819,KV=26,KI=131,POL=0,SLEW=102,USE_PRESET=0,parameter real START_X=100.0,START_V=0.0)(output reg done=0);
 reg clk=0;always #5 clk=~clk;reg rst=0,rx=1,frame=0,simulate=0;
 reg [3:0] keys=15;reg [10:0] bx=960;reg [1:0] enc=0,phase=0;
 wire en,dir,step,tx;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 vision_monitor #(.REGION_RETURN(1),.ASYM_RANGE(1),.MS_CYCLES(50),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(5000),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(50000),
 .SETUP_CYCLES(1000),.HALF_CYCLES(125),.SETTLE_CYCLES(2500),.TIMEOUT_CYCLES(250000),.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1),.CASCADE_PRESET(USE_PRESET),.DEFAULT_DEADZONE(USE_PRESET ? 3 : 5),.DEFAULT_LIMIT(USE_PRESET ? 60 : 32)) dut(
 clk,rst,keys,enc,2'b0,frame,bx,11'd500,1'b1,1'b0,4'd15,rx,tx,en,dir,step,led,16'd0,16'd0,1'b0,cs,ae,ag,rl,rt,rr,rb);
 integer cycles=0,fc=0,ms=0,mscycles=0,commands=0,encoded=0,goal=0,qw=0,qr=0,i=0,trace;
 integer times[0:4095];integer goals[0:4095];real x=0.0,velocity=0.0,acceleration=0.0,peak=0.0,squared=0.0;integer samples=0;real overshoot=0.0;integer quiet_since=-1,first_settle=-1;
 real delayed[0:19];integer ad=0;
 always @(posedge step)begin commands=commands+(dir ? 1 : -1);times[qw]=cycles+600;goals[qw]=-(commands*32/25);qw=qw+1;end
 always @(negedge clk)begin
  cycles=cycles+1;frame<=0;
  if(qr<qw && cycles>=times[qr])begin goal=goals[qr];qr=qr+1;end
  if(cycles%3==0 && encoded!=goal)begin phase=phase+(goal>encoded ? 2'd1 : 2'd3);encoded=encoded+(goal>encoded ? 1 : -1);case(phase)0:enc=0;1:enc=1;2:enc=3;3:enc=2;endcase end
  if(fc==1649)begin fc=0;frame<=1;if(simulate)bx<=960+$rtoi(x);end else fc=fc+1;
  if(simulate)begin
   if(dut.fault!=0)$fatal(1,"new plant%0d guard F=%0d ms=%0d P=%d x=%f",ID,dut.fault,ms,dut.position,x);
   if(mscycles==49)begin
    mscycles=0;ms=ms+1;
    acceleration=B*delayed[ad]-0.2*velocity;delayed[ad]=$itor(commands)*1.28;ad=(ad+1)%20;
    velocity=velocity+acceleration*0.001;x=x+velocity*0.001;
    if(ms<8000 && x*START_X<0 && (x<0 ? -x : x)>overshoot)overshoot=x<0 ? -x : x;
    if(ms<8000)begin
     if(x<=10 && x>=-10 && velocity<=15 && velocity>=-15)begin
      if(quiet_since<0)quiet_since=ms;
      if(ms-quiet_since>=1000 && first_settle<0)first_settle=quiet_since;
     end else quiet_since=-1;
    end
    if(ms==8000)begin x=x+(ID==1 ? -40.0 : 40.0);velocity=velocity+3.0;end
    if((x<0 ? -x : x)>peak)peak=x<0 ? -x : x;
    if(x>800 || x< -800)$fatal(1,"new plant%0d diverged",ID);
    if(ms%20==0)$fdisplay(trace,"%0d,%f,%f,%0d,%0d,%0d,%0d,%0d,%0d",ms,x,velocity,$signed(dut.position),$signed(dut.n_reference_q8),$signed(dut.n_frequency),dut.fault,dut.spent,dut.completed_count);
    if((ms>=7000 && ms<8000) || ms>=15000)begin
     if(x>26 || x< -26 || velocity>25 || velocity< -25)$fatal(1,"new plant%0d settling specification ms=%0d x=%f v=%f",ID,ms,x,velocity);
     squared=squared+x*x;samples=samples+1;
    end
    if(ms==18000)begin
     if(!dut.auto_run || dut.errors1!=0)$fatal(1,"new plant run/AB failure");
     $display("ASYM_PLANT_CASE_PASS id=%0d B=%f peak=%f RMS=%f final=%f velocity=%f",ID,B,peak,$sqrt(squared/samples),x,velocity);
     $display("PLANT_BRAKING_METRIC id=%0d settle_ms=%0d overshoot=%f",ID,first_settle,overshoot);
     $fclose(trace);done=1;simulate=0;
    end
   end else mscycles=mscycles+1;
  end
 end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task click(input integer k);begin keys[k]=0;tick(40);keys[k]=1;tick(45);end endtask
 task sendbyte(input [7:0] v);integer j;begin rx=0;tick(4);for(j=0;j<8;j=j+1)begin rx=v[j];tick(4);end rx=1;tick(4);end endtask
 reg [199:0] payload;reg [7:0] sum;string line;
 initial begin
  for(i=0;i<20;i=i+1)delayed[i]=0.0;
  trace=$fopen($sformatf("sim/results/asym_plant_%0d.csv",ID),"w");$fdisplay(trace,"ms,error_pixels,velocity_pixels_s,P,reference_q8,frequency_hz,fault,spent,completed_count");
  tick(5);rst=1;tick(2500);click(0);wait(dut.ready);click(2);tick(2500);
  if(!USE_PRESET)begin
  payload={8'd1,16'd1,8'd1,8'd0,16'(KP),16'(KV),16'(KI),16'd0,16'd8192,16'd200,16'd100,8'd20,8'd4,16'(SLEW),8'(POL),8'd0};
  sum=0;for(i=0;i<25;i=i+1)sum=sum^payload[i*8+:8];line=$sformatf("C%050h%02h",payload,sum);
  for(i=0;i<line.len();i=i+1)sendbyte(line[i]);sendbyte(10);tick(2500);
  end
  click(1);wait(dut.auto_run);
  x=ID==1 ? -START_X : START_X;velocity=START_V;bx=960+$rtoi(x);simulate=1;
 end
endmodule
module tb_asym_plant;
 wire [2:0] done;
 asym_plant_case #(.ID(20),.B(-5.0),.USE_PRESET(1)) a(done[0]);
 asym_plant_case #(.ID(21),.B(-10.0),.USE_PRESET(1),.START_X(-100.0)) b(done[1]);
 asym_plant_case #(.ID(22),.B(-20.0),.USE_PRESET(1)) c(done[2]);
 initial begin wait(&done);$display("ASYM_PLANT_PASS 3assumed plants,realAB12ms,15/25hold,disturbance;not physical validation");$finish;end
 initial begin #150000000;$fatal(1,"region plant timeout %b",done);end
endmodule
