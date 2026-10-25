"""One-off visual verification harness (not part of the package).

Renders the main window offscreen and saves screenshots so the UI changes
can be inspected without screen-recording permission:

* welcome page, light + dark, default (English) locale
* welcome page in a narrow window — the three cards must not overlap
* the example project loaded through the real entry point
"""

import sys

sys.path.insert(0, "src")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(["-platform", "offscreen"])
# Force the harness onto the first-launch language.  clear() cannot be used:
# stale keys may sit in a QSettings *fallback* location it refuses to touch,
# and this harness (no app/org name) reads that fallback.  Real users get
# English by simply having no saved preference.
from PySide6.QtCore import QSettings  # noqa: E402

QSettings().setValue("ui/language", "en")
from pyitolstudio.theme import build_stylesheet  # noqa: E402
from pyitolstudio.theme_mode import build_palette, current_dark, set_override  # noqa: E402


def apply(dark: bool) -> None:
    """Theme exactly the way main.py does: one current_dark() drives QSS,
    palette and pixmap re-rasterisation together."""
    set_override(dark)
    app.setStyleSheet(build_stylesheet(current_dark()))
    app.setPalette(build_palette(current_dark()))


apply(False)
from pyitolstudio.app.main_window import MainWindow  # noqa: E402

win = MainWindow()
win.retheme_ui()
win.resize(1280, 800)
win.show()
app.processEvents()
win.grab().save("/tmp/check_welcome_light.png")

# Narrow window: the three action cards must not overlap.
win.resize(760, 640)
app.processEvents()
win.grab().save("/tmp/check_welcome_narrow.png")

# Dark mode look (black/white/grey + Klein blue accent).
apply(True)
win.retheme_ui()
win.resize(1280, 800)
app.processEvents()
win.grab().save("/tmp/check_welcome_dark.png")

# Load the example project through the real entry point.
win.resize(1280, 800)
win.load_example_project()
for _ in range(20):
    app.processEvents()
from pyitolstudio.i18n import translator  # noqa: E402

print("locale:", translator().locale)
print("tree_path:", win.project.tree_path)
print("units:", [u.label for u in win.project.units])
print("current:", win.current_unit.label if win.current_unit else None)
win.grab().save("/tmp/check_example_dark.png")

apply(False)
win.retheme_ui()
app.processEvents()
win.grab().save("/tmp/check_example_light.png")
print("OK")
