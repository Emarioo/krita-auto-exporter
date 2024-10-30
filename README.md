# Auto exporter
This Krita plugin automatically exports a `.png` "thumbnail" file when you save a document. The file will end up in the same folder as the `.kra` document. The image below shows the **Auto Exporter** docker and an auto-exported image.

![](/docs/img/example.png)

<!--
Sections below are pasted into Manual.md except for Installation and downwards.
-->

## Features
- Auto export .png file when document is saved. (ignores autosaves)
- A docker for controlling if and how the document is exported
- Ability to enable auto-export on a per document basis. Exporting is disabled on all documents by default.
- Ability to crop the exported image (full image by default)
- Ability to choose which layers to make visible and hidden before exporting. This is done using Python regex on the layers' names.

## Cropping an image
The number boxes beside the crop area label begin with X and Y offset and then the last two are for width and height. -1 means the current width/height.

## Layer regex
The regex on layers' names uses the Python `re` module. Empty text will do nothing, layers that are hidden and visible will remain as they are.

Here are some examples of regex.
- `Background` will match layers with names `Background`, `Background 1`, and `Backgroundhello` but not `Backgund`.
- `top mask$` will match layers which has the exact name `top mask` while `stop mask` and `top mask 5` will not match.
- `.*show$` will match layers that end with `show`.
- `(?!.*hide).*` will match all names that **DO NOT** contain `hide`.

## Minor inconveniences
When you save and the auto exporter resizes the image it will be registered in
the undo history. The Krita Python API doesn't have access to undo actions so you will have to deal with undo history littered with two resize image everytime you save an auto-exported document. Let me know if you have any ideas on how to solve it.

Saving may be slower than usual since you are also exporting an image (if the document uses auto-export).

<!--
It's a bigger problem when the visibilty of many layers are changed. Your undo history will be filled with garbage.
ACTUALL NO, Krita is smart and doesn't add layer property changes to the history since we toggle the visibilty right back. Nicely done Krita developers!
Still want that undo feature in Python plugins though.
-->

# Installation
There are Three ways:
- Go into *Tools > Scripts > Import Python from Web* and paste `https://github.com/Emarioo/krita-auto-exporter` into the text box.
- Download the latest release (zip file) and in Krita go to *Tools > Scripts > Import Python from File* and select the downloaded zip file.
- Clone the repo and move the contents of `krita_plugin` into `%APPDATA%/krita/pykrita/` (contents being `auto_exporter` and `auto_exporter.desktop`). You could run `install.bat` which will automatically move the contents but it is mainly meant for use during development.

Don't forget to enable **Auto Exporter** in *Configure Krita > Python Plugins Manager*. You may need to restart once after importing the plugin and a second time after enabling it.

# Implementation notes
The plugin creates a directory in it's plugin directory that stores which documents the auto-export is enabled for among other things (`auto_exporter/user_data/export_settings.txt`). There is also a log file used when debugging (`auto_exporter/user_data/log.txt`).

# Future features
- Specify other directory to export to?
- Log saved files in the log.txt file?
- A feature to control how frequently you export when saving. Every second or third time for example. Or perhaps an image is exported once under one minute even if you save multiple times during that minute. Another option would be to detect if saving+exporting takes a long time and how much the document has changed and determine if an export is worthwhile.
- Use QSettings instead of `user_data/export_settings.txt`.