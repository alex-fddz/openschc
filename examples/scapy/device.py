import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '../../src/')

from scapy.all import *
import scapy.contrib.coap as scapy_coap


import gen_rulemanager as RM
import compr_parser as parser
from compr_core import *
from protocol import SCHCProtocol
from net_sim_sched import SimulScheduler

from gen_utils import dprint, sanitize_value


import sched

import protocol

import pprint
import binascii

import socket
import ipaddress

import time, datetime

coap_options = {'If-Match':1,
            'Uri-Host':3,
            'ETag':4,
            'If-None-Match':5,
            'Observe':6,
            'Uri-Port':7,
            'Location-Path':8,
            'Uri-Path':11,
            'Content-Format':12,
            'Max-Age':14,
            'Uri-Query':15,
            'Accept':17,
            'Location-Query':20,
            'Block2':23,
            'Block1':27,
            'Size2':28,
            'Proxy-Uri':35,
            'Proxy-Scheme':39,
            'Size1':60}

class debug_protocol:
    def _log(*arg):
        print (arg)

parse = parser.Parser(debug_protocol)
rm    = RM.RuleManager()
rm.Add(file="icmp.json")
rm.Print()

comp = Compressor(debug_protocol)
decomp = Decompressor(debug_protocol)

def send_scapy(fields, pkt_bb, rule=None):
    """" Create and send a packet, rule is needed if containing CoAP options to order them
    """ 

    pkt_data = bytearray()
    while (pkt_bb._wpos - pkt_bb._rpos) >= 8:
        octet = pkt_bb.get_bits(nb_bits=8)
        pkt_data.append(octet)

    c = {}
    for k in [T_IPV6_DEV_PREFIX, T_IPV6_DEV_IID, T_IPV6_APP_PREFIX, T_IPV6_APP_IID]:
        v = fields[(k, 1)][0]
        if type(v) == bytes:
            c[k] = int.from_bytes(v, "big")
        elif type(v) == int:
            c[k] = v
        else:
            raise ValueError ("Type not supported")
        
    
    IPv6Src = (c[T_IPV6_DEV_PREFIX] <<64) + c[T_IPV6_DEV_IID]
    IPv6Dst = (c[T_IPV6_APP_PREFIX] <<64) + c[T_IPV6_APP_IID]

    
    IPv6Sstr = ipaddress.IPv6Address(IPv6Src)
    IPv6Dstr = ipaddress.IPv6Address(IPv6Dst)
    
    IPv6Header = IPv6 (
        version= fields[(T_IPV6_VER, 1)][0],
        tc     = fields[(T_IPV6_TC, 1)][0],
        fl     = fields[(T_IPV6_FL, 1)][0],
        nh     = fields[(T_IPV6_NXT, 1)][0],
        hlim   = fields[(T_IPV6_HOP_LMT, 1)][0],
        src    =IPv6Sstr.compressed, 
        dst    =IPv6Dstr.compressed
    ) 

    if fields[(T_IPV6_NXT, 1)][0] == 58: #IPv6 /  ICMPv6
        ICMPv6Header = ICMPv6EchoReply(
            id = fields[(T_ICMPV6_IDENT, 1)][0],
            seq =  fields[(T_ICMPV6_SEQNO, 1)][0],
            data = pkt_data
        )

        full_header = IPv6Header/ICMPv6Header
    elif fields[(T_IPV6_NXT, 1)][0] == 17: # IPv6 / UDP
        UDPHeader = UDP (
            sport = fields[(T_UDP_DEV_PORT, 1)][0],
            dport = fields[(T_UDP_APP_PORT, 1)][0]
            )
        if (T_COAP_VERSION, 1) in fields: # IPv6 / UDP / COAP
            print ("CoAP Inside")

            b1 = (fields[(T_COAP_VERSION, 1)][0] << 6)|(fields[(T_COAP_TYPE, 1)][0]<<4)|(fields[(T_COAP_TKL, 1)][0])
            coap_h = struct.pack("!BBH", b1, fields[(T_COAP_CODE, 1)][0], fields[(T_COAP_MID, 1)][0])

            tkl = fields[(T_COAP_TKL, 1)][0]
            if tkl != 0:
                token = fields[(T_COAP_TOKEN, 1)][0]
                for i in range(tkl-1, -1, -1):
                    bt = (token & (0xFF << 8*i)) >> 8*i
                    coap_h += struct.pack("!B", bt)

            delta_t = 0
            comp_rule = rule[T_COMP] # look into the rule to find options 
            for idx in range(0, len(comp_rule)):
                if comp_rule[idx][T_FID] == T_COAP_MID:
                    break

            idx += 1 # after MID is there TOKEN
            if idx < len(comp_rule) and comp_rule[idx][T_FID] == T_COAP_TOKEN:
                print ("skip token")
                idx += 1

            for idx2 in range (idx, len(comp_rule)):
                print (comp_rule[idx2])
                opt_name = comp_rule[idx2][T_FID].replace("COAP.", "")
                
                delta_t = coap_options[opt_name] - delta_t
                print (delta_t)

                if delta_t < 13:
                    dt = delta_t
                else:
                    dt = 13
                    
                opt_len = fields[(comp_rule[idx2][T_FID], comp_rule[idx2][T_FP])][1] // 8
                opt_val = fields[(comp_rule[idx2][T_FID], comp_rule[idx2][T_FP])][0]
                print (opt_len, opt_val)

                if opt_len < 13:
                    ol = opt_len
                else:
                    ol = 13
                    
                coap_h += struct.pack("!B", (dt <<4) | ol)

                if dt == 13:
                    coap_h += struct.pack("!B", delta_t - 13)

                if ol == 13:
                    coap_h += struct.pack("!B", opt_len - 13)


                for i in range (0, opt_len):
                    print (i)
                    if type(opt_val) == str:
                        coap_h += struct.pack("!B", ord(opt_val[i]))
                    elif type(opt_val) == int:
                        v = (opt_val & (0xFF << (opt_len - i - 1))) >> (opt_len - i - 1)
                        coap_h += struct.pack("!B", v)

            if len(pkt_data) > 0:
                coap_h += b'\xff'
                coap_h += pkt_data

                    
            print (binascii.hexlify(coap_h))

            full_header = IPv6Header / UDPHeader / Raw(load=coap_h)
            pass
        else: # IPv6/UDP
            full_header = IPv6Header / UDPHeader / Raw(load=pkt_data)
    else: # IPv6 only
        full_header= IPv6Header / Raw(load=pkt_data)
        

    full_header.show()

    send(full_header, iface="he-ipv6")

