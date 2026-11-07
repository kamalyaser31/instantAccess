Instant Access 2026.7

Instant Access for NVDA
=======================

*   **Author:** Kamal Yaser
*   **Version:** 2026.7
*   **Compatibility:** NVDA 2024.1 and later

Overview
--------

**Instant Access** is a powerful productivity add-on for NVDA that allows you to create your own custom shortcut layer. Instead of memorizing dozens of complex shortcuts, you can activate "Instant Access mode" with a single key, then press a simple gesture to launch applications, run mini-workflows, insert text, and much more.

This add-on goes beyond simple launchers by allowing you to chain multiple **actions** into a single, sequenced **item**, turning a single shortcut into a powerful macro.

Key Features
------------

*   **Multi-Action Items:** Assign a sequence of actions to a single shortcut.
*   **Variables:** Put the date, the time, the clipboard text, the selected text, or the file or folder from File Explorer into text snippets, website addresses and program arguments.
*   **Find and Run Items:** Open a list of your items, type to filter it, and press `Enter` to run the one you want.
*   **Stop a Running Item:** Press `NVDA+E` to stop a long item or a test.
*   **Browse Items Without Remembering Shortcuts:** Optionally move through the items available in the current application with the arrow keys or Tab inside Instant Access mode, press `Enter` to run one, or open a list of all of them.
*   **Reliable, One-at-a-Time Execution:** Items and action tests run one after another, never at the same time, so they can't mix up your clipboard or keystrokes. If something fails, keys like `Shift` or `Ctrl` are released automatically.
*   **Item Duplication:** Clone any configured item with a single click, preserving all actions and settings.
*   **Action Testing:** Test individual actions directly within the action dialog, with a 3-second preparation delay for keystroke and text snippet actions.
*   **Stop on Error:** Optional setting to abort the rest of an item's action sequence if any action fails to execute.
*   **Timing Control:** Set a custom delay before each action and a shared interval between all actions in an item.
*   **App-Specific Shortcuts:** Make a shortcut global or restrict it to one or more applications.
*   **Turn Items Off:** Disable an item without deleting it, and bring it back later.
*   **Name Announcement:** Choose whether items speak their name when they run, for all items or for each one.
*   **Keyboard Ergonomics:**
    *   Press `Enter` to edit the selected item.
    *   Press `Delete` to delete the selected item or action (with confirmation).
    *   Press `Ctrl+Up` / `Ctrl+Down` in the item dialog to reorder actions.
    *   Press `Ctrl+Up` / `Ctrl+Down` in the settings list to reorder items.
*   **Wide Range of Actions:**
    *   Launch websites, custom URL protocols (`mailto:`, `ms-settings:`), programs, folders, files, batch scripts (`.bat`, `.cmd`), and system PATH commands.
    *   Execute NVDA commands from a filterable list.
    *   Insert, copy, or paste reusable text snippets.
    *   Simulate keystroke sequences with adjustable delay.
*   **Centralized Management:** A comprehensive settings panel to add, edit, duplicate, test, and organize your items.
*   **Safe Import & Export:** Back up and share your configuration in JSON format. When importing, replace everything or merge the new items into your own.
*   **Safe Saving & Recovery:** Your configuration is saved in a way that can't leave a half-written file, and a backup (`config.json.bak`) is kept. If the configuration is ever damaged, the add-on offers to restore the backup.
*   **Adjustable Verbosity:** Choose between detailed feedback (Beginner) or concise tones (Advanced).

Built-In Shortcuts
------------------

*   `NVDA+E`: Toggle Instant Access mode on or off. While an item or a test is running, it stops the item instead and drops any items waiting to run.
*   `NVDA+Shift+E`: Announce the name of the currently focused application. This is useful for creating app-specific shortcuts.
*   `NVDA+Shift+E` (pressed twice quickly): Copy the app name to the clipboard.
*   `Escape` (while Instant Access mode is active): Deactivate the mode without running a command.

Browsing Items in Instant Access Mode
-------------------------------------

If you don't remember an item's shortcut, you can browse to it instead. This is off by default: turn it on with **Enable browsing items in the instant Access layer** in the settings panel.

