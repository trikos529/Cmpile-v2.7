import customtkinter as ctk
import os
import threading
from tkinter import filedialog
import cmpile
import sys
import extensions

# Set theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cmpile V2.2")
        self.geometry("900x650")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -- Sidebar --
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Cmpile V2.2", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Main Actions are now relative to the active tab, or global?
        # Keeping them global for the "Build" flow as they manipulate the file list which is in Build tab.
        # But "Extensions" tab has different actions.
        # Ideally, sidebar buttons should control the "Build" tab context if that's the primary functions.
        
        self.add_file_btn = ctk.CTkButton(self.sidebar_frame, text="Add Files", command=self.add_files)
        self.add_file_btn.grid(row=1, column=0, padx=20, pady=10)

        self.add_folder_btn = ctk.CTkButton(self.sidebar_frame, text="Add Folder", command=self.add_folder)
        self.add_folder_btn.grid(row=2, column=0, padx=20, pady=10)

        self.clear_btn = ctk.CTkButton(self.sidebar_frame, text="Clear List", fg_color="transparent", border_width=2, command=self.clear_files)
        self.clear_btn.grid(row=3, column=0, padx=20, pady=10)

        self.clear_log_btn = ctk.CTkButton(self.sidebar_frame, text="Clear Output Log", fg_color="transparent", border_width=2, command=self.clear_log)
        self.clear_log_btn.grid(row=4, column=0, padx=20, pady=10)

        self.quit_button = ctk.CTkButton(self.sidebar_frame, text="Quit", fg_color="transparent", border_width=2, command=self.quit)
        self.quit_button.grid(row=6, column=0, padx=20, pady=10, sticky="s")

        # -- Main Content Area (Tabview) --
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=1, padx=20, pady=10, sticky="nsew")
        self.tabview.add("Build")
        self.tabview.add("Extensions")
        
        # Configure Grid for Tabs
        self.tabview.tab("Build").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Build").grid_rowconfigure(1, weight=1) # File list expands
        self.tabview.tab("Extensions").grid_columnconfigure(0, weight=1)

        # -- BUILD TAB CONTENT --
        self.setup_build_tab()

        # -- EXTENSIONS TAB CONTENT --
        self.setup_extensions_tab()

        # Logic
        self.source_files = []
        self.builder = cmpile.CmpileBuilder(log_callback=self.log_message)
        self.extension_manager = extensions.ExtensionManager()
        
        # Initialize extension list UI
        self.refresh_extension_list()

    def setup_build_tab(self):
        tab = self.tabview.tab("Build")
        
        self.file_list_label = ctk.CTkLabel(tab, text="Source Files", anchor="w")
        self.file_list_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10,0))

        self.file_textbox = ctk.CTkTextbox(tab, height=150)
        self.file_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.file_textbox.configure(state="disabled")

        self.options_frame = ctk.CTkFrame(tab)
        self.options_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.flags_entry = ctk.CTkEntry(self.options_frame, placeholder_text="Compiler Flags (e.g. -O2 -Wall)")
        self.flags_entry.pack(side="left", expand=True, fill="x", padx=10, pady=10)

        self.clean_checkbox = ctk.CTkCheckBox(self.options_frame, text="Clean Build")
        self.clean_checkbox.pack(side="left", padx=10, pady=10)

        self.build_btn = ctk.CTkButton(self.options_frame, text="Build & Run", command=self.start_build, fg_color="green", hover_color="darkgreen")
        self.build_btn.pack(side="right", padx=10, pady=10)

        self.log_label = ctk.CTkLabel(tab, text="Output Log", anchor="w")
        self.log_label.grid(row=3, column=0, sticky="w", padx=10)

        self.log_textbox = ctk.CTkTextbox(tab, height=200, font=("Consolas", 12))
        self.log_textbox.grid(row=4, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.log_textbox.configure(state="disabled")

    def setup_extensions_tab(self):
        tab = self.tabview.tab("Extensions")
        
        # Header / Controls
        ctrl_frame = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(ctrl_frame, text="Compiler Path (Optional Override):").pack(side="left", padx=(0,10))
        self.compiler_path_entry = ctk.CTkEntry(ctrl_frame, placeholder_text="Path to compiler (bin folder)...", width=300)
        self.compiler_path_entry.pack(side="left")
        
        self.install_all_btn = ctk.CTkButton(ctrl_frame, text="Install All Extensions", command=self.install_all_extensions)
        self.install_all_btn.pack(side="right")

        self.add_custom_btn = ctk.CTkButton(ctrl_frame, text="Add Custom Extension", fg_color="gray", command=self.add_custom_extension_dialog)
        self.add_custom_btn.pack(side="right", padx=10)

        # List of Extensions
        self.ext_scroll_frame = ctk.CTkScrollableFrame(tab, label_text="Available Extensions")
        self.ext_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_extension_list(self):
        # Clear existing
        for widget in self.ext_scroll_frame.winfo_children():
            widget.destroy()

        # Add items
        for ext in self.extension_manager.get_all_extensions():
            self.create_extension_item(ext)

    def create_extension_item(self, ext):
        item_frame = ctk.CTkFrame(self.ext_scroll_frame)
        item_frame.pack(fill="x", padx=5, pady=5)

        name_lbl = ctk.CTkLabel(item_frame, text=ext.name, font=("Arial", 16, "bold"))
        name_lbl.pack(side="left", padx=10, pady=10)

        status_text = "Installed" if ext.is_installed() else "Not Installed"
        status_color = "green" if ext.is_installed() else "gray"
        
        status_lbl = ctk.CTkLabel(item_frame, text=status_text, text_color=status_color)
        status_lbl.pack(side="left", padx=10)

        if not ext.is_installed():
            install_btn = ctk.CTkButton(item_frame, text="Install", width=100, 
                                        command=lambda e=ext: self.install_extension(e))
            install_btn.pack(side="right", padx=10)
            
            # Manual path button
            path_btn = ctk.CTkButton(item_frame, text="Set Path", width=100, fg_color="gray",
                                     command=lambda e=ext: self.set_extension_path(e))
            path_btn.pack(side="right", padx=5)
        else:
             ctk.CTkLabel(item_frame, text=f"Path: {ext.path}", font=("Arial", 10)).pack(side="bottom", anchor="w", padx=10, pady=(0,5))

    def set_extension_path(self, ext):
        path = filedialog.askdirectory(title=f"Select {ext.name} directory")
        if path:
            if ext.set_manual_path(path):
                self.log_message(f"Path set for {ext.name}", "success")
                self.refresh_extension_list()
            else:
                self.log_message(f"Invalid path for {ext.name}. Could not find required files.", "error")

    def install_extension(self, ext):
        self.log_message(f"Installing {ext.name}...", "info")
        # Run in thread
        t = threading.Thread(target=self._run_install, args=(ext,))
        t.start()
    
    def install_all_extensions(self):
        self.log_message("Installing all extensions...", "info")
        t = threading.Thread(target=self._run_install_all)
        t.start()

    def _run_install(self, ext):
        def progress(msg):
             self.log_message(msg)
        try:
            ext.install(progress_callback=progress)
            self.after(0, self.refresh_extension_list)
        except Exception as e:
            self.log_message(str(e), "error")

    def _run_install_all(self):
        def progress(msg):
             self.log_message(msg)
        try:
            self.extension_manager.install_all(progress_callback=progress)
            self.after(0, self.refresh_extension_list)
        except Exception as e:
            self.log_message(str(e), "error")

    def add_custom_extension_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Custom Extension")
        dialog.geometry("500x400")
        
        # Make modal
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Add Custom Extension", font=("Arial", 18, "bold")).pack(pady=10)
        
        # Name
        ctk.CTkLabel(dialog, text="Extension Name:").pack(anchor="w", padx=20)
        name_entry = ctk.CTkEntry(dialog)
        name_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        # Include Path
        ctk.CTkLabel(dialog, text="Include Path (Folder containing headers):").pack(anchor="w", padx=20)
        inc_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        inc_frame.pack(fill="x", padx=20, pady=(0, 10))
        inc_entry = ctk.CTkEntry(inc_frame)
        inc_entry.pack(side="left", fill="x", expand=True)
        def browse_inc():
            p = filedialog.askdirectory()
            if p:
                inc_entry.delete(0, "end")
                inc_entry.insert(0, p)
        ctk.CTkButton(inc_frame, text="Browse", width=60, command=browse_inc).pack(side="right", padx=(10, 0))
        
        # Lib Path
        ctk.CTkLabel(dialog, text="Library Path (Folder containing .a/.lib):").pack(anchor="w", padx=20)
        lib_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        lib_frame.pack(fill="x", padx=20, pady=(0, 10))
        lib_entry = ctk.CTkEntry(lib_frame)
        lib_entry.pack(side="left", fill="x", expand=True)
        def browse_lib():
            p = filedialog.askdirectory()
            if p:
                lib_entry.delete(0, "end")
                lib_entry.insert(0, p)
        ctk.CTkButton(lib_frame, text="Browse", width=60, command=browse_lib).pack(side="right", padx=(10, 0))
        
        # Flags
        ctk.CTkLabel(dialog, text="Linker Flags (e.g. -lraylib -lgdi32):").pack(anchor="w", padx=20)
        flags_entry = ctk.CTkEntry(dialog)
        flags_entry.pack(fill="x", padx=20, pady=(0, 20))
        
        def submit():
            name = name_entry.get().strip()
            inc = inc_entry.get().strip()
            lib = lib_entry.get().strip()
            flags_str = flags_entry.get().strip()
            
            if not name or not inc or not lib:
                self.log_message("Error: Name, Include Path, and Lib Path are required.", "error")
                return
            
            flags = flags_str.split()
            
            ext = extensions.CustomExtension(name, inc, lib, flags)
            self.extension_manager.add_extension(ext)
            self.refresh_extension_list()
            self.log_message(f"Custom extension '{name}' added.", "success")
            dialog.destroy()
            
        ctk.CTkButton(dialog, text="Add Extension", command=submit, fg_color="green").pack(pady=10)

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("C/C++ Files", "*.c *.cpp *.h *.hpp")])
        if files:
            for f in files:
                if f not in self.source_files:
                    self.source_files.append(f)
            self.refresh_file_list()

    def add_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            if folder not in self.source_files:
                self.source_files.append(folder)
            self.refresh_file_list()

    def clear_files(self):
        self.source_files = []
        self.refresh_file_list()

    def clear_log(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")

    def refresh_file_list(self):
        self.file_textbox.configure(state="normal")
        self.file_textbox.delete("0.0", "end")
        for f in self.source_files:
            self.file_textbox.insert("end", f"{os.path.basename(f)}  ({f})\n")
        self.file_textbox.configure(state="disabled")

    def log_message(self, message, style=""):
        self.after(0, lambda: self._append_log(message, style))

    def _append_log(self, message, style):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
        # Ensure build tab is visible if logging error? Maybe not force switch.

    def start_build(self):
        if not self.source_files:
            self.log_message("Please select source files first!", "error")
            return

        flags = self.flags_entry.get()
        clean = self.clean_checkbox.get() == 1
        
        # Check for compiler override
        compiler_override = self.compiler_path_entry.get().strip()
        if compiler_override:
            # Need to pass this to builder.
            # Currently CmpileBuilder doesn't accept it easily, need to modify CmpileBuilder or modify os.environ
            os.environ["PATH"] = compiler_override + os.pathsep + os.environ["PATH"]

        self.build_btn.configure(state="disabled")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")

        thread = threading.Thread(target=self.run_build_process, args=(flags, clean))
        thread.start()

    def run_build_process(self, flags, clean):
        try:
            # Gather extensions info
            ext_includes = []
            ext_libs = []
            ext_flags = []
            
            for ext in self.extension_manager.get_all_extensions():
                if ext.is_installed():
                    inc = ext.get_include_path()
                    lib = ext.get_lib_path()
                    lnk = ext.get_link_flags()
                    if inc: ext_includes.append(inc)
                    if lib: ext_libs.append(lib)
                    if lnk: ext_flags.extend(lnk)
            
            # Pass these to builder
            self.builder.build_and_run(
                self.source_files, 
                compiler_flags=flags, 
                clean=clean, 
                run=True,
                extra_includes=ext_includes,
                extra_lib_paths=ext_libs,
                extra_link_flags=ext_flags
            )
        except Exception as e:
            self.log_message(f"A critical error occurred: {e}", "error")
        finally:
            self.after(0, lambda: self.build_btn.configure(state="normal"))

    def quit(self):
        self.destroy()

if __name__ == "__main__":
    try:
        import multiprocessing
        multiprocessing.freeze_support()
    except:
        pass

    app = App()
    app.mainloop()