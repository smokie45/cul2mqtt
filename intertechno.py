import logging
log = logging.getLogger( __name__ )
#log.setLevel( logging.DEBUG )
log.setLevel( logging.INFO)

class Switch():
    def __init__(self, topic, itaddr, cul, txQ):
        self.mqtt_topic = topic     # the mqtt topic this switch is listen to
        self.itaddr = itaddr        # the IT address of the switch as HEX ASCII
        self.cul = cul        # reference to serial port of cul
        self.txQ = txQ
        self.state = 'OFF'
        if len(itaddr) == 6:
            self.version = 'v1'     # protocol version, v1=12 bit addr, v3=27bit addr
        else:
            self.version = 'v3'

    def set(self, state):
        # got IT command from switch. Publish to mqtt
        self.state = state
        # publish to mqtt

    def doSwitch(self, state):
        # got switch command by mqtt. Send IT command
        self.state = state
        cmd = self._encode()
        self.txQ.put( cmd )      # add IT cmd to tx queue


    def _encode(self):
        # log.debug("_encode: addr="+str(addr)+", state="+str(state)+" - "+str(type(state)))
        addr = int( self.itaddr, base=16)
        cmd  ="is"              # IT cmd prefix
        n=0
        if self.version == 'v1':
            if self.state == "ON":
                addr |= 0x5
            elif self.state == "OFF":
                addr |= 0x4
            else:
                log.error("Error, unknown state ("+self.state+") to encode! Only 'ON' and 'OFF' supported.")
                return
            bits = f"{addr:024b}"    # convert int to binary string with 24 digits, zero prefixed
            bin2tri = { '00' : '0', '01' : 'F', '10' : 'D', '11' : '1' }
        else:
            if self.state == "ON":     
                addr |= 0x600        # if add state and keep chennel info
            else:
                addr |= 0x500       
            bits = f"{addr:064b}"
            bin2tri = { '00' : 'D', '01' : '0', '10' : '1', '11' : '2'}
        # two bit create a tristate. The mapping is: 00 or 01 is 0, 01 or 10 is f
        while n < len(bits):
            # iter over all bits and replace two with tristate
            t = bits[n:n+2]
            cmd += bin2tri[ t ]
            #print( "n=" + str(n) + ", bits=" + bits[n:n+2]+', cmd='+str(cmd) )
            n += 2
        cmd += '\n'
        cmd = cmd.encode()
        log.debug("IT: addr="+f"{addr:x}"+", state="+str(self.state)+", cmd="+str(cmd))
        return cmd

# A factory to create multiple intertechno.Switch() objects from a given it2mqtt list.
class Factory():
    switchByAddr  = {}
    switchByTopic = {}

    def __init__( self, it2mqtt, txQ ):
        for addr in it2mqtt:
            s = Switch( it2mqtt[ addr ], addr, None, txQ)
            self.switchByAddr[ addr ] = s
            self.switchByTopic[ it2mqtt[addr]] = s

    # update a switch state from received IT message
    def update( self, buf ):
        addr, state = self._decode( buf )
        if addr :
            if addr in self.switchByAddr:
                # the address is configured, set new state
                log.debug("IT: addr known, set new state")
                self.switchByAddr[ addr ].set( state )

    def switch( self, topic, state):
        self.switchByTopic[ topic ].doSwitch( state )

    # TODO: move to Switch
    # decode a byte buffer of IT command.
    # Returns:  string addr - hex address of IT switch or None. For v3 the 8 bit channel is concated to address
    #           string state - ON, OFF or None
    #
    def _decode( self, buf ):
        if  not buf.startswith( b'i'):
            log.debug("rx: no IT message")
            return [None, None]
        if len(buf) == 9:
            x = int(buf[1:7], base=16)      # convert hex encoded buffer to ínt
            state = x & 3                   # mask lower 2 bits
            addr  = x & 0xFFFFF0               # shift values by two bits down = addr
            if state == 0 or state == 3:
                log.debug("rx:ITv1: "+f"{addr:x}"+" -> OFF ("+ f"{state:b}"+")")
                state = 'OFF'
            else:
                log.debug("rx:ITv1: "+f"{addr:x}"+" -> ON  ("+ f"{state:b}"+")")
                state = 'ON'
        else:
            # decode new v3 protocol: 27bit address + 2bit state + 4 bit channel
            # protocol is tristate: 2 bits => 1 bit
            x = int( buf[2:17], base=16)
            state = (x >> 8) & 1
            addr  = x & 0xFFFFFFFFFFFFF0FF
            if state == 1:
                log.debug("rx:ITv3: "+f"{addr:x}"+" -> ON ("+ f"{state:b}"+")")
                state = 'ON'
            else:
                log.debug("rx:ITv3: "+f"{addr:x}"+" -> OFF ("+ f"{state:b}"+")")
                state = 'OFF'

        return [f"{addr:x}", state]

