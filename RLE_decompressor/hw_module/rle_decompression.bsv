package rle_decompression;

    import Vector::*;

		function Bit#(8) fn_max_zero_count(Bit#(4) width);
         if(width == 1)
             return 1;
         else if(width == 2)
             return 3; 
         else if(width == 3)
             return 7;
         else if(width == 4)
             return 15;
         else if(width == 5)
             return 31;
         else if(width == 6)
             return 63;
         else if(width == 7)
             return 127;
         else
             return 255; 
     endfunction
 

    interface Ifc_rle_decompression;
        method Action ma_get_inputs(Bit#(64) val);
        method Bit#(32) mv_get_decompressed_output;
        method Action ma_send_decompressed_output;
    endinterface : Ifc_rle_decompression

    (*synthesize*)
    module mkrle_decompression(Ifc_rle_decompression);

        Vector#(64,Reg#(Bit#(1))) rg_count_block <- replicateM(mkReg(0)); //Holds the compressed zero count values
        Vector#(16,Reg#(Bit#(4))) rg_word_block <- replicateM(mkReg(0));  //Holds the compressed word

        Reg#(Bool) rg_count_valid <- mkReg(False); //Validity of zero count
        Reg#(Bool) rg_word_valid <- mkReg(False);  //Validity of word
        Reg#(Bool) rg_counter_valid <- mkReg(False);

        Reg#(Bit#(7)) rg_zero_counter <- mkReg(0); //Count on zero count block
        Reg#(Bit#(5)) rg_word_counter <- mkReg(0); //Count on word block
        Reg#(Bit#(8)) rg_counter <- mkReg(0);      //8-bit zero counter
        Reg#(Bit#(4)) rg_count_width <- mkReg(0);  //Holds zero count width
        Reg#(Bit#(4)) rg_word_width <- mkReg(0);   //Holds word width
        Reg#(Bit#(4)) rg_next_count <- mkReg(0);   //Holds the zero count in next block

        Wire#(Bool) wr_send_output <- mkWire();    //Condition to send decompressed output - rule condition
        Wire#(Bool) wr_output_valid <- mkWire();   //Holds Validity of output
        Wire#(Bit#(32)) wr_decompressed_output <- mkWire(); //Holds the current output
        Reg#(Bool) rg_is_next_word <- mkReg(False);

        rule rl_decompress_word(wr_send_output && rg_is_next_word && rg_counter == 0);
            Bit#(32) lv_output = 0;
            Bit#(5) lv_count = rg_word_counter;
            Bit#(5) lv_update_count = rg_word_counter + zeroExtend(rg_word_width);
            lv_output[3:0] = rg_word_block[lv_count];
            if(rg_word_width > 1)
                lv_output[7:4] = rg_word_block[lv_count+1];
            if(rg_word_width > 2) begin
                lv_output[11:8] = rg_word_block[lv_count+2];
                lv_output[15:12] = rg_word_block[lv_count+3];
            end
            if(rg_word_width > 4) begin
                lv_output[19:16] = rg_word_block[lv_count+4];
                lv_output[23:20] = rg_word_block[lv_count+5];
                lv_output[27:24] = rg_word_block[lv_count+6];
                lv_output[31:28] = rg_word_block[lv_count+7];
            end
            if(lv_update_count == 16)
                rg_word_valid <= False;
            wr_output_valid <= True;
            wr_decompressed_output <= lv_output;
            rg_counter_valid <= False;
            rg_is_next_word <= False;
            rg_word_counter <= lv_update_count;
        endrule

        rule rl_update_counter((rg_counter == 0 || rg_next_count != 0) && !rg_counter_valid && rg_count_valid);
            Bit#(7) lv_count = rg_zero_counter;
            Bit#(7) lv_update_count = rg_zero_counter + zeroExtend(rg_count_width);
            Bit#(4) lv_counter_index = 0;
            Bit#(4) lv_allowed_count = rg_count_width;
            if(rg_next_count != 0) begin
                lv_counter_index = rg_next_count;
                lv_update_count = zeroExtend(rg_count_width - rg_next_count);
                lv_allowed_count = truncate(lv_update_count);
                rg_next_count <= 0;
            end
            Bit#(8) lv_zero_count = 0;
            lv_zero_count[lv_counter_index] = rg_count_block[lv_count];
            if(lv_allowed_count > 1)
                lv_zero_count[lv_counter_index+1] = rg_count_block[lv_count+1];
            if(lv_allowed_count > 2)
                lv_zero_count[lv_counter_index+2] = rg_count_block[lv_count+2];
            if(lv_allowed_count > 3)
                lv_zero_count[lv_counter_index+3] = rg_count_block[lv_count+3];
            if(lv_allowed_count > 4)
                lv_zero_count[lv_counter_index+4] = rg_count_block[lv_count+4];
            if(lv_allowed_count > 5)
                lv_zero_count[lv_counter_index+5] = rg_count_block[lv_count+5];
            if(lv_allowed_count > 6)
                lv_zero_count[lv_counter_index+6] = rg_count_block[lv_count+6];
            if(lv_allowed_count > 7)
                lv_zero_count[lv_counter_index+7] = rg_count_block[lv_count+7];
            
            for(Bit#(4) i = 0; i<8; i=i+1) begin
                if(i < lv_counter_index)
                    lv_zero_count[i] = rg_counter[i];
            end
            if(lv_zero_count == fn_max_zero_count(rg_count_width))
                rg_counter <= lv_zero_count - 1;
            else
                rg_counter <= lv_zero_count;

            if(lv_update_count >= 64) begin
                lv_allowed_count = truncate(64-lv_count);
                rg_next_count <= lv_allowed_count;
                rg_zero_counter <= 64;
                rg_count_valid <= False;
            end
            else begin
                rg_zero_counter <= lv_update_count;
                rg_counter_valid <= True;
                if(lv_zero_count == 0 || lv_zero_count != fn_max_zero_count(rg_count_width))
                    rg_is_next_word <= True;
            end
        endrule

        rule rl_decompress_zero(wr_send_output && rg_counter != 0);
            wr_decompressed_output <= 0;
            wr_output_valid <= True;
            rg_counter <= rg_counter - 1;
            if(rg_counter == 1 && !rg_is_next_word)
                rg_counter_valid <= False;
        endrule

        method Action ma_get_inputs(Bit#(64) val) if(rg_count_valid == False || rg_word_valid == False);
            if(!rg_count_valid) begin
                for(Integer i=0; i<64; i=i+1)
                    rg_count_block[i] <= val[i];
                rg_count_valid <= True;
                if(rg_zero_counter == 0) begin
                    rg_word_width <= val[3:0];
                    rg_count_width <= val[7:4];
                    rg_zero_counter <= 8;
                end
                else
                    rg_zero_counter <= 0;
            end
            else begin
                rg_word_block[0] <= val[3:0];
                rg_word_block[1] <= val[7:4];
                rg_word_block[2] <= val[11:8];
                rg_word_block[3] <= val[15:12];
                rg_word_block[4] <= val[19:16];
                rg_word_block[5] <= val[23:20];
                rg_word_block[6] <= val[27:24];
                rg_word_block[7] <= val[31:28];
                rg_word_block[8] <= val[35:32];
                rg_word_block[9] <= val[39:36];
                rg_word_block[10] <= val[43:40];
                rg_word_block[11] <= val[47:44];
                rg_word_block[12] <= val[51:48];
                rg_word_block[13] <= val[55:52];
                rg_word_block[14] <= val[59:56];
                rg_word_block[15] <= val[63:60];
                rg_word_valid <= True;
                rg_word_counter <= 0;
            end
        endmethod
        method Bit#(32) mv_get_decompressed_output if(wr_output_valid);
            return wr_decompressed_output;
        endmethod
        method Action ma_send_decompressed_output if(rg_word_valid && rg_count_valid && rg_next_count == 0);
            wr_send_output <= True;
        endmethod
    endmodule : mkrle_decompression

endpackage : rle_decompression
