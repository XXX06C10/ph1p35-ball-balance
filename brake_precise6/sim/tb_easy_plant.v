`timescale 1ns/1ps
module tb_easy_plant;
 wire [2:0] done;
 cascade_plant_case #(.ID(3),.B(-5.0),.USE_PRESET(1)) p0(done[0]);
 cascade_plant_case #(.ID(4),.B(-10.0),.USE_PRESET(1)) p1(done[1]);
 cascade_plant_case #(.ID(5),.B(-20.0),.USE_PRESET(1)) p2(done[2]);
 initial begin wait(&done);$display("EASY_PLANT_ALL_PASS:3assumed plants,same built-in gains,no serial configuration,K3/K2,5s recovery10s hold;physical pending");$finish;end
 initial begin #100000000;$fatal(1,"easy plant timeout %b",done);end
endmodule
