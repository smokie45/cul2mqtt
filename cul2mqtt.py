#!/bin/python
#
# Small program to read data received from CUL stick on 433Mhz
# TODO: add install to /usr/local/[bin, lib/python3.8/culmqtt]
#
import asyncio
import serial_asyncio
import serial, time
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import logging
import sys
import queue
import intertechno
import argparse

# PORT        = '/dev/ttyUSB0'
PORT        = '/dev/culstick'
BAUDRATE    = 38400
MQTT_SERVER = "192.168.0.90"
MQTT_PORT   = 1883

async def main():
    try:
        reader, writer = await serial_asyncio.open_serial_connection(url=PORT, baudrate=BAUDRATE)
    except IOError:
        log.error( "Can not open " + PORT )
        exit("Cannot open " + PORT)
    # messages = [b'V\n',b'X01\n']
    txQ.put( b'V\n' )
    txQ.put( b'X01\n' )
    txQ.put( b'it360\n' )
    sender = send( writer )
    receiver = recv(reader)

    print("Start receiving from " + PORT )
    await asyncio.gather( send(writer), recv(reader) )

async def send( w ):
    while True:
        try:
            cmd = txQ.get_nowait()
        except queue.Empty:
            cmd = None
            pass
        if cmd:
            w.write( cmd )
            log.debug( 'tx::raw: ' + str(cmd) )
        await asyncio.sleep(0.5)

async def recv( r ):
    state = 'run'
    while True:
        msg = await r.readuntil(b'\n')
        if state != 'run':
            print('Done receiving')
            break
        log.debug( 'rx::raw: ' +str(msg) )
        it.update(  msg )

def on_mqtt( client, userdata, msg ):
    log.debug("on_mqtt: '"+msg.topic+"' -> '" + str(msg.payload) +"'")
    it.switch( msg.topic, msg.payload.decode() )

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("connected to mqtt server")
        client.isConnected = True
    else:
        log.error("on_connect: failed to connect to mqtt server")

def on_subscribe( client, userdata, mid, granted_qos):
    log.debug("on_subscribe:")

def on_log( client, userdata, level, buf):
    if "PING" not in buf:
        log.debug("on_log: " + buf)

my_parser = argparse.ArgumentParser(description='Talk to CUL stick on ttyUSB and publish to MQTT server')

my_parser.add_argument('--port',
                       required=False,
                       type=str,
                       default="/dev/culstick",
                       help='Path to serial port device')
my_parser.add_argument('--log',
                       required=False,
                       type=str,
                       default="ERROR",
                       help='Set loglevel to [DEBUG, INFO, ..]')
args = my_parser.parse_args()
PORT = args.port

# get name of program. Remove prefixed path and postfixed fileytpe
myName = sys.argv[0]
myName = myName[ myName.rfind('/')+1: ]
myName = myName[ : myName.find('.')]
print("Started " + myName + " using " + PORT)

logging.basicConfig(
    format='%(levelname)7s: %(message)s',
    level = getattr(logging, args.log.upper()),
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.handlers.RotatingFileHandler('/tmp/'+myName+'.log',
                                             # maxBytes=2000,
                                             # backupCount=1)
    ]
)
log = logging.getLogger( __name__ )

state='stop'

IT2MQTT = { '151550' : '/IT/Switch1', '154550' : '/IT/Switch2', \
            '155150' : '/IT/Switch3', '155550' : '/IT/Switch4', \
            '5A9A6A5A55555056' : '/IT/Switch11', '5A9A6A5A55555059' : '/IT/Switch12', \
            '5A9A6A5A5555505A' : '/IT/Switch13', '5A9A6A5A55555065' : '/IT/Switch14', \
            '504010' : '/IT/Window' }
txQ = queue.Queue()
it = intertechno.Factory( IT2MQTT, txQ )

# create mqtt client
mqttC = mqtt.Client( client_id = myName )
mqttC.isConnected = False
mqttC.on_connect = on_connect
mqttC.on_message = on_mqtt
mqttC.on_subscribe = on_subscribe
mqttC.on_log = on_log
mqttC.loop_start()        # create rx/tx thread in background
try:
    mqttC.connect( MQTT_SERVER, MQTT_PORT, 10)
except:
    log.error("Failed to connect to mqtt server. Retry in 2 secs ....")
while not mqttC.isConnected:
        time.sleep(1)           # wait till mqtt server arrives.

for t in IT2MQTT:
    mqttC.subscribe( IT2MQTT[t], 0 )
    log.info('subscribed to mqtt: ' + IT2MQTT[t] )

try:
    asyncio.run( main() )
except KeyboardInterrupt:
    state='stop'
    time.sleep(2)
    loop.stop()
    mqttC.loop_stop()
    mqttC.disconnect()
    print("Terminated")
