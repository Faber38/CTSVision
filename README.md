# CTSVision

> **Computer Vision, OCR and Journal Framework for Elite Dangerous**

[🇬🇧 English](README.md) | [🇩🇪 Deutsch](README_DE.md)

## ⚠️ Important Notice – Frontier Developments / Elite Dangerous

CTSVision automates certain operations when using a Fleet Carrier in **Elite Dangerous**. Frontier Developments' rules prohibit certain forms of gameplay automation. Fleet Carrier automation may be considered a violation of these rules.

**Using CTSVision may therefore result in warnings, restrictions, a temporary suspension, or other action against your Elite Dangerous account.**

CTSVision is an independent community project and is **not affiliated with Frontier Developments, supported by Frontier Developments, or approved by Frontier Developments**.

**Use of this software is entirely at your own risk.**

Before using CTSVision, please review the current **Elite Dangerous Terms of Use, EULA and Frontier Code of Conduct**.

## What is CTSVision?

CTSVision is an open-source project for analyzing the **Elite Dangerous** user interface.

![CTSVision Banner](docs/images/ctsvision_banner.png)

The framework combines **Computer Vision**, **OCR (PaddleOCR)** and **Journal analysis** to reliably detect game states.

### Features
- Vision-based menu detection
- OCR (PaddleOCR)
- Journal Monitor
- Vision Wizard
- Reference image management
- Debug tools
- Native Linux support
- Modular architecture

# 🚀 Quick Start

## 1. Download the repository

```bash
git clone https://github.com/Faber38/CTSVision.git
cd CTSVision
```

## 2. Installation

Run the installation script:

```bash
chmod +x install.sh start.sh
./install.sh
```

The script automatically:

- creates the Python virtual environment
- installs all required Python packages
- prepares CTSVision for its first start

## 3. Start CTSVision

After a successful installation, simply use:

```bash
./start.sh
```

The start script:

- automatically activates the Python environment,
- checks whether **Elite Dangerous** is already running,
- and then starts CTSVision.

---

# 👁 First Start

Before using CTSVision for the first time, reference images for your own screen resolution should be created with the **Vision Wizard**.

Good reference image quality is essential for reliable image recognition.

**Tip:** When creating reference images, the coordinate fields in the Vision Wizard can be adjusted very precisely using the **↑ ↓ arrow keys**. This is especially useful when the selection frame is not visible or is difficult to see on the game screen.

## Recommendations

- Create reference images **as small as possible and only as large as necessary**.
- Capture only static elements such as menus, icons or buttons.
- Avoid stars, nebulae, planets or other dynamic backgrounds.
- Create new reference images after changing the screen resolution or UI scaling.
- Test the generated reference images afterwards with the Vision Wizard.
- For automatic refueling, it is recommended to always use **the same ship** whenever possible. A ship with **the largest possible cargo capacity** is preferable, as menu positions may vary slightly between different ship types.

## Project Philosophy

CTSVision does not make uncertain decisions.

**Robustness before speed.**

### Version 1.9
✨ New
- **Integrated help added.**
  CTSVision now includes built-in German help that can be opened directly from the main window.
  It explains the main functions, settings, assistants, safety mechanisms,
  and the operation of the route and refueling automation.
- **Manual XYZ route planner added.**
  Fleet Carrier routes can now be planned completely by hand using the XYZ coordinates
  from the Elite Dangerous galaxy map.
  The planner is especially useful for distant or sparsely explored regions
  where systems may not yet be known to EDD or Spansh.
- **Step-by-step planning with real systems.**
  CTSVision calculates a theoretical search point in the direction of the destination
  (495 ly by default). A real system near that point is then selected in the galaxy map
  and entered with its actual XYZ coordinates.
  The next search point is always recalculated from the system that was really selected.
- **Carrier jump range validation.**
  Before a system is accepted, CTSVision checks whether the actual distance
  is within the configured maximum Fleet Carrier jump range.
- **Direct handover to CTSVision.**
  A completed manual route can be saved as a CTSVision-compatible CSV file
  and loaded directly as the current route.
- **Improved “Resume Route” function.**
  After an interruption or unexpected shutdown of CTSVision, the user can now specify
  the route system where the Carrier is actually located.
  This is especially useful when Elite Dangerous still completes an already requested Carrier jump
  after CTSVision has stopped and CTSVision therefore never receives the corresponding `CarrierJump`.
- **Manual correction of route progress.**
  When resuming, CTSVision shows the stored progress, the selected current location
  and the resulting next jump destination. The new progress is only saved after confirmation.
- **Manual route planning documented in the integrated help.**
  The help explains XYZ coordinate orientation, the planning workflow
  and how the finished route is handed over to CTSVision.

### Version 1.8
✨ New
- **Dark Mode** added.
  The appearance can be switched directly in CTSVision and the setting is saved permanently.
  Dark Mode is also applied to the separate route information window.
- **Single-instance protection** added.
  CTSVision can no longer be started multiple times accidentally.
- **Automatic closing of Elite Dangerous has been revised and made safer.**
  Before closing the game, CTSVision ensures that it is in a known menu state.
  If necessary, BACKSPACE is used step by step to return to Menu 1.
  CTSVision then opens the Odyssey menu and safely confirms it using the new
  `exit_menu_fortsetzen` vision reference before sending the keystrokes required to exit the game.
- **Elite Dangerous exit test** added.
  The “Test ED Exit” function allows the complete exit sequence to be tested independently of a route.
  The PC is never shut down during this test.
- **Vision Wizard improved.**
  A new “ED Exit – CONTINUE” reference is available for safely detecting the Odyssey menu.
  Image preview handling has also been improved so that previews resize correctly with the window
  without cropping reference images or shifting controls.

### Version 1.7.1
✨ New
- Elite Dangerous can be closed automatically after the jump route has been completed successfully.
  This only happens if the automation has completed successfully.
- If desired, the PC can then also be shut down automatically.
  The PC is only shut down if Elite Dangerous was successfully closed first.
- Automatic update checking has been added.
  CTSVision checks for a new version on GitHub at startup.
- If a new version is available, this is shown directly in the version display.
- Updates can be installed directly from CTSVision.
  A backup of the existing installation is created automatically before installation.
- Personal data such as configuration, reference images, routes and runtime data are preserved during the update.
- After a successful installation, CTSVision restarts automatically.

### Version 1.6
- The route is updated immediately after the CarrierJump.
- The current destination is immediately marked as completed.
- The next jump destination is shown in the GUI immediately.
- This keeps the route display up to date throughout the cooldown period.
- Fuel check before the first jump.
- Before the first jump, CTSVision checks whether enough Tritium is available in the Carrier.
- If required, refueling is performed automatically.
- The first jump only starts after a successful fuel check.

Improvements:
- More consistent workflow between the first and all subsequent jumps.
- Route status always remains up to date during the cooldown phase.
- Greater reliability before starting a long Carrier route.

### Version 1.5
- Vision Wizard
- OCR
- Journal Monitor
- Tank Wizard
- Workspace protection

![CTSVision Banner](docs/images/Haupt.png)

## Roadmap

### Version 2.0
- Internationalization
- Windows support
- Plugin system

GNU GPL v3.0

Developed by **Faber38**
