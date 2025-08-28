import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import unicodedata
import re
def _sanitize(name: str) -> str:
    """Normalize and clean a string so it can be used as a file name."""
    nfkd = unicodedata.normalize("NFKD", name)
    # remove accents
    name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # replace forbidden characters
    name = re.sub(r"[\\/*?:\"<>|]", "", name)
    return name.strip().replace(" ", "_")
def _extract_info(path: str):
    """Extract IBGE code and municipality name from a CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        sample = f.read(1024)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(f, dialect)
        rows = list(reader)
    if len(rows) < 2:
        return None, None
    headers = [h.strip().upper() for h in rows[0]]
    data = [d.strip() for d in rows[1]]
    ibge = None
    municipio = None
    for idx, header in enumerate(headers):
        if ibge is None and "IBGE" in header:
            if idx < len(data):
                ibge = data[idx]
        if municipio is None and ("MUNIC" in header or "MUNICIPIO" in header or "MUNICÍPIO" in header):
            if idx < len(data):
                municipio = data[idx]
    # fallback to first two columns
    if ibge is None and len(data) > 0:
        ibge = data[0]
    if municipio is None and len(data) > 1:
        municipio = data[1]
    return ibge, municipio
def _rename_files(paths):
    for path in paths:
        ibge, municipio = _extract_info(path)
        if not ibge or not municipio:
            continue
        new_name = f"{ibge}-{_sanitize(municipio)}.csv"
        new_path = os.path.join(os.path.dirname(path), new_name)
        os.rename(path, new_path)
    messagebox.showinfo("Concluído", "Arquivos renomeados com sucesso.")
def _select_files():
    files = filedialog.askopenfilenames(title="Selecionar arquivos CSV", filetypes=[("CSV", "*.csv")])
    if files:
        _rename_files(files)
def main():
    root = tk.Tk()
    root.title("Renomear CSV")
    root.geometry("300x100")
    btn = tk.Button(root, text="Selecionar CSVs", command=_select_files)
    btn.pack(expand=True)
    root.mainloop()
if __name__ == "__main__":
    main()