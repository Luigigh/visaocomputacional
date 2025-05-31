import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import winsound
import threading
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use('TkAgg')

class View:
    """
    Classe responsável pela interface gráfica do sistema de análise de postura.
    Organiza os frames, menus, temas e interação com o usuário.
    """
    def __init__(self, root, controller):
        """
        Inicializa a interface, configura estilos, temas e cria os frames principais.
        :param root: Janela principal Tkinter.
        :param controller: Instância do Controller.
        """
        self.window = root
        self.controller = controller
        self.window.geometry("1600x900")
        self.window.title("Sistema de Análise de Postura")

        # Configuração de estilos
        self.style = ttk.Style()
        
        # Adiciona fonte personalizada
        self.fonte_titulo = ('Helvetica', 16, 'bold')
        self.fonte_normal = ('Helvetica', 10)
        self.fonte_pequena = ('Helvetica', 8)

        # Configuração de temas
        self.temas = {
            'Claro': {
                'bg': '#FFFFFF',
                'fg': '#000000',
                'accent': '#007BFF',
                'success': '#28A745',
                'warning': '#FFC107',
                'error': '#DC3545',
                'secondary': '#6C757D',
                'light': '#F8F9FA',
                'dark': '#343A40'
            },
            'Escuro': {
                'bg': '#2B2B2B',
                'fg': '#FFFFFF',
                'accent': '#0D6EFD',
                'success': '#198754',
                'warning': '#FFC107',
                'error': '#DC3545',
                'secondary': '#6C757D',
                'light': '#F8F9FA',
                'dark': '#343A40'
            },
            'Azul': {
                'bg': '#E3F2FD',
                'fg': '#000000',
                'accent': '#1976D2',
                'success': '#2E7D32',
                'warning': '#F57F17',
                'error': '#C62828',
                'secondary': '#546E7A',
                'light': '#ECEFF1',
                'dark': '#263238'
            }
        }
        self.tema_atual = 'Claro'
        self._aplicar_tema(self.tema_atual)

        # Variáveis para alertas
        self.alerta_thread = None
        self.alerta_ativo = False

        # Criar menu principal
        self._criar_menu()

        # Criar grid principal
        self.grid_principal = ttk.Frame(self.window)
        self.grid_principal.pack(fill="both", expand=True, padx=10, pady=10)

        # Configurar colunas do grid
        self.grid_principal.columnconfigure(0, weight=1)
        self.grid_principal.columnconfigure(1, weight=1)

        # Criar frames principais
        self._criar_frame_camera()
        self._criar_frame_configuracoes()

        # Iniciar atualização de estatísticas
        self._atualizar_estatisticas()

    def _criar_menu(self):
        """Cria o menu principal da aplicação"""
        self.menu_bar = tk.Menu(self.window)
        self.window.config(menu=self.menu_bar)

        # Menu Arquivo
        arquivo_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Arquivo", menu=arquivo_menu)
        arquivo_menu.add_command(label="Exportar Dados", command=self._mostrar_exportacao)
        arquivo_menu.add_separator()
        arquivo_menu.add_command(label="Sair", command=self.window.quit)

        # Menu Configurações
        config_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Configurações", menu=config_menu)
        config_menu.add_command(label="Preferências", command=self._mostrar_preferencias)
        
        # Submenu de Temas
        temas_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="Temas", menu=temas_menu)
        for tema in self.temas.keys():
            temas_menu.add_command(label=tema, command=lambda t=tema: self._aplicar_tema(t))

        # Menu Ajuda
        ajuda_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ajuda", menu=ajuda_menu)
        ajuda_menu.add_command(label="Sobre", command=self._mostrar_sobre)

    def _configurar_estilos(self):
        """Configura os estilos da interface"""
        self.style.configure('TFrame', background=self.temas[self.tema_atual]['bg'])
        self.style.configure('TLabel', background=self.temas[self.tema_atual]['bg'], 
                           foreground=self.temas[self.tema_atual]['fg'])
        self.style.configure('TButton', background=self.temas[self.tema_atual]['accent'])
        self.style.configure('TLabelframe', background=self.temas[self.tema_atual]['bg'])
        self.style.configure('TLabelframe.Label', background=self.temas[self.tema_atual]['bg'],
                           foreground=self.temas[self.tema_atual]['fg'])

    def _aplicar_tema(self, tema):
        """Aplica um tema à interface"""
        self.tema_atual = tema
        self.window.configure(bg=self.temas[tema]['bg'])
        self._configurar_estilos()
        self._atualizar_cores_interface()

    def _atualizar_cores_interface(self):
        """Atualiza as cores de todos os elementos da interface"""
        for widget in self.window.winfo_children():
            if isinstance(widget, (ttk.Frame, ttk.LabelFrame)):
                widget.configure(style='TFrame')
            elif isinstance(widget, ttk.Label):
                widget.configure(style='TLabel')
            elif isinstance(widget, ttk.Button):
                widget.configure(style='TButton')

    def _mostrar_preferencias(self):
        """Mostra a janela de preferências"""
        pref_window = tk.Toplevel(self.window)
        pref_window.title("Preferências")
        pref_window.geometry("400x300")
        pref_window.configure(bg=self.temas[self.tema_atual]['bg'])

        # Frame para configurações
        frame = ttk.Frame(pref_window)
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Configurações de alerta
        ttk.Label(frame, text="Configurações de Alerta").pack(pady=10)
        
        # Tempo para alerta
        ttk.Label(frame, text="Tempo para alerta (segundos):").pack()
        tempo_var = tk.StringVar(value="10")
        ttk.Entry(frame, textvariable=tempo_var).pack(pady=5)

        # Sensibilidade
        ttk.Label(frame, text="Sensibilidade do detector:").pack()
        sensibilidade_var = tk.StringVar(value="Média")
        ttk.Combobox(frame, textvariable=sensibilidade_var,
                    values=["Baixa", "Média", "Alta"]).pack(pady=5)

        # Botões
        ttk.Button(frame, text="Salvar",
                  command=lambda: self._salvar_preferencias(tempo_var.get(),
                                                          sensibilidade_var.get())).pack(pady=10)
        ttk.Button(frame, text="Cancelar",
                  command=pref_window.destroy).pack()

    def _mostrar_exportacao(self):
        """Mostra a janela de exportação"""
        export_window = tk.Toplevel(self.window)
        export_window.title("Exportar Dados")
        export_window.geometry("400x200")
        export_window.configure(bg=self.temas[self.tema_atual]['bg'])

        frame = ttk.Frame(export_window)
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        ttk.Label(frame, text="Selecione o período:").pack(pady=10)

        # Datas
        ttk.Label(frame, text="Data Inicial:").pack()
        data_inicial = DateEntry(frame, width=12)
        data_inicial.pack(pady=5)

        ttk.Label(frame, text="Data Final:").pack()
        data_final = DateEntry(frame, width=12)
        data_final.pack(pady=5)

        # Botões
        ttk.Button(frame, text="Exportar CSV",
                  command=lambda: self._exportar_csv()).pack(pady=10)
        ttk.Button(frame, text="Cancelar",
                  command=export_window.destroy).pack()

    def _mostrar_sobre(self):
        """Mostra a janela Sobre"""
        messagebox.showinfo(
            "Sobre",
            "Sistema de Análise de Postura\n"
            "Versão 1.0\n\n"
            "Desenvolvido para monitorar e melhorar a postura corporal."
        )

    def _salvar_preferencias(self, tempo_alerta, sensibilidade):
        """Salva as preferências do usuário"""
        # Aqui você pode implementar a lógica para salvar as preferências
        messagebox.showinfo("Sucesso", "Preferências salvas com sucesso!")

    def _criar_frame_camera(self):
        """Cria o frame da câmera (lado esquerdo)"""
        self.camera_frame = ttk.LabelFrame(self.grid_principal, text="Câmera")
        self.camera_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Título com fonte personalizada
        titulo = ttk.Label(self.camera_frame, text="Visualização da Câmera",
                          font=self.fonte_titulo)
        titulo.pack(pady=10)
        
        # Área para exibir o vídeo com borda
        self.video_frame = ttk.Frame(self.camera_frame, style='Video.TFrame')
        self.video_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack(padx=2, pady=2)

        # Frame de status com ícone
        self.status_frame = ttk.Frame(self.camera_frame)
        self.status_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_icon = ttk.Label(self.status_frame, text="●",
                                    font=('Helvetica', 12))
        self.status_icon.pack(side="left", padx=5)
        
        self.status_label = ttk.Label(self.status_frame,
                                    text="Sistema pronto",
                                    font=self.fonte_normal)
        self.status_label.pack(side="left")

    def _criar_frame_configuracoes(self):
        """Cria o frame de configurações (lado direito)"""
        self.config_frame = ttk.Frame(self.grid_principal)
        self.config_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        # Criar frames de configuração
        self._criar_frame_controles()
        self._criar_frame_angulos()
        self._criar_frame_alertas()
        self._criar_frame_estatisticas()
        self._criar_frame_exportacao()
        self._criar_frame_rodape()

    def _criar_frame_controles(self):
        """Cria o frame de controles da câmera"""
        self.controles_frame = ttk.LabelFrame(self.config_frame, text="Controles de Câmera")
        self.controles_frame.pack(fill="x", padx=5, pady=5)

        # Grid para controles
        for i in range(4):
            self.controles_frame.columnconfigure(i, weight=1)

        # Resolução com ícone
        ttk.Label(self.controles_frame, text="📐 Resolução:",
                 font=self.fonte_normal).grid(row=0, column=0, padx=5, pady=5)
        self.resolucao_var = tk.StringVar(value="1280x720")
        self.resolucao_combo = ttk.Combobox(self.controles_frame, 
                                          textvariable=self.resolucao_var,
                                          values=["1280x720", "1920x1080", "800x600"],
                                          font=self.fonte_normal)
        self.resolucao_combo.grid(row=0, column=1, padx=5, pady=5)
        self.resolucao_combo.bind('<<ComboboxSelected>>', self._on_resolucao_change)

        # FPS com ícone
        ttk.Label(self.controles_frame, text="⚡ FPS:",
                 font=self.fonte_normal).grid(row=0, column=2, padx=5, pady=5)
        self.fps_var = tk.StringVar(value="30")
        self.fps_combo = ttk.Combobox(self.controles_frame,
                                    textvariable=self.fps_var,
                                    values=["15", "30", "60"],
                                    font=self.fonte_normal)
        self.fps_combo.grid(row=0, column=3, padx=5, pady=5)
        self.fps_combo.bind('<<ComboboxSelected>>', self._on_fps_change)

        # Brilho com slider
        ttk.Label(self.controles_frame, text="☀️ Brilho:",
                 font=self.fonte_normal).grid(row=1, column=0, padx=5, pady=5)
        self.brightness_scale = ttk.Scale(self.controles_frame,
                                        from_=0, to=100,
                                        orient="horizontal",
                                        command=self._on_brightness_change)
        self.brightness_scale.set(50)
        self.brightness_scale.grid(row=1, column=1, columnspan=3,
                                 padx=5, pady=5, sticky="ew")

        # Contraste com slider
        ttk.Label(self.controles_frame, text="🎨 Contraste:",
                 font=self.fonte_normal).grid(row=2, column=0, padx=5, pady=5)
        self.contrast_scale = ttk.Scale(self.controles_frame,
                                      from_=0, to=200,
                                      orient="horizontal",
                                      command=self._on_contrast_change)
        self.contrast_scale.set(100)
        self.contrast_scale.grid(row=2, column=1, columnspan=3,
                               padx=5, pady=5, sticky="ew")

    def _criar_frame_angulos(self):
        """Cria o frame para exibição dos ângulos"""
        self.angulos_frame = ttk.LabelFrame(self.config_frame, text="Ângulos Corporais")
        self.angulos_frame.pack(fill="x", padx=5, pady=5)

        # Labels para os ângulos
        self.angulo_pescoco_label = ttk.Label(self.angulos_frame,
                                            text="Ângulo do Pescoço: 0°",
                                            style='TLabel')
        self.angulo_pescoco_label.grid(row=0, column=0, padx=5, pady=5)

        self.angulo_coluna_label = ttk.Label(self.angulos_frame,
                                           text="Ângulo da Coluna: 0°",
                                           style='TLabel')
        self.angulo_coluna_label.grid(row=0, column=1, padx=5, pady=5)

    def _criar_frame_alertas(self):
        """Cria o frame para exibição de alertas e sugestões"""
        self.alertas_frame = ttk.LabelFrame(self.config_frame, text="Alertas e Sugestões")
        self.alertas_frame.pack(fill="x", padx=5, pady=5)

        # Frame para o alerta principal
        self.alerta_principal_frame = ttk.Frame(self.alertas_frame)
        self.alerta_principal_frame.pack(fill="x", padx=5, pady=5)
        
        self.alerta_label = ttk.Label(self.alerta_principal_frame,
                                    text="",
                                    style='TLabel')
        self.alerta_label.pack(pady=5)

        # Frame para as sugestões
        self.sugestoes_frame = ttk.Frame(self.alertas_frame)
        self.sugestoes_frame.pack(fill="x", padx=5, pady=5)
        
        self.sugestao_labels = []
        for i in range(3):
            label = ttk.Label(self.sugestoes_frame,
                            text="",
                            style='TLabel')
            label.pack(pady=2)
            self.sugestao_labels.append(label)

    def _criar_frame_estatisticas(self):
        """Cria o frame de estatísticas com gráficos melhorados"""
        self.estatisticas_frame = ttk.LabelFrame(self.config_frame, text="Estatísticas")
        self.estatisticas_frame.pack(fill="x", padx=5, pady=5)

        # Frame para estatísticas do dia
        self.estatisticas_dia_frame = ttk.Frame(self.estatisticas_frame)
        self.estatisticas_dia_frame.pack(fill="x", padx=5, pady=5)

        # Labels para estatísticas do dia
        self.tempo_correto_label = ttk.Label(self.estatisticas_dia_frame,
                                           text="Tempo em postura correta: 0 min",
                                           font=self.fonte_normal)
        self.tempo_correto_label.grid(row=0, column=0, padx=5, pady=2)

        self.tempo_incorreto_label = ttk.Label(self.estatisticas_dia_frame,
                                             text="Tempo em postura incorreta: 0 min",
                                             font=self.fonte_normal)
        self.tempo_incorreto_label.grid(row=0, column=1, padx=5, pady=2)

        self.percentual_label = ttk.Label(self.estatisticas_dia_frame,
                                        text="Percentual correto: 0%",
                                        font=self.fonte_normal)
        self.percentual_label.grid(row=0, column=2, padx=5, pady=2)

        # Cria figura do matplotlib com estilo moderno
        self.fig = plt.Figure(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor(self.temas[self.tema_atual]['bg'])
        
        # Adiciona subplot com estilo moderno
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(self.temas[self.tema_atual]['light'])
        
        # Configura estilo do gráfico
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        
        # Cria canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.estatisticas_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def _criar_frame_exportacao(self):
        """Cria o frame para exportação de dados"""
        self.exportacao_frame = ttk.LabelFrame(self.config_frame, text="Exportação de Dados")
        self.exportacao_frame.pack(fill="x", padx=5, pady=5)

        # Frame para seleção de período
        self.periodo_frame = ttk.Frame(self.exportacao_frame)
        self.periodo_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(self.periodo_frame, text="Data Inicial:").grid(row=0, column=0, padx=5, pady=5)
        self.data_inicial = DateEntry(self.periodo_frame, width=12, background='darkblue',
                                    foreground='white', borderwidth=2)
        self.data_inicial.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.periodo_frame, text="Data Final:").grid(row=0, column=2, padx=5, pady=5)
        self.data_final = DateEntry(self.periodo_frame, width=12, background='darkblue',
                                  foreground='white', borderwidth=2)
        self.data_final.grid(row=0, column=3, padx=5, pady=5)

        # Frame para botão de exportação
        self.botoes_frame = ttk.Frame(self.exportacao_frame)
        self.botoes_frame.pack(fill="x", padx=5, pady=5)

        self.botao_csv = ttk.Button(self.botoes_frame,
                                  text="Exportar para CSV",
                                  command=self._exportar_csv)
        self.botao_csv.grid(row=0, column=0, padx=5, pady=5)

    def _criar_frame_rodape(self):
        """Cria o frame do rodapé com botões de controle"""
        self.bottom_frame = ttk.Frame(self.config_frame)
        self.bottom_frame.pack(fill="x", padx=5, pady=5)
        
        self.botao_iniciar = ttk.Button(self.bottom_frame, 
                                      text="Iniciar Monitoramento",
                                      command=self.controller.iniciar_monitoramento)
        self.botao_iniciar.grid(row=0, column=0, padx=5, pady=5)

        self.botao_parar = ttk.Button(self.bottom_frame,
                                    text="Parar Monitoramento",
                                    command=self.controller.parar_monitoramento)
        self.botao_parar.grid(row=0, column=1, padx=5, pady=5)

    def atualizar_video(self, photo):
        """
        Atualiza o frame do vídeo na interface.
        """
        self.video_label.configure(image=photo)
        self.video_label.image = photo

    def atualizar_status(self, mensagem, tipo="info"):
        """
        Atualiza o status do sistema na interface, exibindo mensagens e ícones.
        """
        cores = {
            "success": self.temas[self.tema_atual]['success'],
            "warning": self.temas[self.tema_atual]['warning'],
            "error": self.temas[self.tema_atual]['error'],
            "info": self.temas[self.tema_atual]['accent']
        }
        
        icones = {
            "success": "✓",
            "warning": "⚠",
            "error": "✕",
            "info": "ℹ"
        }
        
        self.status_icon.configure(
            text=icones.get(tipo, "ℹ"),
            foreground=cores.get(tipo, self.temas[self.tema_atual]['accent'])
        )
        self.status_label.configure(text=mensagem)

    def atualizar_angulos(self, angulos):
        """
        Atualiza os labels dos ângulos corporais exibidos na interface.
        """
        self.angulo_pescoco_label.configure(
            text=f"Ângulo do Pescoço: {angulos['pescoco']:.1f}°"
        )
        self.angulo_coluna_label.configure(
            text=f"Ângulo da Coluna: {angulos['coluna']:.1f}°"
        )

    def ativar_alertas(self, tipo_erro, sugestoes):
        """
        Ativa alertas visuais e sonoros na interface.
        """
        if not self.alerta_ativo:
            self.alerta_ativo = True
            
            # Atualiza o alerta principal
            mensagens = {
                'coluna_curvada': "⚠️ Alerta: Coluna muito curvada!",
                'coluna_reta': "⚠️ Alerta: Coluna muito reta!",
                'pescoco_inclinado': "⚠️ Alerta: Pescoço muito inclinado!"
            }
            self.alerta_label.configure(
                text=mensagens.get(tipo_erro, "⚠️ Alerta: Postura incorreta!"),
                foreground="red"
            )
            
            # Atualiza as sugestões
            for i, sugestao in enumerate(sugestoes):
                if i < len(self.sugestao_labels):
                    self.sugestao_labels[i].configure(
                        text=f"• {sugestao}",
                        foreground="blue"
                    )
            
            # Inicia o alerta sonoro em uma thread separada
            self.alerta_thread = threading.Thread(target=self._tocar_alerta_sonoro)
            self.alerta_thread.daemon = True
            self.alerta_thread.start()

    def desativar_alertas(self):
        """
        Desativa os alertas visuais e sonoros.
        """
        self.alerta_ativo = False
        self.alerta_label.configure(text="")
        for label in self.sugestao_labels:
            label.configure(text="")

    def _tocar_alerta_sonoro(self):
        """
        Toca o alerta sonoro enquanto o alerta estiver ativo.
        """
        while self.alerta_ativo:
            winsound.Beep(1000, 500)  # Frequência 1000Hz, duração 500ms
            time.sleep(2)  # Espera 2 segundos entre os beeps

    def _on_resolucao_change(self, event):
        """
        Callback para mudança de resolução da câmera.
        """
        res = self.resolucao_var.get().split('x')
        self.controller.atualizar_configuracao_camera('resolution', (int(res[0]), int(res[1])))

    def _on_fps_change(self, event):
        """
        Callback para mudança de FPS da câmera.
        """
        self.controller.atualizar_configuracao_camera('fps', int(self.fps_var.get()))

    def _on_brightness_change(self, value):
        """
        Callback para mudança de brilho da câmera.
        """
        self.controller.atualizar_configuracao_camera('brightness', float(value))

    def _on_contrast_change(self, value):
        """
        Callback para mudança de contraste da câmera.
        """
        self.controller.atualizar_configuracao_camera('contrast', float(value))

    def _atualizar_estatisticas(self):
        """
        Atualiza as estatísticas do dia e o gráfico na interface.
        """
        try:
            # Atualiza estatísticas do dia
            resumo = self.controller.model.get_resumo_diario()
            self.tempo_correto_label.configure(
                text=f"Tempo em postura correta: {resumo['minutos_correto']} min"
            )
            self.tempo_incorreto_label.configure(
                text=f"Tempo em postura incorreta: {resumo['minutos_incorreto']} min"
            )
            self.percentual_label.configure(
                text=f"Percentual correto: {resumo['percentual_correto']:.1f}%"
            )

            # Atualiza gráfico
            self._atualizar_grafico()

            # Agenda próxima atualização
            self.window.after(5000, self._atualizar_estatisticas)  # Atualiza a cada 5 segundos
        except Exception as e:
            print(f"Erro ao atualizar estatísticas: {e}")

    def _atualizar_grafico(self):
        """
        Atualiza o gráfico de histórico de posturas.
        """
        try:
            # Limpa o gráfico
            self.ax.clear()
            
            # Obtém dados
            estatisticas = self.controller.model.get_estatisticas(dias=7)
            if not estatisticas:
                return
            
            # Prepara dados
            datas = [datetime.strptime(e['data'], '%Y-%m-%d').strftime('%d/%m') 
                    for e in estatisticas]
            corretos = [e['total_correto'] for e in estatisticas]
            incorretos = [e['total_incorreto'] for e in estatisticas]
            
            # Plota dados
            x = range(len(datas))
            width = 0.35
            
            self.ax.bar([i - width/2 for i in x], corretos, width,
                       label='Postura Correta',
                       color=self.temas[self.tema_atual]['success'])
            self.ax.bar([i + width/2 for i in x], incorretos, width,
                       label='Postura Incorreta',
                       color=self.temas[self.tema_atual]['warning'])
            
            # Configura eixos
            self.ax.set_xticks(x)
            self.ax.set_xticklabels(datas, rotation=45)
            self.ax.set_ylabel('Minutos')
            self.ax.set_title('Histórico de Posturas', pad=20)
            
            # Adiciona legenda
            self.ax.legend(loc='upper right')
            
            # Ajusta layout
            self.fig.tight_layout()
            
            # Atualiza canvas
            self.canvas.draw()
            
        except Exception as e:
            print(f"Erro ao atualizar gráfico: {e}")

    def _exportar_csv(self):
        """
        Exporta os dados para CSV conforme o período selecionado.
        """
        try:
            # Obtém datas selecionadas
            data_inicio = datetime.combine(self.data_inicial.get_date(), datetime.min.time())
            data_fim = datetime.combine(self.data_final.get_date(), datetime.max.time())

            # Exporta dados
            if self.controller.model.exportar_dados('csv', data_inicio, data_fim):
                messagebox.showinfo(
                    "Sucesso",
                    "Dados exportados com sucesso para o diretório 'exportacoes'!"
                )
            else:
                messagebox.showerror(
                    "Erro",
                    "Não foi possível exportar os dados. Verifique se existem dados no período selecionado."
                )
        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao exportar dados: {str(e)}"
            ) 