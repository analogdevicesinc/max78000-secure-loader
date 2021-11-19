# MAX78000 Hello World

A basic getting started program. Use this example to ensure proper hardware and tools setup.

## Description

The `Hello_World` prints an incrementing count to the UART console and an LED is toggled once every 500 ms.

## Setup

If using the Standard EV kit [(EvKit_V1)](https://www.maximintegrated.com/en/products/microcontrollers/MAX78000EVKIT.html):

1. Connect a USB cable between the PC and the CN1 (USB/PWR) connector.
2. Connect pins 1 and 2 (P0_1) of the JH1 (UART 0 EN) header.
3. Open a terminal application on the PC and connect to the EV kit UART console at `115200/8-N-1`.
4. Close jumper JP1 (LED1 EN).
5. Close jumper JP2 (LED2 EN).
6. Select "`EvKit_V1`" for `BOARD` in `Makefile`

    ```Makefile
    ...
    # Specify the board used
    ifeq "$(BOARD)" ""
    BOARD=EvKit_V1
    #BOARD=FTHR_RevA
    endif
    ...
    ```

If using the Featherboard [(FTHR_RevA)](https://www.maximintegrated.com/en/products/microcontrollers/MAX78000FTHR.html):

1. Connect a USB cable between the PC and the CN1 (USB/PWR) connector.
2. Open a terminal application on the PC and connect to the Featherboard UART console at `115200/8-N-1`.
3. Select "`FTHR_RevA`" for `BOARD` in `Makefile`

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

The following UART messages are sent to the terminal:

```UART
Hello World!
count : 0
count : 1
count : 2
count : 3
```

Also an LED (LED1 for EvKit_V1 or D1 for the Featherboard) blinks at a rate of 2Hz.
