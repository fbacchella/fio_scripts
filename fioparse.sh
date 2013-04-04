#!/bin/bash 

usage()
{
cat << EOF
usage: $0 options

collects I/O related dtrace information into file "ioh.out"
and displays the

OPTIONS:
   -h              Show this message
   -v              verbose, include histograms in output
   -d              include dtrace data in output
   -p              include I/O latency at percents 95%, 99% and 99.99%
   -r              r format (includes histograms and percentiles)
   -R              r format (includes histograms and percentiles) with name
EOF
}

# bit of a hack
# shell script takes command line args
# thise args are then passed into perl at command line args
# the perl looks at each commandline arge and sets a 
# variable with that name = 1
#
AGRUMENTS=""
VERBOSE=0
RPLOTS=0
PERCENTILES=0
PERLPARSER=$(cd $(dirname $0) && pwd -P)/fioparse.pl
while getopts .hp:vr:. OPTION
do
     case $OPTION in
         h)
             usage
             exit 1
             ;;
         v)
             ARGUMENTS="$ARGUMENTS verbose"
             VERBOSE=1
             ;;
         r)
             ARGUMENTS="$ARGUMENTS rplots percentiles"
             RPLOTS=1
             PERCENTILES=1
             TESTNAME=$OPTARG
             ;;
         p)
             ARGUMENTS="$ARGUMENTS percentiles"
             PERCENTILES=1
             ;;
         ?)
             usage
             exit
             ;;
     esac
done
shift $((OPTIND-1))

for i in $*; do
  echo "filename=$i"
  cat $i 
  echo "END"
done | \
perl $PERLPARSER $ARGUMENTS
[ -n "$TESTNAME" ] && printf 'testtype = "%s"\n' "$TESTNAME"

