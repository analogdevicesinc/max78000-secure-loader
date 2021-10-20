#!/usr/bin/python

################################################################################
# Copyright (C) 2018 Maxim Integrated Products, Inc., All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL MAXIM INTEGRATED BE LIABLE FOR ANY CLAIM, DAMAGES
# OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# Except as contained in this notice, the name of Maxim Integrated
# Products, Inc. shall not be used except as stated in the Maxim Integrated
# Products, Inc. Branding Policy.
#
# The mere transfer of this software does not imply any licenses
# of trade secrets, proprietary technology, copyrights, patents,
# trademarks, maskwork rights, or any other form of intellectual
# property whatsoever. Maxim Integrated Products, Inc. retains all
# ownership rights.
#
###############################################################################

from __future__ import print_function
import os
import sys
import serial
import threading
import logging
import signal
import time
import argparse
import atexit
import re
import struct
import ctypes
import zlib
import time
import ConfigParser
from enum import Enum
from copy import deepcopy
from ctypes import *
from threading import Timer, Thread, Event
from datetime import datetime
from colorama import Fore, Back, Style, init
from packaging import version

VERSION = "0.2"
platform_types = {1: 'MAX32660'}

class Object(object):
    pass

bl_exit_mode = { 0 : 'Jump immediately',
				1 : 'Wait for programmable delay',
				2 : 'remain in bootloader until receive exit command'}

bl_gpio_polarities = {  0 : 'active low',
						1 : 'active high'}

bl_entry_check = {	0 : 'Do not check EBL pin',
					1 : 'Check EBL pin'}

bl_config_en_dis = { 0 : 'disabled',
					 1 : 'enabled'}

bl_config_i2c_addr = {  0 : '0x58',
						1 : '0x5A',
						2 : '0x5C',
						3 : '0xAA'}

class EBL_MODE:
	USE_TIMEOUT = 0
	USE_GPIO = 1

