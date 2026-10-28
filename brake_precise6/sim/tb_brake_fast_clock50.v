`timescale 1ns/1ps
module tb_brake_fast_clock50;
 wire [1:0] done;
 brake_fast_plant_case #(.ID(30),.CPM(50),.B(-5.0),.USE_PRESET(1)) weak_run(done[0]);
 brake_fast_plant_case #(.ID(31),.CPM(50),.B(-20.0),.USE_PRESET(1),.START_X(-500.0),.START_V(1500.0)) fast_run(done[1]);
 initial begin wait(&done);$display("BRAKE_FAST_CLOCK50_PASS weakand1500pxs,original50clocks_ms,same100px_and25pxs_criteria");$finish;end
 initial begin #150000000;$fatal(1,"clock50 timeout");end
endmodule
