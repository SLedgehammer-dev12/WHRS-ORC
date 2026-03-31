from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from whrs_orc.logging.run_logger import log_screening_case_run
from whrs_orc.persistence.saved_cases import default_saved_case_filename, read_saved_case, write_saved_case
from whrs_orc.reporting.screening_report import (
    build_screening_markdown_report,
    build_screening_report_payload,
    default_report_filename,
)
from whrs_orc.equipment.contracts import BoilerDesignDriver, BoilerMode, OrcScreeningHeatMode, OrcScreeningPowerMode, ThermalOilLoopMode
from whrs_orc.properties.thermal_oil_properties import ThermalOilPropertyProvider
from whrs_orc.solvers.screening_case import ScreeningCaseInputs, ScreeningCaseResult, c_to_k, run_screening_case
from whrs_orc.ui.benchmark_cases import benchmark_display_map, design_target_display_value
from whrs_orc.ui.diagram_units import (
    PROCESS_INPUT_SPECS,
    convert_from_base,
    convert_to_base,
    design_target_default_value,
    design_target_default_unit,
    design_target_quantity,
    format_for_display,
    supported_units,
)
from whrs_orc.ui.equipment_details import build_equipment_details, build_idle_equipment_details, render_equipment_detail
from whrs_orc.ui.operator_guidance import build_operator_guidance, render_operator_guidance
from whrs_orc.ui.process_diagram import build_empty_process_snapshot, build_process_snapshot, status_color
from whrs_orc.ui.presets import DEFAULT_EXHAUST_COMPOSITION, WORKING_FLUID_PRESETS
from whrs_orc.ui.stream_motion import point_along_polyline, points_from_segments, polyline_length
from whrs_orc.ui.stream_palette import colors_for_temperature_span, fluid_gradient, gradient_swatch_colors
from whrs_orc.ui.view_model import build_ui_behavior_state


APP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES_DIR = APP_ROOT / "data" / "cases"
DEFAULT_LOG_PATH = APP_ROOT / "data" / "logs" / "screening_runs.jsonl"


class WHRSOrcApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("WHRS ORC Arayuz")
        self.geometry("1980x1280")
        self.minsize(1700, 1040)
        self.configure(bg="#f3efe6")
        DEFAULT_CASES_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        self.oil_provider = ThermalOilPropertyProvider()
        self.thermal_oils = self.oil_provider.list_thermal_oils()
        self.thermal_oil_names = ["Manual Oil"] + [str(item["display_name"]) for item in self.thermal_oils]
        self.benchmark_cases_by_name = benchmark_display_map()
        self.benchmark_case_names = list(self.benchmark_cases_by_name)

        self._build_styles()
        self._build_state()
        self._build_layout()
        self._load_defaults()

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Shell.TFrame", background="#f3efe6")
        style.configure("Panel.TFrame", background="#fffaf0")
        style.configure("PanelTitle.TLabel", background="#fffaf0", foreground="#223127", font=("Segoe UI Semibold", 12))
        style.configure("Hero.TFrame", background="#17322b")
        style.configure("HeroTitle.TLabel", background="#17322b", foreground="#f4efe2", font=("Georgia", 24, "bold"))
        style.configure("HeroBody.TLabel", background="#17322b", foreground="#c9d9cf", font=("Segoe UI", 10))
        style.configure("Card.TFrame", background="#f7f2e7", relief="flat")
        style.configure("CardTitle.TLabel", background="#f7f2e7", foreground="#5d6f63", font=("Segoe UI Semibold", 10))
        style.configure("CardValue.TLabel", background="#f7f2e7", foreground="#17322b", font=("Georgia", 16, "bold"))
        style.configure("Soft.TLabel", background="#fffaf0", foreground="#4c5d54", font=("Segoe UI", 9))
        style.configure("Process.TLabel", background="#fffaf0", foreground="#17322b", font=("Segoe UI Semibold", 10))
        style.configure("DiagramHint.TLabel", background="#fffaf0", foreground="#6f7d75", font=("Segoe UI", 8))
        style.configure("Run.TButton", font=("Segoe UI Semibold", 11))
        style.configure("Accent.TCombobox", padding=4)

    def _build_state(self) -> None:
        self.case_name_var = tk.StringVar(value="Station Screening Case")
        self.boiler_mode_var = tk.StringVar(value=BoilerMode.PERFORMANCE.value)
        self.boiler_driver_var = tk.StringVar(value=BoilerDesignDriver.TARGET_BOILER_EFFICIENCY.value)
        self.stack_min_temp_var = tk.StringVar(value="150")
        self.closure_tol_var = tk.StringVar(value="0.03")
        self.study_mode_title_var = tk.StringVar(value="")
        self.study_mode_helper_var = tk.StringVar(value="")
        self.selected_benchmark_var = tk.StringVar(value="")
        self.benchmark_summary_var = tk.StringVar(value="Hazir benchmark secerek ya da kayitli vaka acarak forma veri yukleyebilirsiniz.")
        self.export_status_var = tk.StringVar(value="Henuz export olusturulmadi.")
        self.selected_equipment_title_var = tk.StringVar(value="Selected Equipment")
        self.selected_equipment_body_var = tk.StringVar(value="Solve a case and click an equipment block to inspect details.")
        self.design_target_label_var = tk.StringVar(value="Tasarim hedefi")
        self.design_target_helper_var = tk.StringVar(value="")
        self.diagram_headline_var = tk.StringVar(value="Solve a case to populate the process view.")
        self.process_var = tk.StringVar(value="Exhaust -> Boiler -> Oil Loop -> ORC Heater -> Gross Power")

        self.exhaust_mass_flow_var = tk.StringVar(value="10")
        self.exhaust_inlet_temp_var = tk.StringVar(value="500")
        self.exhaust_outlet_temp_var = tk.StringVar(value="200")
        self.exhaust_pressure_var = tk.StringVar(value="101325")
        self.exhaust_vars = {component: tk.StringVar(value=str(value)) for component, value in DEFAULT_EXHAUST_COMPOSITION}

        self.oil_name_var = tk.StringVar(value="Manual Oil")
        self.oil_cp_var = tk.StringVar(value="2200")
        self.oil_density_var = tk.StringVar(value="880")
        self.oil_max_bulk_var = tk.StringVar(value="320")
        self.oil_mass_flow_var = tk.StringVar(value="20")
        self.oil_inlet_temp_var = tk.StringVar(value="175")
        self.oil_outlet_temp_var = tk.StringVar(value="250")
        self.loop_target_delivery_temp_var = tk.StringVar(value="245")

        self.loop_mode_var = tk.StringVar(value=ThermalOilLoopMode.ADIABATIC_LINK.value)
        self.loop_heat_loss_var = tk.StringVar(value="0")
        self.loop_pressure_drop_var = tk.StringVar(value="0")
        self.loop_pump_eff_var = tk.StringVar(value="0.75")

        self.wf_name_var = tk.StringVar(value="Cyclopentane Screening")
        self.wf_cp_var = tk.StringVar(value="2000")
        self.wf_inlet_temp_var = tk.StringVar(value="100")
        self.wf_pressure_var = tk.StringVar(value="200000")
        self.wf_max_outlet_var = tk.StringVar(value="170")

        self.orc_heat_mode_var = tk.StringVar(value=OrcScreeningHeatMode.SCREENING_FROM_OIL_SIDE.value)
        self.orc_target_wf_outlet_var = tk.StringVar(value="150")
        self.orc_known_heat_input_var = tk.StringVar(value="1000000")
        self.orc_min_approach_var = tk.StringVar(value="5")

        self.orc_power_mode_var = tk.StringVar(value=OrcScreeningPowerMode.GROSS_POWER_FROM_EFFICIENCY.value)
        self.eta_orc_gross_var = tk.StringVar(value="0.18")
        self.gross_power_target_var = tk.StringVar(value="400000")

        self.design_target_var = tk.StringVar(value="0.50")
        self._last_design_target_driver = self.boiler_driver_var.get()
        self.input_snapshot_text: ScrolledText | None = None
        self.guidance_text: ScrolledText | None = None
        self.process_canvas: tk.Canvas | None = None
        self.last_case: ScreeningCaseInputs | None = None
        self.last_result: ScreeningCaseResult | None = None
        self.selected_equipment_key = "boiler"
        self.current_equipment_details = build_idle_equipment_details()
        self.design_target_label_widget: ttk.Label | None = None
        self.design_target_entry: ttk.Entry | None = None
        self.design_target_hint_label: ttk.Label | None = None
        self.exhaust_outlet_entry: ttk.Entry | None = None
        self.oil_outlet_entry: ttk.Entry | None = None
        self.loop_heat_loss_entry: ttk.Entry | None = None
        self.loop_target_delivery_entry: ttk.Entry | None = None
        self.orc_target_wf_entry: ttk.Entry | None = None
        self.orc_known_heat_entry: ttk.Entry | None = None
        self.orc_efficiency_entry: ttk.Entry | None = None
        self.gross_power_target_entry: ttk.Entry | None = None
        self.oil_property_entries: list[ttk.Entry] = []
        self.wf_property_entries: list[ttk.Entry] = []
        self.diagram_stage_items: dict[str, dict[str, int]] = {}
        self.diagram_stream_items: dict[str, list[int]] = {}
        self.diagram_stream_particles: dict[str, int] = {}
        self.diagram_stream_progress: dict[str, float] = {}
        self.diagram_stream_speeds: dict[str, float] = {}
        self._stream_animation_after_id: str | None = None
        self.diagram_input_fields: dict[str, dict[str, object]] = {}
        self.diagram_design_target_field: dict[str, object] | None = None
        self.diagram_composition_fields: dict[str, dict[str, object]] = {}
        self.diagram_composition_total_label: tk.Label | None = None
        self._base_state_vars = {
            "exhaust_mass_flow": self.exhaust_mass_flow_var,
            "exhaust_inlet_temp": self.exhaust_inlet_temp_var,
            "exhaust_pressure": self.exhaust_pressure_var,
            "exhaust_outlet_temp": self.exhaust_outlet_temp_var,
            "stack_min_temp": self.stack_min_temp_var,
            "closure_tolerance": self.closure_tol_var,
            "oil_mass_flow": self.oil_mass_flow_var,
            "oil_outlet_temp": self.oil_outlet_temp_var,
            "oil_inlet_temp": self.oil_inlet_temp_var,
            "loop_heat_loss": self.loop_heat_loss_var,
            "loop_target_delivery_temp": self.loop_target_delivery_temp_var,
            "wf_max_outlet_temp": self.wf_max_outlet_var,
            "orc_min_approach": self.orc_min_approach_var,
            "wf_inlet_temp": self.wf_inlet_temp_var,
            "orc_target_wf_outlet": self.orc_target_wf_outlet_var,
            "orc_known_heat_input": self.orc_known_heat_input_var,
            "eta_orc_gross": self.eta_orc_gross_var,
            "gross_power_target": self.gross_power_target_var,
        }

    def _build_layout(self) -> None:
        shell = ttk.Frame(self, style="Shell.TFrame", padding=18)
        shell.pack(fill="both", expand=True)

        hero = ttk.Frame(shell, style="Hero.TFrame", padding=(22, 18))
        hero.pack(fill="x", pady=(0, 14))
        ttk.Label(hero, text="WHRS ORC Screening Studio", style="HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(
            hero,
            text="Egzoz > Waste Heat Boiler > Thermal Oil Loop > ORC Screening Heat Uptake > Gross Power",
            style="HeroBody.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        body = ttk.Panedwindow(shell, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, style="Panel.TFrame", padding=14)
        right = ttk.Frame(body, style="Panel.TFrame", padding=14)
        body.add(left, weight=3)
        body.add(right, weight=4)

        self._build_input_panel(left)
        self._build_output_panel(right)

    def _build_input_panel(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="Panel.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Hesaplama Girdileri", style="PanelTitle.TLabel").pack(side="left")
        actions = ttk.Frame(header, style="Panel.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text="Hesabi Calistir", style="Run.TButton", command=self._solve_case).pack(side="right")
        ttk.Button(actions, text="Vaka Kaydet", command=self._save_current_case).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Vaka Ac", command=self._load_saved_case).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Benchmark Yukle", command=self._load_selected_benchmark).pack(side="right", padx=(8, 0))
        ttk.Combobox(
            actions,
            textvariable=self.selected_benchmark_var,
            values=self.benchmark_case_names,
            state="readonly",
            width=32,
            style="Accent.TCombobox",
        ).pack(side="right", padx=(0, 8))

        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, pady=(10, 0))

        tab_case = ttk.Frame(notebook, style="Panel.TFrame", padding=10)
        tab_exhaust = ttk.Frame(notebook, style="Panel.TFrame", padding=10)
        tab_oil = ttk.Frame(notebook, style="Panel.TFrame", padding=10)
        tab_orc = ttk.Frame(notebook, style="Panel.TFrame", padding=10)
        notebook.add(tab_case, text="Calisma")
        notebook.add(tab_exhaust, text="Egzoz + Kazan")
        notebook.add(tab_oil, text="Yag Dongusu")
        notebook.add(tab_orc, text="ORC")

        self._build_case_tab(tab_case)
        self._build_exhaust_tab(tab_exhaust)
        self._build_oil_tab(tab_oil)
        self._build_orc_tab(tab_orc)

    def _build_case_tab(self, parent: ttk.Frame) -> None:
        self._entry_row(parent, "Vaka adi", self.case_name_var, 0)
        self._combo_row(parent, "Kazan modu", self.boiler_mode_var, [m.value for m in BoilerMode], 1)
        self._combo_row(parent, "Tasarim surucusu", self.boiler_driver_var, [d.value for d in BoilerDesignDriver], 2)
        self.design_target_label_widget = ttk.Label(parent, textvariable=self.design_target_label_var)
        self.design_target_label_widget.grid(row=3, column=0, sticky="w", pady=4, padx=(0, 10))
        self.design_target_entry = ttk.Entry(parent, textvariable=self.design_target_var)
        self.design_target_entry.grid(row=3, column=1, sticky="ew", pady=4)
        parent.grid_columnconfigure(1, weight=1)
        self.design_target_hint_label = ttk.Label(parent, textvariable=self.design_target_helper_var, style="Soft.TLabel", wraplength=340, justify="left")
        self.design_target_hint_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self._entry_row(parent, "Minimum stack sicakligi [degC]", self.stack_min_temp_var, 5)
        self._entry_row(parent, "Enerji kapanis toleransi", self.closure_tol_var, 6)
        ttk.Separator(parent).grid(row=7, column=0, columnspan=2, sticky="ew", pady=10)
        ttk.Label(parent, textvariable=self.study_mode_title_var, style="PanelTitle.TLabel").grid(row=8, column=0, columnspan=2, sticky="w")
        ttk.Label(parent, textvariable=self.study_mode_helper_var, style="Soft.TLabel", wraplength=340, justify="left").grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(4, 0),
        )
        ttk.Separator(parent).grid(row=10, column=0, columnspan=2, sticky="ew", pady=10)
        ttk.Label(parent, text="Case note", style="PanelTitle.TLabel").grid(row=11, column=0, columnspan=2, sticky="w")
        ttk.Label(parent, textvariable=self.benchmark_summary_var, style="Soft.TLabel", wraplength=340, justify="left").grid(
            row=12,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(4, 0),
        )

    def _build_exhaust_tab(self, parent: ttk.Frame) -> None:
        self._entry_row(parent, "Egzoz debisi [kg/s]", self.exhaust_mass_flow_var, 0)
        self._entry_row(parent, "Egzoz giris sicakligi [degC]", self.exhaust_inlet_temp_var, 1)
        self.exhaust_outlet_entry = self._entry_row(parent, "Egzoz cikis sicakligi [degC]", self.exhaust_outlet_temp_var, 2)
        self._entry_row(parent, "Egzoz basinci [Pa]", self.exhaust_pressure_var, 3)
        ttk.Label(parent, text="Egzoz kompozisyonu", style="PanelTitle.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", pady=(14, 4))
        row = 5
        for component, variable in self.exhaust_vars.items():
            self._entry_row(parent, f"{component} mol kesri", variable, row)
            row += 1

    def _build_oil_tab(self, parent: ttk.Frame) -> None:
        self._combo_row(parent, "Isi transfer yagi", self.oil_name_var, self.thermal_oil_names, 0)
        self.oil_property_entries.append(self._entry_row(parent, "Yag cp [J/kg/K]", self.oil_cp_var, 1))
        self.oil_property_entries.append(self._entry_row(parent, "Yag yogunluk [kg/m3]", self.oil_density_var, 2))
        self.oil_property_entries.append(self._entry_row(parent, "Yag max bulk temp [degC]", self.oil_max_bulk_var, 3))
        self._entry_row(parent, "Yag debisi [kg/s]", self.oil_mass_flow_var, 4)
        self._entry_row(parent, "Yag giris sicakligi [degC]", self.oil_inlet_temp_var, 5)
        self.oil_outlet_entry = self._entry_row(parent, "Kazan cikisi yag sicakligi [degC]", self.oil_outlet_temp_var, 6)
        ttk.Separator(parent).grid(row=7, column=0, columnspan=2, sticky="ew", pady=10)
        self._combo_row(parent, "Loop modu", self.loop_mode_var, [m.value for m in ThermalOilLoopMode], 8)
        self.loop_heat_loss_entry = self._entry_row(parent, "Loop isi kaybi [W]", self.loop_heat_loss_var, 9)
        self.loop_target_delivery_entry = self._entry_row(parent, "Hedef teslim yag sicakligi [degC]", self.loop_target_delivery_temp_var, 10)
        self._entry_row(parent, "Loop basinc dusumu [Pa]", self.loop_pressure_drop_var, 11)
        self._entry_row(parent, "Pompa verimi", self.loop_pump_eff_var, 12)

        self.oil_name_var.trace_add("write", lambda *_: self._apply_oil_preset())

    def _build_orc_tab(self, parent: ttk.Frame) -> None:
        self._combo_row(parent, "ORC akiskani", self.wf_name_var, list(WORKING_FLUID_PRESETS), 0)
        self.wf_property_entries.append(self._entry_row(parent, "Akiskan cp [J/kg/K]", self.wf_cp_var, 1))
        self._entry_row(parent, "Akiskan giris sicakligi [degC]", self.wf_inlet_temp_var, 2)
        self._entry_row(parent, "Akiskan basinci [Pa]", self.wf_pressure_var, 3)
        self.wf_property_entries.append(self._entry_row(parent, "Akiskan max cikis sicakligi [degC]", self.wf_max_outlet_var, 4))
        ttk.Separator(parent).grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)
        self._combo_row(parent, "ORC isi alma modu", self.orc_heat_mode_var, [m.value for m in OrcScreeningHeatMode], 6)
        self.orc_target_wf_entry = self._entry_row(parent, "Hedef akiskan cikis sicakligi [degC]", self.orc_target_wf_outlet_var, 7)
        self.orc_known_heat_entry = self._entry_row(parent, "Bilinen ORC isi girdisi [W]", self.orc_known_heat_input_var, 8)
        self._entry_row(parent, "Minimum yaklasim [K]", self.orc_min_approach_var, 9)
        ttk.Separator(parent).grid(row=10, column=0, columnspan=2, sticky="ew", pady=10)
        self._combo_row(parent, "ORC guc modu", self.orc_power_mode_var, [m.value for m in OrcScreeningPowerMode], 11)
        self.orc_efficiency_entry = self._entry_row(parent, "Hedef ORC brut verim", self.eta_orc_gross_var, 12)
        self.gross_power_target_entry = self._entry_row(parent, "Hedef brut elektrik gucu [W]", self.gross_power_target_var, 13)

        self.wf_name_var.trace_add("write", lambda *_: self._apply_wf_preset())

    def _build_output_panel(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="Panel.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Proses Gorunumu + Sonuclar", style="PanelTitle.TLabel").pack(side="left")
        actions = ttk.Frame(header, style="Panel.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text="JSON Bundle Kaydet", command=self._export_case_bundle).pack(side="right")
        ttk.Button(actions, text="Markdown Rapor Kaydet", command=self._export_markdown_report).pack(side="right", padx=(0, 8))
        ttk.Label(parent, textvariable=self.export_status_var, style="Soft.TLabel").pack(anchor="w", pady=(4, 0))

        process_strip = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        process_strip.pack(fill="x", pady=(10, 14))
        ttk.Label(process_strip, textvariable=self.diagram_headline_var, style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(process_strip, textvariable=self.process_var, style="Process.TLabel", wraplength=1320, justify="left").pack(anchor="w", pady=(4, 4))
        ttk.Label(
            process_strip,
            text="Process kutularindan giris yapabilirsiniz. Her kutuda birim secimi vardir; girisler solve oncesi otomatik taban birimlere donusturulur. Her akiskan ailesi kendi soguk-sicak renk gecisi ile cizilir.",
            style="DiagramHint.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        self.process_canvas = tk.Canvas(process_strip, height=880, bg="#fbf7ef", highlightthickness=0, bd=0)
        self.process_canvas.pack(fill="x")
        self._draw_process_scene()
        self._build_process_input_boxes()
        self._build_design_target_box()
        self._build_exhaust_composition_box()
        legend = ttk.Frame(process_strip, style="Panel.TFrame")
        legend.pack(fill="x", pady=(8, 0))
        self._legend_gradient_item(legend, "exhaust")
        self._legend_gradient_item(legend, "oil")
        self._legend_gradient_item(legend, "working_fluid")
        self._legend_item(legend, "Electrical power", "#134f95")
        self._legend_item(legend, "Success", status_color("success"))
        self._legend_item(legend, "Warning", status_color("warning"))
        self._legend_item(legend, "Blocked", status_color("blocked"))

        detail_card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        detail_card.pack(fill="x", pady=(0, 12))
        ttk.Label(detail_card, textvariable=self.selected_equipment_title_var, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            detail_card,
            textvariable=self.selected_equipment_body_var,
            style="Soft.TLabel",
            wraplength=1320,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        cards = ttk.Frame(parent, style="Panel.TFrame")
        cards.pack(fill="x")
        self.kpi_labels: dict[str, tk.StringVar] = {}
        for key, title in [
            ("q_exhaust_available_w", "Available Heat"),
            ("eta_boiler", "Boiler Eff."),
            ("q_orc_absorbed_w", "ORC Heat"),
            ("gross_electric_power_w", "Gross Power"),
            ("eta_system_gross", "System Eff."),
        ]:
            frame = ttk.Frame(cards, style="Card.TFrame", padding=12)
            frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
            ttk.Label(frame, text=title, style="CardTitle.TLabel").pack(anchor="w")
            var = tk.StringVar(value="--")
            ttk.Label(frame, textvariable=var, style="CardValue.TLabel").pack(anchor="w", pady=(6, 0))
            self.kpi_labels[key] = var

        body = ttk.Notebook(parent)
        body.pack(fill="both", expand=True, pady=(14, 0))

        input_tab = ttk.Frame(body, style="Panel.TFrame", padding=10)
        guidance_tab = ttk.Frame(body, style="Panel.TFrame", padding=10)
        summary_tab = ttk.Frame(body, style="Panel.TFrame", padding=10)
        diagnostics_tab = ttk.Frame(body, style="Panel.TFrame", padding=10)
        body.add(input_tab, text="Input Snapshot")
        body.add(guidance_tab, text="Operator Guidance")
        body.add(summary_tab, text="Summary")
        body.add(diagnostics_tab, text="Diagnostics")

        self.input_snapshot_text = ScrolledText(input_tab, wrap="word", font=("Consolas", 10), bg="#fbf7ef", fg="#21312b")
        self.input_snapshot_text.pack(fill="both", expand=True)
        self.guidance_text = ScrolledText(guidance_tab, wrap="word", font=("Consolas", 10), bg="#fbf7ef", fg="#21312b")
        self.guidance_text.pack(fill="both", expand=True)
        self.summary_text = ScrolledText(summary_tab, wrap="word", font=("Consolas", 10), bg="#fbf7ef", fg="#21312b")
        self.summary_text.pack(fill="both", expand=True)
        self.diagnostics_text = ScrolledText(diagnostics_tab, wrap="word", font=("Consolas", 10), bg="#fbf7ef", fg="#21312b")
        self.diagnostics_text.pack(fill="both", expand=True)

    def _entry_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=4)
        parent.grid_columnconfigure(1, weight=1)
        return entry

    def _legend_item(self, parent: ttk.Frame, label: str, color: str) -> None:
        item = ttk.Frame(parent, style="Panel.TFrame")
        item.pack(side="left", padx=(0, 14))
        swatch = tk.Canvas(item, width=16, height=16, bg="#fffaf0", highlightthickness=0, bd=0)
        swatch.pack(side="left")
        swatch.create_rectangle(2, 2, 14, 14, fill=color, outline=color)
        ttk.Label(item, text=label, style="Soft.TLabel").pack(side="left", padx=(5, 0))

    def _legend_gradient_item(self, parent: ttk.Frame, fluid_key: str) -> None:
        palette = fluid_gradient(fluid_key)
        item = ttk.Frame(parent, style="Panel.TFrame")
        item.pack(side="left", padx=(0, 16))
        swatch = tk.Canvas(item, width=68, height=16, bg="#fffaf0", highlightthickness=0, bd=0)
        swatch.pack(side="left")
        colors = gradient_swatch_colors(fluid_key, steps=6)
        for index, color in enumerate(colors):
            swatch.create_rectangle(4 + index * 10, 3, 12 + index * 10, 13, fill=color, outline=color)
        swatch.create_text(6, 8, text="C", fill="#21312b", font=("Segoe UI", 7, "bold"))
        swatch.create_text(60, 8, text="H", fill="#21312b", font=("Segoe UI", 7, "bold"))
        ttk.Label(item, text=f"{palette.label}  cold -> hot", style="Soft.TLabel").pack(side="left", padx=(6, 0))

    def _build_process_input_boxes(self) -> None:
        if self.process_canvas is None:
            return
        for spec in PROCESS_INPUT_SPECS:
            frame = tk.Frame(
                self.process_canvas,
                bg="#fffdfa",
                highlightthickness=2,
                highlightbackground=spec.accent_color,
                highlightcolor=spec.accent_color,
                bd=0,
                padx=7,
                pady=6,
            )
            label = tk.Label(frame, text=spec.label, bg="#fffdfa", fg="#17322b", font=("Segoe UI Semibold", 8))
            label.pack(anchor="w")
            row = tk.Frame(frame, bg="#fffdfa")
            row.pack(fill="x", pady=(4, 0))
            display_var = tk.StringVar(value="")
            unit_var = tk.StringVar(value=spec.default_unit)
            entry = ttk.Entry(row, textvariable=display_var, width=11)
            entry.pack(side="left")
            combo = ttk.Combobox(row, textvariable=unit_var, values=list(supported_units(spec.quantity)), state="readonly", width=7, style="Accent.TCombobox")
            combo.pack(side="left", padx=(6, 0))
            hint = tk.Label(frame, text=spec.default_unit, bg="#fffdfa", fg="#6f7d75", font=("Segoe UI", 7))
            hint.pack(anchor="w", pady=(3, 0))
            self.process_canvas.create_window(spec.x, spec.y, anchor="nw", window=frame)
            self.diagram_input_fields[spec.key] = {
                "spec": spec,
                "frame": frame,
                "label": label,
                "entry": entry,
                "combo": combo,
                "hint": hint,
                "display_var": display_var,
                "unit_var": unit_var,
            }
            entry.bind("<FocusOut>", lambda _event, key=spec.key: self._commit_diagram_field(key, show_error=False))
            entry.bind("<Return>", lambda _event, key=spec.key: self._commit_diagram_field(key))
            combo.bind("<<ComboboxSelected>>", lambda _event, key=spec.key: self._on_diagram_unit_changed(key))

    def _build_design_target_box(self) -> None:
        if self.process_canvas is None:
            return
        frame = tk.Frame(
            self.process_canvas,
            bg="#fffdfa",
            highlightthickness=2,
            highlightbackground="#123f7a",
            highlightcolor="#123f7a",
            bd=0,
            padx=7,
            pady=6,
        )
        title = tk.Label(frame, text="Design target", bg="#fffdfa", fg="#17322b", font=("Segoe UI Semibold", 8))
        title.pack(anchor="w")
        helper = tk.Label(frame, text="", bg="#fffdfa", fg="#6f7d75", font=("Segoe UI", 7), wraplength=176, justify="left")
        helper.pack(anchor="w", pady=(2, 2))
        row = tk.Frame(frame, bg="#fffdfa")
        row.pack(fill="x")
        display_var = tk.StringVar(value="")
        unit_var = tk.StringVar(value="degC")
        entry = ttk.Entry(row, textvariable=display_var, width=12)
        entry.pack(side="left")
        combo = ttk.Combobox(row, textvariable=unit_var, values=("degC",), state="readonly", width=7, style="Accent.TCombobox")
        combo.pack(side="left", padx=(6, 0))
        hint = tk.Label(frame, text="", bg="#fffdfa", fg="#6f7d75", font=("Segoe UI", 7))
        hint.pack(anchor="w", pady=(3, 0))
        self.process_canvas.create_window(1460, 268, anchor="nw", window=frame)
        self.diagram_design_target_field = {
            "frame": frame,
            "title": title,
            "helper": helper,
            "entry": entry,
            "combo": combo,
            "hint": hint,
            "display_var": display_var,
            "unit_var": unit_var,
        }
        entry.bind("<FocusOut>", lambda _event: self._commit_design_target_field(show_error=False))
        entry.bind("<Return>", lambda _event: self._commit_design_target_field())
        combo.bind("<<ComboboxSelected>>", lambda _event: self._on_design_target_unit_changed())

    def _build_exhaust_composition_box(self) -> None:
        if self.process_canvas is None:
            return
        frame = tk.Frame(
            self.process_canvas,
            bg="#fffdfa",
            highlightthickness=2,
            highlightbackground="#de2f2f",
            highlightcolor="#de2f2f",
            bd=0,
            padx=7,
            pady=6,
        )
        tk.Label(frame, text="Exhaust composition", bg="#fffdfa", fg="#17322b", font=("Segoe UI Semibold", 8)).pack(anchor="w")
        tk.Label(
            frame,
            text="Mol kesri veya yuzde girebilirsiniz.",
            bg="#fffdfa",
            fg="#6f7d75",
            font=("Segoe UI", 7),
        ).pack(anchor="w", pady=(2, 4))
        for component in self.exhaust_vars:
            row = tk.Frame(frame, bg="#fffdfa")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=component, width=5, anchor="w", bg="#fffdfa", fg="#17322b", font=("Segoe UI", 8)).pack(side="left")
            display_var = tk.StringVar(value="")
            unit_var = tk.StringVar(value="frac")
            entry = ttk.Entry(row, textvariable=display_var, width=8)
            entry.pack(side="left")
            combo = ttk.Combobox(row, textvariable=unit_var, values=("frac", "%"), state="readonly", width=5, style="Accent.TCombobox")
            combo.pack(side="left", padx=(6, 0))
            self.diagram_composition_fields[component] = {
                "frame": frame,
                "entry": entry,
                "combo": combo,
                "display_var": display_var,
                "unit_var": unit_var,
            }
            entry.bind("<FocusOut>", lambda _event, component_id=component: self._commit_composition_field(component_id, show_error=False))
            entry.bind("<Return>", lambda _event, component_id=component: self._commit_composition_field(component_id))
            combo.bind("<<ComboboxSelected>>", lambda _event, component_id=component: self._on_composition_unit_changed(component_id))
        self.diagram_composition_total_label = tk.Label(frame, text="Total = --", bg="#fffdfa", fg="#6f7d75", font=("Segoe UI Semibold", 7))
        self.diagram_composition_total_label.pack(anchor="w", pady=(4, 0))
        self.process_canvas.create_window(20, 446, anchor="nw", window=frame)

    def _bind_base_state_sync(self) -> None:
        for key, variable in self._base_state_vars.items():
            variable.trace_add("write", lambda *_args, sync_key=key: self._sync_single_state_to_diagram_field(sync_key))
        for component, variable in self.exhaust_vars.items():
            variable.trace_add("write", lambda *_args, component_id=component: self._sync_single_composition_field(component_id))
        self.design_target_var.trace_add("write", lambda *_args: self._sync_design_target_field())

    def _sync_all_state_to_diagram_fields(self) -> None:
        for key in self.diagram_input_fields:
            self._sync_single_state_to_diagram_field(key)
        for component in self.diagram_composition_fields:
            self._sync_single_composition_field(component)
        self._update_composition_total_display()
        self._sync_design_target_field()
        self._update_process_stream_colors()

    def _sync_single_state_to_diagram_field(self, key: str) -> None:
        field = self.diagram_input_fields.get(key)
        if field is None:
            return
        spec = field["spec"]
        unit = field["unit_var"].get()
        base_var = self._base_state_vars[spec.base_state_key]
        raw = base_var.get().strip()
        if not raw:
            field["display_var"].set("")
            return
        try:
            display_value = convert_from_base(spec.quantity, float(raw), unit)
        except ValueError:
            return
        field["display_var"].set(format_for_display(spec.quantity, display_value))
        field["hint"].configure(text=unit)
        self._update_process_stream_colors()

    def _commit_diagram_field(self, key: str, *, show_error: bool = True):
        field = self.diagram_input_fields.get(key)
        if field is None:
            return "break"
        raw = field["display_var"].get().strip()
        if not raw:
            return "break"
        spec = field["spec"]
        try:
            base_value = convert_to_base(spec.quantity, float(raw), field["unit_var"].get())
        except ValueError as exc:
            if show_error:
                messagebox.showerror("Input Error", f"{spec.label}: {exc}")
            return "break"
        self._base_state_vars[spec.base_state_key].set(self._format_base_value(base_value))
        return "break"

    def _on_diagram_unit_changed(self, key: str) -> None:
        self._sync_single_state_to_diagram_field(key)

    def _sync_single_composition_field(self, component: str) -> None:
        field = self.diagram_composition_fields.get(component)
        if field is None:
            return
        raw = self.exhaust_vars[component].get().strip()
        if not raw:
            field["display_var"].set("")
            return
        value = convert_from_base("ratio", float(raw), field["unit_var"].get())
        field["display_var"].set(format_for_display("ratio", value))
        self._update_composition_total_display()

    def _commit_composition_field(self, component: str, *, show_error: bool = True):
        field = self.diagram_composition_fields.get(component)
        if field is None:
            return "break"
        raw = field["display_var"].get().strip()
        if not raw:
            return "break"
        try:
            value = convert_to_base("ratio", float(raw), field["unit_var"].get())
        except ValueError as exc:
            if show_error:
                messagebox.showerror("Input Error", f"{component}: {exc}")
            return "break"
        self.exhaust_vars[component].set(self._format_base_value(value))
        self._update_composition_total_display()
        return "break"

    def _on_composition_unit_changed(self, component: str) -> None:
        self._sync_single_composition_field(component)

    def _update_composition_total_display(self) -> None:
        if self.diagram_composition_total_label is None:
            return
        total = 0.0
        for variable in self.exhaust_vars.values():
            raw = variable.get().strip()
            if not raw:
                continue
            total += float(raw)
        delta = abs(total - 1.0)
        fg = "#2e8b57" if delta <= 0.01 else "#c0392b"
        self.diagram_composition_total_label.configure(text=f"Total = {total:.3f}", fg=fg)

    def _sync_design_target_field(self) -> None:
        if self.diagram_design_target_field is None:
            return
        driver = BoilerDesignDriver(self.boiler_driver_var.get())
        quantity = design_target_quantity(driver)
        default_unit = design_target_default_unit(driver)
        combo = self.diagram_design_target_field["combo"]
        unit_var = self.diagram_design_target_field["unit_var"]
        values = list(supported_units(quantity))
        combo.configure(values=values)
        if unit_var.get() not in values:
            unit_var.set(default_unit)
        title_text = f"{self.design_target_label_var.get()}"
        self.diagram_design_target_field["title"].configure(text=title_text)
        self.diagram_design_target_field["helper"].configure(text=self.design_target_helper_var.get())
        raw = self.design_target_var.get().strip()
        if not raw:
            self.diagram_design_target_field["display_var"].set("")
            return
        display_value = convert_from_base(quantity, float(raw), unit_var.get())
        self.diagram_design_target_field["display_var"].set(format_for_display(quantity, display_value))
        self.diagram_design_target_field["hint"].configure(text=unit_var.get())
        self._update_process_stream_colors()

    def _commit_design_target_field(self, *, show_error: bool = True):
        if self.diagram_design_target_field is None:
            return "break"
        raw = self.diagram_design_target_field["display_var"].get().strip()
        if not raw:
            return "break"
        driver = BoilerDesignDriver(self.boiler_driver_var.get())
        quantity = design_target_quantity(driver)
        try:
            value = convert_to_base(quantity, float(raw), self.diagram_design_target_field["unit_var"].get())
        except ValueError as exc:
            if show_error:
                messagebox.showerror("Input Error", f"Design target: {exc}")
            return "break"
        self.design_target_var.set(self._format_base_value(value))
        return "break"

    def _on_design_target_unit_changed(self) -> None:
        self._sync_design_target_field()

    def _draw_process_scene(self) -> None:
        if self.process_canvas is None:
            return
        canvas = self.process_canvas
        canvas.delete("all")
        canvas.configure(width=1720)
        self.diagram_stage_items = {}
        self.diagram_stream_items = {}
        self.diagram_stream_particles = {}
        self.diagram_stream_progress = {}
        self.diagram_stream_speeds = {}

        exhaust_hot = fluid_gradient("exhaust").hot_color
        oil_hot = fluid_gradient("oil").hot_color
        wf_hot = fluid_gradient("working_fluid").hot_color
        power_color = "#134f95"
        metal = "#123f7a"
        text_dark = "#17322b"
        panel_bg = "#fbf7ef"

        canvas.create_text(72, 318, text="FACTORY", fill=metal, font=("Georgia", 21, "bold"))
        canvas.create_text(252, 332, text="EXHAUST GAS CIRCUIT", fill=exhaust_hot, font=("Segoe UI Semibold", 10))
        canvas.create_text(438, 22, text="THERMAL OIL CIRCUIT", fill=oil_hot, font=("Segoe UI Semibold", 10))
        canvas.create_text(604, 20, text="ORGANIC FLUID CIRCUIT", fill=wf_hot, font=("Segoe UI Semibold", 10))
        canvas.create_text(812, 40, text="GRID", fill=metal, font=("Segoe UI Semibold", 9))
        canvas.create_text(804, 138, text="SELF\nUSE", fill=metal, font=("Segoe UI Semibold", 8), justify="center")
        canvas.create_text(246, 26, text="STACK", fill="#6f7d75", font=("Segoe UI", 8))
        canvas.create_text(392, 58, text="Oil supply header", fill="#6f7d75", font=("Segoe UI", 8))
        canvas.create_text(618, 286, text="Heat rejection + condensate return", fill="#6f7d75", font=("Segoe UI", 8))
        canvas.create_text(646, 174, text="Electric power export", fill="#6f7d75", font=("Segoe UI", 8))
        canvas.create_text(300, 260, text="Duty transfer zone", fill="#6f7d75", font=("Segoe UI", 8))

        self._draw_factory_icon(canvas, 42, 110, metal, stage_tag="stage_factory")
        self._register_stage_texts(canvas, "factory", "Factory", 72, 96, 72, 210, panel_bg, text_dark, stage_tag="stage_factory")
        self._draw_stack_icon(canvas, 332, 6, metal)
        self._draw_exhaust_loop(canvas)
        self._draw_oil_loop(canvas)
        self._draw_wf_loop(canvas)
        self._draw_power_path(canvas, power_color)

        self._register_round_rect_stage("boiler", canvas, 220, 58, 292, 220, "Boiler", metal, panel_bg, text_dark)
        self._draw_boiler_core(canvas, 220, 58, 292, 220, exhaust_hot, oil_hot, stage_tag="stage_boiler")
        self._register_capsule_stage("heat_exchanger", canvas, 350, 70, 452, 120, "Heat Exchanger", metal, panel_bg, text_dark)
        self._draw_heat_exchanger_core(canvas, 350, 70, 452, 120, wf_hot, stage_tag="stage_heat_exchanger")
        self._register_turbine_stage(canvas, 492, 76, 580, 138, "turbine", "Turbine", metal, panel_bg, text_dark)
        self._register_rect_stage("generator", canvas, 607, 83, 698, 131, "Generator", metal, panel_bg, text_dark)
        self._register_capsule_stage("regenerator", canvas, 550, 206, 690, 250, "Regenerator", metal, panel_bg, text_dark)
        self._draw_heat_exchanger_core(canvas, 550, 206, 690, 250, wf_hot, stage_tag="stage_regenerator")
        self._register_condenser_stage(canvas, 575, 275, 685, 340, "condenser", "Air Condenser", metal, panel_bg, text_dark)
        self._register_pump_stage("oil_pump", canvas, 335, 226, "Oil Pump", metal, panel_bg, text_dark)
        self._register_pump_stage("organic_pump", canvas, 458, 298, "Organic Pump", metal, panel_bg, text_dark)
        canvas.create_line(680, 98, 734, 70, fill=power_color, width=2, dash=(4, 3))
        canvas.create_line(214, 224, 244, 248, fill=exhaust_hot, width=2, dash=(4, 3))
        canvas.create_line(392, 226, 422, 252, fill=oil_hot, width=2, dash=(4, 3))
        canvas.scale("all", 0, 0, 1.38, 1.38)
        canvas.move("all", 256, 86)
        self._update_process_stream_colors()
        self._bind_stage_interactions()
        self._restart_stream_animation()

    def _draw_factory_icon(self, canvas: tk.Canvas, x: int, y: int, color: str, *, stage_tag: str | None = None) -> None:
        tags = (stage_tag,) if stage_tag else ()
        canvas.create_rectangle(x, y + 20, x + 60, y + 72, fill=color, outline=color, tags=tags)
        for index in range(3):
            offset = x + 8 + index * 18
            canvas.create_rectangle(offset, y, offset + 10, y + 20, fill=color, outline=color, tags=tags)
            canvas.create_line(offset + 4, y - 10, offset + 12, y - 14, fill=color, width=3, smooth=True, tags=tags)
        for notch in range(4):
            nx = x + 6 + notch * 14
            canvas.create_rectangle(nx, y + 48, nx + 8, y + 56, fill=canvas["bg"], outline=canvas["bg"], tags=tags)

    def _draw_stack_icon(self, canvas: tk.Canvas, x: int, y: int, color: str) -> None:
        canvas.create_rectangle(x + 6, y + 8, x + 20, y + 44, fill="", outline=color, width=3)
        canvas.create_line(x + 10, y + 4, x + 16, y, fill=color, width=2, smooth=True)
        canvas.create_line(x + 18, y + 2, x + 24, y - 4, fill=color, width=2, smooth=True)
        canvas.create_line(x + 6, y + 44, x + 20, y + 44, fill=color, width=3)

    def _draw_exhaust_loop(self, canvas: tk.Canvas) -> None:
        self._create_path_items(
            canvas,
            "exhaust_main",
            [
                (104, 146),
                (152, 146),
                (152, 34),
                (236, 34),
                (236, 146),
                (236, 232),
                (104, 232),
            ],
            width=6,
            smooth=False,
        )
        for y in [58, 148, 206]:
            canvas.create_rectangle(206, y, 234, y + 10, outline="#527ba8", width=2)

    def _draw_oil_loop(self, canvas: tk.Canvas) -> None:
        self._create_path_items(
            canvas,
            "oil_supply",
            [
                (292, 72),
                (392, 72),
                (392, 120),
                (286, 120),
            ],
            width=6,
            smooth=False,
        )
        self._create_path_items(
            canvas,
            "oil_return",
            [
                (272, 220),
                (272, 232),
                (350, 232),
                (350, 224),
                (392, 224),
                (392, 120),
            ],
            width=6,
            smooth=False,
        )

    def _draw_wf_loop(self, canvas: tk.Canvas) -> None:
        self._create_path_items(
            canvas,
            "wf_hot",
            [
                (452, 92),
                (492, 92),
                (492, 72),
                (540, 72),
            ],
            width=6,
            smooth=False,
        )
        self._create_path_items(
            canvas,
            "wf_reject",
            [
                (540, 138),
                (540, 206),
                (620, 206),
                (620, 250),
                (620, 275),
                (490, 275),
            ],
            width=6,
            smooth=False,
        )
        self._create_path_items(
            canvas,
            "wf_cold",
            [
                (490, 275),
                (490, 312),
                (428, 312),
                (428, 120),
                (350, 120),
            ],
            width=6,
            smooth=False,
        )
        for index, x in enumerate([578, 602, 626]):
            tag = f"wf_regen_branch_{index}"
            self._create_path_items(canvas, tag, [(x, 250), (x, 272)], width=4, smooth=False)

    def _draw_power_path(self, canvas: tk.Canvas, color: str) -> None:
        self._create_path_items(
            canvas,
            "power_export",
            [
                (580, 108),
                (607, 108),
                (698, 108),
                (760, 108),
                (760, 48),
            ],
            width=5,
            smooth=False,
            fixed_color=color,
        )
        self._create_path_items(
            canvas,
            "power_auxiliary",
            [
                (698, 108),
                (698, 154),
                (760, 154),
            ],
            width=5,
            smooth=False,
            fixed_color=color,
        )
        self._draw_grid_icon(canvas, 738, 20, color)
        self._draw_factory_icon(canvas, 726, 160, color)
        canvas.create_line(640, 55, 646, 45, fill=color, width=3)
        canvas.create_line(650, 55, 656, 45, fill=color, width=3)
        canvas.create_line(632, 64, 637, 54, fill=color, width=3)

    def _draw_grid_icon(self, canvas: tk.Canvas, x: int, y: int, color: str) -> None:
        canvas.create_polygon(x + 20, y, x + 34, y + 18, x + 6, y + 18, fill="", outline=color, width=3)
        canvas.create_line(x + 20, y + 18, x + 12, y + 58, fill=color, width=3)
        canvas.create_line(x + 20, y + 18, x + 28, y + 58, fill=color, width=3)
        canvas.create_line(x + 10, y + 30, x + 30, y + 30, fill=color, width=3)
        canvas.create_line(x + 6, y + 42, x + 34, y + 42, fill=color, width=3)
        canvas.create_line(x + 2, y + 58, x + 38, y + 58, fill=color, width=3)

    def _create_path_items(
        self,
        canvas: tk.Canvas,
        key: str,
        points: list[tuple[int, int]],
        *,
        width: int,
        smooth: bool,
        fixed_color: str | None = None,
    ) -> None:
        item_ids: list[int] = []
        if fixed_color is None:
            default_color = "#8d99a6"
        else:
            default_color = fixed_color
        for index, ((x1, y1), (x2, y2)) in enumerate(zip(points, points[1:])):
            item_ids.append(
                canvas.create_line(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=default_color,
                    width=width,
                    smooth=smooth,
                    capstyle="round",
                    joinstyle="round",
                    arrow="last",
                    arrowshape=(10, 12, 4),
                )
            )
        self.diagram_stream_items[key] = item_ids

    def _update_process_stream_colors(self) -> None:
        if self.process_canvas is None or not self.diagram_stream_items:
            return
        exhaust_in = self._read_float_var(self.exhaust_inlet_temp_var, 500.0)
        exhaust_out = self._effective_exhaust_outlet_temp_c()
        oil_hot = self._effective_oil_hot_temp_c()
        oil_delivery = self._effective_oil_delivery_temp_c()
        oil_return = self._read_float_var(self.oil_inlet_temp_var, 175.0)
        wf_in = self._read_float_var(self.wf_inlet_temp_var, 100.0)
        wf_hot = self._effective_wf_hot_temp_c()
        wf_condense = self._effective_wf_condense_temp_c(wf_in, wf_hot)

        self._paint_stream_path("exhaust_main", "exhaust", exhaust_in, exhaust_out)
        self._paint_stream_path("oil_supply", "oil", oil_hot, oil_delivery)
        self._paint_stream_path("oil_return", "oil", max(oil_return + 10.0, oil_return), oil_return)
        self._paint_stream_path("wf_hot", "working_fluid", max(wf_hot - 12.0, wf_in), wf_hot)
        self._paint_stream_path("wf_reject", "working_fluid", wf_hot, wf_condense)
        self._paint_stream_path("wf_cold", "working_fluid", wf_condense, wf_in)
        for branch_key in [name for name in self.diagram_stream_items if name.startswith("wf_regen_branch_")]:
            self._paint_stream_path(branch_key, "working_fluid", wf_condense, max(wf_condense - 10.0, wf_in))
        self._paint_stream_path("power_export", "power", 1.0, 1.0)
        self._paint_stream_path("power_auxiliary", "power", 1.0, 1.0)
        self._update_stream_particle_colors()

    def _paint_stream_path(self, key: str, fluid_key: str, start_temp_c: float, end_temp_c: float) -> None:
        item_ids = self.diagram_stream_items.get(key)
        if not item_ids or self.process_canvas is None:
            return
        colors = colors_for_temperature_span(fluid_key, start_temp_c, end_temp_c, steps=len(item_ids))
        for item_id, color in zip(item_ids, colors):
            self.process_canvas.itemconfigure(item_id, fill=color)

    def _bind_stage_interactions(self) -> None:
        if self.process_canvas is None:
            return
        canvas = self.process_canvas
        for key in self.diagram_stage_items:
            tag = f"stage_{key}"
            canvas.tag_bind(tag, "<Button-1>", lambda _event, selected_key=key: self._select_equipment_detail(selected_key))
            canvas.tag_bind(tag, "<Enter>", lambda _event: canvas.configure(cursor="hand2"))
            canvas.tag_bind(tag, "<Leave>", lambda _event: canvas.configure(cursor=""))

    def _select_equipment_detail(self, key: str) -> None:
        self.selected_equipment_key = key
        self._refresh_selected_equipment_detail()

    def _refresh_selected_equipment_detail(self) -> None:
        detail = self.current_equipment_details.get(self.selected_equipment_key)
        if detail is None:
            detail = self.current_equipment_details.get("boiler") or build_idle_equipment_details()["boiler"]
        self.selected_equipment_title_var.set(detail.title)
        self.selected_equipment_body_var.set(render_equipment_detail(detail))

    def _stream_points_for_key(self, key: str) -> tuple[tuple[float, float], ...]:
        if self.process_canvas is None:
            return ()
        segments: list[tuple[float, float, float, float]] = []
        for item_id in self.diagram_stream_items.get(key, []):
            coords = self.process_canvas.coords(item_id)
            if len(coords) < 4:
                continue
            segments.append((coords[0], coords[1], coords[-2], coords[-1]))
        return points_from_segments(tuple(segments))

    def _stream_fluid_key(self, key: str) -> str:
        if key.startswith("exhaust"):
            return "exhaust"
        if key.startswith("oil"):
            return "oil"
        if key.startswith("wf"):
            return "working_fluid"
        return "power"

    def _default_stream_speed(self, key: str) -> float:
        if key.startswith("wf_regen_branch_"):
            return 5.5
        fluid_key = self._stream_fluid_key(key)
        speed_map = {
            "exhaust": 10.0,
            "oil": 7.5,
            "working_fluid": 8.5,
            "power": 11.5,
        }
        return speed_map.get(fluid_key, 8.0)

    def _stream_particle_color(self, key: str) -> str:
        if self.process_canvas is not None:
            item_ids = self.diagram_stream_items.get(key, [])
            if item_ids:
                sample_id = item_ids[min(len(item_ids) - 1, max(len(item_ids) // 2, 0))]
                color = self.process_canvas.itemcget(sample_id, "fill")
                if color:
                    return color
        return fluid_gradient(self._stream_fluid_key(key)).hot_color

    def _update_stream_particle_colors(self) -> None:
        if self.process_canvas is None:
            return
        for key, particle_id in self.diagram_stream_particles.items():
            self.process_canvas.itemconfigure(particle_id, fill=self._stream_particle_color(key), outline="")

    def _restart_stream_animation(self) -> None:
        if self.process_canvas is None:
            return
        if self._stream_animation_after_id is not None:
            try:
                self.after_cancel(self._stream_animation_after_id)
            except tk.TclError:
                pass
            self._stream_animation_after_id = None

        canvas = self.process_canvas
        for particle_id in self.diagram_stream_particles.values():
            canvas.delete(particle_id)
        self.diagram_stream_particles = {}
        self.diagram_stream_progress = {}
        self.diagram_stream_speeds = {}

        for key in self.diagram_stream_items:
            points = self._stream_points_for_key(key)
            length = polyline_length(points)
            if length <= 0.0:
                continue
            radius = 4 if key.startswith("wf_regen_branch_") else 5
            x_pos, y_pos = point_along_polyline(points, 0.0)
            particle_id = canvas.create_oval(
                x_pos - radius,
                y_pos - radius,
                x_pos + radius,
                y_pos + radius,
                fill=self._stream_particle_color(key),
                outline="",
            )
            self.diagram_stream_particles[key] = particle_id
            self.diagram_stream_progress[key] = 0.0
            self.diagram_stream_speeds[key] = self._default_stream_speed(key)

        self._animate_stream_particles()

    def _animate_stream_particles(self) -> None:
        if self.process_canvas is None:
            return

        canvas = self.process_canvas
        for key, particle_id in list(self.diagram_stream_particles.items()):
            points = self._stream_points_for_key(key)
            length = polyline_length(points)
            if length <= 0.0:
                continue
            progress = (self.diagram_stream_progress.get(key, 0.0) + self.diagram_stream_speeds.get(key, 8.0)) % length
            self.diagram_stream_progress[key] = progress
            x_pos, y_pos = point_along_polyline(points, progress)
            coords = canvas.coords(particle_id)
            radius = 5.0
            if len(coords) == 4:
                radius = max((coords[2] - coords[0]) / 2.0, 3.0)
            canvas.coords(particle_id, x_pos - radius, y_pos - radius, x_pos + radius, y_pos + radius)

        self._stream_animation_after_id = self.after(90, self._animate_stream_particles)

    def _effective_exhaust_outlet_temp_c(self) -> float:
        raw = self.exhaust_outlet_temp_var.get().strip()
        if raw:
            return float(raw)
        return self._read_float_var(self.stack_min_temp_var, 150.0)

    def _effective_oil_hot_temp_c(self) -> float:
        raw = self.oil_outlet_temp_var.get().strip()
        if raw:
            return float(raw)
        design_driver = self.boiler_driver_var.get()
        if design_driver == BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE.value and self.design_target_var.get().strip():
            return float(self.design_target_var.get())
        return max(self._read_float_var(self.loop_target_delivery_temp_var, 245.0) + 5.0, self._read_float_var(self.oil_inlet_temp_var, 175.0) + 20.0)

    def _effective_oil_delivery_temp_c(self) -> float:
        delivery = self._read_float_var(self.loop_target_delivery_temp_var, 245.0)
        return min(delivery, self._effective_oil_hot_temp_c())

    def _effective_wf_hot_temp_c(self) -> float:
        target = self.orc_target_wf_outlet_var.get().strip()
        if self.orc_heat_mode_var.get() == OrcScreeningHeatMode.SINGLE_PHASE_TEMPERATURE_GAIN.value and target:
            return float(target)
        return self._read_float_var(self.wf_max_outlet_var, 170.0)

    def _effective_wf_condense_temp_c(self, wf_in: float, wf_hot: float) -> float:
        return max(wf_in + 12.0, wf_hot - max((wf_hot - wf_in) * 0.45, 20.0))

    def _read_float_var(self, variable: tk.StringVar, fallback: float) -> float:
        raw = variable.get().strip()
        if not raw:
            return fallback
        try:
            return float(raw)
        except ValueError:
            return fallback

    def _register_rect_stage(
        self,
        key: str,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        title: str,
        fill: str,
        panel_bg: str,
        text_dark: str,
    ) -> None:
        stage_tag = f"stage_{key}"
        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=fill, tags=(stage_tag,))
        self._register_stage_texts(canvas, key, title, (x1 + x2) / 2, y1 - 18, (x1 + x2) / 2, y2 + 22, panel_bg, text_dark, stage_tag=stage_tag)

    def _register_round_rect_stage(
        self,
        key: str,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        title: str,
        fill: str,
        panel_bg: str,
        text_dark: str,
    ) -> None:
        radius = 16
        stage_tag = f"stage_{key}"
        canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline=fill, tags=(stage_tag,))
        canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline=fill, tags=(stage_tag,))
        canvas.create_oval(x1, y1, x1 + radius * 2, y1 + radius * 2, fill=fill, outline=fill, tags=(stage_tag,))
        canvas.create_oval(x2 - radius * 2, y1, x2, y1 + radius * 2, fill=fill, outline=fill, tags=(stage_tag,))
        canvas.create_oval(x1, y2 - radius * 2, x1 + radius * 2, y2, fill=fill, outline=fill, tags=(stage_tag,))
        canvas.create_oval(x2 - radius * 2, y2 - radius * 2, x2, y2, fill=fill, outline=fill, tags=(stage_tag,))
        self._register_stage_texts(canvas, key, title, (x1 + x2) / 2, y1 - 18, (x1 + x2) / 2, y2 + 22, panel_bg, text_dark, stage_tag=stage_tag)

    def _register_capsule_stage(
        self,
        key: str,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        title: str,
        fill: str,
        panel_bg: str,
        text_dark: str,
    ) -> None:
        stage_tag = f"stage_{key}"
        canvas.create_rectangle(x1 + 22, y1, x2 - 22, y2, fill=fill, outline=fill, tags=(stage_tag,))
        canvas.create_oval(x1, y1, x1 + 44, y2, fill=fill, outline=fill, tags=(stage_tag,))
        canvas.create_oval(x2 - 44, y1, x2, y2, fill=fill, outline=fill, tags=(stage_tag,))
        self._register_stage_texts(canvas, key, title, (x1 + x2) / 2, y1 - 18, (x1 + x2) / 2, y2 + 22, panel_bg, text_dark, stage_tag=stage_tag)

    def _register_turbine_stage(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        key: str,
        title: str,
        fill: str,
        panel_bg: str,
        text_dark: str,
    ) -> None:
        stage_tag = f"stage_{key}"
        canvas.create_polygon(x1, y1, x2, y1 + 10, x2, y2 - 10, x1, y2, fill=fill, outline=fill, tags=(stage_tag,))
        self._register_stage_texts(canvas, key, title, (x1 + x2) / 2, y1 - 18, (x1 + x2) / 2, y2 + 22, panel_bg, text_dark, stage_tag=stage_tag)

    def _register_condenser_stage(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        key: str,
        title: str,
        fill: str,
        panel_bg: str,
        text_dark: str,
    ) -> None:
        stage_tag = f"stage_{key}"
        canvas.create_polygon(x1, y1, x2, y1, x2 - 12, y2, x1 + 12, y2, fill=fill, outline=fill, tags=(stage_tag,))
        for dx in [20, 42, 64, 86]:
            canvas.create_line(x1 + dx, y1 + 18, x1 + dx, y2 - 14, fill=panel_bg, width=2, tags=(stage_tag,))
        for cx in [x1 + 28, x1 + 56, x1 + 84]:
            canvas.create_oval(cx - 8, y2 - 8, cx + 8, y2 + 8, outline=panel_bg, width=2, tags=(stage_tag,))
            canvas.create_line(cx - 5, y2, cx + 5, y2, fill=panel_bg, width=2, tags=(stage_tag,))
            canvas.create_line(cx, y2 - 5, cx, y2 + 5, fill=panel_bg, width=2, tags=(stage_tag,))
        self._register_stage_texts(canvas, key, title, (x1 + x2) / 2, y1 - 18, (x1 + x2) / 2, y2 + 16, panel_bg, text_dark, stage_tag=stage_tag)

    def _register_pump_stage(
        self,
        key: str,
        canvas: tk.Canvas,
        cx: int,
        cy: int,
        title: str,
        fill: str,
        panel_bg: str,
        text_dark: str,
    ) -> None:
        stage_tag = f"stage_{key}"
        canvas.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill=panel_bg, outline=fill, width=3, tags=(stage_tag,))
        canvas.create_line(cx - 10, cy + 8, cx + 10, cy - 8, fill=fill, width=3, tags=(stage_tag,))
        canvas.create_rectangle(cx - 18, cy + 14, cx + 18, cy + 20, fill=fill, outline=fill, tags=(stage_tag,))
        self._register_stage_texts(canvas, key, title, cx, cy + 28, cx, cy + 48, panel_bg, text_dark, stage_tag=stage_tag)

    def _draw_boiler_core(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        exhaust_color: str,
        oil_color: str,
        *,
        stage_tag: str | None = None,
    ) -> None:
        tags = (stage_tag,) if stage_tag else ()
        center_x = (x1 + x2) / 2
        canvas.create_line(
            center_x - 10,
            y1 + 24,
            center_x + 8,
            y1 + 56,
            center_x - 10,
            y1 + 88,
            center_x + 8,
            y1 + 120,
            center_x - 10,
            y1 + 152,
            fill=exhaust_color,
            width=3,
            tags=tags,
        )
        canvas.create_line(
            center_x + 10,
            y1 + 24,
            center_x - 8,
            y1 + 56,
            center_x + 10,
            y1 + 88,
            center_x - 8,
            y1 + 120,
            center_x + 10,
            y1 + 152,
            fill=oil_color,
            width=3,
            tags=tags,
        )
        for offset in [44, 76, 108, 140]:
            canvas.create_line(x1 + 18, y1 + offset, x2 - 18, y1 + offset, fill="#dce7ef", width=1, tags=tags)
        canvas.create_text(center_x, y1 + 168, text="multi-pass duty section", fill="#dce7ef", font=("Segoe UI", 6), tags=tags)

    def _draw_heat_exchanger_core(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: str,
        *,
        stage_tag: str | None = None,
    ) -> None:
        tags = (stage_tag,) if stage_tag else ()
        mid_y = (y1 + y2) / 2
        canvas.create_line(
            x1 + 16,
            mid_y,
            x1 + 34,
            mid_y - 14,
            x1 + 52,
            mid_y + 14,
            x1 + 70,
            mid_y - 14,
            x1 + 88,
            mid_y + 14,
            fill=color,
            width=3,
            tags=tags,
        )
        canvas.create_line(x1 + 18, y1 + 12, x2 - 18, y1 + 12, fill="#dce7ef", width=1, tags=tags)
        canvas.create_line(x1 + 18, y2 - 12, x2 - 18, y2 - 12, fill="#dce7ef", width=1, tags=tags)

    def _register_stage_texts(
        self,
        canvas: tk.Canvas,
        key: str,
        title: str,
        title_x: float,
        title_y: float,
        text_x: float,
        text_y: float,
        panel_bg: str,
        text_dark: str,
        *,
        stage_tag: str | None = None,
    ) -> None:
        tags = (stage_tag,) if stage_tag else ()
        canvas.create_text(title_x, title_y, text=title.upper(), fill=text_dark, font=("Segoe UI Semibold", 8), tags=tags)
        primary_id = canvas.create_text(text_x, text_y, text="Awaiting solve", fill=text_dark, font=("Segoe UI Semibold", 8), tags=tags)
        secondary_id = canvas.create_text(text_x, text_y + 14, text="", fill="#5f6f65", font=("Segoe UI", 8), tags=tags)
        status_id = canvas.create_oval(text_x + 48, text_y - 8, text_x + 60, text_y + 4, fill=status_color("idle"), outline="", tags=tags)
        self.diagram_stage_items[key] = {
            "primary": primary_id,
            "secondary": secondary_id,
            "status": status_id,
        }

    def _combo_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, values: list[str], row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", style="Accent.TCombobox").grid(row=row, column=1, sticky="ew", pady=4)
        parent.grid_columnconfigure(1, weight=1)

    def _load_defaults(self) -> None:
        self._apply_wf_preset()
        self._apply_oil_preset()
        self._reset_outputs()
        self._bind_base_state_sync()
        self._bind_dynamic_behavior()
        self._sync_all_state_to_diagram_fields()
        self._refresh_form_state()
        self._apply_process_snapshot(build_empty_process_snapshot())

    def _load_selected_benchmark(self) -> None:
        display_name = self.selected_benchmark_var.get().strip()
        if not display_name:
            messagebox.showinfo("Benchmark", "Lutfen once bir benchmark vakasi secin.")
            return
        benchmark = self.benchmark_cases_by_name[display_name]
        self._apply_screening_case_to_form(benchmark.inputs, benchmark.summary)

    def _save_current_case(self) -> None:
        try:
            case = self._build_case_inputs()
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))
            return
        path = filedialog.asksaveasfilename(
            title="Vaka dosyasini kaydet",
            initialdir=str(DEFAULT_CASES_DIR),
            defaultextension=".whrs.json",
            initialfile=default_saved_case_filename(case.case_name),
            filetypes=[("WHRS case", "*.whrs.json"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        source_label = self.selected_benchmark_var.get().strip() or "ui_form"
        write_saved_case(path, case, source_label=source_label, note=self.benchmark_summary_var.get())
        self.export_status_var.set(f"Vaka kaydedildi: {Path(path).name}")

    def _load_saved_case(self) -> None:
        path = filedialog.askopenfilename(
            title="Vaka dosyasi ac",
            initialdir=str(DEFAULT_CASES_DIR),
            filetypes=[("WHRS case", "*.whrs.json"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        document = read_saved_case(path)
        self.selected_benchmark_var.set("")
        note = document.note or f"Kayitli vaka yuklendi: {Path(path).name}"
        if document.source_label:
            note = f"{note} | source: {document.source_label}"
        self._apply_screening_case_to_form(document.case_inputs, note)
        self.export_status_var.set(f"Vaka yuklendi: {Path(path).name}")

    def _apply_screening_case_to_form(self, case: ScreeningCaseInputs, source_note: str) -> None:
        self.case_name_var.set(case.case_name)
        self.boiler_mode_var.set(case.boiler_mode.value)
        self.boiler_driver_var.set(
            case.boiler_design_driver.value if case.boiler_design_driver is not None else BoilerDesignDriver.TARGET_BOILER_EFFICIENCY.value
        )
        self.stack_min_temp_var.set(self._format_base_value(case.stack_min_temp_c))
        self.closure_tol_var.set(self._format_base_value(case.closure_tolerance_fraction))

        self.exhaust_mass_flow_var.set(self._format_base_value(case.exhaust_mass_flow_kg_s))
        self.exhaust_inlet_temp_var.set(self._format_base_value(case.exhaust_inlet_temp_c))
        self.exhaust_outlet_temp_var.set("" if case.exhaust_outlet_temp_c is None else self._format_base_value(case.exhaust_outlet_temp_c))
        self.exhaust_pressure_var.set(self._format_base_value(case.exhaust_pressure_pa))
        composition_map = {component_id: fraction for component_id, fraction in case.exhaust_components}
        for component_id, variable in self.exhaust_vars.items():
            variable.set(self._format_base_value(composition_map.get(component_id, 0.0)))

        self.oil_name_var.set(case.oil_name)
        self.oil_cp_var.set(self._format_base_value(case.oil_cp_const_j_kg_k))
        self.oil_density_var.set(self._format_base_value(case.oil_density_kg_m3))
        self.oil_max_bulk_var.set(self._format_base_value(case.oil_max_bulk_temp_c))
        self.oil_mass_flow_var.set(self._format_base_value(case.oil_mass_flow_kg_s))
        self.oil_inlet_temp_var.set(self._format_base_value(case.oil_inlet_temp_c))
        self.oil_outlet_temp_var.set("" if case.oil_outlet_temp_c is None else self._format_base_value(case.oil_outlet_temp_c))
        self.loop_mode_var.set(case.loop_mode.value)
        self.loop_heat_loss_var.set(self._format_base_value(case.loop_heat_loss_w))
        self.loop_target_delivery_temp_var.set(self._format_base_value(case.loop_target_delivery_temp_c))
        self.loop_pressure_drop_var.set(self._format_base_value(case.loop_pressure_drop_pa))
        self.loop_pump_eff_var.set(self._format_base_value(case.loop_pump_efficiency))

        self.wf_name_var.set(case.wf_name)
        self.wf_cp_var.set(self._format_base_value(case.wf_cp_const_j_kg_k))
        self.wf_inlet_temp_var.set(self._format_base_value(case.wf_inlet_temp_c))
        self.wf_pressure_var.set(self._format_base_value(case.wf_pressure_pa))
        self.wf_max_outlet_var.set(self._format_base_value(case.wf_max_outlet_temp_c))

        self.orc_heat_mode_var.set(case.orc_heat_mode.value)
        self.orc_target_wf_outlet_var.set(self._format_base_value(case.orc_target_wf_outlet_temp_c))
        self.orc_known_heat_input_var.set(self._format_base_value(case.orc_known_heat_input_w))
        self.orc_min_approach_var.set(self._format_base_value(case.min_orc_approach_k))
        self.orc_power_mode_var.set(case.orc_power_mode.value)
        self.eta_orc_gross_var.set(self._format_base_value(case.eta_orc_gross_target))
        self.gross_power_target_var.set(self._format_base_value(case.gross_electric_power_target_w))

        if case.boiler_design_driver is not None and case.boiler_design_target_si is not None:
            display_target = design_target_display_value(case)
            if display_target is not None:
                self.design_target_var.set(self._format_base_value(display_target))

        self.benchmark_summary_var.set(source_note)
        self._reset_outputs()
        self._sync_all_state_to_diagram_fields()
        self._refresh_form_state()

    def _bind_dynamic_behavior(self) -> None:
        for variable in [
            self.boiler_mode_var,
            self.boiler_driver_var,
            self.loop_mode_var,
            self.orc_heat_mode_var,
            self.orc_power_mode_var,
            self.oil_name_var,
            self.wf_name_var,
        ]:
            variable.trace_add("write", lambda *_: self._refresh_form_state())

    def _apply_oil_preset(self) -> None:
        selected = self.oil_name_var.get()
        if selected == "Manual Oil":
            self._refresh_form_state()
            return
        for item in self.thermal_oils:
            if str(item["display_name"]) == selected:
                self.oil_cp_var.set(f"{float(item['cp_a']) + 2.5 * 100:.0f}")
                self.oil_density_var.set(str(item.get("density_kg_m3", 880.0)))
                self.oil_max_bulk_var.set(str(item.get("max_bulk_temp_c", 320.0)))
                break
        self._refresh_form_state()

    def _apply_wf_preset(self) -> None:
        preset = WORKING_FLUID_PRESETS.get(self.wf_name_var.get())
        if preset is None:
            self._refresh_form_state()
            return
        self.wf_cp_var.set(str(preset.cp_const_j_kg_k))
        self.wf_max_outlet_var.set(str(preset.max_outlet_temp_c))
        self._refresh_form_state()

    def _refresh_form_state(self) -> None:
        current_driver_value = self.boiler_driver_var.get()
        if current_driver_value != self._last_design_target_driver:
            driver = BoilerDesignDriver(current_driver_value)
            self.design_target_var.set(self._format_base_value(design_target_default_value(driver)))
            self._last_design_target_driver = current_driver_value
        state = build_ui_behavior_state(
            BoilerMode(self.boiler_mode_var.get()),
            BoilerDesignDriver(current_driver_value),
            ThermalOilLoopMode(self.loop_mode_var.get()),
            OrcScreeningHeatMode(self.orc_heat_mode_var.get()),
            OrcScreeningPowerMode(self.orc_power_mode_var.get()),
            self.oil_name_var.get(),
            self.wf_name_var.get(),
        )
        self.study_mode_title_var.set(state.study_title)
        self.study_mode_helper_var.set(state.study_helper)
        self.design_target_label_var.set(f"{state.design_target.label} [{state.design_target.unit_hint}]")
        self.design_target_helper_var.set(state.design_target.helper_text)
        self._set_entry_state(self.design_target_entry, state.design_target.enabled)
        self._set_entry_state(self.exhaust_outlet_entry, state.exhaust_outlet_enabled)
        self._set_entry_state(self.oil_outlet_entry, state.oil_outlet_enabled)
        self._set_entry_state(self.loop_heat_loss_entry, state.loop_heat_loss_enabled)
        self._set_entry_state(self.loop_target_delivery_entry, state.loop_target_delivery_enabled)
        self._set_entry_state(self.orc_target_wf_entry, state.orc_target_wf_outlet_enabled)
        self._set_entry_state(self.orc_known_heat_entry, state.orc_known_heat_input_enabled)
        self._set_entry_state(self.orc_efficiency_entry, state.orc_efficiency_enabled)
        self._set_entry_state(self.gross_power_target_entry, state.gross_power_target_enabled)
        for entry in self.oil_property_entries:
            self._set_entry_state(entry, state.oil_manual_properties_enabled)
        for entry in self.wf_property_entries:
            self._set_entry_state(entry, state.wf_manual_properties_enabled)
        self._set_diagram_field_enabled("exhaust_outlet_temp", state.exhaust_outlet_enabled)
        self._set_diagram_field_enabled("oil_outlet_temp", state.oil_outlet_enabled)
        self._set_diagram_field_enabled("loop_heat_loss", state.loop_heat_loss_enabled)
        self._set_diagram_field_enabled("loop_target_delivery_temp", state.loop_target_delivery_enabled)
        self._set_diagram_field_enabled("orc_target_wf_outlet", state.orc_target_wf_outlet_enabled)
        self._set_diagram_field_enabled("orc_known_heat_input", state.orc_known_heat_input_enabled)
        self._set_diagram_field_enabled("eta_orc_gross", state.orc_efficiency_enabled)
        self._set_diagram_field_enabled("gross_power_target", state.gross_power_target_enabled)
        self._set_design_target_field_enabled(state.design_target.enabled)
        self._sync_design_target_field()

    def _set_entry_state(self, entry: ttk.Entry | None, enabled: bool) -> None:
        if entry is None:
            return
        entry.configure(state="normal" if enabled else "disabled")

    def _set_diagram_field_enabled(self, key: str, enabled: bool) -> None:
        field = self.diagram_input_fields.get(key)
        if field is None:
            return
        frame = field["frame"]
        label = field["label"]
        hint = field["hint"]
        entry = field["entry"]
        combo = field["combo"]
        spec = field["spec"]
        bg = "#fffdfa" if enabled else "#ece8df"
        fg = "#17322b" if enabled else "#8e968f"
        frame.configure(bg=bg, highlightbackground=spec.accent_color if enabled else "#b9b9b9", highlightcolor=spec.accent_color if enabled else "#b9b9b9")
        label.configure(bg=bg, fg=fg)
        hint.configure(bg=bg, fg="#6f7d75" if enabled else "#9ca39d")
        entry.configure(state="normal" if enabled else "disabled")
        combo.configure(state="readonly" if enabled else "disabled")

    def _set_design_target_field_enabled(self, enabled: bool) -> None:
        field = self.diagram_design_target_field
        if field is None:
            return
        bg = "#fffdfa" if enabled else "#ece8df"
        fg = "#17322b" if enabled else "#8e968f"
        frame = field["frame"]
        frame.configure(bg=bg, highlightbackground="#123f7a" if enabled else "#b9b9b9", highlightcolor="#123f7a" if enabled else "#b9b9b9")
        field["title"].configure(bg=bg, fg=fg)
        field["helper"].configure(bg=bg, fg="#6f7d75" if enabled else "#9ca39d")
        field["hint"].configure(bg=bg, fg="#6f7d75" if enabled else "#9ca39d")
        field["entry"].configure(state="normal" if enabled else "disabled")
        field["combo"].configure(state="readonly" if enabled else "disabled")

    def _build_case_inputs(self) -> ScreeningCaseInputs:
        for key in self.diagram_input_fields:
            self._commit_diagram_field(key, show_error=True)
        for component in self.diagram_composition_fields:
            self._commit_composition_field(component, show_error=True)
        self._commit_design_target_field(show_error=True)
        components = [(component, float(variable.get())) for component, variable in self.exhaust_vars.items()]
        is_design = self.boiler_mode_var.get() == BoilerMode.DESIGN.value
        driver = BoilerDesignDriver(self.boiler_driver_var.get()) if is_design else None
        design_target_si = None
        if driver is not None:
            raw_target = float(self.design_target_var.get())
            design_target_si = self._convert_design_target_to_si(driver, raw_target)

        return ScreeningCaseInputs(
            case_name=self.case_name_var.get(),
            boiler_mode=BoilerMode(self.boiler_mode_var.get()),
            boiler_design_driver=driver,
            boiler_design_target_si=design_target_si,
            stack_min_temp_c=float(self.stack_min_temp_var.get()),
            closure_tolerance_fraction=float(self.closure_tol_var.get()),
            exhaust_components=components,
            exhaust_mass_flow_kg_s=float(self.exhaust_mass_flow_var.get()),
            exhaust_inlet_temp_c=float(self.exhaust_inlet_temp_var.get()),
            exhaust_outlet_temp_c=float(self.exhaust_outlet_temp_var.get()) if (not is_design and self.exhaust_outlet_temp_var.get().strip()) else None,
            exhaust_pressure_pa=float(self.exhaust_pressure_var.get()),
            oil_name=self.oil_name_var.get(),
            oil_cp_const_j_kg_k=float(self.oil_cp_var.get()),
            oil_density_kg_m3=float(self.oil_density_var.get()),
            oil_max_bulk_temp_c=float(self.oil_max_bulk_var.get()),
            oil_mass_flow_kg_s=float(self.oil_mass_flow_var.get()),
            oil_inlet_temp_c=float(self.oil_inlet_temp_var.get()),
            oil_outlet_temp_c=float(self.oil_outlet_temp_var.get()) if (not is_design and self.oil_outlet_temp_var.get().strip()) else None,
            loop_mode=ThermalOilLoopMode(self.loop_mode_var.get()),
            loop_heat_loss_w=float(self.loop_heat_loss_var.get()),
            loop_target_delivery_temp_c=float(self.loop_target_delivery_temp_var.get()),
            loop_pressure_drop_pa=float(self.loop_pressure_drop_var.get()),
            loop_pump_efficiency=float(self.loop_pump_eff_var.get()),
            wf_name=self.wf_name_var.get(),
            wf_cp_const_j_kg_k=float(self.wf_cp_var.get()),
            wf_inlet_temp_c=float(self.wf_inlet_temp_var.get()),
            wf_pressure_pa=float(self.wf_pressure_var.get()),
            wf_max_outlet_temp_c=float(self.wf_max_outlet_var.get()),
            orc_heat_mode=OrcScreeningHeatMode(self.orc_heat_mode_var.get()),
            orc_target_wf_outlet_temp_c=float(self.orc_target_wf_outlet_var.get()),
            orc_known_heat_input_w=float(self.orc_known_heat_input_var.get()),
            min_orc_approach_k=float(self.orc_min_approach_var.get()),
            orc_power_mode=OrcScreeningPowerMode(self.orc_power_mode_var.get()),
            eta_orc_gross_target=float(self.eta_orc_gross_var.get()),
            gross_electric_power_target_w=float(self.gross_power_target_var.get()),
        )

    def _convert_design_target_to_si(self, driver: BoilerDesignDriver, raw_value: float) -> float:
        if driver in {
            BoilerDesignDriver.MINIMUM_STACK_TEMPERATURE,
            BoilerDesignDriver.TARGET_OIL_OUTLET_TEMPERATURE,
        }:
            return c_to_k(raw_value)
        return raw_value

    def _format_base_value(self, value: float) -> str:
        return f"{value:.10g}"

    def _solve_case(self) -> None:
        try:
            case = self._build_case_inputs()
            result = run_screening_case(case)
        except Exception as exc:
            messagebox.showerror("Solve Error", str(exc))
            return

        self._reset_outputs()
        self.process_var.set(
            f"{case.case_name}  |  Boiler: {case.boiler_mode.value}  |  ORC Heat: {case.orc_heat_mode.value}  |  ORC Power: {case.orc_power_mode.value}"
        )
        self.last_case = case
        self.last_result = result
        try:
            log_screening_case_run(DEFAULT_LOG_PATH, case, result)
            self.export_status_var.set(f"Solve ve log tamamlandi: {DEFAULT_LOG_PATH.name}")
        except Exception as exc:
            self.export_status_var.set(f"Solve tamamlandi, log yazilamadi: {exc}")
        if self.input_snapshot_text is not None:
            self.input_snapshot_text.insert("1.0", self._build_input_snapshot(case))
        self._apply_process_snapshot(build_process_snapshot(result))
        self._fill_from_result(result)

    def _export_markdown_report(self) -> None:
        if self.last_case is None or self.last_result is None:
            messagebox.showinfo("Export", "Lutfen once bir vakayi cozun.")
            return
        path = filedialog.asksaveasfilename(
            title="Markdown raporu kaydet",
            defaultextension=".md",
            initialfile=default_report_filename(self.last_case.case_name, ".md"),
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        report_text = build_screening_markdown_report(self.last_case, self.last_result)
        Path(path).write_text(report_text, encoding="utf-8")
        self.export_status_var.set(f"Markdown raporu kaydedildi: {Path(path).name}")

    def _export_case_bundle(self) -> None:
        if self.last_case is None or self.last_result is None:
            messagebox.showinfo("Export", "Lutfen once bir vakayi cozun.")
            return
        path = filedialog.asksaveasfilename(
            title="JSON bundle kaydet",
            defaultextension=".json",
            initialfile=default_report_filename(self.last_case.case_name, ".json"),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        payload = build_screening_report_payload(self.last_case, self.last_result)
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.export_status_var.set(f"JSON bundle kaydedildi: {Path(path).name}")

    def _apply_process_snapshot(self, snapshot) -> None:
        self.diagram_headline_var.set(snapshot.headline)
        for key in [
            "factory",
            "boiler",
            "oil_pump",
            "heat_exchanger",
            "turbine",
            "generator",
            "regenerator",
            "condenser",
            "organic_pump",
        ]:
            if self.process_canvas is None or key not in self.diagram_stage_items:
                continue
            stage = getattr(snapshot, key)
            items = self.diagram_stage_items[key]
            self.process_canvas.itemconfigure(items["primary"], text=stage.primary_text)
            self.process_canvas.itemconfigure(items["secondary"], text=stage.secondary_text)
            self.process_canvas.itemconfigure(items["status"], fill=status_color(stage.status))

    def _fill_from_result(self, result) -> None:
        self.current_equipment_details = build_equipment_details(result)
        self._refresh_selected_equipment_detail()
        module_results = [
            ("Boiler", result.boiler_result),
            ("Oil Loop", result.loop_result),
            ("ORC Heat", result.orc_heat_result),
            ("ORC Power", result.orc_power_result),
        ]

        summary_lines: list[str] = []
        diagnostics_lines: list[str] = []
        guidance_text = render_operator_guidance(build_operator_guidance(result))

        for module_name, envelope in module_results:
            if envelope is None:
                continue
            summary_lines.append(f"[{module_name}] status = {envelope.status}")
            if envelope.blocked_state.blocked:
                summary_lines.append(f"  BLOCKED: {envelope.blocked_state.reason}")
                if envelope.blocked_state.suggested_action:
                    summary_lines.append(f"  Suggested action: {envelope.blocked_state.suggested_action}")
            for metric in envelope.values.values():
                formatted = self._format_metric(metric.key, metric.value_si)
                summary_lines.append(f"  {metric.display_name}: {formatted}")
                if metric.key in self.kpi_labels:
                    self.kpi_labels[metric.key].set(formatted)
            if envelope.warnings:
                summary_lines.append("  Warnings:")
                for warning in envelope.warnings:
                    summary_lines.append(f"    - {warning.code}: {warning.message}")

            diagnostics_lines.append(f"[{module_name}]")
            diagnostics_lines.append(f"status = {envelope.status}")
            diagnostics_lines.append(f"metadata = {envelope.metadata}")
            if envelope.blocked_state.blocked:
                diagnostics_lines.append(f"blocked = {envelope.blocked_state.reason}")
                if envelope.blocked_state.suggested_action:
                    diagnostics_lines.append(f"suggested_action = {envelope.blocked_state.suggested_action}")
            if envelope.assumptions:
                diagnostics_lines.append("assumptions:")
                for assumption in envelope.assumptions:
                    diagnostics_lines.append(f"  - {assumption.code}: {assumption.message}")
            if envelope.calc_trace:
                diagnostics_lines.append("calc_trace:")
                for trace in envelope.calc_trace:
                    diagnostics_lines.append(f"  - {trace.step}: {trace.message} | {trace.value_snapshot}")
            diagnostics_lines.append("")

        if self.guidance_text is not None:
            self.guidance_text.insert("1.0", guidance_text)
        self.summary_text.insert("1.0", "\n".join(summary_lines) if summary_lines else "No result.")
        self.diagnostics_text.insert("1.0", "\n".join(diagnostics_lines) if diagnostics_lines else "No diagnostics.")

    def _build_input_snapshot(self, case: ScreeningCaseInputs) -> str:
        lines = [
            f"case_name = {case.case_name}",
            f"boiler_mode = {case.boiler_mode.value}",
            f"boiler_design_driver = {case.boiler_design_driver.value if case.boiler_design_driver else '-'}",
            f"boiler_design_target_si = {case.boiler_design_target_si if case.boiler_design_target_si is not None else '-'}",
            f"stack_min_temp_c = {case.stack_min_temp_c}",
            "",
            f"exhaust_mass_flow_kg_s = {case.exhaust_mass_flow_kg_s}",
            f"exhaust_inlet_temp_c = {case.exhaust_inlet_temp_c}",
            f"exhaust_outlet_temp_c = {case.exhaust_outlet_temp_c if case.exhaust_outlet_temp_c is not None else '-'}",
            f"oil_name = {case.oil_name}",
            f"oil_mass_flow_kg_s = {case.oil_mass_flow_kg_s}",
            f"oil_inlet_temp_c = {case.oil_inlet_temp_c}",
            f"oil_outlet_temp_c = {case.oil_outlet_temp_c if case.oil_outlet_temp_c is not None else '-'}",
            f"loop_mode = {case.loop_mode.value}",
            f"loop_target_delivery_temp_c = {case.loop_target_delivery_temp_c}",
            f"orc_heat_mode = {case.orc_heat_mode.value}",
            f"orc_power_mode = {case.orc_power_mode.value}",
            "",
            "exhaust_composition =",
        ]
        lines.extend(f"  - {component}: {fraction}" for component, fraction in case.exhaust_components)
        return "\n".join(lines)

    def _format_metric(self, key: str, value: float) -> str:
        if key.endswith("_w"):
            return f"{value/1000.0:,.1f} kW"
        if key.endswith("_k"):
            return f"{value:,.2f} K"
        if key.startswith("eta_") or key.endswith("_ratio"):
            return f"{100.0 * value:,.2f} %"
        return f"{value:,.3f}"

    def _reset_outputs(self) -> None:
        self.last_case = None
        self.last_result = None
        self.current_equipment_details = build_idle_equipment_details()
        for var in self.kpi_labels.values():
            var.set("--")
        self.diagram_headline_var.set("Solve a case to populate the process view.")
        self.process_var.set("Exhaust -> Boiler -> Oil Loop -> ORC Heater -> Gross Power")
        self.export_status_var.set("Henuz export olusturulmadi.")
        if self.input_snapshot_text is not None:
            self.input_snapshot_text.delete("1.0", "end")
        if self.guidance_text is not None:
            self.guidance_text.delete("1.0", "end")
        self.summary_text.delete("1.0", "end")
        self.diagnostics_text.delete("1.0", "end")
        self._apply_process_snapshot(build_empty_process_snapshot())
        self._refresh_selected_equipment_detail()

    def destroy(self) -> None:
        if self._stream_animation_after_id is not None:
            try:
                self.after_cancel(self._stream_animation_after_id)
            except tk.TclError:
                pass
            self._stream_animation_after_id = None
        super().destroy()


def launch_app() -> None:
    app = WHRSOrcApp()
    app.mainloop()
