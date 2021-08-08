package coo_compression;

    //word_width  : 4,8,12,16,20,24,28,32
    //index_width : 4,8,12,16,20,24,28,32

    //TODO : parameterize with respect to Data width, max_index_width, max_word_width 

    import Vector::*;

    interface Ifc_coo_compression;
        method Action ma_start_compression(Bit#(4) word_width, Bit#(4) index_width);
        method Action ma_get_input(Bit#(64) val);
        method ActionValue#(Bit#(64)) mav_send_compressed_value;
        //method Bool mv_compression_out_ready;
        method Action ma_end_compression;
        method Bool mv_compression_done;
    endinterface

    (*synthesize*)
    module mkcoo_compression(Ifc_coo_compression);

        Reg#(Bit#(5)) rg_block_counter <- mkReg(0);
        Reg#(Bit#(5)) rg_block_length <- mkReg(0);
        Reg#(Bit#(4)) rg_word_width <- mkReg(0);
        Reg#(Bit#(4)) rg_index_width <- mkReg(0);

        Vector#(16,Reg#(Bit#(4))) rg_data <- replicateM(mkReg(0));
        Reg#(Bool) rg_append_input <- mkReg(False);
        Wire#(Bool) wr_send_output <- mkDWire(False);

        Reg#(Bit#(5)) rg_next_count <- mkReg(0);
        Vector#(16, Reg#(Bit#(4))) rg_compressed_block <- replicateM(mkReg(0));

        rule rl_append_data(rg_append_input);
            Bit#(5) lv_word_count;
            Bit#(5) lv_update_count;
            Bit#(4) lv_index_count;
            Bit#(5) lv_index_limit;
            if(rg_next_count == 0) begin
                lv_word_count = rg_block_counter;
                lv_update_count = lv_word_count + rg_block_length;
                lv_index_count = 0;
            end 
            else begin
                lv_update_count = rg_next_count;
                lv_word_count = 0;
                lv_index_count = truncate(rg_block_length-rg_next_count);
            end
            if(lv_update_count <= 16) begin
                rg_block_counter <= lv_update_count;
                rg_next_count <= 0;
                lv_index_limit = lv_update_count;
            end
            else begin
                rg_block_counter <= 16;
                lv_index_limit = 16;
                rg_next_count <= lv_update_count - 16;
            end
            rg_compressed_block[lv_word_count] <= rg_data[lv_index_count];
            for(Bit#(5) i=1; i< 16; i=i+1) begin
                if(lv_word_count+i < lv_index_limit)
                    rg_compressed_block[lv_word_count+i] <= rg_data[lv_index_count+truncate(i)];
            end
            rg_append_input <= False;
        endrule
 
        rule rl_send_compressed_output(rg_block_counter == 16);
            wr_send_output <= True;
        endrule

        method Action ma_start_compression(Bit#(4) word_width, Bit#(4) index_width) if(rg_block_counter == 0 && !rg_append_input);
            rg_block_length <= zeroExtend(word_width) + zeroExtend(index_width);
            rg_word_width <= word_width;
            rg_index_width <= index_width;
            rg_compressed_block[0] <= word_width;
            rg_compressed_block[1] <= index_width;
            rg_block_counter <= 2;
        endmethod
        method Action ma_get_input(Bit#(64) val) if(rg_block_counter != 16 && !rg_append_input);
            Vector#(16,Bit#(4)) lv_data;
            lv_data[0] = val[3:0];
            lv_data[1] = val[7:4];
            lv_data[2] = val[11:8];
            lv_data[3] = val[15:12];
            lv_data[4] = val[19:16];
            lv_data[5] = val[23:20];
            lv_data[6] = val[27:24];
            lv_data[7] = val[31:28];
            lv_data[8] = val[35:32];
            lv_data[9] = val[39:36];
            lv_data[10] = val[43:40];
            lv_data[11] = val[47:44];
            lv_data[12] = val[51:48];
            lv_data[13] = val[55:52];
            lv_data[14] = val[59:56];
            lv_data[15] = val[63:60];
            Bit#(5) lv_index = 8 - zeroExtend(rg_index_width);
            for(Bit#(5) i=0; i<16; i=i+1) begin
                if(i < zeroExtend(rg_index_width))
                    rg_data[i] <= lv_data[i];
                else if (i < zeroExtend(rg_block_length))
                    rg_data[i] <= lv_data[i+lv_index];
                else
                    rg_data[i] <= 0;
            end
            rg_append_input <= True;
        endmethod
        method ActionValue#(Bit#(64)) mav_send_compressed_value if(wr_send_output && !rg_append_input);
            if(rg_next_count != 0) begin
                rg_append_input <= True;
            end
            else
                rg_block_counter <= 0;
            for(Bit#(5) j=0; j< 16; j=j+1)
                rg_compressed_block[j] <= 0;
            Vector#(16, Bit#(4)) vec_temp_out;
            for(Bit#(5) i=0; i<16; i=i+1)
                if(i < rg_block_counter)
                    vec_temp_out[i] = rg_compressed_block[i];
                else
                    vec_temp_out[i] = 0;
            Bit#(64) temp_out = pack(vec_temp_out);
            return temp_out;
        endmethod
        //method Bool mv_compression_out_ready if(wr_send_output && !rg_append_input);
        //    return True;
        //endmethod
        method Action ma_end_compression;
            if(rg_block_counter != 0)
                rg_block_counter <= 16;
        endmethod
        method Bool mv_compression_done if(rg_block_counter == 0);
            return True;
        endmethod
    endmodule

endpackage
