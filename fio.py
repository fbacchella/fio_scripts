#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
from optparse import OptionParser
import subprocess
import os
from distutils import spawn
import signal
import re
import platform

def merge_dicts(*dict_args):
    '''
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    '''
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
        if hasattr(Executor,'process') and Executor.process is not None:
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
            return FioException("no command given")
        filename_path = spawn.find_executable(filename)
        if filename_path is not None:
            try:
                if not os.access(filename_path, os.X_OK):
                    return FioException("no executable command '%s'" % filename_path)
            except OSError as e:
                return FioException("no valid command path '%s': '%s'" % (filename_path, e))
        else:
            return FioException("command '%s' not found in path" % filename)
        return filename_path

    def __init__(self, argv, debug=None, follow_stdout=False, forget=False, **kwargs):
        realbinary = Executor.check_executable(argv[0])
        if isinstance(realbinary, Exception):
            raise realbinary
        self.argv = [ realbinary ] + argv[1:]
        self.status = None
        self.forget = forget
        self.kwargs = dict(list(Executor.default.items()) + list(kwargs.items()))
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
fadvise_hint=0
%(ENGINECONF)s""" % jobs_args
    return content

class Jobs(object):
    @staticmethod
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

    @staticmethod
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
    
    @staticmethod
    def randread(numjobs, **jobs_args):
        content = ""
        for i in range(numjobs):
            content += """[job%(JOBNUMBER)s]
rw=randread
bs=%(BLOCKSIZE)sk
numjobs=1
offset=%(OFFSET)s
%(RANDOM_DIRECTIVE)s
""" % merge_dicts({'JOBNUMBER': i + 1 }, jobs_args)
        return content

    @staticmethod
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
    e = Executor([fio, "--append-terse", job_file_prefix + ".job"],
                 stdout = open(job_file_prefix + ".out", "w"),
                 stderr=sys.stderr
    ).run().check()

    
def do_r(rootdir, outputdir, run_name, jobsinfo):
    parser = [ rootdir + "/fioparse.py"]
    parser += map( lambda x: "%s/%s_u%02d_kb%04d.out" % (outputdir, x[0], x[1], x[2]), jobsinfo)
    summary_file = open(outputdir + "/fio_summary.r", "w")
    e = Executor(parser,
                 stdout = summary_file,
                 stderr=sys.stderr
    ).run()
    summary_file.write('testtype = "%s"\n' % run_name)
    summary_file.close()
    jobsgraph = reduce(lambda x,y: x + [ '"%s"' % y[0], '"%dK"' % y[2] ], jobsinfo, [])
    plotr_file = open(outputdir + "/plot.r", "w")
    plotr_file.write("""source("%(rootdir)s/fiop.r")
