import tkinter as tk
from tkinter import ttk, messagebox
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import json
import os

# === CONFIGURATION ===
API_KEY = "UUW46YCUQOF188ZW"
BASE_URL = "https://www.alphavantage.co/query"
PORTFOLIO_FILE = "portfolio.json"

# === PORTFOLIO (chargement depuis fichier si dispo)
portfolio = {}

def load_portfolio():
    global portfolio
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            portfolio = json.load(f)

def save_portfolio():
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)

# === FONCTION: HISTORIQUE DES PRIX
def fetch_price_history(symbol):
    try:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY
        }
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        if "Time Series (Daily)" not in data:
            raise ValueError(f"Données indisponibles pour {symbol}")

        ts = data["Time Series (Daily)"]
        dates = []
        prices = []

        for date_str in sorted(ts.keys()):
            dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
            prices.append(float(ts[date_str]["4. close"]))

        return dates, prices
    except Exception as e:
        messagebox.showerror("Erreur", str(e))
        return [], []

# === FONCTION: DERNIER PRIX
def fetch_last_price(symbol):
    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": API_KEY
        }
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        return float(data["Global Quote"]["05. price"])
    except:
        return 0.0

# === INTERFACE
def start_ui():
    load_portfolio()
    root = tk.Tk()
    root.title("Suivi de portefeuille")
    root.geometry("1000x700")
    root.configure(bg="#f0f0f0")

    # === CHAMPS D'ENTRÉE
    input_frame = tk.Frame(root, bg="#f0f0f0")
    input_frame.pack(pady=10)

    tk.Label(input_frame, text="Symbole :", bg="#f0f0f0").grid(row=0, column=0)
    symbol_entry = tk.Entry(input_frame, width=10)
    symbol_entry.grid(row=0, column=1, padx=5)

    tk.Label(input_frame, text="Quantité :", bg="#f0f0f0").grid(row=0, column=2)
    qty_entry = tk.Entry(input_frame, width=10)
    qty_entry.grid(row=0, column=3, padx=5)

    def add_asset():
        symbol = symbol_entry.get().upper().strip()
        qty = qty_entry.get().strip()

        if not symbol or not qty.isdigit():
            messagebox.showerror("Erreur", "Entrez un symbole valide et une quantité.")
            return

        quantity = int(qty)
        last_price = fetch_last_price(symbol)

        if not last_price:
            messagebox.showerror("Erreur", f"Impossible de récupérer le prix de {symbol}")
            return

        portfolio[symbol] = {
            "quantity": quantity,
            "last_price": last_price
        }

        save_portfolio()
        update_symbol_list()
        update_portfolio_table()

    tk.Button(input_frame, text="Ajouter", command=add_asset, bg="#28a745", fg="white").grid(row=0, column=4, padx=10)

    # === SÉLECTEUR DE SYMBOLE
    selected_symbol = tk.StringVar()
    symbol_menu = ttk.Combobox(root, textvariable=selected_symbol, state="readonly", values=[])
    symbol_menu.pack(pady=5)

    # === GRAPHIQUE
    fig, ax = plt.subplots(figsize=(8, 3))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack()

    def plot_selected_symbol(event=None):
        symbol = selected_symbol.get()
        if symbol in portfolio:
            dates, prices = fetch_price_history(symbol)
            if dates and prices:
                ax.clear()
                ax.plot(dates, prices, label=symbol, color="blue")
                ax.set_title(f"Évolution de {symbol}")
                ax.set_xlabel("Date")
                ax.set_ylabel("Prix ($)")
                ax.grid(True)
                ax.legend()
                ax.xaxis.set_major_locator(plt.MaxNLocator(8))
                fig.autofmt_xdate()
                canvas.draw()

    symbol_menu.bind("<<ComboboxSelected>>", plot_selected_symbol)

    # === TABLEAU DU PORTEFEUILLE
    style = ttk.Style()
    style.configure("Treeview", rowheight=25)
    style.map('Treeview', background=[('selected', '#007BFF')])
    style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

    table = ttk.Treeview(root, columns=("Symbole", "Quantité", "Dernier prix", "Valeur totale"), show="headings")
    for col in table["columns"]:
        table.heading(col, text=col)
        table.column(col, anchor="center", width=150)
    table.pack(fill="x", padx=20, pady=10)

    # === SUPPRESSION ACTIF
    def remove_selected():
        selected = table.selection()
        if not selected:
            messagebox.showinfo("Info", "Sélectionnez un actif à supprimer.")
            return
        values = table.item(selected[0])["values"]
        symbol = values[0]
        if symbol in portfolio:
            del portfolio[symbol]
            save_portfolio()
            update_symbol_list()
            update_portfolio_table()

    tk.Button(root, text="Supprimer l'actif sélectionné", command=remove_selected, bg="#dc3545", fg="white").pack(pady=5)

    # === TOTAL PORTEFEUILLE
    portfolio_total_var = tk.StringVar(value="Total portefeuille : 0.00 $")
    tk.Label(root, textvariable=portfolio_total_var, font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=5)

    def update_symbol_list():
        symbol_menu["values"] = list(portfolio.keys())

    def update_portfolio_table():
        for row in table.get_children():
            table.delete(row)

        total = 0.0
        for idx, (symbol, data) in enumerate(portfolio.items()):
            qty = data["quantity"]
            last_price = data["last_price"]
            total_value = round(qty * last_price, 2)
            total += total_value
            table.insert("", "end", values=(
                symbol,
                qty,
                f"{last_price:.2f} $",
                f"{total_value:.2f} $"
            ), tags=("oddrow" if idx % 2 == 0 else "evenrow"))

        table.tag_configure("oddrow", background="#ffffff")
        table.tag_configure("evenrow", background="#e9e9e9")

        portfolio_total_var.set(f"Total portefeuille : {total:.2f} $")

    update_symbol_list()
    update_portfolio_table()

    root.mainloop()

# === DÉMARRAGE
if __name__ == "__main__":
    start_ui()
