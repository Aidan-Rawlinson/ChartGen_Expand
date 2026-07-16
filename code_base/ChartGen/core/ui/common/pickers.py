"""
pickers.py
Native Windows file/folder picker dialogs (tkinter). Pure UI plumbing.
"""


def pick_save_file(title: str, initial_file: str = "") -> str:
    """
    Open a native Windows Save dialog for a .cgw file — one dialog for both
    folder and filename, rather than a folder picker plus a separate name
    box. The OS dialog itself prompts to confirm overwrite if the chosen
    name already exists, so callers don't need their own overwrite step.
    Returns the full path (with .cgw extension) or empty string if cancelled.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=".cgw",
            initialfile=initial_file,
            filetypes=[("ChartGen workfile", "*.cgw"), ("All files", "*.*")],
        )
        root.destroy()
        return path or ""
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
