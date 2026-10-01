"""Welcome page (empty state) — design book §5.2.

Three action cards, a recent-projects list that says *where* a project lives
and how much is in it, and a drop zone that names the two file types the app
can open.  The ground is the plain QSS ``canvas`` colour — the old faint
radial grid was removed (UI review: visual noise behind the centred content).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QModelIndex, QObject, QPropertyAnimation, QRect, QSize, Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..icons import icon_pixmap
from ..project import load_project
from ..theme import (
    FONT_SIZE,
    FONT_SIZE_CAPTION,
    FONT_WEIGHT_STRONG,
    MONO_FAMILIES,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    SPACE_7,
    SPACE_8,
)
from ..theme_mode import theme_color, theme_qcolor
from .widgets import LayoutSizeHintButton

RECENT_PATH_ROLE = int(Qt.ItemDataRole.UserRole) + 1

GRID_STEP = 44
GRID_RADIUS = 380
RECENT_ROW_HEIGHT = 46


class RecentItemDelegate(QStyledItemDelegate):
    """Recent project row: name over a mono path + unit count."""

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:  # noqa: N802
        name = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        detail = str(index.data(RECENT_PATH_ROLE) or "")
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if selected or hovered:
            painter.fillRect(option.rect, theme_qcolor("hover"))

        left = option.rect.left() + SPACE_4
        glyph = icon_pixmap("folder-tree", 14, theme_color("text_dim"))
        painter.drawPixmap(left, option.rect.center().y() - 7, glyph)

        text_left = left + 14 + SPACE_3
        rect = QRect(text_left, option.rect.top(), option.rect.right() - text_left - SPACE_4, option.rect.height())
        width = rect.width()

        name_font = painter.font()
        name_font.setPixelSize(FONT_SIZE)
        name_font.setWeight(QFont.Weight(FONT_WEIGHT_STRONG))
        metrics = QFontMetrics(name_font)
        det_font = QFont()
        det_font.setFamilies(list(MONO_FAMILIES))
        det_font.setPixelSize(FONT_SIZE_CAPTION)
        det_metrics = QFontMetrics(det_font)

        painter.save()
        painter.setFont(name_font)
        painter.setPen(theme_qcolor("text"))
        painter.drawText(
            QRect(rect.left(), rect.top() + SPACE_2, width, metrics.height()),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            metrics.elidedText(name, Qt.TextElideMode.ElideMiddle, width),
        )
        painter.setFont(det_font)
        painter.setPen(theme_qcolor("text_tertiary"))
        painter.drawText(
            QRect(rect.left(), rect.top() + metrics.height() + SPACE_1, width, det_metrics.height()),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            det_metrics.elidedText(detail, Qt.TextElideMode.ElideMiddle, width),
        )
        painter.restore()

    def sizeHint(self, option, index: QModelIndex) -> QSize:  # noqa: N802
        return QSize(0, RECENT_ROW_HEIGHT)


class _CardHoverFilter(QObject):
    """Give a welcome action-card a quiet 3px hover lift (review P2 — small
    micro-interaction, fits the Instrument tone: quick, no bounce)."""

    _LIFT = 3
    _DURATION = 140

    def __init__(self, card: QPushButton) -> None:
        super().__init__(card)
        self._card = card
        self._baseline = card.pos()
        self._anim: QPropertyAnimation | None = None
        card.installEventFilter(self)

    def _animate(self, hovered: bool) -> None:
        if self._anim is not None:
            self._anim.stop()
        card = self._card
        start = card.pos()
        end = QRect(
            self._baseline.x(),
            self._baseline.y() - (self._LIFT if hovered else 0),
            card.width(),
            card.height(),
        ).topLeft()
        anim = QPropertyAnimation(card, b"pos", self)
        anim.setDuration(self._DURATION)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(start)
        anim.setEndValue(end)
        self._anim = anim
        anim.start()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt API)
        # Re-baseline if the layout moved us between hovers.
        if event.type() == QEvent.Type.Enter:
            self._baseline = self._card.pos()
            self._animate(True)
            return False
        if event.type() == QEvent.Type.Leave:
            self._animate(False)
            return False
        return False


class WelcomePage(QWidget):
    """Empty-state landing: three cards + recent projects (§5.1/§5.2)."""

    new_project = Signal()
    open_project = Signal()
    browse_examples = Signal()
    open_path = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("welcome")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(SPACE_8, SPACE_8, SPACE_8, SPACE_8)
        layout.setSpacing(0)
        layout.addStretch(1)

        self.logo = QLabel()
        self.logo.setObjectName("welcomeLogo")
        self.logo.setFixedSize(74, 74)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignHCenter)

        self.title = QLabel(tr("app.title"))
        self.title.setObjectName("welcomeTitle")
        layout.addSpacing(SPACE_5)
        layout.addWidget(self.title, 0, Qt.AlignmentFlag.AlignHCenter)

        self.subtitle = QLabel(tr("app.subtitle"))
        self.subtitle.setObjectName("welcomeSubtitle")
        layout.addSpacing(SPACE_3)
        layout.addWidget(self.subtitle, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addSpacing(SPACE_7)
        cards = QHBoxLayout()
        cards.setSpacing(SPACE_4)
        cards.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._cards: list[tuple[QPushButton, str, str, str]] = []
        self._card_glyphs: list[tuple[QLabel, str]] = []
        self._card_hovers: list[_CardHoverFilter] = []
        for icon_name, text_key, hint_key, signal in (
            ("file-plus", "welcome.new_project", "welcome.key_new", self.new_project),
            ("folder-open", "welcome.open_project", "welcome.key_open", self.open_project),
            ("wand", "welcome.examples", "", self.browse_examples),
        ):
            card = self._build_card(icon_name, text_key, hint_key)
            card.clicked.connect(signal.emit)
            cards.addWidget(card)
            self._cards.append((card, icon_name, text_key, hint_key))
        layout.addLayout(cards)

        layout.addSpacing(SPACE_7)
        self.recent_label = QLabel(tr("welcome.recent"))
        self.recent_label.setObjectName("caption")
        layout.addWidget(self.recent_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(SPACE_3)
        self.recent_list = QListWidget()
        self.recent_list.setObjectName("recentList")
        # Shrink with the window instead of overflowing it (fixed 610px only
        # fits the default 1280px layout).
        self.recent_list.setMinimumWidth(320)
        self.recent_list.setMaximumWidth(610)
        self.recent_list.setItemDelegate(RecentItemDelegate(self.recent_list))
        self.recent_list.setMouseTracking(True)
        self.recent_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent_list.itemDoubleClicked.connect(
            lambda item: self.open_path.emit(item.data(Qt.ItemDataRole.UserRole))
        )
        layout.addWidget(self.recent_list, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addSpacing(SPACE_5)
        layout.addWidget(self._build_dropzone(), 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(2)
        self.retranslate_ui()
        self.refresh_recent()

    # -- construction ----------------------------------------------------
    def _build_card(self, icon_name: str, text_key: str, hint_key: str) -> LayoutSizeHintButton:
        card = LayoutSizeHintButton()
        card.setObjectName("actionCard")
        # 196×104 was *fixed*, which clipped the description: the card holds a
        # 32px glyph + title row + a word-wrapped desc that needs two lines in
        # Chinese (~114px total) and three in English (~129px).  Two things fix
        # that: 196×104 becomes only the minimum (width stays pinned at the
        # designed 196 so the row stays centred), and the size hints delegate
        # to the embedded layout (LayoutSizeHintButton — the same fix the
        # wizard's step buttons use) with height-for-width enabled, so the
        # layout system sees the wrapped description's real height.  The
        # shared QHBoxLayout keeps all three cards equally tall
        # (UI review: button text must never truncate).
        card.setFixedWidth(196)
        card.setMinimumHeight(104)
        # Expanding alone is not enough: the layout system only asks a widget
        # for height-for-width when its size policy *has* that flag.  With it,
        # the wrapped description grows the card instead of being clipped.
        policy = card.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        policy.setHeightForWidth(True)
        card.setSizePolicy(policy)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        # Quiet hover lift on the card itself (review P2 — micro-interaction).
        # Keep every filter referenced: a single attribute would be overwritten
        # each loop, so only the last card's lift survived (UI review P2-8).
        self._card_hovers.append(_CardHoverFilter(card))
        inner = QVBoxLayout(card)
        inner.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        inner.setSpacing(0)
        glyph = QLabel()
        glyph.setObjectName("cardIcon")
        glyph.setFixedSize(32, 32)
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph.setPixmap(icon_pixmap(icon_name, 16, theme_color("accent")))
        self._card_glyphs.append((glyph, icon_name))
        inner.addWidget(glyph)
        inner.addSpacing(SPACE_3)
        row = QHBoxLayout()
        row.setSpacing(SPACE_2)
        name = QLabel(tr(text_key))
        name.setObjectName("cardName")
        row.addWidget(name)
        if hint_key:
            chip = QLabel(tr(hint_key))
            chip.setObjectName("kbd")
            row.addWidget(chip)
        row.addStretch(1)
        inner.addLayout(row)
        inner.addSpacing(SPACE_1)
        desc = QLabel(tr(f"{text_key}_desc"))
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        inner.addWidget(desc)
        inner.addStretch(1)
        return card

    def _build_dropzone(self) -> QWidget:
        host = QWidget()
        host.setObjectName("dropzone")
        row = QHBoxLayout(host)
        row.setContentsMargins(SPACE_5, SPACE_3, SPACE_5, SPACE_3)
        row.setSpacing(SPACE_2)
        glyph = QLabel()
        glyph.setPixmap(icon_pixmap("upload", 14, theme_color("text_tertiary")))
        self._drop_glyph = glyph
        row.addWidget(glyph)
        row.addSpacing(SPACE_2)
        self.drop_prefix = QLabel(tr("welcome.drop_prefix"))
        self.drop_prefix.setObjectName("dropText")
        self.drop_tree = QLabel(tr("welcome.drop_tree"))
        self.drop_tree.setObjectName("dropEmph")
        self.drop_mid = QLabel(tr("welcome.drop_or"))
        self.drop_mid.setObjectName("dropText")
        self.drop_template = QLabel(tr("welcome.drop_template"))
        self.drop_template.setObjectName("dropEmph")
        self.drop_suffix = QLabel(tr("welcome.drop_suffix"))
        self.drop_suffix.setObjectName("dropText")
        for widget in (
            self.drop_prefix,
            self.drop_tree,
            self.drop_mid,
            self.drop_template,
            self.drop_suffix,
        ):
            row.addWidget(widget)
        return host

    # -- Qt ---------------------------------------------------------------
    # No paintEvent override: the surface colour comes from the QSS rule
    # ``QWidget#welcome`` → ``canvas`` (``WA_StyledBackground`` paints it).
    # The old override drew a faint radial grid, which the review retired —
    # removing the override (rather than emptying it) also keeps a repaint
    # path shorter.

    # -- public API -------------------------------------------------------
    def retranslate_ui(self) -> None:
        self.title.setText(tr("app.title"))
        self.subtitle.setText(tr("app.subtitle"))
        self.recent_label.setText(tr("welcome.recent"))
        self.drop_prefix.setText(tr("welcome.drop_prefix"))
        self.drop_tree.setText(tr("welcome.drop_tree"))
        self.drop_mid.setText(tr("welcome.drop_or"))
        self.drop_template.setText(tr("welcome.drop_template"))
        self.drop_suffix.setText(tr("welcome.drop_suffix"))
        self.logo.setPixmap(icon_pixmap("folder-tree", 40, theme_color("on_accent")))
        for card, _, text_key, _ in self._cards:
            name_label = card.findChild(QLabel, "cardName")
            if name_label is not None:
                name_label.setText(tr(text_key))
            desc_label = card.findChild(QLabel, "cardDesc")
            if desc_label is not None:
                desc_label.setText(tr(f"{text_key}_desc"))

    def retheme_ui(self) -> None:
        """Re-rasterise the pixmaps that baked a theme colour (logo, card and
        dropzone glyphs) after a dark↔light switch; repaint the rest."""
        self.logo.setPixmap(icon_pixmap("folder-tree", 40, theme_color("on_accent")))
        for glyph, icon_name in self._card_glyphs:
            glyph.setPixmap(icon_pixmap(icon_name, 16, theme_color("accent")))
        self._drop_glyph.setPixmap(
            icon_pixmap("upload", 14, theme_color("text_tertiary"))
        )
        self.recent_list.viewport().update()

    def refresh_recent(self) -> None:
        from PySide6.QtCore import QSettings

        self.recent_list.clear()
        settings = QSettings()
        recent = settings.value("recent_projects", []) or []
        if isinstance(recent, str):  # QSettings may collapse a 1-item list
            recent = [recent]
        paths = [p for p in recent if isinstance(p, str) and Path(p).exists()]
        for path in paths:
            item = QListWidgetItem(Path(path).stem)
            item.setData(Qt.ItemDataRole.UserRole, path)
            # Path only for now — the unit count is loaded off-thread below,
            # so a slow (network) disk cannot stall the first paint.
            item.setData(RECENT_PATH_ROLE, self._display_path(path))
            self.recent_list.addItem(item)
        has_any = bool(paths)
        # Empty state: hide the caption and the (otherwise 192px) list box so a
        # first launch does not show an empty "Recent Projects" frame (P1-11).
        self.recent_label.setVisible(has_any)
        self.recent_list.setVisible(has_any)
        if has_any:
            self._load_details_async(paths)

    def _load_details_async(self, paths: list[str]) -> None:
        """Fetch the per-project unit counts on a worker thread (design plan
        §5.6 — every engine/file call stays off the UI thread)."""
        from ..adapter.tasks import EngineTask

        self._detail_generation = getattr(self, "_detail_generation", 0) + 1
        generation = self._detail_generation

        def _read_counts() -> dict[str, int]:
            counts: dict[str, int] = {}
            for path in paths:
                try:
                    counts[path] = len(load_project(path).units)
                except (ValueError, OSError):
                    pass  # unreadable project — keep the bare path
            return counts

        def _apply(counts: dict[str, int]) -> None:
            if generation != self._detail_generation:
                return  # a newer refresh happened meanwhile — drop this batch
            for row in range(self.recent_list.count()):
                item = self.recent_list.item(row)
                path = str(item.data(Qt.ItemDataRole.UserRole))
                count = counts.get(path)
                if count is not None:
                    item.setData(
                        RECENT_PATH_ROLE,
                        f"{self._display_path(path)} · {tr('welcome.unit_count', count)}",
                    )
            self.recent_list.viewport().update()

        task = EngineTask(_read_counts)
        task.finished_with.connect(_apply)
        # Keep the worker referenced (and drop stale references when done) so
        # Python cannot GC a running QThread; failed reads need no UI action.
        self._detail_tasks = getattr(self, "_detail_tasks", [])
        self._detail_tasks.append(task)
        task.finished.connect(lambda t=task: self._discard_detail_task(t))
        task.start()

    def _discard_detail_task(self, task) -> None:
        tasks = getattr(self, "_detail_tasks", None)
        if tasks and task in tasks:
            tasks.remove(task)

    @staticmethod
    def _display_path(path: str) -> str:
        return str(Path(path)).replace(str(Path.home()), "~")


__all__ = [
    "RECENT_PATH_ROLE",
    "RecentItemDelegate",
    "WelcomePage",
]
