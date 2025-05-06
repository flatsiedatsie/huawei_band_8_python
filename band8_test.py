import os
import sys
# This helps the addon find python libraries it comes with, which are stored in the "lib" folder. The "package.sh" file will download Python libraries that are mentioned in requirements.txt and place them there.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')) 

import time

import asyncio
import base64
import enum
import logging
import platform
from configparser import ConfigParser
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional, Tuple

from bleak import BleakClient

from huawei.protocol import (
    GATT_READ,
    GATT_WRITE,
    Command,
    Packet,
    check_result,
    generate_nonce,
    hexlify,
    initialization_vector,
)
from huawei.services import device_config, fitness, locale_config, notification
from huawei.services.notification import NotificationType

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEVICE_NAME = "default"
CONFIG_FILE = Path("band.ini")


@enum.unique
class BandState(enum.IntEnum):
    Connected = enum.auto()

    RequestedLinkParams = enum.auto()
    ReceivedLinkParams = enum.auto()
    RequestedAuthentication = enum.auto()
    ReceivedAuthentication = enum.auto()
    RequestedBondParams = enum.auto()
    ReceivedBondParams = enum.auto()
    RequestedBond = enum.auto()
    ReceivedBond = enum.auto()

    RequestedAck = enum.auto()
    Ready = enum.auto()

    Disconnected = enum.auto()


