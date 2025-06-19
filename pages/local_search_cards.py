import customtkinter as ctk
from typing import List
from models.Carta import Carta
from pages.search_cards import SearchCardsPage

class LocalSearchCardsPage(ctk.CTkFrame):
    """Exibe uma lista de cartas locais permitindo filtrar pelo nome."""
    def __init__(self, master, cards: List[Carta], on_card_select=None):
        super().__init__(master, corner_radius=12)
        self.cards = cards
        self.on_card_select = on_card_select
        self.var_search = ctk.StringVar()
        self._build()
        self._render_cards(self.cards)

    def _build(self):
        ctk.CTkLabel(
            self,
            text="Buscar Cartas",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        ctk.CTkEntry(
            self,
            textvariable=self.var_search,
            width=250
        ).grid(row=1, column=0, pady=5, padx=10, sticky="w")
        ctk.CTkButton(
            self,
            text="Buscar",
            command=self.on_search
        ).grid(row=1, column=1, padx=5)

        self.results_frame = ctk.CTkScrollableFrame(self, corner_radius=12)
        self.results_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10,0))
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

    def on_search(self):
        term = self.var_search.get().strip().lower()
        if term:
            filtered = [c for c in self.cards if term in c.nome.lower()]
        else:
            filtered = list(self.cards)
        self._render_cards(filtered)

    def _render_cards(self, cards: List[Carta]):
        for w in self.results_frame.winfo_children():
            w.destroy()
        if not cards:
            ctk.CTkLabel(self.results_frame, text="Nenhuma carta encontrada.").pack(pady=20)
            return
        grid_frame = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        grid_frame.pack(anchor="center", padx=10, pady=10)
        columns = 4
        for idx, card in enumerate(cards):
            row = idx // columns
            col = idx % columns
            SearchCardsPage.create_card_widget(self, grid_frame, card, row, col)

