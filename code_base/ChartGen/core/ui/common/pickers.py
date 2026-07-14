"""
pickers.py
Native Windows file/folder picker dialogs (tkinter). Pure UI plumbing.
"""


def pick_folder() -> str:
    """Open a native Windows folder picker via tkinter. Returns path or empty string."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Select save location for new workfile")
        root.destroy()
        return folder or ""
    except Exception:
        return ""


def pick_workfile_file() -> str:
    """Open a native Windows file picker for .cgw files."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Open ChartGen workfile",
            filetypes=[("ChartGen workfile", "*.cgw"), ("All files", "*.*")],
        )
        root.destroy()
        return path or ""
    except Exception:
        return ""
