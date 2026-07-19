from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from automation_gui import AutomationWindow


def main() -> int:
    """
    Startet die Carrier-Automatik-Oberfläche.
    """

    app = QApplication(sys.argv)

    window = AutomationWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