While Instant Access mode is active:

*   `Down Arrow` or `Tab`: Move to and announce the next item.
*   `Up Arrow` or `Shift+Tab`: Move to and announce the previous item.
*   `Enter`: Run the item you last moved to, then leave the mode. If you haven't moved to an item yet, `Enter` leaves the mode without running anything.
*   `F1` or `H`: Open a list of every item available here. Instant Access mode closes when the list opens.

The list wraps around, so moving past the last item takes you back to the first. Only items that can run in the focused application are included: global items, plus the items restricted to that application.

In the list opened by `F1` or `H`:

*   Type in the **Filter** field to narrow the list. It searches item names, shortcuts, app names, action types and what each action does, such as a website address or a file path. If you type several words, an item must match all of them.
*   Press `Tab` to reach the list, and use the arrow keys to move through it.
*   Press `Enter` to run the selected item, or `Escape` to close the list.

Two settings control how browsing sounds:

*   **Browse announcement:** Name, then shortcut (`Open Gmail, g`); Shortcut, then name (`g, Open Gmail`); or Name only.
*   **Browse order:** Settings list order, alphabetical by name, or by shortcut.

Your own items always come first. If an item uses one of these keys (for example `H` or `F1`), that key keeps running the item, and the remaining browse keys still work. Any other key that has no item assigned leaves the mode, as before.

Configuration
-------------

You can configure the add-on from the NVDA settings panel:

1.  Open the **NVDA Menu** (`NVDA+N`).
2.  Go to **Preferences** -> **Settings**.
3.  Select the **instant Access** category.

The main settings panel lists all your configured items, showing their name, type, shortcut, and a summary of their actions. From here, you can **Add**, **Edit**, **Duplicate**, **Delete**, and **Test** your items, or **Export** and **Import** your configuration.

*   **Filter:** Type here to narrow the list by item name. `Ctrl+Up` and `Ctrl+Down` do nothing while the filter is in use.
*   **Reordering:** Press `Ctrl+Up` or `Ctrl+Down` in the list to move the selected item. The new order is saved at once.
*   **Announce the item name when it runs:** Turn this off if you don't want to hear an item's name each time it runs. Each item can override this setting.

Understanding Items and Actions
-------------------------------

The add-on is built around two core concepts: **Items** and **Actions**.

*   An **Item** is the main unit you create. It has a name, a shortcut (gesture), and a list of one or more actions to perform. It can also be restricted to an app, have a pause interval between its actions, and have error halting enabled.
*   An **Action** is a single step within an item. When you trigger an item, it executes its actions in order.

### Creating and Editing an Item

When you add or edit an item, a dialog appears with the following options:

*   **Name:** A unique, descriptive name for your item.
*   **Actions List:** A list of all the actions this item will perform. You can **Add**, **Edit**, **Delete**, **Move up**, and **Move down** actions to define the sequence (or use `Delete` and `Ctrl+Up`/`Ctrl+Down`).
*   **Stop executing subsequent actions if an error occurs:** A checkbox to prevent subsequent actions from running if an error occurs.
*   **Interval between actions (seconds):** A pause (in seconds) that occurs _after_ each action in the sequence (except the last one).
*   **Announce the name when this item runs:** Choose **Use the general setting**, **Announce** or **Do not announce**. Errors are always spoken.
*   **Enabled:** Untick this to turn the item off without deleting it. A disabled item doesn't run and doesn't appear in the mode, and the settings list marks it as disabled. Its shortcut stays reserved, so it can't clash when you turn the item back on.
*   **Restrict this shortcut...:** A checkbox to make the shortcut app-specific.
    *   **App names:** If the restriction is checked, enter one or more exact app names, separated by commas, such as `notepad, winword`. If the field is empty when you tick the box, it is filled with the program you were using before you opened the settings. Use `NVDA+Shift+E` to find an app's name.
*   **Shortcut:** A button to capture the key combination for this item.

### Action Types

When you add or edit an action, you can choose from several types:

