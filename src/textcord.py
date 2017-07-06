import discord
import asyncio

import display as disp
import app as app
import log

async def main():
    log.init()

    log.msg('Awaiting main futures...')
    futures = [disp.run(),
               app.run()]
    await asyncio.wait(futures)

    log.finalize()

if __name__ == '__main__':
    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(main())
    ioloop.close()
