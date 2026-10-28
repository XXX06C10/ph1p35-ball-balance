`timescale 1ns/1ps
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
