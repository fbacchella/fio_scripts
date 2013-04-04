
$ouputrows=0;
$DEBUG=0;
$CLAT=0;

if ( 1 == $DEBUG ) { $debug=1; }

foreach $argnum (0 .. $#ARGV) {
    ${$ARGV[$argnum]}=1;
}
print "continuting ... \n" if defined ($debug);
if(defined ($rplots) && $rplots == 1) {
    $verbose = 1;
    $percentiles = 1;
}


# these are all the possible buckets for dtrace
@buckets_dtrace=("1", "2", "4", "8", "16", "32", "64", "128", "256", "512", "1024", "2048", "4096", "8192", "16384", "32768", "65536", "131072", "262144", "524288", "1048576", "2097152", "4194304", "8388608", "16777216", "33554432");

# these are all the possible buckets for fio histograms:
@buckets_fio=("4","10","20","50","100","250","500","750","1000","2000","4000","10000","20000","50000","100000","250000","500000","750000","1000000","2000000","20000000");

# translation of fio buckets into labels
$buckett{4}="4us";
$buckett{10}="10us";
$buckett{20}="20us";
$buckett{50}="50us";
$buckett{100}=".1ms";
$buckett{250}=".25ms";
$buckett{500}=".5ms";
$buckett{750}=".75ms";
$buckett{1000}="1ms";
$buckett{2000}="2ms";
$buckett{4000}="4ms";
$buckett{10000}="10ms";
$buckett{20000}="20ms";
$buckett{50000}="50ms";
$buckett{100000}=".1s";
$buckett{250000}=".25ms";
$buckett{500000}=".5s";
$buckett{750000}=".75s";
$buckett{1000000}="1s";
$buckett{2000000}="2s";
$buckett{20000000}="2s+";

$bucketr{4}="us4";
$bucketr{10}="us10";
$bucketr{20}="us20";
$bucketr{50}="us50";
$bucketr{100}="us100";
$bucketr{250}="us250";
$bucketr{500}="us500";
$bucketr{750}="us750";
$bucketr{1000}="ms1";
$bucketr{2000}="ms2";
$bucketr{4000}="ms4";
$bucketr{10000}="ms10";
$bucketr{20000}="ms20";
$bucketr{50000}="ms50";
$bucketr{100000}="ms100";
$bucketr{250000}="ms250";
$bucketr{500000}="ms500";
$bucketr{750000}="ms750";
$bucketr{1000000}="s1";
$bucketr{2000000}="s2";
$bucketr{20000000}="s2g";

@output_buckets=("50","1000","4000","10000","20000","50000","100000","1000000","2000000","20000000");
@rbuckets_fio=("4","100","250","500","1000","2000","4000","10000","20000","50000","100000","250000","500000","1000000","2000000","20000000");
@percentiles_header=("95%", "99%", "99.5%", "99.9%", "99.95%", "99.99%");

sub hist_head {
    printf("%8s", "test");
    printf("%6s", "users");
    printf("%5s", "size");
    printf(" %-1.1s", " ");
    printf("%9s",  "MB    ");
    printf("%9s", "lat    ");
    printf("%9s", "min    ");
    printf("%9s", "max    ");
    printf("%9s", "std    ");
    printf("%8s", "IO/s");
    if($verbose == 1) {
        foreach my $time (@output_buckets) {
            if ( $time > $higbucket ) {
                printf(" %5s",$buckett{$time});
            }
        }
    }
    if($percentiles == 1) {
        foreach my $percentile (@percentiles_header) {
            printf(" %8s",$percentile);
        }
    }
    printf("\n");
}

