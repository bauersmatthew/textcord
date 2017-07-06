import asyncio
import curses
import sys
import traceback

import death
import log

from collections import namedtuple

def init():
    global stdscr
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.start_color()
    init_my_color_consts()
    curses.curs_set(False)
    stdscr.nodelay(True)
    stdscr.leaveok(0)
    log.msg('Curses display initialized.')
    log.msg('# Colors: {}'.format(curses.COLORS))
    log.msg('# Color pairs: {}'.format(curses.COLOR_PAIRS))

def finalize():
    global stdscr
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()

do_refresh = False

old_termsize = None
async def check_termsize_change():
    global stdscr, old_termsize, do_recalc_sizes
    new_termsize = stdscr.getmaxyx()
    if old_termsize != new_termsize:
        old_termsize = new_termsize
        return True
    else:
        return False

glblsec = None # the root section
async def run():
    global stdscr, glblsec, do_refresh
    try:
        init()
        glblsec = Section()

        log.msg('Entering infinite disp/IO loop...')
        # infinite display loop
        while not death.die_all:
            await asyncio.sleep(0)
            if do_refresh:
                stdscr.refresh()
                do_refresh = False
            if (await check_termsize_change()):
                glblsec.recalc_coords()
                stdscr.clear()
                await glblsec.draw()
            await check_input()
    except Exception as e:
        log.msg('Infinite disp/IO loop failed!')
        log.msg(str(e))
        log.msg(sys.exc_info()[0])
        log.msg(traceback.format_exc())
        sys.exit(-5)
    finally:
        log.msg('Finalizing curses display...')
        finalize()


# color and attribute constants
BLACK = curses.COLOR_BLACK
BLUE = curses.COLOR_BLUE
CYAN = curses.COLOR_CYAN
GREEN = curses.COLOR_GREEN
MAGENTA = curses.COLOR_MAGENTA
RED = curses.COLOR_RED
WHITE = curses.COLOR_WHITE
YELLOW = curses.COLOR_YELLOW

BLINK = curses.A_BLINK
BOLD = curses.A_BOLD
DIM = curses.A_DIM
INVIS = curses.A_INVIS
NORMAL = curses.A_NORMAL
REVERSE = curses.A_REVERSE
UNDERLINE = curses.A_UNDERLINE
def init_my_color_consts():
    # MUST BE CALLED AFTER CURSES SETUP!
    global BLACK
    global BLUE
    global CYAN
    global GREEN
    global MAGENTA
    global RED
    global WHITE
    global YELLOW
    global BLINK
    global BOLD
    global DIM
    global INVIS
    global NORMAL
    global REVERSE
    global UNDERLINE
    BLACK = curses.COLOR_BLACK
    BLUE = curses.COLOR_BLUE
    CYAN = curses.COLOR_CYAN
    GREEN = curses.COLOR_GREEN
    MAGENTA = curses.COLOR_MAGENTA
    RED = curses.COLOR_RED
    WHITE = curses.COLOR_WHITE
    YELLOW = curses.COLOR_YELLOW
    BLINK = curses.A_BLINK
    BOLD = curses.A_BOLD
    DIM = curses.A_DIM
    INVIS = curses.A_INVIS
    NORMAL = curses.A_NORMAL
    REVERSE = curses.A_REVERSE
    UNDERLINE = curses.A_UNDERLINE

    global color_table
    color_table.append(Color(WHITE, BLACK, NORMAL))

Color = namedtuple('Color', ['fg', 'bg', 'attr'])
color_table = []
color_default = 0

def make_color(fg=None, bg=None, attr=None):
    # the Color constructor requires all 3 args; this one doesnt
    col = Color(
        (fg if fg is not None else color_table[color_default].fg),
        (bg if bg is not None else color_table[color_default].bg),
        (attr if attr is not None else color_table[color_default].attr))

    global color_table
    try:
        # return already-existing index (if applicable)
        return color_table.index(col)
    except:
        # create new index, add that
        color_table.append(col)
        index = len(color_table)-1
        curses.init_pair(index, col.fg, col.bg)
        return index

def putstr(s, x, y, col=color_default):
    global stdscr, color_table
    stdscr.addstr(y, x, s,
                  curses.color_pair(col) | color_table[col].attr)

active_section = None
async def check_input():
    global stdscr, active_section
    ch = stdscr.getch()
    if ch == curses.ERR:
        return
    #else
    if active_section is not None:
        await active_section.handle_input(ch)