class Band:
    def __init__(self, loop, client: BleakClient, client_mac: str, device_mac: str, key: bytes):
        self.state: BandState = BandState.Disconnected

        self.client: BleakClient = client
        self.loop = loop

        self.client_mac: str = client_mac
        self.device_mac: str = device_mac
        self.client_serial: str = client_mac.replace(":", "")[-6:]  # android.os.Build.SERIAL

        self._key: bytes = key
        self._server_nonce: Optional[bytes] = None
        self._client_nonce: bytes = generate_nonce()
        self._encryption_counter: int = 0

        self.link_params: Optional[device_config.LinkParams] = None

        self.bond_status: Optional[int] = None
        self.bond_status_info: Optional[int] = None
        self.bt_version: Optional[int] = None

        self._packet: Optional[Packet] = None
        self._event = asyncio.Event()
        self.__message_id: int = -1
        
        self._expected_service_id = None
        self._expected_command_id = None
        self._events = {}
        
        self.sent_sync_response = False
        self.sent_sync_response2 = False
        self.received_music_message = False
        self.retried_auth = False

    @property
    def _credentials(self):
        self._encryption_counter, iv = initialization_vector(self._encryption_counter)
        return {"key": self._key, "iv": iv}

    @property
    def _message_id(self) -> int:
        if self.__message_id < 256:
            self.__message_id += 1
        else:
            self.__message_id = 0
        return self.__message_id

    async def _send_data(self, packet: Packet, new_state: BandState):
        print("band -> _send_data. packet: ", packet)
        print("band -> _send_data. new_state: ", new_state)
        print("band -> _send_data. self.state: ", self.state)
        #assert not self.state.name.startswith("Requested"), f"tried to send while waiting for response: {self.state}"

        data = bytes(packet)
        logger.debug(f"Request packet: {packet}")
        logger.debug(f"Current state: {self.state}, target state: {new_state}, sending: {hexlify(data)}")
        
        if new_state:
            self.state = new_state
        await self.client.write_gatt_char(GATT_WRITE, bytearray(data))

    async def _receive_data(self, sender: int, data: bytes):
        print("\n\n[...]\nband -> _receive_data. sender: ", sender)
        #print("band -> _receive_data: self.state.name: ", self.state.name)
        
        try:
            
            logger.debug(f"Current state: {self.state}, received from '{sender}': {hexlify(bytes(data))}")
            #self._packet = Packet.from_bytes(data)
            _received_packet = Packet.from_bytes(data)
            logger.debug(f"band -> _receive_data: Parsed response packet: \n{_received_packet}\n")
            
            print(" ) ) )  _received_packet.command: ", _received_packet.command)
            
            event_key = str(_received_packet.service_id) + '-' + str(_received_packet.command_id)
            print("band -> _receive_data: event_key: ", event_key)
            
            await asyncio.sleep(0.5)
            
            if event_key in self._events.keys():
                print("\nband -> _receive_data: FOUND IT. Likely calling a function next.\n")
            
                try:
                    
                    
                    
                    
                    self._events[event_key]['f'](_received_packet.command)
                    #result = func(self._packet.command)

                    self.state, self._packet = self._events[event_key]['target_state'], None
                    logger.debug(f"receive_data: current state: {self.state}")
            
                    if event_key == '1-1':
                        print("\ntrying anticipated band.handshake_part2")
                        await asyncio.sleep(1)
                        await self.handshake_part2()
                        #await self.handshake_part1()
                        
                        
                
                    elif event_key == '1-8':
                        print("\nreceived battery level")
                
                        #await self.handshake_part1()
                
                    elif event_key == '1-15':
                        print("received response for 1-15 - received the bond parameters")
                        #await self.handshake_part2()
                        await asyncio.sleep(1)
                        print("\ntrying anticipated band.handshake_part4")
                        await self.handshake_part4()
                     
                     
                
                    elif event_key == '1-61':
                        print("received a 1-61 message. Ignoring for now..")
                        #print("\ntrying anticipated band.handshake_part3")
                        #await self.handshake_part3()
                        
                        
                    
                    elif event_key == '55-1':
                        print("received an anticipated sync message")
                        #await self.sync_respond()
            
                    else:
                        print("UNIMPLEMENTED EVENT KEY: ", event_key)
                    
                    
                except Exception as ex:
                    print("caught error in _receive_data: ", ex)
                    
                    if self.retried_auth == False:
                        self.retried_auth = True
                        await asyncio.sleep(1)
                        await self.handshake_part2()
                    
                
        
        
        
            elif event_key == '37-3':
                    print("received an unrequested music control message")
                    #await self.sync_respond()
                    
                    #device_config._process_authentication()
                    
                    if self.received_music_message == False:
                        self.received_music_message = True
                        await asyncio.sleep(5)
                        await self.handshake_part3()
                    else:
                        print("received another unexpected music control message")
        
            elif event_key == '55-1':
                    print("received an unrequested sync message, responding")
                    await self.sync_respond()
        
            elif event_key == '1-61':
                 print("received an unrequested 1-61 (unkown use - maybe authentification response?)")
                 #print("\ntrying band.handshake_part3")
                 #await self.handshake_part3()
                 
                 self._process_authentication(_received_packet.command)
                 await self.sync_respond2()
                 
        
            """
            #assert self.state.name.startswith("Requested"), "unexpected packet"
            if self._expected_service_id and self._expected_service_id != _received_packet.service_id:
            
                print("\n\nEH?\nreceived a packet with unexpected service ID. Expected", self._expected_service_id, " , got: ", _received_packet.service_id)
            
                #self.loop.call_soon_threadsafe(self._event.set)
            
                self._packet = None
            
            
                #await self._event.wait()
                #self.loop.call_soon_threadsafe(self._event.wait)
            
                #print("_process_response: EVENT.WAIT DONE")
                #self._event.clear()
            
            else:
                print("packet service ID matches with what was expected: ", self._expected_service_id)
            
                self._packet = _received_packet
            
                print("self._packet.command_id: ", self._packet.command_id)
                print("=?=")
                print("self._expected_command_id: ", self._expected_command_id)
                #if self._packet.service_id != 37:

                #self.loop.call_soon_threadsafe(self._event.set)

            """
            
        except Exception as ex:
            print("\n!!!\nCAUGHT GENERAL ERROR in _receive_data: ", ex)
        
        

    async def _process_response_yo(self, request: Packet, func: Callable, new_state: BandState):
        print("\nband ->  _process_response_YO!!")
        self._expected_service_id = request.service_id
        self._expected_command_id = request.command_id
        logger.debug(f"Waiting for response from service_id={request.service_id}, command_id={request.command_id}...")
        
        
        await self._event.wait()
        print("_process_response: EVENT.WAIT DONE")
        self._event.clear()

        #assert (self._packet.service_id, self._packet.command_id) == (request.service_id, request.command_id)
        
        print("SAME SAME? ", (self._packet.service_id, self._packet.command_id) == (request.service_id, request.command_id))
        
        result = func(self._packet.command)

        self.state, self._packet = new_state, None
        logger.debug(f"Response processed, attained requested state: {self.state}")

        return result

    
    async def _process_response(self, request: Packet, func: Callable, new_state: BandState):
        print("\nWARNING!\nband ->  _process_response")
        self._expected_service_id = request.service_id
        self._expected_command_id = request.command_id
        logger.debug(f"Waiting for response from service_id={request.service_id}, command_id={request.command_id}...")
        
        await self._event.wait()
        print("_process_response: EVENT.WAIT DONE")
        self._event.clear()

        #assert (self._packet.service_id, self._packet.command_id) == (request.service_id, request.command_id)
        
        print("SAME SAME? ", (self._packet.service_id, self._packet.command_id) == (request.service_id, request.command_id))
        
        result = func(self._packet.command)

        self.state, self._packet = new_state, None
        logger.debug(f"Response processed, attained requested state: {self.state}")

        return result

    
    
    async def sync_respond(self):
        print("in sync_respond")
        
        if self.sent_sync_response == False:
            self.sent_sync_response = True
            
            #await asyncio.sleep(1)
        
            request = device_config.reply_ok(
                self.link_params.auth_version,
                self.client_serial,
                self.device_mac,
                **self._credentials,
            )
            await self._send_data(request,None)
            print("sync response sent")
        
    async def sync_respond2(self):
        print("in sync_respond 2")
        
        if self.sent_sync_response2 == False:
            self.sent_sync_response2 = True
            
            #await asyncio.sleep(1)
        
            request = device_config.reply_ok2(
                self.link_params.auth_version,
                self.client_serial,
                self.device_mac,
                **self._credentials,
            )
            await self._send_data(request,None)
            print("sync response 2 sent")
        

    async def _transact(self, request: Packet, func: Callable, states: Optional[Tuple[BandState, BandState]] = None):
        print("\nWARNING\nband -> transact")
        source_state, target_state = states if states is not None else (BandState.RequestedAck, BandState.Ready)
        await self._send_data(request, source_state)
        #self._events[str(request.service_id) + '-' + str(request.command_id)] = {'r':request,'source_state':source_state,'target_state':target_state,'f':func}
        return await self._process_response(request, func, target_state)

    async def _shout(self, request: Packet, func: Callable, states: Optional[Tuple[BandState, BandState]] = None):
        print("band -> shout")
        source_state, target_state = states if states is not None else (BandState.RequestedAck, BandState.Ready)
        await self._send_data(request, source_state)
        self._events[str(request.service_id) + '-' + str(request.command_id)] = {'r':request,'source_state':source_state,'target_state':target_state,'f':func}
        #return await self._process_response(request, func, target_state)
        #await self._event.wait()
        #print("_process_response: EVENT.WAIT DONE")
        #self._event.clear()



    async def connect(self):
        print("band -> connect")
        if not self.client.is_connected:
            print("self.connect: not connected, so attempting to connect with client")
            await self.client.connect()
        await self.client.start_notify(GATT_READ, self._receive_data)
        self.state = BandState.Connected
        logger.info(f"Connected to band, current state: {self.state}")
        
        await asyncio.sleep(0.5)
        
        print("going from connect to trying a handshake")
        await self.handshake_part1()
        
        

    async def disconnect(self):
        print("\nband -> DISCONNECT\n")
        self.state = BandState.Disconnected
        await asyncio.sleep(0.5)
        await self.client.stop_notify(GATT_READ)
        await self.client.disconnect()
        logger.info(f"Stopped notifications, current state: {self.state}")




    async def handshake_part1(self):
        print("band ->  handshake. self.link_params: ", self.link_params)
        
        request = device_config.request_link_params()
        print("\nhandshake: got link_params?  BandState: ", BandState)
        
        print("handshake: self.link_params: ", self.link_params)
        
        states = (BandState.RequestedLinkParams, BandState.ReceivedLinkParams)
        print("\nhandshake: states: ", states)
        
        #await self._transact(request, self._process_link_params, states)
        await self._shout(request, self._process_link_params, states)

        #if self.link_params:
        #    print("forcing auth_version 3")
        #    self.link_params.auth_version = 3
        
        
        
        """
        request = device_config.request_bond_params(self.client_serial, self.client_mac)
        states = (BandState.RequestedBondParams, BandState.ReceivedBondParams)
        await self._transact(request, self._process_bond_params, states)

        # TODO: not needed if status is already correct
        request = device_config.request_bond(
            self.link_params.auth_version,
            self.client_serial,
            self.device_mac,
            **self._credentials,
        )
        states = (BandState.RequestedBond, BandState.ReceivedBond)
        await self._transact(request, self._process_bond, states)

        self.state = BandState.Ready
        logger.info(f"Handshake completed, current state: {self.state}")
        """
        
        
        
    async def handshake_part2(self):
        print("handshake_part2: self.link_params: ", self.link_params)
        print("handshake_part2: requesting authentication")
        request = device_config.request_authentication(
            self.link_params.auth_version,
            self._client_nonce,
            self._server_nonce,
        )
        states = (BandState.RequestedAuthentication, BandState.ReceivedAuthentication)
        
        print("HANDSHAKE_part2: HALFWAY STATES: ", states)
        await self._shout(request, self._process_authentication, states)
        #await self._shout(request, device_config._process_authentication, states)
        print("\nsent handshake part2 (request auth)\n\n\n\n+\n\n")


    async def handshake_part3(self):
        print("\nin handshake_part3 (trying to get process_bond_params)")
        request = device_config.request_bond_params(self.client_serial, self.client_mac)
        states = (BandState.RequestedBondParams, BandState.ReceivedBondParams)
        await self._shout(request, self._process_bond_params, states)
        print("\nsent handshake part3 (get process_bond_params)\n\n\n\n+ +\n\n")


    async def handshake_part4(self):
        print("\nin handshake_part4 - requesting bond")
        
        # TODO: not needed if status is already correct
        request = device_config.request_bond(
            self.link_params.auth_version,
            self.client_serial,
            self.device_mac,
            **self._credentials,
        )
        states = (BandState.RequestedBond, BandState.ReceivedBond)
        await self._shout(request, self._process_bond, states)

        self.state = BandState.Ready
        logger.info(f"Handshake completed, current state: {self.state}")
        print("\n\nBOND MADE\n\n")
        

    @check_result
    async def factory_reset(self):
        print("in factory_reset")
        request = device_config.factory_reset(**self._credentials)
        return await self._transact(request, lambda _: _)

    async def get_product_info(self):
        print("in get_product_info")
        request = device_config.request_product_info(**self._credentials)
        result = await self._transact(request, lambda _: _)
        logger.info(result)

    async def get_battery_level(self) -> int:
        print("in get_battery_level")
        request = device_config.request_battery_level(**self._credentials)
        return await self._shout(request, device_config.process_battery_level)

    @check_result
    async def set_date_format(self, date_format: device_config.DateFormat, time_format: device_config.TimeFormat):
        print("in set_date_format")
        request = device_config.set_date_format(date_format, time_format, **self._credentials)
        return await self._transact(request, lambda _: _)

    @check_result
    async def set_time(self):
        print("in set_time")
        request = device_config.set_time(datetime.now(), **self._credentials)
        return await self._transact(request, lambda _: _)

    async def set_rotation_actions(self, activate: bool = True, navigate: bool = False):
        @check_result
        async def set_status(func, state):
            request = func(state, **self._credentials)
            return await self._transact(request, lambda _: _)

        await set_status(device_config.set_activate_on_rotate, activate)
        await set_status(device_config.set_navigate_on_rotate, navigate)

    @check_result
    async def set_right_wrist(self, state: bool):
        request = device_config.set_right_wrist(state, **self._credentials)
        return await self._transact(request, lambda _: _)

    @check_result
    async def set_locale(self, language_tag: str, measurement_system: int):
        request = locale_config.set_locale(language_tag, measurement_system, **self._credentials)
        return await self._transact(request, lambda _: _)

    @check_result
    async def set_user_info(self, height: int, weight: int, sex: fitness.Sex, birth_date: date):
        print("in set_user_info")
        request = fitness.set_user_info(height, weight, sex, birth_date, **self._credentials)
        return await self._transact(request, lambda _: _)

    async def get_today_totals(self):
        print("in get_today_totals")
        request = fitness.request_today_totals(**self._credentials)
        return await self._transact(request, fitness.process_today_totals)

    @check_result
    async def enable_trusleep(self, state: bool):
        print("in trusleep")
        request = fitness.enable_trusleep(state, **self._credentials)
        return await self._transact(request, lambda _: _)

    @check_result
    async def enable_heart_rate_monitoring(self, state: bool):
        print("in enable_heart_rate_monitoring")
        request = fitness.enable_heart_rate_monitoring(state, **self._credentials)
        return await self._transact(request, lambda _: _)

    @check_result
    async def send_notification(
        self,
        text: str,
        title: Optional[str] = None,
        vibrate: bool = False,
        notification_type: NotificationType = NotificationType.Generic,
    ):
        return await self._transact(
            notification.send_notification(
                self._message_id,
                text,
                title,
                vibrate,
                notification_type,
                **self._credentials,
            ),
            lambda _: _,
        )

    def _process_link_params(self, command: Command):
        print(" in _process_link_params. ", self.state, BandState.RequestedAuthentication)
        #assert self.state == BandState.RequestedLinkParams, "bad state"
        self.link_params, self._server_nonce = device_config.process_link_params(command)

    def _process_authentication(self, command: Command):
        print(" in _process_authentication. ", self.state, BandState.RequestedAuthentication)
        print(" _process_authentication: command: ", command)
        #assert self.state == BandState.RequestedAuthentication, "bad state"
        
        #if not '' in command:
            
        
        device_config.process_authentication(
            self.link_params.auth_version,
            command,
            self._client_nonce,
            self._server_nonce,
        )

    def _process_bond_params(self, command: Command):
        print("_process_bond_params: state?", self.state, BandState.RequestedBondParams)
        #assert self.state == BandState.RequestedBondParams, "bad state"
        self.link_params.max_frame_size, self._encryption_counter = device_config.process_bond_params(command)
        print("_process_bond_params: self._encryption_counter", self._encryption_counter)

    @check_result
    def _process_bond(self, command: Command):
        print("_process_bond. command: ", command)
        print("_process_bond: in the correct state? ", (self.state == BandState.RequestedBond))
        #assert self.state == BandState.RequestedBond, "bad state"
        return command  # TLV(tag=2, value=bytes.fromhex('01'))


