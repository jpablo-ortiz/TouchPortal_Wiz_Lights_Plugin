# ----------------------------------------------------------
# ------------------------ IMPORTS -------------------------
# ----------------------------------------------------------

import asyncio
import json
import os
import sys
# imports below are optional, to provide argument parsing and logging functionality
from argparse import SUPPRESS as APSUPPRESS
from argparse import ArgumentParser
from logging import (DEBUG, INFO, WARNING, FileHandler, Formatter, NullHandler,
                     StreamHandler, getLogger)

import TouchPortalAPI as TP

# ----------------------------------------------------------
# ----------------------- VARIABLES ------------------------
# ----------------------------------------------------------

# Version string of this plugin (in Python style).
__version__ = "1.0"

# The unique plugin ID string is used in multiple places.
PLUGIN_ID = "tp.plugin.wiz"

# Basic plugin metadata
TP_PLUGIN_INFO = {
    'sdk': 3,
    'version': int(float(__version__) * 100),  # TP only recognizes integer version numbers
    'name': "Wiz Plugin",
    'id': PLUGIN_ID,
    "plugin_start_cmd": "\"%TP_PLUGIN_FOLDER%Wiz\\wiz.exe\"",
    'configuration': {
        'colorDark': "#25274c",
        'colorLight': "#707ab5"
    }
}

# Setting(s) for this plugin.
TP_PLUGIN_SETTINGS = {
    "light1": {
        "name": "IP Light #1",
        "type": "text",
        "default": "192.168.1.102",
        "max_length": "15"
    },
    "light2": {
        "name": "IP Light #2",
        "type": "text",
        "default": "",
        "max_length": "15"
    },
    "light3": {
        "name": "IP Light #3",
        "type": "text",
        "default": "",
        "max_length": "15"
    },
    "light4": {
        "name": "IP Light #4",
        "type": "text",
        "default": "",
        "max_length": "15"
    }
}

TP_PLUGIN_CATEGORIES = {
    "main": {
        'id': PLUGIN_ID + ".main",
        'name' : "Wiz",
        # 'imagepath' : "icon-24.png"
    }
}

# Action(s) which this plugin supports.
TP_PLUGIN_ACTIONS = {
    # Propios
    'turn_on_light': {
        'category': "main",
        'id': PLUGIN_ID + ".act.turn_on_light",
        'name': "Prender Luz",
        'prefix': TP_PLUGIN_CATEGORIES['main']['name'],
        'type': "communicate",
        'tryInline': True,
        'format': "Prender la luz con ip: $[1]",
        'data': {
            'ip_light': {
                'id': PLUGIN_ID + ".act.turn_on_light.data.light",
                'type': "text",
                'label': "IP Luz",
                'default': ""
            },
        }
    },
    'turn_off_light': {
        'category': "main",
        'id': PLUGIN_ID + ".act.turn_off_light",
        'name': "Apagar Luz",
        'prefix': TP_PLUGIN_CATEGORIES['main']['name'],
        'type': "communicate",
        'tryInline': True,
        'format': "Apagar la luz con ip: $[1]",
        'data': {
            'ip_light': {
                'id': PLUGIN_ID + ".act.turn_off_light.data.light",
                'type': "text",	
                'label': "IP Luz",
                'default': ""
            },
        }
    },
    'brightness': {
        'category': "main",
        'id': PLUGIN_ID + ".act.brightness",
        'name': "Ajustar Brillo",
        'prefix': TP_PLUGIN_CATEGORIES['main']['name'],
        'type': "communicate",
        'tryInline': True,
        'format': "Ajustar brillo de la luz con ip: $[1] al $[2]% (1-100%)",
        'data': {
            'ip_light': {
                'id': PLUGIN_ID + ".act.brightness.data.light",
                'type': "text",
                'label': "IP Luz",
                'default': ""
            },
            'brightness': {
                'id': PLUGIN_ID + ".act.brightness.data.brightness",
                'type': "text",
                'label': "Brillo",
                'default': ""
            }
        }
    }
    # TODO - Futuras acciones
    # 1. Ajustar Blanco frío y calido
    # 2. Ajustar color con Valores RGB
    # 3. Cambiar entre escenas
    # Aunque no es una acción, poder ver el estado actual de la luz
    # Aunque no es una acción, poder ver el nombre de la escena actual

}

