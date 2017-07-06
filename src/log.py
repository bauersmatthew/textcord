import sys

out = None
def init():
    global out
    out = open('log.out', 'w')

def finalize():
    global out
    out.close()

def msg(s):
    out.write(str(s) + '\n')
