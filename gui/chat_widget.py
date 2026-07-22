"""Chat display widget for Dulus GUI.

Provides a scrollable chat view with message bubbles, markdown-like rendering,
code blocks with copy buttons, tool execution pills, and a typing indicator.
"""
from __future__ import annotations

import re
import tkinter as tk
import webbrowser
from datetime import datetime
from typing import Callable

try:
    import customtkinter as ctk
except ImportError:
    raise ImportError("customtkinter is required. Install: pip install customtkinter")

from gui.themes import get_theme

# ── Theme constants (loaded from active theme) ──────────────────────────────
_t = get_theme()
BG_COLOR = _t["bg"]
CARD_COLOR = _t["card"]
ACCENT_COLOR = _t["accent"]
ACCENT_HOVER = _t["accent_hover"]
TEXT_COLOR = _t["text"]
TEXT_DIM = _t["dim"]
USER_BUBBLE = _t["user_bubble"]
ASSISTANT_BUBBLE = _t["assistant_bubble"]
CODE_BG = _t["code_bg"]
BORDER_COLOR = _t["border"]

# Tag colors (updated by apply_theme)
TAG_BOLD_COLOR = _t.get("text", "#ffffff")
TAG_CODE_COLOR = _t.get("dim", "#c9d1d9")
TAG_ITALIC_COLOR = _t.get("dim", "#bbbbbb")

FONT_FAMILY = "Segoe UI"
FONT_NORMAL = (FONT_FAMILY, 13)
FONT_BOLD = (FONT_FAMILY, 13, "bold")
FONT_SMALL = (FONT_FAMILY, 11)
FONT_CODE = ("Consolas", 12)
FONT_TIMESTAMP = (FONT_FAMILY, 10)


