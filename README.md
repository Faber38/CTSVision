# CTSVision

> **Computer Vision & OCR Framework for Elite Dangerous**

![CTSVision Banner](assets/ctsvision_banner.png)

CTSVision is a modular **Computer Vision Framework** for **Elite
Dangerous**. It combines **template matching**, **OCR (PaddleOCR)** and
**Journal monitoring** to reliably detect game states.

The project is designed around reusable vision components. Optional
modules can build on these components for analysis or other workflows.

------------------------------------------------------------------------

## ✨ Features

-   Vision-based menu detection
-   OCR text recognition with PaddleOCR
-   Live Journal monitoring
-   Reference Image Wizard
-   Debug & diagnostic tools
-   Resolution-specific reference images
-   Native Linux support
-   Python / PySide6

------------------------------------------------------------------------

## 🏗 Architecture

``` text
Elite Dangerous
        │
        ▼
+----------------------+
|    Vision Engine     |
+----------------------+
        │
 ┌──────┼───────────┐
 │      │           │
OCR   Journal   Templates
 │      │           │
 └──────┼───────────┘
        ▼
 State Detection
        │
        ▼
 Optional Modules
```

------------------------------------------------------------------------

## 📂 Project Structure

``` text
CTSVision/
├── automation_gui.py
├── vision.py
├── vision_wizard.py
├── journal_monitor.py
├── tank_controller.py
├── ocr/
├── references/
├── config/
├── tools/
└── assets/
```

------------------------------------------------------------------------

## 👁 Vision Wizard

The Vision Wizard creates reference images that match your own screen
resolution.

### Best Practice

-   Create reference images as small as possible and only as large as
    necessary.
-   Capture only static UI elements such as menus, icons or buttons.
-   Avoid dynamic backgrounds like stars, nebulae or planets.

------------------------------------------------------------------------

## 🔎 OCR

Uses PaddleOCR to recognize:

-   Tank levels
-   Cargo lists
-   Inventory
-   Transfer menus
-   UI text

------------------------------------------------------------------------

## 📖 Journal Monitoring

-   Automatic journal detection
-   Handles journal rotation
-   Reads events in real time

------------------------------------------------------------------------

## 🛠 Debug Tools

-   Screenshot capture
-   Template matching
-   OCR debugging
-   Detailed logging

------------------------------------------------------------------------

## ⚙ Requirements

-   Linux (tested with Pop!\_OS)
-   Python 3.11+
-   Elite Dangerous
-   PaddleOCR
-   PySide6
-   OpenCV

------------------------------------------------------------------------

## 🚀 Installation

``` bash
git clone https://github.com/Faber38/CTSVision.git
cd CTSVision
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python automation_gui.py
```

------------------------------------------------------------------------

## ❤️ Philosophy

CTSVision focuses on reliable state detection.

If the application cannot determine the current game state safely, it
stops instead of making assumptions.

------------------------------------------------------------------------

## 🗺 Roadmap

-   ✅ Vision Wizard
-   ✅ OCR Engine
-   ✅ Journal Monitor
-   ✅ Tank Wizard
-   ✅ Debug Tools
-   ⬜ Route Wizard
-   ⬜ Plugin System
-   ⬜ Statistics
-   ⬜ Settings

------------------------------------------------------------------------

## 📄 License

GNU GPL v3.0

Developed by **CMDR Faber38** for the Elite Dangerous community.

Fly safe, o7
