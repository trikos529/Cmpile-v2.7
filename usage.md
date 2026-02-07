# Cmpile Usage Guide

## Introduction
Cmpile is a powerful tool designed to simplify the process of compiling and managing software projects. This guide will walk you through the basic usage of the Cmpile GUI to help you get started quickly.

## Installation
To get started with Cmpile, the process is simple. Simply, build the project as described in the README.md file and run the Cmpile.exe file you will find inside the dist folder to start using Cmpile.

## Usage
Using Cmpile is straightforward. Follow these steps to compile your project:

1.  **Add Source Files**:
    *   Click the **"Add Files"** button to select specific C/C++ files.
    *   Click the **"Add Folder"** button to include all source files within a directory recursively.

2.  **Configure Build Settings**:
    *   **Compiler Flags**: Enter any additional flags (e.g., `-O3 -Wall`) in the flags input field.
    *   **Build Type**:
        *   **Standard Build**: Compiles an executable (`.exe`).
        *   **DLL Build**: Check the **"Build DLL"** checkbox to generate a Shared Library (`.dll`).
        *   **CMake Build**: Check the **"Use CMake"** checkbox to build using CMake (generates `CMakeLists.txt` automatically).
        *   **No Console**: Check **"No Console"** for GUI applications that shouldn't open a terminal window.
    *   **Compiler Selection**:
        *   Use the dropdown menu to choose between **Auto**, **LLVM-MinGW (Clang)**, or **WinLibs (GCC)**.

3.  **Compile**:
    *   Click the **"Compile"** button to start the build process.
    *   On the **first run**, you will be prompted to choose a portable compiler:
        *   **LLVM-MinGW (Clang)**: Modern and fast.
        *   **WinLibs (GCC)**: Classic MinGW-w64 experience.

4.  **Monitor Progress**:
    *   The **Output Window** displays real-time logs.
    *   Any errors or warnings will be highlighted for easy debugging.
    *   Missing dependencies (detected via `#include`) will be automatically installed via `vcpkg`.

5.  **Run**:
    *   Upon success, the executable will be run automatically (unless it's a DLL build).
    *   Output files are located in the `out/` folder (or `build/` for CMake).

## CLI Usage
You can also use Cmpile from the command line (Terminal).

**Basic Syntax:**
```bash
python cmpile.py <files> [options]
```

**Options:**
*   `--compiler <llvm|winlibs|auto>`: Specify which compiler to use. Overrides previous defaults.
*   `--compiler-flags "<flags>"`: Add custom flags (e.g., `-O3`).
*   `--cmake`: Use CMake build system.
*   `--dll`: Build as a shared library.
*   `--clean`: Force a clean build/re-download.

**Examples:**
```bash
# Build with LLVM explicitly
python cmpile.py main.cpp --compiler llvm

# Build with WinLibs and custom flags
python cmpile.py main.cpp --compiler winlibs --compiler-flags "-O2 -Wall"
```

## Features
- **File Management**: Easily add and remove in your project.
- **Customizable Settings**: Tailor the compilation process to fit your specific requirements.
- **Real-time Output**: Monitor the compilation progress and view errors as they occur.
- **User-friendly Interface**: Intuitive design that makes it easy for users of all skill levels to navigate and use the tool.
- **Extension Management**: Manage and install extensions to extend the use and functionality of Cmpile.
- **Package Management**: Manage and install packages according to your needs for your projects thenks to vcpkg.
- **Automatic Dependency Handling**: When installing extensions, all of their dependencies are downloaded automatically for you.
- **Full DLL Support**: Cmpile fully supports DLL files, allowing you to compile projects that rely on dynamic link libraries.
- **Automatic Library Linking**: Cmpile automatically links fetched libraries when compiling executables, eliminating the need for manual configuration.
- **Fetching Libraries**: Cmpile supports fetching libraries from GitHub using the `// @fetch` directive.
- **CMake Support**: Cmpile now supports CMake projects with the `--cmake` option.
- **Multiple Compilers**: Cmpile now supports multiple compilers allowing users to choose their compiler on first run.

## Support
If you ever enounter any issues or have questions about Cmpile, you can open an issue on our GitHub repository. We are here to help and support you in any way we can.