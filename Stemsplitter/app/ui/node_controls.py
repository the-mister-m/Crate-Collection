"""NodeControls — Wave B of Session 2.

One instance per node. Holds every node-level control from the demucs
flag whitelist (docs/00-locked-spec.md DEMUCS FLAG WHITELIST): model,
stems, shifts, overlap, segment, format, mp3_bitrate, bit_depth --
plus ``mode``, which is not a demucs flag but decides what the checked
stems become on disk (see MODE_REMOVE / MODE_SEPARATE below).

Meant to be embedded inside Wave A's NodeCard body — this widget is
self-contained and does not build a card header, disclosure, or
remove button. get_node_config() is the seam: it returns this node's
slice of the run config dict (docs/00-locked-spec.md THE RUN CONFIG
DICT), everything except id/output_dir/filename_template, which
belong to Wave A/Wave C.

Mock data only. Nothing here calls demucs.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Stem names per model, in the order each model lists its stems.
# 4-stem models: drums, bass, vocals, other. htdemucs_6s adds guitar, piano.
MODEL_STEMS: dict[str, list[str]] = {
    "mdx_extra_q": ["drums", "bass", "vocals", "other"],
    "htdemucs": ["drums", "bass", "vocals", "other"],
    "htdemucs_ft": ["drums", "bass", "vocals", "other"],
    "htdemucs_6s": ["drums", "bass", "vocals", "other", "guitar", "piano"],
    "mdx_extra": ["drums", "bass", "vocals", "other"],
}

MODELS = ["mdx_extra_q", "htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx_extra"]

DEFAULT_MODEL = "htdemucs"
SEGMENT_MIN = 1
SEGMENT_MAX = 999

# What the checked stems become on disk. In BOTH modes a checked stem is
# a stem you want; the mode only decides whether they land in one file or
# many. Remove is the original behaviour and stays the default.
MODE_REMOVE = "remove"      # sum the checked stems into one file
MODE_SEPARATE = "separate"  # write each checked stem as its own file
DEFAULT_MODE = MODE_REMOVE


class NodeControls(QWidget):
    # Fires on every mode change so OUTPUT can grey out the suffix field it
    # no longer owns in separate mode. Carries "remove" | "separate".
    mode_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        self._stem_checkboxes: dict[str, QCheckBox] = {}

        outer = QVBoxLayout(self)

        # --- model -----------------------------------------------------
        model_form = QFormLayout()
        model_form.setContentsMargins(0, 0, 0, 0)
        model_form.setSpacing(6)
        model_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        model_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        model_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)
        self.model_combo.setCurrentText(DEFAULT_MODEL)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_form.addRow("Model", self.model_combo)
        outer.addLayout(model_form)

        # --- mode ----------------------------------------------------------
        # Sits directly above the stems grid because it is what the grid's
        # checkmarks mean: one summed file, or one file each.
        self.mode_remove_radio = QRadioButton("Remove stems")
        self.mode_remove_radio.setToolTip(
            "Sum the checked stems into a single file."
        )
        self.mode_separate_radio = QRadioButton("Separate stems")
        self.mode_separate_radio.setToolTip(
            "Write each checked stem as its own file, named after the stem."
        )
        self.mode_remove_radio.setChecked(True)

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.mode_remove_radio)
        self._mode_group.addButton(self.mode_separate_radio)
        # One radio is enough to listen to: an exclusive group toggles both.
        self.mode_remove_radio.toggled.connect(self._on_mode_toggled)

        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(12)
        mode_row.addWidget(self.mode_remove_radio)
        mode_row.addWidget(self.mode_separate_radio)
        mode_row.addStretch(1)
        outer.addLayout(mode_row)

        # --- stems -------------------------------------------------------
        self.stems_grid = QGridLayout()
        self.stems_grid.setContentsMargins(0, 0, 0, 0)
        self.stems_grid.setHorizontalSpacing(12)
        self.stems_grid.setVerticalSpacing(4)
        outer.addLayout(self.stems_grid)

        stem_buttons = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        select_all_btn.clicked.connect(self._select_all_stems)
        deselect_all_btn.clicked.connect(self._deselect_all_stems)
        stem_buttons.addWidget(select_all_btn)
        stem_buttons.addWidget(deselect_all_btn)
        stem_buttons.addStretch(1)
        outer.addLayout(stem_buttons)

        self._populate_stems(MODEL_STEMS[DEFAULT_MODEL])

        # --- remaining node fields ---------------------------------------
        fields_form = QFormLayout()
        fields_form.setContentsMargins(0, 0, 0, 0)
        fields_form.setSpacing(6)
        fields_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        fields_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        fields_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        self.shifts_spin = QSpinBox()
        self.shifts_spin.setFixedWidth(90)
        self.shifts_spin.setRange(0, 10)
        self.shifts_spin.setValue(0)
        fields_form.addRow("Shifts", self.shifts_spin)

        self.overlap_spin = QDoubleSpinBox()
        self.overlap_spin.setFixedWidth(90)
        self.overlap_spin.setDecimals(2)
        self.overlap_spin.setRange(0.0, 0.99)
        self.overlap_spin.setSingleStep(0.01)
        self.overlap_spin.setValue(0.25)
        fields_form.addRow("Overlap", self.overlap_spin)

        self.segment_spin = QSpinBox()
        self.segment_spin.setFixedWidth(90)
        self.segment_spin.setRange(SEGMENT_MIN, SEGMENT_MAX)
        self.segment_spin.setSpecialValueText("default")
        self.segment_spin.setValue(SEGMENT_MIN)
        fields_form.addRow("Segment", self.segment_spin)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["wav", "mp3", "flac"])
        self.format_combo.setCurrentText("wav")
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        fields_form.addRow("Format", self.format_combo)

        self.mp3_bitrate_spin = QSpinBox()
        self.mp3_bitrate_spin.setFixedWidth(90)
        self.mp3_bitrate_spin.setRange(32, 320)
        self.mp3_bitrate_spin.setValue(320)
        fields_form.addRow("MP3 bitrate", self.mp3_bitrate_spin)

        self.bit_depth_combo = QComboBox()
        self.bit_depth_combo.addItems(["int24", "float32", "model default"])
        self.bit_depth_combo.setCurrentText("model default")
        fields_form.addRow("Bit depth", self.bit_depth_combo)

        outer.addLayout(fields_form)

        self._on_format_changed(self.format_combo.currentText())

    # --- stems grid ------------------------------------------------------

    def _populate_stems(self, stem_keys: list[str]) -> None:
        self._stem_checkboxes = {}
        for index, stem_key in enumerate(stem_keys):
            checkbox = QCheckBox(stem_key.title())
            checkbox.setChecked(True)
            row, col = divmod(index, 2)
            self.stems_grid.addWidget(checkbox, row, col)
            self._stem_checkboxes[stem_key] = checkbox

    def _clear_stems(self) -> None:
        while self.stems_grid.count():
            item = self.stems_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _select_all_stems(self) -> None:
        for checkbox in self._stem_checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all_stems(self) -> None:
        for checkbox in self._stem_checkboxes.values():
            checkbox.setChecked(False)

    # --- reactions ---------------------------------------------------------

    def _on_model_changed(self, model_name: str) -> None:
        self._clear_stems()
        self._populate_stems(MODEL_STEMS.get(model_name, MODEL_STEMS[DEFAULT_MODEL]))

    def _on_mode_toggled(self, _checked: bool) -> None:
        self.mode_changed.emit(self.get_mode())

    def _on_format_changed(self, format_name: str) -> None:
        self.mp3_bitrate_spin.setEnabled(format_name == "mp3")
        self.bit_depth_combo.setEnabled(format_name != "mp3")

    # --- seam: this node's slice of the run config dict ---------------------

    def get_mode(self) -> str:
        """MODE_REMOVE | MODE_SEPARATE — read by OUTPUT and by the mixer."""
        return MODE_SEPARATE if self.mode_separate_radio.isChecked() else MODE_REMOVE

    def get_node_config(self) -> dict:
        """This node's slice of the run config dict.

        Returns model, mode, stems, shifts, overlap, segment, format,
        mp3_bitrate, bit_depth. Every field but mode matches
        docs/00-locked-spec.md THE RUN CONFIG DICT field names and types;
        mode is an addition the spec does not yet carry. Does not include
        id/output_dir/filename_template (Wave A/Wave C own those).
        """
        segment_value = self.segment_spin.value()
        segment = None if segment_value == SEGMENT_MIN else segment_value

        bit_depth_text = self.bit_depth_combo.currentText()
        bit_depth = None if bit_depth_text == "model default" else bit_depth_text

        return {
            "model": self.model_combo.currentText(),
            "mode": self.get_mode(),
            "stems": {
                stem_key: checkbox.isChecked()
                for stem_key, checkbox in self._stem_checkboxes.items()
            },
            "shifts": self.shifts_spin.value(),
            "overlap": self.overlap_spin.value(),
            "segment": segment,
            "format": self.format_combo.currentText(),
            "mp3_bitrate": self.mp3_bitrate_spin.value(),
            "bit_depth": bit_depth,
        }
