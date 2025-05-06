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
