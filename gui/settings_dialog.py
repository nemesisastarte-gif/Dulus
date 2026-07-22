"""Paramètres popup for Dulus GUI."""
from __future__ import annotations

import os
from typing import Optional

import customtkinter as ctk

from config import save_config
from gui.themes import list_themes, set_theme

THEME = {
    "bg": "#1a1a2e",
    "card": "#16213e",
    "accent": "#00BCD4",
    "accent_hover": "#00acc1",
    "text": "#eaeaea",
    "dim": "#888888",
    "border": "#2a2a4a",
}

FONT_FAMILY = "Segoe UI"


def _build_model_list() -> list[str]:
    """Build list of provider/model strings from PROVIDERS registry."""
    try:
        from providers import PROVIDERS
        models: list[str] = []
        for pname, pmeta in PROVIDERS.items():
            for m in pmeta.get("models", []):
                models.append(f"{pname}/{m}")
        return sorted(models) if models else ["kimi/kimi-k2.5"]
    except Exception:
        return [
            "kimi/kimi-k2.5",
            "openai/gpt-4o",
            "anthropic/claude-3-5-sonnet",
            "deepseek/deepseek-chat",
            "ollama/llama3.3",
        ]


class ParamètresDialog(ctk.CTkToplevel):
    """Floating settings window."""

    def __init__(self, master, config: dict) -> None:
        super().__init__(master)
        self.config = config
        self.title("Paramètres")
        self.geometry("480x520")
        self.configure(fg_color=THEME["bg"])
        self.transient(master)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Header
        ctk.CTkLabel(
            self,
            text="⚙ Paramètres",
            font=(FONT_FAMILY, 18, "bold"),
            text_color=THEME["accent"],
        ).pack(pady=(20, 15))

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", width=440)
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        # Modèle
        ctk.CTkLabel(scroll, text="Modèle", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(10, 2))
        self.model_var = ctk.StringVar(value=config.get("model", "kimi/kimi-k2.5"))
        models = _build_model_list()
        ctk.CTkOptionMenu(scroll, values=models, variable=self.model_var, fg_color=THEME["card"]).pack(fill="x", pady=2)

        # Thinking
        ctk.CTkLabel(scroll, text="Niveau de réflexion", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        think_val = {0: "off", 1: "min", 2: "med", 3: "max", 4: "raw"}.get(config.get("thinking", 0), "off")
        self.think_var = ctk.StringVar(value=think_val)
        ctk.CTkOptionMenu(scroll, values=["off", "min", "med", "max", "raw"], variable=self.think_var, fg_color=THEME["card"]).pack(fill="x", pady=2)

        # Verbose
        ctk.CTkLabel(scroll, text="Mode détaillé", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.verbose_var = ctk.BooleanVar(value=config.get("verbose", False))
        ctk.CTkSwitch(scroll, text="Activer la sortie détaillée", variable=self.verbose_var, progress_color=THEME["accent"]).pack(anchor="w", pady=2)

        # Apparence mode
        ctk.CTkLabel(scroll, text="Apparence", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.appearance_var = ctk.StringVar(value=config.get("appearance", "Dark"))
        ctk.CTkOptionMenu(scroll, values=["Dark", "Light", "System"], variable=self.appearance_var, fg_color=THEME["card"]).pack(fill="x", pady=2)

        # Color theme
        ctk.CTkLabel(scroll, text="Thème de couleurs", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.theme_var = ctk.StringVar(value=config.get("theme", "midnight"))
        ctk.CTkOptionMenu(scroll, values=list_themes(), variable=self.theme_var, fg_color=THEME["card"]).pack(fill="x", pady=2)

        # API Key (masked)
        ctk.CTkLabel(scroll, text="Clé API (provider actif)", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.api_var = ctk.StringVar()
        ctk.CTkEntry(scroll, textvariable=self.api_var, show="●", fg_color=THEME["card"], text_color=THEME["text"]).pack(fill="x", pady=2)

        # Sections avancées — regroupées comme les interfaces d'agents modernes.
        ctk.CTkLabel(scroll, text="Permissions", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(18, 2))
        self.permission_var = ctk.StringVar(value=self.config.get("permission_mode", "auto"))
        ctk.CTkOptionMenu(scroll, values=["auto", "manual", "accept-all"], variable=self.permission_var, fg_color=THEME["card"]).pack(fill="x", pady=2)

        ctk.CTkLabel(scroll, text="Outils", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.tools_var = ctk.BooleanVar(value=not self.config.get("no_tools", False))
        ctk.CTkSwitch(scroll, text="Activer les appels d’outils", variable=self.tools_var, progress_color=THEME["accent"]).pack(anchor="w", pady=2)

        ctk.CTkLabel(scroll, text="Mémoire", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.memory_var = ctk.BooleanVar(value=self.config.get("mem_palace", True))
        ctk.CTkSwitch(scroll, text="Activer la mémoire persistante", variable=self.memory_var, progress_color=THEME["accent"]).pack(anchor="w", pady=2)

        ctk.CTkLabel(scroll, text="Réseau", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.web_var = ctk.BooleanVar(value=not self.config.get("no_web", False))
        ctk.CTkSwitch(scroll, text="Autoriser les outils Web", variable=self.web_var, progress_color=THEME["accent"]).pack(anchor="w", pady=2)

        ctk.CTkLabel(scroll, text="Avancé", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.compact_var = ctk.BooleanVar(value=self.config.get("auto_compact", True))
        ctk.CTkSwitch(scroll, text="Compacter automatiquement le contexte", variable=self.compact_var, progress_color=THEME["accent"]).pack(anchor="w", pady=2)

        ctk.CTkLabel(scroll, text="Mode d’interface", font=(FONT_FAMILY, 12, "bold"), text_color=THEME["text"]).pack(anchor="w", pady=(15, 2))
        self.gui_mode_var = ctk.StringVar(value=self.config.get("gui_mode", "simple"))
        ctk.CTkOptionMenu(scroll, values=["simple", "developer"], variable=self.gui_mode_var, fg_color=THEME["card"]).pack(fill="x", pady=2)
        ctk.CTkLabel(scroll, text="Le mode developer affiche les événements et détails d’outils.", font=(FONT_FAMILY, 10), text_color=THEME["dim"]).pack(anchor="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(
            btn_frame,
            text="Annuler",
            fg_color=THEME["border"],
            hover_color="red",
            command=self.destroy,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Enregistrer",
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            command=self._save,
        ).pack(side="right", padx=5)

    def _save(self) -> None:
        self.config["model"] = self.model_var.get()
        think_map = {"off": 0, "min": 1, "med": 2, "max": 3, "raw": 4}
        self.config["thinking"] = think_map.get(self.think_var.get(), 0)
        self.config["verbose"] = self.verbose_var.get()
        self.config["permission_mode"] = self.permission_var.get()
        self.config["no_tools"] = not self.tools_var.get()
        self.config["mem_palace"] = self.memory_var.get()
        self.config["no_web"] = not self.web_var.get()
        self.config["auto_compact"] = self.compact_var.get()
        self.config["gui_mode"] = self.gui_mode_var.get()
        self.config["appearance"] = self.appearance_var.get()
        self.config["theme"] = self.theme_var.get()
        ctk.set_appearance_mode(self.appearance_var.get())
        # Notify parent to apply color theme
        if hasattr(self.master, "apply_theme"):
            self.master.apply_theme(self.theme_var.get())
        key = self.api_var.get().strip()
        if key:
            pname = self.config.get("model", "").split("/")[0]
            if pname:
                self.config[f"{pname}_api_key"] = key
        try:
            save_config(self.config)
        except Exception:
            pass
        self.destroy()
