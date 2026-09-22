#!/usr/bin/env python3
"""Drives the real Edge Fade filter dialog and checks the linked/unlinked UI.

Uses Windows UI Automation, so it reads the widgets OBS actually created instead
of a model of them:

  1. finds the OBS window and opens the Filters dialog through its button
  2. reads the dialog: which rows were built and each slider's value
  3. toggles "Vincular" through the automation API
  4. re-reads the dialog and asserts the rows swapped
  5. drives the sliders and checks the resulting values

Usage:
    python tools/obs-ui-check.py [--dump] [--timeout 60]
"""

from __future__ import annotations

import argparse
import sys
import time

import comtypes.client  # type: ignore

UIA = comtypes.client.GetModule("UIAutomationCore.dll")
from comtypes.gen import UIAutomationClient as U  # noqa: E402

SIDE_LABELS = ("Izquierda", "Derecha", "Superior", "Inferior", "Left", "Right", "Top", "Bottom")
UNIFORM_LABELS = ("Todos", "Todos los bordes", "All borders")
LINK_LABELS = ("Vincular", "Link sides")
FIXED_LABELS = ("Suavidad", "Curva", "Smoothness", "Curve")


def automation():
    return comtypes.client.CreateObject(
        "{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=U.IUIAutomation
    )


class Report:
    def __init__(self) -> None:
        self.checks = 0
        self.failures: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        print(f"  {'ok  ' if condition else 'FAIL'} {message}")
        if not condition:
            self.failures.append(message)


class Ui:
    def __init__(self) -> None:
        self.auto = automation()

    def descendants(self, element, cap=6000):
        arr = element.FindAll(U.TreeScope_Descendants, self.auto.CreateTrueCondition())
        return [arr.GetElement(i) for i in range(min(arr.Length, cap))]

    def children(self, element):
        arr = element.FindAll(U.TreeScope_Children, self.auto.CreateTrueCondition())
        return [arr.GetElement(i) for i in range(arr.Length)]

    @staticmethod
    def label(element) -> str:
        try:
            return (element.CurrentName or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def ctype(element) -> int:
        try:
            return element.CurrentControlType
        except Exception:  # noqa: BLE001
            return 0

    def find(self, root, predicate):
        for element in self.descendants(root):
            if predicate(element):
                return element
        return None

    def find_by_label(self, root, labels, ctype=None):
        return self.find(
            root,
            lambda e: self.label(e) in labels and (ctype is None or self.ctype(e) == ctype),
        )

    def slider_value(self, element):
        try:
            pattern = element.GetCurrentPattern(U.UIA_RangeValuePatternId).QueryInterface(
                U.IUIAutomationRangeValuePattern
            )
            return int(round(pattern.CurrentValue))
        except Exception:  # noqa: BLE001
            return None

    def set_slider(self, element, value: int) -> bool:
        try:
            pattern = element.GetCurrentPattern(U.UIA_RangeValuePatternId).QueryInterface(
                U.IUIAutomationRangeValuePattern
            )
            pattern.SetValue(float(value))
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"    (could not set slider: {exc})")
            return False

    def toggle_state(self, element):
        try:
            pattern = element.GetCurrentPattern(U.UIA_TogglePatternId).QueryInterface(
                U.IUIAutomationTogglePattern
            )
            return pattern.CurrentToggleState == U.ToggleState_On
        except Exception:  # noqa: BLE001
            return None

    def toggle(self, element) -> bool:
        try:
            element.GetCurrentPattern(U.UIA_TogglePatternId).QueryInterface(
                U.IUIAutomationTogglePattern
            ).Toggle()
            return True
        except Exception:  # noqa: BLE001
            pass
        try:
            element.GetCurrentPattern(U.UIA_InvokePatternId).QueryInterface(
                U.IUIAutomationInvokePattern
            ).Invoke()
            return True
        except Exception:  # noqa: BLE001
            return False

    def invoke(self, element) -> bool:
        try:
            element.GetCurrentPattern(U.UIA_InvokePatternId).QueryInterface(
                U.IUIAutomationInvokePattern
            ).Invoke()
            return True
        except Exception:  # noqa: BLE001
            return False

    def rows(self, dialog):
        """(row label, slider element, value) for every slider in the dialog.

        OBS builds each row as a label followed by the slider, and rows whose
        property is not visible are never created at all.
        """
        out = []
        ordered = self.descendants(dialog)
        for index, element in enumerate(ordered):
            if self.ctype(element) != U.UIA_SliderControlTypeId:
                continue
            row_label = ""
            for back in range(index - 1, max(index - 6, -1), -1):
                text = self.label(ordered[back])
                if text and self.ctype(ordered[back]) != U.UIA_SliderControlTypeId:
                    row_label = text
                    break
            out.append((row_label, element, self.slider_value(element)))
        return out

    def summary(self, dialog) -> str:
        return ", ".join(f"{name or '?'}={value}" for name, _element, value in self.rows(dialog)) or "(none)"

    def labels(self, dialog) -> list[str]:
        out = []
        for element in self.descendants(dialog):
            text = self.label(element)
            if text and self.ctype(element) != U.UIA_SliderControlTypeId:
                out.append(text)
        return out


