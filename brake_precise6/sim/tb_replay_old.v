module tb_replay_old;
 wire done;replay_case #(.OLD(1)) c(done);
 initial begin wait(done);$display("REPLAY_OLD_ALL_PASS");$finish;end
 initial begin #120000000;$fatal(1,"old replay timeout");end
endmodule
