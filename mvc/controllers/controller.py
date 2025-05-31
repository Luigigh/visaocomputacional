from views.view import View
from models.model import Model
import cv2
from PIL import Image, ImageTk
import numpy as np
import mediapipe as mp
import math
import time
from datetime import datetime, timedelta

class Controller:
    """
    Classe responsável por controlar o fluxo do sistema de análise de postura.
    Gerencia a comunicação entre a View (interface) e o Model (dados), além de processar imagens e alertas.
    """
    def __init__(self, model, root):
        """
        Inicializa o Controller, configura variáveis, cache, câmera e integra com a View.
        :param model: Instância do Model para acesso ao banco de dados.
        :param root: Janela principal Tkinter.
        """
        self.model = model
        self.root = root  # Adiciona referência à janela principal
        self.view = View(root, self)
        self.cap = None
        self.is_running = False
        
        # Cache para frames
        self.frame_cache = []
        self.max_cache_size = 5
        
        # Otimização de processamento
        self.skip_frames = 2  # Processa 1 a cada 3 frames
        self.frame_count = 0
        
        # Configurações padrão da câmera
        self.camera_settings = {
            'resolution': (1280, 720),
            'fps': 30,
            'brightness': 10,
            'contrast': 1.2
        }
        
        # Lista de câmeras disponíveis
        self.available_cameras = self._get_available_cameras()

        # Inicializa MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            static_image_mode=False
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Dicionário para armazenar os ângulos
        self.angulos = {
            'pescoco': 0,
            'ombro_esquerdo': 0,
            'ombro_direito': 0,
            'coluna': 0
        }

        # Sistema de alertas
        self.ultimo_alerta = None
        self.tempo_ultimo_alerta = None
        self.duracao_postura_incorreta = 0
        self.alerta_ativo = False
        self.tempo_para_alerta = 10
        self.sugestoes = {
            'coluna_curvada': [
                "Sente-se com as costas apoiadas na cadeira",
                "Mantenha os pés apoiados no chão",
                "Ajuste a altura da cadeira"
            ],
            'coluna_reta': [
                "Relaxe um pouco a postura",
                "Mantenha uma leve curvatura natural",
                "Evite forçar a coluna"
            ],
            'pescoco_inclinado': [
                "Alinhe a cabeça com a coluna",
                "Mantenha o queixo paralelo ao chão",
                "Evite inclinar a cabeça para frente"
            ]
        }

    def _get_available_cameras(self):
        """Retorna lista de câmeras disponíveis no sistema"""
        available = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available

    def iniciar_monitoramento(self):
        """
        Inicia a captura da câmera e o monitoramento da postura.
        Aplica configurações iniciais e agenda a atualização dos frames.
        """
        if not self.is_running:
            try:
                # Tenta abrir a câmera
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    raise Exception("Não foi possível acessar a câmera")

                # Aplica configurações iniciais
                self._aplicar_configuracoes_camera()
                
                # Verifica se as configurações foram aplicadas
                width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                if width == 0 or height == 0:
                    raise Exception("Erro ao configurar resolução da câmera")

                self.is_running = True
                self.view.atualizar_status("Monitoramento iniciado com sucesso!", "success")
                self.atualizar_frame()
            except Exception as e:
                self.view.atualizar_status(f"Erro ao iniciar câmera: {str(e)}", "error")
                self.parar_monitoramento()

    def _aplicar_configuracoes_camera(self):
        """
        Aplica as configurações atuais (resolução, FPS, brilho, contraste) na câmera aberta.
        """
        if self.cap is not None:
            try:
                # Aplica resolução
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_settings['resolution'][0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_settings['resolution'][1])
                
                # Aplica FPS
                self.cap.set(cv2.CAP_PROP_FPS, self.camera_settings['fps'])
                
                # Aplica brilho e contraste
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.camera_settings['brightness'])
                self.cap.set(cv2.CAP_PROP_CONTRAST, self.camera_settings['contrast'])
                
                # Verifica se as configurações foram aplicadas
                width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                if width == 0 or height == 0:
                    raise Exception("Erro ao configurar câmera")
            except Exception as e:
                print(f"Erro ao aplicar configurações: {e}")
                raise

    def atualizar_configuracao_camera(self, setting, value):
        """
        Atualiza uma configuração específica da câmera (ex: brilho, contraste, resolução, FPS).
        """
        # Garante que o atributo existe
        if not hasattr(self, 'camera_settings') or self.camera_settings is None:
            self.camera_settings = {
                'resolution': (1280, 720),
                'fps': 30,
                'brightness': 10,
                'contrast': 1.2
            }
        if setting in self.camera_settings:
            self.camera_settings[setting] = value
            if self.cap is not None:
                self.cap.set(self._get_camera_property(setting), value)

    def parar_monitoramento(self):
        """
        Encerra o monitoramento e libera a câmera.
        """
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.view.atualizar_status("Monitoramento parado!", "info")

    def _calcular_angulo(self, p1, p2, p3):
        """
        Calcula o ângulo formado por três pontos (usado para análise de postura).
        """
        a = np.array(p1)
        b = np.array(p2)
        c = np.array(p3)
        
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        angle = np.arccos(cosine_angle)
        
        return np.degrees(angle)

    def _analisar_postura(self, landmarks):
        """
        Analisa os pontos do corpo detectados e classifica a postura.
        """
        if landmarks is None:
            return None

        try:
            # Otimização: Usa cache para landmarks similares
            cache_key = self._gerar_cache_key(landmarks)
            if cache_key in self.frame_cache:
                return self.frame_cache[cache_key]

            # Pontos para análise do pescoço
            nariz = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            ombro_esquerdo = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            ombro_direito = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            quadril_esquerdo = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
            quadril_direito = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]

            # Calcula ângulos
            self.angulos['pescoco'] = self._calcular_angulo(
                (nariz.x, nariz.y),
                (ombro_esquerdo.x, ombro_esquerdo.y),
                (ombro_direito.x, ombro_direito.y)
            )

            self.angulos['coluna'] = self._calcular_angulo(
                (ombro_esquerdo.x, ombro_esquerdo.y),
                (quadril_esquerdo.x, quadril_esquerdo.y),
                (quadril_direito.x, quadril_direito.y)
            )

            # Atualiza a view com os ângulos
            self.view.atualizar_angulos(self.angulos)

            # Analisa a postura
            postura, tipo_erro = self._classificar_postura()
            if postura:
                self._gerenciar_alertas(postura, tipo_erro)
                self.model.registrar_postura(postura, 1, self.angulos)

            # Atualiza cache
            self._atualizar_cache(cache_key, (postura, tipo_erro))

            return postura, tipo_erro
        except Exception as e:
            print(f"Erro ao analisar postura: {e}")
            return None, None

    def _classificar_postura(self):
        """
        Classifica a postura com base nos ângulos calculados.
        """
        try:
            if self.angulos['coluna'] < 70:
                return "Postura incorreta - Coluna muito curvada", "coluna_curvada"
            elif self.angulos['coluna'] > 110:
                return "Postura incorreta - Coluna muito reta", "coluna_reta"
            elif self.angulos['pescoco'] < 60:
                return "Postura incorreta - Pescoço muito inclinado", "pescoco_inclinado"
            else:
                return "Postura correta", None
        except Exception as e:
            print(f"Erro ao classificar postura: {e}")
            return None, None

    def _gerenciar_alertas(self, postura, tipo_erro):
        """
        Gerencia o sistema de alertas visuais e sonoros conforme a postura detectada.
        """
        try:
            agora = datetime.now()
            
            if "incorreta" in postura:
                if not self.alerta_ativo:
                    self.alerta_ativo = True
                    self.tempo_ultimo_alerta = agora
                    self.duracao_postura_incorreta = 0
                else:
                    self.duracao_postura_incorreta += 1
                    
                if self.duracao_postura_incorreta >= self.tempo_para_alerta:
                    self._ativar_alertas(tipo_erro)
            else:
                self.alerta_ativo = False
                self.duracao_postura_incorreta = 0
                self.view.desativar_alertas()
        except Exception as e:
            print(f"Erro ao gerenciar alertas: {e}")

    def _ativar_alertas(self, tipo_erro):
        """
        Ativa alertas visuais e sonoros na interface.
        """
        try:
            sugestoes = self.sugestoes.get(tipo_erro, ["Ajuste sua postura"])
            self.view.ativar_alertas(tipo_erro, sugestoes)
        except Exception as e:
            print(f"Erro ao ativar alertas: {e}")

    def atualizar_frame(self):
        """
        Atualiza o frame da câmera, processa a imagem e agenda a próxima atualização.
        """
        if self.is_running and self.cap is not None:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    raise Exception("Erro ao capturar frame")

                # Otimização: Redimensiona o frame para processamento mais rápido
                frame = cv2.resize(frame, (640, 480))
                
                # Otimização: Processa apenas alguns frames
                self.frame_count += 1
                if self.frame_count % self.skip_frames != 0:
                    # Aplica ajustes de brilho e contraste
                    frame = self._aplicar_ajustes_imagem(frame)
                    # Converte para formato Tkinter
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                    self.view.atualizar_video(photo)
                    self.root.after(10, self.atualizar_frame)
                    return

                # Aplica ajustes de brilho e contraste
                frame = self._aplicar_ajustes_imagem(frame)

                # Processa o frame com MediaPipe
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(frame_rgb)

                if results.pose_landmarks:
                    # Desenha os landmarks
                    self.mp_drawing.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        self.mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                    )

                    # Analisa a postura
                    self._analisar_postura(results.pose_landmarks.landmark)

                # Converte para formato Tkinter
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                self.view.atualizar_video(photo)

                # Agenda próxima atualização
                self.root.after(10, self.atualizar_frame)

            except Exception as e:
                print(f"Erro ao atualizar frame: {e}")
                self.parar_monitoramento()

    def _aplicar_ajustes_imagem(self, frame):
        """
        Aplica ajustes de brilho e contraste no frame da câmera.
        """
        try:
            brightness = self.camera_settings['brightness']
            contrast = self.camera_settings['contrast']
            
            # Aplica contraste
            frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=brightness)
            return frame
        except Exception as e:
            print(f"Erro ao aplicar ajustes de imagem: {e}")
            return frame

    def get_camera_settings(self):
        """
        Retorna uma cópia das configurações atuais da câmera.
        """
        return self.camera_settings.copy()

    def get_available_cameras(self):
        """
        Retorna a lista de câmeras disponíveis no sistema.
        """
        return self.available_cameras.copy()

    def _gerar_cache_key(self, landmarks):
        """
        Gera uma chave única para o cache baseada nos principais pontos do corpo.
        """
        try:
            # Usa apenas os pontos principais para gerar a chave
            pontos = [
                landmarks[self.mp_pose.PoseLandmark.NOSE.value],
                landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value],
                landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            ]
            return tuple((p.x, p.y) for p in pontos)
        except:
            return None

    def _atualizar_cache(self, key, value):
        """
        Atualiza o cache de frames processados para otimização.
        """
        if key is None:
            return

        # Adiciona ao cache
        self.frame_cache.append((key, value))
        
        # Remove itens antigos se necessário
        if len(self.frame_cache) > self.max_cache_size:
            self.frame_cache.pop(0) 