#! ipy3
import traceback
import sys
import clr

# Load .NET assemblies for WinForms
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
from System.Windows.Forms import Form, TextBox, Button, Label, DialogResult, FormBorderStyle, FormStartPosition
from System.Drawing import Point, Size

from pyrevit import revit, script
from Autodesk.Revit import DB, UI
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException

doc = revit.doc
uidoc = revit.uidoc

# ==========================================
# UI HELPER FUNCTIONS (NO WPF)
# ==========================================
def show_alert(title, msg, exit_script=True):
    """Native Revit TaskDialog for alerts"""
    dialog = UI.TaskDialog(title)
    dialog.MainInstruction = msg
    dialog.Show()
    if exit_script:
        script.exit()

def ask_for_string_winforms(title, prompt, default_text=""):
    """Basic WinForms InputBox to replace pyRevit's WPF forms.ask_for_string"""
    form = Form()
    form.Text = title
    form.Width = 320
    form.Height = 160
    form.FormBorderStyle = FormBorderStyle.FixedDialog
    form.StartPosition = FormStartPosition.CenterScreen
    form.MaximizeBox = False
    form.MinimizeBox = False
    
    label = Label()
    label.Text = prompt
    label.Location = Point(10, 15)
    label.Width = 280
    
    text_box = TextBox()
    text_box.Text = default_text
    text_box.Location = Point(10, 40)
    text_box.Width = 280
    
    button_ok = Button()
    button_ok.Text = "OK"
    button_ok.Location = Point(120, 80)
    button_ok.DialogResult = DialogResult.OK
    
    button_cancel = Button()
    button_cancel.Text = "Cancel"
    button_cancel.Location = Point(210, 80)
    button_cancel.DialogResult = DialogResult.Cancel
    
    form.Controls.Add(label)
    form.Controls.Add(text_box)
    form.Controls.Add(button_ok)
    form.Controls.Add(button_cancel)
    form.AcceptButton = button_ok
    form.CancelButton = button_cancel
    
    result = form.ShowDialog()
    if result == DialogResult.OK:
        return text_box.Text
    return None

def ask_for_justification():
    """Native Revit TaskDialog to replace pyRevit's WPF forms.SelectFromList"""
    dialog = UI.TaskDialog("Family Justification")
    dialog.MainInstruction = "How is this family internally justified?"
    dialog.MainContent = "This tells the script how to offset the cabinets from your placement line."
    dialog.AddCommandLink(UI.TaskDialogCommandLinkId.CommandLink1, "Left Edge")
    dialog.AddCommandLink(UI.TaskDialogCommandLinkId.CommandLink2, "Center")
    dialog.AddCommandLink(UI.TaskDialogCommandLinkId.CommandLink3, "Right Edge")
    
    result = dialog.Show()
    if result == UI.TaskDialogResult.CommandLink1:
        return "Left Edge"
    elif result == UI.TaskDialogResult.CommandLink2:
        return "Center"
    elif result == UI.TaskDialogResult.CommandLink3:
        return "Right Edge"
    return None


# ==========================================
# CORE LOGIC
# ==========================================
class CabinetFilter(ISelectionFilter):
    def AllowElement(self, elem):
        if isinstance(elem, DB.FamilyInstance) and isinstance(elem.Location, DB.LocationPoint):
            return True
        return False
    def AllowReference(self, ref, pt):
        return False

def parse_to_decimal_feet(input_str, current_doc):
    try:
        success, parsed_val = DB.UnitFormatUtils.TryParse(current_doc.GetUnits(), DB.SpecTypeId.Length, input_str)
    except AttributeError:
        success, parsed_val = DB.UnitFormatUtils.TryParse(current_doc.GetUnits(), DB.UnitType.UT_Length, input_str)
    if success:
        return parsed_val
    return None

