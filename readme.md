   Instant Access 2026.2

Instant Access for NVDA
=======================

*   **Author:** Kamal Yaser
*   **Version:** 2026.2
*   **Compatibility:** NVDA 2024.1 and later

Overview
--------

**Instant Access** is a powerful productivity add-on for NVDA that allows you to create your own custom shortcut layer. Instead of memorizing dozens of complex shortcuts, you can activate "Instant Access mode" with a single key, then press a simple gesture to launch applications, run mini-workflows, insert text, and much more.

This add-on goes beyond simple launchers by allowing you to chain multiple **actions** into a single, sequenced **item**, turning a single shortcut into a powerful macro.

Key Features
------------

*   **Multi-Action Items:** Assign a sequence of actions to a single shortcut.
*   **Timing Control:** Set a custom delay before each action and a shared interval between all actions in an item.
*   **App-Specific Shortcuts:** Make a shortcut global or restrict it to a specific application.
*   **Wide Range of Actions:**
    *   Launch websites, programs, folders, and files.
    *   Execute NVDA commands from a filterable list.
    *   Insert, copy, or paste reusable text snippets.
*   **Centralized Management:** A comprehensive settings panel to add, edit, test, and organize your items.
*   **Import & Export:** Back up and share your configuration in JSON format.
*   **Adjustable Verbosity:** Choose between detailed feedback (Beginner) or concise tones (Advanced).

Built-In Shortcuts
------------------

*   `NVDA+E`: Toggle Instant Access mode on or off.
*   `NVDA+Shift+E`: Announce the name of the currently focused application. This is useful for creating app-specific shortcuts.
*   `NVDA+Shift+E` (pressed twice quickly): Copy the app name to the clipboard.
*   `Escape` (while Instant Access mode is active): Deactivate the mode without running a command.

Configuration
-------------

You can configure the add-on from the NVDA settings panel:

1.  Open the **NVDA Menu** (`NVDA+N`).
2.  Go to **Preferences** -> **Settings**.
3.  Select the **instant Access** category.

The main settings panel lists all your configured items, showing their name, type, shortcut, and a summary of their actions. From here, you can **Add**, **Edit**, **Delete**, and **Test** your items.

Understanding Items and Actions
-------------------------------

The add-on is built around two core concepts: **Items** and **Actions**.

*   An **Item** is the main unit you create. It has a name, a shortcut (gesture), and a list of one or more actions to perform. It can also be restricted to an app and have a pause interval between its actions.
*   An **Action** is a single step within an item. When you trigger an item, it executes its actions in order.

### Creating and Editing an Item

When you add or edit an item, a dialog appears with the following options:

*   **Name:** A unique, descriptive name for your item.
*   **Actions List:** A list of all the actions this item will perform. You can **Add**, **Edit**, **Delete**, **Move up**, and **Move down** actions to define the sequence.
*   **Interval between actions (seconds):** A pause (in seconds) that occurs _after_ each action in the sequence (except the last one).
*   **Restrict this shortcut...:** A checkbox to make the shortcut app-specific.
    *   **App name:** If the restriction is checked, you must provide the exact app name (use `NVDA+Shift+E` to find it).
*   **Shortcut:** A button to capture the key combination for this item.

### Action Types

When you add or edit an action, you can choose from several types:

*   **Website:** Opens a URL in your default browser.
*   **Program:** Launches an executable file (`.exe`). You can also provide optional **Arguments**.
*   **Folder:** Opens a folder in File Explorer.
*   **File:** Opens any file using its default associated application.
*   **NVDA Command:** Executes an NVDA script. A dialog appears allowing you to filter and select from all available NVDA and add-on commands.
*   **Text Snippet:** Inserts reusable text. This action has three modes:
    *   **Type:** Simulates typing the text. You can set a custom **Typing delay** (in seconds) between characters.
    *   **Copy:** Puts the text on the clipboard.
    *   **Paste:** Puts the text on the clipboard and then simulates a `Ctrl+V` paste.
*   **Delay before executing this action:** A pause (in seconds) that occurs _before_ this specific action runs.

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

Now, when you are in Microsoft Teams, you can press ``NVDA+E` then `G`` to instantly paste that message into the chat. The same shortcut (`G`) can be used for a different global item or for an item in another app.

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

App-Specific Shortcuts
----------------------

You can make a shortcut behave differently depending on the application you are in.

*   A **global shortcut** has no app restriction and works everywhere.
*   An **app-specific shortcut** is only active when the target application is focused.

To create an app-specific shortcut:

