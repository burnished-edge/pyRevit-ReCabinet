# pyRevit ReCabinet

This pyRevit extension provides a "magic button" to evenly resize and distribute selected millwork over a chosen distance. It is designed to replace the clunky, time-consuming process of drawing construction lines, constraining them to EQ dimensions, and manually aligning the edges of millwork families. 

---

## Features

* **Fraction-Friendly & Equation Ready:** By tapping directly into Revit's internal `UnitFormatUtils`, the tool reads inputs exactly like the Revit Properties panel. It handles complex fractions (e.g., `4'-10 33/128"`) and even accepts mathematical equations right in the prompt (e.g., `=120/3`).
* **Elevation-Friendly Auto-Workplanes:** Using `PickPoint()` in elevation views traditionally crashes if no workplane is set. This tool automatically detects if a workplane is missing and generates a temporary, invisible mathematical plane aligned with your camera behind the scenes.
* **True Vector Projection:** To prevent cabinets from accidentally shifting forward or backward in plan view, the script calculates the existing, true centerline of your cabinets. Your clicks are projected onto this line, ignoring any accidental depth or vertical drift from your mouse.

---

## How to Use (Order of Operations)

1. **Click the Tool:** Launch the command from your pyRevit ribbon.
2. **Select Cabinets:** Select the millwork families you want to array. You can either click one them one at a time or drag a selection box to select.
3. **Enter Total Width:** A popup text box will prompt you for the overall dimension. You can use standard architectural units or formulas.
4. **Pick Justification:** A native Revit TaskDialog will ask you to select the family's internal insertion point (so the script knows how to offset the first cabinet). This will vary by family.
5. **Click Start Point:** Click the starting point in the model (the insertion point) on the canvas. 
6. **Click Direction:** Click a second point anywhere in the direction you want the cabinets to run. Imagine a vertical line drawn at the first point. The second point determines which side of that line your millwork will be arrayed.
7. **Review Results:** The script divides the total width by the number of cabinets, updates their parameters, shifts them flush, and provides a final popup message indicating success.

---

> **Note on Constraints:** This tool only works on millwork families with an instance-based Width parameter. If your cabinets are currently locked to existing EQ construction lines or alignments, the API constraint solver may get confused and collapse them into a single point. Make sure you delete any EQ dimensions or alignment locks on these specific cabinets before running the tool.