async def set_active(sec):
    global active_section
    if active_section is not None:
        await active_section.on_deactivate()
    active_section = sec
    await active_section.on_activate()

# model a section of the screen
class Section:
    # all in integer percentages
    def __init__(self,
                 x=0, y=0, w=100, h=100,
                 uid=0, parent=None):
        self.x_prop = x
        self.y_prop = y
        self.w_prop = w
        self.h_prop = h
        self.uid = uid
        self.parent = parent
        self.children = []
        self.key_handlers = {}
        self.active = False

        self.recalc_coords()

    # calculate actual coords from % vals
    # assume that the parent has already recalculated!
    def recalc_coords(self):
        self.recalc_coords_self()
        self.recalc_coords_children()

    # do own
    def recalc_coords_self(self):
        xoff = yoff = wmax = hmax = None
        if self.parent is None:
            # load from env (no parent)
            global stdscr
            xoff = yoff = 0
            dims = stdscr.getmaxyx()
            wmax = dims[1]
            hmax = dims[0]
        else:
            # load from parent
            xoff = self.parent.x_real
            yoff = self.parent.y_real
            wmax = self.parent.w_real
            hmax = self.parent.h_real
            
        pc_of = lambda v, pc: int(float(v)*(float(pc)/100.0))
        self.x_real = xoff+pc_of(wmax, self.x_prop)
        self.y_real = yoff+pc_of(hmax, self.y_prop)
        self.w_real = pc_of(wmax, self.w_prop)
        self.h_real = pc_of(hmax, self.h_prop)

    # do childrens
    def recalc_coords_children(self):
        # DFS update children
        for child in self.children:
            if child is not None:
                child.recalc_coords()

    # remove a child
    def disown(self, uid):
        # unlink both ways
        if self.children[uid] is not None:
            self.children[uid].parent = None
        self.children[uid] = None

    # remove all children
    def disown_all(self):
        for uid in range(len(self.children)):
            self.disown(uid)

    # remove self from parent
    def release(self):
        if self.parent is not None:
            self.parent.disown(self.uid)

    # add a child
    # values in %
    def sub(self, sub_type, x, y, w, h, **kwargs):
        new_sub = sub_type(
            x, y, w, h,
            len(self.children), self,
            **kwargs)
        self.children.append(new_sub)
        return new_sub

    # drawing
    async def draw_children(self):
        for child in self.children:
            if child is not None:
                await child.draw(False)

    async def draw_self(self):
        # do something
        pass

    # head is internal use only
    async def draw(self, head=True):
        await self.draw_self()
        await self.draw_children()
        if head:
            global do_refresh
            do_refresh = True

    # call handler for the keypress
    async def handle_input(self, ch):
        if ch in self.key_handlers:
            await self.key_handlers[ch]()
            return True
        return False

    # add keypress handler
    # ch must be a number (i.e. ord('r'), not 'r')
    # fun must be a coroutine
    def add_key_handler(self, ch, fun):
        self.key_handlers[ch] = fun

    # remove keypress handler
    def rem_key_handler(self, ch):
        if ch in self.key_handlers:
            del self.key_handlers[ch]

    async def on_activate(self):
        self.active = True

    async def on_deactivate(self):
        self.active = False

class Activator(Section):
    def __init__(self, x, y, w, h, uid, parent, swallow_my_input=True):
        Section.__init__(self, x, y, w, h, uid, parent)
        self.to_activate = []
        self.to_send_input = []
        self.swallow = swallow_my_input

    async def on_activate(self):
        await Section.on_activate(self)
        for itr, child_uid in enumerate(self.to_activate):
            child = self.children[child_uid]
            if child is None:
                del self.to_activate[itr]
            else:
                await child.on_activate()

    async def on_deactivate(self):
        await Section.on_deactivate(self)
        for itr, child_uid in enumerate(self.to_activate):
            child = self.children[child_uid]
            if child is None:
                del self.to_activate[itr]
            else:
                await child.on_deactivate()

    def sub(self, sub_type, x, y, w, h,
            do_activate=True, do_send_input=False,
            **kwargs):
        child = Section.sub(self, sub_type, x, y, w, h, **kwargs)
        uid = len(self.children)-1
        if do_activate:
            self.to_activate.append(uid)
        if do_send_input:
            self.to_send_input.append(uid)
        return child

    async def handle_input(self, ch):
        handled = (await Section.handle_input(self, ch))
        if (handled and not self.swallow) or (not handled):
            for itr, child_uid in enumerate(self.to_send_input):
                child = self.children[child_uid]
                if child is None:
                    del self.to_send_input[itr]
                else:
                    await child.handle_input(ch)

