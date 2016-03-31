fio_scripts
===========

Thses scripts are for facilitating running the I/O benchmark tool
fio, parsing the fio data and graphing the output.
There are a lot of I/O benchmarking tools out there, most noteably
iozone and bonnie++, but fio seems to be the most flexible with
 the most active user community

* fio project: http://freecode.com/projects/fio
* download: http://brick.kernel.dk/snaps/fio-2.0.7.tar.gz
* man page: http://linux.die.net/man/1/fio
* how to: http://www.bluestop.org/fio/HOWTO.txt
* mail list subscription: http://vger.kernel.org/vger-lists.html
* mail list archives : http://www.spinics.net/lists/fio/


files in this project

+ fio.py - run a set of I/O benchmarks using fio
+ fioparse.py - parse the output files from fio.sh runs
+ fiop.r - create a function called graphit() in R
+ fiopg.r - run graphit on different combinations of data from fioparse.py


NOTE: the scripts in this project require that you have already
downloaded fio and compiled a binary of fio.
The scripts also require version 2.0 of fio to work correctly.

Running fio.py
---------------------------
First run fio.py.
The script fio.py will run a series of I/O benchmarks.
The series of I/O benchmarks are aimed at simulating the typical workload
of an Oracle database.
There are 3 types of I/O run

* random small reads
* sequential large reads
* sequential writes

for each of these the number of users is varied and the I/O request size is 
varied.


    Usage: fio.py [options]

    Options:
      -h, --help            show this help message and exit
      -d, --directio        use directio
      -b FIOBINARY, --fiobinary=FIOBINARY
                            name of fio binary, defaults to fio
      -w WORKDIR, --workdir=WORKDIR
                            work directory where fio creates a fio and reads and
                            writes, no default
      -r RAW_DEVICE, --raw_device=RAW_DEVICE
                            use raw device instead of file
      -o OUTPUTDIR, --outputdir=OUTPUTDIR
      -t TESTS, --test=TESTS
                            tests to run, defaults to all, options are
                            randread - IOPS test : 8k by 1, 8, 16, 32, 64 users
                            read  - MB/s test : 1M by 1,8,16,32 users & 8k, 32k,
                            128k, 1024k by 1 user
                            write - redo test, ie sync seq writes : 1k, 4k, 8k,
                            128k, 1024k by 1 user
                            randrw   - workload test: 8k read write by 1,8,16,32,
                            64 users
      -s SECONDS, --seconds=SECONDS
                            seconds to run each test for, default 60
      -m MEGABYTES, --megabytes=MEGABYTES
      -i, --individual      
      -u USERS, --users=USERS
                            test only use this many users
      -l BLOCKSIZES, --blocksize=BLOCKSIZES
                            test only use this blocksize in KB, ie 1-1024
      -R RANDOM_DIRECTIVE, --random=RANDOM_DIRECTIVE
                            Add an random directive (see random_distribution and
                            other directives in fio(1)
      -N RUN_NAME, --run_name=RUN_NAME
                            Give a name to the run
      -E ENGINE, --engine=ENGINE
                            chose engine
      -C ENGINE_CONF, --engine_conf=ENGINE_CONF
                            configure engine, append this definition to [global]
                            section
      -D, --distant         engine is distant (hdfs, ceph)
      -B, --graph_block     with non default run, keep users, change block size in
                            graph
      -U, --graph_users     with non default run, keep block size, change users in
                            graph
      --fadvise             activate fadvise hint
                          
           example
                      fio.py -b /usr/local/bin/fio -w /domain0/fiotest  -t randread -s 10 -m 1000

Running fioparse.py
---------------------------
Once the benchmarks have been run, fio.py uses fioparse.py to extract a consise
set of statistics from the output files that will be imported in R.

Graphing in R
-----------------------------------------


R will run through a series of different combinations graphing them and saving the output.
The output is save to png files in the directory specified with 'dir'

GRAPH Examples:	

https://sites.google.com/site/oraclemonitor/i-o-graphics#TOC-Percentile-Latency

Each PNG file will have 3 graphs

1. latency on a log scale
2. throughout MB/s

1: the log scale latency has several parts
-------------------------------------------

Four lines:

1. max latency - dashed red line
2. 99% latency - top of light grey shaded area
3. 95% latency - top of dark grey shaded area
4. avg latency   - black line

Plus:

+ back ground is barchaerts, 0 percent at bottom to 100% at top

        light blue % of I/Os below 1ms - probably some sort of cache read
        green % of I/Os below 10ms
        yellow % of I/Os over 10ms

+  histograms of latency buckets 

	at each user load level, color coded. Each bugkets height (horizontal) is % of I/Os in that bucket
	like a fine grain breakdown of the background
   

2. the throughput bar chart, shows MB/s
-------------------------------------------

    the bars are color code with amount percentage of throughput that had a latency of that color where colors
    are in the right hand axis legend in top graph the latency on log scale

see: 

https://sites.google.com/site/oraclemonitor/i-o-graphics#TOC-percentile-latency-with-scaling


New Graphics
-----------------------------------------------------
a new version of the function graphit() is created by
fiop.r and fiopg.r will go through a set of I/O data
and print out variouis graphs of the data.

Examples of the graphs are on

https://plus.google.com/photos/105986002174480058008/albums/5773655476406055489?authkey=CIvKiJnA2eXSbQ

A visual explanation is here

https://plus.google.com/photos/105986002174480058008/albums/5773661884246310993

A Summary of the graph contents is:

The charts are mainly for exploring the data as opposed to a polished final graph showing I/O performance

A quick recap of the graphics:
There are 3 graphs

1.  latency on log graph
2. latency on base 10 graph
3. throughput bar charts

On the log latency graph latency is shown for

* max latency - dashed red line
* average latency - solid black line
* 95% latency - dash black line with grey fill between 95% and average
* 99% latency - dash black line with light grey fill between 95% and 99% latency
* latency histogram - buckets represent % of I/Os for that latency.Each bucket is drawn at the y axis height that represents that latency. The buckets are also color coded to help more quickly identify
* background color - for each load test the background is coded one of 3 colors. 
* ... yellow - % of I/Os over 10ms
* ... green - % of I/Os under 10ms
* ... blue - % of I/Os under 1ms

the idea being that  the graphs should have all green. If the backgrounds are yellow then the I/Os are slow. If the backgrounds are blue then the I/Os represent a certain about of cached reads as opposed to physical spindle reads. 


The second graph is latency on base 10 in order to more easily see the slopes of the increasing I/O latency with load.
On this second graph is also a bar chart in the background. The bars are color coded

* dark red - latency increased and throughput decreases
* light red - latency increased but throughput also increased
* light blue - latency actually got faster (shouldn't happen but does)

Ideally the bars are so small they aren't visible which means latency stays the same as load increases. The higher the bar the more the latency changed between tests

The third chart is simply the throughput, ie the MB/s. These bars have slices that represent the percentage of the I/O at the latency that corresponds to that color. The colors are defined in the legend of the top chart.

.
