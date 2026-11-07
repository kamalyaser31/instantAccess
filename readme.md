# Instant Access for NVDA

*   **Author:** Kamal Yaser
*   **Version:** 2026.7
*   **Compatibility:** NVDA 2024.1 and later

Every day you open the same programs, visit the same websites and type the same replies. Each of these takes many key presses, and every shortcut you add is one more to remember.

Instant Access gives you one key that opens your own private keyboard. Press `NVDA+E`, then one key of your choice, and the job is done. That job can be one step or a long chain of steps.

## What it solves

*   **Too many shortcuts to remember.** All your work sits behind `NVDA+E`, and one key can mean different things in different programs.
*   **Forgetting a key.** Open a list of your items, type a word to find one, and press `Enter`. This list is off until you turn on browsing in the settings, as explained below.
*   **Doing the same steps again and again.** One item can open a folder, start a program, wait, and open a website.
*   **Copying text from one place to another.** An item can use the selected text, the clipboard, or the selected file. For example, one key can search Google for the words you selected.
*   **Keys that have no shortcut.** An item can press keys for you, such as opening a menu and moving down five times.

## Install it

1.  In NVDA, open **Tools**, then **Add-on Store**.
2.  Find Instant Access in the available add-ons and install it.
3.  Restart NVDA.