# Plugin static state(s). These are listed in the entry.tp file,
# vs. dynamic states which would be created/removed at runtime.
TP_PLUGIN_STATES = {
    # Propios
    'light1': {
        'id': PLUGIN_ID + ".state.light1",
        'desc': "IP Light 1",
        'type': "text",
        'default': TP_PLUGIN_SETTINGS['light1']['default'],
    },
    'light2': {
        'id': PLUGIN_ID + ".state.light2",
        'desc': "IP Light 2",
        'type': "text",
        'default': TP_PLUGIN_SETTINGS['light2']['default'],
    },
    'light3': {
        'id': PLUGIN_ID + ".state.light3",
        'desc': "IP Light 3",
        'type': "text",
        'default': TP_PLUGIN_SETTINGS['light3']['default'],
    },
    'light4': {
        'id': PLUGIN_ID + ".state.light4",
        'desc': "IP Light 4",
        'type': "text",
        'default': TP_PLUGIN_SETTINGS['light4']['default'],
    }
}

# Plugin Event(s).
TP_PLUGIN_EVENTS = {}

# ----------------------------------------------------------
# ----------------------- API CLIENT -----------------------
# ----------------------------------------------------------

try:
    TPClient = TP.Client(
        pluginId = PLUGIN_ID,  # required ID of this plugin
        sleepPeriod = 0.05,    # allow more time than default for other processes
        autoClose = True,      # automatically disconnect when TP sends "closePlugin" message
        checkPluginId = True,  # validate destination of messages sent to this plugin
        maxWorkers = 4,        # run up to 4 event handler threads
        updateStatesOnBroadcast = False,  # do not spam TP with state updates on every page change
    )
except Exception as e:
    sys.exit(f"Could not create TP Client, exiting. Error was:\n{repr(e)}")

# Crate the (optional) global logger
g_log = getLogger()

# ----------------------------------------------------------
# --------------------- SETTINGS USE -----------------------
# ----------------------------------------------------------

# Settings will be sent by TP upon initial connection to the plugin,
# as well as whenever they change at runtime. This example uses a
# shared function to handle both cases. See also onConnect() and onSettingUpdate()
def handleSettings(settings, on_connect=False):
    # the settings array from TP can just be flattened to a single dict,
    # from:
    #   [ {"Setting 1" : "value"}, {"Setting 2" : "value"} ]
    # to:
    #   { "Setting 1" : "value", "Setting 2" : "value" }
    settings = { list(settings[i])[0] : list(settings[i].values())[0] for i in range(len(settings)) }

    # now we can just get settings, and their values, by name
    
    if (value := settings.get(TP_PLUGIN_SETTINGS['light1']['name'])) is not None:
        # Proceso que hacer al cambiar el valor de la configuración
        TP_PLUGIN_SETTINGS['light1']['value'] = value
        TPClient.stateUpdate(TP_PLUGIN_STATES['light1']['id'], value)

    if (value := settings.get(TP_PLUGIN_SETTINGS['light2']['name'])) is not None:
        # Proceso que hacer al cambiar el valor de la configuración
        TP_PLUGIN_SETTINGS['light2']['value'] = value
        TPClient.stateUpdate(TP_PLUGIN_STATES['light2']['id'], value)

    if (value := settings.get(TP_PLUGIN_SETTINGS['light3']['name'])) is not None:
        # Proceso que hacer al cambiar el valor de la configuración
        TP_PLUGIN_SETTINGS['light3']['value'] = value
        TPClient.stateUpdate(TP_PLUGIN_STATES['light3']['id'], value)

    if (value := settings.get(TP_PLUGIN_SETTINGS['light4']['name'])) is not None:
        # Proceso que hacer al cambiar el valor de la configuración
        TP_PLUGIN_SETTINGS['light4']['value'] = value
        TPClient.stateUpdate(TP_PLUGIN_STATES['light4']['id'], value)

# ----------------------------------------------------------
# -------------- HANDLER DE EVENTS Y ACTIONS ---------------
# ----------------------------------------------------------

# Initial connection handler
@TPClient.on(TP.TYPES.onConnect)
def onConnect(data):
    g_log.info(f"Connected to TP v{data.get('tpVersionString', '?')}, plugin v{data.get('pluginVersion', '?')}.")
    g_log.debug(f"Connection: {data}")
    if settings := data.get('settings'):
        handleSettings(settings, True)

# Settings handler
@TPClient.on(TP.TYPES.onSettingUpdate)
def onSettingUpdate(data):
    g_log.debug(f"Settings: {data}")
    if settings := data.get('values'):
        handleSettings(settings, False)

