`timescale 1ns/1ps
module tb_probe_guards;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,key=0,k4=1,en=1,valid=1,stale=0,frame=0,changed=0,overflow=0;
 reg [7:0] sel=2;reg signed [31:0] p=0;reg [31:0] t=0;reg [10:0] x=960,y=500;
 reg [15:0] left=0,right=1279,top=0,bottom=719;reg [3:0] fault=0;
 wire run,request,cancel;wire [3:0] status,phase,reason,reject;wire signed [7:0] target;
 vision_region_probe #(.MS_CYCLES(2)) dut(.clk(clk),.rst_n(rst),.key_event(key),.k4_n(k4),.enable_request(en),.settings_ready(1'b1),
 .valid(valid),.stale(stale),.frame(frame),.changed(changed),.center_confirmed(1'b1),.neutral_ready(1'b1),.core_ready(1'b1),.core_busy(1'b0),
 .event_overflow(overflow),.selection(sel),.neutral(8'sd0),.position(p),.fault(fault),.time_ms(t),.x(x),.y(y),.center(16'd960),
 .roi_left(left),.roi_right(right),.roi_top(top),.roi_bottom(bottom),.run(run),.request(request),.cancel(cancel),.status(status),.phase(phase),.reason(reason),.reject(reject),.target(target));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task check(input integer ok,input string label);begin if(!ok)$fatal(1,"PROBE_GUARD %s run=%b status=%d why=%d",label,run,status,reason);end endtask
 task configure(input integer s);begin changed=1;sel=s;tick(1);changed=0;tick(1);check(status==0 && !run,"fresh config clear DONE");end endtask
 task start;begin key=1;tick(1);key=0;tick(1);end endtask
 task sample(input integer timevalue,newx);begin t=timevalue;x=newx;frame=1;tick(1);frame=0;tick(1);end endtask
 integer i;
 initial begin
  tick(3);rst=1;en=0;configure(2);start;check(run,"static permits disabled motor");tick(19990);check(run,"static cannot end early");tick(14);check(status==2,"static full10s");
  en=1;configure(3);start;tick(100);key=1;tick(1);key=0;check(!run && status==4 && reason==7,"K2 abort");
  configure(1);start;tick(2005);check(!run && status==4 && reason==11,"single leg1s deadline");
  configure(1);start;p=8;tick(190);check(!dut.holding,"100ms band required");tick(20);check(dut.holding,"100ms band qualifies");p=4;tick(3);check(!run && reason==12,"hold drift stops");p=0;
  configure(1);start;overflow=1;tick(1);check(!run && reason==14,"real FIFO loss stops");overflow=0;
  configure(1);start;fault=4;tick(1);check(!run && reason==6,"F4 never cleared");fault=0;
  configure(1);start;valid=0;tick(1);check(!run && reason==3,"loss immediate in probe");valid=1;tick(10);check(!run,"no resume");
  configure(1);start;stale=1;tick(1);check(!run && reason==4,"200ms external stale abort");stale=0;
  configure(1);start;k4=0;tick(1);check(!run && reason==2,"K4 abort");k4=1;
  configure(1);start;en=0;tick(1);check(!run && reason==1,"K1 abort");en=1;
  configure(1);start;x=1081;tick(1);check(!run && reason==9,"120px offset");x=960;
  // 1280 sensor ROI corresponds to1920 telemetry pixels. Test actual transformed edge.
  configure(1);right=650;start;check(!run && reject==3,"right ROI24pixel guard");right=1279;
  configure(1);start;sample(1000,960);sample(1033,964);check(run,"121px/s allowed");sample(1066,970);check(!run && reason==15,"181px/s rejected");x=960;
  configure(1);start;changed=1;tick(1);changed=0;check(!run && status==0,"configuration clear active");
  $display("PROBE_GUARDS_PASS exact10s/100ms/1s, transformedROI, speed/loss/fault/K1K2K4/config/overflow");$finish;
 end
 initial begin tick(100000);$fatal(1,"guard timeout");end
endmodule
