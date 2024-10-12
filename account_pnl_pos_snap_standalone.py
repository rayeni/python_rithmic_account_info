#!/usr/bin/env python3
'''
Created on September 10, 2024

Author: Rufus Ayeni

Contact: https://github.com/rayeni

Usage: python account_pnl_pos_snap_standalone.py [USERNAME] [PASSWORD] [FCM] [IB] [ACCOUNT_ID]

Example: python account_pnl_pos_snap_standalone.py 00000000-DEMO password123 Ironbeam Ironbeam 999999
'''

import asyncio
import google.protobuf.message
import pathlib
import ssl
import sys
import websockets

from protobuf import account_pnl_position_update_pb2
from protobuf import base_pb2
from protobuf import instrument_pnl_position_update_pb2
from protobuf import request_heartbeat_pb2
from protobuf import request_login_pb2
from protobuf import request_logout_pb2
from protobuf import request_pnl_position_snapshot_pb2
from protobuf import request_rithmic_system_info_pb2
from protobuf import response_login_pb2
from protobuf import response_pnl_position_snapshot_pb2
from protobuf import response_rithmic_system_info_pb2

class PnlPosSnap:
    '''
    Retrieves PnL and position data for an account.
    '''
    
    def __init__(self, uri, system_name, user_id, password, fcm_id, ib_id, account_id):
        # Web socket connection
        self.uri = uri
        # Rithmic System
        self.system_name = system_name
        # Username
        self.user_id = user_id
        # Password
        self.password = password
        # Futures Commission Merchant
        self.fcm_id = fcm_id
        # Introducing Broker
        self.ib_id = ib_id
        # Account name
        self.account_id = account_id
        # Flag to indicate end of response
        self.rp_is_done = False
        # SSL used to connect to Rithmic
        self.ssl_context = None
        # List to hold PnL information
        self.pnl_and_pos_info = []
    
    async def account_pnl_position_update(self, msg_buf):
        '''
        Interpret msg_buf as a AccountPnLPositionUpdate, 451.
        Extract data from msg_buf and place into a list.
        Print contents of list.

        :param msg_buf: bytes
            A binary message sent from Rithmic's PnL plant.
        '''
        

        msg = account_pnl_position_update_pb2.AccountPnLPositionUpdate()
        msg.ParseFromString(msg_buf[4:])

        
        self.pnl_and_pos_info.append(f'Account: {msg.account_id}')
        self.pnl_and_pos_info.append(f'Account Balance: {msg.account_balance}')
        self.pnl_and_pos_info.append(f'Margin Balance: {msg.margin_balance}')
        self.pnl_and_pos_info.append(f'Daily Pnl: {msg.day_pnl}')
        self.pnl_and_pos_info.append('')

        for info in self.pnl_and_pos_info:
            print(info)
        
    async def instrument_pnl_pos_update(self, msg_buf):
        '''
        Interpret msg_buf as a InstrumentPnLPositionUpdate, 450.
        Extract data from msg_buf and place into a list.

        :param msg_buf: bytes
            A binary message sent from Rithmic's PnL plant.
        '''

        msg = instrument_pnl_position_update_pb2.InstrumentPnLPositionUpdate()
        msg.ParseFromString(msg_buf[4:])

        if msg.symbol:
            self.pnl_and_pos_info.append(f'{msg.symbol} number of open positions: {msg.open_position_quantity}')
            self.pnl_and_pos_info.append(f'{msg.symbol} number of closed positions: {msg.closed_position_quantity}')
            self.pnl_and_pos_info.append(f'{msg.symbol} number of long orders filled: {msg.fill_buy_qty}')
            self.pnl_and_pos_info.append(f'{msg.symbol} number of short orders filled: {msg.fill_sell_qty}')
            self.pnl_and_pos_info.append(f'{msg.symbol} open pnl: {msg.day_open_pnl}')
            self.pnl_and_pos_info.append(f'{msg.symbol} closed pnl: {msg.day_closed_pnl}')
            self.pnl_and_pos_info.append(f'{msg.symbol} daily pnl: {msg.day_pnl}')
            self.pnl_and_pos_info.append('')

    async def connect_to_rithmic(self, retry_attempts=3, retry_delay=2):
        '''
        Connects to the specified URI and returns 
        the websocket connection object.
        '''

        attempt = 0
        while attempt < retry_attempts:
            try:
                if "wss://" in self.uri and self.ssl_context is None:
                    self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    localhost_pem = pathlib.Path(__file__).with_name("rithmic_ssl_cert_auth_params")
                    self.ssl_context.load_verify_locations(localhost_pem)

                ws = await websockets.connect(self.uri, ssl=self.ssl_context, ping_interval=3)
                #print(f"DEBUG: connected to {self.uri}")
                return (ws)
            except ConnectionResetError as e:
                print(f"DEBUG: Connection reset by peer, attempt {attempt+1} of {retry_attempts}")
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                attempt += 1
        raise Exception("Failed to connect to Rithmic after several attempts")

    async def send_heartbeat(self, ws):
        '''
        Send a heartbeat request.  

        :param ws: websocket
            Used to send message to Rithmic.
        '''

        rq = request_heartbeat_pb2.RequestHeartbeat()

        rq.template_id = 18

        serialized = rq.SerializeToString()
        length     = len(serialized)
        
        # length into bytes (4 bytes, big/little, true/false)
        buf  = bytearray()
        buf  = length.to_bytes(4, byteorder='big', signed=True)
        buf += serialized

        await ws.send(buf)
        
    async def list_systems(self, ws):
        '''
        Request the list of available Rithmic systems, and wait for
        the response from the server.  After this request is processed by the
        server, the server will initiate the closing of the websocket connection.

        :param ws: websocket
            Used to send and receive message to and from Rithmic.
        '''

        rq = request_rithmic_system_info_pb2.RequestRithmicSystemInfo()

        rq.template_id = 16
        rq.user_msg.append("hello");
        rq.user_msg.append("world");

        serialized = rq.SerializeToString()
        length     = len(serialized)
        
        # length into bytes (4 bytes, big/little, true/false)
        buf  = bytearray()
        buf  = length.to_bytes(4, byteorder='big', signed=True)
        buf += serialized

        await ws.send(buf)
        print(f"sent list_systems request")

        rp_buf = bytearray()
        rp_buf = await ws.recv()

        # get length from first four bytes from rp_buf
        rp_length = int.from_bytes(rp_buf[0:3], byteorder='big', signed=True)

        rp = response_rithmic_system_info_pb2.ResponseRithmicSystemInfo()
        rp.ParseFromString(rp_buf[4:])

        # an rp code of "0" indicates that the request was completed successfully
        if rp.rp_code[0] == "0":
            print(f" Available Systems :")
            print(f" ===================")
            for sys_name in rp.system_name:
                print(f"{sys_name}")
        else:
            print(f" error retrieving system list :")
            print(f" template_id : {rp.template_id}")
            print(f"    user_msg : {rp.user_msg}")
            print(f"     rp code : {rp.rp_code}")
            print(f" system_name : {rp.system_name}")

    # This routine reads data off the wire, occassionally sending heartbeats if
    # there is no traffic.  It will exit after receiving max_num_messages.
    async def consume(self, ws):
        '''
        Read data off the wire, occassionally send heartbeats if
        there is no traffic. It will exit after response is done.

        :param ws: websocket
            Used to receive messages from Rithmic.  
        '''

        # send a heartbeat immediately, just in case
        await self.send_heartbeat(ws)

        max_num_msgs = 100000
        num_msgs = 0

        # After <max_num_msgs>  messages are read or the tick bar response is done,
        # this routine will exit
        while num_msgs < max_num_msgs and not self.rp_is_done:
            
            msg_buf = bytearray()

            waiting_for_msg = True
        
            while waiting_for_msg:
                try:
                    #print(f"waiting for msg ...")
                    msg_buf = await asyncio.wait_for(ws.recv(), timeout=5)
                    waiting_for_msg = False
                except asyncio.TimeoutError:
                    if ws.open:
                        #print(f"sending heartbeat ...")
                        await self.send_heartbeat(ws)
                    else:
                        #print(f"connection appears to be closed.  exiting consume()")
                        return;

            num_msgs += 1

            # get length from first four bytes from msg_buf
            msg_length = int.from_bytes(msg_buf[0:3], byteorder='big', signed=True)

            # parse into base class just to get a template id
            base = base_pb2.Base()
            base.ParseFromString(msg_buf[4:])

            # route msg based on template id
            if base.template_id == 13:
                msg_type = "logout response"
                #print(f" consumed msg : {msg_type} ({base.template_id})")
            
            elif base.template_id == 19:
                msg_type = "heartbeat response"
                #print(f" consumed msg : {msg_type} ({base.template_id})")
            
            elif base.template_id == 403:
                msg_type = "pnl position snapshot response"
                #print(f" consumed msg : {msg_type} ({base.template_id})")
                msg = response_pnl_position_snapshot_pb2.ResponsePnLPositionSnapshot()
                msg.ParseFromString(msg_buf[4:])
                # print(f"")
                # print(f" ResponsePnLPositionSnapshot : ")
                # print(f"                    user_msg : {msg.user_msg}")
                # print(f"                     rp_code : {msg.rp_code}")
                if len(msg.rp_code) > 0:
                    print(f"PnL and Position response is done.")

                    # Set flag to end connection to server
                    self.rp_is_done = True

            elif base.template_id == 450:
                msg_type = "instrument pnl position update"
                #print(f" consumed msg : {msg_type} ({base.template_id})")
                await self.instrument_pnl_pos_update(msg_buf)

            elif base.template_id == 451:
                msg_type = "account pnl position update"
                #print(f" consumed msg : {msg_type} ({base.template_id})")
                await self.account_pnl_position_update(msg_buf)
    
            else:
                msg_type = "unrecognized template id"
                #print(f" consumed msg : {msg_type} ({base.template_id})")

    async def rithmic_login(self, ws, infra_type):
        '''
        Log into the specified Rithmic system using the specified
        credentials.  It will also wait for the login response.

        :param ws: websocket
            Used to send and receive messages to and from Rithmic.
        
        :param infra_type: SysInfraType
            The plant to which you are requesting login.
        '''

        rq = request_login_pb2.RequestLogin()

        rq.template_id      = 10;
        rq.template_version = "3.9"
        rq.user_msg.append("hello")

        rq.user        = self.user_id
        rq.password    = self.password
        rq.app_name    = "CHANGE_ME:account_pnl_pos_snap_standalone.py"
        rq.app_version = "0.1.0.0"
        rq.system_name = self.system_name
        rq.infra_type  = infra_type

        serialized = rq.SerializeToString()
        length     = len(serialized)

        buf  = bytearray()
        buf  = length.to_bytes(4, byteorder = 'big', signed=True)
        buf += serialized

        await ws.send(buf)

        rp_buf = bytearray()
        rp_buf = await ws.recv()

        # get length from first four bytes from rp_buf
        rp_length = int.from_bytes(rp_buf[0:3], byteorder='big', signed=True)

        rp = response_login_pb2.ResponseLogin()
        rp.ParseFromString(rp_buf[4:])

        print(f"")
        print(f"      ResponseLogin :")
        print(f"      ===============")
        print(f"        template_id : {rp.template_id}")
        print(f"   template_version : {rp.template_version}")
        print(f"           user_msg : {rp.user_msg}")
        print(f"            rp code : {rp.rp_code}")
        print(f"             fcm_id : {rp.fcm_id}")
        print(f"             ib_id  : {rp.ib_id}")
        print(f"       country_code : {rp.country_code}")
        print(f"         state_code : {rp.state_code}")
        print(f" heartbeat_interval : {rp.heartbeat_interval}")
        print(f"     unique_user_id : {rp.unique_user_id}")
        print(f"")

    async def position(self, ws):
        '''
        Request position and pnl data.
        Any received messages resulting from this request
        are handled elsewhere (see the consume() routine).
        The message is a snapshot

        :param ws: websocket
            Used to send and receive messages to and from Rithmic.
        '''
        
        rq = request_pnl_position_snapshot_pb2.RequestPnLPositionSnapshot()

        rq.template_id      = 402;
        rq.user_msg.append("hello")

        rq.fcm_id     = self.fcm_id
        rq.ib_id      = self.ib_id
        rq.account_id = self.account_id

        serialized = rq.SerializeToString()
        length     = len(serialized)

        buf  = bytearray()
        buf  = length.to_bytes(4, byteorder='big', signed=True)
        buf += serialized

        await ws.send(buf)

    async def rithmic_logout(self, ws):
        '''
        Send a logout request.  Don't wait for a response.

        :param ws: websocket
            Used to send and receive messages to and from Rithmic.
        '''

        rq = request_logout_pb2.RequestLogout()

        rq.template_id      = 12;
        rq.user_msg.append("hello")

        serialized = rq.SerializeToString()
        length     = len(serialized)

        buf = bytearray()
        buf = length.to_bytes(4, byteorder='big', signed=True)
        buf += serialized

        await ws.send(buf)
 
    async def disconnect_from_rithmic(self, ws):
        '''
        Close the websocket connection. The status code is
        hard-coded to 1000, indicating a normal closure.

        :param ws: websocket
            Used to send and receive messages to and from Rithmic.
        '''
        await ws.close(1000, "see you tomorrow")

    def run(self):
        '''
        Start task to request PnL and position stream.
        '''

        loop = asyncio.get_event_loop()

        if "wss://" in self.uri:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            localhost_pem = pathlib.Path(__file__).with_name("rithmic_ssl_cert_auth_params")
            self.ssl_context.load_verify_locations(localhost_pem)

        ws = loop.run_until_complete(self.connect_to_rithmic())

        loop.run_until_complete(self.rithmic_login(ws, request_login_pb2.RequestLogin.SysInfraType.PNL_PLANT))
        loop.run_until_complete(self.position(ws))
        loop.run_until_complete(self.consume(ws))

        if ws.open:
            #print(f"DEBUG: logging out ...")
            loop.run_until_complete(self.rithmic_logout(ws))
            #print(f"DEBUG: disconnecting ...")
            loop.run_until_complete(self.disconnect_from_rithmic(ws))
            #print(f"DEBUG: done!")
        else:
            print(f"DEBUG: connection appears to be closed. exiting app.")

# Create PnlPosSnap object.
pnl_pos_snap = PnlPosSnap(
    uri='CHANGE_ME', 
    system_name='Rithmic Paper Trading', 
    user_id=sys.argv[1],
    password=sys.argv[2], 
    fcm_id=sys.argv[3],
    ib_id=sys.argv[4],
    account_id=sys.argv[5]
    )

# Execute the object's run function.
pnl_pos_snap.run()
