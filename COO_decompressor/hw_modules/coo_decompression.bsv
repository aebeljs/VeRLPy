package coo_decompression;

    import Vector::*;
    import DReg::*;

    //TODO : Parameterise with respect to datawidth

    interface Ifc_coo_decompression;
        method Action ma_get_inputs(Bit#(64) val);
        method Bit#(64) mv_get_decompressed_output;
        method Action ma_send_decompressed_output;
        //method Bool mv_decompressor_busy;
    endinterface

    (*synthesize*)
    module mkcoo_decompression(Ifc_coo_decompression);

        Reg#(Bit#(4)) rg_word_width <- mkReg(0);
        Reg#(Bit#(4)) rg_index_width <- mkReg(0);
        Reg#(Bit#(5)) rg_block_counter <- mkReg(0);

        Vector#(16, Reg#(Bit#(4))) rg_compressed_block <- replicateM(mkReg(0));
        Reg#(Bool) rg_input_valid <- mkReg(False);
        Reg#(Bool) rg_output_valid <- mkDReg(False);
        Reg#(Bit#(5)) rg_next_count <- mkReg(0);

        Vector#(8,Reg#(Bit#(4))) rg_word <- replicateM(mkReg(0));
        Vector#(8,Reg#(Bit#(4))) rg_index <- replicateM(mkReg(0)); 

        Wire#(Bool) wr_decompress <- mkWire();

        rule rl_decompress_output(wr_decompress && rg_input_valid);
            Bit#(5) lv_block_count = rg_block_counter;
            Bit#(5) lv_update_count = rg_block_counter + zeroExtend(rg_word_width) + zeroExtend(rg_index_width);
            Bit#(5) lv_start_count = rg_next_count;
            if(lv_update_count <= 16) begin
                rg_block_counter <= lv_update_count - lv_start_count;
                rg_next_count <= 0;
                rg_output_valid <= True;
            end
            else begin
                rg_block_counter <= 0;
                rg_next_count <= 16 - rg_block_counter;
                rg_input_valid <= False;
            end
            for(Bit#(5) j=0; j<8; j=j+1)
                if(j+lv_start_count < zeroExtend(rg_index_width) && lv_block_count-lv_start_count+j < 16)
                    rg_index[lv_start_count+j] <= rg_compressed_block[lv_block_count-lv_start_count+j];
                else
                    rg_index[lv_start_count+j] <= 0;
            Bit#(5) lv_word_count = lv_block_count - lv_start_count + zeroExtend(rg_index_width);
            if(lv_start_count < zeroExtend(rg_index_width))
                lv_start_count = 0;
            else
                lv_start_count = lv_start_count - zeroExtend(rg_index_width);
            for(Bit#(5) i=0; i<8; i=i+1)
                if(i+lv_start_count < zeroExtend(rg_word_width) && lv_word_count+i < 16)
                    rg_word[lv_start_count+i] <= rg_compressed_block[lv_word_count+i];
                else
                    rg_word[lv_start_count+i] <= 0;
            //$display($time," Decompressor output : block counter %x : index %x %x %x %x %x %x %x %x : word %x %x %x %x %x %x %x %x \n \t \t next count %x : %x %x %x %x %x %x %x %x %x %x %x %x %x %x %x %x \n", 
            //            rg_block_counter, rg_index[7],rg_index[6],rg_index[5],rg_index[4],rg_index[3],rg_index[2],rg_index[1],rg_index[0], 
            //            rg_word[7], rg_word[6], rg_word[5], rg_word[4], rg_word[3], rg_word[2], rg_word[1], rg_word[0], rg_next_count,
            //            rg_compressed_block[15], rg_compressed_block[14], rg_compressed_block[13], rg_compressed_block[12], rg_compressed_block[11], rg_compressed_block[10],
            //            rg_compressed_block[9], rg_compressed_block[8], rg_compressed_block[7], rg_compressed_block[6], rg_compressed_block[5], rg_compressed_block[4],
            //            rg_compressed_block[3], rg_compressed_block[2], rg_compressed_block[1], rg_compressed_block[0]);
        endrule

        method Action ma_get_inputs(Bit#(64) val) if(rg_block_counter == 0);
            rg_compressed_block[0] <= val[3:0];
            rg_compressed_block[1] <= val[7:4];
            rg_compressed_block[2] <= val[11:8];
            rg_compressed_block[3] <= val[15:12];
            rg_compressed_block[4] <= val[19:16];
            rg_compressed_block[5] <= val[23:20];
            rg_compressed_block[6] <= val[27:24];
            rg_compressed_block[7] <= val[31:28];
            rg_compressed_block[8] <= val[35:32];
            rg_compressed_block[9] <= val[39:36];
            rg_compressed_block[10] <= val[43:40];
            rg_compressed_block[11] <= val[47:44];
            rg_compressed_block[12] <= val[51:48];
            rg_compressed_block[13] <= val[55:52];
            rg_compressed_block[14] <= val[59:56];
            rg_compressed_block[15] <= val[63:60];
            if(rg_word_width == 0) begin
                rg_word_width <= val[3:0];
                rg_index_width <= val[7:4];
                rg_block_counter <= 2;
            end
            rg_input_valid <= True;
            //$display($time," Decompressor input : block counter %x : index %x %x %x %x %x %x %x %x word %x %x %x %x %x %x %x %x next count %x \n",
            //                    rg_block_counter,rg_index[7],rg_index[6],rg_index[5],rg_index[4],rg_index[3],rg_index[2],rg_index[1],rg_index[0],
            //                    rg_word[7],rg_word[6],rg_word[5],rg_word[4],rg_word[3],rg_word[2],rg_word[1],rg_word[0],rg_next_count);
        endmethod

        method Bit#(64) mv_get_decompressed_output if(rg_output_valid);
            return {pack(readVReg(rg_index)),pack(readVReg(rg_word))};
        endmethod
        method Action ma_send_decompressed_output if(rg_input_valid);
            wr_decompress <= True;
        endmethod
        //method Bool mv_decompressor_busy;
        //    return rg_input_valid;
        //endmethod
    endmodule

endpackage