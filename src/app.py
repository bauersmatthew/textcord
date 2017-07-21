import asyncio
import display as disp
import discord
import log
import sys
import death
import curses
import traceback
import fuzzyfinder

class Flag:
    def __init__(self, initial=False):
        self.raised = initial
    async def wave(self):
        self.raised = True
    async def lower(self):
        self.raised = False
    def __bool__(self):
        return self.raised

async def run():
    # first stage: the main menu
    try:
        log.msg('Waiting display setup...')
        while disp.glblsec is None:
            await asyncio.sleep(0)

        try_login = Flag()

        log.msg('Setting up login screen sections...')
        sec = {} #SECtion registry
        
        sec['title'] = disp.glblsec.sub(
            disp.TextBox, 0, 0, 100, 33,
            text='Welcome to TextCord!',
            color=disp.make_color(fg=disp.BLUE,
                                  attr=disp.UNDERLINE|disp.BOLD),
            align=disp.TextBox.ALIGN_CENTER, voff=50)

        sec['login'] = disp.glblsec.sub(
            disp.BorderedBox, 15, 33, 70, 50)

        # key 27 is escape

        sec['email'] = sec['login'].sub(
            disp.Activator, 0, 0, 100, 33)
        sec['email_prompt'] = sec['email'].sub(
            disp.TextBox, 0, 0, 25, 100,
            text='Email: ',
            color_active=disp.make_color(attr=disp.BOLD|disp.REVERSE),
            align=disp.TextBox.ALIGN_RIGHT)
        sec['email_input'] = sec['email'].sub(
            disp.InputBox, 25, 0, 75, 100, do_send_input=True)
        sec['email'].add_key_handler(
            ord('\n'), lambda: disp.set_active(sec['passwd']))
        sec['email'].add_key_handler(
            ord('\t'), lambda: disp.set_active(sec['passwd']))
            
        sec['passwd'] = sec['login'].sub(
            disp.Activator, 0, 33, 100, 33)
        sec['passwd_prompt'] = sec['passwd'].sub(
            disp.TextBox, 0, 0, 25, 100,
            text='Password: ',
            color_active=disp.make_color(attr=disp.BOLD),
            align=disp.TextBox.ALIGN_RIGHT)
        sec['passwd_input'] = sec['passwd'].sub(
            disp.MaskedInput, 25, 0, 75, 100, do_send_input=True)
        sec['passwd'].add_key_handler(
            ord('\n'), lambda: try_login.wave())
        sec['passwd'].add_key_handler(
            ord('\t'), lambda: disp.set_active(sec['btn_quit']))

        sec['btn_quit'] = sec['login'].sub(
            disp.TextBox, 0, 66, 50, 33,
            text='Quit',
            color_active=disp.make_color(attr=disp.REVERSE),
            align=disp.TextBox.ALIGN_CENTER, voff=50)
        sec['btn_quit'].add_key_handler(
            ord('\n'), death.set_die_all)
        sec['btn_quit'].add_key_handler(
            ord('\t'), lambda: disp.set_active(sec['btn_login']))

        sec['btn_login'] = sec['login'].sub(
            disp.TextBox, 50, 66, 50, 33,
            text='Login',
            color_active=disp.make_color(attr=disp.REVERSE),
            align=disp.TextBox.ALIGN_CENTER, voff=50)
        sec['btn_login'].add_key_handler(
            ord('\t'), lambda: disp.set_active(sec['email']))
        sec['btn_login'].add_key_handler(
            ord('\n'), lambda: try_login.wave())

        log.msg('Finalizing screen sections...')
        await disp.set_active(sec['email'])
        await disp.glblsec.draw()

        client = TextcordClient()
        
        log.msg('Entering deadwait loop...')
        while True:
            if death.die_all:
                # abort
                await client.close()
                return

            if try_login:
                await try_login.lower()

                error = False
                err_text = ''
                try:
                    await client.login(sec['email_input'].text,
                                        sec['passwd_input'].text)
                except discord.LoginFailure as err:
                    error = True
                    err_text = 'Incorrect login credentials!'
                except discord.HTTPException as err:
                    error = True
                    err_text = 'Could not connect to server.'
                except:
                    error = True
                    err_text = 'Something went wrong!'

                if not error and not client.is_logged_in:
                    error = True
                    err_text = 'Failed to log in.'
                    
                if error:
                    await disp.glblsec.sub(
                        disp.TextBox, 0, 83, 100, 17,
                        text=err_text,
                        color=disp.make_color(fg=disp.RED, attr=disp.BOLD),
                        align=disp.TextBox.ALIGN_CENTER, voff=50).draw()
                else:
                    break
                    
            await asyncio.sleep(0)
        # we logged in successfully; clear this screen
        log.msg('Logged in.')
        disp.glblsec.disown_all() # disconnect all from root
        await disp.set_active(disp.glblsec) # deactivate login screen
        # delete all sections
        sec.clear()
        disp.stdscr.clear() # clear the screen
        
        # start discord connection and main UI
        try:
            done, pending = await asyncio.wait([
                ui_thread(client),
                client.connect()])
            assert not pending
            for future in done:
                if future.exception() is not None:
                    raise future.exception()
        except:
            raise
        finally:
            await client.close()

        # finish
        death.die_all = True

    except Exception as e:
        log.msg('App failed!')
        log.msg(str(e))
        log.msg(sys.exc_info()[0])
        log.msg(traceback.format_exc())
        raise

