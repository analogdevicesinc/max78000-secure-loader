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
from enum import Enum
from copy import deepcopy
from ctypes import *
from threading import Timer, Thread, Event
from datetime import datetime
from colorama import Fore, Back, Style, init

VERSION = "0.36"
platform_types = { 1: 'MAX32660',
                   3: 'MAX32670', 
                   5: 'MAX78000',}

DEFAULT_PAGE_SIZE = 8192

class MsblHeader(Structure):
	_fields_ = [('magic', 4 * c_char),
				('formatVersion', c_uint),
				('target', 16 * c_char),
				('enc_type', 16 * c_char),
				('nonce', 11 * c_ubyte),
				('resv0', c_ubyte),
				('auth', 16 * c_ubyte),
				('numPages', c_ushort),
				('pageSize', c_ushort),
				('crcSize', c_ubyte),
				('resv1', 3 * c_ubyte)]

class AppHeader(Structure):
	_fields_ = [('crc32', c_uint),
				('length', c_uint),
				('validMark', c_uint),
				('boot_mode', c_uint)]

class Page(Structure):
	_fields_ = [('data', (8192 + 16) * c_ubyte)]

class RawPage(Structure):
	_fields_ = [('data', (8192) * c_ubyte)]

class CRC32(Structure):
	_fields_ = [('val', c_uint)]

class KeyFile(Structure):
	_fields_ = [('key_start', 13 * c_char),
				('formatVersion', c_uint),
				('target', 16 * c_char),
				('enc_type', 16 * c_char),
				('nonce', 11 * c_ubyte),
				('resv0', c_ubyte),
				('auth', 16 * c_ubyte),
				('numPages', c_ushort),
				('pageSize', c_ushort),
				('crcSize', c_ubyte),
				('resv1', 3 * c_ubyte)]

class Object(object):
    pass

bl_exit_mode = { 0 : 'Jump immediately',
				1 : 'Wait for programmable delay',
				2 : 'remain in bootloader until receive exit command'}

bl_gpio_polarities = {  0 : 'active low',
						1 : 'active high'}

bl_entry_check = { 0 : 'always enter',
					1 : 'check EBL pin'}

class BL_MODE:
	SINGLE_DOWNLOAD = 1
	CONTINUES_DOWNLOAD = 2

class EBL_MODE:
	USE_TIMEOUT = 0
	USE_GPIO = 1

