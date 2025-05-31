import unittest
import tkinter as tk
from models.model import Model
from controllers.controller import Controller
from views.view import View
import cv2
import numpy as np
from datetime import datetime, timedelta

class TestSistemaPostura(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Configuração inicial para todos os testes"""
        cls.root = tk.Tk()
        cls.model = Model()
        cls.controller = Controller(cls.model, cls.root)
        cls.view = View(cls.root, cls.controller)

    def setUp(self):
        """Configuração antes de cada teste"""
        self.model.db_connection.execute("DELETE FROM registros")
        self.model.db_connection.execute("DELETE FROM estatisticas_diarias")
        self.model.db_connection.commit()

    def test_captura_camera(self):
        """Testa a funcionalidade de captura da câmera"""
        self.controller.iniciar_monitoramento()
        self.assertTrue(self.controller.is_running)
        self.assertIsNotNone(self.controller.cap)
        self.controller.parar_monitoramento()

    def test_deteccao_postura(self):
        """Testa a detecção de postura"""
        # Simula landmarks do MediaPipe
        landmarks = {
            0: type('Landmark', (), {'x': 0.5, 'y': 0.5})(),  # nariz
            11: type('Landmark', (), {'x': 0.4, 'y': 0.4})(),  # ombro esquerdo
            12: type('Landmark', (), {'x': 0.6, 'y': 0.4})(),  # ombro direito
            23: type('Landmark', (), {'x': 0.4, 'y': 0.6})(),  # quadril esquerdo
            24: type('Landmark', (), {'x': 0.6, 'y': 0.6})()   # quadril direito
        }
        
        postura, tipo_erro = self.controller._analisar_postura(landmarks)
        self.assertIsNotNone(postura)
        self.assertIn(postura, ["Postura correta", "Postura incorreta - Coluna muito curvada",
                               "Postura incorreta - Coluna muito reta",
                               "Postura incorreta - Pescoço muito inclinado"])

    def test_registro_postura(self):
        """Testa o registro de posturas no banco de dados"""
        angulos = {'pescoco': 90, 'coluna': 85}
        sucesso = self.model.registrar_postura("Postura correta", 1, angulos)
        self.assertTrue(sucesso)

        # Verifica se o registro foi feito
        cursor = self.model.db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM registros")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)

    def test_estatisticas(self):
        """Testa a geração de estatísticas"""
        # Registra algumas posturas
        angulos = {'pescoco': 90, 'coluna': 85}
        self.model.registrar_postura("Postura correta", 5, angulos)
        self.model.registrar_postura("Postura incorreta", 3, angulos)

        # Verifica estatísticas
        estatisticas = self.model.get_estatisticas(dias=1)
        self.assertGreater(len(estatisticas), 0)
        self.assertIn('total_correto', estatisticas[0])
        self.assertIn('total_incorreto', estatisticas[0])

    def test_exportacao_dados(self):
        """Testa a exportação de dados"""
        # Registra alguns dados
        angulos = {'pescoco': 90, 'coluna': 85}
        self.model.registrar_postura("Postura correta", 5, angulos)
        
        # Testa exportação
        sucesso = self.model.exportar_dados(formato='csv')
        self.assertTrue(sucesso)

    def test_interface_temas(self):
        """Testa a mudança de temas na interface"""
        temas = ['Claro', 'Escuro', 'Azul']
        for tema in temas:
            self.view._aplicar_tema(tema)
            self.assertEqual(self.view.tema_atual, tema)

    def test_alertas(self):
        """Testa o sistema de alertas"""
        # Simula uma postura incorreta
        self.controller.duracao_postura_incorreta = 15
        self.controller._gerenciar_alertas("Postura incorreta - Coluna muito curvada", "coluna_curvada")
        self.assertTrue(self.controller.alerta_ativo)

    @classmethod
    def tearDownClass(cls):
        """Limpeza após todos os testes"""
        cls.root.destroy()

if __name__ == '__main__':
    unittest.main() 