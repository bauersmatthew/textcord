import curses
import os
os.environ.setdefault('ESCDELAY', '25')
stdscr=curses.initscr()
curses.noecho()
curses.cbreak()
stdscr.keypad(1)
curses.raw()
a = stdscr.getch()
b = None
if a == 27:
    b = stdscr.getch()
curses.nocbreak()
stdscr.keypad(0)
curses.echo()
curses.noraw()
curses.endwin()
print("#{}\t=\t{}".format(a, str(curses.keyname(a))))
if b is not None:
    print("#{}\t=\t{}".format(b, str(curses.keyname(b))))
