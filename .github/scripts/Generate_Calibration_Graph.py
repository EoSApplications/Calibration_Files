"""
Builds Calibration_Graph.json - a single static, read-only snapshot of the
calibration network for the website's EoSHolo page.

This is a CI-adapted copy of Development/Website_Files/Build/Build_Calibration_Graph.py.
The only differences from that script: the EoSAlign code directory and the output
path are passed in as CLI arguments (pointing at fresh checkouts in the runner's
workspace) instead of being resolved relative to the Development monorepo. The
actual graph-building logic (Build_Calibration_Graph, Build_Calibration_Info, and
their helpers) is unchanged - keep the two in sync if either is edited.

The logic mirrors EoSHolo.py's Initialize_Data() method: same nodes (one per
calibration, plus synthetic "special"/"missing parent" nodes) and the same
parent-matching rules. Node layout/positioning and all interaction live in JS
(Website_Files/Assets/js/EoSHolo.js); this script only builds the data.

Usage:
    python3 Generate_Calibration_Graph.py --eosalign-code EoSAlign/Code --output Website/data/Calibration_Graph.json
"""

import argparse
import json
import sys
from pathlib import Path

Parser = argparse.ArgumentParser()
Parser.add_argument('--eosalign-code', required=True, help="Path to EoSAlign's checked-out Code/ folder")
Parser.add_argument('--output', required=True, help='Path to write Calibration_Graph.json to')
Args = Parser.parse_args()

sys.path.insert(0, str(Path(Args.eosalign_code).resolve()))

# Force canonical-only data: without this, the loader would also look for
# User_Edited/User_Entered YAML files under a local app-data folder - irrelevant
# in a fresh CI runner, but kept for parity with the desktop app's own loading path
from EoS_Math.Build_Dataframe import Set_Calibration_File_Settings  # noqa: E402

Set_Calibration_File_Settings(False, False)

from EoS_Math.Build_Dataframe import Calibration_List, Calibration_Metadata  # noqa: E402
from Reference_Values_And_Units import (  # noqa: E402
    Material_Information, Calibration_File_Variable_Information, Calibration_Field_Sections,
    Equation_Entry_From_Calibration_Entry, Function_Information,
)

# These are pure functions/data (no Qt instantiation happens just by importing
# them) - reused as-is from the desktop calibration viewer so the website's
# "Preview Calibrant" view never drifts out of sync with how the app itself
# labels, sections, and filters these fields.
from View_Edit_And_Save_Calibration_Files_In_A_New_Window import (  # noqa: E402
    Check_If_Method_Matches, Find_Method_Index, Get_Value_For_Method,
    Build_Best_Label_Html, Convert_Value_To_Display_Text,
    Get_V0_Display_Information, Find_Active_V0_Entry_Key, Get_Primary_V0_Calibration_Key,
    Check_If_Text_Is_A_Valid_Doi, Convert_Doi_Text_To_Url,
    Typo_Fallbacks, Hidden_Entry_Keys, Reference_Fields_List,
    Equation_Required_Entry_Keys, Unit_Label_Fields,
)

OUTPUT_PATH = Path(Args.output)


def _Get_Calibration_Value(Calibration_Data, Field_Meta):
    Calibration_Keys = Field_Meta.get('Calibration_File_Variable_Name', '')
    if isinstance(Calibration_Keys, str):
        Calibration_Keys = [Calibration_Keys]
    for Calibration_Key in Calibration_Keys:
        if Calibration_Key in Calibration_Data:
            return Calibration_Data[Calibration_Key]
        for Alt in Typo_Fallbacks.get(Calibration_Key, []):
            if Alt in Calibration_Data:
                return Calibration_Data[Alt]
    return None


def _Get_Required_Entry_Keys_For_Equation(Eos, Order):
    Order_Str = str(Order) if Order not in (None, '') else None
    Display_Name = Equation_Entry_From_Calibration_Entry.get((Eos, Order_Str))
    if Display_Name is None and Order_Str is not None:
        Display_Name = Equation_Entry_From_Calibration_Entry.get((Eos, None))
    if Display_Name is None:
        return None
    return Equation_Required_Entry_Keys.get(Display_Name)