# Action handler
@TPClient.on(TP.TYPES.onAction)
def onAction(data):
    g_log.debug(f"Action: {data}")

    # check that `data` and `actionId` members exist and save them for later use
    if not (action_data := data.get('data')) or not (aid := data.get('actionId')):
        return

    # Aquí es donde se define lo que hace las acciones como prender o apagar las luces

    if aid == TP_PLUGIN_ACTIONS['turn_on_light']['id']:
        ip_light = TPClient.getActionDataValue(action_data, TP_PLUGIN_ACTIONS['turn_on_light']['data']['ip_light']['id'])

        g_log.info(f"Turning on light {ip_light}")
        os.system("python -m Commands -on -i" + ip_light)
        g_log.info(f"Turning on light {ip_light} Completed")

    elif aid == TP_PLUGIN_ACTIONS['turn_off_light']['id']:
        ip_light = TPClient.getActionDataValue(action_data, TP_PLUGIN_ACTIONS['turn_off_light']['data']['ip_light']['id'])

        g_log.info(f"Turning off light {ip_light}")
        os.system("python -m Commands -off -i" + ip_light)
        g_log.info(f"Turning off light {ip_light} Completed")

    elif aid == TP_PLUGIN_ACTIONS['brightness']['id']:
        ip_light = TPClient.getActionDataValue(action_data, TP_PLUGIN_ACTIONS['brightness']['data']['ip_light']['id'])
        brightness = TPClient.getActionDataValue(action_data, TP_PLUGIN_ACTIONS['brightness']['data']['brightness']['id'])

        # convertir de 0-100% a 1-255
        brightness = int(int(brightness) * 255 / 100)

        g_log.info(f"Setting brightness light {ip_light} to {brightness}")
        os.system("python -m Commands -i " + ip_light + " -b " + str(brightness))
        g_log.info(f"Setting brightness light {ip_light} to {brightness} Completed")

    else:
        g_log.warning("Got unknown action ID: " + aid)

# Shutdown handler
@TPClient.on(TP.TYPES.onShutdown)
def onShutdown(data):
    g_log.info('Received shutdown event from TP Client.')
    # We do not need to disconnect manually because we used `autoClose = True`
    # when constructing TPClient()
    # TPClient.disconnect()

# Error handler
@TPClient.on(TP.TYPES.onError)
def onError(exc):
    g_log.error(f'Error in TP Client event handler: {repr(exc)}')
    # ... do something ?

# ----------------------------------------------------------
# -------------------------- MAIN --------------------------
# ----------------------------------------------------------

def main():
    global TPClient, g_log
    ret = 0  # sys.exit() value

    # handle CLI arguments
    parser = ArgumentParser()
    parser.add_argument("-d", action='store_true',
                        help="Use debug logging.")
    parser.add_argument("-w", action='store_true',
                        help="Only log warnings and errors.")
    parser.add_argument("-q", action='store_true',
                        help="Disable all logging (quiet).")
    parser.add_argument("-l", metavar="<logfile>",
                        help="Log to this file (default is stdout).")
    parser.add_argument("-s", action='store_true',
                        help="If logging to file, also output to stdout.")
    parser.add_argument("--tpstart", action='store_true',
	                    help=APSUPPRESS) # Started by TouchPortal. Do not use interactively.

    opts = parser.parse_args()
    del parser

    # set up logging
    if opts.q:
        # no logging at all
        g_log.addHandler(NullHandler())
    else:
        # set up pretty log formatting (similar to TP format)
        fmt = Formatter(
            fmt="{asctime:s}.{msecs:03.0f} [{levelname:.1s}] [{filename:s}:{lineno:d}] {message:s}",
            datefmt="%H:%M:%S", style="{"
        )
        # set the logging level
        if   opts.d: g_log.setLevel(DEBUG)
        elif opts.w: g_log.setLevel(WARNING)
        else:        g_log.setLevel(INFO)
        # set up log destination (file/stdout)
        if opts.l:
            try:
                # note that this will keep appending to any existing log file
                fh = FileHandler(str(opts.l))
                fh.setFormatter(fmt)
                g_log.addHandler(fh)
            except Exception as e:
                opts.s = True
                print(f"Error while creating file logger, falling back to stdout. {repr(e)}")
        if not opts.l or opts.s:
            sh = StreamHandler(sys.stdout)
            sh.setFormatter(fmt)
            g_log.addHandler(sh)

    # ready to go
    g_log.info(f"Starting {TP_PLUGIN_INFO['name']} v{__version__} on {sys.platform}.")

    try:
        # Connect to Touch Portal desktop application.
        # If connection succeeds, this method will not return (blocks) until the client is disconnected.
        TPClient.connect()
        g_log.info('TP Client closed.')
    except KeyboardInterrupt:
        g_log.warning("Caught keyboard interrupt, exiting.")
    except Exception:
        # This will catch and report any critical exceptions in the base TPClient code,
        # _not_ exceptions in this plugin's event handlers (use onError(), above, for that).
        from traceback import format_exc
        g_log.error(f"Exception in TP Client:\n{format_exc()}")
        ret = -1
    finally:
        # Make sure TP Client is stopped, this will do nothing if it is already disconnected.
        TPClient.disconnect()

    # TP disconnected, clean up.
    del TPClient

    g_log.info(f"{TP_PLUGIN_INFO['name']} stopped.")
    return ret


if __name__ == "__main__":
    sys.exit(main())