class BorderedBox(Activator):
    def __init__(self,
                 x, y, w, h, uid, parent,
                 vert_ch='|', horiz_ch='-', corner_ch='+',
                 left_ch=None, right_ch=None,
                 top_ch=None, bot_ch=None,
                 tlc_ch=None, trc_ch=None,
                 blc_ch=None, brc_ch=None,
                 left_wid=1, right_wid=1,
                 top_wid=1, bot_wid=1):
        self.left_ch = (left_ch if left_ch is not None else vert_ch)
        self.right_ch = (right_ch if right_ch is not None else vert_ch)
        self.top_ch = (top_ch if top_ch is not None else horiz_ch)
        self.bot_ch = (bot_ch if bot_ch is not None else horiz_ch)
        self.tlc_ch = (tlc_ch if tlc_ch is not None else corner_ch)
        self.trc_ch = (trc_ch if trc_ch is not None else corner_ch)
        self.blc_ch = (blc_ch if blc_ch is not None else corner_ch)
        self.brc_ch = (brc_ch if brc_ch is not None else corner_ch)
        self.left_wid = left_wid
        self.right_wid = right_wid
        self.top_wid = top_wid
        self.bot_wid = bot_wid
        Activator.__init__(self,
            x, y, w, h, uid, parent)

    def recalc_coords_self(self):
        Section.recalc_coords_self(self)
        # distinguish between padded and unpadded
        # save raw values
        self.raw_x_real = self.x_real
        self.raw_y_real = self.y_real
        self.raw_w_real = self.w_real
        self.raw_h_real = self.h_real

        # trick our children
        self.x_real += self.left_wid
        self.y_real += self.top_wid
        self.w_real -= (self.left_wid + self.right_wid)
        self.h_real -= (self.top_wid + self.bot_wid)

    async def draw_border(self, sx, lenx, sy, leny, ch):
        border_str = ch * lenx
        for y in range(sy, sy+leny):
            putstr(border_str, sx, y)

    async def draw_self(self):
        # top
        await self.draw_border(
            self.raw_x_real, self.raw_w_real,
            self.raw_y_real, self.top_wid,
            self.top_ch)
        # right
        await self.draw_border(
            self.raw_x_real+self.raw_w_real-self.right_wid, self.right_wid,
            self.raw_y_real, self.raw_h_real,
            self.right_ch)
        # bot
        await self.draw_border(
            self.raw_x_real, self.raw_w_real,
            self.raw_y_real+self.raw_h_real-self.bot_wid, self.bot_wid,
            self.bot_ch)
        # left
        await self.draw_border(
            self.raw_x_real, self.left_wid,
            self.raw_y_real, self.raw_h_real,
            self.left_ch)
        # tlc
        await self.draw_border(
            self.raw_x_real, self.left_wid,
            self.raw_y_real, self.top_wid,
            self.tlc_ch)
        # trc
        await self.draw_border(
            self.raw_x_real+self.raw_w_real-self.right_wid, self.right_wid,
            self.raw_y_real, self.top_wid,
            self.trc_ch)
        # brc
        await self.draw_border(
            self.raw_x_real+self.raw_w_real-self.right_wid, self.right_wid,
            self.raw_y_real+self.raw_h_real-self.bot_wid, self.bot_wid,
            self.brc_ch)
        # blc
        await self.draw_border(
            self.raw_x_real, self.left_wid,
            self.raw_y_real+self.raw_h_real-self.bot_wid, self.bot_wid,
            self.blc_ch)