async def run(config, loop):
    secret = base64.b64decode(config["secret"])
    device_uuid = config["device_uuid"]
    device_mac = config["device_mac"]
    client_mac = config["client_mac"]

    async with BleakClient(device_mac if platform.system() != "Darwin" else device_uuid, loop=loop) as client:
        band = Band(loop=loop, client=client, client_mac=client_mac, device_mac=device_mac, key=secret)
        
        print("\nband: ", band)
        
        print("\ntrying band.connect")
        await band.connect()
        
        #await asyncio.sleep(15)
        
        loop_counter = 0
        while True:
            await asyncio.sleep(.1)
            
            """
            loop_counter += 1
            
            if loop_counter == 150:
                print("trying to get battery level")
                await band.get_battery_level()
            """
            
            
            
        
        """
        
        
        

        print("\ntrying band.get_product_info")
        await band.get_product_info()

        # await band.factory_reset()

        print("\ntrying band.get_battery_level")
        battery_level = await band.get_battery_level()
        logger.info(f"Battery level: {battery_level}")

        await band.set_right_wrist(False)
        await band.set_rotation_actions()
        await band.set_time()
        await band.set_locale("en-US", locale_config.MeasurementSystem.Metric)
        await band.set_date_format(device_config.DateFormat.YearFirst, device_config.TimeFormat.Hours24)

        await band.set_user_info(
            int(config.get("height", 170)),
            int(config.get("weight", 60)),
            fitness.Sex(int(config.get("sex", 1))),
            date.fromisoformat(config.get("birth_date", "1990-08-01")),
        )

        await band.enable_trusleep(True)
        await band.enable_heart_rate_monitoring(False)

        today_totals = await band.get_today_totals()
        logger.info(f"Today totals: {today_totals}")

        # await band.send_notification("Really nice to see you ^__^", "Hello, World!",
        #                              vibrate=True, notification_type=NotificationType.Email)

        
        
        """
        
        
        
        #print("\n.\n..\n...\n")
        #print("Disconnecting in 10 seconds...")
        #time.sleep(10)
        #await asyncio.sleep(10)
        
        
        #print("END! calling band.disconnect")
        #await band.disconnect()
        #await asyncio.sleep(2)
        #print("bye")
        
        
        

