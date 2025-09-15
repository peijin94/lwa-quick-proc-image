import numpy as np
import casatools, casatasks

casatasks.applycal(vis='/fast/peijinz/agile_proc/testdata/slow/20240519_173002_55MHz.ms',
                    gaintable='/fast/peijinz/agile_proc/testdata/caltables/20240517_100405_55MHz.bcal',
                    applymode='calflag')