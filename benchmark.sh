# python -m bench.benchmark --dir bench/sample_data --candidate marker --force
# python -m bench.benchmark --dir bench/sample_data --candidate olmocr_pipeline --force



# python -m bench.benchmark --dir bench/orbit_data --candidate marker --force 

# for some Chinese/Japanese/Korean PDFs, skip the baseline
python -m bench.benchmark --dir bench/orbit_data --candidate marker --force --skip_baseline 