sub print_hist {
    $mybucket=0;

    # for all possible fo buckets, @buckets_fio is all known fio histogram buckets
    if ( $rplot_hist == 1 ) {
        foreach $curbucket (@rbuckets_fio) {
            $label="";
            if ($curbucket eq "4" ) {
                if ( $labels == 1 ) {
                    $label="us50=";
                }
                printf(",%s%2d",$label, int(${$hist_type}{$curbucket} + ${$hist_type}{"10"} + ${$hist_type}{"20"} + ${$hist_type}{"50"})||0 );
                delete ${$hist_type}{"10"};
                delete ${$hist_type}{"20"};
                delete ${$hist_type}{"50"};
            }
            elsif ( $curbucket eq "1000" ) {
                if ( $labels == 1 ) {
                    $label=$bucketr{$curbucket}."=";
                }
                printf(",%s%2d",$label, (${$hist_type}{$curbucket} + ${$hist_type}{"750"})||0 );
                delete ${$hist_type}{"750"};
            }
            elsif ( $curbucket eq "1000000" ) {
                if ( $labels == 1 ) { $label=$bucketr{$curbucket}."="; }
                printf(",%s%2d",$label, int(${$hist_type}{$curbucket}+ ${$hist_type}{"750000"})||0 );
                delete ${$hist_type}{"750000"};
                # the "20000000" bucket is just a tag for > 2s, so lets call it 5s for graphing purposes
            }
            elsif ( $curbucket eq "20000000" ) {
                if ( $labels == 1 ) { $label="s5="; }
                printf(",%s%2d",$label, int(${$hist_type}{$curbucket})||0 );
            }
            else {
                if ( $labels == 1 ) { $label=$bucketr{$curbucket}."="; }
                printf(",%s%2d",$label, int(${$hist_type}{$curbucket})||0 );
            }
            delete ${$hist_type}{$curbucket};
        }
    }
    else {
        foreach $curbucket (@{$bucket_list}) {
            # printf("curbucket %s >=? %s \n",$curbucket, $output_buckets[$mybucket] );
            # output_buckets => the list of buckets to actually output
            # bucket_list => buckets possible for this data (fio or dtrace)
            # curbucket => is this bucket less the bucket to output? if so add it to
            # if the current bucket from curbucket is smaller then our the planed output bucket
            # but larger than the last output bucket, then summ it up
            # ie if the first output bucket at 1ms, sum up all buckets from 4us to 1ms
            # if the next output bucket is 1s, them sum up all bucets from 1ms+ to 1s
            if ( $curbucket <= $output_buckets[$mybucket] ) {
                # bucket values from fio are in $lat[key]
                # bucket values from dtrace are in $dtrace_lat[key]
                $bucketu{$output_buckets[$mybucket]}+=${$hist_type}{$curbucket};
            }
            else {
                $bucketu{$output_buckets[$mybucket+1]}+=${$hist_type}{$curbucket};
            }
            delete ${$hist_type}{$curbucket};
            # if we reach our output bucket time, then go to the next bucket in all buckets
            if ( $curbucket >= $output_buckets[$mybucket] ) {
                $mybucket++;
            }
        }
        # now that weve summed up the fine grain buckets in all buckets into
        # the desired courser grain buckets, print out the course grain bucket values
        foreach $tu (@output_buckets) {
            if ( $bucketu{$tu} > 0 ) {
                printf(" %5s",int( 100*($bucketu{$tu}/$iop) ) );
            }
            else {
                if ( $rplot_hist == 1 ) {
                    printf(",%s=%2d",$bucketr{$tu},0 );
                }
                else {
                    printf(" %5s","");
                }
            }
            $bucketu{$tu}=0;
        }
    }
}

$| = 1;

