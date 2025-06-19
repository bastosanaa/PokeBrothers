import customtkinter as ctk
import requests
from PIL import Image
from io import BytesIO
from models.Simulacao import SimulacaoTroca
from pages.search_cards import SearchCardsPage
from pages.local_search_cards import LocalSearchCardsPage
from models.ItemTroca import ItemTroca
from models.Carta import Carta
from tkinter import messagebox

DOLLAR_TO_REAL = 5.0


class SimulacaoTrocaPage(ctk.CTkFrame):


    SLOTS_POR_PAINEL = 10
    COLUNAS = 5
    """
    Página para simular trocas de cartas entre colecionadores,
    com painéis de cartas oferecidas e recebidas.
    """

    def __init__(self, master, inventario=None, lista_desejos=None):
        super().__init__(master, corner_radius=12)
        self.inventario = inventario or []
        self.lista_desejos = lista_desejos or []
        self.simulacao = SimulacaoTroca(limite_percentual=10.0)
        self.ofertados_frames = []
        self.recebidos_frames = []
        # atributos simples
        self.total_ofertados: float = 0.0
        self.total_recebidos: float = 0.0
        self.status_text: str = "Indefinido (adicione pelo menos uma carta em cada lado da simulação)"
        self._build()

    def _build(self):
        # Título da página
        ctk.CTkLabel(
            self, text="Simular Troca", font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, columnspan=2, pady=(10, 20))

        # Layout de colunas
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Painel de cartas ofertadas
        painel_ofertados = ctk.CTkFrame(
            self, corner_radius=10, fg_color="#2b2b2b"
        )
        painel_ofertados.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self._montar_painel(
            painel=painel_ofertados,
            titulo="Cartas Oferecidas",
            lista_frames=self.ofertados_frames,
            cmd_add=self._adicionar_carta,
            ofertado=True,
        )

        # Painel de cartas recebidas
        painel_recebidos = ctk.CTkFrame(
            self, corner_radius=10, fg_color="#2b2b2b"
        )
        painel_recebidos.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self._montar_painel(
            painel=painel_recebidos,
            titulo="Cartas Recebidas",
            lista_frames=self.recebidos_frames,
            cmd_add=self._adicionar_carta,
            ofertado=False,
        )

        self.lbl_status = ctk.CTkLabel(
            self,
            text=self.status_text,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#4E73D8",
        )
        self.lbl_status.grid(row=2, column=0, columnspan=2, pady=(0, 5))

        botao_salvar = ctk.CTkButton(
            self, text="Registrar Simulação", command=self._registrar_simulacao
        )
        botao_salvar.grid(row=3, column=0, columnspan=2, pady=(10, 20))

    def _montar_painel(self, painel, titulo, lista_frames, cmd_add, ofertado: bool):
        ctk.CTkLabel(
            painel,
            text=titulo,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=self.COLUNAS, pady=(10, 5))

        # Label de total
        lbl_total = ctk.CTkLabel(
            painel,
            text=(
                f"Valor total: R${self.total_ofertados:,.2f}"
                if ofertado
                else f"Valor total: R${self.total_recebidos:,.2f}"
            ),
            anchor="e",
        )
        lbl_total.grid(
            row=1, column=0, columnspan=self.COLUNAS, sticky="e", padx=10
        )

        # Slots de cartas
        frame_grid = ctk.CTkFrame(
            painel, corner_radius=6, fg_color="#1a1a1a"
        )
        frame_grid.grid(
            row=2, column=0, columnspan=self.COLUNAS, padx=10, pady=(5, 10), sticky="nsew"
        )
        for idx in range(self.SLOTS_POR_PAINEL):
            linha = idx // self.COLUNAS
            coluna = idx % self.COLUNAS
            slot = ctk.CTkFrame(
                frame_grid,
                width=130,
                height=200,
                fg_color="#333333",
                corner_radius=6,
            )
            slot.grid(row=linha, column=coluna, padx=5, pady=5)
            btn = ctk.CTkButton(
                slot, text="+ Add", command=lambda i=idx: cmd_add(i, ofertado=ofertado)
            )
            btn.place(relx=0.5, rely=0.5, anchor="center")
            lista_frames.append((slot, ofertado))

        # Badge de diferença
        lbl_diff = ctk.CTkLabel(
            painel,
            text=f"{self.simulacao.equilibrio:.0f}%",
            fg_color="#4E73D8",
            text_color="black",
            corner_radius=10,
            padx=8,
            pady=4,
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        lbl_diff.grid(row=3, column=0, columnspan=self.COLUNAS, pady=(0, 10))

        if ofertado:
            self.lbl_total_ofertados = lbl_total
            self.lbl_diff_ofertados = lbl_diff
            self.badge_of = lbl_diff
        else:
            self.lbl_total_recebidos = lbl_total
            self.lbl_diff_recebidos = lbl_diff
            self.badge_rc = lbl_diff

    def _adicionar_carta(self, indice:int ,ofertado: bool):
                self._escolher_fonte_carta(ofertado=ofertado, indice=indice)


    def _escolher_fonte_carta(self, ofertado: bool, indice: int):
        """
        Modal que pergunta ao usuário se ele quer:
          • Buscar cartas na API (SearchCards)
          • Selecionar do Inventário (se ofertado) ou da Lista de Desejos (se ofertante)
        """
        topo = ctk.CTkToplevel(self)
        topo.title("De onde você quer adicionar?")
        topo.geometry("400x150")
        # Escolha o texto e a função correta
        if not ofertado:
            txt_lista = "Selecionar da Lista de Desejos"
            cmd_lista = lambda: self._selecionar_da_lista_desejos(indice, topo)
        else:
            txt_lista = "Selecionar do Inventário"
            cmd_lista = lambda: self._selecionar_do_inventario(indice, topo)

        # Botão buscar na API
        ctk.CTkButton(
            topo,
            text="Pesquisar Cartas",
            command=lambda:
                (topo.destroy(),
                    self._abrir_buscar_cartas(ofertado, indice))
        ).pack(fill="x", padx=20, pady=(20, 5))

        # Botão listar do inventário ou wishlist
        ctk.CTkButton(
            topo,
            text=txt_lista,
            command=lambda: (topo.destroy(), cmd_lista())
        ).pack(fill="x", padx=20, pady=(0, 20))

    def _abrir_buscar_cartas(self, ofertado: bool, indice: int):
        """
        Abre diretamente o SearchCardsPage em um novo modal.
        """
        topo = ctk.CTkToplevel(self)
        topo.title("Buscar Carta")
        topo.geometry("1200x800")
        SearchCardsPage(
            master=topo,
            on_card_select=lambda carta:
                (topo.destroy(),
                    self._selecionar_carta(ofertado, carta, indice, topo))
        ).pack(fill="both", expand=True)


    def _selecionar_do_inventario(self, indice):
        """Abre busca limitada às cartas do inventário."""
        if not self.inventario:
            return
        cartas = [item.get_carta() for item in self.inventario]
        topo = ctk.CTkToplevel(self)
        topo.title("Inventário")
        topo.geometry("800x600")
        LocalSearchCardsPage(
            master=topo,
            cards=cartas,
            on_card_select=lambda c: self._selecionar_ofertado(c, indice, topo)
        ).pack(fill="both", expand=True)

    def _selecionar_da_lista_desejos(self, indice):
        """Abre busca limitada às cartas da lista de desejos."""
        if not self.lista_desejos:
            return
        topo = ctk.CTkToplevel(self)
        topo.title("Lista de Desejos")
        topo.geometry("800x600")
        LocalSearchCardsPage(
            master=topo,
            cards=self.lista_desejos,
            on_card_select=lambda c: self._selecionar_recebido(c, indice, topo)
        ).pack(fill="both", expand=True)


    def _atualizar_totais_e_status(self):
        # Atualiza valores numéricos
        self.total_ofertados = self.simulacao.total_ofertados()
        self.total_recebidos = self.simulacao.total_recebidos()

        # Atualiza totais na UI
        self.lbl_total_ofertados.configure(
            text=f"Valor total: R${self.total_ofertados:,.2f}"
        )
        self.lbl_total_recebidos.configure(
            text=f"Valor total: R${self.total_recebidos:,.2f}"
        )

        # Se não houver cartas em ambos os lados, não calcula diferença
        if (
            len(self.simulacao.ofertados) < 1
            or len(self.simulacao.recebidos) < 1
        ):
            # Exibe placeholder
            self.lbl_diff_ofertados.configure(text="—")
            self.lbl_diff_recebidos.configure(text="—")
            # Mantém status indefinido
            self.lbl_status.configure(
                text=self.status_text, text_color="#4E73D8"
            )
            # Clear badges color
            neutral_color = "#4E73D8"
            self.badge_of.configure(fg_color=neutral_color)
            self.badge_rc.configure(fg_color=neutral_color)
            return

        # Atualiza badges
        self.lbl_diff_ofertados.configure(text=f"{self.simulacao.equilibrio:.0f}%")
        self.lbl_diff_recebidos.configure(text=f"{(-self.simulacao.equilibrio):.0f}%")


        if abs(self.simulacao.equilibrio) > self.simulacao.limite_percentual:
            cor = "#FF6B6B"
            status = "Desequilibrada ＞﹏＜"
            cor_status = cor
        else:
            cor = "#5EF06A"
            status = "Equilibrada (●'◡'●)"
            cor_status = cor

        self.badge_of.configure(fg_color=cor)
        self.badge_rc.configure(fg_color=cor)
        self.lbl_status.configure(text=status, text_color=cor_status)

    def _selecionar_carta(self, ofertado:bool, carta:Carta, indice, topo):
        topo.destroy()  
        item = ItemTroca(carta)
        # adiciona na simulação
        if ofertado:
            self.simulacao.adicionar_ofertado(item)
        else:
            self.simulacao.adicionar_recebido(item)

        # renderiza no slot apropriado
        self._renderizar_slot(ofertado=ofertado, indice=indice, item=item)
        self._atualizar_totais_e_status()

    def _renderizar_slot(self, ofertado: bool, indice: int, item: ItemTroca):
        """
        Limpa o frame do slot, exibe imagem, quantidade e botão de remover.
        """
        lista = self.ofertados_frames if ofertado else self.recebidos_frames
        slot_frame, total_var = lista[indice]

        # limpa conteúdo
        for w in slot_frame.winfo_children():
            w.destroy()

        # imagem clicável (não altera função de seleção já feito)
        img = self.load_image_from_url(item.carta.imagem_url, size=(100,140))
        if img:
            lbl_img = ctk.CTkLabel(slot_frame, image=img, text="")
            lbl_img.image = img
            lbl_img.pack(pady=(5,0))
        # preco
        preco_formatado = f"R${item.carta.preco_real:,.2f}"
        ctk.CTkLabel(
            slot_frame,
            text=preco_formatado
        ).pack()
        # botão remover
        ctk.CTkButton(
            slot_frame,
            text="X",
            fg_color="red",
            command=lambda i=item.id, o=ofertado: self._remover_item(i, o)
        ).pack(pady=(5,0))

    @staticmethod
    def load_image_from_url(url, size=(150, 210)):
        try:
            response = requests.get(url, timeout=5)
            image = Image.open(BytesIO(response.content))
            return ctk.CTkImage(light_image=image, dark_image=image, size=size)
        except Exception:
            return None


    def _remover_item(self, item_id: str, ofertado: bool):
        # Remove do modelo
        if ofertado:
            self.simulacao.remover_ofertado(item_id)
            items = self.simulacao.ofertados
            frames = self.ofertados_frames
        else:
            self.simulacao.remover_recebido(item_id)
            items = self.simulacao.recebidos
            frames = self.recebidos_frames

        # Re-renderiza todos os slots
        for idx, (frame_slot, _) in enumerate(frames):
            # limpa conteúdo
            for w in frame_slot.winfo_children():
                w.destroy()

            if idx < len(items):
                # renderiza a carta existente
                self._renderizar_slot(ofertado, idx, items[idx])
            else:
                # recria o botão de adicionar, chamando a função genérica
                btn = ctk.CTkButton(
                    frame_slot,
                    text="+ Add",
                    command=lambda i=idx, o=ofertado: self._adicionar_carta(i, o)
                )
                btn.place(relx=0.5, rely=0.5, anchor="center")

        # atualiza totais e status
        self._atualizar_totais_e_status()


    def _registrar_simulacao(self):
        # Verifica desequilíbrio
        if self.simulacao.esta_desequilibrada():
            # TODO: abrir modal de alerta antes de confirmar
            return
        # TODO: persistir simulação em backend ou local
        return messagebox.showinfo("Simulação", "Simulação registrada com sucesso!")