*   **Website:** Opens a URL in your default browser.
*   **Program:** Launches an executable file (`.exe`). You can also provide optional **Arguments**, and tick **Run as administrator** to start the program with administrator rights. Windows then shows its usual prompt, and if you decline it, the add-on says "Cancelled".
*   **Folder:** Opens a folder in File Explorer.
*   **File:** Opens any file using its default associated application.
*   **NVDA Command:** Executes an NVDA script. A dialog appears allowing you to filter and select from all available NVDA and add-on commands.
*   **Text Snippet:** Inserts reusable text. This action has three modes:
    *   **Type:** Simulates typing the text. You can set a custom **Typing delay** (in seconds) between characters.
    *   **Copy:** Puts the text on the clipboard.
    *   **Paste:** Puts the text on the clipboard and then simulates a `Ctrl+V` paste. The text you had copied before comes back to the clipboard afterwards. Only text can be restored.
*   **Keystrokes:** Simulates a sequence of keyboard keys or shortcut combinations (one per line).
    *   **Syntax:** Write the shortcut name (e.g., `ctrl+alt+del` or `shift+f10`).
    *   **Repetition:** You can repeat a key by appending a space and a count (e.g., `down 5` to press the Down Arrow 5 times).
    *   **Add keystroke:** Press this button, then press a key or shortcut, and it is added as a new line. Numeric keypad keys can't be recorded, and neither can `Escape`, which cancels. Type `esc` yourself if you need it.
    *   **Delay between keystrokes:** You can set a custom pause (in seconds) to occur between each keystroke.
*   **Delay before executing this action:** A pause (in seconds) that occurs _before_ this specific action runs.
*   **Test Button:** Allows you to test the current action in isolation without having to save the item or run the entire sequence. For Keystroke and Text Snippet actions, and for actions that read the selected text or File Explorer, a 3-second preparation countdown allows you to switch (via `Alt+Tab`) to the intended target window first.

### Variables

Text snippets, website addresses and program arguments can include values that change each time the item runs. Press the **Insert variable** button next to the field and choose one from the menu:

*   **Date** (`{date}`) and **Time** (`{time}`): The current date and time, in your Windows format.
*   **Clipboard text** (`{clipboard}`): The text on the clipboard.
*   **Selected text** (`{selection}`): The text selected when the item starts.
*   **Selected file** (`{file}`): The file selected in File Explorer. If several are selected, all of them are used.
*   **Open folder** (`{folder}`): The folder open in File Explorer.

For example, this website address searches for the text on your clipboard: `https://www.google.com/search?q={clipboard}`

Some things to know:

*   If an item needs the selected text, a selected file or an open folder and there is none, the item stops before doing anything and tells you why.
*   If a File Explorer window has several tabs, the file or folder may come from a different tab than the one you see.
*   `{clipboard}`, `{selection}`, `{file}` and `{folder}` can't be used in the arguments of `.bat` and `.cmd` files, because the text could run as commands.
*   To type a brace, double it: `{{` gives `{` and `}}` gives `}`. This matters if a text snippet you already have contains double braces.

Examples of Use
---------------

Here are a few examples to inspire you and show how to combine actions into powerful workflows.

### Example 1: Morning News Briefing

This item opens your three favorite news websites in sequence, with a short pause between each one.

*   **Name:** `Morning News`
*   **Shortcut:** `N`
*   **Interval between actions:** `1.5` (seconds)
*   **Actions:**
    1.  **Type:** `Website`, **Path:** `https://www.bbc.com/news`
    2.  **Type:** `Website`, **Path:** `https://www.reuters.com`
    3.  **Type:** `Website`, **Path:** `https://www.apnews.com`

When you trigger this item (e.g., `NVDA+E`, then `N`), it will open the BBC News website, wait 1.5 seconds, open Reuters, wait another 1.5 seconds, and finally open AP News.

### Example 2: Project Startup Workflow

This item gets you ready to code by opening your project folder, your main code file in your editor, and your local development server in a browser.