# FLAGS FOR COMMUNICATION BETWEEN UI AND CLIENT
flg_ready = Flag()

# all past-login UI
async def ui_thread(client):
    await loading_screen()
    await main_screen(client)
    
async def main_screen(client):
    main_ss = disp.glblsec.sub(
        EasySplitSec, 0, 0, 100, 100,
        default_inner=ContentSec,
        client=client)
    disp.stdscr.clear()
    #disp.stdscr.refresh()
    await disp.set_active(main_ss)
    await disp.glblsec.draw()
    while True:
        await asyncio.sleep(0)

class ContentSec(disp.Activator):
    def __init__(self, x, y, w, h, uid, parent, client):
        disp.Activator.__init__(self, x, y, w, h, uid, parent)
        self.client = client
        self.init_stage_serversel()

    def init_stage_serversel(self):
        lb = self.sub(
            HighlightListBox, 0, 20, 50, 80,
            lines=[s.name for s in self.client.servers],
            align=disp.TextBox.ALIGN_CENTER,
            color_active=disp.make_color(fg=disp.RED, attr=disp.BOLD))
        self.sub(
            FuzzyFindInput, 65, 20, 35, 80, do_send_input=True,
            listbox=lb, callback=self.exit_stage_serversel,
            color_active=disp.make_color(fg=disp.BLUE, attr=disp.BOLD))

    async def exit_stage_serversel(self, servername):
        self.children = []
        self.to_activate = []
        self.to_send_input = []
        await self.init_stage_channelsel(servername)

    async def init_stage_channelsel(self, servername):
        self.server = None
        for s in self.client.servers:
            if s.name == servername:
                self.server = s
                break
        lb = self.sub(
            HighlightListBox, 0, 20, 50, 80,
            lines=[c.name for c in self.server.channels if
                   c.type == discord.ChannelType.text],
            align=disp.TextBox.ALIGN_CENTER,
            color_active=disp.make_color(fg=disp.RED, attr=disp.BOLD))
        self.sub(
            FuzzyFindInput, 65, 20, 35, 80, do_send_input=True,
            listbox=lb, callback=self.exit_stage_channelsel,
            color_active=disp.make_color(fg=disp.BLUE, attr=disp.BOLD))
        await self.on_activate()

    async def exit_stage_channelsel(self, channelname):
        self.children = []
        self.to_activate = []
        self.to_send_input = []

        self.channel = None
        for c in self.server.channels:
            if c.name == channelname:
                self.channel = c
                break
        await self.init_stage_chat()

    async def init_stage_chat(self):
        box_inpbox = self.sub(
            disp.BorderedBox, 15, 70, 70, 20,
            do_activate=False, do_send_input=False,
            color=disp.color_default,
            color_active=disp.make_color(fg=disp.RED, attr=disp.BOLD))
        inpbox = box_inpbox.sub(
            disp.InputBox, 0, 0, 100, 100,
            do_activate=True, do_send_input=True)
        box_logs = self.sub(
            disp.BorderedBox, 15, 10, 70, 50,
            do_activate=False, do_send_input=False,
            color=disp.color_default,
            color_active=disp.make_color(fg=disp.RED, attr=disp.BOLD))
        log_msgs = []
        async for msg in self.client.logs_from(self.channel, reverse=True):
            log_msgs.append(msg)
        log_text = '\n'.join(
            ['{}: {}'.format(
                m.author.name if m.author.nick is None else m.author.nick,
                m.content)
             for m in log_msgs])
        logs = box_logs.sub(
            disp.BottomstuckTextBox, 0, 0, 100, 100,
            do_activate=True, do_send_input=True,
            text=log_text)

        self.chat_active = None

        async def inpbox_tabhdl():
            await self.chat_set_active(box_logs)
        async def inpbox_enterhdl():
            await self.client.send_message(
                self.channel, inpbox.text)
            inpbox.text = ''
            inpbox.do_clear = True
            await inpbox.draw()
        async def logbox_tabhdl():
            await self.chat_set_active(box_inpbox)

        box_inpbox.add_key_handler(9, inpbox_tabhdl)
        box_inpbox.add_key_handler(10, inpbox_enterhdl)
        box_logs.add_key_handler(9, logbox_tabhdl)
        
        await self.chat_set_active(box_inpbox)
        global chat_logs
        if self.server.name not in chat_logs:
            chat_logs[self.server.name] = {self.channel.name : logs}
        else:
            chat_logs[self.server.name][self.channel.name] = logs

        disp.stdscr.clear()
        await self.draw()

    async def chat_set_active(self, sec):
        if self.chat_active is not None:
            await self.chat_active.on_deactivate()
        self.chat_active = sec
        await self.chat_active.on_activate()

    async def handle_input(self, ch):
        await disp.Activator.handle_input(self, ch)
        try:
            await self.chat_active.handle_input(ch)
        except:
            pass #mehhh
            
