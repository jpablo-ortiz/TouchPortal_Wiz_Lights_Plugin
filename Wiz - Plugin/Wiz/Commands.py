from argparse import ArgumentParser

# handle CLI arguments
parser = ArgumentParser()
parser.add_argument("-i", help="Insert Ip")
parser.add_argument("-on", help="Turn On Command", action='store_true')
parser.add_argument("-off", help="Turn Off Command", action='store_true')
parser.add_argument("-b", help="Set Brightness")
parser.add_argument("-pruebas", help="Pruebas", action='store_true')

opts = parser.parse_args()
del parser

ip = opts.i

import asyncio

import pywizlight
from pywizlight import PilotBuilder, discovery, wizlight


async def turn_off():
    try:
        light = wizlight(ip)
        await light.turn_off()
    except Exception as e:
        print("No light found")

async def turn_on(brightness = 255):
    try:
        light = wizlight(ip)
        await light.turn_on(PilotBuilder(brightness = brightness))
    except Exception as e:
        print("No light found")

if opts.on:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(turn_on())
elif opts.off:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(turn_off())
elif opts.b:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(turn_on(int(opts.b)))
else:
    print("No command given")
