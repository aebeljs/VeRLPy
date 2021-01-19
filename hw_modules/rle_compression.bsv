//https://slides.com/shilpa39/new-model-results/edit
package rle_compression;

    // Word width  : 4,8,16,32
    // zero count width : 1, 2, 3, 4, 5, 6, 7, 8 (max of only 8-bit counter)    

    import Vector::*;

    interface Ifc_rle_compression;
        method Action ma_start_compression(Bit#(4) word_width, Bit#(4) count_Width);
        method Action ma_get_input(Bit#(32) val);
        method ActionValue#(Tuple2#(Bool,Bit#(64))) mav_send_compressed_value;
        method Action ma_end_compression;
        method Bool mv_compression_done;
    endinterface 

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

    (*synthesize*)
    module mkrle_compression(Ifc_rle_compression);


        Reg#(Bit#(4)) rg_word_width <- mkReg(0);
        Reg#(Bit#(4)) rg_count_width <- mkReg(0);

        Vector#(16,Reg#(Bit#(4))) rg_compressed_word <- replicateM(mkReg(0));
        Reg#(Bit#(5)) rg_word_counter <- mkReg(0);
        Vector#(64,Reg#(Bit#(1))) rg_compressed_count <- replicateM(mkReg(0));
        Reg#(Bit#(7)) rg_zero_counter <- mkReg(0);
        Reg#(Bit#(8)) rg_counter <- mkReg(0);

        Reg#(Bit#(8)) rg_next_word <- mkReg(0);
        Reg#(Bit#(3)) rg_next_count <- mkReg(0);

        Wire#(Bit#(32)) wr_input <- mkWire();
        Wire#(Bool) wr_append_zero <- mkWire();
        Wire#(Bool) wr_last_count <- mkWire();
        Wire#(Bit#(8)) wr_append_count <- mkWire();

        rule rl_append_word(wr_input != 0 && rg_word_counter != 16);
            Bit#(5) lv_count = rg_word_counter;
            Bit#(5) lv_update_count = rg_word_counter + zeroExtend(rg_word_width);
            rg_compressed_word[lv_count] <= wr_input[3:0];
            rg_compressed_word[lv_count+1] <= wr_input[7:4];
            rg_compressed_word[lv_count+2] <= wr_input[11:8];
            rg_compressed_word[lv_count+3] <= wr_input[15:12];
            rg_compressed_word[lv_count+4] <= wr_input[19:16];
            rg_compressed_word[lv_count+5] <= wr_input[23:20];
            rg_compressed_word[lv_count+6] <= wr_input[27:24];
            rg_compressed_word[lv_count+7] <= wr_input[31:28];
            rg_word_counter <= lv_update_count;
        endrule

        rule rl_append_zero_count(wr_append_zero && rg_zero_counter != 64);
            Bit#(7) temp_count = rg_zero_counter; // 60
            Bit#(7) temp_update_count = rg_zero_counter + zeroExtend(rg_count_width);
            Bit#(4) temp_index_count = rg_count_width;
            Bit#(4) temp_word_count = zeroExtend(rg_next_count);
            if(temp_update_count > 64) begin
                rg_zero_counter <= 64;
                temp_index_count = truncate(64 - temp_count); // 4
                rg_next_count <= truncate(temp_index_count); // 4
                rg_next_word <= wr_append_count; // rg_counter
            end
            else begin       
                if(rg_next_count != 0) begin
                    temp_index_count = rg_count_width - zeroExtend(rg_next_count);
                    rg_next_count <= 0;
                    rg_next_word <= 0;
                    temp_word_count = zeroExtend(rg_next_count);
                    temp_update_count = zeroExtend(temp_index_count);
                end
                if(wr_last_count)
                    rg_zero_counter <= 64;
                else          
                    rg_zero_counter <= temp_update_count;
            end
            rg_compressed_count[temp_count] <= wr_append_count[temp_word_count];
            if(temp_index_count > 1)
                rg_compressed_count[temp_count+1] <= wr_append_count[temp_word_count+1];
            if(temp_index_count > 2)
                rg_compressed_count[temp_count+2] <= wr_append_count[temp_word_count+2];
            if(temp_index_count > 3)
                rg_compressed_count[temp_count+3] <= wr_append_count[temp_word_count+3];
            if(temp_index_count > 4)
                rg_compressed_count[temp_count+4] <= wr_append_count[temp_word_count+4];
            if(temp_index_count > 5)
                rg_compressed_count[temp_count+5] <= wr_append_count[temp_word_count+5];
            if(temp_index_count > 6)
                rg_compressed_count[temp_count+6] <= wr_append_count[temp_word_count+6];
            if(temp_index_count > 7)
                rg_compressed_count[temp_count+7] <= wr_append_count[temp_word_count+7];
        endrule

        rule rl_append_next_count(rg_zero_counter == 0 && rg_next_count != 0);
            wr_append_zero <= True;
            wr_append_count <= rg_next_word;
            wr_last_count <= False;
        endrule

        method Action ma_start_compression(Bit#(4) word_width, Bit#(4) count_Width) if(rg_zero_counter == 0 && rg_word_counter == 0);
            rg_word_width <= word_width;
            rg_count_width <= count_Width;
            rg_compressed_count[0] <= word_width[0];
            rg_compressed_count[1] <= word_width[1];
            rg_compressed_count[2] <= word_width[2];
            rg_compressed_count[3] <= word_width[3];
            rg_compressed_count[4] <= count_Width[0];
            rg_compressed_count[5] <= count_Width[1];
            rg_compressed_count[6] <= count_Width[2];
            rg_compressed_count[7] <= count_Width[3];
            rg_zero_counter <= rg_zero_counter + 8;
        endmethod
        method Action ma_get_input(Bit#(32) val) if(rg_word_counter != 16 && rg_zero_counter != 64 && rg_next_count == 0);
            if(val == 0) begin
                Bit#(8) temp = fn_max_zero_count(rg_count_width);
                if(rg_counter == temp - 1) begin
                    wr_append_zero <= True;
                    wr_append_count <= temp;
                    wr_last_count <= False;
                    if(rg_count_width != 1)
                        rg_counter <= 1;
                end
                else 
                    rg_counter <= rg_counter + 1;
            end
            else begin
                wr_append_zero <= False;
                rg_counter <= 0;
                wr_append_count <= rg_counter;
                wr_last_count <= False;
                wr_input <= val;
            end
        endmethod
        method ActionValue#(Tuple2#(Bool,Bit#(64))) mav_send_compressed_value if(rg_word_counter == 16 || rg_zero_counter == 64);
            Vector#(64,Bit#(1)) lv_count;
            Vector#(16,Bit#(4)) lv_word;
            Bit#(64) lv_output = 0;
            Bool temp_zero = False;
            if(rg_word_counter == 16) begin
                for(Integer i=0; i<16; i=i+1) begin
                    lv_word[i] = rg_compressed_word[i];
                    rg_compressed_word[i] <= 0;
                end
                rg_word_counter <= 0;
                lv_output = pack(lv_word);
            end
            else if(rg_zero_counter == 64) begin
                for(Integer i=0; i<64; i=i+1) begin
                    lv_count[i] = rg_compressed_count[i];
                    rg_compressed_count[i] <= 0;
                end 
                rg_zero_counter <= 0;
                temp_zero = True;
                lv_output = pack(lv_count);
            end
            return tuple2(temp_zero,pack(lv_output));
        endmethod
        method Action ma_end_compression;
            if(rg_zero_counter != 0)
                if(rg_counter != 0) begin
                    wr_append_zero <= True;
                    wr_append_count <= rg_counter;
                    wr_last_count <= True;
                    rg_counter <= 0;
                end
                else
                    rg_zero_counter <= 64;
            if(rg_word_counter != 0)
                rg_word_counter <= 16;
        endmethod
        method Bool mv_compression_done if(rg_zero_counter == 0 && rg_word_counter == 0);
            return True;
        endmethod
    endmodule
endpackage