chat_logs = {} # server / channel / UI textbox

class FuzzyFindInput(disp.InputBox):
    def __init__(self, x, y, w, h, uid, parent, listbox, callback,
                 **kwargs):
        disp.InputBox.__init__(self, x, y, w, h, uid, parent, **kwargs)
        self.lb = listbox
        self.callback = callback

    async def handle_input(self, ch):
        if ch == 258: # down
            await self.lb.hldown()
            return True
        elif ch == 259: # up
            await self.lb.hlup()
            return True
        elif ch == 9: # tab
            self.text = self.lb.lines[0]
            self.cursor = len(self.text)
            self.do_clear = True
            await self.draw()
            self.lb.hlline = 0
            await self.lb.draw()
            return True
        elif ch == 10: # enter
            await self.callback(self.lb.lines[self.lb.hlline])
            return True
        elif (await disp.InputBox.handle_input(self, ch)):
            self.lb.lines = fuzzyfinder.fuzzyrank(
                self.text, self.lb.lines)
            self.lb.do_clear = True
            await self.lb.draw()
            return True
        return False

class HighlightListBox(disp.ListBox):
    def __init__(self, x, y, w, h, uid, parent, **kwargs):
        disp.ListBox.__init__(self, x, y, w, h, uid, parent, **kwargs)
        self.hlline = 0
        color_info = disp.color_table[self.color]
        coloractive_info = disp.color_table[self.color_active]
        self.color_inv = disp.make_color(
            fg=color_info.fg, bg=color_info.bg,
            attr=color_info.attr | disp.REVERSE)
        self.coloractive_inv = disp.make_color(
            fg=coloractive_info.fg, bg=coloractive_info.bg,
            attr=coloractive_info.attr | disp.REVERSE)

    async def hldown(self):
        self.hlline += 1
        if self.hlline >= len(self.lines):
            self.hlline = 0
        await self.draw()

    async def hlup(self):
        self.hlline -= 1
        if self.hlline < 0:
            self.hlline = len(self.lines)-1
        await self.draw()

    async def draw_self(self):
        if self.do_clear:
            await self.clear()
            self.do_clear = False
        use_color = self.color_active if self.active else self.color
        use_hl = self.coloractive_inv if self.active else self.color_inv
        lnnum = 0 + int(float(self.voff)*float(self.h_real)/100)
        for i, line in enumerate(self.text_lines()):
            if lnnum == self.hlline:
                self.draw_one_line(line, lnnum, use_hl)
            else:
                self.draw_one_line(line, lnnum, use_color)
            lnnum += 1
                
