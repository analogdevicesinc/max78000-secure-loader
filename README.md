# Secure Loader Project

The secure bootloader allows the end user of MAX78000 to load an encrypted firmware to MAX78000-based platforms and lock the SWD port. Once it is programmed, the firmware, including the CNN model and application code, cannot be extracted from the chip by anyone, except the developer of the firmware who has the keys.

## Programming the [MAX78000](https://www.analog.com/en/products/max78000.html) with the Bootloader Firmware

_Note: Install the [Analog Devices MSDK](https://www.analog.com/en/design-center/evaluation-hardware-and-software/software/software-download?swpart=SFW0010820A) before following the steps below!_

Use the following steps to program the [MAX78000FTHR](https://www.analog.com/en/design-center/evaluation-hardware-and-software/evaluation-boards-kits/max78000fthr.html) board with bootloader code. For a complete list of documentation, see [Documentation](#documentation) below.

1. Connect the micro USB cable to the [MAX78000FTHR](https://www.analog.com/en/design-center/evaluation-hardware-and-software/evaluation-boards-kits/max78000fthr.html) and the PC.
2. Go to the `C:\MaximSDK\Tools\MSYS2` directory and double-click on `msys.bat`. This opens a MinGW window.
3. Go to to the demo directory by typing:

    ```shell
        cd c: /max78000_demo
    ```

4. To flash the bootloader to the board, enter the following:

    ```shell
        openocd -s $MAXIM_PATH/tools/OpenOCD/scripts -f interface/cmsis-dap.cfg -f target/max78000.cfg -c 'init ;halt;max32xxx mass_erase 0;program MAX78000_Bootloader_vx_x_x.bin verify reset exit 0x10000000'
    ```

    where x, y and z are bootloader revision.

## Documentation

- See [MAX78000 Secure Bootloader InApplication Programming](./MAX78000_MSBL/Docs/MAX78000_Secure_Bootloader_InApplication_Programming.pdf) for step-by-step instructions of how to use the secure bootloader.

  - There is an example code available under the [MAX78000_Hello_World](./MAX78000_MSBL/MAX78000_Hello_World) to verify the setup. Look at the [README.md](./MAX78000_MSBL/MAX78000_Hello_World/README.md) under the project directory for important information about the `Makefile`.
  - You can find more information for the bootloader and its architecture by referring to [MAX78000 Bootloader User Guide](./MAX78000_MSBL/Docs/MAX78000_Bootloader_UG.pdf).

- Optionally, there are Bootloader GUI tools available from the MSDK Maintenance Tools. You have to install the [Analog Devices MSDK](https://www.analog.com/en/design-center/evaluation-hardware-and-software/software/software-download?swpart=SFW0010820A) before you can use this tool.
  
  - The detailed explanations of how to communicate to the bootloader can be found in the [Bootloader Tools User Guide](https://www.analog.com/media/en/technical-documentation/user-guides/maxim-bootloader-tools-user-guide.pdf), or see [here](./MAX78000_MSBL/Docs/Maxim_Bootloader_Tools_UG.pdf) for more up-to-date version.
