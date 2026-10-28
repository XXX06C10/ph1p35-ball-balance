`timescale 1ns/1ps
module tb_cascade_config;
 reg clk=0;always #5 clk=~clk;reg rst=0,rx=1;wire applied,commit;wire [15:0] seq,errs;
 vision_cascade_config #(.UART_DIV(4),.TIMEOUT_CYCLES(3000)) dut(.clk(clk),.rst_n(rst),.rx(rx),.applied(applied),.commit_now(commit),.config_seq(seq),.errors(errs));
 integer commits=0;always @(posedge applied)commits=commits+1;
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sendbyte(input [7:0] v);integer j;begin rx=0;tick(4);for(j=0;j<8;j=j+1)begin rx=v[j];tick(4);end rx=1;tick(4);end endtask
 task packet(input [199:0] payload,input integer corrupt);
  reg [7:0] sum;integer j;string line;begin sum=0;for(j=0;j<25;j=j+1)sum=sum^payload[j*8+:8];if(corrupt)sum=sum^1;
   line=$sformatf("C%050h%02h",payload,sum);for(j=0;j<line.len();j=j+1)sendbyte(line[j]);sendbyte(10);tick(40);
  end
 endtask
 reg [199:0] good,bad;integer i,before_errors;
 initial begin
  good={8'd1,16'd1,8'd1,8'd1,16'd512,16'd128,16'd0,16'd0,16'd8192,16'd200,16'd50,8'd0,8'd4,16'd80,8'd0,8'd0};
  tick(4);rst=1;tick(20);packet(good,0);if(seq!=1 || commits!=1)$fatal(1,"C valid atomic LF");
  for(i=0;i<23;i=i+1)begin
   bad=good;
   case(i)
    0:bad[199:192]=2;1:bad[175:168]=4;2:bad[167:160]=2;3:bad[159:144]=16385;4:bad[143:128]=2049;
    5:bad[127:112]=3278;6:bad[111:96]=2049;7:bad[111:96]=-2049;8:bad[95:80]=255;9:bad[95:80]=32769;
    10:bad[79:64]=257;11:bad[63:48]=49;12:bad[63:48]=201;13:bad[47:40]=121;14:bad[39:32]=3;
    15:begin bad[175:168]=3;bad[39:32]=16;end
    16:bad[31:16]=7;17:bad[31:16]=257;18:bad[15:8]=2;19:bad[7:0]=1;
    20:bad[175:168]=255;21:bad[63:48]=0;22:bad[39:32]=0;
   endcase
   before_errors=errs;packet(bad,0);if(commits!=1 || seq!=1 || errs!=before_errors+1)$fatal(1,"C bound case%0d",i);
  end
  packet(good,1);if(commits!=1)$fatal(1,"C bad XOR committed");
  sendbyte("P");sendbyte("C");sendbyte("0");sendbyte(10);tick(30);if(commits!=1)$fatal(1,"C found inside legacy line");
  sendbyte("C");sendbyte("0");tick(3010);sendbyte(10);tick(30);if(commits!=1)$fatal(1,"C truncated timeout committed");
  good[191:176]=2;packet(good,0);if(commits!=2 || seq!=2)$fatal(1,"C did not recover after rejected input");
  $display("CASCADE_CONFIG_PASS:23bounds,XOR,line-start framing,timeout/recovery,LF atomicity,no motion interface");$finish;
 end
 initial begin #10000000;$fatal(1,"C parser timeout");end
endmodule
