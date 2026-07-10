python ../scripts/ZYMalign.py \
    --QUERY data/sRO10_AF.cif \
    --HOMOLOGY_SEARCH_METHOD "foldseek" \
    --RESULT_DIR output_foldseek_homologs \
    --FOLDSEEK_DATABASES afdb50 \
    --FOLDSEEK_MODE 3diaa \
    --NUMB_HOMOLOGS 10 \