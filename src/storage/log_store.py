"""
Persistent Log Storage
Guarda los logs en SQLite para sobrevivir reinicios
"""

import aiosqlite
import json
import os
from typing import List, Optional
from dataclasses import asdict


class LogStore:
    """
    Almacenamiento persistente para logs de Raft
    
    Garantiza que los logs sobrevivan reinicios del nodo,
    cumpliendo con la durabilidad requerida por Raft.
    """
    
    def __init__(self, node_id: int, data_dir: str = "./data"):
        """
        Args:
            node_id: ID del nodo
            data_dir: Directorio para almacenar la base de datos
        """
        self.node_id = node_id
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, f"node_{node_id}.db")
        
        # Crear directorio si no existe
        os.makedirs(data_dir, exist_ok=True)
        
    async def initialize(self):
        """Inicializa la base de datos y crea las tablas"""
        async with aiosqlite.connect(self.db_path) as db:
            # Tabla de logs
            await db.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term INTEGER NOT NULL,
                    index_ INTEGER NOT NULL UNIQUE,
                    command TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            
            # Tabla de estado persistente
            await db.execute("""
                CREATE TABLE IF NOT EXISTS node_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Índice para búsquedas rápidas
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_index 
                ON logs(index_)
            """)
            
            await db.commit()
            
    async def append_entry(self, term: int, index: int, command: dict, timestamp: float):
        """
        Guarda una entrada en el log
        
        Args:
            term: Term de la entrada
            index: Índice de la entrada
            command: Comando a guardar
            timestamp: Timestamp de creación
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO logs (term, index_, command, timestamp)
                VALUES (?, ?, ?, ?)
            """, (term, index, json.dumps(command), timestamp))
            await db.commit()
            
    async def get_all_entries(self) -> List[dict]:
        """
        Recupera todas las entradas del log
        
        Returns:
            Lista de entradas ordenadas por índice
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT term, index_, command, timestamp
                FROM logs
                ORDER BY index_ ASC
            """) as cursor:
                entries = []
                async for row in cursor:
                    entries.append({
                        'term': row['term'],
                        'index': row['index_'],
                        'command': json.loads(row['command']),
                        'timestamp': row['timestamp']
                    })
                return entries
                
    async def get_entry(self, index: int) -> Optional[dict]:
        """
        Recupera una entrada específica por índice
        
        Args:
            index: Índice de la entrada
            
        Returns:
            Entrada o None si no existe
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT term, index_, command, timestamp
                FROM logs
                WHERE index_ = ?
            """, (index,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'term': row['term'],
                        'index': row['index_'],
                        'command': json.loads(row['command']),
                        'timestamp': row['timestamp']
                    }
                return None
                
    async def delete_from_index(self, from_index: int):
        """
        Borra todas las entradas desde un índice
        
        Usado cuando hay conflictos en el log
        
        Args:
            from_index: Índice desde donde borrar (inclusive)
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM logs
                WHERE index_ >= ?
            """, (from_index,))
            await db.commit()
            
    async def get_last_index(self) -> int:
        """
        Retorna el índice de la última entrada
        
        Returns:
            Último índice o 0 si el log está vacío
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT MAX(index_) as max_index FROM logs
            """) as cursor:
                row = await cursor.fetchone()
                return row[0] if row[0] is not None else 0
                
    async def save_state(self, current_term: int, voted_for: Optional[int]):
        """
        Guarda el estado persistente del nodo
        
        Args:
            current_term: Term actual
            voted_for: ID del nodo por quien votó
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO node_state (key, value)
                VALUES ('current_term', ?)
            """, (str(current_term),))
            
            await db.execute("""
                INSERT OR REPLACE INTO node_state (key, value)
                VALUES ('voted_for', ?)
            """, (str(voted_for) if voted_for is not None else 'null',))
            
            await db.commit()
            
    async def load_state(self) -> dict:
        """
        Carga el estado persistente del nodo
        
        Returns:
            Diccionario con current_term y voted_for
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            state = {
                'current_term': 0,
                'voted_for': None
            }
            
            async with db.execute("""
                SELECT key, value FROM node_state
            """) as cursor:
                async for row in cursor:
                    if row['key'] == 'current_term':
                        state['current_term'] = int(row['value'])
                    elif row['key'] == 'voted_for':
                        val = row['value']
                        state['voted_for'] = int(val) if val != 'null' else None
                        
            return state
            
    async def get_log_count(self) -> int:
        """Retorna el número total de entradas en el log"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM logs") as cursor:
                row = await cursor.fetchone()
                return row[0]