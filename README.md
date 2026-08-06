# pyRevit Millwork Resizer

This pyRevit extension provides a "magic button" to evenly resize and distribute selected millwork over a chosen distance. It is designed to replace the clunky, time-consuming process of drawing construction lines, constraining them to EQ dimensions, and manually aligning the edges of millwork families. 

---

## Features

* **Fraction-Friendly & Equation Ready:** By tapping directly into Revit's internal `UnitFormatUtils`, the tool reads inputs exactly like the Revit Properties panel. It effortlessly handles complex fractions (e.g., `4'-10 33/128"`) and even accepts mathematical equations right in the prompt (e.g., `=120/3`).
* **Elevation-Friendly Auto-Workplanes:** Using `PickPoint()` in elevation views traditionally crashes if no workplane is set. This tool automatically detects if a workplane is missing and generates a temporary, invisible mathematical plane aligned with your camera behind the scenes.
* **True Vector Projection:** To prevent cabinets from accidentally shifting forward or backward in plan view, the script calculates the existing, true centerline of your cabinets. Your clicks are mathematically projected onto this line, completely ignoring any accidental depth or vertical drift from your mouse.
* **Thread-Safe UI:** Built specifically for IronPython 3. To completely eliminate window-focus lockups and thread crashing, this script bypasses WPF forms entirely. It utilizes synchronous Windows Forms (WinForms) for text input and native Revit TaskDialogs for selectors and popup messages.

---

## How to Use (Order of Operations)

The tool utilizes a strict pre-selection workflow to keep the Revit UI thread perfectly stable:

1. **Click the Tool:** Launch the command from your pyRevit ribbon.
2. **Select Cabinets:** The script uses the native `PickObjects` method to let you select the freestanding cabinets you want to array. 
3. **Enter Total Width:** A WinForms text box will prompt you for the overall dimension. You can use standard architectural units or formulas.
4. **Pick Justification:** A native Revit TaskDialog will ask you to select the family's internal insertion point (so the script knows how to offset the first cabinet).
5. **Click Start Point:** Click the starting point in the model (the insertion point) on the canvas. 
6. **Click Direction:** Click a second point anywhere in the direction you want the cabinets to run. 
7. **Review Results:** The script divides the total width by the number of cabinets, updates their parameters, shifts them flush, and provides a final popup message summarizing the results.

---

> **Note on Constraints:** If your cabinets are currently locked to existing EQ construction lines or alignments, the API constraint solver may get confused and collapse them into a single point. Make sure you delete any EQ dimensions or alignment locks on these specific cabinets before running the tool.
