# Cmpile V2

**Cmpile V2** is a zero-configuration C/C++ build tool written in Python. It automatically handles compiler installation (Clang/MinGW) and dependency management (vcpkg) for you.

## Quick Start

 **Prerequisites**: You only need Python 3 installed.
  Install Dependencies: Run pip install -r requirements.txt.
 Install PyInstaller: Run pip install pyinstaller.
  Build: Run pyinstaller CmpileGUI.spec
   ```

On the first run, Cmpile will:
- Download a portable C++ compiler (LLVM-Mingw).
- Download and set up `vcpkg` for library management.
- Detect any `#include` libraries in your code (e.g., `#include <nlohmann/json.hpp>`).
- Install those libraries automatically.
- Compile and run your program.

## Usage

```bash
python cmpile.py [files...] [options]
```

Example:
```bash
python cmpile.py main.cpp utils.cpp --compiler-flags "-O2"
```

### Options
- `--compiler-flags "..."`: Pass extra flags to the compiler.
  - Example: `python cmpile.py main.cpp --compiler-flags "-O3 -Wall"`
- `--clean`: Force a re-check of the environment (useful if downloads get corrupted).
- `-h, --help`: Show help message.

## How it Works

- **Infrastructure**: All tools (compiler, git, vcpkg) are downloaded into the `internal_downloads` folder. To uninstall, simply delete that folder.
- **Dependencies**: The tool scans your C++ file for headers. If it sees a known header (like `fmt/core.h` or `nlohmann/json.hpp`), it installs the corresponding package via vcpkg.

