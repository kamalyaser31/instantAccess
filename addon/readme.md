# instant Access

* **Author:** Kamal Yaser
* **Compatibility:** NVDA 2024.1 and later
* **Version:** 2026.1

## Overview
instant Access allows you to launch your favorite websites, applications, and folders using simple, single-key shortcuts. Instead of navigating the Start Menu or Desktop, you simply enter "instant Access Mode" and press a single letter or key combination.

## Usage

### 1. Adding Commands
To configure your shortcuts, go to **NVDA Menu** -> **Preferences** -> **Settings** -> **instant Access**.

1.  Click the **Add** button.
2.  **Name:** Enter a name for the command (e.g., "Google" or "Notepad").
3.  **Type:** Choose one of the following:
    * **Website:** Opens a URL in your default browser.
    * **Program:** Launches an executable file (.exe).
    * **Folder:** Opens a directory in File Explorer.
4.  **Path or URL:**
    * For Websites: Paste the link (e.g., `google.com`). The add-on adds `https://` automatically if missing.
    * For Programs/Folders: Click the **Browse** button to find the file on your computer.
5.  **Shortcut:**
    * Click the **Shortcut** button.
    * A dialog will appear asking you to press a key.
    * Press the key you want to use (e.g., `G`, `Control+1`, `F5`).
    * The dialog will close and save your key automatically.
6.  Click **OK** to save the item.

### 2. Using instant Access
1.  Press **NVDA + E** to toggle instant Access mode.
    * NVDA will announce: *"instant Access On"*.
2.  Press the key you assigned (e.g., press **G**).
3.  The item will open immediately, and instant Access mode will close automatically.

### 3. Exiting Mode
If you enter instant Access mode by mistake, you can exit without launching anything by pressing:
* **Escape**
* **NVDA + E**

## Managing Commands
In the instant Access Settings panel, you can:
* **Edit:** Change the path or shortcut of an existing command.
* **Delete:** Remove a command.
* **Test:** Launch the selected item immediately to verify it works.

## Features
* **Auto-Detection:** No need to type complex key codes; just press the key you want to set.
* **Safety:** The add-on verifies that files exist before trying to open them.
* **Secure Mode:** The add-on automatically disables itself on secure screens (like the Windows Sign-in screen) to comply with NVDA security standards.

## Changelog
### Version 2026.1
* Initial Release.
* Added GUI for managing commands.
* Added support for Websites, Programs, and Folders.
* Added automatic key detection.