def _Build_Doi_Lines(Display_Text):
    Lines = [Line.strip() for Line in Display_Text.splitlines() if Line.strip()]
    return [
        {'text': Line, 'url': Convert_Doi_Text_To_Url(Line) if Check_If_Text_Is_A_Valid_Doi(Line) else ''}
        for Line in Lines
    ]


def Build_Calibration_Info(Calibration_Data):
    """Read-only "view mode" rendering of one calibration's raw YAML dict —
    mirrors Load_Form_From_File -> Populate_Fields -> Apply_View_Visibility
    (Is_Editing=False) in View_Edit_And_Save_Calibration_Files_In_A_New_Window.py:
    same sections/labels/units, fields hidden when blank, Equation Variables
    filtered to the ones the matched equation actually uses, V0 displayed
    using whichever variant is active in the file, DOI rendered as a link.
    """

    Method = str(Calibration_Data.get('method', '') or '')
    Eos = str(Calibration_Data.get('eos', '') or '')
    Order_Raw = Calibration_Data.get('order')
    Required_Keys = _Get_Required_Entry_Keys_For_Equation(Eos, Order_Raw)

    Order_Str = str(Order_Raw) if Order_Raw not in (None, '') else None
    Equation_Display_Name = Equation_Entry_From_Calibration_Entry.get((Eos, Order_Str))
    if Equation_Display_Name is None and Order_Str is not None:
        Equation_Display_Name = Equation_Entry_From_Calibration_Entry.get((Eos, None))

    Active_V0_Entry_Key = Find_Active_V0_Entry_Key(Calibration_Data, Method)

    Sections = []
    for Section_Name, Entry_Keys in Calibration_Field_Sections.items():
        if Section_Name == 'Pressure Calibration Reference':
            continue

        Rows = []
        for Entry_Key in Entry_Keys:
            if Entry_Key in Hidden_Entry_Keys:
                continue
            Field_Meta = Calibration_File_Variable_Information.get(Entry_Key)
            if Field_Meta is None:
                continue
            if not Check_If_Method_Matches(Field_Meta, Method):
                continue
            Midx = Find_Method_Index(Field_Meta, Method)

            Is_Doi = (Entry_Key == 'DOI')
            Is_Equation = (Entry_Key == 'Full Equation')
            Unit_Text = Unit_Label_Fields.get(Entry_Key, '')

            if Entry_Key == 'V0':
                V0_Display_Information = Get_V0_Display_Information(Active_V0_Entry_Key, Method)
                Label_Html = V0_Display_Information['Symbol_Html']
                Unit_Text = V0_Display_Information['Unit_Text']
                if Active_V0_Entry_Key == 'V0':
                    Raw_Value = None
                    for Generic_Key in ('V0', 'lambda_0', 'nu_0', 'nu0'):
                        if Generic_Key in Calibration_Data and str(Calibration_Data.get(Generic_Key, '') or '').strip():
                            Raw_Value = Calibration_Data.get(Generic_Key)
                            break
                else:
                    Raw_Value = Calibration_Data.get(Get_Primary_V0_Calibration_Key(Active_V0_Entry_Key, Method))
            elif Entry_Key == 'Composition':
                Comp_Key = str(Calibration_Data.get('composition', '') or '')
                Raw_Value = Material_Information.get(Comp_Key, {}).get('Display_Label', Comp_Key)
                Label_Html = Build_Best_Label_Html(Field_Meta, Midx)
            elif Entry_Key == 'Equation of State':
                Raw_Value = Equation_Display_Name or ''
                Label_Html = Build_Best_Label_Html(Field_Meta, Midx)
            elif Entry_Key == 'Full Equation':
                # The dialog's Sync_Full_Equation_From_Eos always overwrites this
                # field with the canonical equation for the matched EoS, regardless
                # of whatever raw text is in the YAML's own equation_full key.
                Raw_Value = Function_Information.get(Equation_Display_Name, {}).get('Latex_Equation', '') \
                    if Equation_Display_Name else ''
                Label_Html = Build_Best_Label_Html(Field_Meta, Midx)
            elif Entry_Key == 'Catagory':
                Cat_Val = str(Calibration_Data.get('category', '') or '').strip()
                Raw_Value = Cat_Val if Cat_Val in ('1', '2', '3') else ''
                Label_Html = Build_Best_Label_Html(Field_Meta, Midx)
            elif Entry_Key == 'Is The Initial Bulk Modulus Fixed?':
                Raw_K0 = Calibration_Data.get('is_K0_fixed', Calibration_Data.get('is_k0_fixed'))
                if isinstance(Raw_K0, bool):
                    Raw_Value = 'yes' if Raw_K0 else 'no'
                else:
                    Val = str(Raw_K0).strip().lower() if Raw_K0 is not None else ''
                    Raw_Value = Val if Val in ('yes', 'no') else ''
                Label_Html = Build_Best_Label_Html(Field_Meta, Midx)
            else:
                Raw_Value = _Get_Calibration_Value(Calibration_Data, Field_Meta)
                Label_Html = Build_Best_Label_Html(Field_Meta, Midx)

            Display_Text = Convert_Value_To_Display_Text(Raw_Value)
            Has_Value = bool(Display_Text.strip())

            Is_Equation_Variable = Entry_Key in Calibration_Field_Sections['Equation Variables']
            if Is_Equation_Variable:
                if Entry_Key.endswith(' Uncertainty'):
                    Base_Key = Entry_Key[: -len(' Uncertainty')]
                    Unc_Methods = Field_Meta.get('Method', [])
                    if isinstance(Unc_Methods, str):
                        Unc_Methods = [Unc_Methods]
                    Method_Compatible = (not Method) or (not Unc_Methods) or (Method in Unc_Methods)
                    Visible = Has_Value and Method_Compatible and (
                        Required_Keys is None or Base_Key in Required_Keys
                    )
                else:
                    Visible = Has_Value and (Required_Keys is None or Entry_Key in Required_Keys)
            else:
                Visible = Has_Value

            if not Visible:
                continue

            Row = {'label_html': Label_Html, 'value': Display_Text}
            if Unit_Text:
                Row['unit'] = Unit_Text
            if Is_Doi:
                Row['doi_lines'] = _Build_Doi_Lines(Display_Text)
            if Is_Equation:
                Row['is_equation'] = True
            Rows.append(Row)

        if Rows:
            Sections.append({'name': Section_Name, 'rows': Rows})

    Reference_Rows = []
    Split_Data = {}
    Max_Count = 0
    for Calibration_Key, _Label in Reference_Fields_List:
        Value = Calibration_Data.get(Calibration_Key)
        if Value is not None and str(Value).strip():
            Parts = [Part.strip() for Part in str(Value).split(';')]
            Split_Data[Calibration_Key] = Parts
            Max_Count = max(Max_Count, len(Parts))

    for Index in range(Max_Count):
        Fields = []
        for Calibration_Key, Field_Label in Reference_Fields_List:
            Parts = Split_Data.get(Calibration_Key, [])
            Value = Parts[Index] if Index < len(Parts) else ''
            if Value:
                Fields.append({'label': Field_Label, 'value': Value})
        if Fields:
            Reference_Rows.append({'title': f'Reference {Index + 1}', 'fields': Fields})

    return {'sections': Sections, 'references': Reference_Rows}


