import asyncio
import display as disp
import discord
import log
import sys
import death
import curses
import traceback

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

        sec_title = disp.glblsec.sub(
            disp.TextBox, 0, 0, 100, 33,
            text='Welcome to TextCord!',
            color=disp.make_color(fg=disp.BLUE,
                                  attr=disp.UNDERLINE|disp.BOLD),
            align=disp.TextBox.ALIGN_CENTER, voff=50)

        sec_login = disp.glblsec.sub(
            disp.BorderedBox, 15, 33, 70, 50)

        # key 27 is escape

        sec_email = sec_login.sub(
            disp.Activator, 0, 0, 100, 33)
        sec_email_prompt = sec_email.sub(
            disp.TextBox, 0, 0, 25, 100,
            text='Email: ',
            color_active=disp.make_color(attr=disp.BOLD|disp.REVERSE),
            align=disp.TextBox.ALIGN_RIGHT)
        sec_email_input = sec_email.sub(
            disp.InputBox, 25, 0, 75, 100, do_send_input=True)
        sec_email.add_key_handler(
            ord('\n'), lambda: disp.set_active(sec_passwd))
        sec_email.add_key_handler(
            ord('\t'), lambda: disp.set_active(sec_passwd))
            
        sec_passwd = sec_login.sub(
            disp.Activator, 0, 33, 100, 33)
        sec_passwd_prompt = sec_passwd.sub(
            disp.TextBox, 0, 0, 25, 100,
            text='Password: ',
            color_active=disp.make_color(attr=disp.BOLD),
            align=disp.TextBox.ALIGN_RIGHT)
        sec_passwd_input = sec_passwd.sub(
            disp.MaskedInput, 25, 0, 75, 100, do_send_input=True)
        sec_passwd.add_key_handler(
            ord('\n'), lambda: try_login.wave())
        sec_passwd.add_key_handler(
            ord('\t'), lambda: disp.set_active(btn_quit))

        btn_quit = sec_login.sub(
            disp.TextBox, 0, 66, 50, 33,
            text='Quit',
            color_active=disp.make_color(attr=disp.REVERSE),
            align=disp.TextBox.ALIGN_CENTER, voff=50)
        btn_quit.add_key_handler(
            ord('\n'), death.set_die_all)
        btn_quit.add_key_handler(
            ord('\t'), lambda: disp.set_active(btn_login))

        btn_login = sec_login.sub(
            disp.TextBox, 50, 66, 50, 33,
            text='Login',
            color_active=disp.make_color(attr=disp.REVERSE),
            align=disp.TextBox.ALIGN_CENTER, voff=50)
        btn_login.add_key_handler(
            ord('\t'), lambda: disp.set_active(sec_email))
        btn_login.add_key_handler(
            ord('\n'), lambda: try_login.wave())

        log.msg('Finalizing screen sections...')
        await disp.set_active(sec_email)
        await disp.glblsec.draw()

        client = discord.Client()
        
        log.msg('Entering deadwait loop...')
        while not death.die_all:
            if try_login:
                await try_login.lower()

                error = False
                err_text = ''
                try:
                    await client.login(sec_email_input.text,
                                        sec_passwd_input.text)
                except discord.LoginFailure as err:
                    error = True
                    err_text = 'Incorrect login credentials!'
                except discord.HTTPException as err:
                    error = True
                    err_text = 'Could not connect to server.'
                except:
                    error = True
                    err_text = 'Something went wrong!'

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
        # and hand main control over to discord.py
        log.msg('Logged in.')
        disp.glblsec.disown_all()
        disp.stdscr.clear()
        await disp.glblsec.draw()
        try:
            await client.connect()
        except:
            raise
        finally:
            client.close()

    except Exception as e:
        log.msg('App failed!')
        log.msg(str(e))
        log.msg(sys.exc_info()[0])
        log.msg(traceback.format_exc())
        raise

