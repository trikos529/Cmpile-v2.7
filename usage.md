# Cmpile Usage Guide

## Introduction
Cmpile is a powerful tool designed to simplify the process of compiling and managing software projects. This guide will walk you through the basic usage of the Cmpile GUI to help you get started quickly.

## Installation
To get started with Cmpile, the process is simple. Simply, build the project as described in the README.md file and run the Cmpile.exe file you will find inside the dist folder to start using Cmpile.

## Usage
Cmpile is easy and simple to use. You first need to add the files you want to compile to the file list. You can do this by clicking the "Add Files" button and selecting the desired files from your system. You can add mutliple files at once if needed. There is also the option to add a whole folder by clicking the "Add Folder" button. This will include all files within the selected folder to the file list.
Once you have added the files, you can configure the compilation settings according to your needs. You can select the compiler options, and set any additional parameters required for your project. Once you have configured the settings, you can start the compilation process by clicking the "Compile" button. Additionally, you can build a DLL instead of an executable by checking the "Build DLL" checkbox before starting the compilation if you want to.
The progress of the compilation will be displayed in the output window, allowing you to monitor the process in real-time. If any errors occur during compilation, they will be highlighted in the output window for easy identification and troubleshooting. All that's left is to wait for the compilation to complete. Once finished, you can find the compiled files in the specified output directory. And that's it! You've successfully used Cmpile to compile your project.

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

## Support
If you ever enounter any issues or have questions about Cmpile, you can open an issue on our GitHub repository. We are here to help and support you in any way we can.