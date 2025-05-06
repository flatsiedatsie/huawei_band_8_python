# Huawei Band 8 Python test

An attempt to connect to a Huawei fitness band and get some basic data from it, like battery level and daily steps.

Tested on Mac OS, but currently doesn't work. it doesn't complete the auth phase yet.

### Based on
https://github.com/zyv/huawei-lpv2


### More information
https://github.com/zyv/huawei-lpv2/issues/11


### Getting started

First run scan.py to find the Band's MAC address (Linux) or UUID (on Mac OS). Put that data in the `test_band8.py` file. 

Also replace the client bluetooth mac address with that of your own client device (e.g. your Macbook). On linux you can run `hciconfig` to quickly find your device's MAC address. On Mac OS you can click on the Bluetooth icon in your menu bar at the top of your screen while holding the ALT button on your keyboard.

You may need to reset your band before it will show up in a scan / before you can connect to it.

Finally, I made some small additions to device_config.py, so you'll want to override that file inside `lib/huawei`. Original file: https://github.com/zyv/huawei-lpv2/blob/master/huawei/services/device_config.py








# Other


The output from the BLE scan:
```
NAME:  HUAWEI Band 8-6D2
Services found for device
	Device address: D914AD48-48BE-0265-7B36-4665721BCD30
	Device name: HUAWEI Band 8-6D2
	Services:
		Service
		Description: HUAWEI Technologies Co.: Ltd.
		Service: 0000fe86-0000-1000-8000-00805f9b34fb (Handle: 42): HUAWEI Technologies Co.: Ltd.
		Characteristics: [['0000fe01-0000-1000-8000-00805f9b34fb', 'Vendor specific', 43, ['write-without-response', 'write']], ['0000fe02-0000-1000-8000-00805f9b34fb', 'Vendor specific', 45, ['notify']]]
		Service
		Description: Device Information
		Service: 0000180a-0000-1000-8000-00805f9b34fb (Handle: 48): Device Information
		Characteristics: [['00002a29-0000-1000-8000-00805f9b34fb', 'Manufacturer Name String', 49, ['read']], ['00002a24-0000-1000-8000-00805f9b34fb', 'Model Number String', 51, ['read']], ['00002a25-0000-1000-8000-00805f9b34fb', 'Serial Number String', 53, ['read']], ['00002a26-0000-1000-8000-00805f9b34fb', 'Firmware Revision String', 55, ['read']], ['00002a27-0000-1000-8000-00805f9b34fb', 'Hardware Revision String', 57, ['read']], ['00002a28-0000-1000-8000-00805f9b34fb', 'Software Revision String', 59, ['read']]]
		Service
		Description: Unknown
		Service: cc353442-be58-4ea2-876e-11d8d6976366 (Handle: 512): Unknown
		Characteristics: [['c551c36a-0377-4a29-9657-74ffb655a188', 'Unknown', 513, ['read', 'write', 'notify']]]
		Service
		Description: Vendor specific
		Service: 00003802-0000-1000-8000-00805f9b34fb (Handle: 768): Vendor specific
		Characteristics: [['00004a02-0000-1000-8000-00805f9b34fb', 'Vendor specific', 769, ['read', 'write', 'notify']]]
```



Grep command to search for hex command codes in the Gadgetbridge source code (e.g. searching for `public static final byte id = 0x37;`, which is the music control)
```
grep -Rnw . -e 'public static final byte id = 0x37'
```
Which should then lead to: https://codeberg.org/Freeyourgadget/Gadgetbridge/src/branch/master/app/src/main/java/nodomain/freeyourgadget/gadgetbridge/devices/huawei/packets/MusicControl.java

See also:
https://codeberg.org/Freeyourgadget/Gadgetbridge/src/branch/master/app/src/main/java/nodomain/freeyourgadget/gadgetbridge/devices/huawei/packets/DeviceConfig.java
