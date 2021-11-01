# Secure Loader Project

The secure bootloader allows the end-user of MAX78000 to load an encrypted firmware to MAX78000 based platforms and lock the SWD port. Once it is programmed, the firmware including the CNN model and application code, cannot be extracted from the chip by anyone except for the developer of the firmware who has the keys.

## Programming the [MAX78000](https://www.maximintegrated.com/en/products/microcontrollers/MAX78000.html) with the Bootloader Firmware

_Note: Install [MaximSDK](https://www.maximintegrated.com/en/design/software-description.html/swpart=SFW0010820A#) before following the steps below!_

Use the following steps to program the [MAX78000FTHR](https://www.maximintegrated.com/en/products/microcontrollers/MAX78000FTHR.html) board with bootloader code. For complete list of documentations see [Documentations](#documentations) below.

1. Connect the micro-USB cable to the [MAX78000FTHR](https://www.maximintegrated.com/en/products/microcontrollers/MAX78000FTHR.html) and the PC.
2. Under the `C:\MaximSDK\Tools\MinGW\msys\1.0` directory, double-click on `msys.bat`. This opens a MinGW® window.
3. Navigate to the demo directory by typing:

    ```shell
        cd c: /max78000_demo
    ```

4. To flash the bootloader to the board:

    ```shell
        openocd -s $MAXIM_PATH/tools/OpenOCD/scripts -f interface/cmsis-dap.cfg -f target/max78000.cfg -c 'init ;halt;max32xxx mass_erase 0;program MAX78000_Bootloader_vx_x_x.bin verify reset exit 0x10000000'
    ```

    where x, y and z are bootloader revision.

## Documentations

- See [MAX78000 Secure Bootloader InApplication Programming](./MAX78000_MSBL/Docs/MAX78000_Secure_Bootloader_InApplication_Programming.pdf) for step-by-step instructions of how to use the secure bootloader.

  - There is an example code available under the [MAX78000_Hello_World](./MAX78000_MSBL/MAX78000_Hello_World) to verify the setup. Look at the [README.md](./MAX78000_MSBL/MAX78000_Hello_World/README.md) under the project directory for important information about the `Makefile`.
  - You can find more information for the bootloader and its architecture by referring to [MAX78000 Bootloader User Guide](./MAX78000_MSBL/Docs/MAX78000_Bootloader_UG.pdf).

- Optionally, there is a Bootloader GUI tools available from MaximSDK Maintenance Tools. You have to install [MaximSDK](https://www.maximintegrated.com/en/design/software-description.html/swpart=SFW0010820A#) before you can use this tool.
  
  - The detailed explanations of how to communicate to the bootloader can be found in [UG7510 Maxim Bootloader Tools User Guide](https://pdfserv.maximintegrated.com/en/an/ug7510-maxim-bootloader-tools.pdf), or see [here](./MAX78000_MSBL/Docs/Maxim_Bootloader_Tools_UG.pdf) for more up-to-date version.