while (my $line = <STDIN>) {
    chomp($line);
    printf("line: %s\n", $line) if defined ($debug);
    #job: (g=0): rw=randread, bs=8K-8K/8K-8K, ioengine=psync, iodepth=2
    if ( $line =~ m/filename/ ) {
        $dir=$line;
        $dir =~ s/filename=//;
        $dir =~ s/\/.*//;
    }
    if ( $line =~ m/ioengine/ ) {
        $bs=$benchmark=$line;
        $benchmark =~ s/.* rw=//;
        $benchmark =~ s/,.*//;
        $bs =~ s/.* bs=//;
        $bs =~ s/-.*//;
        next;
    }
    # READ: io=48216KB, aggrb=802KB/s, minb=822KB/s, maxb=822KB/s, mint=60052msec, maxt=60052msec
    # WRITE: io=12256KB, aggrb=204KB/s, minb=208KB/s, maxb=208KB/s, mint=60052msec, maxt=60052msec
    if ( $line =~ m/aggrb/ ) {
        $type=$throughput=$line;
        $type =~ s/:.*//;
        $type =~ s/[ ][ ]*//;
        # lower case:
        $type = lc( $type);
        $throughput =~ s/.*aggrb=//;
        $throughput =~ s/,.*//;
        printf("throughput:%s:\n",$throughput) if defined ($debug);
        $factor = $throughput;
        $factor =~ s/.*MB.s/1048576/;
        $factor =~ s/.*KB.s/1024/;
        $factor =~ s/.*B.s/1/;
        $throughput =~ s/MB.s//;
        $throughput =~ s/KB.s//;
        $throughput =~ s/B.s//;
        printf("throughput:%s: factor:%s:\n",$throughput,$factor) if defined ($debug);
        $throughput{$type}=$throughput*$factor;
        next;
    }
    # read : io=48216KB, bw=822173 B/s, iops=100 , runt= 60052msec
    # get iops and set type for later usage
    if ( $line =~ m/ bw=/ ) {
        $type=$iops =$line;
        $type =~ s/[ ]*:.*//;
        $type =~ s/[ ]*//;
        $iops =~ s/.*iops=//;
        $iops =~ s/ .*//;
        $iops{$type}=$iops;
        next;
    }
    # lat (usec): min=7 , max=1305.5K, avg=61053.50, stdev=73135.80
    if ( $line =~ m/ stdev=/ ) { # filter out histogram lines that have "lat"
        if ( $line =~ m/ lat/ ) { # filter out clat lines
            $lat=$unit=$latmin=$latmax=$latstd=$line;
            $lat =~ s/.*avg=//;
            $lat =~ s/,.*//;
            $latmin =~ s/.*min=//;
            $latmin =~ s/ *,.*//;
            $latmax =~ s/.*max=//;
            $latmax =~ s/ *,.*//;
            $latstd =~ s/.*stdev=//;
            $latstd =~ s/ *//;

            $unit =~ s/.*\(//;
            $unit =~ s/\).*//;
            $unit =~ s/msec/1000/;
            $unit =~ s/usec/1/;

            foreach $var ( "latmin" , "latmax" , "laststd" ) {
                if ( ${$var} =~ m/K/ ) {
                    ${$var} =~ s/K//;
                    ${$var} = ${$var} *1000;
                }
            }

            $latmin{$type}=$latmin*$unit;
            $latmax{$type}=$latmax*$unit;
            $latstd{$type}=$latstd*$unit;

            $lat{$type}=$lat*$unit;
            $unit{$type}=$unit;
            next;
        }
    }
    # #job: (g=0): rw=randread, bs=8K-8K/8K-8K, ioengine=psync, iodepth=2
    if ( $line =~ m/ioengine/ ) {
        $bs=$line;
        $bs =~ s/.* bs=//;
        $bs =~ s/-.*//;
        next;
    }
    #Starting 1 process
    if ( $line =~ m/Starting/ ) {
        $users=$line;
        $users =~ s/Starting //;
        $users =~ s/ process.*//;
        next;
    }
    # lat (usec): 4=97.56%, 10=1.10%, 20=0.09%, 50=0.03%, 100=0.01%
    # lat (usec): 250=0.01%, 500=0.01%, 750=0.01%
    # lat (msec): 4=0.01%, 10=0.50%, 20=0.64%, 50=0.04%, 100=0.01%
    # lat (msec): 250=0.01%
    # lat (msec): 4=6.20%, 10=15.29%, 20=42.56%, 50=30.58%, 100=2.89%
    # lat (msec): 250=0.41%, 750=0.41%, 1000=0.83%, 2000=0.41%, >=2000=0.41%

    # 2 4 10 20 50 100 250 500 750 1000 2000 4000 10000 20000 50000
    # 100000 250000 500000 750000 1000000 2000000 2000000+
    if ( $line =~ m/ lat / ) {
        if ( $line =~ m/%/ ) {
            $units=$lats=$line;
            $units =~ s/.*\(//;
            $units =~ s/\).*//;
            $units =~ s/msec/1000/;
            $units =~ s/usec/1/;
            $lats =~ s/.*://;
            $lats =~ s/%//g;
            $lats =~ s/>=/Z/g;
            @lats = split(",", $lats);
            foreach $lat (@lats) {
                ($key,$val) = split("=", $lat);
                if ( $key =~ m/Z/ ) {
                    $key=20000000;
                    $extra="+";
                }
                else {
                    $key=$key*$units;
                    $extra="";
                }
                $lat{$key}=$val;
            }
        }
    }

    # clat percentiles (usec):
    # | 1.00th=[ 179], 5.00th=[ 185], 10.00th=[ 191], 20.00th=[ 195],
    # | 30.00th=[ 199], 40.00th=[ 201], 50.00th=[ 203], 60.00th=[ 207],
    # | 70.00th=[ 215], 80.00th=[ 219], 90.00th=[ 229], 95.00th=[ 266],
    # | 99.00th=[ 398], 99.50th=[ 474], 99.90th=[ 532], 99.95th=[ 796],
    # | 99.99th=[ 1352]
    # bw (KB/s) : min=33040, max=38352, per=100.00%, avg=36799.16, stdev=1312.23

    if ( $CLAT == 1 ) {
        if ( $line =~ m/\|/ ) {
             if ( $line =~ m/95.00th/ ) {
                $clat95_00 = $line;
                $clat95_00 =~ s/.*95.00th=\[//;
                $clat95_00 =~ s/\],.*//;
                $clat95_00 =~ s/ //g;
            }
            if ( $line =~ m/99.00th/ ) {
                $line =~ s/99\...th.*?=\[//g;
                $line =~ s/\|//g;
                $line =~ s/\]//g;
                $line =~ s/ //g;
                ($clat99_00, $clat99_50, $clat99_90, , $clat99_95 )=split(",",$line);
            }
            if ( $line =~ m/99.99th/ ) {
                $clat99_99 = $line;
                $clat99_99 =~ s/.*99.99th=\[//;
                $clat99_99 =~ s/\].*//;
                $clat99_99 =~ s/ //g;
            }
        }
        else {
            $CLAT = 0;
        }
    }
    if ( $line =~ m/clat percentiles / ) {
        $CLAT=1 ;
        # clat percentiles (usec):
        $clat_unit=$line ;
        $clat_unit =~ s/.*\(//;
        $clat_unit =~ s/\).*//;
        if ( $clat_unit eq "usec" ) {
            $clat_mult = .001 ;
        }
        elsif ( $clat_unit eq "msec" ) {
            $clat_mult = 1;
        }
        elsif ( $clat_unit eq "sec" ) {
            $clat_mult = 1000;
        }
        else {
            printf("clat unit :%s: unknown\n",$clat_unit);
            printf("exiting \n");
            exit;
        }
    }

    # important for the follwoing dtrace lines, get rid of spaces and tabs
    $line=~ s/[ ][ ]/,/;
    $line =~ s/[ ][ ]*//g;

    if ( $line =~ m/dtrace_secs/ ) {
        ($type, $value)=split(",",$line);
        $dtrace_secs=$value;
    }
    if ( $line =~ m/dtrace_avgsize/ ) {
        ($dtrace_io_type,$type, $value)=split(",",$line);
        $dtrace_avgsize{$dtrace_io_type}=$value;
    }
    if ( $line =~ m/dtrace_bytes/ ) {
        ($dtrace_io_type,$type, $value)=split(",",$line);
        $dtrace_bytes{$dtrace_io_type}=$value;
    }
    if ( $line =~ m/dtrace_avglat/ ) {
        ($dtrace_io_type,$type, $value)=split(",",$line);
        $value =~ s/[ ][ ]*//g;
        $value =~ s/ *//g;
        $dtrace_avglat{$dtrace_io_type}=$value;
    }
    if ( $line =~ m/dtrace_iop/ ) {
        ($dtrace_io_type,$type, $value)=split(",",$line);
        $dtrace_iop{$dtrace_io_type}=$value;
    }

    if ( $line =~ m/dtrace_size_start/ ) { $dtrace_size=1; }
    if ( $line =~ m/size_distribution/ ) { ($dtrace_io_type, $value)=split(",",$line);}
    if ( $line =~ m/dtrace_size_end/ ) { $dtrace_size=0; }

    if ( $line =~ m/dtrace_latency_start/ ) { $dtrace_latency=1; }
    if ( $line =~ m/latency_distribution/ ) { ($dtrace_io_type, $value)=split(",",$line);}
    if ( $line =~ m/dtrace_latency_end/ ) { $dtrace_latency=0; }

    if ( $line =~ m/\|/ ) {
        $line=~ s/\|@*/,/;
        $line =~ s/ *//g;
        if ( $dtrace_size == 1 ) {
            ($bucket, $value)=split(",",$line);
            $size{$dtrace_io_type,$bucket}=$val;
        }
        # 128, 0
        # 256 , 1
        # 512 , 23
        # 1024 ,8
        # 2048 ,2
        if ( $dtrace_latency == 1 ) {
            ($bucket, $value)=split(",",$line);
            if ( $dtrace_io_type eq "W" ) {
                $dtrace_lat_w{$bucket}=$value;
                if ( $bucket > $max_dtrace_w_bucket ) { $max_dtrace_w_bucket = $bucket }
            }
            if ( $dtrace_io_type eq "R" ) {
                $dtrace_lat_r{$bucket}=$value;
                if ( $bucket > $max_dtrace_r_bucket ) { $max_dtrace_r_bucket = $bucket }
            }
        }
    }
}

