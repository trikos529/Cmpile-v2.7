import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
import version

console = Console()

def parse_arguments():
    parser = argparse.ArgumentParser(description=f"Cmpile V{version.VERSION} - Compile and Run C/C++ code with ease.")
    parser.add_argument("files", nargs='+', help="The C or C++ files or folders to compile and run.")
    parser.add_argument("--compiler-flags", help="Additional compiler flags (quoted string).", default="")
    parser.add_argument("--clean", action="store_true", help="Force clean build (re-download/re-install if needed).")
    parser.add_argument("--dll", action="store_true", help="Build as a Shared Library (DLL)")
    parser.add_argument("--no-console", action="store_true", help="Do not create a console window for the application (Windows only).")
    parser.add_argument("--cmake", action="store_true", help="Use CMake to build the project.")
    parser.add_argument("--compiler", choices=['llvm', 'winlibs', 'auto'], default=None, help="Specify compiler preference (llvm or winlibs).")
    return parser.parse_args()

def get_compiler_choice(log_func=None):
    """Prompts the user to select a compiler."""
    # Check if we have a valid stdin
    if sys.stdin is None or not sys.stdin.isatty():
        msg = "No compiler found. Defaulting to LLVM-MinGW (Clang) because input is not available."
        if log_func:
            log_func(msg, "yellow")
        else:
            console.print(f"[yellow]{msg}[/yellow]")
        return "llvm"

    console.print("[yellow]No compiler found. Please select one to install:[/yellow]")
    console.print("1. [bold green]LLVM-MinGW (Clang)[/bold green] - Portable Clang-based compiler. Fast and modern.")
    console.print("2. [bold blue]WinLibs (GCC)[/bold blue] - Portable GCC-based compiler. Classic MinGW-w64 experience.")
    
    choice = Prompt.ask("Enter choice", choices=["1", "2"], default="1")
    return "llvm" if choice == "1" else "winlibs"

def display_header():
    console.print(Panel.fit(f"[bold cyan]Cmpile V{version.VERSION}[/bold cyan]", border_style="cyan"))

def display_status(message, style="bold blue"):
    console.print(f"[{style}]{message}[/{style}]")

def display_error(message):
    console.print(f"[bold red]Error: {message}[/bold red]")

def display_success(message):
    console.print(f"[bold green]{message}[/bold green]")

def get_user_confirmation(prompt_message):
    if sys.stdin is None or not sys.stdin.isatty():
        # Assume yes in non-interactive mode
        console.print(f"[yellow]Automatically confirming '{prompt_message}' because input is not available.[/yellow]")
        return True
    return Confirm.ask(f"[yellow]{prompt_message}[/yellow]")
