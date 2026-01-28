import os
import sys
import subprocess
import shlex
import shutil
import concurrent.futures

# Import our modules
import ui
import download_script
import vcpkg_automation
import package_finder
import extensions
import version

# Constants
INTERNAL_DOWNLOADS = download_script.INTERNAL_DOWNLOADS
GCC_BIN = os.path.join(download_script.GCC_DIR, "bin")
GPP_EXE = os.path.join(GCC_BIN, "clang++.exe")
GCC_EXE = os.path.join(GCC_BIN, "clang.exe")
CMAKE_BIN = os.path.join(download_script.CMAKE_DIR, "bin")
CMAKE_EXE = os.path.join(CMAKE_BIN, "cmake.exe")
GIT_CMD = os.path.join(download_script.INTERNAL_DOWNLOADS, "git", "cmd")

def setup_git_env():
    """Adds local git to PATH if present."""
    if not download_script.is_tool_on_path("git") and os.path.exists(GIT_CMD):
        if GIT_CMD not in os.environ["PATH"]:
            os.environ["PATH"] = GIT_CMD + os.pathsep + os.environ["PATH"]
            return True
    return False

def ensure_environment(log_func):
    """Checks and sets up GCC, Git and vcpkg."""
    log_func("Checking environment...")

    # Check/Install Git first
    download_script.install_git(log_func=log_func)
    setup_git_env()

    # Check GCC
    if not (download_script.is_tool_on_path("clang") or download_script.is_tool_on_path("gcc")):
        if not os.path.exists(GPP_EXE):
            log_func("GCC not found. Installing...")
            try:
                download_script.install_gcc(log_func=log_func)
            except Exception as e:
                log_func(f"Failed to install GCC: {e}", "bold red")
                raise e

    # Add internal GCC to PATH if no system compiler is found
    if not (download_script.is_tool_on_path("clang") or download_script.is_tool_on_path("gcc")):
        if GCC_BIN not in os.environ["PATH"]:
            os.environ["PATH"] = GCC_BIN + os.pathsep + os.environ["PATH"]

    # Check CMake
    if not download_script.is_tool_on_path("cmake"):
        if not os.path.exists(CMAKE_EXE):
            log_func("CMake not found. Installing...")
            try:
                download_script.install_cmake(log_func=log_func)
            except Exception as e:
                log_func(f"Failed to install CMake: {e}", "bold red")
                raise e
        
        if os.path.exists(CMAKE_BIN) and CMAKE_BIN not in os.environ["PATH"]:
            os.environ["PATH"] = CMAKE_BIN + os.pathsep + os.environ["PATH"]

    # Check vcpkg
    vcpkg_mgr = vcpkg_automation.VcpkgManager(INTERNAL_DOWNLOADS, log_func=log_func)
    if not vcpkg_mgr.is_installed() and not download_script.is_tool_on_path("vcpkg"):
        log_func("vcpkg not found. Installing...")
        try:
            download_script.install_vcpkg(git_path_env=GIT_CMD, log_func=log_func)
        except Exception as e:
            log_func(f"Failed to install vcpkg: {e}", "bold red")
            raise e

    return vcpkg_mgr

def get_compiler_for_file(filepath):
    """Returns the appropriate compiler executable."""
    if filepath.endswith(('.c', '.C')):
        if download_script.is_tool_on_path("clang"): return "clang"
        if download_script.is_tool_on_path("gcc"): return "gcc"
        return GCC_EXE

    if download_script.is_tool_on_path("clang++"): return "clang++"
    if download_script.is_tool_on_path("g++"): return "g++"
    return GPP_EXE

