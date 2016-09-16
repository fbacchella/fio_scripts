#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
from optparse import OptionParser
import subprocess
import os
from distutils import spawn
import signal
import platform
import copy
import time
import cStringIO


def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


# A empty exception class
# used to catch managed exception and errors
class FioException(Exception):
    pass


class ProcessException(FioException):
    def __init__(self, command, argv, status, stdout, stderr):
        self.command = command
        self.argv = argv
        self.status = status
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        str_out = ""
        if self.stdout is not None:
            str_out = "stdout:\n"
            for l in cStringIO.StringIO(self.stdout):
                str_out += "**** %s" % l
        str_err = ""
        if self.stderr is not None:
            str_err = "stderr:\n"
            for l in cStringIO.StringIO(self.stderr):
                str_err += "**** %s" % l
        output = """command %s failed
    %s
%s
%s""" % (self.command, " ".join(self.argv), str_out, str_err)
        return output


class Executor(object):
    default = {'stdin': None, 'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE, 'shell': False, 'close_fds': True}
    debug = False

    @staticmethod
    def signal_handler(signum, frame):
        Executor.terminate_child()

    @staticmethod
    def terminate_child():
        if hasattr(Executor, 'process') and Executor.process is not None:
            Executor.process.terminate()
            polled = 0
            while Executor.process.poll() is None and polled < 5:
                time.sleep(0.1)
                polled += 1
            if Executor.process.poll() is None:
                Executor.process.kill()

    @staticmethod
    def check_executable(filename):
        if filename is None:
            raise FioException("no command given")
        filename_path = spawn.find_executable(filename)
        if filename_path is not None:
            try:
                if not os.access(filename_path, os.X_OK):
                    raise FioException("no executable command '%s'" % filename_path)
            except OSError as ex:
                raise FioException("no valid command path '%s': '%s'" % (filename_path, ex))
        else:
            raise FioException("command '%s' not found in path" % filename)
        return filename_path

    def __init__(self, argv, debug=None, follow_stdout=False, forget=False, **kwargs):
        realbinary = Executor.check_executable(argv[0])
        self.argv = [realbinary] + argv[1:]
        self.status = None
        self.forget = forget
        self.kwargs = dict(list(Executor.default.items()) + list(kwargs.items()))
        self.stdoutdata = None
        self.stderrdata = None
        if follow_stdout:
            self.kwargs['stdout'] = None
        if debug is None:
            debug = Executor.debug
        if debug:
            print "'%s'" % "' '".join(self.argv)

    def run(self, input=None):
        if not self.forget:
            previous_handler = signal.signal(signal.SIGTERM, Executor.signal_handler)
        Executor.process = subprocess.Popen(self.argv, **self.kwargs)
        sys.stdout.flush()
        (self.stdoutdata, self.stderrdata) = Executor.process.communicate(input)
        self.status = Executor.process.wait()
        if not self.forget:
            signal.signal(signal.SIGTERM, previous_handler)
        Executor.process = None
        return self

    def check(self):
        if self.status is None:
            raise FioException("command %s not start" % " ".join(self.argv))
        if self.status == 0:
            return True
        else:
            raise ProcessException(self.argv[0], self.argv[1:], self.status, self.stdoutdata, self.stderrdata)


def job_init(**jobs_args):
    content = """[global]
%(SIZE)s
%(FILENAME)s
%(DIRECTORYCMD)s
direct=%(DIRECT)s
runtime=%(SECS)s
time_based
randrepeat=0
end_fsync=1
group_reporting=1
ioengine=%(ENGINE)s
fadvise_hint=%(FADVISE)s
%(ENGINECONF)s
""" % jobs_args
    return content


jobs_callables = {}


def new_job(f):
    jobs_callables[f.func_name] = f
    return f


# #####
# All the tests function
######
@new_job
def randrw(numjobs, **jobs_args):
    content = """[job]
rw=randrw
rwmixread=80
bs=%(BLOCKSIZE)sk
sync=0
numjobs=%(USERS)s
%(RANDOM_DIRECTIVE)s
""" % merge_dicts({'USERS': numjobs}, jobs_args)
    return content


@new_job
def read(numjobs, **jobs_args):
    content = ""
    for i in range(numjobs):
        content += """[job%(JOBNUMBER)s]
rw=read
bs=%(BLOCKSIZE)sk
numjobs=1
offset=%(OFFSET)s
""" % merge_dicts({'JOBNUMBER': i}, jobs_args)
    return content


@new_job
def randread(numjobs, **jobs_args):
    content = ""
    for i in range(numjobs):
        content += """[job%(JOBNUMBER)s]
rw=randread
bs=%(BLOCKSIZE)sk
numjobs=1
offset=%(OFFSET)s
%(RANDOM_DIRECTIVE)s
""" % merge_dicts({'JOBNUMBER': i + 1}, jobs_args)
    return content


@new_job
def write(numjobs, **jobs_args):
    content = ""
    for i in range(numjobs):
        content += """[job%(JOBNUMBER)s]
rw=write
bs=%(BLOCKSIZE)sk
numjobs=1
offset=%(OFFSET)s
sync=1
direct=%(DIRECT)s
""" % merge_dicts({'JOBNUMBER': i + 1}, jobs_args)
    return content


def run_job(job, fio, job_file_prefix, block_size, numjobs, job_args):
    job_file = open(job_file_prefix + ".job", "w")
    job_file.write(job_init(BLOCKSIZE=block_size, **job_args))
    job_file.write(job(numjobs, BLOCKSIZE=block_size, **job_args))
    job_file.close()
    Executor([fio, "--append-terse", job_file_prefix + ".job", "--output", job_file_prefix + ".out"],
             stdout=sys.stdout,
             stderr=sys.stderr).run().check()
    print


def do_r(rootdir, outputdir, run_name, graphtype, jobsinfo):
    parser = [rootdir + "/fioparse.py"]
    parser += map(lambda x: "%s/%s_u%02d_kb%04d.out" % (outputdir, x[0], x[1], x[2]), jobsinfo)
    summary_file = open(outputdir + "/fio_summary.r", "w")
    Executor(parser,
             stdout=summary_file,
             stderr=sys.stderr).run()
    summary_file.write('testtype = "%s"\n' % run_name)
    summary_file.close()
    if graphtype == 'default':
        jobsgraph = ['"randread"', '"8K"', '0',
                     '"read"', '"1024K"', '0',
                     '"read"', '"undefined"', '1',
                     '"read"', '"undefined"', '8',
                     '"write"', '"undefined"', '1',
                     '"write"', '"undefined"', '8',
                     '"randrw"', '"8K"', '0', ]
    elif graphtype == 'block':
        jobsgraph = reduce(lambda x, y: x + ['"%s"' % y[0], '"undefined"', '%d' % y[1]], jobsinfo, [])
    elif graphtype == 'users':
        jobsgraph = reduce(lambda x, y: x + ['"%s"' % y[0], '"%dK"' % y[2], '0'], jobsinfo, [])
    else:
        raise FioException("invalid graph type")
    plotr_file = open(outputdir + "/plot.r", "w")
    plotr_file.write("""source("%(rootdir)s/fiop.r")
source("%(outputdir)s/fio_summary.r")
dir =  "%(outputdir)s"
jobs <- NULL
jobs <- matrix(c(%(jobsgraphs)s), nrow=3)
jobs <- t(jobs)
source("%(rootdir)s/fiopg.r")
""" % {'rootdir': rootdir, 'outputdir': outputdir, 'jobsgraphs': ", ".join(jobsgraph)})
    plotr_file.close()
    Executor(["R", "--no-save", "-f", outputdir + "/plot.r"],
             stdout=open("%s/R.out" % outputdir, "w"),
             stderr=sys.stderr).run().check()


def main():
    parser = OptionParser()
    parser.add_option("-d", "--directio", action="store_true", dest="directio",
                      help="use directio")
    parser.add_option("-b", "--fiobinary", action="store", dest="fiobinary",
                      help="name of fio binary, defaults to fio")
    parser.add_option("-w", "--workdir", action="store", dest="workdir",
                      help="work directory where fio creates a fio and reads and writes, no default")
    parser.add_option("-r", "--raw_device", action="store", dest="raw_device",
                      help="use raw device instead of file")
    parser.add_option("-o", "--outputdir", action="store", dest="outputdir")
    parser.add_option("-t", "--test", action="append", dest="tests",
                      help="""tests to run, defaults to all, options are
                              randread - IOPS test : 8k by 1, 8, 16, 32, 64 users 
                              read  - MB/s test : 1M by 1,8,16,32 users & 8k, 32k, 128k, 1024k by 1 user
                              write - redo test, ie sync seq writes : 1k, 4k, 8k, 128k, 1024k by 1 user 
                              randrw   - workload test: 8k read write by 1,8,16,32, 64 users""")
    parser.add_option("-s", "--seconds", action="store", dest="seconds", type=type(1),
                      help="seconds to run each test for, default 60")
    parser.add_option("-m", "--megabytes", action="store", dest="megabytes", type=type(1))
    parser.add_option("-i", "--individual", action="store_true", dest="individual_files")
    parser.add_option("-u", "--users", action="append", dest="users", type=type(1),
                      help="test only use this many users")
    parser.add_option("-l", "--blocksize", action="append", dest="blocksizes", type=type(1),
                      help="test only use this blocksize in KB, ie 1-1024")
    # -x              remove work file after run
    # -y              initialize raw devices to "-m megabytes" with writes 
    parser.add_option("-R", "--random", action="store", dest="random_directive",
                      help="Add an random directive (see random_distribution and other directives in fio(1)")
    parser.add_option("-N", "--run_name", action="store", dest="run_name",
                      help="Give a name to the run")
    parser.add_option("-E", "--engine", action="store", dest="engine",
                      help="chose engine")
    parser.add_option("-C", "--engine_conf", action="store", dest="engine_conf",
                      help="configure engine, append this definition to [global] section")
    parser.add_option("-D", "--distant", action="store_true", dest="distant",
                      help="engine is distant (hdfs, ceph)")
    parser.add_option("-B", "--graph_block", action="store_const", dest="graph_type", const="block",
                      help="with non default run, keep users, change block size in graph")
    parser.add_option("-U", "--graph_users", action="store_const", dest="graph_type", const="users",
                      help="with non default run, keep block size, change users in graph")
    parser.add_option("--fadvise", action="store_true", dest="fadvise",
                      help="activate fadvise hint")

    default_options = {
        'directio': False,
        'fiobinary': "fio",
        'workdir': None,
        'raw_device': None,
        'outputdir': ".",
        'tests': [],
        'seconds': 60,
        'megabytes': 65536,
        'individual_files': False,
        'users': [],
        'blocksizes': [],
        'random_directive': "random_distribution=random",
        'run_name': platform.node(),
        'distant': False,
        'engine': "psync",
        'engine_conf': "",
        'graph_type': 'default',
        'fadvise': False,
    }

    parser.set_defaults(**default_options)
    (options, args) = parser.parse_args()

    # resolve some path
    try:
        rbinary = Executor.check_executable("R")
    except FioException:
        print "will not generate graph"
        rbinary = None
    fiobinary = Executor.check_executable(options.fiobinary)

    old_runningdir = os.getcwdu()
    rootdir = os.path.dirname(os.path.abspath(__file__))
    if options.workdir is None and options.raw_device is None and not options.distant:
        raise FioException("work directory or raw device must be specified or a distant test")
    if not options.distant and options.workdir is not None:
        os.chdir(options.workdir)
        workdir = os.getcwdu()
        os.chdir(old_runningdir)
    else:
        workdir = options.workdir

    os.chdir(options.outputdir)
    outputdir = os.getcwdu()

    if len(options.tests) == 0:
        tests = ['randrw', 'read', 'randread', 'write']
    else:
        tests = options.tests

    # if non default tests runs, change the graph type
    if len(options.tests) > 0 or len(options.users) > 0 or len(options.blocksizes) > 0:
        if options.graph_type == 'default':
            options.graph_type = 'users'

    ternary_if = lambda x, y, z: y if x else z

    default_args = {
        'MEGABYTES': options.megabytes,
        'RANDOM_DIRECTIVE': options.random_directive,
        'ENGINE': options.engine,
        'ENGINECONF': options.engine_conf,
        'OFFSET': '0',
        'DIRECTORYCMD': ternary_if(workdir is not None, 'directory=%s' % workdir, ''),
        'DIRECT': '1' if options.directio else '0',
        'SECS': options.seconds,
        'FADVISE': '1' if options.fadvise else '0',
    }

    jobs_settings = {
        'randread': ({'blocksizes': (8,), 'users': (1, 8, 16, 32, 64)}, ),
        'read': ({'blocksizes': (1024,), 'users': (1, 8, 16, 32, 64)},
                 {'blocksizes': (1, 4, 8, 128, 1024), 'users': (1, 8)}, ),
        'write': ({'blocksizes': (1, 4, 8, 128, 1024), 'users': (1, 8)}, ),
        'randrw': ({'blocksizes': (8,), 'users': (1, 8, 16, 32, 64)}, ),
    }

    if options.raw_device is None:
        default_args['SIZE'] = "size=%dm" % options.megabytes
        default_args['FILENAME'] = 'filename=%s' % ternary_if(not options.individual_files, 'fiodata', '')
        # never extend or reuse a smaller filer, start from scratch
        default_args['FILENAME'] += "\noverwrite=0\nfile_append=0"
    else:
        default_args['SIZE'] = ""
        default_args['FILENAME'] = 'filename=%s' % options.raw_device


    jobs_done = set()
    for job in tests:
        try:
            job_callable = jobs_callables[job]
        except KeyError:
            raise FioException("%s is not a valid test name" % job)

        for job_setting in jobs_settings[job]:
            #Extract some settings from job definition
            if len(options.blocksizes) == 0:
                blocksizes = job_setting['blocksizes']
            else:
                blocksizes = options.blocksizes

            if len(options.users) == 0:
                users = job_setting['users']
            else:
                users = options.users

            for bs in blocksizes:
                for u in users:
                    if (job, u, bs) in jobs_done:
                        # test already done, don't run again
                        continue
                    job_args = copy.copy(default_args)

                    job_prefix_name = "%s_u%02d_kb%04d" % (job, u, bs)
                    print "running %s, %d users, %dk block" % (job, u, bs)
                    run_job(job_callable, fiobinary, job_prefix_name, bs, u, job_args)
                    jobs_done.add((job, u, bs))
    print "jobs finished, parsing the results"
    jobs_done = sorted(jobs_done, key=lambda x: "%s_u%02d_kb%04d.out" % (x[0], x[1], x[2]))
    if rbinary is not None:
        do_r(rootdir, outputdir, options.run_name, options.graph_type, jobs_done)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FioException as e:
        print e
        Executor.terminate_child()
        sys.exit(1)
    except KeyboardInterrupt:
        Executor.terminate_child()
        sys.exit(1)