def _sanitize_markdown(text: str) -> str:
    """Escape HTML-like chars so tkinter Text widget stays safe."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ChatWidget(ctk.CTkFrame):
    """Scrollable chat widget with message bubbles and rich formatting."""

    def __init__(
        self,
        master,
        on_copy_callback: Callable | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.on_copy = on_copy_callback
        self._message_frames: list[ctk.CTkFrame] = []
        self._current_bubble_text: ctk.CTkTextbox | None = None
        self._current_bubble_is_user: bool = False
        self._current_bubble_outer: ctk.CTkFrame | None = None

        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Scrollable container
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_fg_color=BORDER_COLOR,
            scrollbar_button_color=ACCENT_COLOR,
            scrollbar_button_hover_color=ACCENT_HOVER,
        )
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._scroll.grid_columnconfigure(0, weight=1)

        # Inner frame where messages live
        self._container = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._container.pack(fill="both", expand=True)
        self._container.grid_columnconfigure(0, weight=1)

        # Thinking indicator (hidden by default)
        self._thinking_frame = ctk.CTkFrame(
            self._container, fg_color=ASSISTANT_BUBBLE, corner_radius=12
        )
        self._thinking_label = ctk.CTkLabel(
            self._thinking_frame,
            text="🌀  NEMESIS réfléchit…",
            font=FONT_NORMAL,
            text_color=ACCENT_COLOR,
        )
        self._thinking_label.pack(padx=16, pady=10)

    # ── Public API ──────────────────────────────────────────────────────────

    def add_user_message(self, text: str) -> None:
        """Add a user message bubble on the right."""
        self._hide_thinking()
        self._finish_current_stream()

        bubble, txt = self._create_bubble(
            text=text,
            is_user=True,
            timestamp=datetime.now().strftime("%H:%M"),
        )
        bubble.pack(anchor="e", padx=12, pady=(6, 2), fill="x")
        self._message_frames.append(bubble)
        self._scroll_to_bottom()

    def add_assistant_message(self, text: str) -> None:
        """Start a new assistant message bubble on the left."""
        self._hide_thinking()
        self._finish_current_stream()

        bubble, txt = self._create_bubble(
            text=text,
            is_user=False,
            timestamp=datetime.now().strftime("%H:%M"),
        )
        bubble.pack(anchor="w", padx=12, pady=(6, 2), fill="x")
        self._message_frames.append(bubble)
        self._current_bubble_text = txt
        self._current_bubble_is_user = False
        self._current_bubble_outer = bubble
        self._scroll_to_bottom()

    def append_to_last_message(self, text: str) -> None:
        """Append text to the current assistant bubble (streaming)."""
        if self._current_bubble_text is None or self._current_bubble_is_user:
            self.add_assistant_message(text)
            return

        widget = self._current_bubble_text
        widget.configure(state="normal")
        current = widget.get("1.0", "end-1c")
        widget.delete("1.0", "end")
        self._render_formatted(widget, current + text)
        self._adjust_text_height(widget)
        widget.configure(state="disabled")
        self._scroll_to_bottom()

    def add_tool_indicator(self, name: str, status: str = "running", details: str = "") -> None:
        """Show a collapsible tool card with status, details and result."""
        self._hide_thinking()
        running = status == "running"
        card = ctk.CTkFrame(
            self._container,
            fg_color=CODE_BG if running else "#10261b",
            corner_radius=10,
            border_width=1,
            border_color=ACCENT_COLOR if running else "#4ade80",
        )
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(5, 2))
        icon = "◌" if running else "✓"
        color = ACCENT_COLOR if running else "#4ade80"
        title = ctk.CTkLabel(row, text=f"{icon}  {name}", font=FONT_SMALL, text_color=color)
        title.pack(side="left")
        toggle = ctk.CTkButton(row, text="＋", width=24, height=22, fg_color="transparent",
                               hover_color=BORDER_COLOR, text_color=TEXT_DIM, corner_radius=6)
        toggle.pack(side="right")
        body = ctk.CTkLabel(card, text=details or "", justify="left", anchor="w",
                            font=(FONT_FAMILY, 10), text_color=TEXT_DIM, wraplength=720)
        expanded = bool(details)
        if expanded:
            body.pack(fill="x", padx=12, pady=(0, 7))
            toggle.configure(text="−")
        def flip():
            nonlocal expanded
            expanded = not expanded
            if expanded:
                body.pack(fill="x", padx=12, pady=(0, 7)); toggle.configure(text="−")
            else:
                body.pack_forget(); toggle.configure(text="＋")
        toggle.configure(command=flip)
        if self._current_bubble_outer is not None:
            card.pack(before=self._current_bubble_outer, anchor="w", padx=20, pady=(2, 4))
        else:
            card.pack(anchor="w", padx=20, pady=(2, 4))
        self._message_frames.append(card)
        self._scroll_to_bottom()

    def show_thinking(self) -> None:
        """Show the 'thinking' indicator at the bottom."""
        self._thinking_frame.pack(anchor="w", padx=12, pady=6, fill="x")
        self._scroll_to_bottom()

    def hide_thinking(self) -> None:
        """Hide the thinking indicator."""
        self._hide_thinking()

    def clear_chat(self) -> None:
        """Remove all messages and reset state."""
        self._finish_current_stream()
        for w in self._message_frames:
            w.destroy()
        self._message_frames.clear()
        self._current_bubble_text = None
        self._current_bubble_is_user = False
        self._hide_thinking()

    def load_messages(self, messages: list[dict]) -> None:
        """Bulk load messages into the chat view without repetitive scrolling."""
        self.clear_chat()
        
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            
            # Skip system/soul messages and empty ones
            if role == "system" or not content:
                continue
            
            is_user = (role == "user")
            display_text = content
            if role == "assistant" and m.get("thinking"):
                display_text = f"*[Pensamiento]*\n{m['thinking']}\n\n{content}"
            elif role == "thinking":
                display_text = f"*[Pensamiento]*\n{content}"
                is_user = False
                
            bubble, txt = self._create_bubble(
                text=display_text,
                is_user=is_user,
                timestamp=m.get("timestamp", datetime.now().strftime("%H:%M")),
            )
            anchor = "e" if is_user else "w"
            bubble.pack(anchor=anchor, padx=12, pady=(6, 2), fill="x")
            self._message_frames.append(bubble)
        
        # Only one scroll at the end (safe access)
        def _final_scroll():
            try:
                canvas = getattr(self._scroll, "_parent_canvas", None)
                if canvas:
                    canvas.update_idletasks()
                    canvas.yview_moveto(1.0)
            except: pass
        self.after(100, _final_scroll)

    def apply_theme(self) -> None:
        """Re-apply current theme colors to existing widgets."""
        t = get_theme()
        global BG_COLOR, CARD_COLOR, ACCENT_COLOR, ACCENT_HOVER, TEXT_COLOR, TEXT_DIM
        global USER_BUBBLE, ASSISTANT_BUBBLE, CODE_BG, BORDER_COLOR
        global TAG_BOLD_COLOR, TAG_CODE_COLOR, TAG_ITALIC_COLOR
        BG_COLOR = t["bg"]
        CARD_COLOR = t["card"]
        ACCENT_COLOR = t["accent"]
        ACCENT_HOVER = t["accent_hover"]
        TEXT_COLOR = t["text"]
        TEXT_DIM = t["dim"]
        USER_BUBBLE = t["user_bubble"]
        ASSISTANT_BUBBLE = t["assistant_bubble"]
        CODE_BG = t["code_bg"]
        BORDER_COLOR = t["border"]
        TAG_BOLD_COLOR = t["text"]
        TAG_CODE_COLOR = t["dim"]
        TAG_ITALIC_COLOR = t["dim"]

        self.configure(fg_color="transparent")
        self._scroll.configure(
            fg_color=t["bg"],
            scrollbar_fg_color=t["border"],
            scrollbar_button_color=t["accent"],
            scrollbar_button_hover_color=t["accent_hover"],
        )
        self._container.configure(fg_color=t["bg"])
        self._thinking_frame.configure(fg_color=t["assistant_bubble"])
        self._thinking_label.configure(text_color=t["accent"])
        # Recolor existing message bubbles
        for outer in self._message_frames:
            if hasattr(outer, "_bubble"):
                new_fg = t["user_bubble"] if outer._is_user else t["assistant_bubble"]
                outer._bubble.configure(fg_color=new_fg)
                for child in outer._bubble.winfo_children():
                    if isinstance(child, ctk.CTkTextbox):
                        child.configure(text_color=t["text"])
                    elif isinstance(child, ctk.CTkLabel):
                        child.configure(text_color=t["dim"])
        
        self.update_idletasks()

    # ── Internal helpers ────────────────────────────────────────────────────

    def _hide_thinking(self) -> None:
        self._thinking_frame.pack_forget()

    def _finish_current_stream(self) -> None:
        """Lock the current bubble so future appends start a new one."""
        if self._current_bubble_text is not None:
            self._current_bubble_text = None
            self._current_bubble_is_user = False
            self._current_bubble_outer = None

    def _scroll_to_bottom(self) -> None:
        """Auto-scroll to the latest message."""
        def _do_scroll():
            try:
                canvas = getattr(self._scroll, "_parent_canvas", None)
                if canvas:
                    canvas.yview_moveto(1.0)
                else:
                    # fallback for different customtkinter versions
                    self._scroll._scrollbar._command("moveto", 1.0)
            except Exception:
                pass
        self.after(50, _do_scroll)

    def _create_bubble(
        self, text: str, is_user: bool, timestamp: str
    ) -> tuple[ctk.CTkFrame, ctk.CTkTextbox]:
        """Create a message bubble frame with formatted text widget inside."""
        fg = USER_BUBBLE if is_user else ASSISTANT_BUBBLE
        anchor = "e" if is_user else "w"

        # Outer frame for alignment
        outer = ctk.CTkFrame(self._container, fg_color="transparent")
        outer.grid_columnconfigure(0, weight=1 if not is_user else 0)
        outer.grid_columnconfigure(1, weight=0 if not is_user else 1)

        # Bubble frame
        bubble = ctk.CTkFrame(outer, fg_color=fg, corner_radius=14)
        outer._bubble = bubble
        outer._is_user = is_user
        if is_user:
            bubble.grid(row=0, column=1, sticky="e", padx=(80, 0))
        else:
            bubble.grid(row=0, column=0, sticky="w", padx=(0, 80))

        # Timestamp label
        ts_label = ctk.CTkLabel(
            bubble,
            text=timestamp,
            font=FONT_TIMESTAMP,
            text_color=TEXT_DIM,
        )
        ts_label.pack(anchor="nw" if not is_user else "ne", padx=12, pady=(6, 0))

        # Text widget for formatted content
        txt = ctk.CTkTextbox(
            bubble,
            fg_color="transparent",
            text_color=TEXT_COLOR,
            font=FONT_NORMAL,
            wrap="word",
            state="disabled",
            activate_scrollbars=False,
            height=20,
            width=500, # Initial width
            corner_radius=0,
        )
        txt.pack(fill="both", expand=True, padx=12, pady=(2, 10))
        txt.configure(state="normal")
        self._render_formatted(txt, text)
        txt.configure(state="disabled")

        # Dynamic height adjustment
        self._adjust_text_height(txt)

        return outer, txt

    def _adjust_text_height(self, txt: ctk.CTkTextbox) -> None:
        """Dynamic height based on content lines."""
        content = txt.get("1.0", "end-1c")
        if not content:
            txt.configure(height=40)
            return
        # Improved line counting: detect actual text lines
        # and factor in wrapping (approx match to bubble width)
        # We increase the chars-per-line to 65 since we made it wider
        wrapped = sum((len(line) // 65) + 1 for line in content.split("\n"))
        # Add a small buffer to prevent scrollbars (26px per line is safer than 24)
        height = max(40, min(1200, wrapped * 26 + 10))
        txt.configure(height=height)

    def _render_formatted(self, txt: ctk.CTkTextbox, text: str) -> None:
        """Parse and insert markdown-like formatting into a CTkTextbox.

        NOTE: CTkTextbox forbids 'font' in tag_config, so we use colors only.
        """
        txt.delete("1.0", "end")
        try:
            # CTkTextbox does not allow 'font' in tag_config — use foreground only
            txt.tag_config("bold", foreground=TAG_BOLD_COLOR)
            txt.tag_config("code", foreground=TAG_CODE_COLOR)
            txt.tag_config("code_block", foreground=TAG_CODE_COLOR)
            txt.tag_config("italic", foreground=TAG_ITALIC_COLOR)
            txt.tag_config("heading", foreground=ACCENT_COLOR)
            txt.tag_config("link", foreground=ACCENT_COLOR, underline=True)
            txt.tag_bind("link", "<Button-1>", lambda e: webbrowser.open(e.widget.tag_cget("link", "url") if False else "https://www.google.com"))
        except Exception:
            # Fallback: tags unsupported, render plain text
            txt.insert("end", text)
            return

        # Simple regex-based parsing
        # Process code blocks first (```...```)
        parts = re.split(r"(```(?:[\w]*\n)?[\s\S]*?```)", text)

        idx = 0
        for part in parts:
            if part.startswith("```") and part.endswith("```"):
                # Extract language and code
                inner = part[3:-3]
                lang = ""
                if "\n" in inner:
                    first, rest = inner.split("\n", 1)
                    first = first.strip()
                    if first and " " not in first:
                        lang = first
                        inner = rest
                    else:
                        inner = first + "\n" + rest if rest else first
                self._insert_code_block(txt, inner.strip(), lang)
            else:
                self._insert_inline_formatted(txt, part)
            idx += 1

    def _insert_code_block(self, txt: ctk.CTkTextbox, code: str, lang: str = "") -> None:
        """Insert a code block with real Copy and Save actions."""
        txt.insert("end", "\n")
        if lang:
            txt.insert("end", f"  {lang}\n", "code_block")
        txt.insert("end", code, "code_block")
        txt.insert("end", "\n")
        bar = tk.Frame(txt, bg=CODE_BG)
        def copy_code():
            try:
                txt.clipboard_clear(); txt.clipboard_append(code); txt.update()
            except Exception: pass
        def save_code():
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(title="Enregistrer le code", defaultextension=".txt",
                                                filetypes=[("Fichier texte", "*.txt"), ("Tous les fichiers", "*.*")])
            if path:
                try: Path(path).write_text(code, encoding="utf-8")
                except Exception: pass
        tk.Button(bar, text="Copier", command=copy_code, relief="flat", bg=CODE_BG,
                  fg=TEXT_DIM, activebackground=ACCENT_COLOR, activeforeground=BG_COLOR).pack(side="left", padx=2)
        tk.Button(bar, text="Enregistrer", command=save_code, relief="flat", bg=CODE_BG,
                  fg=TEXT_DIM, activebackground=ACCENT_COLOR, activeforeground=BG_COLOR).pack(side="left", padx=2)
        try: txt.window_create("end", window=bar)
        except Exception: pass
        txt.insert("end", "\n")

    def _insert_inline_formatted(self, txt: ctk.CTkTextbox, text: str) -> None:
        """Process inline bold, italic, and inline code within a text segment."""
        # Headings and bullet lines get a visual hierarchy.
        lines = text.splitlines(True)
        if len(lines) > 1:
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    txt.insert("end", line, "heading")
                elif stripped.startswith(("- ", "* ", "• ")):
                    txt.insert("end", "  • " + stripped[2:])
                else:
                    self._insert_inline_formatted(txt, line.rstrip("\n"))
                    if line.endswith("\n"): txt.insert("end", "\n")
            return
        # Pattern order: bold **text**, italic *text*, inline `code`, links [title](url)
        pattern = re.compile(r"(\*\*.*?\*\*|\*.*?\*|`.+?`|\[[^\]]+\]\(https?://[^)]+\))")
        pos = 0
        for m in pattern.finditer(text):
            # Text before match
            if m.start() > pos:
                txt.insert("end", text[pos:m.start()])
            token = m.group(0)
            if token.startswith("**") and token.endswith("**"):
                txt.insert("end", token[2:-2], "bold")
            elif token.startswith("*") and token.endswith("*"):
                txt.insert("end", token[1:-1], "italic")
            elif token.startswith("`") and token.endswith("`"):
                txt.insert("end", token[1:-1], "code")
            elif token.startswith("[") and "](" in token:
                label, url = token[1:].split("](", 1)
                url = url.rstrip(")")
                start_index = txt.index("end")
                txt.insert("end", label, "link")
                # Bind this specific range to the URL.
                tag = f"link_{start_index.replace('.', '_')}"
                txt.tag_add(tag, start_index, "end-1c")
                txt.tag_config(tag, foreground=ACCENT_COLOR, underline=True)
                txt.tag_bind(tag, "<Button-1>", lambda e, u=url: webbrowser.open(u))
            pos = m.end()
        if pos < len(text):
            txt.insert("end", text[pos:])
