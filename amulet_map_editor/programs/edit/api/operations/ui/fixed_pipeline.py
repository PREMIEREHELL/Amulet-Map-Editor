import wx
from typing import Callable, Dict, Any, TYPE_CHECKING, Sequence
import logging
import inspect
from amulet_map_editor.api.opengl.camera import Projection
from amulet_map_editor.programs.edit.api.behaviour import (
    BlockSelectionBehaviour,
    StaticSelectionBehaviour,
)
from amulet.api.selection import SelectionGroup
from amulet.api.selection import SelectionBox
from amulet_map_editor.programs.edit.api.events import (
    EVT_SELECTION_CHANGE,
)
from amulet_map_editor.api.wx.util.validators import IntValidator

from amulet.api.data_types import OperationReturnType
from amulet_map_editor.programs.edit.api.operations import DefaultOperationUI

if TYPE_CHECKING:
    from amulet_map_editor.programs.edit.api.canvas import EditCanvas
    from amulet.api.level import BaseLevel

log = logging.getLogger(__name__)

FixedOperationType = Callable[
    ["BaseLevel", "Dimension", "SelectionGroup", Dict[str, Any]], OperationReturnType
]


class FixedFunctionUI(wx.Panel, DefaultOperationUI):
    def __init__(
        self,
        parent: wx.Window,
        canvas: "EditCanvas",
        world: "BaseLevel",
        options_path: str,
        operation: FixedOperationType,
        options: Dict[str, Any],
    ):
        wx.Panel.__init__(self, parent)
        DefaultOperationUI.__init__(self, parent, canvas, world, options_path)
        self._operation = operation
        self.Hide()
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)
        self._options_sizer = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self._options_sizer)
        self._run_button = wx.Button(self, label="Run Operation")
        self._run_button.Bind(wx.EVT_BUTTON, self._run_operation)
        self._sizer.Add(self._run_button, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)
        self.selectionenabled = False
        self._options: Dict[str, wx.Window] = {}
        self._create_options(options)
        self.Layout()
        self.Show()

    def bind_events(self):
        if self.selectionenabled:
            super().bind_events()
            self._selection.bind_events()
            self._selection.enable()

    def enable(self):
        if self.selectionenabled:
            self.canvas.camera.projection_mode = Projection.PERSPECTIVE
            self._selection = BlockSelectionBehaviour(self.canvas)
            self._selection.enable()

    def _create_options(self, options: Dict[str, Sequence]):
        create_functions: Dict[str, Callable[[str, Sequence], None]] = {
            "label": self._create_label,
            "bool": self._create_bool,
            "int": self._create_int,
            "float": self._create_float,
            "str": self._create_string,
            "str_choice": self._create_str_choice,
            "file_open": self._create_file_open_picker,
            "file_save": self._create_file_save_picker,
            "directory": self._create_directory_picker,
            "button": self._create_button,
            "checklistbox": self._create_checklistbox,
            "selection_behaviour": None,
        }

        for option_name, args in options.items():
            try:
                option_type, *args = args
                if option_type not in create_functions:
                    raise ValueError(f"Invalid option type {option_type}")
                if option_type == "selection_behaviour":
                    self.selectionenabled = True
                else:
                    create_functions[option_type](option_name, *args)
            except Exception as e:
                log.exception(e)

    def _create_label(self, option_name: str):
        label = wx.StaticText(self, label=option_name)
        self._options_sizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

    def _create_horizontal_options_sizer(self, label) -> wx.BoxSizer:
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, label=label)
        sizer.Add(label, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        self._options_sizer.Add(sizer, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)
        return sizer

    def _create_bool(self, option_name: str, value: bool = False):
        if not isinstance(value, bool):
            raise TypeError("value must be a bool")
        sizer = self._create_horizontal_options_sizer(option_name)
        option = wx.CheckBox(self)
        sizer.Add(option)
        option.SetValue(value)
        self._options[option_name] = option

    def _create_int(
        self, option_name: str, initial=0, min_val=-30_000_000, max_val=30_000_000
    ):
        if not (
            isinstance(initial, int)
            and isinstance(min_val, int)
            and isinstance(max_val, int)
        ):
            raise TypeError("Input value must be int")
        sizer = self._create_horizontal_options_sizer(option_name)
        option = wx.SpinCtrl(
            self,
            min=min(min_val, max_val),
            max=max(min_val, max_val),
            initial=initial,
        )
        option.SetValidator(IntValidator())
        sizer.Add(option)
        self._options[option_name] = option

    def _create_float(
        self, option_name: str, initial=0, min_val=-30_000_000, max_val=30_000_000
    ):
        if not (
            isinstance(initial, (int, float))
            and isinstance(min_val, (int, float))
            and isinstance(max_val, (int, float))
        ):
            raise TypeError("Input value must be int or float")
        sizer = self._create_horizontal_options_sizer(option_name)
        option = wx.SpinCtrlDouble(
            self,
            min=min(min_val, max_val),
            max=max(min_val, max_val),
            initial=initial,
        )
        sizer.Add(option)
        self._options[option_name] = option

    def _create_string(self, option_name: str, value: str = ""):
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        sizer = self._create_horizontal_options_sizer(option_name)
        option = wx.TextCtrl(self)
        sizer.Add(option)
        option.SetValue(value)
        self._options[option_name] = option

    def _create_str_choice(self, option_name: str, *choices: str):
        if not (choices and all(isinstance(o, str) for o in choices)):
            return
        sizer = self._create_horizontal_options_sizer(option_name)
        option = wx.Choice(self, choices=choices)
        option.SetSelection(0)
        sizer.Add(option)
        self._options[option_name] = option

    def _create_file_picker(self, option_name: str, path: str, mode):
        if not isinstance(path, str):
            raise TypeError("path must be a string")
        sizer = self._create_horizontal_options_sizer(option_name)
        option = wx.FilePickerCtrl(self, path=path, style=mode | wx.FLP_USE_TEXTCTRL)
        sizer.Add(option)
        self._options[option_name] = option

    def _create_file_save_picker(self, option_name: str, path: str = ""):
        self._create_file_picker(option_name, path, wx.FLP_SAVE)

    def _create_file_open_picker(self, option_name: str, path: str = ""):
        self._create_file_picker(option_name, path, wx.FLP_OPEN)

    def _create_directory_picker(self, option_name: str, path: str = ""):
        if not isinstance(path, str):
            raise TypeError("path must be a string")
        sizer = self._create_horizontal_options_sizer(option_name)
        option = wx.DirPickerCtrl(self, path=path, style=wx.DIRP_USE_TEXTCTRL)
        sizer.Add(option)
        self._options[option_name] = option

    def _create_button(
        self,
        option_name: str,
        button_name: str = "",
        callback: Callable[[], Any] = lambda: None,
    ):
        if not isinstance(button_name, str):
            raise TypeError("button_name must be a string")
        if inspect.signature(callback).parameters:
            raise TypeError("callback does not take any arguments")
        button = wx.Button(self, wx.ID_ANY, button_name)
        button.Bind(wx.EVT_BUTTON, lambda evt: callback())
        sizer = self._create_horizontal_options_sizer(option_name)
        sizer.Add(button)

    def _create_checklistbox(self, option_name: str, items: list, all_checked=False):
        self.items = items
        listbox = wx.CheckListBox(self, choices=self.items, name=option_name)
        sizer = self._create_horizontal_options_sizer(option_name)
        sizer.Add(listbox, 2, wx.ALIGN_CENTER | wx.TOP, 2)
        if all_checked:
            for i in range(listbox.GetCount()):
                listbox.Check(i, True)
        self._options[option_name] = listbox

    def _get_values(self) -> Dict[str, Any]:
        options = {}
        for key, window in self._options.items():
            if isinstance(
                window,
                (
                    wx.CheckBox,
                    wx.SpinCtrl,
                    wx.SpinCtrlDouble,
                    wx.TextCtrl,
                ),
            ):
                options[key] = window.GetValue()
            elif isinstance(window, wx.Choice):
                options[key] = window.GetString(window.GetSelection())
            elif isinstance(window, (wx.FilePickerCtrl, wx.DirPickerCtrl)):
                options[key] = window.GetPath()
            elif isinstance(window, wx.CheckListBox):
                options[key] = [window.GetString(x) for x in window.GetCheckedItems()]
        return options

    def _run_operation(self, evt):
        self.canvas.run_operation(
            lambda: self._operation(
                self.world,
                self.canvas.dimension,
                self.canvas.selection.selection_group,
                self._get_values(),
            )
        )
