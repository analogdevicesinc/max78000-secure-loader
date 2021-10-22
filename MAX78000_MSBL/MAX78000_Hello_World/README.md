# MAX78000 Hello World

A basic getting started program. Use this example to ensure proper tools and hardware setup.

## Description

This version of Hello_World prints an incrementing count to the console UART and toggles an LED once every 500 ms.

## Setup

If using the Standard EvKit (EvKit_V1):

- Connect a USB cable between the PC and the CN1 (USB/PWR) connector.
- Connect pins 1 and 2 (P0_1) of the JH1 (UART 0 EN) header.
- Open a terminal application on the PC and connect to the EV kit's console UART at 115200, 8-N-1.
- Close jumper JP1 (LED1 EN).
- Close jumper JP2 (LED2 EN).
- Select "`EvKit_V1`" for `BOARD` in `Makefile`

```Makefile
...
# Specify the board used
ifeq "$(BOARD)" ""
BOARD=EvKit_V1
#BOARD=FTHR_RevA
endif
...
```

If using the Featherboard (FTHR_RevA):

- Connect a USB cable between the PC and the CN1 (USB/PWR) connector.
- Open a terminal application on the PC and connect to the EV kit's console UART at 115200, 8-N-1.
- Select "`FTHR_RevA`" for `BOARD` in `Makefile`

```Makefile
...
# Specify the board used
ifeq "$(BOARD)" ""
#BOARD=EvKit_V1
BOARD=FTHR_RevA
endif
...
```

## Expected Output

The Console UART of the device will output these messages:

```UART
Hello World!
count : 0
count : 1
count : 2
count : 3
```

You will also observe the LED (LED1 for EvKit_V1 or D1 for the Featherboard) blinking at a rate of 2Hz.