# (not bordered)
class TextBox(Section):
    ALIGN_LEFT = 0
    ALIGN_CENTER = 1
    ALIGN_RIGHT = 2

    def __init__(self, x, y, w, h, uid, parent,
                 do_scrolling=True, text='', color=color_default,
                 color_active=None, align=None, voff=0):
        Section.__init__(self, x, y, w, h, uid, parent)
        self.text = text
        self.scroll_offset = 0
        self.do_scrolling = do_scrolling
        self.do_clear = True
        self.color = color
        self.color_active = (color_active if color_active is not None else color)
        self.align = (align if align is not None else self.ALIGN_LEFT)
        self.voff = voff #vertical offset (%)
        
    def text_lines(self):
        cur_off = self.scroll_offset * self.w_real
        while cur_off < len(self.text):
            yield self.text[cur_off:cur_off+self.w_real]
            cur_off += self.w_real

    async def clear(self):
        blank_line = ' '*self.w_real
        lnnum = 0
        for y in range(self.y_real, self.y_real+self.h_real):
            try:
                putstr(blank_line, self.x_real, self.y_real+lnnum)
            except:
                pass
            lnnum += 1

    async def draw_self(self):
        # don't do clever word-safe wrapping or anything
        # maybe we'll do that later
        if self.do_clear:
            await self.clear()
            self.do_clear = False
        use_color = self.color_active if self.active else self.color
        lnnum = 0 + int(float(self.voff)*float(self.h_real)/100)
        for line in self.text_lines():
            if len(line) < self.w_real:
                # wrapping only matters for not-full lines
                adj_x = None
                if self.align == self.ALIGN_LEFT:
                    adj_x = self.x_real
                elif self.align == self.ALIGN_CENTER:
                    adj_x = self.x_real+((self.w_real-len(line))//2)
                else: # RIGHT
                    adj_x = self.x_real+self.w_real-len(line)

                putstr(line, adj_x, self.y_real+lnnum, use_color)
            else:
                putstr(line, self.x_real, self.y_real+lnnum, use_color)
            lnnum += 1

    async def handle_input(self, ch):
        # scroll (maybe)
        if self.do_scrolling:
            if ch == ord('j'): # down
                self.scroll_offset += 1
                self.do_clear = True
                return True
            elif ch == ord('k'):
                self.scroll_offset -= 1 # up
                if self.scroll_offset < 0:
                    self.scroll_offset = 0
                self.do_clear = True
                return True
            else:
                # it can't hurt I guess
                return await Section.handle_input(self, ch)
        else:
            return await Section.handle_input(self, ch)

    async def on_activate(self):
        await Section.on_activate(self)
        await self.draw()

    async def on_deactivate(self):
        await Section.on_deactivate(self)
        await self.draw()

class InputBox(TextBox):
    def __init__(self, x, y, w, h, uid, parent, **kwargs):
        TextBox.__init__(self, x, y, w, h, uid, parent,
                         do_scrolling=False, **kwargs)
        self.cursor = 0

    # typing!
    async def handle_input(self, ch):
        ret = True
        # overrides
        if (await Section.handle_input(self, ch)):
            pass
        # normal characters
        elif ch <= 255:
            self.text = (self.text[:self.cursor] +
                         chr(ch) +
                         self.text[self.cursor:])
            self.cursor += 1
        # movement
        elif ch == curses.KEY_LEFT:
            self.cursor -= 1
            if self.cursor < 0:
                self.cursor = 0
        elif ch == curses.KEY_RIGHT:
            self.cursor += 1
            if self.cursor >= len(self.text):
                self.cursor = len(self.text)-1
        elif ch == curses.KEY_UP:
            self.cursor -= self.w_real
            if self.cursor < 0:
                self.cursor = 0
        elif ch == curses.KEY_DOWN:
            self.cursor += self.w_real
            if self.cursor >= len(self.text):
                self.cursor = len(self.text)-1
        elif ch == curses.KEY_BACKSPACE:
            if self.cursor != 0:
                self.text = (self.text[:self.cursor-1] +
                             self.text[self.cursor:])
                self.cursor -= 1
                self.do_clear = True
        else:
            ret = False

        await self.draw()
        return ret

    def text_lines(self):
        all_lines = list(TextBox.text_lines(self))
        if len(all_lines) <= self.h_real:
            return all_lines
        else:
            # the last h_real
            return all_lines[-self.h_real:]

    async def draw_self(self):
        await TextBox.draw_self(self)
        if self.active:
            # draw cursor
            tot_lines = len(self.text)//self.w_real
            scroll_offset = (0 if tot_lines < self.h_real
                             else tot_lines-self.h_real)
            cursor_y = self.y_real + ((self.cursor//self.w_real) - scroll_offset)
            cursor_x = self.x_real + (self.cursor % self.w_real)
            putstr('█', cursor_x, cursor_y, self.color)

    async def draw(self, head=True):
        await TextBox.draw(self, head)

    async def on_activate(self):
        await TextBox.on_activate(self)
        await self.draw()

    async def on_deactivate(self):
        await TextBox.on_deactivate(self)
        self.do_clear = True
        await self.draw()

class MaskedInput(InputBox):
    def __init__(self, x, y, w, h, uid, parent,
                 mask='*', **kwargs):
        InputBox.__init__(self, x, y, w, h, uid, parent, **kwargs)
        self.mask = mask

    def text_lines(self):
        for line in InputBox.text_lines(self):
            yield self.mask*len(line)
