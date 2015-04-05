from asyncio import get_event_loop

from .redminecharts import redminecharts


loop = get_event_loop()
loop.run_until_complete(redminecharts(loop))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