class EasySplitSec(disp.BorderedBox):
    def __init__(self, x, y, w, h, uid, parent,
                 bleft=False, bright=False,
                 btop=False, bbottom=False,
                 default_inner=None, inner_inst=None,
                 **kwargs):
        # Section.__init__ calls recalc_coords which needs
        # active_sec, sec0, and sec1 to be valid attributes
        self.active_sec = None
        self.sec0 = None
        self.sec1 = None
        disp.BorderedBox.__init__(
            self, x, y, w, h, uid, parent,
            left_wid = 1 if bleft else 0,
            right_wid = 1 if bright else 0,
            top_wid = 1 if btop else 0,
            bot_wid = 1 if bbottom  else 0)
        self.def_inner = default_inner
        self.inner_kwargs = kwargs
        self.split_type = None # None, 'horiz', 'vert'
        self.sec0 = None # left, top
        self.sec1 = None # right, bottom
        if inner_inst is not None:
            self.active_sec = inner_inst
            # adopt inner_inst fully
            self.active_sec.parent = self
            self.active_sec.recalc_coords()
        else:
            self.active_sec = self.sub(
                self.def_inner, 0, 0, 100, 100, **self.inner_kwargs)

    async def handle_input(self, ch):
        ret = False
        draw = False
        if (await disp.Section.handle_input(self, ch)):
            ret = True
        # movement between sections
        elif ch == -ord('h') and self.split_type is not None:
            # m-h
            if (self.active_sec.__class__ is EasySplitSec and
                not (await self.active_sec.handle_input(ch))):
                if self.split_type == 'vert' and \
                   self.active_sec is not self.sec0:
                    await self.active_sec.on_deactivate()
                    self.active_sec = self.sec0
                    await self.active_sec.on_activate()
                    ret = True
                else:
                    ret = False
            else:
                ret = True
        elif ch == -ord('l') and self.split_type is not None:
            # m-l
            if (self.active_sec.__class__ is EasySplitSec and
                not (await self.active_sec.handle_input(ch))):
                if self.split_type == 'vert' and \
                   self.active_sec is not self.sec1:
                    await self.active_sec.on_deactivate()
                    self.active_sec = self.sec1
                    await self.active_sec.on_activate()
                    ret = True
                else:
                    ret = False
            else:
                ret = True
        elif ch == -ord('k') and self.split_type is not None:
            # m-k
            if (self.active_sec.__class__ is EasySplitSec and
                not (await self.active_sec.handle_input(ch))):
                if self.split_type == 'horiz' and \
                   self.active_sec is not self.sec0:
                    await self.active_sec.on_deactivate()
                    self.active_sec = self.sec0
                    await self.active_sec.on_activate()
                    ret = True
                else:
                    return False
            else:
                return True
        elif ch == -ord('j') and self.split_type is not None:
            # m-j
            if (self.active_sec.__class__ is EasySplitSec and
                not (await self.active_sec.handle_input(ch))):
                if self.split_type == 'horiz' and \
                   self.active_sec is not self.sec1:
                    await self.active_sec.on_deactivate()
                    self.active_sec = self.sec1
                    await self.active_sec.on_activate()
                    ret = True
                else:
                    ret = False
            else:
                ret = True
        elif ch == -ord('u'): # m-u ==> vert split
            draw = True
            if self.active_sec.__class__ is EasySplitSec:
                ret = (await self.active_sec.handle_input(ch))
            else:
                self.split_type = 'vert'
                # active sec --> left sec under new easysplitsec
                self.sec0 = self.sub(
                    EasySplitSec, 0, 0, 50, 100,
                    bright=True,
                    default_inner=self.def_inner,
                    inner_inst=self.active_sec, **self.inner_kwargs)
                self.sec0.recalc_coords()
                self.active_sec = self.sec0
                await self.active_sec.on_activate()
                # right sec --> new easysplitsec
                self.sec1 = self.sub(
                    EasySplitSec, 50, 0, 50, 100,
                    #bleft=True,
                    default_inner=self.def_inner,
                    **self.inner_kwargs)
                ret = True
        elif ch == -ord('i'): # m-i ==> horiz split
            draw = True
            if self.active_sec.__class__ is EasySplitSec:
                ret = (await self.active_sec.handle_input(ch))
            else:
                self.split_type = 'horiz'
                # active sec --> top sec under new easysplitsec
                self.sec0 = self.sub(
                    EasySplitSec, 0, 0, 100, 50,
                    #bbottom=True,
                    default_inner=self.def_inner,
                    inner_inst=self.active_sec, **self.inner_kwargs)
                self.sec0.recalc_coords()
                self.active_sec = self.sec0
                await self.active_sec.on_activate()
                # bottom sec --> new easysplitsec
                self.sec1 = self.sub(
                    EasySplitSec, 0, 50, 100, 50,
                    btop=True,
                    default_inner=self.def_inner,
                    **self.inner_kwargs)
                ret = True
        elif ch == -ord('x'): # m-x ==> close
            draw = True
            if self.active_sec.__class__ is EasySplitSec:
                ret = (await self.active_sec.handle_input(ch))
            else:
                # remove self from parent
                p = self.parent # alias for less typing
                nonactive = None
                if p.active_sec is p.sec0:
                    nonactive = p.sec1
                else:
                    nonactive = p.sec0

                p.sec0 = None
                p.sec1 = None

                if nonactive.active_sec.__class__ is EasySplitSec:
                    p.split_type = nonactive.split_type
                    p.sec0 = nonactive.sec0
                    p.sec0.parent = p
                    p.sec1 = nonactive.sec1
                    p.sec1.parent = p
                    p.active_sec = nonactive.active_sec
                else:
                    p.split_type = None
                    p.active_sec = nonactive.active_sec
                    p.active_sec.parent = p

                await p.active_sec.on_activate()

                # remove more refs
                self.parent = None
                self.active_sec.parent = None
                self.active_sec = None

                # update display
                p.active_sec.recalc_coords()
                if p.sec0 is not None and p.sec0 is not p.active_sec:
                    p.sec0.recalc_coords()
                if p.sec1 is not None and p.sec1 is not p.active_sec:
                    p.sec1.recalc_coords()
                await p.draw()

                return True
        elif ch > 0:
            # all other keys; just send to active
            ret = (await self.active_sec.handle_input(ch))
        if draw:
            await self.draw()
        return ret

    async def on_activate(self):
        await disp.Section.on_activate(self)
        await self.active_sec.on_activate()

    async def on_deactivate(self):
        await disp.Section.on_deactivate(self)
        await self.active_sec.on_deactivate()

    async def draw(self, head=True):
        if self.active_sec is None:
            return
        if head:
            disp.stdscr.clear()
        await self.draw_self()
        await self.active_sec.draw(False)
        if self.sec0 is not None and self.sec0 is not self.active_sec:
            await self.sec0.draw(False)
        if self.sec1 is not None and self.sec1 is not self.active_sec:
            await self.sec1.draw(False)
        if head:
            disp.do_refresh = True

    def sub(self, sub_type, x, y, w, h, **kwargs):
        # do not use self.children
        return sub_type(x, y, w, h, 0, self, **kwargs)

    def recalc_coords_children(self):
        if self.active_sec is not None:
            self.active_sec.recalc_coords()
        if self.sec0 is not None and self.sec0 is not self.active_sec:
            self.sec0.recalc_coords()
        if self.sec1 is not None and self.sec1 is not self.active_sec:
            self.sec1.recalc_coords()

