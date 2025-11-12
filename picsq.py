import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps

def select_image():
    path = filedialog.askopenfilename(filetypes=[("画像ファイル", "*.jpg;*.png;*.jpeg")])
    if path:
        entry_path.delete(0, tk.END)
        entry_path.insert(0, path)

def process_image():
    try:
        img_path = entry_path.get()
        img = Image.open(img_path)

        width = int(entry_width.get())
        height = int(entry_height.get())
        border = int(entry_border.get())
        color = entry_color.get()

        # リサイズと余白追加
        img_resized = img.resize((width, height))
        img_bordered = ImageOps.expand(img_resized, border=border, fill=color)

        save_path = filedialog.asksaveasfilename(defaultextension=".png")
        if save_path:
            img_bordered.save(save_path)
            messagebox.showinfo("完了", f"保存しました: {save_path}")
    except Exception as e:
        messagebox.showerror("エラー", str(e))

# GUI構築
root = tk.Tk()
root.title("画像リサイズ＋余白追加ツール")

tk.Label(root, text="画像ファイル:").grid(row=0, column=0, sticky="e")
entry_path = tk.Entry(root, width=40)
entry_path.grid(row=0, column=1)
tk.Button(root, text="選択", command=select_image).grid(row=0, column=2)

tk.Label(root, text="幅:").grid(row=1, column=0, sticky="e")
entry_width = tk.Entry(root, width=10)
entry_width.insert(0, "300")
entry_width.grid(row=1, column=1, sticky="w")

tk.Label(root, text="高さ:").grid(row=2, column=0, sticky="e")
entry_height = tk.Entry(root, width=10)
entry_height.insert(0, "300")
entry_height.grid(row=2, column=1, sticky="w")

tk.Label(root, text="余白(px):").grid(row=3, column=0, sticky="e")
entry_border = tk.Entry(root, width=10)
entry_border.insert(0, "50")
entry_border.grid(row=3, column=1, sticky="w")

tk.Label(root, text="色:").grid(row=4, column=0, sticky="e")
entry_color = tk.Entry(root, width=10)
entry_color.insert(0, "white")
entry_color.grid(row=4, column=1, sticky="w")

tk.Button(root, text="変換して保存", command=process_image).grid(row=5, column=1, pady=10)

root.mainloop()
