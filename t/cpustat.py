#!/bin/env python2

from subprocess import *
import sys
import os
import signal
import re

# 3: user
# 5: sys
# 6: soft

MAX_CPU = 128
current_time = None
col_map = [None] * 3
cpu_stat = [None] * MAX_CPU
cpu_num = 0
first = True
counts = 0

def out(ctime, cpu_stat, cpu_num):
    global first
    if first:
        first = False
        print('{0}    ALL    {1}'.format(ctime, ' '.join('{0}{1:<6}'.format('  ', i) for i in range(cpu_num))))
    num_sum = [0] * 3
    for x in cpu_stat[:cpu_num]:
        for i in range(len(num_sum)):
            num_sum[i] += float(x[i])
    for i in range(len(num_sum)):
        num_sum[i] /= cpu_num
    fieldf = lambda r: '{0:8}'.format('{0:2.0f}|{1:1.0f}|{2:1.0f}'.format(float(r[0]), float(r[1]), float(r[2])))
    print('{0}  {1}'.format(ctime, ' '.join([fieldf(num_sum)] + [fieldf(x) for x in cpu_stat[:cpu_num]])))

def out2(ctime, cpu_stat, cpu_num):
    global counts
    title = []
    for thread_type in spec:
        title.append(thread_type)
        d = spec[thread_type]
        s = 0
        for i in range(d['start'], d['end']):
            s += float(cpu_stat[i][0]) + float(cpu_stat[i][1]) + float(cpu_stat[i][2])
        d['cpu'] = int(s / (d['end'] - d['start']))
    if counts % 20 == 0:
        print('{0}  {1}'.format(ctime, ' '.join(title)))
    counts += 1
    print('{0}  {1}'.format(ctime, ' '.join(['{0:3}'.format(spec[x]['cpu']) for x in spec])))

def calc_bind_spec(rule):
    def make_mask(s, c): return hex(((1<<c) - 1) << s).replace('L', '')
    def move(p, s):
        if s[0] not in '+-': return int(s)
        return p + int(s)
    spec = dict()
    p = 0
    for thread_type,bind_style,id_range in re.findall('(\w+):(?:(\w+):)?([0-9.+-]+)', rule):
        if not bind_style: bind_style = 's'
        if '..' in id_range:
            s, e = id_range.split('..')
        else:
            s, e = '+0', id_range
            if e[0] not in '+-': e = '+' + e
        start = move(p, s)
        end =  move(start, e)
        p = end
        spec[thread_type] = dict(style=bind_style, mask=make_mask(start, end - start), comment='[%d,%d)'%(start, end), start = start, end = end)
    return spec
default_spec = 'DAG:6,IOMGR:2,IODISK:2,EASY:4,misc:+0..24'
spec = calc_bind_spec(default_spec)

def get_column_info(r):
    global col_map
    for i, k in enumerate(r):
        if k == '%usr':
            col_map[0] = i
        if k == '%sys':
            col_map[1] = i
        if k == '%soft':
            col_map[2] = i
def process(l):
    global current_time
    global col_map
    global cpu_stat
    global cpu_num
    r = l.split()
    if len(r) > 2 and len(r) > col_map[2]:
        if r[2] == 'CPU':
            if current_time is not None:
                out(current_time, cpu_stat, cpu_num)
            else:
                get_column_info(r)
            current_time = r[0]
        elif r[2].isdigit():
            cpu_id = int(r[2])
            if cpu_id < MAX_CPU:
                cpu_num = cpu_id + 1 if cpu_id >= cpu_num else cpu_num
                cpu_stat[cpu_id] = (r[col_map[0]], r[col_map[1]], r[col_map[2]])


p = Popen('mpstat -P ALL 1', shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, env=os.environ, executable='/bin/bash')

signal.signal(signal.SIGTERM, lambda signal, frame: p.terminate())

while p.poll() is None:
    line = p.stdout.readline()
    if line:
        process(line)
ret = p.returncode
#try:
#    while p.poll() is None:
#        line = p.stdout.readline()
#        if line:
#            process(line)
#    ret = p.returncode
#except Exception as e:
#    p.terminate()
#    ret = p.returncode
#    print(str(e))
#except KeyboardInterrupt:
#    p.terminate()
#    ret = p.returncode

sys.exit(ret)
