import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import os
from typing import List, Dict, Any, Tuple

class Model:
    """
    Classe responsável pelo gerenciamento dos dados e interação com o banco SQLite.
    Armazena registros de postura, estatísticas e exportação de dados.
    """
    def __init__(self):
        """
        Inicializa o banco de dados e cria as tabelas necessárias.
        """
        self.db_connection = sqlite3.connect('postura.db')
        self._criar_tabelas()

    def _criar_tabelas(self):
        """
        Cria as tabelas do banco de dados se não existirem.
        """
        cursor = self.db_connection.cursor()
        
        # Remove tabelas existentes para recriar com a nova estrutura
        cursor.execute('DROP TABLE IF EXISTS registros')
        cursor.execute('DROP TABLE IF EXISTS estatisticas_diarias')
        
        # Tabela de registros de postura
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora DATETIME,
                tipo_postura TEXT,
                duracao INTEGER,
                angulo_pescoco REAL,
                angulo_coluna REAL
            )
        ''')

        # Tabela de estatísticas diárias
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estatisticas_diarias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data DATE,
                total_minutos_correto INTEGER,
                total_minutos_incorreto INTEGER,
                percentual_correto REAL
            )
        ''')

        self.db_connection.commit()

    def registrar_postura(self, tipo_postura: str, duracao: int, angulos: Dict[str, float]) -> bool:
        """
        Registra um novo evento de postura no banco de dados.
        """
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO registros (data_hora, tipo_postura, duracao, angulo_pescoco, angulo_coluna)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now(),
                tipo_postura,
                duracao,
                angulos.get('pescoco', 0),
                angulos.get('coluna', 0)
            ))
            self.db_connection.commit()
            
            # Atualiza estatísticas diárias
            self._atualizar_estatisticas_diarias()
            
            return True
        except sqlite3.Error as e:
            print(f"Erro ao registrar postura: {e}")
            return False

    def _atualizar_estatisticas_diarias(self):
        """
        Atualiza as estatísticas diárias de postura correta/incorreta.
        """
        try:
            cursor = self.db_connection.cursor()
            hoje = datetime.now().date()
            
            # Calcula totais para o dia
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN tipo_postura = 'Postura correta' THEN duracao ELSE 0 END) as total_correto,
                    SUM(CASE WHEN tipo_postura != 'Postura correta' THEN duracao ELSE 0 END) as total_incorreto
                FROM registros
                WHERE date(data_hora) = ?
            ''', (hoje,))
            
            resultado = cursor.fetchone()
            total_correto = resultado[0] or 0
            total_incorreto = resultado[1] or 0
            total_geral = total_correto + total_incorreto
            
            percentual_correto = (total_correto / total_geral * 100) if total_geral > 0 else 0
            
            # Atualiza ou insere estatísticas
            cursor.execute('''
                INSERT OR REPLACE INTO estatisticas_diarias 
                (data, total_minutos_correto, total_minutos_incorreto, percentual_correto)
                VALUES (?, ?, ?, ?)
            ''', (hoje, total_correto, total_incorreto, percentual_correto))
            
            self.db_connection.commit()
        except sqlite3.Error as e:
            print(f"Erro ao atualizar estatísticas: {e}")

    def get_estatisticas(self, dias: int = 7) -> List[Dict[str, Any]]:
        """
        Retorna estatísticas dos últimos dias para geração de gráficos.
        """
        try:
            cursor = self.db_connection.cursor()
            data_inicio = datetime.now() - timedelta(days=dias)
            
            cursor.execute('''
                SELECT 
                    date(data_hora) as data,
                    SUM(CASE WHEN tipo_postura = 'Postura correta' THEN duracao ELSE 0 END) as total_correto,
                    SUM(CASE WHEN tipo_postura != 'Postura correta' THEN duracao ELSE 0 END) as total_incorreto,
                    COUNT(DISTINCT CASE WHEN tipo_postura != 'Postura correta' THEN tipo_postura END) as tipos_incorretos
                FROM registros
                WHERE data_hora >= ?
                GROUP BY date(data_hora)
                ORDER BY data DESC
            ''', (data_inicio,))
            
            return [{
                'data': row[0],
                'total_correto': row[1],
                'total_incorreto': row[2],
                'tipos_incorretos': row[3]
            } for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Erro ao buscar estatísticas: {e}")
            return []

    def get_historico(self, data_inicio: datetime = None, data_fim: datetime = None) -> List[Dict[str, Any]]:
        """Retorna histórico de posturas no período especificado"""
        try:
            cursor = self.db_connection.cursor()
            
            if data_inicio is None:
                data_inicio = datetime.now() - timedelta(days=7)
            if data_fim is None:
                data_fim = datetime.now()
            
            cursor.execute('''
                SELECT 
                    data_hora,
                    tipo_postura,
                    duracao,
                    angulo_pescoco,
                    angulo_coluna
                FROM registros
                WHERE data_hora BETWEEN ? AND ?
                ORDER BY data_hora DESC
            ''', (data_inicio, data_fim))
            
            return [{
                'data_hora': row[0],
                'tipo_postura': row[1],
                'duracao': row[2],
                'angulo_pescoco': row[3],
                'angulo_coluna': row[4]
            } for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Erro ao buscar histórico: {e}")
            return []

    def exportar_dados(self, formato: str = 'excel', data_inicio: datetime = None, data_fim: datetime = None) -> bool:
        """
        Exporta os dados do banco para CSV ou Excel no período selecionado.
        """
        try:
            # Busca dados
            dados = self.get_historico(data_inicio, data_fim)
            if not dados:
                return False
            
            # Converte para DataFrame
            df = pd.DataFrame(dados)
            
            # Cria diretório de exportação se não existir
            os.makedirs('exportacoes', exist_ok=True)
            
            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if formato.lower() == 'excel':
                arquivo = f'exportacoes/posturas_{timestamp}.xlsx'
                df.to_excel(arquivo, index=False, sheet_name='Posturas')
                
                # Adiciona estatísticas em outra aba
                estatisticas = pd.DataFrame(self.get_estatisticas())
                with pd.ExcelWriter(arquivo, engine='openpyxl', mode='a') as writer:
                    estatisticas.to_excel(writer, index=False, sheet_name='Estatísticas')
            else:
                arquivo = f'exportacoes/posturas_{timestamp}.csv'
                df.to_csv(arquivo, index=False)
            
            return True
        except Exception as e:
            print(f"Erro ao exportar dados: {e}")
            return False

    def get_resumo_diario(self) -> Dict[str, Any]:
        """
        Retorna um resumo das posturas do dia (minutos correto/incorreto, percentual).
        """
        try:
            cursor = self.db_connection.cursor()
            hoje = datetime.now().date()
            
            cursor.execute('''
                SELECT 
                    total_minutos_correto,
                    total_minutos_incorreto,
                    percentual_correto
                FROM estatisticas_diarias
                WHERE data = ?
            ''', (hoje,))
            
            resultado = cursor.fetchone()
            if resultado:
                return {
                    'minutos_correto': resultado[0],
                    'minutos_incorreto': resultado[1],
                    'percentual_correto': resultado[2]
                }
            return {
                'minutos_correto': 0,
                'minutos_incorreto': 0,
                'percentual_correto': 0
            }
        except sqlite3.Error as e:
            print(f"Erro ao buscar resumo diário: {e}")
            return {
                'minutos_correto': 0,
                'minutos_incorreto': 0,
                'percentual_correto': 0
            }

    def get_posturas_incorretas_por_tempo(self, minutos=30):
        """Retorna dados de posturas incorretas por intervalo de tempo"""
        try:
            # Obtém registros dos últimos X minutos
            tempo_inicial = datetime.now() - timedelta(minutes=minutos)
            
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT 
                    strftime('%H:%M:%S', data_hora) as tempo,
                    COUNT(*) as quantidade
                FROM registros 
                WHERE tipo_postura != 'Postura correta'
                AND data_hora >= ?
                GROUP BY strftime('%H:%M:%S', data_hora)
                ORDER BY data_hora
            """, (tempo_inicial,))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"Erro ao buscar dados de posturas incorretas: {e}")
            return []

    def __del__(self):
        """Fecha a conexão com o banco de dados"""
        if hasattr(self, 'db_connection'):
            self.db_connection.close() 