class MaximBootloaderConfigurator(object):
	def __init__(self, port):
		self.ser = serial.Serial()
		self.ser.port = port
		self.ser.baudrate = 115200
		self.ser.timeout = 300
		try:
			self.ser.open()	 # open the serial port

			if self.ser.isOpen():
				 print(self.ser.name + ' is open...')
		except (OSError, serial.SerialException):
			print (Fore.RED + 'Cannot open serial port ' + port)
			exit(-1)

		self.quit_flag = False

	def key_press_to_continue(self):
		try:
			input("Press enter to continue")
		except SyntaxError:
			pass
		except KeyboardInterrupt:
			print('Interrupted by Ctrl + C...')
			self.quit()

	def set_host_mcu(self, ebl_mode, delay_factor, comm_interface):

		if comm_interface is not None and self.set_host_comm_interface(comm_interface) != 0:
			print('Unable to change communication medium.')
			return False

		if self.disable_echo() != 0:
			print('Unable to disable echo mode. Communication failed...')
			return False

		if not EBL_MODE.USE_TIMEOUT <= ebl_mode <= EBL_MODE.USE_GPIO:
			print("Invalid parameter")
			return False

		if self.set_host_ebl_mode(ebl_mode) != 0:
			print('Unable to set EBL mode in host')
			return False

		if self.set_host_delay_factor(delay_factor) != 0:
			print('Unable to set delay factor mode in host')
			return False


		return True


	######### Bootloader Configure #########
	def bootloader_configure(self, reset, config_file):
		print('\nConfiguring bootloader')
		config = ConfigParser.RawConfigParser()
		if config_file!= None:
			config.read(config_file)

		if self.enter_bootloader_mode() != 0:
			print('Entering bootloader mode failed')
			return

		self.bl_version = self.get_bl_version()
		if self.bl_version is None:
			print('Unable to read bootloader version')

		# if self.get_device_info() != 0:
			# print('Reading device info failed')

		if config_file!= None:
			var = config.getint('BootConfig', 'enter_bl_check')
			if self.set_config_ebl_check(str(var)):
				print('Enter BL check configuration failed')
				return

			var = config.getint('BootConfig', 'ebl_pin')
			if self.set_config_ebl_pin(str(var)):
				print('EBL Pin configuration failed')
				return

			var = config.getint('BootConfig', 'ebl_pol')
			if self.set_config_ebl_polarity(str(var)):
				print('EBL Pin Polarity configuration failed')
				return

			var = config.getint('BootConfig', 'valid_mark_check')
			if self.set_config_valid_check(str(var)):
				print('Valid Mark Check configuration failed')
				return

			var = config.getint('BootConfig', 'uart_enable')
			if self.set_config_interface('uart', str(var)):
				print('UART interface configuration failed')
				return

			var = config.getint('BootConfig', 'i2c_enable')
			if self.set_config_interface('i2c', str(var)):
				print('I2C interface configuration failed')
				return

			var = config.getint('BootConfig', 'spi_enable')
			if self.set_config_interface('spi', str(var)):
				print('SPI interface configuration failed')
				return

			var = config.getint('BootConfig', 'i2c_addr')
			if self.set_config_i2c_addr(str(var)):
				print('I2C Slave Addr configuration failed')
				return

			var = config.getint('BootConfig', 'crc_check')
			if self.set_config_crc_check(str(var)):
				print('CRC Check configuration failed')
				return

			var = config.getint('BootConfig', 'swd_lock')
			if self.set_config_swd_lock(str(var)):
				print('SWD Lock configuration failed')
				return

			var = config.getint('BootConfig', 'ebl_timeout')
			if self.set_config_bl_timeout(str(var)):
				print('BL Timeout configuration failed')
				return

			var = config.getint('BootConfig', 'exit_bl_mode')
			if self.set_exit_bl_to_mode(str(var)):
				print('Exit BL Timeout Mode configuration failed')
				return

			if self.save_bl_config():
				print('Bootloader Config save failed')
				return

		if self.get_config_bl():
			print('BL config received')
			return

		self.exit_from_bootloader(0)


	def set_host_comm_interface(self, comm):
		print(Fore.GREEN + '\nBootloader communication interface as ' + comm)
		ret = self.send_str_cmd('set_cfg comm ' + str(comm) + '\n')
		#print('Command: set_cfg comm ' + str(comm) + '\n')
		if ret[0] == 0:
			print('Set comm interface to ' + str(comm))
		time.sleep(0.6)
		return ret[0]

	def set_config_ebl_check(self, ebl):
		ret = self.send_str_cmd('set_cfg bl enter_mode ' + str(ebl) + '\n')
		#print('Command: set_cfg bl enter_mode ' + str(ebl) + '\n')
		if ret[0] == 0:
			print(Fore.GREEN + '\tenter_bl_check ' + bl_config_en_dis[int(ebl)])
		time.sleep(0.6)
		return ret[0]

	def set_config_ebl_polarity(self, pol):
		ret = self.send_str_cmd('set_cfg bl enter_pol ' + str(pol) + '\n')
		#print('Command: set_cfg bl enter_pol ' + str(pol) + '\n')
		if ret[0] == 0:
			print(Fore.GREEN + '\tebl_polarity is ' + bl_gpio_polarities[int(pol)])
		time.sleep(0.6)
		return ret[0]

	def set_config_ebl_pin(self, pin):
		ret = self.send_str_cmd('set_cfg bl enter_pin ' + '0 ' + str(pin) + '\n')
		#print('Command: set_cfg bl enter_pin ' + '0.' + str(pin) + '\n')
		if ret[0] == 0:
			print(Fore.GREEN + '\tebl_pin ' + pin)
		time.sleep(0.6)
		return ret[0]

	def set_config_valid_check(self, validMark):
		ret = self.send_str_cmd('set_cfg bl valid ' + str(validMark) + '\n')
		#print('Command: set_cfg valid ' + str(validMark) + '\n')
		if ret[0] == 0:
			if(validMark):
				print(Fore.GREEN + '\tvalid_mark_check ' + bl_config_en_dis[int(validMark)])
		time.sleep(0.6)
		return ret[0]

	def set_config_interface(self, interface, comm):

		ret = self.send_str_cmd('set_cfg bl ' + interface + ' ' + str(comm) + '\n')
		#print('Command: set_cfg bl ' + interface + str(comm) + '\n')
		if ret[0] == 0:
			print(Fore.GREEN  + '\t' + interface.lower() + '_enable: ' + str(comm))
		time.sleep(0.6)
		return ret[0]

	def set_config_i2c_addr(self, i2c_addr):
		ret = self.send_str_cmd('set_cfg bl addr_i2c ' + str(i2c_addr) + '\n')
		#print('Command: set_cfg bl addr_i2c ' + str(i2c_addr) + '\n')
		if ret[0] == 0:
			if (version.parse(self.bl_version) < version.parse('3.4.2')):
				i2c_addr = bl_config_i2c_addr[int(i2c_addr)]
			print(Fore.GREEN + '\ti2c_addr: ' + str(i2c_addr))
		time.sleep(0.6)
		return ret[0]

	def set_config_crc_check(self, crc):
		ret = self.send_str_cmd('set_cfg bl crc ' + str(crc) + '\n')
		#print('Command: set_cfg crc ' + str(crc) + '\n')
		if ret[0] == 0:
			print(Fore.GREEN + '\tcrc_check ' + bl_config_en_dis[int(crc)])
		time.sleep(0.6)
		return ret[0]

	def set_config_swd_lock(self, lock_mode):
		ret = self.send_str_cmd('set_cfg bl swd_lock ' + str(lock_mode) + '\n')
		#print('Command: set_cfg swd_lock ' + str(crc) + '\n')
		if ret[0] == 0:
			print(Fore.GREEN + '\tswd_lock ' + bl_config_en_dis[int(lock_mode)])
		time.sleep(0.6)
		return ret[0]

	def set_exit_bl_to_mode(self, mode):
		ret = self.send_str_cmd('set_cfg bl exit_mode ' + str(mode) + '\n')
		#print('Command: set_cfg bl exit_mode ' + str(mode) + '\n')
		if ret[0] == 0:
			print(Fore.GREEN + '\texit_bl_mode: ' + bl_exit_mode[int(mode)])
		time.sleep(0.6)
		return ret[0]

	def set_config_bl_timeout(self, timeout):
		ret = self.send_str_cmd('set_cfg bl exit_to ' + str(timeout) + '\n')
		#print('Command: sset_cfg bl exit_to ' + str(timeout) + '\n')
		if ret[0] == 0:
			print(Fore.GREEN + '\tebl_timeout: ' + timeout)
		time.sleep(0.6);
		return ret[0]

	def save_bl_config(self):
		#print(Fore.GREEN + '\nSave Bootloader Config')
		ret = self.send_str_cmd('set_cfg bl save ' + '\n')
		if ret[0] == 0:
			print('Bootloader Config saved')
		time.sleep(0.6);
		return ret[0]

	def get_bl_version(self):
		ret = self.send_str_cmd('get_device_info\n')
		version = None
		if ret[0] == 0:
			version = str(ret[1]['hub_firm_ver'])
		return version

	def get_config_bl(self):
		ret = self.send_str_cmd('get_cfg bl\n')
		if ret[0] == 0:
			i2c_addr = int(ret[1]['i2c_addr'])
			if (version.parse(self.bl_version) < version.parse('3.4.2')):
				i2c_addr = bl_config_i2c_addr[i2c_addr]
			print(Fore.GREEN + '\tBL config received ')
			print(Fore.GREEN + '\tenter_bl_check ' + bl_config_en_dis[int(ret[1]['enter_bl_check'])])
			print(Fore.GREEN + '\tebl_pin: ' + str(ret[1]['ebl_pin']))
			print(Fore.GREEN + '\tebl_polarity is ' + bl_gpio_polarities[int(ret[1]['ebl_polarity'])])
			print(Fore.GREEN + '\tvalid_mark_check: ' + bl_config_en_dis[int(ret[1]['valid_mark_check'])])
			print(Fore.GREEN + '\tuart_enable: ' + str(ret[1]['uart_enable']))
			print(Fore.GREEN + '\ti2c_enable: ' + str(ret[1]['i2c_enable']))
			print(Fore.GREEN + '\tspi_enable: ' + str(ret[1]['spi_enable']))
			print(Fore.GREEN + '\ti2c_addr: ' + str(i2c_addr))
			print(Fore.GREEN + '\tcrc_check ' + bl_config_en_dis[int(ret[1]['crc_check'])])
			print(Fore.GREEN + '\tswd_lock ' + bl_config_en_dis[int(ret[1]['swd_lock'])])
			print(Fore.GREEN + '\tebl_timeout: ' + str(ret[1]['ebl_timeout']))
			print(Fore.GREEN + '\texit_bl_mode: ' + bl_exit_mode[int(ret[1]['exit_bl_mode'])])
		time.sleep(0.6);
		return ret[0]

	def set_host_ebl_mode(self, ebl_mode):
		print(Fore.GREEN + '\nSet timeout mode to enter bootloader')
		ret = self.send_str_cmd('set_cfg host ebl ' + str(ebl_mode) + '\n')
		print('Command: set_cfg host ebl ' + str(ebl_mode) + '\n')
		if ret[0] == 0:
			print('Set ebl_mode to ' + str(ebl_mode))
		return ret[0]

	def set_host_delay_factor(self, delay_factor):
		print(Fore.GREEN + '\nSet delay factor in host')
		ret = self.send_str_cmd('set_cfg host cdf ' + str(delay_factor) + '\n')
		if ret[0] == 0:
			print('Set bl comm delay factor to ' + str(delay_factor))
		return ret[0]

	def disable_echo(self):
		while True:
			ret = self.send_str_cmd('silent_mode 1\n')
			if ret[0] == 0:
				print('In silent mode. ret: ' + str(ret[0]))
				break
			elif ret[0] == -1:
				break
			else:
				print("Failed... ret: " + str(ret[0]) + " RETRY...")
		return ret[0]


		for i in range(10):
			out = self.ser.readline()
			length = len(out)
			if (length > 2):
				break;

		if (length < 2):
			print('send_str_cmd failed. cmd: ' + cmd + ' len: ' + str(length))
			return -1;

	def parse_response(self, cmd):
		retry = 0
		while True:
			try:
				out = self.ser.readline()
			except:
				return [-1, {}]

			length = len(out)
			if (length < 2):
				print('TRY AGAIN... send_str_cmd failed. cmd: ' + cmd + ' len: ' + str(length))
				continue

			arr=out.split(' ')
			values = {}
			num_keys = len(arr)
			for i in range(1, num_keys):
				key_pair = arr[i].split('=')
				if len(key_pair) == 2:
					values[key_pair[0]] = key_pair[1]
				else:
					values[key_pair[0]] = ''

			retry = retry + 1
			if 'err' in values:
				break
			else:
				continue

		return [int(values['err']), values];


	def send_str_cmd(self, cmd):
		length = 0;
		self.ser.write(cmd.encode())
		return self.parse_response(cmd.encode())

	def enter_bootloader_mode(self):
		ret = self.send_str_cmd('bootldr\n')
		if ret[0] != 0:
			print('Unable to enter bootloader mode... err: ' + str(ret[0]))
		return ret[0]

	def get_device_info(self):
		ret = self.send_str_cmd('get_device_info\n')
		if ret[0] == 0:
			for key, value in ret[1].items():
			    print(key, value)
		else:
			print('Device Info err: ' + str(ret[0]))
		return ret[0]

	def exit_from_bootloader(self, num_pages):
		time.sleep(0.03*num_pages);
		print(Fore.GREEN + '\nJump to main application')
		ret = self.send_str_cmd('exit\n')
		if ret[0] == 0:
			print('Jumping to main application. ret: ' + str(ret[0]))
		return ret[0]

	def print_as_hex(self, label, arr):
		print(label + ' : ' + ' '.join(format(i, '02x') for i in arr))

	def quit(self):
		self.quit_flag = True
		self.close()

	def close(self):
		print("Closing")
		self.ser.close()

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--config_file", type=str,
                    help="Configuration input file")
	parser.add_argument("-p", "--port", required=True, type=str,
                    help=("Serial port name in Windows and device file path in Linux."
							"For example:"
							"	/dev/ttyACM0 in linux"
							"	COM1 in Windows"))

	parser.add_argument("-e", "--ebl_mode", action='store_true',
                    help="This parameter sets host to use GPIO to put device into bootloader mode. "
					"Default is timeout unless this parameter is specified."
					"If bootloader is commanded via serial during timeout, it will stay in bootloader mode."
					"Otherwise it jumps application if there is a valid one..");

	parser.add_argument("-d", "--delay_factor", type=int, choices=range(0,51),
					metavar="[0-50]",
                    help="Communication wait time factor. Default value is 1."
					"If bootloader need more time to process a command, this is a multiplication factor.", default=1)

	parser.add_argument("-r", "--reset", action='store_true',
                    help="Reset target when flashing is done..."
					"If not specified, it jumps to application from bootloader...")

	parser.add_argument("-c", "--comm_interface", type=str, choices=['i2c', 'spi', 'uart'],
					metavar="uart",
                    help="Communication Interface selection for host and device. "
					"Default is i2c unless this parameter is specified.",
					default='i2c')

	parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
	args = parser.parse_args()
	init(autoreset=True)
	print(Fore.CYAN + '\n\nMAXIM BOOTLOADER CONFIGURATOR ' + VERSION + '\n\n')
	ebl_mode = int(args.ebl_mode == True)
	print(">>> Parameters <<<")
	print("EBL mode: ", ebl_mode)
	print("Delay Factor: ", args.delay_factor)
	print("Port: ", args.port)
	print("Comm Interface: ", args.comm_interface)

	bl = MaximBootloaderConfigurator(args.port)
	print('### Press double Ctrl + C to stop\t');
	try:

		if bl.set_host_mcu(ebl_mode, args.delay_factor, args.comm_interface) == False:
			raise Exception('Unable to set host')

		bl.bootloader_configure(args.reset, args.config_file)

	except KeyboardInterrupt:
		bl.quit();
		sys.exit(0);

if __name__ == '__main__':
	main()