class CmpileBuilder:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback

    def log(self, message, style=""):
        if self.log_callback:
            self.log_callback(message, style)
        else:
            # Fallback to UI print if no callback (CLI mode)
            if "error" in style or "bold red" in style:
                ui.display_error(message)
            elif "success" in style or "bold green" in style:
                ui.display_success(message)
            else:
                ui.display_status(message)

    def copy_runtime_dlls(self, vcpkg_mgr, output_folder, required_packages):
        """Copies DLLs from vcpkg bin folder to output directory for all required packages."""
        if not required_packages:
            return

        bin_path = vcpkg_mgr.get_bin_path()
        if not os.path.exists(bin_path):
            return
            
        for f in os.listdir(bin_path):
            if f.endswith(".dll"):
                try:
                    shutil.copy(os.path.join(bin_path, f), os.path.join(output_folder, f))
                except Exception:
                    pass

    def build_and_run(self, source_files, compiler_flags=None, clean=False, run=True, extra_includes=None, extra_lib_paths=None, extra_link_flags=None, build_dll=False):

        expanded_files = []
        for path in source_files:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(('.c', '.cpp', '.C', '.CPP', '.cc', '.cxx')):
                            expanded_files.append(os.path.join(root, file))
            elif os.path.isfile(path):
                expanded_files.append(path)

        if not expanded_files:
            self.log("No valid source files found.", "bold red")
            return False

        files = [os.path.abspath(f) for f in expanded_files]
        for path in files:
            if not os.path.exists(path):
                self.log(f"File not found: {path}", "bold red")
                return False

        # 1. Environment Setup
        try:
            vcpkg_mgr = ensure_environment(self.log)
        except Exception as e:
            self.log(f"Environment setup failed: {e}", "bold red")
            return False

        # 1.5 GitHub Fetches (CMake-like FetchContent)
        ext_mgr = extensions.ExtensionManager()
        fetched_extensions_map = {} # repo_url -> ext
        
        # Scan for @fetch directives in all source files
        for src in files:
            fetches = package_finder.find_github_fetches(src)
            for repo_url, version in fetches:
                key = f"{repo_url}@{version}"
                if key in fetched_extensions_map:
                    continue
                    
                self.log(f"Detected fetch directive: {repo_url} @ {version}")
                ext = extensions.GitHubFetchExtension(repo_url, version)
                if not ext.is_installed():
                    try:
                        ext.install(progress_callback=self.log)
                    except Exception as e:
                        self.log(f"Failed to fetch {repo_url}: {e}", "bold red")
                        return False
                else:
                    ext.auto_detect_paths()
                
                fetched_extensions_map[key] = ext
        
        fetched_extensions = list(fetched_extensions_map.values())
        
        # Add fetched extensions to includes and libs
        if not extra_includes: extra_includes = []
        if not extra_lib_paths: extra_lib_paths = []
        if not extra_link_flags: extra_link_flags = []

        for ext in fetched_extensions:
            inc = ext.get_include_path()
            if inc:
                self.log(f"Adding include path: {inc}")
                if inc not in extra_includes:
                    extra_includes.append(inc)
            
            lib = ext.get_lib_path()
            if lib:
                self.log(f"Adding lib path: {lib}")
                if lib not in extra_lib_paths:
                    extra_lib_paths.append(lib)
            
            flags = ext.get_link_flags()
            if flags:
                self.log(f"Adding link flags: {', '.join(flags)}")
                for flag in flags:
                    if flag not in extra_link_flags:
                        extra_link_flags.append(flag)

        # 2. Dependency Analysis
        all_includes = set()
        for src in files:
            self.log(f"Analyzing {os.path.basename(src)}...")
            includes = package_finder.find_includes(src)
            all_includes.update(includes)

        # Filter out includes that are already provided by fetched extensions
        external_includes = set()
        for inc in all_includes:
            found_in_fetch = False
            for ext in fetched_extensions:
                ext_inc_path = ext.get_include_path()
                if ext_inc_path:
                    check_path = os.path.join(ext_inc_path, inc)
                    if os.path.exists(check_path):
                        found_in_fetch = True
                        self.log(f"Include '{inc}' found in fetched extension '{ext.name}'.")
                        break
            if not found_in_fetch:
                external_includes.add(inc)

        required_packages = package_finder.map_includes_to_packages(external_includes)

        if required_packages:
            # Filter out packages that are already being linked explicitly via extensions
            filtered_packages = set()
            for pkg in required_packages:
                is_provided = False
                if extra_link_flags:
                     for flag in extra_link_flags:
                         # Heuristic: if -lraylib is present, don't vcpkg install raylib
                         if flag == f"-l{pkg}":
                             is_provided = True
                             self.log(f"Package '{pkg}' is provided by extensions/flags. Skipping vcpkg install.")
                             break
                if not is_provided:
                    filtered_packages.add(pkg)
            
            if filtered_packages:
                self.log(f"Identified dependencies: {', '.join(filtered_packages)}")
                for pkg in filtered_packages:
                     if vcpkg_mgr.is_package_installed(pkg):
                         continue
                     if not vcpkg_mgr.install_package(pkg):
                         self.log(f"Failed to install dependency: {pkg}", "bold red")
                         return False # Stop if dependency fails
            else:
                self.log("Dependencies provided by extensions.")
        else:
            self.log("No external dependencies detected.")

        # 3. Compilation
        self.log("Compiling..." if not build_dll else "Compiling DLL...")

        if not files:
            self.log("No valid source files found.", "bold red")
            return False

        # Determine project root based on the first source file
        project_root = os.path.dirname(files[0])
        OUT_DIR = os.path.join(project_root, "out")
        
        if clean and os.path.exists(OUT_DIR):
             self.log("Cleaning output directory...", "bold yellow")
             try:
                 shutil.rmtree(OUT_DIR)
             except Exception as e:
                 self.log(f"Failed to clean output directory: {e}", "bold red")

        if not os.path.exists(OUT_DIR):
            os.makedirs(OUT_DIR)

        object_files = []

        include_path = vcpkg_mgr.get_include_path()
        lib_path = vcpkg_mgr.get_lib_path()

        base_compile_flags = []
        if os.path.exists(include_path):
            base_compile_flags.extend(["-I", include_path])
        if extra_includes:
            for inc in extra_includes:
                base_compile_flags.extend(["-I", inc])
        if compiler_flags:
            try:
                base_compile_flags.extend(shlex.split(compiler_flags))
            except:
                base_compile_flags.extend(compiler_flags.split())

        # Helper function for parallel compilation
        def compile_single_file(src):
            compiler = get_compiler_for_file(src)
            base_name = os.path.basename(src)
            obj_name = os.path.splitext(base_name)[0] + ".o"
            obj_path = os.path.join(OUT_DIR, obj_name)
            dep_path = os.path.join(OUT_DIR, os.path.splitext(base_name)[0] + ".d")
            
            # Check if recompile is needed
            needs_recompile = True
            if os.path.exists(obj_path) and not clean:
                is_up_to_date = False
                # 1. Check source modification time
                if os.path.getmtime(src) < os.path.getmtime(obj_path):
                    is_up_to_date = True
                    
                    # 2. Check header dependencies if .d file exists
                    if os.path.exists(dep_path):
                        try:
                            with open(dep_path, 'r') as f:
                                content = f.read().replace('\\\n', '')
                                # Parse makefile rule: target: dep1 dep2 ...
                                if ':' in content:
                                    deps = content.split(':')[1].split()
                                    obj_mtime = os.path.getmtime(obj_path)
                                    for dep in deps:
                                        dep = dep.strip()
                                        if dep and os.path.exists(dep):
                                            if os.path.getmtime(dep) > obj_mtime:
                                                is_up_to_date = False
                                                break
                        except Exception:
                            # If we fail to read deps, assume we need to recompile
                            is_up_to_date = False
                
                if is_up_to_date:
                    return (obj_path, False, f"Skipping {base_name} (up to date)", None)

            cmd = [compiler, "-c", src, "-o", obj_path, "-MMD", "-MF", dep_path] + base_compile_flags
            try:
                # Capture stderr to show compile errors
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                log_msg = f"Compiling {base_name}..."
                if result.stderr:
                     return (obj_path, True, log_msg, result.stderr)
                return (obj_path, True, log_msg, None)
            except subprocess.CalledProcessError as e:
                return (None, True, f"Compilation failed for {src}.", e.stderr)

        compilation_failed = False
        self.log(f"Compiling {len(files)} files...")
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Map returns results in order
            results = executor.map(compile_single_file, files)
            
            for src, (obj_path, was_compiled, log_msg, error_msg) in zip(files, results):
                if log_msg:
                    self.log(log_msg)
                
                if error_msg:
                    self.log(error_msg, "bold red")
                    if obj_path is None: # Critical failure
                         compilation_failed = True
                
                if obj_path:
                    object_files.append(obj_path)
                else:
                    compilation_failed = True

        if compilation_failed:
            return False

        # Link
        self.log("Linking...")

        cpp_in_use = any(get_compiler_for_file(src) in [GPP_EXE, "g++", "clang++"] for src in files)
        if cpp_in_use:
            if download_script.is_tool_on_path("clang++"): linker = "clang++"
            elif download_script.is_tool_on_path("g++"): linker = "g++"
            else: linker = GPP_EXE
        else:
            if download_script.is_tool_on_path("clang"): linker = "clang"
            elif download_script.is_tool_on_path("gcc"): linker = "gcc"
            else: linker = GCC_EXE

        exe_name = os.path.splitext(os.path.basename(files[0]))[0]
        output_implib = None

        if build_dll:
            if os.name == 'nt':
                exe_name += ".dll"
                # Create an import library (lib<name>.a) for MinGW/Clang
                implib_name = "lib" + os.path.splitext(os.path.basename(files[0]))[0] + ".a"
                output_implib = os.path.join(OUT_DIR, implib_name)
            else:
                exe_name += ".so"
        else:
            exe_name += ".exe"
            
        # Output executable in the source directory (project root), not in 'out' folder
        output_exe = os.path.join(project_root, exe_name)

        cmd = [linker] + object_files + ["-o", output_exe]
        
        if build_dll:
            cmd.append("-shared")
            if output_implib:
                cmd.append(f"-Wl,--out-implib,{output_implib}")
            
        if os.path.exists(lib_path):
            cmd.extend(["-L", lib_path])
        
        if extra_lib_paths:
            for lib in extra_lib_paths:
                cmd.extend(["-L", lib])

        # Add required libraries. This is a simplified approach.
        # A more robust solution would involve checking vcpkg's installed files.
        if required_packages:
            for pkg in required_packages:
                 if pkg == "nlohmann-json": continue
                 
                 # Check for explicit library mapping (e.g. for qtbase -> Qt6Widgets, etc.)
                 if hasattr(package_finder, 'PACKAGE_LIBS') and pkg in package_finder.PACKAGE_LIBS:
                     for lib in package_finder.PACKAGE_LIBS[pkg]:
                         cmd.append(f"-l{lib}")
                     continue

                 # Dynamic library searching
                 lib_name = pkg
                 if os.path.exists(lib_path):
                     # Priority: 1. lib{pkg}dll.a (DLL import lib), 2. lib{pkg}.a (Static/Import), 3. {pkg}.lib (MSVC style)
                     candidates = [f"lib{pkg}dll.a", f"lib{pkg}.a", f"{pkg}.lib"]
                     found_cand = False
                     for cand in candidates:
                         if os.path.exists(os.path.join(lib_path, cand)):
                             # Convert filename to -l format
                             if cand.startswith("lib") and cand.endswith(".a"):
                                 lib_name = cand[3:-2]
                             elif cand.endswith(".lib"):
                                 # For .lib files, we might need to pass the full path or just the name depending on linker
                                 # MinGW often handles .lib, but -l syntax prefers stripping extension
                                 lib_name = cand[:-4]
                             found_cand = True
                             break
                     
                     if not found_cand:
                        # Fallback: Search for any file starting with lib{pkg}
                        for f in os.listdir(lib_path):
                            if f.startswith(f"lib{pkg}") and f.endswith(".a"):
                                lib_name = f[3:-2]
                                break

                 cmd.append(f"-l{lib_name}")

        if extra_link_flags:
            cmd.extend(extra_link_flags)

        cmd.extend(["-static-libgcc", "-static-libstdc++"])

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.stderr:
                self.log(result.stderr, "bold red")
            self.log("Build successful!", "bold green")

            # Copy runtime DLLs for both executables and DLLs so they are self-contained
            self.copy_runtime_dlls(vcpkg_mgr, os.path.dirname(output_exe), required_packages)

        except subprocess.CalledProcessError as e:
            self.log("Linking failed.", "bold red")
            self.log(e.stderr, "bold red")
            return False

        if run and not build_dll:
            self.log("Running...", "bold")

            env = os.environ.copy()
            bin_path = vcpkg_mgr.get_bin_path()
            if os.path.exists(bin_path):
                env["PATH"] = bin_path + os.pathsep + env["PATH"]

            try:
                p = subprocess.Popen([output_exe], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, encoding='utf-8', errors='replace')

                # Stream output
                if p.stdout:
                    for line in iter(p.stdout.readline, ''):
                        if line.strip(): self.log(line.strip())

                # Check for errors after execution
                p.wait()
                if p.returncode != 0:
                    err_data = p.stderr.read() if p.stderr else ""
                    if err_data.strip():
                        self.log(f"Execution finished with return code {p.returncode}", "bold red")
                        self.log(err_data.strip(), "bold red")

            except Exception as e:
                self.log(f"Execution error: {e}", "bold red")
        elif build_dll:
            self.log(f"DLL created at: {output_exe}", "bold blue")
            if output_implib and os.path.exists(output_implib):
                 pass

        return True

def main():
    print(f"╭──────────────╮\n│ Cmpile V{version.VERSION} │\n╰──────────────╯")
    args = ui.parse_arguments()

    # Define a logger for the CLI that maps to the `ui` functions
    def cli_logger(message, style=""):
        if "error" in style or "bold red" in style:
            ui.display_error(message)
        elif "success" in style or "bold green" in style:
            ui.display_success(message)
        else:
            ui.display_status(message)

    # In CLI mode, the builder is provided with our CLI logger
    builder = CmpileBuilder(log_callback=cli_logger)
    builder.build_and_run(args.files, args.compiler_flags, args.clean, run=True, build_dll=args.dll)

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception as e:
        print(f"Critical Error: {e}")

    if (len(sys.argv) > 1 or getattr(sys, 'frozen', False)) and not any('gui' in arg.lower() for arg in sys.argv):
         print("\n")
         input("Press Enter to exit...")