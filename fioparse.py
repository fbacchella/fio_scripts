#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import sys
import csv
import re
import os
import collections

csv_lines = ""
csv_re = re.compile('^\d+;fio-[\d\.]+;')
for f in sys.argv:
    prefix = os.path.basename(f)
    with open(f, "r") as outfile:
        for line in outfile:
            if csv_re.match(line) is not None:
                csv_lines += "%s;%s" % (prefix, line)

# The fio run output is cleaned to be parsable by a csv.reader
csv_values = []

quote_string_re = re.compile(r'(^|;)([^;"\n]*[A-Za-z=][^;"\n]*)(;|$)')
terse_line_re = re.compile(r'^([a-z_0-9]+\.out;(\d+);fio-[^;]*;?.*$)', re.MULTILINE)

for found in terse_line_re.findall(csv_lines):
    if found[1] == "3":
        line = found[0].replace("%", "")
        # a while because quote_string regex will not manage two consecutive string
        while True:
            # wrapping all textual values with a ".."
            (line, count) = quote_string_re.subn(r'\1"\2"\3', line)
            if count == 0:
                break
        csv_values.append(line)

csv_columns = ["filename", "version", "fiover", "jobname", "groupid", "error"]
# read columns
csv_columns += ["r_total", "r_bw", "r_IOPS", "r_runt", "r_slat_min", "r_slat_max", "r_slat_mean", "r_slat_std",
                "r_clat_min", "r_clat_max", "r_clat_mean", "r_clat_std"]
for i in range(1, 21):
    csv_columns += ["r_clat_perc_%d" % i]
csv_columns += ["r_tlat_min", "r_tlat_max", "r_tlat_mean", "r_tlat_std"]
csv_columns += ["r_bw_min", "r_bw_max", "r_bw_agg_perc", "r_bw_mean", "r_bw_std"]

# write columns
csv_columns += ["w_total", "w_bw", "w_IOPS", "w_runt", "w_slat_min", "w_slat_max", "w_slat_mean", "w_slat_std",
                "w_clat_min", "w_clat_max", "w_clat_mean", "w_clat_std"]
for i in range(1, 21):
    csv_columns += ["w_clat_perc_%d" % i]
csv_columns += ["w_tlat_min", "w_tlat_max", "w_tlat_mean", "w_tlat_std"]
csv_columns += ["w_bw_min", "w_bw_max", "w_bw_agg_perc", "w_bw_mean", "w_bw_std"]

#cpu and memory usages columns
csv_columns += ["cpu_user", "cpu_system", "cpu_ctx", "mem_maj", "mem_min"]

#IO depth
csv_columns += ["io_1", "io_2", "io_4", "io_8", "io_16", "io_32", "io_64"]

#IO latency distribution
latency_buckets = ("2", "4", "10", "20", "50", "100", "250", "500", "750", "1000", "2000", "4000", "10000", "20000",
                   "50000", "100000", "250000", "500000", "750000", "1000000", "2000000", "20000000")
for latency in latency_buckets:
    csv_columns += ["lat_dist_%s" % latency]

cvsinput = csv.DictReader(csv_values, fieldnames=csv_columns, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)

latency_reducer = collections.OrderedDict()
latency_reducer['us50'] = (2, 4, 10, 20, 50)
latency_reducer['us100'] = (100,)
latency_reducer['us250'] = (250,)
latency_reducer['us500'] = (500,)
latency_reducer['ms1'] = (750, 1000)
latency_reducer['ms2'] = (2000,)
latency_reducer['ms4'] = (4000,)
latency_reducer['ms10'] = (10000,)
latency_reducer['ms20'] = (20000,)
latency_reducer['ms50'] = (50000,)
latency_reducer['ms100'] = (100000,)
latency_reducer['ms250'] = (250000,)
latency_reducer['ms500'] = (500000,)
latency_reducer['s1'] = (750000, 1000000)
latency_reducer['s2'] = (2000000,)
latency_reducer['s5'] = (20000000,)

print("""m <- NULL 
m <- matrix(c(""")

filename_re = re.compile(r'([a-z]+)_u(\d+)_kb(\d+).out')

