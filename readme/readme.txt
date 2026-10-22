Plugin for CudaText.
It compares two files and shows them side-by-side.
Plugin shows two files in a single tab.

It gives few commands in menu "Plugins / Differ".
Command "Refresh" runs comparison again, if one or both files were edited.
It has options dialog, call it via "Options / Settings-plugins / Differ / Config".

Plugin supports CudaText running with "-p" command-line param:
  cudatext -p=cuda_differ#filename1#filename2
This will run CudaText with 2 given filenames in the Differ plugin.

The plugin can also produce a diff file (or patch).

Authors:
  OlehL, https://github.com/OlehL
  Alexey Torgashin (CudaText)
  Andrey Kvichanskiy, https://github.com/kvichans
  Vivalzar, https://github.com/Vivalzar
License: MIT