*   **Name:** `Start Project X`
*   **Shortcut:** `P`
*   **Interval between actions:** `3` (seconds, to give apps time to load)
*   **Actions:**
    1.  **Type:** `Folder`, **Path:** `C:\dev\project-x`
    2.  **Type:** `Program`, **Path:** `C:\Users\YourName\AppData\Local\Programs\Microsoft VS Code\Code.exe`, **Arguments:** `C:\dev\project-x\src\main.js`
    3.  **Type:** `Website`, **Path:** `http://localhost:3000`

This workflow gives you a fully prepared development environment with a single command.

### Example 3: Paste a Standard Reply

This item is for quickly pasting a common response into an email or chat window. This example uses an app-specific shortcut for Microsoft Teams.

*   **Name:** `Teams Greeting`
*   **Shortcut:** `G`
*   **Restrict to App:** Yes, **App Name:** `teams`
*   **Actions:**
    1.  **Type:** `Text Snippet`
        *   **Snippet Action:** `Paste`
        *   **Text:** `Hello team, I will be available to review this after 2 PM. Thanks!`

Now, when you are in Microsoft Teams, you can press `NVDA+E` then `G` to instantly paste that message into the chat. The same shortcut (`G`) can be used for a different global item or for an item in another app.

### Example 4: Quick Accessibility Testing Setup

This item prepares your environment for testing websites and applications with accessibility tools.

*   **Name:** `A11y Testing Kit`
*   **Shortcut:** `A`
*   **Interval between actions:** `1.5` seconds
*   **Actions:**
    1.  **Type:** Website, **Path:** `https://wave.webaim.org`
    2.  **Type:** Website, **Path:** `https://www.axe-core.org`
    3.  **Type:** Folder, **Path:** `C:\Users\YourName\Documents\A11yTests`

**Result:**
Press `NVDA+E` then `A` to instantly open WAVE accessibility checker, axe DevTools documentation, and your testing notes folder in one action.

### Example 5: Open Teaching Tools (for Online Lessons)

This item prepares your teaching environment by opening several tools used during an online class.

