from __future__ import annotations

import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from blog_agent.config import Settings
from blog_agent.draft_service import DraftResult, generate_body as create_body
from blog_agent.draft_service import generate_outline as create_outline
from blog_agent.naver_oauth import NaverLogin, NaverProfile
from blog_agent.profiles import THEMES, ThemeProfileStore


APP_TITLE = "Blog Draft Agent"

THEMES_UI = {
    "dark": {
        "bg": "#111827",
        "surface": "#182234",
        "card": "#1f2a3d",
        "field": "#111c2d",
        "border": "#31415c",
        "text": "#edf4ff",
        "muted": "#9db0c9",
        "accent": "#33d6b3",
        "accent_text": "#06211c",
        "danger": "#ff8095",
    },
    "light": {
        "bg": "#f3f6fb",
        "surface": "#ffffff",
        "card": "#ffffff",
        "field": "#f7f9fd",
        "border": "#d4deec",
        "text": "#172033",
        "muted": "#617088",
        "accent": "#0ba98b",
        "accent_text": "#ffffff",
        "danger": "#c33351",
    },
}


def resource_path(relative_path: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / relative_path


class BlogDraftAgent(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1460x920")
        self.minsize(1160, 760)
        icon_path = resource_path("assets/blog-draft-agent-logo.ico")
        if icon_path.exists():
            self.iconbitmap(default=str(icon_path))

        self.settings = Settings.load()
        self.photos: list[Path] = []
        self.naver_profile: NaverProfile | None = None
        self.style_store = ThemeProfileStore()
        self.preview_images: list[ImageTk.PhotoImage] = []
        self.theme_name = "dark"
        self.last_image_analysis = ""

        self.topic_var = tk.StringVar()
        self.theme_var = tk.StringVar(value="맛집 후기")
        self.status_var = tk.StringVar(value="1단계에서 글 구성안을 만든 뒤, 2단계에서 완성 본문을 작성하세요.")
        self.naver_status_var = tk.StringVar(value="네이버: 연결 안 됨")

        self._configure_style()
        self._build_ui()
        self._apply_theme()

    @property
    def colors(self) -> dict[str, str]:
        return THEMES_UI[self.theme_name]

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame")
        style.configure("Card.TFrame")
        style.configure("Title.TLabel", font=("Malgun Gothic", 16, "bold"))
        style.configure("Section.TLabel", font=("Malgun Gothic", 11, "bold"))
        style.configure("Body.TLabel", font=("Malgun Gothic", 9))
        style.configure("Muted.TLabel", font=("Malgun Gothic", 9))
        style.configure("Accent.TButton", font=("Malgun Gothic", 10, "bold"), padding=(12, 8))
        style.configure("Soft.TButton", font=("Malgun Gothic", 9), padding=(9, 6))

    def _apply_theme(self) -> None:
        colors = self.colors
        style = ttk.Style(self)
        self.configure(background=colors["bg"])
        style.configure("App.TFrame", background=colors["bg"])
        style.configure("Card.TFrame", background=colors["card"])
        for label_style, foreground in (
            ("Title.TLabel", colors["text"]),
            ("Section.TLabel", colors["text"]),
            ("Body.TLabel", colors["text"]),
            ("Muted.TLabel", colors["muted"]),
        ):
            style.configure(label_style, background=colors["card"], foreground=foreground)
        style.configure("TLabel", background=colors["bg"], foreground=colors["text"], font=("Malgun Gothic", 9))
        style.configure("TFrame", background=colors["bg"])
        style.configure("TPanedwindow", background=colors["bg"])
        style.configure("TNotebook", background=colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=colors["surface"], foreground=colors["muted"], padding=(14, 8))
        style.map("TNotebook.Tab", background=[("selected", colors["card"])], foreground=[("selected", colors["accent"])])
        style.configure("TEntry", fieldbackground=colors["field"], foreground=colors["text"], bordercolor=colors["border"], padding=7)
        style.configure("TCombobox", fieldbackground=colors["field"], foreground=colors["text"], background=colors["field"], padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", colors["field"])], foreground=[("readonly", colors["text"])])
        style.configure("TButton", background=colors["surface"], foreground=colors["text"], bordercolor=colors["border"])
        style.map("TButton", background=[("active", colors["border"]), ("disabled", colors["surface"])])
        style.configure("Accent.TButton", background=colors["accent"], foreground=colors["accent_text"], bordercolor=colors["accent"])
        style.map("Accent.TButton", background=[("active", "#55e0c4"), ("disabled", colors["border"])], foreground=[("disabled", colors["muted"])])
        for widget in getattr(self, "text_widgets", []):
            widget.configure(bg=colors["field"], fg=colors["text"], insertbackground=colors["text"], selectbackground=colors["accent"], relief="flat", highlightthickness=1, highlightbackground=colors["border"], highlightcolor=colors["accent"])
        if hasattr(self, "photo_list"):
            self.photo_list.configure(bg=colors["field"], fg=colors["text"], selectbackground=colors["accent"], selectforeground=colors["accent_text"], highlightbackground=colors["border"], relief="flat")
            self.preview_canvas.configure(bg=colors["field"], highlightbackground=colors["border"])
            self.preview_inner.configure(bg=colors["field"])
            self._refresh_photo_previews()
        if hasattr(self, "theme_button"):
            self.theme_button.configure(text="☀ 라이트" if self.theme_name == "dark" else "◐ 다크")

    def toggle_theme(self) -> None:
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self._apply_theme()

    def _build_ui(self) -> None:
        self.text_widgets: list[tk.Text] = []
        root = ttk.Frame(self, style="App.TFrame", padding=(18, 14, 18, 16))
        root.pack(fill="both", expand=True)

        toolbar = ttk.Frame(root, style="Card.TFrame", padding=(18, 14))
        toolbar.pack(fill="x", pady=(0, 12))
        ttk.Label(toolbar, text="✦  Blog Draft Agent", style="Title.TLabel").pack(side="left")
        ttk.Label(toolbar, text="사진과 내 말투로 만드는 블로그 작성 공간", style="Muted.TLabel").pack(side="left", padx=14)
        self.theme_button = ttk.Button(toolbar, text="☀ 라이트", style="Soft.TButton", command=self.toggle_theme)
        self.theme_button.pack(side="right")
        ttk.Button(toolbar, text="설정", style="Soft.TButton", command=self.open_settings).pack(side="right", padx=6)
        ttk.Button(toolbar, text="네이버 로그인", style="Soft.TButton", command=self.login_naver).pack(side="right", padx=6)
        ttk.Label(toolbar, textvariable=self.naver_status_var, style="Muted.TLabel").pack(side="right", padx=8)

        paned = ttk.PanedWindow(root, orient="horizontal")
        paned.pack(fill="both", expand=True)
        form = ttk.Frame(paned, style="Card.TFrame", padding=16)
        result = ttk.Frame(paned, style="Card.TFrame", padding=16)
        paned.add(form, weight=1)
        paned.add(result, weight=2)
        self._build_form(form)
        self._build_result(result)

        footer = ttk.Frame(root, style="Card.TFrame", padding=(16, 10))
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").pack(side="left", fill="x", expand=True)
        self.body_button = ttk.Button(footer, text="2. 본문 완성", style="Accent.TButton", command=self.generate_body, state="disabled")
        self.body_button.pack(side="right")
        self.outline_button = ttk.Button(footer, text="1. 초안 설계", style="Soft.TButton", command=self.generate_outline)
        self.outline_button.pack(side="right", padx=(0, 8))

    def _new_text(self, parent: ttk.Frame, height: int, font_size: int = 10) -> tk.Text:
        widget = tk.Text(parent, height=height, wrap="word", font=("Malgun Gothic", font_size), padx=10, pady=8)
        self.text_widgets.append(widget)
        return widget

    def _build_form(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(12, weight=1)
        heading = ttk.Frame(parent, style="Card.TFrame")
        heading.grid(row=0, column=0, sticky="ew")
        ttk.Label(heading, text="글 재료", style="Section.TLabel").pack(side="left")
        ttk.Label(heading, text="테마", style="Muted.TLabel").pack(side="right", padx=(8, 5))
        theme_combo = ttk.Combobox(heading, textvariable=self.theme_var, values=THEMES, state="readonly", width=11)
        theme_combo.pack(side="right")
        theme_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_theme_samples())

        ttk.Label(parent, text="글 주제", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=(14, 3))
        ttk.Entry(parent, textvariable=self.topic_var).grid(row=2, column=0, sticky="ew")
        ttk.Label(parent, text="알고 있는 사실·방문 계기·메뉴·가격 등", style="Body.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 3))
        self.memo_text = self._new_text(parent, 5)
        self.memo_text.grid(row=4, column=0, sticky="ew")

        photo_header = ttk.Frame(parent, style="Card.TFrame")
        photo_header.grid(row=5, column=0, sticky="ew", pady=(13, 3))
        ttk.Label(photo_header, text="사진", style="Body.TLabel").pack(side="left")
        ttk.Button(photo_header, text="＋ 사진 추가", style="Soft.TButton", command=self.add_photos).pack(side="right")
        ttk.Button(photo_header, text="선택 제거", style="Soft.TButton", command=self.remove_photo).pack(side="right", padx=5)
        self.photo_list = tk.Listbox(parent, height=4, exportselection=False, font=("Malgun Gothic", 9))
        self.photo_list.grid(row=6, column=0, sticky="ew")
        self.photo_list.bind("<<ListboxSelect>>", self.select_photo_preview)

        preview_card = ttk.Frame(parent, style="Card.TFrame")
        preview_card.grid(row=7, column=0, sticky="ew", pady=(6, 0))
        self.preview_canvas = tk.Canvas(preview_card, height=122, highlightthickness=1)
        preview_scroll = ttk.Scrollbar(preview_card, orient="horizontal", command=self.preview_canvas.xview)
        self.preview_canvas.configure(xscrollcommand=preview_scroll.set)
        self.preview_canvas.pack(fill="x")
        preview_scroll.pack(fill="x")
        self.preview_inner = tk.Frame(self.preview_canvas)
        self.preview_canvas_window = self.preview_canvas.create_window((0, 0), window=self.preview_inner, anchor="nw")
        self.preview_inner.bind("<Configure>", lambda _event: self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all")))

        ttk.Label(parent, text="사진 메모 (사진 순서대로 한 줄씩)", style="Body.TLabel").grid(row=8, column=0, sticky="w", pady=(12, 3))
        self.photo_notes_text = self._new_text(parent, 4)
        self.photo_notes_text.grid(row=9, column=0, sticky="ew")

        sample_header = ttk.Frame(parent, style="Card.TFrame")
        sample_header.grid(row=10, column=0, sticky="ew", pady=(12, 3))
        ttk.Label(sample_header, text="내 기존 글 예시", style="Body.TLabel").pack(side="left")
        ttk.Button(sample_header, text="샘플 저장", style="Soft.TButton", command=self.save_theme_samples).pack(side="right")
        ttk.Button(sample_header, text="불러오기", style="Soft.TButton", command=self.load_theme_samples).pack(side="right", padx=5)
        ttk.Label(parent, text="테마별로 이 PC에 저장됩니다. 원문은 복사하지 않고 문체만 반영합니다.", style="Muted.TLabel").grid(row=11, column=0, sticky="w", pady=(0, 3))
        self.style_samples_text = self._new_text(parent, 10)
        self.style_samples_text.grid(row=12, column=0, sticky="nsew")

    def _build_result(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        ttk.Label(parent, text="작성 워크스페이스", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        outline_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=7)
        body_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=7)
        analysis_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=7)
        profile_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=7)
        self.notebook.add(outline_tab, text="1 · 초안 설계")
        self.notebook.add(body_tab, text="2 · 완성 본문")
        self.notebook.add(analysis_tab, text="사진 분석")
        self.notebook.add(profile_tab, text="말투 프로필")
        for tab in (outline_tab, body_tab, analysis_tab, profile_tab):
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)
        self.outline_text = self._new_text(outline_tab, 20, 11)
        self.draft_text = self._new_text(body_tab, 20, 11)
        self.analysis_text = self._new_text(analysis_tab, 20)
        self.profile_text = self._new_text(profile_tab, 20)
        for widget, tab in ((self.outline_text, outline_tab), (self.draft_text, body_tab), (self.analysis_text, analysis_tab), (self.profile_text, profile_tab)):
            widget.grid(row=0, column=0, sticky="nsew")

        actions = ttk.Frame(parent, style="Card.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(9, 0))
        ttk.Button(actions, text="본문 복사", style="Soft.TButton", command=self.copy_draft).pack(side="left")
        ttk.Button(actions, text="Markdown 저장", style="Soft.TButton", command=lambda: self.save_draft("md")).pack(side="left", padx=5)
        ttk.Button(actions, text="TXT 저장", style="Soft.TButton", command=lambda: self.save_draft("txt")).pack(side="left")
        ttk.Label(actions, text="[사진 N 삽입] 위치에 네이버 에디터에서 사진을 배치하세요.", style="Muted.TLabel").pack(side="right")

    def add_photos(self) -> None:
        filenames = filedialog.askopenfilenames(title="블로그에 쓸 사진 선택", filetypes=[("이미지", "*.jpg *.jpeg *.png *.gif *.webp"), ("모든 파일", "*.*")])
        for filename in filenames:
            path = Path(filename)
            if path not in self.photos:
                self.photos.append(path)
        self._refresh_photos()

    def _refresh_photos(self) -> None:
        self.photo_list.delete(0, "end")
        for number, photo in enumerate(self.photos, start=1):
            self.photo_list.insert("end", f"{number}. {photo.name}")
        self._refresh_photo_previews()

    def _refresh_photo_previews(self) -> None:
        if not hasattr(self, "preview_inner"):
            return
        colors = self.colors
        for child in self.preview_inner.winfo_children():
            child.destroy()
        self.preview_images.clear()
        if not self.photos:
            tk.Label(self.preview_inner, text="사진을 추가하면 여기에서 미리 볼 수 있습니다.", bg=colors["field"], fg=colors["muted"], font=("Malgun Gothic", 9)).pack(anchor="w", padx=10, pady=42)
            return
        for index, path in enumerate(self.photos):
            card = tk.Frame(self.preview_inner, bg=colors["field"], padx=4, pady=4)
            card.pack(side="left", padx=(8 if index == 0 else 2, 6), pady=6)
            try:
                image = Image.open(path).convert("RGB")
                image.thumbnail((112, 82), Image.Resampling.LANCZOS)
                photo_image = ImageTk.PhotoImage(image)
                self.preview_images.append(photo_image)
                label = tk.Label(card, image=photo_image, bg=colors["field"], cursor="hand2")
                label.pack()
            except OSError:
                label = tk.Label(card, text="미리보기\n실패", width=14, height=5, bg=colors["field"], fg=colors["danger"], cursor="hand2")
                label.pack()
            caption = tk.Label(card, text=f"{index + 1}. {path.name[:16]}", bg=colors["field"], fg=colors["muted"], font=("Malgun Gothic", 8))
            caption.pack(pady=(4, 0))
            for target in (card, label, caption):
                target.bind("<Button-1>", lambda _event, selected=index: self._select_photo(selected))
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))

    def _select_photo(self, index: int) -> None:
        self.photo_list.selection_clear(0, "end")
        self.photo_list.selection_set(index)
        self.photo_list.see(index)

    def select_photo_preview(self, _event: tk.Event) -> None:
        selection = self.photo_list.curselection()
        if selection:
            self.preview_canvas.xview_moveto(max(0, selection[0] / max(len(self.photos), 1)))

    def remove_photo(self) -> None:
        selection = self.photo_list.curselection()
        if not selection:
            return
        del self.photos[selection[0]]
        self._refresh_photos()

    def _photo_notes(self) -> list[str]:
        return [line.strip() for line in self.photo_notes_text.get("1.0", "end").splitlines()]

    def _input_data(self) -> tuple[str, str, list[str], str, str] | None:
        topic = self.topic_var.get().strip()
        memo = self.memo_text.get("1.0", "end").strip()
        if not topic and not memo and not self.photos:
            messagebox.showwarning(APP_TITLE, "글 주제, 메모, 사진 중 하나 이상을 입력해 주세요.")
            return None
        return topic, memo, self._photo_notes(), self.style_samples_text.get("1.0", "end").strip(), self.theme_var.get()

    def _set_busy(self, busy: bool) -> None:
        self.outline_button.configure(state="disabled" if busy else "normal")
        self.body_button.configure(state="disabled" if busy or not self.outline_text.get("1.0", "end").strip() else "normal")

    def generate_outline(self) -> None:
        values = self._input_data()
        if not values:
            return
        topic, memo, photo_notes, style_samples, theme = values
        self._set_busy(True)
        self.status_var.set("사진을 분석하고 검토 가능한 초안 설계안을 만드는 중입니다...")

        def work() -> None:
            try:
                result = create_outline(self.settings, topic, memo, self.photos, photo_notes, style_samples, theme)
                self.after(0, lambda: self.show_outline(result))
            except Exception as error:  # Keep the desktop UI recoverable even for unexpected errors.
                self.after(0, lambda: self.show_error(error))

        threading.Thread(target=work, daemon=True).start()

    def show_outline(self, result: DraftResult) -> None:
        self.last_image_analysis = result.image_analysis
        self._set_text(self.outline_text, result.content)
        self._set_text(self.analysis_text, result.image_analysis)
        self._set_text(self.profile_text, result.style_profile)
        self.notebook.select(0)
        self.status_var.set("초안 설계 완료. 내용을 수정한 뒤 ‘2. 본문 완성’을 누르세요.")
        self._set_busy(False)

    def generate_body(self) -> None:
        values = self._input_data()
        outline = self.outline_text.get("1.0", "end").strip()
        if not values or not outline:
            messagebox.showwarning(APP_TITLE, "먼저 1단계 초안 설계를 만들고 검토해 주세요.")
            return
        topic, memo, photo_notes, style_samples, theme = values
        self._set_busy(True)
        self.status_var.set("검토한 설계안을 바탕으로 완성 본문을 작성하는 중입니다...")

        def work() -> None:
            try:
                result = create_body(self.settings, topic, memo, self.photos, photo_notes, style_samples, theme, outline, self.last_image_analysis)
                self.after(0, lambda: self.show_body(result))
            except Exception as error:
                self.after(0, lambda: self.show_error(error))

        threading.Thread(target=work, daemon=True).start()

    def show_body(self, result: DraftResult) -> None:
        self._set_text(self.draft_text, result.content)
        self._set_text(self.analysis_text, result.image_analysis)
        self._set_text(self.profile_text, result.style_profile)
        self.notebook.select(1)
        source = "NVIDIA 모델" if result.used_remote_model else "로컬 작성 모드"
        self.status_var.set(f"본문 완성: {source}로 작성했습니다. 사실을 최종 확인한 뒤 저장하세요.")
        self._set_busy(False)

    def show_error(self, error: Exception) -> None:
        self.status_var.set("작성 중 오류가 발생했습니다. 설정과 사진 파일을 확인해 주세요.")
        self._set_busy(False)
        messagebox.showerror(APP_TITLE, str(error))

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def save_theme_samples(self) -> None:
        samples = self.style_samples_text.get("1.0", "end").strip()
        if not samples:
            messagebox.showinfo(APP_TITLE, "저장할 말투 예시를 먼저 붙여 넣어 주세요.")
            return
        self.style_store.save(self.theme_var.get(), samples)
        self.status_var.set(f"‘{self.theme_var.get()}’ 테마의 말투 예시를 이 PC에 저장했습니다.")

    def load_theme_samples(self) -> None:
        samples = self.style_store.load(self.theme_var.get())
        self._set_text(self.style_samples_text, samples)
        self.status_var.set(f"‘{self.theme_var.get()}’ 테마의 {'저장된 말투 예시를 불러왔습니다.' if samples else '기본 작성 가이드를 적용합니다.'}")

    def copy_draft(self) -> None:
        content = self.draft_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo(APP_TITLE, "먼저 완성 본문을 만들어 주세요.")
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.status_var.set("본문을 클립보드에 복사했습니다.")

    def save_draft(self, extension: str) -> None:
        content = self.draft_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo(APP_TITLE, "저장할 완성 본문이 없습니다.")
            return
        filename = filedialog.asksaveasfilename(title="본문 저장", defaultextension=f".{extension}", filetypes=[("Markdown", "*.md")] if extension == "md" else [("Text", "*.txt")])
        if not filename:
            return
        if extension == "txt":
            content = content.replace("# ", "").replace("## ", "")
        Path(filename).write_text(content, encoding="utf-8")
        self.status_var.set(f"저장했습니다: {filename}")

    def login_naver(self) -> None:
        self.naver_status_var.set("네이버: 로그인 창 여는 중...")
        NaverLogin(self.settings).start(lambda profile, error: self.after(0, lambda: self._show_naver_result(profile, error)))

    def _show_naver_result(self, profile: NaverProfile | None, error: str | None) -> None:
        if error:
            self.naver_status_var.set("네이버: 연결 실패")
            messagebox.showwarning(APP_TITLE, error)
            return
        self.naver_profile = profile
        self.naver_status_var.set(f"네이버: {profile.nickname}")
        self.status_var.set("네이버 로그인 연결 완료. 게시물 자동 발행은 하지 않습니다.")

    def open_settings(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("연동 설정")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        content = ttk.Frame(dialog, style="Card.TFrame", padding=18)
        content.pack(fill="both", expand=True)
        ttk.Button(content, text="NVIDIA API 키 페이지 열기", style="Soft.TButton", command=self.open_nvidia_api_page).grid(row=0, column=0, sticky="w")
        ttk.Label(content, text="NVIDIA Build에서 키를 만든 뒤 아래 칸에 붙여 넣으세요. 키는 이 PC의 .env에만 저장됩니다.", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(7, 14))
        fields = [("NVIDIA API Key", "nvidia_api_key", True), ("NVIDIA Base URL", "nvidia_base_url", False), ("사진 분석 모델", "vision_model", False), ("글 작성 모델", "writer_model", False), ("NAVER Client ID", "naver_client_id", False), ("NAVER Client Secret", "naver_client_secret", True), ("NAVER Redirect URI", "naver_redirect_uri", False)]
        entries: dict[str, ttk.Entry] = {}
        for row, (label, name, secret) in enumerate(fields, start=2):
            ttk.Label(content, text=label, style="Body.TLabel").grid(row=row * 2, column=0, sticky="w")
            entry = ttk.Entry(content, width=66, show="*" if secret else "")
            entry.insert(0, getattr(self.settings, name))
            entry.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(2, 8))
            entries[name] = entry

        def save() -> None:
            for name, entry in entries.items():
                setattr(self.settings, name, entry.get().strip())
            self.settings.save()
            dialog.destroy()
            self.status_var.set("설정을 로컬 .env 파일에 저장했습니다.")

        ttk.Button(content, text="저장", style="Accent.TButton", command=save).grid(row=(len(fields) + 2) * 2, column=0, sticky="e", pady=(8, 0))

    @staticmethod
    def open_nvidia_api_page() -> None:
        webbrowser.open("https://build.nvidia.com/settings/api-key")


if __name__ == "__main__":
    BlogDraftAgent().mainloop()
