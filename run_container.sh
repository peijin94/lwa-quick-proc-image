#!/bin/bash
# Run LWA solar pipeline in container

podman run --rm -it \
  -v /fast/peijinz/agile_proc/lwa-quick-proc-image:/lwasoft:ro \
  -v /fast/peijinz/agile_proc/testdata_v2:/data:rw \
  -w /data \
  peijin/lwa-solar-pipehost:v202510 \
  python3 /lwasoft/pipeline_quick_proc_img.py \
    /data/slow/20250917_200002_73MHz.ms \
    /data/caltables/20250814_064505_73MHz.bcal \
  > proc.log
