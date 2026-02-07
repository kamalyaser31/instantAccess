# instant Access for NVDA

* **Author:** Kamal Yaser
* **Version:** 2026.1
* **Compatibility:** NVDA 2019.3 and later

**instant Access** is a productivity add-on for NVDA that allows you to launch websites, programs, files, and folders using a dedicated "Quick Layer." Instead of memorizing complex global shortcuts for every application, you simply enter "Quick Mode" and press a single key.

## What's New in this Release

This version brings significant improvements for power users and stability:

* **Command Line Arguments:** You can now add flags to programs (e.g., launch a browser in Incognito/Private mode).
* **Universal File Support:** The "Programs" category has been expanded to "Files." You can now launch images, PDFs, or text documents in their default viewer.
* **No More Freezing:** All file and URL launching now happens in the background. NVDA will no longer pause or freeze while waiting for a slow network drive or browser to open.
* **Verbosity Levels:** Choose between helpful spoken descriptions (Beginner) or fast, minimal beeps (Advanced).
* **Settings Management:** Easily backup and restore your shortcuts with the new Import/Export feature.

## Getting Started

1. Open the **NVDA Menu** (`NVDA + N`).
2. Navigate to **Preferences** -> **Settings**.
3. Scroll down to the **instant Access** category.

## Managing Items

In the settings panel, you can Add, Edit, or Delete your shortcuts.

### Adding a New Item

1. Click **Add**.
2. **Name:** Enter a name for the item (e.g., "Google" or "Notes").
3. **Type:** Choose one of the following:
* **Website:** Opens a URL in your default browser.
* **Program:** Executable files (`.exe`). Supports command line arguments.
* **Folder:** Opens a directory in File Explorer.
* **File:** Opens any document (`.txt`, `.pdf`, `.docx`) in its default application.


4. **Path:** Paste the path/URL or use the **Browse** button to locate it.
5. **Arguments (Optional):** (Only for Programs) Enter flags like `-incognito` or `/safe`.
6. **Shortcut:** Click the button and press the key you want to use (e.g., `G` for Google).

## How to Use

1. **Enter Quick Mode:** Press **`NVDA + E`**.
* *Beginner Mode:* NVDA says: "instant Access On. X commands loaded."
* *Advanced Mode:* NVDA says: "On" (or beeps).


2. **Launch an Item:** Press the key you assigned (e.g., press `G`).
* The item will launch immediately.
* Quick Mode automatically closes after the command executes.


3. **Cancel:** Press **Escape** or **`NVDA + E`** again to exit without launching anything.

## Advanced Configuration

### Verbosity Levels

You can customize how chatty the add-on is via the Settings panel:

* **Beginner (Default):** Provides full spoken feedback. Useful when learning your shortcuts.
* *Example:* "instant Access On," "This gesture has no command assigned."


* **Advanced:** Designed for speed. Uses short phrases and beeps.
* *Example:* "On," "Off," or a simple error beep if you press a wrong key.



### Import / Export

You can now share your setup between computers or back up your configuration.

* **Export Settings:** Saves your current list of shortcuts and settings to a `.ini` file.
* **Import Settings:** Loads a configuration file. **Note:** This will overwrite your current list.

## Troubleshooting

* **"Error: File not found":** Ensure the path is correct. If the file is on a network drive, ensure you are connected to the network.
* **Program doesn't open correctly:** Some programs require a specific "Working Directory." This add-on automatically handles this for you, but ensure you have permissions to access the folder.

## License

Copyright (C) 2026 Kamal Yaser.
This add-on is released under the GNU General Public License (GPL) version 2 or later.