class MaximBootloader(object):
	def __init__(self, input_file, port, send_size):
		self.ser = serial.Serial()
		self.ser.port = port
		self.ser.baudrate = 115200
		self.ser.timeout = 300
		self.send_size = send_size
		try:
			self.ser.open();	 # open the serial port

			if self.ser.isOpen():
				 print(self.ser.name + ' is open...')
		except (OSError, serial.SerialException):
			print (Fore.RED + 'Cannot open serial port ' + port)
			exit(-1)

		print('\n\nInitializing bl downloader')
		self.msbl = Object()
		if input_file != None :
			self.msbl.file_name = input_file
			self.quit_flag = False
			print('Input file name: ' + self.msbl.file_name)

	def key_press_to_continue(self):
		try:
			input("Press enter to continue")
		except SyntaxError:
			pass
		except KeyboardInterrupt:
			print('Interrupted by Ctrl + C...')
			self.quit()

	def read_input_file(self):
		file_name, extension = os.path.splitext(self.msbl.file_name)
		if extension == '.bin':
			return self.read_bin_file()
		elif extension == '.msbl':
			return self.read_msbl_file()
		print('Invalid file extension: ' + extension)
		return False

	def get_crc_of_file(self, file_name):
		prev = 0
		for each_line in open(file_name, 'rb'):
			prev = zlib.crc32(each_line, prev)
		return (prev & 0xFFFFFFFF)

	def read_bin_file(self):
		print('Bin file name: ' + self.msbl.file_name)
		app_crc = self.get_crc_of_file(self.msbl.file_name)
		with open(self.msbl.file_name, 'rb') as self.bin_file:
			app_size = os.path.getsize(self.msbl.file_name)
			self.header = MsblHeader()
			self.header.pages = {}
			self.header.magic = 'msbl'
			self.header.formatVersion = 0
			self.header.target = 'MAX32660'
			self.header.enc_type = ''
			self.header.page_size = DEFAULT_PAGE_SIZE
			self.header.crcSize = 4
			self.header.nonce[:] = bytearray(11)
			self.header.auth[:] = bytearray(16)
			self.header.resv1[:] = bytearray(3)
			self.header.numPages = (app_size + DEFAULT_PAGE_SIZE + (DEFAULT_PAGE_SIZE - 1)) / DEFAULT_PAGE_SIZE
			for i in range(self.header.numPages):
				raw_page = RawPage()
				self.bin_file.readinto(raw_page)
				if i == self.header.numPages - 1:
					raw_page.data[0] = app_crc & 0xFF
					raw_page.data[1] = (app_crc >> 8) & 0xFF
					raw_page.data[2] = (app_crc >> 16) & 0xFF
					raw_page.data[3] = (app_crc >> 24) & 0xFF
					raw_page.data[4] = app_size & 0xFF
					raw_page.data[5] = (app_size >> 8) & 0xFF
					raw_page.data[6] = (app_size >> 16) & 0xFF
					raw_page.data[7] = (app_size >> 24) & 0xFF
				crc = zlib.crc32(buffer(bytearray(raw_page), 0, DEFAULT_PAGE_SIZE))
				page = Page()
				ctypes.memmove(page.data, raw_page.data, DEFAULT_PAGE_SIZE)
				page.data[DEFAULT_PAGE_SIZE] = crc & 0xFF
				page.data[DEFAULT_PAGE_SIZE + 1] = (crc >> 8) & 0xFF
				page.data[DEFAULT_PAGE_SIZE + 2] = (crc >> 16) & 0xFF
				page.data[DEFAULT_PAGE_SIZE + 3] = (crc >> 24) & 0xFF
				for page_offset in range(0, 12):
					page.data[DEFAULT_PAGE_SIZE + 4 + page_offset] = 0
				self.header.pages[i] = deepcopy(page.data)
			self.msbl.header = self.header
			self.msbl.page = self.header.pages
		return True

	def read_msbl_file(self):
		total_size = 0
		print('msbl file name: ' + self.msbl.file_name)
		with open(self.msbl.file_name, 'rb') as self.f:
			header = MsblHeader()
			if self.f.readinto(header) == sizeof(header):
				print('magic: ' + str(header.magic)
						+ '  formatVersion: ' + str(header.formatVersion)
						+ '  target: ' + header.target
						+ '  enc_type: ' + header.enc_type
						+ '  numPages: ' + str(header.numPages)
						+ '  pageSize: ' + str(header.pageSize)
						+ '  crcSize: ' + str(header.crcSize)
						+ ' size of header: ' + str(sizeof(header)))

				print('  resv0: ', header.resv0)
				self.print_as_hex('nonce', header.nonce)
				self.print_as_hex('auth', header.auth)
				self.print_as_hex('resv1', header.resv1)
			else:
				return False

			self.msbl.header = header

			i = 0
			self.msbl.page = {}
			tmp_page = Page()
			last_pos = self.f.tell()
			total_size = total_size + sizeof(header)
			print('last_pos: ' + str(last_pos))
			while self.f.readinto(tmp_page) == sizeof(tmp_page):
				self.msbl.page[i] = deepcopy(tmp_page.data)
				total_size = total_size + sizeof(tmp_page)
				#print('read page ' + str(i));
				i = i + 1
				last_pos = self.f.tell()
				#print('last_pos: ' + str(last_pos))

			self.msbl.crc32 = CRC32()
			self.f.seek(-4, 2)

			self.f.readinto(self.msbl.crc32)
			boot_mem_page = i - 1
			total_size = total_size + sizeof(self.msbl.crc32)
			print('Total file size: ' + str(total_size) + ' CRC32: ' + hex(self.msbl.crc32.val))
			print('Reading msbl file succeed.')
		self.f.close()
		return True

	def set_iv(self):
		print(Fore.GREEN + '\nSet IV')
		nonce_hex = "".join("{:02X}".format(c) for c in self.msbl.header.nonce)
		print('set_iv ' + nonce_hex + '\n')
		ret = self.send_str_cmd('set_iv ' + nonce_hex + '\n')
		if ret[0] == 0:
			print('Set IV bytes succeed.')
		return ret[0]

	def set_auth(self):
		print(Fore.GREEN + '\nSet Auth')
		auth_hex = "".join("{:02X}".format(c) for c in self.msbl.header.auth)
		print('set_auth ' + auth_hex + '\n')
		ret = self.send_str_cmd('set_auth ' + auth_hex + '\n')
		if ret[0] == 0:
			print('Set Auth bytes succeed.')
		return ret[0]

	def set_num_pages(self, num_pages):
		print(Fore.GREEN + '\nSet number of pages to download')
		ret = self.send_str_cmd('num_pages ' + str(num_pages) + '\n')
		if ret[0] == 0:
			print('Set page size('+ str(num_pages) +') successfully.')
		return ret[0]

	def erase_app(self):
		print(Fore.GREEN + '\nErase App')
		ret = self.send_str_cmd('erase\n')
		if ret[0] == 0:
			print('Erasing App flash succeed.')
		time.sleep(0.6)
		return ret[0]

	def enter_flash_mode(self):
		print(Fore.GREEN + '\nEnter flashing mode')
		ret = self.send_str_cmd('flash\n')
		if ret[0] == 0:
			print('flash command succeed.')
		else:
			print("FAILED: ret: " + str(ret))
			return ret[0]
		return ret[0]

	def enable_image_on_RAM(self, enable):
		print(Fore.GREEN + '\nEnable image on RAM: ', str(enable))
		ret = self.send_str_cmd('image_on_ram '+ str(int(enable == True)) +'\n')
		print('CMD :'+'image_on_ram '+ str(int(enable == True)) +'\n')
		if ret[0] == 0:
			print('In image_on_ram Mode.')
		else:
			print("FAILED: ret: " + str(ret))
			return ret[0]
		return ret[0]


	def flash_image_on_RAM(self, num_pages):
		print(Fore.GREEN + '\n' + str(datetime.time(datetime.now()))  + ' - Flashing Firmware on RAM')
		ret = self.send_str_cmd('image_flash\n')

		for i in range(0, num_pages):
			print("Flashing " + str(i + 1) + "/" + str(num_pages) + " page...", end="")
			resp = self.ser.readline()
			ret = self.parse_response(resp)
			if ret[0] == 0:
				print("[DONE]")
			else:
				print("[FAILED]... ret: ", ret)

		if ret[0] == 0:
			print('flash command succeed.')
		else:
			print("FAILED: ret: " + str(ret))
			return ret[0]
		return ret[0]

	def download_page(self, page_num):
		page_bin = self.msbl.page[page_num]
		i = 0
		step = 16
		while i < (8192 + 16):
			page_part = page_bin[i: i + step]
			self.ser.write(serial.to_bytes(page_part))
			i = i + step

		ret = self.parse_response("NA")
		return ret[0]

	def get_flash_page_size(self):
		print(Fore.GREEN + '\nGet page size')
		ret = self.send_str_cmd('page_size\n')
		if ret[0] == 0:
			self.page_size = int(ret[1]['value'])
			print('Target page size: ' + str(self.page_size))
			if self.page_size != 8192:
				print ('WARNING: Page size is not 8192. page_size: ' + str(self.page_size))
		return ret[0]

	def get_usn(self):
		print(Fore.GREEN + '\nGet USN')
		ret = self.send_str_cmd('get_usn\n')
		if ret[0] == 0:
			print('USN = ' + ret[1]['value'])
		return ret[0]

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


	######### Bootloader #########
	def bootloader_single_download(self, reset):
		print('\nDownloading msbl file')

		if self.enter_bootloader_mode() != 0:
			print('Entering bootloader mode failed')
			return

		if self.enable_image_on_RAM(False) != 0:
			print('Unable to disable image_on_RAM...')
			return

		if self.get_device_info() != 0:
			print('Reading device info failed')

		if self.get_flash_page_size() != 0:
			print('Reading flash page size failed')
			return

		if self.get_usn() != 0:
			print('Reading USN failed')
			return

		num_pages = self.msbl.header.numPages
		if self.set_num_pages(num_pages) != 0:
			print('Setting page size (',num_pages,') failed. ')
			return

		if self.set_iv() != 0:
			print('Setting IV bytes failed.')
			return

		if self.set_auth() != 0:
			print('Setting Auth bytes failed.')
			return

		send_size = self.send_size
		if send_size is not None and self.set_send_size(send_size) != 0:
			print('Setting send size for partial page failed.')
			return

		if self.erase_app() != 0:
			print('Erasing app memory failed')
			return

		if self.enter_flash_mode() != 0:
			print('Entering flash mode failed')
			return

		for i in range(0, num_pages):
			print("Flashing " + str(i + 1) + "/" + str(num_pages) + " page...", end="")
			ret = self.download_page(i)
			if ret == 0:
				print("[DONE]")
			else:
				print("[FAILED]... err: " + str(ret))
				return

		print('Flashing MSBL file succeed...')
		if reset == True:
			print ("Resetting target...")
			if self.restart_device() != 0:
				return
		else:
			ret = self.exit_from_bootloader(num_pages)
			if ret != 0:
				print("FAILED to jump application...")
				return
		print(Fore.GREEN + 'SUCCEED...')
		self.close()
		sys.exit(0)

	def bootloader_continuous_download(self, reset):
		print('\nDownloading msbl file')

		if self.enable_image_on_RAM(True) != 0:
			print('Unable to enable enable_image_on_RAM...')
			return

		time.sleep(0.2)
		num_pages = self.msbl.header.numPages
		if self.set_num_pages(num_pages) != 0:
			print('Setting page size (' + str(num_pages) + ') failed. ')
			return

		if self.set_iv() != 0:
			print('Setting IV bytes failed.')
			return

		if self.set_auth() != 0:
			print('Setting Auth bytes failed.')
			return

		send_size = self.send_size
		if send_size is not None and self.set_send_size(send_size) != 0:
			print('Setting send size for partial page failed.')
			return

		if self.enter_flash_mode() != 0:
			print('Entering flash mode failed')
			return

		start = time.time()
		for i in range(0, num_pages):
			print('Downloading ' + str(i + 1) + '/' + str(num_pages) + ' page to Host RAM...')
			if self.download_page(i) != 0:
				print('Flashing ' + str(i) + '. page failed')
				return
		end = time.time()
		print("Downloading an image to host RAM takes " + str(end - start) + " sec...")

		while True:
			print(Fore.MAGENTA + '\n\n' + str(datetime.time(datetime.now()))
						+ ' - Application binary is in Host\'s RAM. Ready to Flash..')
			self.key_press_to_continue()
			if self.quit_flag:
				print("Exiting from firmware downloader")
				return

			start = time.time()
			if self.flash_image_on_RAM(num_pages):
				print('Unable to flash image on RAM to target')
				return

			end = time.time()
			print("Transferring an image to target takes " + str(end - start) + " sec...")
			print(Back.BLACK + Fore.GREEN + str(datetime.time(datetime.now())) + ' Flashing SUCCEED...')
			if reset == True:
				if self.restart_device() != 0:
					return
			else:
				self.exit_from_bootloader(num_pages)

		print('SUCCEED...')
		self.close()
		sys.exit(0)


	def bootloader(self, mode, reset):
		if mode == BL_MODE.SINGLE_DOWNLOAD:
			self.bootloader_single_download(reset)
		elif mode == BL_MODE.CONTINUES_DOWNLOAD:
			self.bootloader_continuous_download(reset)

	def load_key(self, key_file):
		if self.enter_bootloader_mode() != 0:
			print('Entering bootloader mode failed')
			return
		print('key file name: ' + key_file)
		keyfile = open(key_file, 'r')
		line = keyfile.readline()
		#Parse Key
		if(line != 'aes_key_start\n'):
			print('Invalid Key file start' )
			return False
		line = keyfile.readline()
		key =""
		while (line != 'aes_key_end\n'):
			trimmed_line = line.replace("0x", "")
			trimmed_line = trimmed_line.replace(", ", "")
			trimmed_line = trimmed_line.replace(",", "")
			trimmed_line = trimmed_line.replace("\n", "")
			key+=trimmed_line
			line = keyfile.readline()
			if(line == 'aes_key_end\n'):
				break
		key_length = len(key)/2
		if((key_length != 16)and(key_length != 24)and(key_length != 32)):
			print('Wrong Key Length')
			return -1 #wrong key len
		print(key)
		for i in range(key_length,32):
			key += "00"
		key = str(hex(key_length)) + key
		key = key.replace("0x", "")
		#Parse AAD
		line = keyfile.readline()
		if(line != 'aes_aad_start\n'):
			print('Invalid Key file start' )
			return False
		line = keyfile.readline()
		aad =""
		while (line != 'aes_key_end\n'):
			trimmed_line = line.replace("0x", "")
			trimmed_line = trimmed_line.replace(", ", "")
			trimmed_line = trimmed_line.replace(",", "")
			trimmed_line = trimmed_line.replace("\n", "")
			aad+=trimmed_line
			line = keyfile.readline()
			if(line == 'aes_key_end\n'):
				break
		aad_length = len(aad)/2
		print(aad)
		if(aad_length > 32):
			print('Wrong AAD Length')
			return -1 #wrong AAD len
		for i in range(aad_length,32):
			aad += "00"
		aad = str(hex(aad_length)) + aad
		aad = aad.replace("0x", "")

		ret = self.send_str_cmd('set_key ' + key + aad + '\n')
		if ret[0] == 0:
			print('Set Key bytes succeed.')
		else:
			print("Key load FAILED!!!: ret: " + str(ret[0]))
		keyfile.close()
		return ret[0]
		return True

	def set_host_comm_interface(self, comm):
		print(Fore.GREEN + '\nBootloader communication interface as ' + comm)
		ret = self.send_str_cmd('set_cfg comm ' + str(comm) + '\n')
		print('Command: set_cfg comm ' + str(comm) + '\n')
		if ret[0] == 0:
			print('Set comm interface to ' + str(comm))
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

	def set_send_size(self, send_size):
		print(Fore.GREEN + '\nSet partial page size in host')
		ret = self.send_str_cmd('set_partial_size ' + str(send_size) + '\n')
		if ret[0] == 0:
			print('Set set_partial_size factor to ' + str(send_size))
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
				break

		if (length < 2):
			print('send_str_cmd failed. cmd: ' + cmd + ' len: ' + str(length))
			return -1

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

		return [int(values['err']), values]


	def send_str_cmd(self, cmd):
		length = 0
		self.ser.write(cmd.encode())
		return self.parse_response(cmd.encode())

	def get_device_info(self):
		ret = self.send_str_cmd('get_device_info\n')
		if ret[0] == 0:
			for key, value in ret[1].items():
			    print(key, value)
		else:
			print('Device Info err: ' + str(ret[0]))
		return ret[0]

	def enter_bootloader_mode(self):
		ret = self.send_str_cmd('bootldr\n')
		if ret[0] != 0:
			print('Unable to enter bootloader mode... err: ' + str(ret[0]))
		return ret[0]

	def restart_device(self):
		print(Fore.GREEN + '\nRestart device')
		ret = self.send_str_cmd('reset\n')
		if ret[0] == 0:
			print('Restarting device. ret: ' + str(ret[0]))
		return ret[0]

	def exit_from_bootloader(self, num_pages):
		time.sleep(0.03*num_pages)
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
	parser.add_argument("-f", "--input_file", type=str,
                    help="msbl or binary file as input")
	parser.add_argument("-p", "--port", required=True, type=str,
                    help=("Serial port name in Windows and device file path in Linux."
							"For example:"
							"	/dev/ttyACM0 in linux"
							"	COM1 in Windows"))
	parser.add_argument("-k", "--key_file", type=str,
                    help="key file as input (Only available for MAX78000)")
	parser.add_argument("-m", "--massflash", action='store_true',
                    help="Downloads firmware to Host\'s RAM, and flashes many targets, saves time..."
					"If not specified, the defualt is single target update...")

	parser.add_argument("-r", "--reset", action='store_true',
                    help="Reset target to bootloader when flashing is done..."
					"If not specified, it jumps to application from bootloader...")

	parser.add_argument("-e", "--ebl_mode", action='store_true',
                    help="This parameter sets host to use GPIO to put device into bootloader mode. "
					"Default is timeout unless this parameter is specified."
					"If bootloader is commanded via serial during timeout, it will stay in bootloader mode."
					"Otherwise it jumps application if there is a valid one..");

	parser.add_argument("-d", "--delay_factor", type=int, choices=range(0,51),
					metavar="[0-50]",
                    help="Communication wait time factor. Default value is 1."
					"If bootloader need more time to process a command, this is a multiplication factor.", default=1)

	parser.add_argument("-c", "--comm_interface", type=str, choices=['i2c', 'spi', 'uart'],
					metavar="uart",
                    help="Communication Interface selection for host and device. "
					"Default is i2c unless this parameter is specified.")

	parser.add_argument("-s", "--send_size", type=int, choices=range(1, 8209),
					metavar="[1-8208]",
					help="Partial page send size from host to bootloader."
					"If specified, host will send pages by multiple of specified size of the packet.")

	parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
	args = parser.parse_args()
	init(autoreset=True)
	print(Fore.CYAN + '\n\nMAXIM FIRMWARE DOWNLOADER ' + VERSION + '\n\n')
	ebl_mode = int(args.ebl_mode == True)
	print(">>> Parameters <<<")
	print("Mass Flash: ", args.massflash)
	print("Reset Target: ", args.reset)
	print("EBL mode: ", ebl_mode)
	print("Delay Factor: ", args.delay_factor)
	print("Port: ", args.port)
	print("MSBL/Binary input file: ", args.input_file)
	print("Comm Interface: ", args.comm_interface)

	bl = MaximBootloader(args.input_file, args.port, args.send_size)
	print('### Press double Ctrl + C to stop\t')
	try:

		if args.input_file != None:
			if bl.read_input_file() != True:
				print('Reading input file failed')
				raise Exception('Unable to read Input file')

		if bl.set_host_mcu(ebl_mode, args.delay_factor, args.comm_interface) == False:
			raise Exception('Unable to set host')

		if args.key_file != None:
			bl.load_key(args.key_file)
		if args.input_file != None:
			if args.massflash == True:
				bl.bootloader(BL_MODE.CONTINUES_DOWNLOAD, args.reset)
			else:
				bl.bootloader(BL_MODE.SINGLE_DOWNLOAD, args.reset)

	except KeyboardInterrupt:
		bl.quit()
		sys.exit(0)

if __name__ == '__main__':
	main()