*   **Name:** `Start Teaching Session`
*   **Shortcut:** `T`
*   **Interval between actions:** `2` seconds
*   **Actions:**
    1.  **Type:** Website, **Path:** [https://zoom.us](https://zoom.us)
    2.  **Type:** Website, **Path:** [https://wordwall.net](https://wordwall.net)
    3.  **Type:** Folder, **Path:** `C:\Users\Teacher\Documents\LessonNotes`

**Result:**
With one command you open the meeting platform, your interactive activity site, and your lesson materials.

### Example 6: Insert Frequently Used Phrase

This item types a phrase that you frequently use in communication.

*   **Name:** `Thank You Message`
*   **Shortcut:** `Y`
*   **Actions:**
    1.  **Type:** Text Snippet
        *   **Snippet Action:** Type
        *   **Typing delay:** 0.02 seconds
        *   **Text:**
            Thank you for your message. I will review it and reply shortly.

**Result:**
Press `NVDA+E` then `Y` to instantly type the message in any text field.

### Example 7: System Utility Launcher

This item opens several Windows system tools used for troubleshooting.

*   **Name:** `System Tools`
*   **Shortcut:** `U`
*   **Interval between actions:** `1` second
*   **Actions:**
    1.  **Type:** Program, **Path:** `C:\Windows\System32\taskmgr.exe`
    2.  **Type:** Program, **Path:** `C:\Windows\System32\control.exe`
    3.  **Type:** Program, **Path:** `C:\Windows\System32\cmd.exe`

**Result:**
This quickly opens **Task Manager**, **Control Panel**, and **Command Prompt**.

### Example 8: Focus Mode Setup

This item prepares a distraction-free work environment.

*   **Name:** `Focus Mode`
*   **Shortcut:** `F`
*   **Interval between actions:** `2` seconds
*   **Actions:**
    1.  **Type:** Program, **Path:** `C:\Program Files\Notepad++\notepad++.exe`
    2.  **Type:** Website, **Path:** [https://pomofocus.io](https://pomofocus.io)
    3.  **Type:** NVDA Command
        *   Command: _toggleSpeechMode_

**Result:**
This opens your editor, starts a Pomodoro timer, and adjusts NVDA feedback for focused work.

Additional Practical Examples
-----------------------------

### Example 9: Email Productivity Setup

This item opens your email account and productivity tools in sequence.

*   **Name:** `Email Station`
*   **Shortcut:** `E`
*   **Interval between actions:** `1` second
*   **Actions:**
    1.  **Type:** Website, **Path:** `https://mail.google.com`
    2.  **Type:** Website, **Path:** `https://calendar.google.com`
    3.  **Type:** Folder, **Path:** `C:\Users\YourName\Documents\EmailTemplates`

**Result:**
Press `NVDA+E` then `E` to open Gmail, Google Calendar, and your email templates folder.

* * *

### Example 10: Quick Backup Status Check

This item verifies backup status and opens relevant backup tools.

*   **Name:** `Backup Check`
*   **Shortcut:** `K`
*   **Interval between actions:** `2` seconds
*   **Actions:**
    1.  **Type:** Folder, **Path:** `C:\Users\YourName\AppData\Local\Packages`
    2.  **Type:** Program, **Path:** `C:\Windows\System32\control.exe`
    3.  **Type:** Website, **Path:** `https://myaccount.google.com/security`

**Result:**
Open backup locations, Control Panel settings, and Google account security in one command.

* * *

### Example 11: Code Documentation Quick Start

This item prepares your documentation workspace for coding projects.

*   **Name:** `Doc Session`
*   **Shortcut:** `O`
*   **Interval between actions:** `2` seconds
*   **Actions:**
    1.  **Type:** Program, **Path:** `C:\Users\YourName\AppData\Local\Programs\Microsoft VS Code\Code.exe`
    2.  **Type:** Website, **Path:** `https://github.com`
    3.  **Type:** Folder, **Path:** `C:\Users\YourName\Documents\ProjectDocs`

**Result:**
Launch VS Code, GitHub, and your documentation folder for collaborative coding work.

* * *

### Example 12: Sequence of Keystrokes (Macro)

This item simulates a sequence of keyboard shortcut actions (e.g., using the context menu, navigating down 5 times, and pressing Enter).

*   **Name:** `Menu Sequence`
*   **Shortcut:** `M`
*   **Actions:**
    1.  **Type:** `Keystrokes`
        *   **Keys:**
            ```
            shift+f10
            down 5
            enter
            ```
        *   **Delay between keystrokes:** `0.1` seconds

**Result:**
Press `NVDA+E` then `M` to simulate pressing `Shift+F10`, waiting 0.1 seconds, pressing `Down Arrow` 5 times (with 0.1s pauses), and pressing `Enter`.

* * *

App-Specific Shortcuts
----------------------

You can make a shortcut behave differently depending on the application you are in.

*   A **global shortcut** has no app restriction and works everywhere.
*   An **app-specific shortcut** is only active when the target application is focused.

To create an app-specific shortcut:

1.  Go to the target application, then open the settings.
2.  Check the "Restrict this shortcut..." box in the item dialog. The "App names" field is filled with that application.

To add another application, go to it and press `NVDA+Shift+E` twice quickly to copy its name. Then paste it into the "App names" field after a comma.

If a global shortcut and an app-specific shortcut use the same gesture, the **app-specific one will always take priority** when its app is active.

Verbosity Levels
----------------

You can change how much feedback the add-on gives you from the main settings panel:

*   **Beginner (Default):** Provides full, spoken messages (e.g., "Instant Access On. 10 commands loaded.").
*   **Advanced:** Uses short sounds and tones for speed and efficiency (e.g., a "bip" for on/off).

Import and Export
-----------------

You can back up your entire configuration or move it to another computer using the **Import settings** and **Export settings** buttons. The configuration is stored in a `config.json` file.
After you choose a file to import, the add-on asks what to do with it:

*   **Replace:** All your items and settings are replaced by the ones in the file.
*   **Merge:** The items in the file that have a new name and a free shortcut are added. Your settings stay as they are, and the add-on tells you how many items were added and skipped.

Super User Recipes (Argument-Driven Workflows)
----------------------------------------------

Instant Access supports **passing command-line arguments to applications**, which allows advanced automation. This enables users to open specific files, trigger program features, run scripts, or execute system tasks directly from a shortcut.

The following examples demonstrate practical, specialized workflows that showcase different argument patterns.

Each recipe suggests its own shortcut, and some reuse keys from the examples above. If you set up several of them, pick keys that don't clash. If you use browsing, remember that `H` and `F1` are also browse keys.

* * *

### 1\. Start a Website in "Application Mode"

Many Chromium browsers can open a site as a **standalone app window** without browser UI.

**Name:** Open WhatsApp Web App
**Shortcut:** W

**Program**

**Path:**

    C:\Program Files\Google\Chrome\Application\chrome.exe

**Arguments:**

    --app=https://web.whatsapp.com

**Result:**
The website opens like a **native desktop application**.

* * *

### 2\. Open Explorer Highlighting a Specific File

Windows Explorer can directly **select a file** when opened.

**Name:** Locate Project Config
**Shortcut:** L

**Program**

**Path:**

    explorer.exe

**Arguments:**

    /select,"C:\dev\project-x\config.json"

**Result:**
Explorer opens the folder and focuses on the file.

* * *

### 3\. Run Windows Disk Cleanup Automatically

Run cleanup without opening the full interface.

**Name:** Quick Disk Cleanup
**Shortcut:** C

**Program**

**Path:**

    cleanmgr.exe

**Arguments:**

    /verylowdisk

**Result:**
Runs disk cleanup automatically.

* * *

### 4\. Launch Firefox in Private Mode

Open a secure browsing session immediately.

**Name:** Private Browser
**Shortcut:** P

**Program**

**Path:**

    C:\Program Files\Mozilla Firefox\firefox.exe

**Arguments:**

    -private-window

**Result:**
Firefox starts directly in **private browsing**.

* * *

### 5\. Open a Folder in VS Code

**Purpose:** Launch Visual Studio Code directly inside a project folder.

**Name:** Open Project in VS Code
**Shortcut:** V

**Program**

**Path:**

    C:\Users\YourName\AppData\Local\Programs\Microsoft VS Code\Code.exe

**Arguments:**

    C:\dev\myproject

**Result:**
VS Code launches with the specified project folder already loaded.

* * *

### 6\. Open Command Prompt in a Specific Directory

**Purpose:** Start a terminal already positioned in a project directory.

**Name:** Dev Terminal
**Shortcut:** T

**Program**

**Path:**

    C:\Windows\System32\cmd.exe

**Arguments:**

    /k cd C:\dev\project-x

**Result:**
Command Prompt opens and automatically changes to the project directory.

* * *

### 7\. Run PowerShell Script Automation

**Purpose:** Execute a PowerShell script that performs automated tasks.

**Name:** Run Backup Script
**Shortcut:** B

**Program**

**Path:**

    C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe

**Arguments:**

    -ExecutionPolicy Bypass -File "C:\Scripts\backup.ps1"

**Result:**
Runs a predefined backup automation script.

* * *

### 8\. Launch Windows Settings Pages

Windows settings pages can be opened using **ms-settings arguments**.

**Name:** Open Bluetooth Settings
**Shortcut:** S

**Program**

**Path:**

    explorer.exe

**Arguments:**

    ms-settings:bluetooth

**Other examples:**

    ms-settings:display
    ms-settings:network
    ms-settings:sound
    ms-settings:windowsupdate


**Result:**
Instantly opens the selected settings page.

* * *

### 9\. Open Multiple Browser Tabs for Research

**Purpose:** Start Firefox with several tabs simultaneously for a research workflow.

**Name:** Research Session
**Shortcut:** R

**Program**

**Path:**

    C:\Program Files\Mozilla Firefox\firefox.exe

**Arguments:**

    https://scholar.google.com https://arxiv.org https://github.com

**Result:**
Opens Firefox with three research resources in separate tabs.

* * *

### 10\. Open Another Registry Editor Window

**Purpose:** Open a second Registry Editor window, even when one is already open, to compare two keys side by side.

**Name:** New Registry Editor Window
**Shortcut:** O

**Program**

**Path:**

    C:\Windows\System32\regedit.exe

**Arguments:**

    /m

**Result:**
Opens a new Registry Editor window. Registry Editor has no read-only mode, so be careful with changes.

* * *

### 11\. Launch System Event Log Viewer

**Purpose:** Open Event Viewer directly for system diagnostics.

**Name:** View System Events
**Shortcut:** E

**Program**

**Path:**

    C:\Windows\System32\eventvwr.exe

**Arguments:**

    /c:System

**Result:**
Opens Event Viewer focused on system events for troubleshooting.

* * *

### 12\. Run a Maintenance Batch File

**Purpose:** Run a batch script through Command Prompt.

**Name:** Maintenance Script
**Shortcut:** J

**Program**

**Path:**

    C:\Windows\System32\cmd.exe

**Arguments:**

    /c call C:\Scripts\system_maintenance.bat

**Result:**
Runs the batch script with your normal permissions. It does not run it as administrator; if the script needs administrator rights, it will fail or ask for them itself.

* * *

### 13\. Launch Git Bash in Project Directory

**Purpose:** Open Git Bash terminal in a specific project folder.

**Name:** Git Project Terminal
**Shortcut:** G

**Program**

**Path:**

    C:\Program Files\Git\git-bash.exe

**Arguments:**

    --cd=C:\dev\my-repo

**Result:**
Opens Git Bash in your project directory, ready for version control commands.

* * *

### 14\. Open Resource Monitor

**Purpose:** See which programs are using your CPU, memory, disk, and network.

**Name:** Resource Monitor
**Shortcut:** M

**Program**

**Path:**

    C:\Windows\System32\perfmon.exe

**Arguments:**

    /res

**Result:**
Opens Resource Monitor. (Use `/rel` instead of `/res` to open Reliability Monitor.)

* * *

### 15\. Launch VLC Media Player with Specific Folder

**Purpose:** Open VLC with a media directory.

**Name:** Music Library
**Shortcut:** U

**Program**

**Path:**

    C:\Program Files\VideoLAN\VLC\vlc.exe

**Arguments:**

    C:\Users\YourName\Music

**Result:**
Launches VLC with your music library ready to play.

* * *

### 16\. Open Windows Network Settings

**Purpose:** Quick access to network configuration.

**Name:** Network Config
**Shortcut:** I

**Program**

**Path:**

    explorer.exe

**Arguments:**

    ms-settings:network-wifi

**Result:**
Opens Windows network settings for Wi-Fi configuration.

* * *

Best Practices
--------------

These workflows illustrate different automation patterns:

*   **Application mode:** Turn websites into standalone apps.
*   **File selection:** Navigate to and select specific files.
*   **Silent utilities:** Run maintenance tools without their interface.
*   **Browser modes:** Open browsers with specific features.
*   **Development setup:** Launch an IDE with a project folder.
*   **Script execution:** Automate system tasks with PowerShell.
*   **Settings pages:** Open specific Windows settings pages.
*   **File associations:** Open files directly in target applications.

* * *

Finding Your Own Arguments
--------------------------

Command-line arguments can come from many sources:

*   Application documentation or help pages
*   `--help` or `/?` command output
*   Windows shell commands and documentation
*   PowerShell command specifications
*   URI schemes (`ms-settings:`, `shell:`, etc.)

Experiment with these arguments to create custom workflows tailored to your specific needs!

Developer Details
-----------------

*   **Developer:** Kamal Yaser
*   **Email:** [kamalyaser31@gmail.com](mailto:kamalyaser31@gmail.com)
*   **Telegram:** [@kamalyaser31](https://t.me/kamalyaser31)
*   **Repository:** [https://github.com/kamalyaser31/instantAccess](https://github.com/kamalyaser31/instantAccess)

License
-------

Copyright (C) 2026 Kamal Yaser.
This add-on is licensed under the GNU General Public License (GPL) Version 2 or any later version.

It includes a trimmed copy of the [keyboard](https://github.com/boppreh/keyboard) library by BoppreH, under the MIT License. The license text is in `globalPlugins/core/keyboard/LICENSE.txt`.
