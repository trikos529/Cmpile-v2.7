# Cmpile V2

**Cmpile V2** is a zero-configuration C/C++ build tool written in Python. It automatically handles compiler installation (Clang/MinGW) and dependency management (vcpkg) for you.

## Quick Start

 You only need Python 3 installed.
 
  Install Dependencies: Run pip install -r requirements.txt.
  
  Install PyInstaller: Run pip install pyinstaller.
  
  Build: Run pyinstaller CmpileGUI.spec
  
On the first run, Cmpile will:
- Download a portable C++ compiler (LLVM-Mingw).
- Download and set up `vcpkg` for library management.
- Download and add Git to PATH for cloning other dependencies.
- Download and add Cmake to PATH for building dependencies and extensions.
- Detect any `#include` libraries in your code (e.g., `#include <nlohmann/json.hpp>`).
- If needed, you may install any of the available extensions from the Extensions tab.
- Install those libraries automatically.
- Compile and run your program.

### Options
- `--compiler-flags "..."`: Pass extra flags to the compiler.
  - Example: `python cmpile.py main.cpp --compiler-flags "-O3 -Wall"`
- `--clean`: Force a re-check of the environment (useful if downloads get corrupted).
- `-h, --help`: Show help message.

## How it Works

- **Infrastructure**: All tools (compiler, git, vcpkg) are downloaded into the `internal_downloads` folder. To uninstall, simply delete that folder.
- **Dependencies**: The tool scans your C++ file for headers. If it sees a known header (like `fmt/core.h` or `nlohmann/json.hpp`), it installs the corresponding package via vcpkg.

## What's New
 # Version 2.5
  - Added Cmake as a dependency to download after the first run.
  - New Extensions are now available.
  - Added more packages to the package finder.
  - Removed Cmake as a standalone download dependency from all extensions.
  - Improved stability issues.
  - Fixed some errors when bootstrapping vcpkg.
  - Updated all Extensions to their latest versions.
  - Rebranded to Version 2.5.
 # Version 2.4
  - Added version number visibility next to each one of the extensions.
  - Added a new Uninstall button to the Extensions tab for uninstalling extensions easier instead of deleting the files manually.
  - More extensions in the Extensions tab are now available.
  - Added more packages to the package finder.
  - Fixed some errors when downloading essential files for the compiler.
  - When extensions are deleted manually, the page now refreshes instantly without a restart.
  - Rebranded to Version 2.4
 # Version 2.3
  - Fixed some errors with dependency installtion.
  - Some other bugs fixes and improvements.
  - Added dependencies for extensions to be downloaded automatically.
  - Updated Compiler (LLVM-MinGW) and Git to latest version.
  - Updated Extensions to their latest versions.
  - Added more packages to package finder.
  - Rebranded to Version 2.3.
 # Version 2.2
  - Added a new feature called Extensions. You can now install extensions to add packages to your project without needing them to download from vcpkg.
  - For now, added two extensions but more will be added in later updates.
  - Added the ability to add custom extensions from local files.
  - Added a new "Clear Log Output" button to the GUI.
  - Rebranded to Version 2.2.