import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.monitors import BusMonitor
from cocotb.drivers import BusDriver
from cocotb.binary import BinaryValue
from cocotb.scoreboard import Scoreboard

class Driver(BusDriver):
    _signals = [
            'EN_ma_get_inputs',
            'ma_get_inputs_val',
            ]

    def __init__(self, dut):
        BusDriver.__init__(self, dut, None, dut.CLK)

class InputTransaction(object):

    def __init__(self,tb,
            EN_ma_get_inputs=0,
            ma_get_inputs_val=0,
            ):

        self.EN_ma_get_inputs = BinaryValue(EN_ma_get_inputs, tb.EN_width, False)
        self.ma_get_inputs_val = BinaryValue(ma_get_inputs_val, tb.input_width, False)

class Output_en_Driver(BusDriver):
    _signals = [
            'EN_ma_send_decompressed_output',
            ]

    def __init__(self, dut):
        BusDriver.__init__(self, dut, None, dut.CLK)

class Output_en_Transaction(object):

    def __init__(self,tb,
            EN_ma_send_decompressed_output=0,
            ):

        self.EN_ma_send_decompressed_output = BinaryValue(EN_ma_send_decompressed_output,
                tb.EN_width, False)

class InputMonitor(BusMonitor):
    _signals = [
            'EN_ma_get_inputs',
            'ma_get_inputs_val',
            'EN_ma_send_decompressed_output',
            'RDY_ma_get_inputs',
            'RDY_ma_send_decompressed_output',
            ]

    def __init__(self,dut,callback=None,event=None):
        BusMonitor.__init__(self,dut,None,dut.CLK,dut.RST_N,callback=callback,event=event)
        self.name = "in"

    @coroutine
    def _monitor_recv(self):
        EN_inp_edge = RisingEdge(self.bus.EN_ma_get_inputs)
        while True:
            if((self.bus.EN_ma_get_inputs == 1 and self.bus.RDY_ma_get_inputs == 1) or
               (self.bus.EN_ma_send_decompressed_output == 1 and self.bus.RDY_ma_send_decompressed_output == 1)):
                # print('[IN_MON] {0:25} : {1}'.format('EN_ma_get_inputs',self.bus.EN_ma_get_inputs.value.integer))
                # print('[IN_MON] {0:25} : {1}'.format('ma_get_inputs',hex(self.bus.ma_get_inputs_val.value.integer)))
                # print('[IN_MON] {0:25} : {1}'.format('EN_ma_send_decompressed_output',self.bus.EN_ma_send_decompressed_output.value.integer))
                vec = (
                        self.bus.EN_ma_get_inputs.value.integer,
                        self.bus.ma_get_inputs_val.value.integer,
                        self.bus.EN_ma_send_decompressed_output.value.integer
                        )
                self._recv(vec)

            yield RisingEdge(self.clock)


class OutputTransaction(object):

    def __init__(self, tb=None,
            RDY_ma_get_inputs=0,
            mv_get_decompressed_output=0,
            RDY_mv_get_decompressed_output=0,
            RDY_ma_send_decompressed_output=0,
            ):
        if RDY_ma_get_inputs is not None and isinstance(RDY_ma_get_inputs, int):
            RDY_ma_get_inputs = BinaryValue(RDY_ma_get_inputs, tb.RDY_width, False)
        if mv_get_decompressed_output is not None and isinstance(mv_get_decompressed_output, int):
            mv_get_decompressed_output = BinaryValue(mv_get_decompressed_output, tb.output_width,False)
        if RDY_mv_get_decompressed_output is not None and isinstance(RDY_mv_get_decompressed_output, int):
            RDY_mv_get_decompressed_output = BinaryValue(RDY_mv_get_decompressed_output, tb.RDY_width, False)
        if RDY_ma_send_decompressed_output is not None and isinstance(RDY_ma_send_decompressed_output, int):
            RDY_ma_send_decompressed_output = BinaryValue(RDY_ma_send_decompressed_output, tb.RDY_width, False)

        self.value = (
                RDY_ma_get_inputs,
                mv_get_decompressed_output,
                RDY_mv_get_decompressed_output,
                RDY_ma_send_decompressed_output

        )

