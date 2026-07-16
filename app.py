from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from blog_agent.config import Settings
from blog_agent.draft_service import DraftResult, generate_draft
from blog_agent.naver_oauth import NaverLogin, NaverProfile


APP_TITLE = "Blog Draft Agent"


class BlogDraftAgent(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1420x900")
        self.minsize(1120, 720)
        self.settings = Settings.load()
        self.photos: list[Path] = []
        self.naver_profile: NaverProfile | None = None

        self.topic_var = tk.StringVar()
        self.status_var = tk.StringVar(value="사진과 메모를 입력한 뒤 초안 만들기를 누르세요.")
        self.naver_status_var = tk.StringVar(value="네이버 로그인: 연결 안 됨")
        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Header.TLabel", font=("Malgun Gothic", 14, "bold"))
        style.configure("Primary.TButton", font=("Malgun Gothic", 10, "bold"))

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self, padding=(12, 10))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=APP_TITLE, style="Header.TLabel").pack(side="left")
        ttk.Button(toolbar, text="설정", command=self.open_settings).pack(side="right")
        ttk.Button(toolbar, text="네이버 로그인", command=self.login_naver).pack(side="right", padx=6)
        ttk.Label(toolbar, textvariable=self.naver_status_var).pack(side="right", padx=12)

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        form = ttk.Frame(paned, padding=8)
        result = ttk.Frame(paned, padding=8)
        paned.add(form, weight=1)
        paned.add(result, weight=2)
        self._build_form(form)
        self._build_result(result)

        footer = ttk.Frame(self, padding=(12, 6, 12, 10))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var).pack(side="left", fill="x", expand=True)
        self.generate_button = ttk.Button(
            footer, text="사진 분석 · 블로그 초안 만들기", style="Primary.TButton", command=self.generate
        )
        self.generate_button.pack(side="right")

    def _build_form(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        ttk.Label(parent, text="글 주제", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.topic_var).grid(row=1, column=0, sticky="ew", pady=(4, 12))

        ttk.Label(parent, text="간단한 상황·사실 메모").grid(row=2, column=0, sticky="w")
        self.memo_text = tk.Text(parent, height=7, wrap="word", font=("Malgun Gothic", 10))
        self.memo_text.grid(row=3, column=0, sticky="ew", pady=(4, 12))

        photo_header = ttk.Frame(parent)
        photo_header.grid(row=4, column=0, sticky="ew")
        ttk.Label(photo_header, text="사진").pack(side="left")
        ttk.Button(photo_header, text="사진 추가", command=self.add_photos).pack(side="right")
        ttk.Button(photo_header, text="선택 제거", command=self.remove_photo).pack(side="right", padx=5)
        self.photo_list = tk.Listbox(parent, height=6, exportselection=False, font=("Malgun Gothic", 9))
        self.photo_list.grid(row=5, column=0, sticky="ew", pady=(4, 8))

        ttk.Label(parent, text="사진 메모 (사진 순서대로 한 줄씩 입력)").grid(row=6, column=0, sticky="w")
        self.photo_notes_text = tk.Text(parent, height=5, wrap="word", font=("Malgun Gothic", 10))
        self.photo_notes_text.grid(row=7, column=0, sticky="ew", pady=(4, 12))

        ttk.Label(parent, text="내 기존 글 예시 (붙여넣기)").grid(row=8, column=0, sticky="w")
        ttk.Label(
            parent,
            text="말투·문단 길이·이모지 사용만 분석합니다. 예시는 최소 3개, 권장은 20개입니다.",
            foreground="#666666",
        ).grid(row=9, column=0, sticky="w", pady=(2, 4))
        self.style_samples_text = tk.Text(parent, height=14, wrap="word", font=("Malgun Gothic", 10))
        self.style_samples_text.grid(row=10, column=0, sticky="nsew")
        parent.rowconfigure(10, weight=1)

    def _build_result(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        notebook = ttk.Notebook(parent)
        notebook.grid(row=0, column=0, sticky="nsew")

        preview_tab = ttk.Frame(notebook, padding=6)
        analysis_tab = ttk.Frame(notebook, padding=6)
        profile_tab = ttk.Frame(notebook, padding=6)
        notebook.add(preview_tab, text="블로그 초안")
        notebook.add(analysis_tab, text="사진 분석")
        notebook.add(profile_tab, text="말투 프로필")

        for tab in (preview_tab, analysis_tab, profile_tab):
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)

        self.draft_text = tk.Text(preview_tab, wrap="word", font=("Malgun Gothic", 11), undo=True)
        self.analysis_text = tk.Text(analysis_tab, wrap="word", font=("Malgun Gothic", 10))
        self.profile_text = tk.Text(profile_tab, wrap="word", font=("Malgun Gothic", 10))
        self.draft_text.grid(row=0, column=0, sticky="nsew")
        self.analysis_text.grid(row=0, column=0, sticky="nsew")
        self.profile_text.grid(row=0, column=0, sticky="nsew")

        actions = ttk.Frame(parent)
        actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(actions, text="본문 복사", command=self.copy_draft).pack(side="left")
        ttk.Button(actions, text="Markdown 저장", command=lambda: self.save_draft("md")).pack(side="left", padx=5)
        ttk.Button(actions, text="TXT 저장", command=lambda: self.save_draft("txt")).pack(side="left")
        ttk.Label(
            actions,
            text="[사진 N 삽입] 위치에 네이버 에디터에서 사진을 넣고 최종 검토 후 발행하세요.",
            foreground="#666666",
        ).pack(side="right")

    def add_photos(self) -> None:
        filenames = filedialog.askopenfilenames(
            title="블로그에 쓸 사진 선택",
            filetypes=[("이미지", "*.jpg *.jpeg *.png *.gif *.webp"), ("모든 파일", "*.*")],
        )
        for filename in filenames:
            path = Path(filename)
            if path not in self.photos:
                self.photos.append(path)
                self.photo_list.insert("end", f"{len(self.photos)}. {path.name}")

    def remove_photo(self) -> None:
        selection = self.photo_list.curselection()
        if not selection:
            return
        index = selection[0]
        del self.photos[index]
        self.photo_list.delete(0, "end")
        for number, photo in enumerate(self.photos, start=1):
            self.photo_list.insert("end", f"{number}. {photo.name}")

    def _photo_notes(self) -> list[str]:
        return [line.strip() for line in self.photo_notes_text.get("1.0", "end").splitlines()]

    def generate(self) -> None:
        topic = self.topic_var.get().strip()
        memo = self.memo_text.get("1.0", "end").strip()
        if not topic and not memo and not self.photos:
            messagebox.showwarning(APP_TITLE, "글 주제, 메모, 사진 중 하나 이상을 입력해 주세요.")
            return

        self.generate_button.configure(state="disabled")
        self.status_var.set("사진을 분석하고 말투를 반영한 초안을 만드는 중입니다...")
        photo_notes = self._photo_notes()
        style_samples = self.style_samples_text.get("1.0", "end").strip()

        def work() -> None:
            draft = generate_draft(self.settings, topic, memo, self.photos, photo_notes, style_samples)
            self.after(0, lambda: self.show_result(draft))

        threading.Thread(target=work, daemon=True).start()

    def show_result(self, draft: DraftResult) -> None:
        self._set_text(self.draft_text, draft.content)
        self._set_text(self.analysis_text, draft.image_analysis)
        self._set_text(self.profile_text, draft.style_profile)
        source = "NVIDIA 모델" if draft.used_remote_model else "로컬 초안 모드"
        self.status_var.set(f"완료: {source}로 초안을 만들었습니다. 내용을 검토한 뒤 저장하거나 복사하세요.")
        self.generate_button.configure(state="normal")

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def copy_draft(self) -> None:
        content = self.draft_text.get("1.0", "end").strip()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.status_var.set("본문을 클립보드에 복사했습니다.")

    def save_draft(self, extension: str) -> None:
        content = self.draft_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo(APP_TITLE, "저장할 초안이 없습니다.")
            return
        filename = filedialog.asksaveasfilename(
            title="초안 저장",
            defaultextension=f".{extension}",
            filetypes=[("Markdown", "*.md")] if extension == "md" else [("Text", "*.txt")],
        )
        if not filename:
            return
        if extension == "txt":
            content = content.replace("# ", "").replace("## ", "")
        Path(filename).write_text(content, encoding="utf-8")
        self.status_var.set(f"저장했습니다: {filename}")

    def login_naver(self) -> None:
        self.naver_status_var.set("네이버 로그인 창을 여는 중...")

        def completed(profile: NaverProfile | None, error: str | None) -> None:
            self.after(0, lambda: self._show_naver_result(profile, error))

        NaverLogin(self.settings).start(completed)

    def _show_naver_result(self, profile: NaverProfile | None, error: str | None) -> None:
        if error:
            self.naver_status_var.set("네이버 로그인: 연결 실패")
            messagebox.showwarning(APP_TITLE, error)
            return
        self.naver_profile = profile
        self.naver_status_var.set(f"네이버 로그인: {profile.nickname}")
        self.status_var.set("네이버 로그인 연결 완료. 이 앱은 글 발행 권한을 사용하지 않습니다.")

    def open_settings(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("연동 설정")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        content = ttk.Frame(dialog, padding=16)
        content.pack(fill="both", expand=True)
        fields = [
            ("NVIDIA API Key", "nvidia_api_key", True),
            ("NVIDIA Base URL", "nvidia_base_url", False),
            ("사진 분석 모델", "vision_model", False),
            ("글 작성 모델", "writer_model", False),
            ("NAVER Client ID", "naver_client_id", False),
            ("NAVER Client Secret", "naver_client_secret", True),
            ("NAVER Redirect URI", "naver_redirect_uri", False),
        ]
        entries: dict[str, ttk.Entry] = {}
        for row, (label, name, secret) in enumerate(fields):
            ttk.Label(content, text=label).grid(row=row * 2, column=0, sticky="w")
            entry = ttk.Entry(content, width=64, show="*" if secret else "")
            entry.insert(0, getattr(self.settings, name))
            entry.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(2, 9))
            entries[name] = entry
        ttk.Label(
            content,
            text="실제 키는 로컬 .env에만 저장되며 Git에 포함되지 않습니다.\nNaver 로그인은 사용자 식별용이며 게시물 발행 기능은 제공하지 않습니다.",
            foreground="#666666",
        ).grid(row=len(fields) * 2, column=0, sticky="w", pady=(2, 10))

        def save() -> None:
            for name, entry in entries.items():
                setattr(self.settings, name, entry.get().strip())
            self.settings.save()
            dialog.destroy()
            self.status_var.set("설정을 로컬 .env 파일에 저장했습니다.")

        ttk.Button(content, text="저장", style="Primary.TButton", command=save).grid(
            row=len(fields) * 2 + 1, column=0, sticky="e"
        )


if __name__ == "__main__":
    BlogDraftAgent().mainloop()
