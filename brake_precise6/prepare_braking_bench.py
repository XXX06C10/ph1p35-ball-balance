from pathlib import Path
r=Path(__file__).resolve().parent;read=lambda p:p.read_text(encoding='utf-8-sig')
p=r/'sim/tb_cascade_plant.v';s=read(p)
s=s.replace('SLEW=102,USE_PRESET=0)', 'SLEW=102,USE_PRESET=0,parameter real START_X=100.0,START_V=0.0)')
s=s.replace('integer samples=0;','integer samples=0;real overshoot=0.0;integer quiet_since=-1,first_settle=-1;')
s=s.replace('    velocity=velocity+acceleration*0.001;x=x+velocity*0.001;', '''    velocity=velocity+acceleration*0.001;x=x+velocity*0.001;
    if(ms<8000 && x*START_X<0 && (x<0 ? -x : x)>overshoot)overshoot=x<0 ? -x : x;
    if(ms<8000)begin
     if(x<=10 && x>=-10 && velocity<=15 && velocity>=-15)begin
      if(quiet_since<0)quiet_since=ms;
      if(ms-quiet_since>=1000 && first_settle<0)first_settle=quiet_since;
     end else quiet_since=-1;
    end''')
s=s.replace('     $fclose(trace);done=1;simulate=0;', '     $display("PLANT_BRAKING_METRIC id=%0d settle_ms=%0d overshoot=%f",ID,first_settle,overshoot);\n     $fclose(trace);done=1;simulate=0;')
s=s.replace('x=ID==1 ? -100.0 : 100.0;bx=960+$rtoi(x);simulate=1;', 'x=ID==1 ? -START_X : START_X;velocity=START_V;bx=960+$rtoi(x);simulate=1;')
p.write_text(s,encoding='utf-8')
(r/'sim/tb_braking_plant.v').write_text('''`timescale 1ns/1ps
module tb_braking_plant;
 wire [4:0] done;
 cascade_plant_case #(.ID(6),.B(-5.0),.USE_PRESET(1),.START_X(100.0),.START_V(0.0)) p0(done[0]);
 cascade_plant_case #(.ID(7),.B(-10.0),.USE_PRESET(1),.START_X(-100.0),.START_V(0.0)) p1(done[1]);
 cascade_plant_case #(.ID(8),.B(-20.0),.USE_PRESET(1),.START_X(100.0),.START_V(0.0)) p2(done[2]);
 cascade_plant_case #(.ID(9),.B(-10.0),.USE_PRESET(1),.START_X(400.0),.START_V(-400.0)) p3(done[3]);
 cascade_plant_case #(.ID(10),.B(-20.0),.USE_PRESET(1),.START_X(400.0),.START_V(-800.0)) p4(done[4]);
 initial begin wait(&done);$display("BRAKING_PLANT_ALL_PASS: 5assumed plants/initial states,fast approach400/800pxs,trueAB12ms,200Hz,60counts,5s recovery10s hold;not physical acceptance");$finish;end
 initial begin #150000000;$fatal(1,"braking plant timeout %b",done);end
endmodule
''',encoding='utf-8')
p=r/'run_sim.ps1';s=read(p);anchor="    if($Testbench -eq 'tb_easy_plant'){$inputs+='sim/tb_cascade_plant.v'}"
assert anchor in s;s=s.replace(anchor,anchor+"\n    if($Testbench -eq 'tb_braking_plant'){$inputs+='sim/tb_cascade_plant.v'}");p.write_text(s,encoding='utf-8-sig')
print('BRAKING_BENCH_READY')