class Monitor(BusMonitor):
    _signals = [
            'RDY_ma_get_inputs',
            'mv_get_decompressed_output',
            'RDY_mv_get_decompressed_output',
            'RDY_ma_send_decompressed_output'
    ]


    def __init__(self,dut,tb,callback=None,event=None):
        BusMonitor.__init__(self,dut,None,dut.CLK,dut.RST_N,callback=callback, event=event)
        self.name = "out"
        self.tb = tb

    @coroutine
    def _monitor_recv(self):
        outp_edge = RisingEdge(self.bus.RDY_mv_get_decompressed_output)
        while True:
            if self.bus.RDY_mv_get_decompressed_output.value != 1:
                yield outp_edge
            # print('[DUT_MON] {0:<25} : {1}'.format('RDY_ma_get_inputs',self.bus.RDY_ma_get_inputs.value))
            # print('[DUT_MON] {0:<25} : {1}'.format('mv_get_decompressed_output',self.bus.mv_get_decompressed_output.value))
            # print('[DUT_MON] {0:<25} : {1}'.format('RDY_mv_get_decompressed_output',self.bus.RDY_mv_get_decompressed_output.value))
            # print('[DUT_MON] {0:<25} : {1}'.format('RDY_ma_send_decompressed_output',self.bus.RDY_ma_send_decompressed_output.value))

            self._recv(OutputTransaction(self.tb,
                self.bus.RDY_ma_get_inputs.value,
                self.bus.mv_get_decompressed_output.value,
                self.bus.RDY_mv_get_decompressed_output.value,
                self.bus.RDY_ma_send_decompressed_output.value))

            yield RisingEdge(self.clock)


class DUTScoreboard(Scoreboard):
    def compare(self, got, exp, log, **_):
        # print(got.value[1])
        # print(exp.value[1])
        if(got.value[1] != exp.value[1]):
            print("Values mismatched")
            exit(1)
        # else:
        #     print("Values matched")


class Testbench(object):

    def __init__(self, dut):
        self.dut = dut
        self.stopped = False

        self.EN_width = 1
        self.RDY_width = 1
        self.input_width = 64
        self.output_width = 16

        self.input_drv = Driver(dut)
        self.input_mon = InputMonitor(dut, callback=self.model)

        self.outen_drv = Output_en_Driver(dut)
        #self.outen_get_drv = Output_get_en_Driver(dut)

        init_val = OutputTransaction(self)
        self.mon = Monitor(dut, self)

        self.expected_output = []
        self.scoreboard = DUTScoreboard(dut)
        #self.scoreboard.add_interface(self.mon, seld.expected_output)

    def model(self, transaction):
        (
                EN_ma_get_inputs,
                ma_get_inputs_val,
                EN_ma_send_decompressed_output
        ) = transaction
        # print("From Model")
        # print("",EN_ma_get_inputs, ma_get_inputs_val, EN_ma_send_decompressed_output)

    def stop(self):
        self.stopped = True

@cocotb.coroutine
def clock_gen(signal):
    while True:
        signal <= 0
        yield Timer(1)
        signal <= 1
        yield Timer(1)

@cocotb.coroutine
def en_decompressed_output(dut,tb):
    while True:
        #yield RisingEdge(dut.CLK)
        if(dut.RDY_ma_send_decompressed_output != 1):
            yield RisingEdge(dut.RDY_ma_send_decompressed_output)
        yield tb.outen_drv.send(Output_en_Transaction(tb,1))
        yield FallingEdge(dut.RDY_ma_send_decompressed_output)
        yield tb.outen_drv.send(Output_en_Transaction(tb,0))
        #yield FallingEdge(dut.CLK)
        #else:
        #   yield RisingEdge(dut.CLK)
