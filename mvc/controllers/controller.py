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
    def __init__(self, model, root):
        self.model = model
        self.view = View(root, self)
        self.cap = None
        self.is_running = False
        
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
        """Aplica as configurações atuais na câmera"""
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
        """Atualiza uma configuração específica da câmera"""
        if setting in self.camera_settings:
            self.camera_settings[setting] = value
            if self.is_running:
                self._aplicar_configuracoes_camera()

    def parar_monitoramento(self):
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.view.atualizar_status("Monitoramento parado!", "info")

    def _calcular_angulo(self, p1, p2, p3):
        """Calcula o ângulo entre três pontos"""
        a = np.array(p1)
        b = np.array(p2)
        c = np.array(p3)
        
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        angle = np.arccos(cosine_angle)
        
        return np.degrees(angle)

    def _analisar_postura(self, landmarks):
        """Analisa a postura e calcula os ângulos"""
        if landmarks is None:
            return None

        try:
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

            return postura, tipo_erro
        except Exception as e:
            print(f"Erro ao analisar postura: {e}")
            return None, None

    def _classificar_postura(self):
        """Classifica a postura baseado nos ângulos"""
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
        """Gerencia o sistema de alertas"""
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
        """Ativa os alertas visuais e sonoros"""
        try:
            sugestoes = self.sugestoes.get(tipo_erro, ["Ajuste sua postura"])
            self.view.ativar_alertas(tipo_erro, sugestoes)
        except Exception as e:
            print(f"Erro ao ativar alertas: {e}")

    def atualizar_frame(self):
        if self.is_running and self.cap is not None:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    raise Exception("Erro ao capturar frame")

                # Aplica ajustes de brilho e contraste
                frame = self._aplicar_ajustes_imagem(frame)
                
                # Converte para RGB para o MediaPipe
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Processa o frame com MediaPipe
                results = self.pose.process(frame_rgb)
                
                # Desenha os landmarks se detectados
                if results.pose_landmarks:
                    self.mp_drawing.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        self.mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                    )
                    
                    # Analisa a postura
                    postura, tipo_erro = self._analisar_postura(results.pose_landmarks.landmark)
                    if postura:
                        self.view.atualizar_status(postura, "warning" if "incorreta" in postura else "success")
                
                # Converte o frame para RGB para exibição
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Converte para formato PIL
                image = Image.fromarray(frame)
                
                # Redimensiona mantendo proporção
                image.thumbnail((960, 720))
                
                # Converte para formato Tkinter
                photo = ImageTk.PhotoImage(image=image)
                
                # Atualiza o label na view
                self.view.atualizar_video(photo)
                
                # Agenda próxima atualização
                self.view.window.after(10, self.atualizar_frame)
            except Exception as e:
                self.view.atualizar_status(f"Erro na captura: {str(e)}", "error")
                self.parar_monitoramento()

    def _aplicar_ajustes_imagem(self, frame):
        """Aplica ajustes de brilho e contraste na imagem"""
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
        """Retorna as configurações atuais da câmera"""
        return self.camera_settings.copy()

    def get_available_cameras(self):
        """Retorna lista de câmeras disponíveis"""
        return self.available_cameras.copy() 