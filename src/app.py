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

        client = discord.Client()
        
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
        
        # ... and hand main control over to discord.py
        try:
            await client.connect()
        except:
            raise
        finally:
            await client.close()

    except Exception as e:
        log.msg('App failed!')
        log.msg(str(e))
        log.msg(sys.exc_info()[0])
        log.msg(traceback.format_exc())
        raise