def wait_for(predicate, timeout: float, pause: float = 1.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(pause)
    return None


def find_link(ui, filters):
    """The 'Vincular' checkbox.

    OBS destroys and rebuilds every widget on each refresh, so the element has to
    be looked up again after any change instead of being cached.
    """
    return ui.find(
        filters,
        lambda e: ui.label(e) in LINK_LABELS and ui.ctype(e) == U.UIA_CheckBoxControlTypeId,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--settle", type=float, default=1.5)
    parser.add_argument("--dump", action="store_true")
    args = parser.parse_args()

    ui = Ui()
    report = Report()

    obs = ui.find_by_label(ui.auto.GetRootElement(), tuple(), None)
    obs = None
    for element in ui.children(ui.auto.GetRootElement()):
        if "OBS" in ui.label(element):
            obs = element
            break
    if obs is None:
        print("OBS window not found")
        return 1

    # The properties dialog is a child window of OBS, not a top level one.
    def find_dialogs():
        found = []
        for element in ui.descendants(obs):
            text = ui.label(element)
            if element is obs or not text:
                continue
            if ui.ctype(element) != U.UIA_WindowControlTypeId:
                continue
            if "Filtros" in text or "Filters" in text:
                found.append(element)
        return found

    dialogs = find_dialogs()
    if not dialogs:
        button = ui.find_by_label(obs, ("Filtros", "Filters"), U.UIA_ButtonControlTypeId)
        if button is None:
            print("'Filtros' button not found")
            return 1
        ui.invoke(button)
        dialogs = wait_for(find_dialogs, args.timeout) or []

    if not dialogs:
        print("Filters dialog did not open")
        if args.dump:
            for element in ui.descendants(obs, 200):
                text = ui.label(element)
                if text:
                    print(f"    {text!r} type={ui.ctype(element)}")
        return 1

    filters = dialogs[0]
    print(f"Filters dialog: {ui.label(filters)!r}")

    link = find_link(ui, filters)
    if link is None:
        print("'Vincular' checkbox not found")
        return 1
    print(f"link checkbox: {ui.label(link)!r} checked={ui.toggle_state(link)}")

    if args.dump:
        print("  --- labels ---")
        for text in ui.labels(filters):
            print(f"    {text!r}")

    # --- linked -------------------------------------------------------------
    link = find_link(ui, filters)
    if not ui.toggle_state(link):
        ui.toggle(link)
        time.sleep(args.settle)

    linked_rows = ui.rows(filters)
    print(f"linked   -> {ui.summary(filters)}")
    linked_labels = ui.labels(filters)
    report.check(
        any(text in UNIFORM_LABELS for text in linked_labels),
        "linked: the single 'all borders' row is present",
    )
    report.check(
        not any(text in SIDE_LABELS for text in linked_labels),
        "linked: the four per-side rows are hidden",
    )
    report.check(
        all(any(text == wanted for text in linked_labels) for wanted in ("Suavidad", "Curva")),
        "linked: Smoothness and Curve are still visible",
    )

    # --- move the global slider --------------------------------------------
    uniform_row = next((row for row in linked_rows if row[0] in UNIFORM_LABELS), None)
    if uniform_row is None and linked_rows:
        uniform_row = linked_rows[0]

    target = 170
    if uniform_row:
        ui.set_slider(uniform_row[1], target)
        time.sleep(args.settle)
        after = next(
            (row[2] for row in ui.rows(filters) if row[0] == uniform_row[0]),
            None,
        )
        report.check(after == target, f"linked: the global slider holds {target} (reads {after})")

    # --- unlinked -----------------------------------------------------------
    # The previous refresh destroyed the old widgets, so look the checkbox up
    # again instead of reusing the stale handle.
    link = find_link(ui, filters)
    print(f"  (toggling; state before = {ui.toggle_state(link)})")
    ok = ui.toggle(link)
    time.sleep(args.settle)
    print(f"  (toggle returned {ok})")
    unlinked_rows = ui.rows(filters)
    unlinked_labels = ui.labels(filters)
    print(f"unlinked -> {ui.summary(filters)}")
    report.check(
        all(any(text == wanted for text in unlinked_labels) for wanted in SIDE_LABELS[:4]),
        "unlinked: the four per-side rows are back",
    )
    report.check(
        not any(text in UNIFORM_LABELS for text in unlinked_labels),
        "unlinked: the single 'all borders' row is hidden",
    )
    report.check(
        all(any(text == wanted for text in unlinked_labels) for wanted in ("Suavidad", "Curva")),
        "unlinked: Smoothness and Curve are still visible",
    )

    side_rows = [row for row in unlinked_rows if row[0] in SIDE_LABELS]
    report.check(len(side_rows) == 4, f"unlinked: exactly four side sliders ({len(side_rows)} found)")
    if side_rows:
        values = [row[2] for row in side_rows]
        report.check(
            all(value == target for value in values),
            f"unlinked: sides kept the linked width {target} (values {values})",
        )

    # --- linked again -------------------------------------------------------
    link = find_link(ui, filters)
    ui.toggle(link)
    time.sleep(args.settle)
    relinked_labels = ui.labels(filters)
    print(f"relinked -> {ui.summary(filters)}")
    report.check(
        any(text in UNIFORM_LABELS for text in relinked_labels)
        and not any(text in SIDE_LABELS for text in relinked_labels),
        "re-linking swaps the rows back",
    )

    print()
    print(f"checks: {report.checks}  failures: {len(report.failures)}")
    for failure in report.failures:
        print(f"  FAIL {failure}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