1.  Check the "Restrict this shortcut..." box in the item dialog.
2.  Go to the target application.
3.  Press `NVDA+Shift+E` twice quickly to copy its name to the clipboard.
4.  Paste the name into the "App name" field.

If a global shortcut and an app-specific shortcut use the same gesture, the **app-specific one will always take priority** when its app is active.

Verbosity Levels
----------------

You can change how much feedback the add-on gives you from the main settings panel:

*   **Beginner (Default):** Provides full, spoken messages (e.g., "Instant Access On. 10 commands loaded.").
*   **Advanced:** Uses short sounds and tones for speed and efficiency (e.g., a "bip" for on/off).

Import and Export
-----------------

You can back up your entire configuration or move it to another computer using the **Import settings** and **Export settings** buttons. The configuration is stored in a `config.json` file.  
**Note:** Importing a configuration will overwrite your existing settings.

Super User Recipes (Argument-Driven Workflows)
----------------------------------------------

Instant Access supports **passing command-line arguments to applications**, which allows advanced automation. This enables users to open specific files, trigger program features, run scripts, or execute system tasks directly from a shortcut.

The following examples demonstrate practical, specialized workflows that showcase different argument patterns:

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

    C:\Program Files\Mozilla Firefox\firefox.exe

**Arguments:**

    https://scholar.google.com https://arxiv.org https://github.com

**Result:**  
Opens Firefox with three research resources in separate tabs.

* * *

### 10\. Open Windows Registry Editor with Specific Hive

**Purpose:** Launch Registry Editor directly to a specific location.

**Name:** Open NVDA Registry Settings  
**Shortcut:** O

**Program**

    C:\Windows\System32\regedit.exe

**Arguments:**

    /m

**Result:**  
Opens Registry Editor in read-only mode for safe browsing.

* * *

### 11\. Launch System Event Log Viewer

**Purpose:** Open Event Viewer directly for system diagnostics.

**Name:** View System Events  
**Shortcut:** E

**Program**

    C:\Windows\System32\eventvwr.exe

**Arguments:**

    /c system

**Result:**  
Opens Event Viewer focused on system events for troubleshooting.

* * *

### 12\. Run Batch File with Admin Privileges

**Purpose:** Execute a batch script that requires elevated privileges.

**Name:** Admin Batch Script  
**Shortcut:** H

**Program**

    C:\Windows\System32\cmd.exe

**Arguments:**

    /c call C:\Scripts\system_maintenance.bat

**Result:**  
Executes a batch script for system maintenance tasks.

* * *

### 13\. Launch Git Bash in Project Directory

**Purpose:** Open Git Bash terminal in a specific project folder.

**Name:** Git Project Terminal  
**Shortcut:** G

**Program**

    C:\Program Files\Git\git-bash.exe

**Arguments:**

    --cd=C:\dev\my-repo

**Result:**  
Opens Git Bash in your project directory, ready for version control commands.

* * *

### 14\. Open Windows Performance Monitor

**Purpose:** Launch Performance Monitor for system monitoring.

**Name:** Performance Monitor  
**Shortcut:** M

**Program**

    C:\Windows\System32\perfmon.exe

**Arguments:**

    /res

**Result:**  
Opens Performance Monitor in Reliability Monitor view for resource tracking.

* * *

### 15\. Launch VLC Media Player with Specific Folder

**Purpose:** Open VLC with a media directory.

**Name:** Music Library  
**Shortcut:** U

**Program**

    C:\Program Files\VideoLAN\VLC\vlc.exe

**Arguments:**

C:\\Users\\YourName\\Music

**Result:**  
Launches VLC with your music library ready to play.

* * *

### 16\. Open Windows Network Settings

**Purpose:** Quick access to network configuration.

**Name:** Network Config  
**Shortcut:** I

**Program**

    explorer.exe

**Arguments:**

    ms-settings:network-wifi

**Result:**  
Opens Windows network settings for Wi-Fi configuration.

* * *

Best Practices
--------------

These workflows illustrate different automation patterns:

Pattern

Purpose

Application mode

Turn websites into standalone apps

File selection

Navigate to and select specific files

Silent utilities

Run maintenance tools without UI

Browser modes

Open browsers with specific features

Development setup

Launch IDE with project folder

Script execution

Automate system tasks with PowerShell

Settings pages

Open specific Windows configuration

File associations

Open files directly in target applications

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

License
-------

Copyright (C) 2026 Kamal Yaser.  
This add-on is licensed under the GNU General Public License (GPL) Version 2 or any later version.