Plugin for CudaText.
It compares two files and shows them side-by-side.
Plugin shows two files in a single tab.

It gives few commands in menu "Plugins / Differ".
Command "Refresh" runs comparision again, if one or both files were edited.

It has few options in config file. To open config, call "Options / Settings-plugins / Differ / Config". Options:

- "added", "changed", "deleted": Changed lines highlight colors. Must be in HTML form #rgb or #rrggbb. If empty, then colors from the current theme are used.
- "enable_scroll_default": bool, 0 or 1: Sync scrolling in both compared files. 


Authors:
  OlehL, https://github.com/OlehL
  Alexey T. (CudaText)
License: MIT
