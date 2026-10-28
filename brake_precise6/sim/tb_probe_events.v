`timescale 1ns/1ps
module tb_probe_events;
 reg clk=0;always #5 clk=~clk;reg rst=0,grant=0;reg [3:0] state=0;reg [31:0] time_ms=0;
 wire tx,busy,wants,overflow;
 vision_probe_events #(.UART_DIV(4)) dut(.clk(clk),.rst_n(rst),.enabled(1'b1),.grant(grant),.time_ms(time_ms),.step(1'b0),.dir(1'b0),
 .position(-32'sd31),.command_position(-32'sd24),.state(state),.pending(8'd1),.commands(-16'sd1),.delta(-16'sd2),.diagnostic_flags({overflow,7'd0}),
 .phase(4'd0),.status(4'd1),.selection(8'd1),.reason(4'd0),.changed(1'b0),.tx(tx),.busy(busy),.wants(wants),.overflow(overflow));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 integer count=0,prev=-1;reg gap=0;
 function [3:0] nibble(input [7:0] ch);begin nibble=ch<="9" ? ch-"0" : ch-"A"+10;end endfunction
 initial begin : decode
  reg [7:0] b,xor8;integer i,j,seq;string line;line="";
  forever begin @(negedge tx);repeat(6)@(posedge clk);#1;
   for(i=0;i<8;i=i+1)begin b[i]=tx;repeat(4)@(posedge clk);#1;end
   if(!tx)$fatal(1,"E1 UART stop");line={line,b};
   if(b==10)begin
    if(line.len()!=58 || line.substr(0,1)!="E1")$fatal(1,"E1 wire length");
    xor8=0;for(j=2;j<56;j=j+2)xor8=xor8^{nibble(line[j]),nibble(line[j+1])};if(xor8!=0)$fatal(1,"E1 XOR");
    seq=0;for(j=2;j<6;j=j+1)seq=seq*16+nibble(line[j]);
    if(prev>=0 && seq!=((prev+1)&65535))gap=1;prev=seq;count=count+1;
    if(count<=2 || gap)$display("PROBE_FIFO_WIRE %s",line);line="";
   end
  end
 end
 initial begin
  tick(4);rst=1;
  repeat(140)begin state=state+1'b1;tick(1);end
  if(!overflow || !wants || dut.wr!=128)$fatal(1,"FIFO full must drop and latch");
  grant=1;tick(4000);state=state+1'b1;tick(1);
  tick(320000);if(count!=129 || !gap || !overflow)$fatal(1,"FIFO drain/count/gap %d %b",count,gap);
  $display("PROBE_EVENTS_PASS: actual FIFO128 overflow, sticky loss, sequence gap, E58 UART XOR signed payload");$finish;
 end
 initial begin tick(500000);$fatal(1,"FIFO timeout");end
endmodule
