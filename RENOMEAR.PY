"""Irá renomear os arquivos, usando como bate o conteudo dentro do arquivo .csv.

Especificadamente na linha 9"""

import datetime
import os
import re
import threading
import unicodedata
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


PANDAS_OK = True
try:
    import pandas as pd 
except Exception:
    PANDAS_OK = False

MUNICIPIO_LINE_NUMBER = 9

MUNICIPIOS_MS = [
    "Água Clara","Alcinópolis","Amambai","Anastácio","Anaurilândia","Angélica",
    "Antônio João","Aparecida do Taboado","Aquidauana","Aral Moreira","Bandeirantes",
    "Bataguassu","Batayporã","Bela Vista","Bodoquena","Bonito","Brasilândia","Caarapó",
    "Camapuã","Campo Grande","Caracol","Cassilândia","Chapadão do Sul","Corguinho",
    "Coronel Sapucaia","Corumbá","Costa Rica","Coxim","Deodápolis","Dois Irmãos do Buriti",
    "Douradina","Dourados","Eldorado","Fátima do Sul","Figueirão","Glória de Dourados",
    "Guia Lopes da Laguna","Iguatemi","Inocência","Itaporã","Itaquiraí","Ivinhema","Japorã",
    "Jaraguari","Jardim","Jateí","Juti","Ladário","Laguna Carapã","Maracaju","Miranda",
    "Mundo Novo","Naviraí","Nioaque","Nova Alvorada do Sul","Nova Andradina",
    "Novo Horizonte do Sul","Paraíso das Águas","Paranaíba","Paranhos","Pedro Gomes","Ponta Porã",
    "Porto Murtinho","Ribas do Rio Pardo","Rio Brilhante","Rio Negro","Rio Verde de Mato Grosso",
    "Rochedo","Santa Rita do Pardo","São Gabriel do Oeste","Selvíria","Sete Quedas","Sidrolândia",
    "Sonora","Tacuru","Taquarussu","Terenos","Três Lagoas","Vicentina","Paraíso das Águas",
]
MS_SET_NORM = {unicodedata.normalize("NFKD", m).encode("ASCII", "ignore").decode("ASCII").upper() for m in MUNICIPIOS_MS}


def _norm_upper_noacc(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"\s+", " ", s).strip().upper()


def fix_mojibake(s: str) -> str:
    if s is None:
        return ""
    out = s
    for _ in range(2):
        try:
            out = out.encode("latin1").decode("utf-8")
        except Exception:
            break
    return out


def safe_filename_preservando_acentos(s: str) -> str:
    if s is None:
        return ""
    s = re.sub(r"\s+", " ", s).strip().upper()
    for ch in r'\/:*?"<>|':
        s = s.replace(ch, "")
    return s


