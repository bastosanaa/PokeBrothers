import sqlite3
import uuid
import customtkinter as ctk
from tkinter import messagebox
from models.ItemInventario import ItemInventario
from models.Carta import Carta
from services.pokeapi_service import buscar_carta_por_id
from PIL import Image
import requests
from io import BytesIO
from pages.search_cards import SearchCardsPage

class InventarioPage(ctk.CTkFrame):
    """
    Página de Inventário do Colecionador: permite adicionar e remover cartas do inventário.
    """
    SLOTS_POR_LINHA = 5
    _MAX_CARTAS = 500
    def __init__(self, master, colecionador):
        super().__init__(master, corner_radius=12)
        self.colecionador = colecionador
        self._inventarioLotado = False
        self._carregar_inventario()
        self._build()

    def _carregar_inventario(self):
        conn = sqlite3.connect("inventario.db")
        cur = conn.cursor()
        cur.execute("SELECT id, carta_id, quantidade FROM inventario WHERE colecionador_id=?", (self.colecionador.get_id(),))
        rows = cur.fetchall()
        conn.close()
        inventario = []
        for row in rows:
            carta = buscar_carta_por_id(row[1])
            if carta:
                inventario.append(ItemInventario(carta, quantidade=row[2], id=row[0]))
        self.colecionador.set_inventario(inventario)

    def _build(self):
        ctk.CTkLabel(self, text="Inventário", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 20))

        btn_add = ctk.CTkButton(self, text="+ Adicionar Carta", command=self._abrir_modal_adicionar)
        btn_add.pack(pady=(0, 15))

        self.frame_cartas = ctk.CTkFrame(self, corner_radius=10)
        self.frame_cartas.pack(fill="both", expand=True, padx=10, pady=10)
        self._renderizar_cartas()

    def _abrir_modal_adicionar(self):
        # Verifica se o inventário está lotado ANTES de abrir a busca
        total_cartas = sum(item.get_quantidade() for item in self.colecionador.get_inventario())
        if total_cartas >= self._MAX_CARTAS:
            self._inventarioLotado = True
            messagebox.showwarning("Inventário Lotado", "Número Máximo de cartas atingido")
            return
        self._inventarioLotado = False
        topo = ctk.CTkToplevel(self)
        topo.title("Adicionar Carta ao Inventário")
        topo.geometry("800x600")
        SearchCardsPage(
            master=topo,
            on_card_select=lambda carta: self._abrir_modal_quantidade(carta, topo)
        ).pack(fill="both", expand=True)

    def _abrir_modal_quantidade(self, carta: Carta, topo_search):
        topo_search.destroy()
        # Calcula o máximo que pode adicionar sem ultrapassar o limite
        total_cartas = sum(item.get_quantidade() for item in self.colecionador.get_inventario())
        max_adicionar = self._MAX_CARTAS - total_cartas
        modal = ctk.CTkToplevel(self)
        modal.title("Quantidade de Cartas")
        modal.geometry("300x180")
        ctk.CTkLabel(modal, text=f"Adicionar '{carta.nome}' ao inventário", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 10))
        frame = ctk.CTkFrame(modal)
        frame.pack(pady=10)
        quantidade = ctk.IntVar(value=1)
        # Funções de incremento/decremento
        def aumentar():
            if quantidade.get() < max_adicionar:
                quantidade.set(quantidade.get() + 1)
        def diminuir():
            if quantidade.get() > 1:
                quantidade.set(quantidade.get() - 1)
        # Funções para auto-repetição ao segurar
        def start_auto_repeat(func):
            def repeat():
                func()
                nonlocal after_id
                after_id = modal.after(60, repeat)
            after_id = None
            def on_press(event=None):
                repeat()
            def on_release(event=None):
                if after_id:
                    modal.after_cancel(after_id)
            return on_press, on_release
        # Botão menos
        btn_menos = ctk.CTkButton(frame, text="-", width=32, command=diminuir)
        btn_menos.grid(row=0, column=0, padx=5)
        menos_press, menos_release = start_auto_repeat(diminuir)
        btn_menos.bind('<ButtonPress-1>', menos_press)
        btn_menos.bind('<ButtonRelease-1>', menos_release)
        # Botão mais
        btn_mais = ctk.CTkButton(frame, text="+", width=32, command=aumentar)
        btn_mais.grid(row=0, column=2, padx=5)
        mais_press, mais_release = start_auto_repeat(aumentar)
        btn_mais.bind('<ButtonPress-1>', mais_press)
        btn_mais.bind('<ButtonRelease-1>', mais_release)
        # Label quantidade
        lbl_qtd = ctk.CTkLabel(frame, textvariable=quantidade, width=40)
        lbl_qtd.grid(row=0, column=1, padx=5)
        def confirmar():
            self._adicionar_carta_confirmada(carta, quantidade.get())
            modal.destroy()
        ctk.CTkButton(modal, text="Adicionar", command=confirmar).pack(pady=(50, 0))

    def _adicionar_carta_confirmada(self, carta: Carta, qtd: int):
        # Verifica se já existe a carta no inventário
        for item in self.colecionador.get_inventario():
            if item.get_carta().id == carta.id:
                item.set_quantidade(item.get_quantidade() + qtd)
                self._atualizar_quantidade_db(item.get_id(), item.get_quantidade())
                break
        else:
            novo_item = ItemInventario(carta, quantidade=qtd)
            self._adicionar_item_db(novo_item)
            self.colecionador.adicionar_item_inventario(novo_item)
        self._renderizar_cartas()

    def _adicionar_item_db(self, item: ItemInventario):
        conn = sqlite3.connect("inventario.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO inventario (id, colecionador_id, carta_id, quantidade) VALUES (?, ?, ?, ?)",
            (item.get_id(), self.colecionador.get_id(), item.get_carta().id, item.get_quantidade())
        )
        conn.commit()
        conn.close()

    def _atualizar_quantidade_db(self, item_id, nova_quantidade):
        conn = sqlite3.connect("inventario.db")
        cur = conn.cursor()
        cur.execute(
            "UPDATE inventario SET quantidade=? WHERE id=?",
            (nova_quantidade, item_id)
        )
        conn.commit()
        conn.close()

    def _remover_carta(self, item_id: str):
        inventario = self.colecionador.get_inventario()
        for item in inventario:
            if item.get_id() == item_id:
                if item.get_quantidade() > 1:
                    item.set_quantidade(item.get_quantidade() - 1)
                    self._atualizar_quantidade_db(item_id, item.get_quantidade())
                else:
                    inventario.remove(item)
                    self._remover_item_db(item_id)
                break
        self._renderizar_cartas()

    def _remover_item_db(self, item_id):
        conn = sqlite3.connect("inventario.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM inventario WHERE id=?", (item_id,))
        conn.commit()
        conn.close()

    def _renderizar_cartas(self):
        for widget in self.frame_cartas.winfo_children():
            widget.destroy()

        inventario = self.colecionador.get_inventario()
        if not inventario:
            ctk.CTkLabel(self.frame_cartas, text="Nenhuma carta no inventário.").pack(pady=20)
            return

        for idx, item in enumerate(inventario):
            row = idx // self.SLOTS_POR_LINHA
            col = idx % self.SLOTS_POR_LINHA
            self._criar_widget_carta(self.frame_cartas, item, row, col)

    def _criar_widget_carta(self, parent, item: ItemInventario, row, col):
        carta = item.get_carta()
        frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#232323")
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="n")

        # Imagem da carta
        img = self._carregar_imagem_url(carta.imagem_url)
        if img:
            lbl_img = ctk.CTkLabel(frame, image=img, text="")
            lbl_img.image = img
            lbl_img.pack(pady=(5, 0))
        else:
            ctk.CTkLabel(frame, text="[imagem]").pack(pady=(5, 0))

        # Nome e quantidade
        ctk.CTkLabel(frame, text=carta.nome, font=ctk.CTkFont(size=13, weight="bold")).pack()
        ctk.CTkLabel(frame, text=f"Qtd: {item.get_quantidade()}").pack()

        # Botão de exclusão (ícone pequeno)
        btn_del = ctk.CTkButton(
            frame,
            text="🗑️",
            width=24,
            height=24,
            fg_color="#d9534f",
            text_color="white",
            font=ctk.CTkFont(size=14),
            command=lambda i=item.get_id(): self._remover_carta(i)
        )
        btn_del.pack(pady=(5, 0))

    @staticmethod
    def _carregar_imagem_url(url, size=(90, 126)):
        try:
            response = requests.get(url, timeout=5)
            image = Image.open(BytesIO(response.content))
            return ctk.CTkImage(light_image=image, dark_image=image, size=size)
        except Exception:
            return None