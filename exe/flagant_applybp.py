import casatasks
from ovrolwasolar import flagging
import shutil
import argparse

from casatasks import flagdata, split

parser = argparse.ArgumentParser()
parser.add_argument("input_ms", type=str)
parser.add_argument("gaintable", type=str)
parser.add_argument("output_ms", type=str)

args = parser.parse_args()
input_ms = args.input_ms
gaintable = args.gaintable
output_ms = args.output_ms

# remove short baselines but keep autocorr
flagdata(vis=input_ms, mode='manual', uvrange='0.1~10lambda', flagbackup=False)
split(vis=input_ms, outputvis=output_ms, datacolumn='data', keepflags=False)

flagging.flag_bad_ants(output_ms)
casatasks.applycal( vis=output_ms,gaintable=gaintable, applymode='calflag')