prefix = "  "

for row in cvsinput:
    colnames = []

    #extract job details from filename
    m = filename_re.match(row["filename"])
    if m is None:
        continue
    test = m.group(1)
    users = int(m.group(2))
    bs = int(m.group(3))
    line = '%s"%s", %d, "%dK", ' % (prefix, test, users, bs)
    print(line, end=' ')
    colnames += ["name", "users", "bs"]
    
    print("%.3f," % (row["r_bw"] / 1024), end=' ')
    print("%.3f," % (row["w_bw"] / 1024), end=' ')
    colnames += ["MB_r", "MB_w"]

    print("% 8.3f, % 8.1f, % 8.0f, % 8.1f," % (row["r_clat_mean"] / 1000,
                                               row["r_clat_min"] / 1000,
                                               row["r_clat_max"] / 1000,
                                               row["r_clat_std"] / 1000), end=' ')
    colnames += ["r_lat", "r_min", "r_max", "r_std"]

    print("% 8.3f, % 8.1f, % 8.0f, % 8.1f," % (row["w_clat_mean"] / 1000,
                                               row["w_clat_min"] / 1000,
                                               row["w_clat_max"] / 1000,
                                               row["w_clat_std"] / 1000), end=' ')
    colnames += ["w_lat", "w_min", "w_max", "w_std"]

    print("%d, " % (row['r_IOPS'] + row['w_IOPS']), end=' ')
    colnames += ["iops"]

    # join latency buckets
    sum_val = 0
    for (reduced_bucket, source_buckets) in latency_reducer.items():
        val = 0
        for source_bucket in source_buckets:
            val += row["lat_dist_%s" % source_bucket]
        row['lat_dist_reduced_%s' % reduced_bucket] = val
        sum_val += val

    for reduced_bucket inlatency_reducer.keys():
        print("%.0f, " % (row['lat_dist_reduced_%s' % reduced_bucket]), end=' ')
        colnames += [reduced_bucket]
        
    #Resolve read percentiles columns to read percentiles bucket
    for i in range(1, 21):
        val = row['r_clat_perc_%.d' % i]
        (percentile, latency) = val.split("=")
        percentile = float(percentile)
        latency = float(latency)
        row['r_clat_perc_bucket_%.2f' % percentile] = latency / 1000
    print("%.3f, %.3f, %.3f, %.3f, %.3f, %.3f," % (row['r_clat_perc_bucket_95.00'],
                                                   row['r_clat_perc_bucket_99.00'],
                                                   row['r_clat_perc_bucket_99.50'],
                                                   row['r_clat_perc_bucket_99.90'],
                                                   row['r_clat_perc_bucket_99.95'],
                                                   row['r_clat_perc_bucket_99.99']), end=' ')
    colnames += ["r_p95_00", "r_p99_00", "r_p99_50", "r_p99_90", "r_p99_95", "r_p99_99"]

    #Resolve write percentiles columns to write percentiles bucket
    for i in range(1, 21):
        val = row['w_clat_perc_%.d' % i]
        (percentile, latency) = val.split("=")
        percentile = float(percentile)
        latency = float(latency)
        row['w_clat_perc_bucket_%.2f' % percentile] = latency / 1000
    print("%.3f, %.3f, %.3f, %.3f, %.3f, %.3f" % (row['w_clat_perc_bucket_95.00'],
                                                  row['w_clat_perc_bucket_99.00'],
                                                  row['w_clat_perc_bucket_99.50'],
                                                  row['w_clat_perc_bucket_99.90'],
                                                  row['w_clat_perc_bucket_99.95'],
                                                  row['w_clat_perc_bucket_99.99']), end=' ')
    colnames += ["w_p95_00", "w_p99_00", "w_p99_50", "w_p99_90", "w_p99_95", "w_p99_99"]

    print()
    prefix = ", "

print("""),nrow=%d)
tm <- t(m)
m <-tm
colnames <- c(""" % len(colnames))
print('"%s"' % '", "' .join(colnames))
print(""")
colnames(m)=colnames
m <- data.frame(m)
""")
