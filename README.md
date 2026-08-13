# CTSVision

> **Computer Vision, OCR & Journal Framework for Elite Dangerous**

[🇬🇧 English](README.md) | [🇩🇪 Deutsch](README_DE.md)

## ⚠️ Important – Frontier Developments / Elite Dangerous

CTSVision automates certain Fleet Carrier operations in **Elite Dangerous**. Frontier Developments' rules prohibit certain forms of gameplay automation, and Fleet Carrier automation may be considered a violation of those rules.

**Using CTSVision may therefore result in warnings, restrictions, suspension, or other action against your Elite Dangerous account.**

CTSVision is an independent community project and is **not affiliated with, endorsed by, or approved by Frontier Developments**.

**Use this software entirely at your own risk.**

Before using CTSVision, please review the current **Elite Dangerous Terms of Use, EULA, and Frontier Code of Conduct**.

## What is CTSVision?

CTSVision is an open-source framework combining Computer Vision, OCR and Journal monitoring for Elite Dangerous.

![CTSVision Banner](docs/images/ctsvision_banner.png)

### Features
- Vision-based menu detection
- OCR
- Journal Monitor
- Vision Wizard
- Debug Tools
- Modular architecture

## Philosophy
Robustness first.

### Version 1.7.1
✨ New
- Elite Dangerous can be closed automatically after the jump route has been completed successfully.
  This will only happen if the automation finishes successfully.
- If desired, the PC can be shut down automatically afterwards.
  The PC will only shut down after Elite Dangerous has been closed successfully.
- Automatic update checking has been added.
  CTSVision checks for new versions on GitHub at startup.
- If a new version is available, it is shown directly in the version indicator.
- Updates can be installed directly from CTSVision.
  A backup of the existing installation is created automatically before the update is installed.
- Personal data such as configuration, reference images, routes and runtime data are preserved during updates.
- After a successful update, CTSVision restarts automatically.

## 🚀 CTSVision 1.6

### Added
- Initial carrier fuel check before the first jump.
- Automatic refueling can now be performed before the route starts.

### Improved
- Route progress is now updated immediately after a successful CarrierJump.
- The next destination becomes visible instantly while cooldown and refueling continue in the background.
- Improved overall automation workflow and synchronization.

As always, CTSVision acts as a computer vision assistant for Fleet Carrier navigation and monitoring.

### Version 1.5
- Vision Wizard
- OCR
- Journal Monitor
- Tank Wizard


## Roadmap

### Version 2.0
- Internationalization
- Windows support
- Plugin system

GNU GPL v3.0

