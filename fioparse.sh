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
DTRACE=0
RPLOTS=0
PERCENTILES=0
while getopts .dhpR:vr. OPTION
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
         d)
             ARGUMENTS="$ARGUMENTS dtrace"
             DTRACE=1
             ;;
         R)
             ARGUMENTS="$ARGUMENTS rplots percentiles"
             RPLOTS=1
             PERCENTILES=1
             export TESTNAME=$OPTARG
             ;;
         r)
             ARGUMENTS="$ARGUMENTS rplots percentiles"
             RPLOTS=1
             PERCENTILES=1
             echo "please enter a test  name:"
             read TESTNAME
             export TESTNAME=${TESTNAME:-"noname"}
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

# print header line

if [ $RPLOTS -eq 0 ] ; then
  echo -n "test  users size         MB       ms      min      max      std    IOPS"
  if [ $VERBOSE -eq 1 ] ; then
    echo  -n "    50us   1ms   4ms  10ms  20ms  50ms   .1s    1s    2s   2s+"
  fi
  if [ $PERCENTILES -eq 1 ] ; then
    echo  -n "       95%      99%    99.5%    99.9%  99.95%    99.99%"
  fi
  echo " "
fi



for i in $*; do
  echo "filename=$i"
  cat $i 
  echo "END"
done | \
perl fioparse.pl $ARGUMENTS