try:
    # 1. CANVAS: Select Cabinets
    references = uidoc.Selection.PickObjects(
        ObjectType.Element, 
        CabinetFilter(), 
        "1/3: Select cabinets, then click 'Finish' in the Options Bar."
    )
    
    if not references or len(references) < 2:
        show_alert("Selection Error", "Please select at least two cabinets to distribute.")
        
    cabinets = [doc.GetElement(ref.ElementId) for ref in references]
    uidoc.RefreshActiveView()
    
    # 2. WORKPLANE FIX
    active_view = doc.ActiveView
    if active_view.SketchPlane is None:
        with revit.Transaction("Set Temporary Workplane"):
            try:
                plane = DB.Plane.CreateByNormalAndOrigin(active_view.ViewDirection, active_view.Origin)
                sketch_plane = DB.SketchPlane.Create(doc, plane)
                active_view.SketchPlane = sketch_plane
            except Exception as e:
                show_alert("Workplane Error", "Could not automatically set a workplane for this view. Please set one manually.")

    # 3. CANVAS: Array Points
    pt_start = uidoc.Selection.PickPoint("2/3: Click STARTING placement point.")
    pt_dir = uidoc.Selection.PickPoint("3/3: Click SECOND point for direction.")
    
    # 4. UI: Width Prompt (WinForms)
    total_width_str = ask_for_string_winforms(
        "Distribute Cabinets", 
        "Enter total run width:", 
        "10' 0\""
    )
    
    if not total_width_str:
        script.exit()
        
    total_width_ft = parse_to_decimal_feet(total_width_str, doc)
    
    if total_width_ft is None:
        show_alert("Format Error", "Revit could not understand that dimension format. Please try again.")
        
    # 5. UI: Justification Prompt (TaskDialog)
    selected_insertion = ask_for_justification()
    if not selected_insertion:
        script.exit()

    # 6. CALCULATION: Vector Projection
    c_pts = [cab.Location.Point for cab in cabinets]
    spread_x = max(p.X for p in c_pts) - min(p.X for p in c_pts)
    spread_y = max(p.Y for p in c_pts) - min(p.Y for p in c_pts)
    spread_z = max(p.Z for p in c_pts) - min(p.Z for p in c_pts)

    if spread_x >= spread_y and spread_x >= spread_z:
        cabinets.sort(key=lambda c: c.Location.Point.X)
    elif spread_y >= spread_x and spread_y >= spread_z:
        cabinets.sort(key=lambda c: c.Location.Point.Y)
    else:
        cabinets.sort(key=lambda c: c.Location.Point.Z)

    c_first = cabinets[0].Location.Point
    c_last = cabinets[-1].Location.Point

    if c_first.DistanceTo(c_last) > 0.01:
        cab_line_dir = c_last.Subtract(c_first).Normalize()
    else:
        cab_line_dir = DB.XYZ(1, 0, 0)

    v_start = pt_start.Subtract(c_first)
    dist_start = v_start.DotProduct(cab_line_dir)
    anchor_pt = c_first.Add(cab_line_dir.Multiply(dist_start))

    v_dir = pt_dir.Subtract(anchor_pt)
    dist_dir = v_dir.DotProduct(cab_line_dir)

    if dist_dir >= 0:
        direction = cab_line_dir
    else:
        direction = cab_line_dir.Multiply(-1)

    num_cabinets = len(cabinets)
    new_width_ft = total_width_ft / num_cabinets

    # 7. EXECUTION
    with revit.Transaction("Distribute Cabinet Widths"):
        missing_param_count = 0
        for i, cab in enumerate(cabinets):
            width_param = cab.LookupParameter("Width")
            if width_param and not width_param.IsReadOnly:
                width_param.Set(new_width_ft)
            else:
                missing_param_count += 1
                
            doc.Regenerate()
            step_offset = direction.Multiply(i * new_width_ft)
            
            if selected_insertion == "Left Edge":
                new_pos = anchor_pt.Add(step_offset)
            elif selected_insertion == "Center":
                half_width_offset = direction.Multiply(new_width_ft / 2.0)
                new_pos = anchor_pt.Add(half_width_offset).Add(step_offset)
            elif selected_insertion == "Right Edge":
                full_width_offset = direction.Multiply(new_width_ft)
                new_pos = anchor_pt.Add(full_width_offset).Add(step_offset)
                
            current_pos = cab.Location.Point
            translation_vec = new_pos.Subtract(current_pos)
            
            DB.ElementTransformUtils.MoveElement(doc, cab.Id, translation_vec)
            doc.Regenerate()

    # 8. REPORT (TaskDialog popup instead of console print)
    try:
        formatted_result = DB.UnitFormatUtils.Format(doc.GetUnits(), DB.SpecTypeId.Length, new_width_ft, False)
    except AttributeError:
        formatted_result = DB.UnitFormatUtils.Format(doc.GetUnits(), DB.UnitType.UT_Length, new_width_ft, False, False)
        
    if missing_param_count > 0:
        msg = "Warning: {} cabinets did not have an editable 'Width' parameter.\n\nAdjusted the remaining cabinets to {}.".format(missing_param_count, formatted_result)
        show_alert("Partial Success", msg, exit_script=False)
    else:
        msg = "Successfully laid out {} cabinets.\nNew individual width: {}".format(num_cabinets, formatted_result)
        show_alert("Success", msg, exit_script=False)

except OperationCanceledException:
    pass
except Exception as e:
    error_msg = traceback.format_exc()
    show_alert("Script Error", "An error occurred:\n\n{}".format(error_msg))