event_queue = []



scheduler = SimulScheduler()

class ScapyUpperLayer:
    def __init__(self):
        self.protocol = None

    # ----- AbstractUpperLayer interface (see: architecture.py)
    
    def _set_protocol(self, protocol):
        self.protocol = protocol

    def recv_packet(self, address, raw_packet):
        raise NotImplementedError("XXX:to be implemented")

    # ----- end AbstractUpperLayer interface

    def send_later(self, delay, udp_dst, packet):
        assert self.protocol is not None
        scheduler = self.protocol.get_system().get_scheduler()
        scheduler.add_event(delay, self._send_now, (udp_dst, packet))

    def _send_now(self, packet):
        #dst_address = address_to_string(udp_dst)
        self.protocol.schc_send(packet)

# --------------------------------------------------        

class ScapyLowerLayer:
    def __init__(self, position, socket=None, other_end=None):
        self.protocol = None
        self.position = position
        self.other_end = other_end
        self.sock = socket

    # ----- AbstractLowerLayer interface (see: architecture.py)
        
    def _set_protocol(self, protocol):
        self.protocol = protocol
        self._actual_init()

    def send_packet(self, packet, dest, transmit_callback=None):
        print("SENDING", packet, dest)            

        if dest.find("udp") == 0:
            if self.position == T_POSITION_CORE:
                destination = (dest.split(":")[1], int(dest.split(":")[2]))
            else:
                destination = other_end

            print (destination)
            hexdump(packet)
            self.sock.sendto(packet, destination)

        print ("L2 send_packet", transmit_callback)
        if transmit_callback is not None:
            print ("do callback", transmit_callback)
            transmit_callback(1)
        else:
            print ("c'est None")

    def get_mtu_size(self):
        return 72 # XXX

    # ----- end AbstractLowerLayer interface

    def _actual_init(self):
        pass

    def event_packet_received(self):
        """Called but the SelectScheduler when an UDP packet is received"""
        packet, address = self.sd.recvfrom(MAX_PACKET_SIZE)
        sender_address = address_to_string(address)
        self.protocol.schc_recv(sender_address, packet)


