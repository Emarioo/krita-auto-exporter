# Auto exporter
This Krita plugin automatically exports `.png` files when you save documents. The file will end up in the same folder as the `.kra` document.

## Features
- Auto export .png file when document is saved. (ignores autosaves)
- Auto exporter docker which allows you to enable the auto-export feature per document.
- Docker allows you to crop the exporter image (full image by default)

## Cropping an image
It's a bit scuffed but you crop by entering four numbers separated by one space in the crop area text box. The first two numbers are the X and Y offset while the last two are the width and height, in pixels.

# Installation
There are two ways:
- Clone the repo or somehow download the `auto_exporter` folder and `auto_exporter.desktop` and manually move them into `%APPDATA%/krita/pykrita/`.
- Download the latest release and in Krita go to *Tools > Scripts > Import Python from File* and select the downloaded zip file.

Don't forget to enable **Auto Exporter** in *Configure Krita > Python Plugins Manager*.

# Implementation notes
The plugin creates a directory in it's plugin directory that stores which documents the auto-export is enabled for and how the image should be cropped (`auto_exporter/user_data/export_settings.txt`). There is also a log file (`auto_exporter/user_data/log.txt`).

# Future features
Customize export settings.
- Add layers to hide and show before exporting.
- Specify other directory to export to?
- Log saved files in the log.txt file.