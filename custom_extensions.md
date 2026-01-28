# Custom Extensions Guide

## Introduction
The Custom Extensions feature in Cmpile allows you to integrate external C/C++ libraries that are stored locally on your machine, bypassing the automatic dependency management system (vcpkg). This is particularly useful for proprietary libraries, custom-built frameworks, or libraries that are not available in the public registry.

## How to Add a Custom Extension

1. **Open the Extensions Tab**
   Launch Cmpile and navigate to the **Extensions** tab in the main interface.

2. **Open the Add Dialog**
   Click the **Add Custom Extension** button located at the top right of the panel.

3. **Fill in the Details**
   A dialog will appear asking for the following information:
   
   - **Extension Name**: A unique name for your extension (e.g., `MyPhysicsEngine`).
   - **Include Path**: The directory containing the header files (`.h`, `.hpp`).
     - *Example*: `C:\Libraries\PhysX\include`
   - **Library Path**: The directory containing the compiled library files (`.a`, `.lib`).
     - *Example*: `C:\Libraries\PhysX\lib`
   - **Linker Flags**: The specific flags required to link against the library, separated by spaces.
     - *Example*: `-lPhysX -lPhysXCommon`
     - *Note*: Usually, you provide the library name prefixed with `-l` (e.g., for `libPhysX.a`, use `-lPhysX`).

4. **Save**
   Click **Add Extension**. The new extension will appear in the list with a status of "Installed".

## Using Custom Extensions
Once added, the custom extension is automatically included in your build configuration. When you click **Build & Run**:
- The **Include Path** is automatically added to the compiler's search paths (`-I`).
- The **Library Path** is automatically added to the linker's search paths (`-L`).
- The **Linker Flags** are passed to the linker to ensure the library is linked correctly.

## Managing Extensions
- **Uninstall/Remove**: To remove a custom extension, simply click the **Uninstall** button next to it in the list.
  - *Note*: This only removes the configuration entry from Cmpile. It **does not delete** your actual library files from your disk.
- **Persistence**: Your custom extensions are saved in `extensions/custom_extensions.json` and will be loaded automatically the next time you launch Cmpile.