source("%(outputdir)s/fio_summary.r")
dir =  "%(outputdir)s"
l <- NULL
l <- matrix(c(%(jobsgraphs)s),nrow=2)
tl <- t(l)
l <- tl
source("%(rootdir)s/fiopg.r")
""" % {'rootdir': rootdir, 'outputdir': outputdir, 'jobsgraphs': ", ".join(jobsgraph)})
    plotr_file.close()
    e = Executor(["R", "--no-save", "-f", outputdir + "/plot.r"],
                 stdout = open("%s/R.out" % outputdir, "w"),
                 stderr=sys.stderr
    ).run().check()
    
def main():

    parser = OptionParser()
    parser.add_option("-d", "--directio", action="store_true", dest="directio",
                      help="do/don't directio")
    parser.add_option("-b", "--fiobinary", action="store", dest="fiobinary",
                      help="name of fio binary, defaults to fio")
    parser.add_option("-w", "--workdir", action="store", dest="workdir",
                      help="work directory where fio creates a fio and reads and writes, no default")
    parser.add_option("-o", "--outputdir", action="store", dest="outputdir")
    parser.add_option("-t", "--test", action="append", dest="tests")
    parser.add_option("-s", "--seconds", action="store", dest="seconds", type=type(1),
                      help="seconds to run each test for, default 60")
    parser.add_option("-m", "--megabytes", action="store", dest="megabytes", type=type(1))
    parser.add_option("-i", "--individual", action="store_true", dest="individual_files")
    parser.add_option("-u", "--users", action="append", dest="users")
    # -l
    # -e
    # -d
    # -x
    # -y
    # -r
    parser.add_option("-R", "--random", action="store", dest="random_directive",
                      help="Add an random directive (see random_distribution and other directives in fio(1)")
    parser.add_option("-N", "--run_name", action="store", dest="run_name",
                      help="Give a name to the run")
    # -E
    # -C
    parser.add_option("-D", "--distant", action="store_true", dest="distant",
                      help="engine is distant (hdfs, ceph)")
    
    default_options= {
        'directio': False,
        'fiobinary': "fio",
        'workdir': None,
        'outputdir': ".",
        'tests': [],
        'seconds': 60,
        'megabytes': 65536,
        'individual_files': False,
        'users': [],
        'run_name': platform.node(),
        'random_directive': "random_distribution=random",
        'distant': False,
    }

    parser.set_defaults(**default_options)
    (options, args) = parser.parse_args()

    # resolve some path
    for bincmd in (Executor.check_executable(options.fiobinary), Executor.check_executable("R")) :
        if isinstance(bincmd, Exception):
            raise bincmd
        
    rootdir = os.getcwdu()
    fiobinary = os.path.abspath(options.fiobinary)
    os.chdir(options.outputdir)
    outputdir = os.getcwdu()
    if options.workdir is None:
        raise FioException("work dir must be specified")
    if not options.distant:
        os.chdir(rootdir)
        os.chdir(options.workdir)
        workdir = os.getcwdu()
        os.chdir(outputdir)
    else:
        workdir = options.workdir

    if(len(options.tests)) == 0:
        tests = [ 'randrw', 'read', 'randread', 'write']
    else:
        tests = options.tests
            
    if(len(options.users)) == 0:
        users = [1, 8, 16, 32, 64]
    else:
        users = options.users

    jobs_settings = {
        'randrw': { 'blocksizes': (8,), 'jobs_default_args': {}},
        'read': { 'blocksizes': (1024,), 'jobs_default_args': {}},
        'randread': { 'blocksizes': (8,), 'jobs_default_args': {}},
        'write': { 'blocksizes': (8, 128), 'jobs_default_args': {}}
    }
    
        
    default_args = {
        'MEGABYTES': options.megabytes,
        'FILE': 'fiodata',
        'RANDOM_DIRECTIVE': options.random_directive,
        'ENGINE': "psync",
        'ENGINECONF': "",
        'OFFSET': '0',
        'DIRECTORYCMD': 'directory=%s' % (outputdir),
        'DIRECT': '1' if options.directio else '0',
        'SECS': options.seconds,
    }
    if not options.individual_files:
        default_args['FILENAME'] = 'filename=fiodata'
        default_args['SIZE'] = "size=%dm" % (options.megabytes)
    else:
        default_args['FILENAME'] = ""
    jobs_done = []
    for job in tests:
        job_callable = getattr(Jobs, job)
        job_setting = jobs_settings[job]
        jobs_default_args = job_setting['jobs_default_args']
        for bs in job_setting['blocksizes']:
            for u in users:
                job_args = merge_dicts(default_args, jobs_default_args)
                # if individual files per process, the global size is the same
                if options.individual_files:
                    job_size = int(options.megabytes / u)
                    if job_size < 1:
                        raise FioException("job size too small, with %d users" % u)
                    job_args['SIZE'] = "size=%dm" % (job_size)

                job_prefix_name = "%s_u%02d_kb%04d" % (job, u, bs)
                run_job(job_callable, fiobinary, job_prefix_name, bs, u, job_args)
                jobs_done += [(job, u, bs)]
        print "jobs finished, parsing the results"
    do_r(rootdir, outputdir, options.run_name, jobs_done)


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
