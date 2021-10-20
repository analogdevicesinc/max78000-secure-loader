# Secure Loader Project

## Programming the [MAX78000](https://www.maximintegrated.com/en/products/microcontrollers/MAX78000.html) with the Bootloader Firmware

_Note: Install [MaximSDK](https://www.maximintegrated.com/en/design/software-description.html/swpart=SFW0010820A#) before following the steps below!_

Use the following steps to program the [MAX78000FTHR](https://www.maximintegrated.com/en/products/microcontrollers/MAX78000FTHR.html) board with bootloader code:
1.	Connect the micro-USB cable to the [MAX78000FTHR](https://www.maximintegrated.com/en/products/microcontrollers/MAX78000FTHR.html) and the PC.
2.	Under the `C:\MaximSDK\Tools\MinGW\msys\1.0` directory, double-click on `msys.bat`. This opens a MinGW® window.
3.	Navigate to the demo directory by typing:
    ```shell
    cd c: /max78000_demo
    ```
4. To flash the bootloader:
    ```shell
    openocd -s $MAXIM_PATH/tools/OpenOCD/scripts -f interface/cmsis-dap.cfg -f target/max78000.cfg -c 'init ;halt;max32xxx mass_erase 0;program MAX78000_Bootloader_vx_x_x.bin verify reset exit 0x10000000'
    ```
    