if ( $rplots == 0 ) {
    hist_head;
    printf("%8s", $benchmark);
    printf("%6s", $users);
    printf("%5s", $bs);
    if ( $benchmark eq "write" ) {
        $type="write" ;
        $dtype="W" ;
    }
    else {
        $type="read" ;
        $dtype="R" ;
    }
    if ( $iops{$type} > 0 ) {
        printf(" %-1.1s", $type);
        printf("%9.3f", $throughput{$type}/1048576);
        printf("%9.3f", $lat{$type}/1000);

        printf("%9.3f", $latmin{$type}/1000);
        printf("%9.3f", $latmax{$type}/1000);
        printf("%9.3f", $latstd{$type}/1000);

        printf("%8s", $iops{$type});
    }
    else {
        printf("%27s ", "");
    }
    if ( $verbose == 1 ) {
        $iop=100;
        $hist_type="lat";
        $bucket_list= "buckets_fio";
        print_hist;
    }

    if ( $percentiles == 1 ) {
        foreach $percent ( $clat95_00, $clat99_00 ,$clat99_50 ,$clat99_90 ,$clat99_95 ,$clat99_99 ) {
            printf(" %8.3f",$percent*$clat_mult);
        }
    }

    printf("\n");

    $users="";
    $benchmark="";
    foreach $type ( keys %iops ) {
        delete $throughput{$type};
        delete $lat{$type};
        delete $iops{$type};
    }
    $type="";
    $benchmark="";
    $users="";
    $bs="";
    $dtrace_avgsize="";
    $dtrace_bytes="";
    $dtrace_secs="";
    $dtrace_avglat="";

}
elsif( $rplots == 1 ) {
    if ($users > 0 ) {
        if ( $benchmark eq "write" ) {
            $type="write" ;
            $dtype="W" ;
        }
        else {
            $type="read" ;
            $dtype="R" ;
        }
        if ( $outputrows > 0 ) {
            if ( $labels == 1 ) {
                printf("m <- rbind(m,data.frame(");
            }
            else {
                printf(",");
            }
        }
        else {
            printf("m <- NULL \n");
            if ( $labels == 1 ) {
                printf("m <- data.frame(");
            }
            else {
                printf("m <- matrix(c(\n");
            }
        }
        $label="";
        if ( $labels == 1 ) { $label="name=";}
        printf("%s%10s,", $label, "\"" . $benchmark . "\"") ;
        if ( $labels == 1 ) { $label="users=";}
        printf("%s%3s,", $label, $users);
        if ( $labels == 1 ) { $label="bs=";}
        printf("%s%6s,", $label, "\"" . $bs . "\"") ;
        if ( $labels == 1 ) { $label="MB=";}
        printf("%s%8.3f,", $label, $throughput{$type}/1048576);
        if ( $labels == 1 ) { $label="lat=";}
        printf("%s%9.3f,", $label, $lat{$type}/1000);
        if ( $labels == 1 ) { $label="min=";}
        printf("%s%4.1f,", $label, $latmin{$type}/1000);
        if ( $labels == 1 ) { $label="max=";}
        printf("%s%9d,", $label, $latmax{$type}/1000);
        if ( $labels == 1 ) { $label="std=";}
        printf("%s%7.1f,", $label, $latstd{$type}/1000);
        if ( $labels == 1 ) { $label="iops=";}
        printf("%s%5s", $label, $iops{$type});
        $iop=100;
        $hist_type="lat";
        $bucket_list= "buckets_fio";
        $rplot_hist = 1;
        print_hist;
        $rplot_hist = 0;
        foreach $percent ( $clat95_00, $clat99_00 ,$clat99_50 ,$clat99_90 ,$clat99_95 ,$clat99_99 ) {
            printf(",%5.3f",$percent*$clat_mult);
        }
        if ( $outputrows > 0 && $labels == 1 ) { printf(")"); }
        if ( $lables == 1 ) { printf(")"); }
        printf("\n");
        $outputrows++;

    }
    if ( $lables != 1 ) {
        if ( $percentiles == 1 ) {
            printf("),nrow=31)\n");
        }
        else {
            printf("),nrow=25)\n");
        }
        printf("tm <- t(m)\n");
        printf("m <-tm\n");
        printf("colnames <- c(\"name\",\"users\",\"bs\",\"MB\",\"lat\",\"min\",\"max\",\"std\",\"iops\"\n");
        printf(", \"us50\",\"us100\",\"us250\",\"us500\",\"ms1\",\"ms2\",\"ms4\",\"ms10\",\"ms20\"\n");
        printf(", \"ms50\",\"ms100\",\"ms250\",\"ms500\",\"s1\",\"s2\",\"s5\"\n");
        if ( $percentiles == 1 ) {
            printf(",\"p95_00\", \"p99_00\", \"p99_50\", \"p99_90\", \"p99_95\", \"p99_99\"\n");
        }
        printf(")\n");
        printf("colnames(m)=colnames\n");
        printf("m <- data.frame(m)\n");
        printf("testtype <- \"%s\"\n",$ENV{'TESTNAME'});
    }
}

printf("at end\n") if defined ($debug);