async def loading_screen():
    sec_text = disp.glblsec.sub(
        disp.TextBox, 0, 0, 100, 50,
        text='Loading...',
        color=disp.make_color(fg=disp.RED, attr=disp.BOLD),
        align=disp.TextBox.ALIGN_CENTER, voff=80)

    ticker_chars = ['-', '\\', '|', '/', '-', '\\', '|', '/']
    ticker_curr = 0
    sec_ticker = disp.glblsec.sub(
        disp.TextBox, 0, 50, 100, 50,
        text=ticker_chars[ticker_curr],
        color=disp.make_color(fg=disp.GREEN, attr=disp.BOLD),
        align=disp.TextBox.ALIGN_CENTER)

    await disp.glblsec.draw()

    while not flg_ready:
        await asyncio.sleep(.25)
        ticker_curr += 1
        if ticker_curr == len(ticker_chars):
            ticker_curr = 0
        sec_ticker.text = ticker_chars[ticker_curr]
        await sec_ticker.draw()

    sec_text.release()
    sec_ticker.release()

class TextcordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        discord.Client.__init__(self, *args, **kwargs)
        self.sec = None # section dictionary/registry

    async def on_ready(self):
        await flg_ready.wave()

    async def on_message(self, message):
        global chat_logs
        cname = message.channel.name
        sname = message.server.name
        auth = message.author
        aname = None
        try:
            aname = auth.name if auth.nick is None else auth.nick
        except:
            return
        if sname in chat_logs and cname in chat_logs[sname]:
            chat_logs[sname][cname].text += '\n{}: {}'.format(
                aname,
                message.content)
            chat_logs[sname][cname].do_clear = True
            await chat_logs[sname][cname].draw()