def Build_Calibration_Graph():
    Parsed_Calibrations = []
    Seen_Combinations    = {}
    All_Nodes            = {}
    Special_Node_Prefix  = "__EoSHolo::special::"
    Missing_Node_Prefix  = "__EoSHolo::missing_parent::"

    for Label, Raw_Calibration_Data in Calibration_List:
        Metadata     = Calibration_Metadata[Label]
        Study_Name   = Metadata['Study']
        Composition  = Metadata['Composition']
        EoS          = Metadata['Equation of State']
        Order        = Metadata['Order']
        Cal_To_Name  = Metadata.get('Reference Study', '')
        PTM          = Metadata.get('Pressure Transmitting Medium', '')
        Max_Pressure = Metadata['Maximum Pressure']
        Is_K0_Fixed  = Metadata.get('Is The Initial Bulk Modulus Fixed?', '')
        Method       = Metadata.get('Method', '')

        Display_Label = (
            f"{Study_Name} | {Composition} | {Method} | {EoS} | "
            f"K0 Fixed: {Is_K0_Fixed} | cal_to: {Cal_To_Name} | "
            f"Max Pressure: {Max_Pressure} GPa | PTM: {PTM}"
        ).replace("\n", "").strip()

        Node_Key = Label
        if Node_Key in Seen_Combinations:
            print("ERROR: Duplicate calibration found!")
            continue
        Seen_Combinations[Node_Key] = Label

        Entry = {
            'study':          Study_Name,
            'composition':    Composition,
            'eos':            EoS,
            'order':          Order,
            'max_pressure':   Max_Pressure,
            'is_K0_fixed':    Is_K0_Fixed,
            'method':         Method,
            'parent_info': {
                'cal_to_name':         Metadata.get('Reference Study', ''),
                'cal_to_composition':  Metadata.get('Reference Composition', ''),
                'cal_to_eos':          Metadata.get('Reference Equation of State', ''),
                'cal_to_order':        Metadata.get('Reference Equation of State Order', None),
                'cal_to_max_pressure': Metadata.get('Reference Maximum Pressure', None),
                'cal_to_is_K0_fixed':  Metadata.get('Reference Initial Bulk Modulus Fixed?', None),
                'cal_to_method':       Metadata.get('Reference Method', None),
                'cal_to_cal':          Metadata.get("Reference's Reference", ''),
            },
            'parent_node_ids': [],
            'label':           Label,
            'display_label':   Display_Label,
            'info':            Build_Calibration_Info(Raw_Calibration_Data),
            'node_id':         Node_Key,
            'has_calibration':        True,
            'is_special':      False,
        }

        Parsed_Calibrations.append(Entry)
        All_Nodes[Node_Key] = Entry

    Missing_Parents = {}
    Special_Nodes   = {}

    def _norm_text(value):
        if value is None:
            return ''
        text = str(value).strip()
        if text.lower() in ('not specified', 'not specfied', 'none', 'null'):
            return ''
        return text

    def _norm_ci(value):
        return _norm_text(value).lower()

    def _parse_int_or_none(value):
        text = _norm_text(value)
        if not text:
            return None
        try:
            return int(text)
        except Exception:
            return None

    def _parse_float_or_none(value):
        text = _norm_text(value)
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None

    def _norm_k0_flag(value):
        text = _norm_ci(value)
        if not text:
            return None
        if text in ('true', 'yes', 'y', '1'):
            return True
        if text in ('false', 'no', 'n', '0'):
            return False
        return text

    def _find_parent_node_ids(parent_study, parent_comp, parent_method, parent_eos, parent_order, parent_max_p, parent_k0):
        study_ci = _norm_ci(parent_study)
        if not study_ci:
            return []

        comp_ci = _norm_ci(parent_comp)
        method_ci = _norm_ci(parent_method)
        eos_ci = _norm_ci(parent_eos)
        order_v = _parse_int_or_none(parent_order)
        max_p_v = _parse_float_or_none(parent_max_p)
        k0_v = _norm_k0_flag(parent_k0)

        candidates = []
        for nid, node in All_Nodes.items():
            if _norm_ci(node.get('study', '')) != study_ci:
                continue
            if comp_ci and _norm_ci(node.get('composition', '')) != comp_ci:
                continue
            if method_ci and _norm_ci(node.get('method', '')) != method_ci:
                continue
            if eos_ci and _norm_ci(node.get('eos', '')) != eos_ci:
                continue
            if order_v is not None:
                node_order_v = _parse_int_or_none(node.get('order'))
                if node_order_v != order_v:
                    continue

            score = 0
            if max_p_v is not None:
                node_max_p_v = _parse_float_or_none(node.get('max_pressure'))
                if node_max_p_v is not None and abs(node_max_p_v - max_p_v) < 1e-9:
                    score += 2
            if k0_v is not None:
                node_k0_v = _norm_k0_flag(node.get('is_K0_fixed'))
                if node_k0_v == k0_v:
                    score += 1

            candidates.append((score, nid))

        candidates.sort(key=lambda pair: (-pair[0], pair[1]))
        return [nid for _, nid in candidates]

    for Entry in Parsed_Calibrations:
        Parent_Info  = Entry.get('parent_info', {})
        Cal_To_Name  = Parent_Info.get('cal_to_name', '')
        if not Cal_To_Name:
            continue

        Parent_Studies      = [P.strip() for P in Cal_To_Name.split(';')]
        Parent_Compositions = [P.strip() for P in (Parent_Info.get('cal_to_composition', '') or '').split(';')] if Parent_Info.get('cal_to_composition') else []
        Parent_EoSs         = [P.strip() for P in (Parent_Info.get('cal_to_eos', '')          or '').split(';')] if Parent_Info.get('cal_to_eos')         else []
        Parent_Orders       = [P.strip() for P in str(Parent_Info.get('cal_to_order', '')      or '').split(';')] if Parent_Info.get('cal_to_order')       else []
        Parent_Max_Ps       = [P.strip() for P in str(Parent_Info.get('cal_to_max_pressure', '') or '').split(';')] if Parent_Info.get('cal_to_max_pressure') else []
        Parent_K0s          = [P.strip() for P in str(Parent_Info.get('cal_to_is_K0_fixed', '') or '').split(';')] if Parent_Info.get('cal_to_is_K0_fixed') else []
        Parent_Methods      = [P.strip() for P in (Parent_Info.get('cal_to_method', '')        or '').split(';')] if Parent_Info.get('cal_to_method')      else []

        for lst in [Parent_Compositions, Parent_EoSs, Parent_Orders, Parent_Max_Ps, Parent_K0s, Parent_Methods]:
            if not lst:
                lst.append('')

        for P_Idx, P_Study in enumerate(Parent_Studies):
            P_Study_Norm = P_Study.strip().lower()

            if 'not specif' in P_Study_Norm:
                Comp = Parent_Compositions[min(P_Idx, len(Parent_Compositions) - 1)] if Parent_Compositions else ''
                if not Comp or 'not specif' in Comp.lower():
                    Comp = 'Not Specified'
                Sp_Key = f"{Special_Node_Prefix}not_specified::{Comp}"
                if Sp_Key not in Special_Nodes:
                    Sp_Node = {
                        'study': 'Not Specified', 'composition': Comp,
                        'eos': '', 'order': None, 'max_pressure': None,
                        'is_K0_fixed': None, 'method': '',
                        'parent_info': {'cal_to_name': ''},
                        'parent_node_ids': [], 'label': "Not Specified",
                        'display_label': "Not Specified",
                        'node_id': Sp_Key,
                        'has_calibration': False, 'is_special': True, 'special_type': 'not_specified',
                    }
                    Special_Nodes[Sp_Key] = Sp_Node
                    All_Nodes[Sp_Key]     = Sp_Node
                    Parsed_Calibrations.append(Sp_Node)
                Entry['parent_node_ids'].append(Sp_Key)
                continue

            if P_Study_Norm == 'absolute':
                Study  = Entry['study']
                Comp   = Entry['composition']
                Sp_Key = f"{Special_Node_Prefix}absolute::{Study}::{Comp}"
                if Sp_Key not in Special_Nodes:
                    Sp_Node = {
                        'study': Study, 'composition': Comp,
                        'eos': '', 'order': None, 'max_pressure': None,
                        'is_K0_fixed': None, 'method': '',
                        'parent_info': {'cal_to_name': ''},
                        'parent_node_ids': [], 'label': f"{Study} (Absolute)",
                        'display_label': f"{Study} (Absolute)",
                        'node_id': Sp_Key,
                        'has_calibration': False, 'is_special': True, 'special_type': 'absolute',
                    }
                    Special_Nodes[Sp_Key] = Sp_Node
                    All_Nodes[Sp_Key]     = Sp_Node
                    Parsed_Calibrations.append(Sp_Node)
                Entry['parent_node_ids'].append(Sp_Key)
                continue

            Sub = P_Study.strip()
            if not Sub or len(Sub) < 3:
                continue
            if '(' in Sub or ')' in Sub or ':' in Sub:
                continue

            P_Comp   = Parent_Compositions[min(P_Idx, len(Parent_Compositions) - 1)]
            P_EoS    = Parent_EoSs[min(P_Idx, len(Parent_EoSs) - 1)]
            P_Order  = Parent_Orders[min(P_Idx, len(Parent_Orders) - 1)]
            P_Max_P  = Parent_Max_Ps[min(P_Idx, len(Parent_Max_Ps) - 1)]
            P_K0     = Parent_K0s[min(P_Idx, len(Parent_K0s) - 1)]
            P_Method = Parent_Methods[min(P_Idx, len(Parent_Methods) - 1)]

            Sub_Comps = [sc.strip() for sc in P_Comp.split(' - ')] if P_Comp and ' - ' in P_Comp else [P_Comp]

            for Sub_Comp in Sub_Comps:
                if not Sub_Comp:
                    Sub_Comp = Entry['composition']
                if Sub_Comp and 'not specif' in Sub_Comp.lower():
                    Sub_Comp = 'Not Specified'

                P_Order_V = _parse_int_or_none(P_Order)
                P_Max_P_V = _parse_float_or_none(P_Max_P)
                Parent_Node_IDs = _find_parent_node_ids(Sub, Sub_Comp, P_Method, P_EoS, P_Order, P_Max_P, P_K0)

                if not Parent_Node_IDs:
                    Miss_Key = f"{Missing_Node_Prefix}{Sub}|{Sub_Comp}|{P_EoS or ''}|{P_Order_V}|{P_Max_P_V}|{P_K0}"
                    if Miss_Key not in Missing_Parents:
                        Miss_Node = {
                            'study': Sub, 'composition': Sub_Comp,
                            'eos': P_EoS or '', 'order': P_Order_V,
                            'max_pressure': P_Max_P_V, 'is_K0_fixed': P_K0, 'method': P_Method,
                            'parent_info': {'cal_to_name': ''},
                            'parent_node_ids': [], 'label': f"{Sub} (missing YAML)",
                            'display_label': f"{Sub} (missing YAML)",
                            'node_id': Miss_Key,
                            'has_calibration': False, 'is_special': False,
                        }
                        Missing_Parents[Miss_Key] = Miss_Node
                        All_Nodes[Miss_Key]       = Miss_Node
                        Parsed_Calibrations.append(Miss_Node)
                    Parent_Node_IDs = [Miss_Key]

                for Parent_Node_ID in Parent_Node_IDs:
                    if Parent_Node_ID and Parent_Node_ID not in Entry['parent_node_ids']:
                        Entry['parent_node_ids'].append(Parent_Node_ID)

    Compositions = sorted({E['composition'] for E in Parsed_Calibrations})
    Composition_Display_Names = {
        c: Material_Information.get(c, {}).get('Display_Name', c)
        for c in Compositions
    }

    for Entry in Parsed_Calibrations:
        Entry.pop('parent_info', None)

    return {
        'nodes': Parsed_Calibrations,
        'compositions': Compositions,
        'composition_display_names': Composition_Display_Names,
    }


def main():
    Graph = Build_Calibration_Graph()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(Graph), encoding="utf-8")

    Has_Calibration = sum(1 for n in Graph['nodes'] if n['has_calibration'])
    print(f"Wrote {len(Graph['nodes'])} nodes ({Has_Calibration} calibrations) across "
          f"{len(Graph['compositions'])} compositions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