def detectar_encoding(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.read(1024)
        return "utf-8"
    except Exception:
        return "latin-1"


def extrair_municipio_da_linha9(path: Path, enc: str) -> tuple[str | None, str | None]:
    idx = MUNICIPIO_LINE_NUMBER - 1
    try:
        with open(path, "r", encoding=enc, newline="") as f:
            linhas = f.readlines()
        if idx < 0 or idx >= len(linhas):
            return None, None

        linha_bruta = linhas[idx].rstrip("\n")
        linha = fix_mojibake(linha_bruta).strip()
        if not linha:
            return None, linha_bruta

        linha = re.sub(r"^\s*munic[ií]pio\s*[:\-]?\s*", "", linha, flags=re.IGNORECASE)

        if "/" in linha:
            municipio = linha.split("/")[-1].strip()
        else:
            partes = re.split(r"[;,\t]", linha)
            municipio, score = "", -10**9
            for t in partes:
                t2 = fix_mojibake(t).strip().strip('"').strip("'")
                if not t2:
                    continue
                letras = sum(ch.isalpha() for ch in t2)
                digitos = sum(ch.isdigit() for ch in t2)
                s = letras - digitos
                if s > score:
                    municipio, score = t2, s

        municipio = fix_mojibake(municipio)
        municipio = re.sub(r"\s+", " ", municipio).strip()
        return (municipio or None), linha_bruta
    except Exception:
        return None, None


def proximo_nome_disponivel(dest: Path) -> Path:
    if not dest.exists():
        return dest
    base, suf, p = dest.stem, dest.suffix, dest.parent
    i = 1
    while True:
        cand = p / f"{base}_({i}){suf}"
        if not cand.exists():
            return cand
        i += 1


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Renomear CSV (Município) - Relatório - Faltantes")
        self.geometry("900x600")
        self.minsize(860, 560)

        top = tk.Frame(self)
        top.pack(pady=10)

        self.btn_sel = tk.Button(
            top, text="Selecionar CSVs (renomear + relatório)",
            command=self.selecionar_csvs, font=("Segoe UI", 10, "bold")
        )
        self.btn_sel.grid(row=0, column=0, padx=6)

        self.btn_check = tk.Button(
            top, text="Verificar faltantes (pasta)",
            command=self.verificar_pasta, font=("Segoe UI", 10)
        )
        self.btn_check.grid(row=0, column=1, padx=6)

        self.lbl = tk.Label(
            self,
            text=f"Lê o município da linha {MUNICIPIO_LINE_NUMBER}. Corrige encoding e mantém acentos/espaços."
        )
        self.lbl.pack()

        self.log = tk.Text(self, height=26, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=12, pady=12)

        self.status = tk.Label(self, text="Pronto.", anchor="w")
        self.status.pack(fill="x")

    def log_add(self, msg: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_status(self, msg: str) -> None:
        self.status.config(text=msg)
        self.update_idletasks()

    def selecionar_csvs(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecione CSVs",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if not paths:
            return
        threading.Thread(target=self._processar, args=(paths,), daemon=True).start()

    def _processar(self, paths: tuple[str, ...]) -> None:
        self.btn_sel.config(state="disabled")
        self.btn_check.config(state="disabled")

        total, ok, fail = len(paths), 0, 0
        vistos_norm = set()
        linhas_relatorio: list[dict[str, str]] = []

        self.set_status(f"Processando {total} arquivo(s)...")
        base_dir = Path(paths[0]).parent if paths else Path.cwd()

        for i, p in enumerate(paths, 1):
            path = Path(p)
            self.log_add(f"[{i}/{total}] {path.name}")
            try:
                enc = detectar_encoding(path)
                municipio, linha9_bruta = extrair_municipio_da_linha9(path, enc)
                if not municipio:
                    self.log_add("  X Município não encontrado na linha 9.")
                    fail += 1
                    continue

                alvo_nome = safe_filename_preservando_acentos(municipio)
                if not alvo_nome:
                    self.log_add("  X Nome inválido após normalização.")
                    fail += 1
                    continue

                destino = proximo_nome_disponivel(path.with_name(alvo_nome + ".csv"))
                os.rename(path, destino)
                self.log_add(f" OK - Renomeado → {destino.name}")
                ok += 1

                vistos_norm.add(_norm_upper_noacc(municipio))
                linhas_relatorio.append({
                    "Município": municipio,
                    "Arquivo Novo": destino.name,
                    "Pasta": str(destino.parent),
                    "Arquivo Original": path.name,
                    "Linha 9 (bruta)": linha9_bruta or ""
                })

            except Exception as e:
                self.log_add(f" X Erro: {e}")
                fail += 1

        presentes = [m for m in MUNICIPIOS_MS if _norm_upper_noacc(m) in vistos_norm]
        faltantes = [m for m in MUNICIPIOS_MS if _norm_upper_noacc(m) not in vistos_norm]

        self.log_add("\n=== Resumo ===")
        self.log_add(f"Renomeados: {ok} - Falhas: {fail}")
        self.log_add(f"Presentes: {len(presentes)} / 79")
        if presentes:
            self.log_add("  " + ", ".join(sorted(presentes)))
        self.log_add(f"Faltantes: {len(faltantes)} / 79")
        if faltantes:
            self.log_add("  " + ", ".join(sorted(faltantes)))

        self._gerar_excel(base_dir, linhas_relatorio, faltantes)

        self.set_status("Concluído.")
        self.btn_sel.config(state="normal")
        self.btn_check.config(state="normal")
        messagebox.showinfo("Resumo", f"Renomeados: {ok}\nFalhas: {fail}\nFaltantes: {len(faltantes)}")

    def _gerar_excel(self, pasta_base: Path, linhas_relatorio: list[dict[str, str]], faltantes: list[str]) -> None:
        if not PANDAS_OK:
            self.log_add("\n pandas/openpyxl não instalados. Relatório não gerado.")
            return
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            xlsx_path = pasta_base / f"RELATORIO_MS_{ts}.xlsx"
            df = pd.DataFrame(linhas_relatorio, columns=["Município", "Arquivo Novo", "Pasta", "Arquivo Original", "Linha 9 (bruta)"])
            with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
                df.to_excel(w, sheet_name="Renomeados", index=False)
                pd.DataFrame({"Faltantes": faltantes}).to_excel(w, sheet_name="Faltantes", index=False)
            self.log_add(f"\n Relatório: {xlsx_path}")
        except Exception as e:
            self.log_add(f"\n X Erro ao gerar Excel: {e}")

    def verificar_pasta(self) -> None:
        pasta = filedialog.askdirectory(title="Selecione a pasta")
        if not pasta:
            return
        threading.Thread(target=self._scan_pasta, args=(Path(pasta),), daemon=True).start()

    def _scan_pasta(self, pasta: Path) -> None:
        self.btn_sel.config(state="disabled")
        self.btn_check.config(state="disabled")
        self.set_status(f"Verificando pasta: {pasta}")

        vistos_norm = set()
        arquivos = sorted(pasta.glob("*.csv"))
        self.log_add(f"\n📁 {pasta} — {len(arquivos)} arquivo(s) .csv")

        for path in arquivos:
            nome_spaced = _norm_upper_noacc(path.stem).replace("_", " ")
            if nome_spaced in MS_SET_NORM:
                vistos_norm.add(nome_spaced)
                continue
            try:
                enc = detectar_encoding(path)
                municipio, _ = extrair_municipio_da_linha9(path, enc)
                if municipio and _norm_upper_noacc(municipio) in MS_SET_NORM:
                    vistos_norm.add(_norm_upper_noacc(municipio))
            except Exception:
                pass

        presentes = [m for m in MUNICIPIOS_MS if _norm_upper_noacc(m) in vistos_norm]
        faltantes = [m for m in MUNICIPIOS_MS if _norm_upper_noacc(m) not in vistos_norm]

        self.log_add("\n=== Faltantes na pasta ===")
        self.log_add(f"Presentes: {len(presentes)} / 79")
        if presentes:
            self.log_add("  " + ", ".join(sorted(presentes)))
        self.log_add(f"Faltantes: {len(faltantes)} / 79")
        if faltantes:
            self.log_add("  " + ", ".join(sorted(faltantes)))

        self.set_status("Concluído.")
        self.btn_sel.config(state="normal")
        self.btn_check.config(state="normal")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        try:
            from ctypes import windll  # type: ignore
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()