You can also download the add-on from the [releases page](https://github.com/kamalyaser31/instantAccess/releases), open the file, and restart NVDA.

## Make your first item

This takes about two minutes. You will make an item that opens Notepad when you press `NVDA+E`, then `N`.

1.  Press `NVDA+N`, open **Preferences**, then **Settings**.
2.  In the categories list, choose **instant Access**.
3.  Press the **Add** button. A new dialog opens.
4.  In the **Name** field, type `Open Notepad`.
5.  Press the **Add** button in this dialog to add an action. Another dialog opens.
6.  In the **Type** list, choose **Program**.
7.  In the **Path or URL** field, type `notepad`, then press **OK**.
8.  Press the **Shortcut** button, then press `N`.
9.  Press **OK** to close the item, then **OK** to close the settings.
10. Press `NVDA+E`, then `N`. Notepad opens.

That is the whole idea. An **item** has a name, a key, and one or more **actions**. To add more steps, edit the item and add more actions. They run in order.

## Use your items

*   `NVDA+E`: Turn Instant Access mode on or off. Then press the key of an item to run it.
*   `Escape`: Leave the mode without running anything.
*   Any other key that has no item: The add-on tells you, and leaves the mode.
*   `NVDA+E` while an item or a test is running: Stop it, and drop any items waiting to run.
*   `NVDA+Shift+E`: Hear the name of the program you are in.
*   `NVDA+Shift+E` pressed twice quickly: Copy that name to the clipboard.

To use other keys instead of `NVDA+E` or `NVDA+Shift+E`, open **Preferences**, then **Input gestures**, and look in the **instant Access** category.

Items run one at a time, so they can't mix up your clipboard or your keystrokes. If you run several quickly, they wait in line.

## Find an item when you forget its key

This is off by default. To turn it on, tick **Enable browsing items in the instant Access layer** in the add-on settings.

Now, in Instant Access mode:

*   `Down Arrow` or `Tab`: Hear the next item.
*   `Up Arrow` or `Shift+Tab`: Hear the previous item.
*   `Enter`: Run the item you last heard, and leave the mode. If you have not moved to an item yet, `Enter` only leaves the mode.
*   `F1` or `H`: Open a list of your items, and leave the mode.

The arrow keys go around in a circle: after the last item, you return to the first.

In the list opened by `F1` or `H`:

1.  Type a word in the **Filter** field. It searches names, shortcuts, app names, action types, and what each action does, such as a website address or a file path. If you type several words, an item must match all of them.
2.  Press `Tab` to reach the list, then use the arrow keys.
3.  Press `Enter` to run the selected item, or `Escape` to close the list.

Only the items you can use in the current program appear: global items, and items restricted to this program.

Your own items come first. If an item uses `H` or `F1`, that key runs the item, and the other browse keys still work.

Two settings change what you hear:

*   **Browse announcement:** Name, then shortcut; shortcut, then name; or name only.
*   **Browse order:** The order of the settings list, alphabetical by name, or by shortcut.

## Examples

Together, these eight examples use every action type and every variable. Each one lists what to enter when you add the item. Change the names, paths and keys to suit you.

### Search for the selected text

Select some words in any program, then search for them on Google in one step.

*   **Name:** `Search selection`
*   **Shortcut:** `S`
*   **Action:** Type **Website**, Path or URL `https://www.google.com/search?q={selection}`

To search for the text you copied instead, use `{clipboard}` in place of `{selection}`.

### Start your work

Open your work folder, today's file and your email, with one key.

*   **Name:** `Start work`
*   **Shortcut:** `W`
*   **Interval between actions:** `2`
*   **Actions:**
    1.  Type **Folder**, Path or URL `C:\Work`
    2.  Type **File**, Path or URL `C:\Work\plan.docx`
    3.  Type **Website**, Path or URL `https://mail.google.com`

The interval gives each program time to open. **Stop executing remaining actions if an action fails** is ticked by default, so if a step fails, the steps after it don't run.

### Paste a reply with today's date

Paste a ready reply, only in the programs you choose. Your copied text comes back afterwards.

*   **Name:** `Quick reply`
*   **Shortcut:** `R`
*   **Restrict this shortcut to work in certain apps:** Ticked, with the names `thunderbird, winword`
*   **Action:** Type **Text snippet**, Snippet action **Paste**, with these two lines of text:
    1.  `Thank you for your message. I will reply soon.`
    2.  `Sent on {date}`

In another program, the same key can run a different item. Use `NVDA+Shift+E` to find the exact name of a program. If you write your email in a browser, use the browser's name, such as `chrome` or `msedge`.

### Type the date and time

Start a note with the current date and time, in any place that accepts text.

*   **Name:** `Time stamp`
*   **Shortcut:** `T`
*   **Action:** Type **Text snippet**, Snippet action **Type the text**, with the text `{date} {time}: `

### Open the selected file in Notepad

Select a file in File Explorer, then open it in Notepad, even if it opens in another program by default.

*   **Name:** `Open in Notepad`
*   **Shortcut:** `O`
*   **Action:** Type **Program**, Path or URL `notepad`, Arguments `{file}`

To change a file that Windows protects, tick **Run as administrator**. Windows shows its usual prompt. If you decline it, the add-on says "Cancelled".

### Copy the path of this folder

While you are in a folder in File Explorer, copy its full path to send it to someone or paste it elsewhere.

*   **Name:** `Copy folder path`
*   **Shortcut:** `P`
*   **Action:** Type **Text snippet**, Snippet action **Copy**, with the text `{folder}`

### Copy the current line

In a document, copy the line you are on without selecting it by hand.

*   **Name:** `Copy line`
*   **Shortcut:** `L`
*   **Action:** Type **Keystrokes**, with **Delay between keystrokes** `0.1`, and these three lines:
    1.  `home`
    2.  `shift+end`
    3.  `ctrl+c`

Press the **Add keystroke** button to record a key instead of typing its name.

### Open the Add-on Store

Some NVDA commands have no key at all. Give one a key of your own.

*   **Name:** `Add-on Store`
*   **Shortcut:** `A`
*   **Action:** Type **NVDA command**. Press **Select command**, type `store` in the filter, and choose the command that opens the Add-on Store.

## Everything you can set

### The settings panel

Open it from **Preferences**, **Settings**, **instant Access**. The list shows each item's name, type, shortcut and details.

*   **Filter:** Narrow the list by item name. Reordering doesn't work while the filter is in use.
*   **Add**, **Edit**, **Delete:** Manage your items. In the list, `Enter` edits and `Delete` deletes.
*   **Duplicate:** Copy an item with all its actions. The copy has no shortcut yet.
*   **Test:** Run the selected item now. If it types, presses keys, or reads the selected text or File Explorer, the add-on asks you first, then waits 3 seconds so you can switch to the window you want.
*   `Ctrl+Up` and `Ctrl+Down` in the list: Move the selected item. The new order is saved at once.
*   **Verbosity level:** **Beginner** speaks full messages, such as "instant Access On. 10 commands loaded". **Advanced** uses short tones.
*   **Announce the item name when it runs:** Turn this off if you don't want to hear names. Each item can change this for itself.

### Item options

*   **Name:** A name that no other item uses.
*   **Actions:** The steps of the item. Use **Add**, **Edit**, **Delete**, **Move up** and **Move down**. In the list, `Delete` deletes, and `Ctrl+Up` and `Ctrl+Down` move an action.
*   **Interval between actions (seconds):** A pause after each action, except the last one.
*   **Stop executing remaining actions if an action fails:** This is ticked by default. If you untick it, the next actions still run after a failure.
*   **Announce the name when this item runs:** **Use the general setting**, **Announce** or **Do not announce**. Errors are always spoken.
*   **Enabled:** Untick this to turn the item off without deleting it. It doesn't run or appear in the mode, and the settings list marks it as disabled. Its shortcut stays reserved.
*   **Restrict this shortcut to work in certain apps:** Tick this to limit the item to some programs. Then fill in **App names, separated by commas**. If the field is empty when you tick the box, it is filled with the program you were using before you opened the settings.
*   **Shortcut:** Press this button, then press one key, such as `G`, or a combination, such as `Ctrl+Shift+G`. Every item needs one. `Escape`, `NVDA+E` and `NVDA+Shift+E` are reserved and can't be used.

An item without a restriction is global. If a global item and a restricted item use the same key, the restricted item wins in its program.

To add a second program to an item, go to that program and press `NVDA+Shift+E` twice quickly. Then paste the name into the field after a comma.

### Action types

*   **Website:** Opens an address in your default browser. It also opens other kinds of address, such as `ms-settings:bluetooth` for a page of Windows Settings, or `mailto:name@example.com`.
*   **Program:** Starts a program. You can give a full path or a name Windows already knows, such as `notepad` or `cmd`. You can also add **Arguments**, and tick **Run as administrator**. Batch files (`.bat` and `.cmd`) work here too.
*   **Folder:** Opens a folder in File Explorer.
*   **File:** Opens a file in its default program.
*   **NVDA command:** Runs an NVDA command. Press **Select command** to choose one from a list you can filter.
*   **Text snippet:** Uses your own text in one of three ways:
    *   **Type the text:** Types it as if you pressed the keys. **Typing delay** sets the pause between characters.
    *   **Copy:** Puts it on the clipboard.
    *   **Paste:** Pastes it, then puts your old text back on the clipboard. Only text can be restored.
*   **Keystrokes:** Presses keys, one key or shortcut per line, such as `alt+f4` or `shift+f10`.
    *   To repeat a key, add a space and a number: `down 5`.
    *   A line that starts with `#` is skipped, so you can use it for a note.
    *   **Add keystroke:** Press this button, then press a key, and it is added as a new line. Numeric keypad keys can't be recorded. `Escape` cancels, so type `esc` if you need it.
    *   **Delay between keystrokes (seconds):** The pause between keys.

Every action also has:

*   **Delay before executing this action (seconds):** A pause before this action. Use it when one step needs more time than the others, such as a slow program.
*   **Test:** Tries this one action without saving. If it types, presses keys, or reads the selected text or File Explorer, the add-on asks you first, then waits 3 seconds so you can switch to the window you want.

### Variables

A variable is a word in braces that the add-on replaces when the item runs. They work in text snippets, website addresses and program arguments. Press **Insert variable** next to the field to choose one:

*   **Date** (`{date}`) and **Time** (`{time}`): Now, in your Windows format.
*   **Clipboard text** (`{clipboard}`): The text you copied.
*   **Selected text** (`{selection}`): The text selected when the item starts.
*   **Selected file** (`{file}`): The file selected in File Explorer. If several are selected, all of them are used.
*   **Open folder** (`{folder}`): The folder open in File Explorer.

Good to know:

*   If an item needs selected text, a selected file or an open folder and there is none, it stops before doing anything and tells you why.
*   If a File Explorer window has several tabs, the file or folder may come from a tab other than the one you see.
*   `{clipboard}`, `{selection}`, `{file}` and `{folder}` can't be used in the arguments of `.bat` and `.cmd` files, because the text could run as commands.
*   To type a brace, double it: `{{` gives `{` and `}}` gives `}`.
*   If you made items with an older version, check any text that contains braces. Words such as `{date}` are now replaced, and `{{` now gives `{`.

### Arguments

Arguments tell a program what to do when it starts. To find a program's arguments, look in its help pages, or run it in Command Prompt with `--help` or `/?`.

### Back up and move your items

Use **Export settings** to save everything to a file, and **Import settings** to load a file. After you choose a file, the add-on asks what to do:

*   **Replace:** The items and settings in the file replace all of yours.
*   **Merge:** Items with a new name and a free shortcut are added, and your settings stay as they are. The add-on tells you how many were added and skipped.

The add-on keeps a backup of your items in `config.json.bak`. If your settings file is ever damaged, it offers to restore the backup.

## If something goes wrong

1.  Do the thing that failed.
2.  Press `NVDA+F1` to open the NVDA log.
3.  Find the lines that contain `instantAccess:`, and copy them.
4.  Post them on the [issues page](https://github.com/kamalyaser31/instantAccess/issues) with a short note about what you did.

These lines can show your item names and file paths, so read them before you post.

See what changed in each version in the [changelog](https://github.com/kamalyaser31/instantAccess/blob/main/changelog.md).

## For developers

The source is on [GitHub](https://github.com/kamalyaser31/instantAccess). Build the add-on with `uv run scons`, and run the tests with `uv run python -m unittest discover -s tests`.

## Developer

*   **Developer:** Kamal Yaser
*   **Email:** [kamalyaser31@gmail.com](mailto:kamalyaser31@gmail.com)
*   **Telegram:** [@kamalyaser31](https://t.me/kamalyaser31)

## License

Copyright (C) 2026 Kamal Yaser.
This add-on is licensed under the GNU General Public License (GPL) Version 2 or any later version.

It includes a trimmed copy of the [keyboard](https://github.com/boppreh/keyboard) library by BoppreH, under the MIT License. The license text is in `globalPlugins/core/keyboard/LICENSE.txt`.
