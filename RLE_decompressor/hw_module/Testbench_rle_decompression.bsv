import rle_decompression::*;
import BRAMCore::*;

`define Sram_addr_length 28
`define Data_width 64
`define Length_of_data 6

module mkTestbench();

    Reg#(Bit#(`Sram_addr_length)) rg_address_counter <- mkReg(0);
	Reg#(Bit#(`Sram_addr_length)) rg_compresses_count <- mkReg(1);
	Bit#(`Sram_addr_length) length_data = fromInteger(valueOf(`Length_of_data));

	BRAM_PORT#(Bit#(`Sram_addr_length), Bit#(`Data_width)) onchip_sram <- mkBRAMCore1Load(valueOf(TExp#(`Sram_addr_length)), False,"/home/sadhana/Documents/SA_comp_decomp/paper_work/series_parallel_comp_decomp/fmaps/l1_rle_decompress", False);

    Ifc_rle_decompression rle_decomp <- mkrle_decompression;

    Reg#(Bit#(3)) rg_flag <- mkReg(0);
    Reg#(Bit#(2)) rg_flag_2 <- mkReg(0);

    rule rl_dumpvars;
        $dumpvars();
    endrule

    rule rl_get_first_data(rg_flag == 0);
        onchip_sram.put(False,rg_address_counter,?);
        rg_flag <= 1;
    endrule

    rule rl_send_compressed_words(rg_flag == 1);
        Bit#(`Data_width) temp_data = onchip_sram.read;
        $display($time," Input to decompressor : %x , %x \n",rg_address_counter,temp_data);
        rle_decomp.ma_get_inputs(temp_data);
        rg_address_counter <= rg_address_counter + 1;
        if(rg_address_counter == length_data - 1)
            rg_flag <= 2;
        else
            rg_flag <= 0;
    endrule
    
    rule rl_get_decompressed_output_1(rg_address_counter > 0);
        rle_decomp.ma_send_decompressed_output;
    endrule

    rule rl_get_decompressed_output_2;
        let word = rle_decomp.mv_get_decompressed_output;
        $display($time, " %d : Decompressed output : %x \n", rg_compresses_count,word);
        rg_compresses_count <= rg_compresses_count + 1;
    endrule
/*
    rule rl_end_decompression(rg_flag == 2);
        //coo_decomp.ma_end_decompression;
        rg_flag <= 3;
    endrule

    rule rl_finish(rg_flag == 3);
        $finish;
    endrule
*/
endmodule