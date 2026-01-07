import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps, ImageDraw

class SquareImageTool:
    def __init__(self, root):
        self.root = root
        self.root.title("長方形→正方形加工ツール")

        # state
        self.image_paths = []
        self.index = 0
        self.original_img = None          # PIL Image (orig size)
        self.display_img = None           # PIL Image (scaled for display)
        self.tk_display_img = None        # PhotoImage for main canvas
        self.preview_thumbnails = []      # keep references for thumbnails
        self.crop_centers = {}            # per-path crop center in original coords: {path: (cx, cy)}
        self.output_folder = None
        self.image_modes = {}             # {path: "crop" or "pad"}


        # --- Controls frame (top) ---
        ctrl = tk.Frame(root)
        ctrl.pack(fill="x", padx=6, pady=6)

        tk.Button(ctrl, text="フォルダを選択", command=self.select_folder).pack(side="left", padx=4)
        tk.Button(ctrl, text="出力フォルダを選択", command=self.select_output_folder).pack(side="left", padx=4)
        self.label_output = tk.Label(ctrl, text="出力: 未選択")
        self.label_output.pack(side="left", padx=6)

        tk.Button(ctrl, text="前へ", command=self.prev_image).pack(side="right", padx=4)
        tk.Button(ctrl, text="次へ", command=self.next_image).pack(side="right", padx=4)

        # Mode radio
        mode_frame = tk.Frame(root)
        mode_frame.pack(fill="x", padx=6)
        self.mode = tk.StringVar(value="crop")
        tk.Radiobutton(mode_frame, text="切り取り (crop)", variable=self.mode, value="crop").pack(side="left")
        tk.Radiobutton(mode_frame, text="余白追加 (pad)", variable=self.mode, value="pad").pack(side="left")

        # --- Preview thumbnails (horizontal scroll) ---
        preview_frame = tk.Frame(root)
        preview_frame.pack(fill="x", padx=6, pady=(6,0))
        self.preview_canvas = tk.Canvas(preview_frame, height=170)
        hscroll = tk.Scrollbar(preview_frame, orient="horizontal", command=self.preview_canvas.xview)
        self.preview_canvas.configure(xscrollcommand=hscroll.set)
        hscroll.pack(side="bottom", fill="x")
        self.preview_canvas.pack(side="top", fill="x", expand=True)

        # inner frame inside preview_canvas
        self.preview_container = tk.Frame(self.preview_canvas)
        self.preview_canvas.create_window((0,0), window=self.preview_container, anchor="nw")

        self.preview_container.bind(
            "<Configure>",
            lambda e: self.preview_canvas.configure(
                scrollregion=self.preview_canvas.bbox("all")
            )
        )

        # --- Main editing canvas ---
        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.main_canvas_w = 600
        self.main_canvas_h = 600
        self.main_canvas = tk.Canvas(main_frame, width=self.main_canvas_w, height=self.main_canvas_h, bg="gray")
        self.main_canvas.pack(fill="both", expand=True)
        # event for dragging crop center
        self.main_canvas.bind("<B1-Motion>", self.on_drag)
        self.main_canvas.bind("<Button-1>", self.on_click)

        # Crop rectangle id on main canvas
        self.crop_rect_id = None

        # Process button
        tk.Button(root, text="正方形に変換して保存（選択画像 or 一括）", command=self.process_all).pack(pady=(0,8))

    # --- folder / output selection ---
    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder = folder
            self.label_output.config(text=f"出力: {folder}")
        else:
            self.output_folder = None
            self.label_output.config(text="出力: 未選択")

    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.image_paths = [os.path.join(folder, f) for f in os.listdir(folder)
                            if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif"))]
        self.image_paths.sort()
        if not self.image_paths:
            messagebox.showerror("エラー", "画像ファイルが見つかりません")
            return
        self.index = 0
        self.show_preview_list()
        self.load_image()

    # --- preview thumbnails ---
    def show_preview_list(self):
        for w in self.preview_container.winfo_children():
            w.destroy()
        self.preview_thumbnails.clear()

        thumb_size = (120, 120)

        for idx, path in enumerate(self.image_paths):

            # 画像の読み込み
            try:
                img = Image.open(path)
                img.thumbnail(thumb_size)
                tkimg = ImageTk.PhotoImage(img)
            except:
                continue

            self.preview_thumbnails.append(tkimg)

            # フレーム（サムネイル＋モード選択）
            frm = tk.Frame(self.preview_container)
            frm.grid(row=0, column=idx, padx=4, pady=4)

            # サムネイルボタン
            btn = tk.Button(frm, image=tkimg,
                            command=lambda p=path: self.load_image_from_preview(p))
            btn.pack()

            # モード選択
            mode_var = tk.StringVar(value=self.image_modes.get(path, "crop"))

            mode_box = tk.OptionMenu(
                frm,
                mode_var,
                "crop", "pad",
                command=lambda v, p=path: self.set_image_mode(p, v)
            )
            mode_box.pack()

    def set_image_mode(self, path, mode):
        self.image_modes[path] = mode

    def load_image_from_preview(self, path):
        if path in self.image_paths:
            self.index = self.image_paths.index(path)
            self.load_image()

    # --- load / display main image ---
    def load_image(self):
        path = self.image_paths[self.index]
        self.original_img = Image.open(path).convert("RGB")
        orig_w, orig_h = self.original_img.size

        # compute display size preserving aspect, fit into main canvas
        max_w, max_h = self.main_canvas_w, self.main_canvas_h
        ratio = min(max_w / orig_w, max_h / orig_h, 1.0)
        disp_w = int(orig_w * ratio)
        disp_h = int(orig_h * ratio)
        self.display_img = self.original_img.copy()
        self.display_img.thumbnail((disp_w, disp_h))
        self.tk_display_img = ImageTk.PhotoImage(self.display_img)

        # clear and draw centered
        self.main_canvas.delete("all")
        x = (self.main_canvas_w - disp_w) // 2
        y = (self.main_canvas_h - disp_h) // 2
        self.main_canvas.create_image(x, y, anchor="nw", image=self.tk_display_img, tags=("img",))
        # remember display geometry for mapping
        self.display_geom = (x, y, disp_w, disp_h)  # x0,y0,w,h

        # set default crop center (use stored if exists)
        path_key = path
        if path_key in self.crop_centers:
            cx, cy = self.crop_centers[path_key]
        else:
            cx, cy = orig_w // 2, orig_h // 2
            self.crop_centers[path_key] = (cx, cy)

        # draw crop rectangle at that center
        self._draw_crop_rect_for_center(cx, cy)

    def _draw_crop_rect_for_center(self, cx_orig, cy_orig):
        # 古い枠を削除
        if self.crop_rect_id:
            self.main_canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None

        orig_w, orig_h = self.original_img.size
        side = min(orig_w, orig_h)  # 正方形の一辺

        x0, y0, dw, dh = self.display_geom

        scale_x = dw / orig_w
        scale_y = dh / orig_h
        scale = min(scale_x, scale_y)

        half_disp = int((side * scale) / 2)

        # 元画像中心 → 表示座標
        disp_cx = x0 + int(cx_orig * scale)
        disp_cy = y0 + int(cy_orig * scale)

        # --- 中心点の制限（はみ出し防止） ---
        min_cx = x0 + half_disp
        max_cx = x0 + dw - half_disp
        min_cy = y0 + half_disp
        max_cy = y0 + dh - half_disp

        disp_cx = max(min_cx, min(disp_cx, max_cx))
        disp_cy = max(min_cy, min(disp_cy, max_cy))

        # 枠の座標
        x1 = disp_cx - half_disp
        y1 = disp_cy - half_disp
        x2 = disp_cx + half_disp
        y2 = disp_cy + half_disp

        self.crop_rect_id = self.main_canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="red",
            width=2,
            tags=("crop",)
        )

        # --- 修正後の中心点を元画像座標に戻して保存 ---
        new_cx = int((disp_cx - x0) / scale)
        new_cy = int((disp_cy - y0) / scale)
        path = self.image_paths[self.index]
        self.crop_centers[path] = (new_cx, new_cy)


    # --- mouse handlers for selecting crop center ---
    def on_click(self, event):
        # treat click like drag: update center
        self._update_center_from_event(event)

    def on_drag(self, event):
        self._update_center_from_event(event)

    def _update_center_from_event(self, event):
        x0, y0, dw, dh = self.display_geom

        if not (x0 <= event.x <= x0 + dw and y0 <= event.y <= y0 + dh):
            return

        orig_w, orig_h = self.original_img.size
        rel_x = event.x - x0
        rel_y = event.y - y0

        cx = int(rel_x * orig_w / dw)
        cy = int(rel_y * orig_h / dh)

        self._draw_crop_rect_for_center(cx, cy)


    # --- processing ---
    def process_image(self, path):
        img = Image.open(path).convert("RGB")
        w, h = img.size
        mode = self.image_modes.get(path, self.mode.get())
        if mode == "crop":
            # square side: use min(w,h)
            side = min(w, h)
            cx, cy = self.crop_centers.get(path, (w//2, h//2))
            left = int(cx - side/2)
            top = int(cy - side/2)
            # clamp
            left = max(0, min(left, w - side))
            top = max(0, min(top, h - side))
            cropped = img.crop((left, top, left + side, top + side))
            result = cropped
        else:
            # pad mode: create square canvas with white bg and paste centered
            side = max(w, h)
            result = Image.new("RGB", (side, side), "white")
            offset = ((side - w)//2, (side - h)//2)
            result.paste(img, offset)

        # Save to output folder (do not overwrite original; append _square)
        folder = self.get_output_folder(path)
        base, ext = os.path.splitext(os.path.basename(path))
        out_name = f"{base}{ext}"
        out_path = os.path.join(folder, out_name)
        result.save(out_path)
        return out_path
    
    def next_image(self):
        if not self.image_paths:
            return
        self.index = (self.index + 1) % len(self.image_paths)
        self.load_image()


    def prev_image(self):
        if not self.image_paths:
            return
        self.index = (self.index - 1) % len(self.image_paths)
        self.load_image()
        path = self.image_paths[self.index]
        self.original_img = Image.open(path)


        # プレビュー表示用に縮小
        preview = self.original_img.copy()
        preview.thumbnail((400, 400))
        self.tk_img = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        self.canvas.create_image(200, 200, image=self.tk_img)


        self.crop_x = 0
        self.crop_y = 0

    def process_all(self):
        if not self.image_paths:
            messagebox.showinfo("情報", "処理する画像がありません")
            return
        # ask whether to process single current or all
        if messagebox.askyesno("確認", "フォルダ内のすべての画像を処理しますか？\nいいえ: 現在の画像のみ"):
            targets = list(self.image_paths)
        else:
            targets = [self.image_paths[self.index]]

        saved = []
        for p in targets:
            try:
                out = self.process_image(p)
                saved.append(out)
            except Exception as e:
                print("処理失敗:", p, e)

        messagebox.showinfo("完了", f"保存しました: {len(saved)} ファイル")

    # utility to ensure canvas geometry tracks resizing
    # (optional: keep main_canvas size constants; for advanced, bind <Configure>)
    # Could be added later.

    def get_output_folder(self, src_path):
        # ユーザーが出力フォルダを選択していればそれを使う
        if self.output_folder:
            os.makedirs(self.output_folder, exist_ok=True)
            return self.output_folder

        # 未選択なら、元画像フォルダ内に作成
        base_dir = os.path.dirname(src_path)
        auto_dir = os.path.join(base_dir, "square_output")
        os.makedirs(auto_dir, exist_ok=True)
        return auto_dir


if __name__ == "__main__":
    root = tk.Tk()
    app = SquareImageTool(root)
    root.mainloop()