class ScapyScheduler:
    def __init__(self):
        self.queue = []
        self.clock = 0
        self.next_event_id = 0
        self.current_event_id = None
        self.observer = None
        self.item=0
        self.fd_callback_table = {}
        self.last_show = 0 

    # ----- AbstractScheduler Interface (see: architecture.py)

    def get_clock(self):
        return time.time()
         
    def add_event(self, rel_time, callback, args):
        dprint("Add event {}".format(sanitize_value(self.queue)))
        dprint("callback set -> {}".format(callback.__name__))
        assert rel_time >= 0
        event_id = self.next_event_id
        self.next_event_id += 1
        clock = self.get_clock()
        abs_time = clock+rel_time
        self.queue.append((abs_time, event_id, callback, args))
        print ("QUEUE apppended ", len(self.queue), (abs_time, event_id, callback, args))

        print (self.queue)
        return event_id

    def cancel_event(self, event):
        print ("remove event", event)

        item_pos = 0
        item_found = False
        for q in self.queue:
            if q[1] == event:
                item_found = True
                break
            item_pos += 1

        if item_found:
            print ("item found", item_pos)
            elm = self.queue.pop(item_pos)
            print (self.queue)

        return elm

    # ----- Additional methods

    def _sleep(self, delay):
        """Implements a delayfunc for sched.scheduler
        This delayfunc sleeps for `delay` seconds at most (in real-time,
        but if any event appears in the fd_table (e.g. packet arrival),
        the associated callbacks are called and the wait is stop.
        """
        self.wait_one_callback_until(delay)


    def wait_one_callback_until(self, max_delay):
        """Wait at most `max_delay` second, for available input (e.g. packet).
        If so, all associated callbacks are run until there is no input.
        """
        fd_list = list(sorted(self.fd_callback_table.keys()))
        print (fd_list)
        while True:
            rlist, unused, unused = select.select(fd_list, [], [], max_delay)
            if len(rlist) == 0:
                break
            for fd in rlist:
                callback, args = self.fd_callback_table[fd]
                callback(*args)
            # note that sched impl. allows to return before sleeping `delay`

    def add_fd_callback(self, fd, callback, args):
        assert fd not in self.fd_callback_table
        self.fd_callback_table[fd] = (callback, args)

    def run(self):
        factor= 10
        if self.item % factor == 0:
            seq = ["|", "/", "-", "\\", "-"]
            print ("{:s}".format(seq[(self.item//factor)%len(seq)]),end="\b", flush=True)
        self.item +=1

        if time.time() - self.last_show > 60: # display the event queue every minute
            print ("*"*40)
            print ("EVENT QUEUE")
            self.last_show = time.time()
            for q in self.queue:
                print ("{0:6.2f}: id.{1:04d}".format(q[0]-time.time(), q[1]), q[2])
            print ("*"*40)


        while len(self.queue) > 0:
            self.queue.sort()

            wake_up_time = self.queue[0][0]
            if time.time() < wake_up_time:
                return

            event_info = self.queue.pop(0)
            self.clock, event_id, callback, args = event_info
            self.current_event_id = event_id
            if self.observer is not None:
                self.observer("sched-pre-event", event_info)
            callback(*args)
            if self.observer is not None:
                self.observer("sched-post-event", event_info)
            dprint("Queue running event -> {}, callback -> {}".format(event_id, callback.__name__))

# --------------------------------------------------        

class ScapySystem:
    def __init__(self):
        self.scheduler = ScapyScheduler()

    def get_scheduler(self):
        return self.scheduler

    def log(self, name, message):
        print(name, message)

# --------------------------------------------------

    
def send_tunnel(pkt, dest):
    print ("send tunnel")
    print (dest, pkt)
    print (pkt.display())


def processPkt(pkt):
    global parser
    global rm
    global event_queue
    global SCHC_machine
    

    scheduler.run()

    # look for a tunneled SCHC pkt

    if pkt.getlayer(Ether) != None: #HE tunnel do not have Ethernet
        e_type = pkt.getlayer(Ether).type
        if e_type == 0x0800:
            ip_proto = pkt.getlayer(IP).proto
            if ip_proto == 17:
                udp_dport = pkt.getlayer(UDP).dport
                if udp_dport == socket_port: # tunnel SCHC msg to be decompressed
                    print ("tunneled SCHC msg")
                    
                    schc_pkt, addr = tunnel.recvfrom(2000)
                    r = schc_protocol.schc_recv(device_id, schc_pkt)
                    print (r)

        
    elif IP in pkt and pkt.getlayer(IP).version == 6 : # regular IPv6trafic to be compression
        schc_protocol.schc_send(bytes(pkt))
        # pkt_fields, data, err = parse.parse( bytes(pkt), T_DIR_DW, layers=["IP", "ICMP"], start="IPv6")
        # print (pkt_fields)

        # if pkt_fields != None:
            # rule, device = rm.FindRuleFromPacket(pkt_fields, direction=T_DIR_DW, failed_field=True)
            # if rule != None:
            #     schc_pkt = comp.compress(rule, pkt_fields, data, T_DIR_DW)
            #     if device.find("udp") == 0:
            #         destination = (device.split(":")[1], int(device.split(":")[2]))
            #         print (destination)
            #         schc_pkt.display()
            #         if len(schc_pkt._content) > 12:
            #             hexdump(schc_pkt._content)
            #             send_frag(schc_pkt, mtu_in_bytes=12, sock=tunnel, dest=destination)
            #         else: 
            #             tunnel.sendto(schc_pkt._content, destination)
            #     else:
            #         print ("unknown connector" + device)
      
                    
        
# look at the IP address to define sniff behavior


POSITION = T_POSITION_DEVICE

if POSITION==T_POSITION_DEVICE:
    device_id = "udp:83.199.24.39:8888"
    socket_port = 8888
    other_end = ("tests.openschc.net", 0x5C4C)
elif POSITION==T_POSITION_CORE:
    pass
else:
    print ("not a good position")


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    ip_addr = s.getsockname()[0]

tunnel = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tunnel.bind(("0.0.0.0", socket_port))



config = {}
upper_layer = ScapyUpperLayer()
lower_layer = ScapyLowerLayer(position=POSITION, socket=tunnel, other_end=other_end)
system = ScapySystem()
scheduler = system.get_scheduler()
schc_protocol = protocol.SCHCProtocol( # rename into SCHC_machine 
    config=config, system=system, 
    layer2=lower_layer, layer3=upper_layer, 
    role=POSITION, unique_peer=False)
schc_protocol.set_position(POSITION)
schc_protocol.set_rulemanager(rm)


sniff(prn=processPkt, iface=[ "en0"])


 