def main():
    config = ConfigParser()
    
    #"device_uuid": "00003802-0000-1000-8000-00805f9b34fb", #"A0E49DB2-XXXX-XXXX-XXXX-D75121192329",
     # ??> 00003802-0000-1000-8000-00805f9b34fb
    if not CONFIG_FILE.exists():
        config[DEVICE_NAME] = {
            #"device_uuid": "D914AD48-48BE-0265-7B36-4665721BCD30", 
            "device_uuid": "D914AD48-48BE-0265-7B36-4665721BCD30", 
            "device_mac": "FC:86:2A:E1:36:D2",
            "client_mac": "F8:4d:89:5F:91:65",
            "secret": base64.b64encode(generate_nonce()).decode(),
        }

        with open(CONFIG_FILE.name, "w") as fp:
            config.write(fp)



        print("created missing ini file. try again.")
        return

    config.read(CONFIG_FILE.name)

    #event_loop = asyncio.get_event_loop()
    event_loop = asyncio.new_event_loop()


    try:
        #event_loop = asyncio.new_event_loop()
        #event_loop.create_task(run(config[DEVICE_NAME], event_loop))
        #event_loop.run_forever()
        
        event_loop.run_until_complete(run(config[DEVICE_NAME], event_loop))
    except KeyboardInterrupt:
        print("got keyboard interrupt")
    except Exception as ex:
        print("CAUGHT ERROR: ", ex)
    finally:
        print("\n\n\nFINALLY\nCLOSING EVENT LOOP")
        event_loop.close()

    print("\n\n__END__\n\n")




if __name__ == "__main__":
    main()
