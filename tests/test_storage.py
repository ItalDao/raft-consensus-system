"""
Tests para el sistema de persistencia
Verifican que los datos sobrevivan reinicios
"""

import pytest
import os
import tempfile
import shutil
from src.storage.log_store import LogStore


class TestLogStore:
    """Test suite para almacenamiento persistente"""
    
    @pytest.fixture
    async def temp_store(self):
        """Crea un store temporal para tests"""
        temp_dir = tempfile.mkdtemp()
        store = LogStore(node_id=1, data_dir=temp_dir)
        await store.initialize()
        
        yield store
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_initialize_creates_database(self):
        """Test: Inicialización crea la base de datos"""
        temp_dir = tempfile.mkdtemp()
        store = LogStore(node_id=1, data_dir=temp_dir)
        
        await store.initialize()
        
        # Verifica que el archivo DB existe
        assert os.path.exists(store.db_path)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_append_and_retrieve_entry(self, temp_store):
        """Test: Guardar y recuperar una entrada"""
        command = {"operation": "SET", "key": "x", "value": 10}
        
        await temp_store.append_entry(
            term=1,
            index=1,
            command=command,
            timestamp=123.456
        )
        
        entries = await temp_store.get_all_entries()
        
        assert len(entries) == 1
        assert entries[0]['term'] == 1
        assert entries[0]['index'] == 1
        assert entries[0]['command'] == command
    
    @pytest.mark.asyncio
    async def test_multiple_entries_ordered(self, temp_store):
        """Test: Múltiples entradas se mantienen en orden"""
        for i in range(1, 6):
            await temp_store.append_entry(
                term=1,
                index=i,
                command={"op": f"cmd_{i}"},
                timestamp=float(i)
            )
        
        entries = await temp_store.get_all_entries()
        
        assert len(entries) == 5
        for i, entry in enumerate(entries, 1):
            assert entry['index'] == i
    
    @pytest.mark.asyncio
    async def test_get_entry_by_index(self, temp_store):
        """Test: Recuperar entrada específica por índice"""
        command = {"operation": "DELETE", "key": "y"}
        
        await temp_store.append_entry(
            term=2,
            index=5,
            command=command,
            timestamp=789.0
        )
        
        entry = await temp_store.get_entry(5)
        
        assert entry is not None
        assert entry['index'] == 5
        assert entry['term'] == 2
        assert entry['command'] == command
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_entry(self, temp_store):
        """Test: Recuperar entrada inexistente retorna None"""
        entry = await temp_store.get_entry(999)
        assert entry is None
    
    @pytest.mark.asyncio
    async def test_delete_from_index(self, temp_store):
        """Test: Borrar entradas desde un índice"""
        # Agregar 5 entradas
        for i in range(1, 6):
            await temp_store.append_entry(
                term=1,
                index=i,
                command={"idx": i},
                timestamp=float(i)
            )
        
        # Borrar desde índice 3
        await temp_store.delete_from_index(3)
        
        entries = await temp_store.get_all_entries()
        
        assert len(entries) == 2
        assert entries[0]['index'] == 1
        assert entries[1]['index'] == 2
    
    @pytest.mark.asyncio
    async def test_get_last_index_empty(self, temp_store):
        """Test: Último índice en log vacío es 0"""
        last_index = await temp_store.get_last_index()
        assert last_index == 0
    
    @pytest.mark.asyncio
    async def test_get_last_index_with_entries(self, temp_store):
        """Test: Último índice con entradas"""
        for i in range(1, 4):
            await temp_store.append_entry(
                term=1,
                index=i,
                command={},
                timestamp=float(i)
            )
        
        last_index = await temp_store.get_last_index()
        assert last_index == 3
    
    @pytest.mark.asyncio
    async def test_save_and_load_state(self, temp_store):
        """Test: Guardar y cargar estado del nodo"""
        await temp_store.save_state(
            current_term=5,
            voted_for=2
        )
        
        state = await temp_store.load_state()
        
        assert state['current_term'] == 5
        assert state['voted_for'] == 2
    
    @pytest.mark.asyncio
    async def test_load_state_default_values(self, temp_store):
        """Test: Estado por defecto si no hay datos guardados"""
        state = await temp_store.load_state()
        
        assert state['current_term'] == 0
        assert state['voted_for'] is None
    
    @pytest.mark.asyncio
    async def test_persistence_across_instances(self):
        """Test: Datos persisten entre instancias del store"""
        temp_dir = tempfile.mkdtemp()
        
        # Primera instancia: guardar datos
        store1 = LogStore(node_id=1, data_dir=temp_dir)
        await store1.initialize()
        await store1.append_entry(1, 1, {"test": "data"}, 123.0)
        await store1.save_state(3, 2)
        
        # Segunda instancia: cargar datos
        store2 = LogStore(node_id=1, data_dir=temp_dir)
        await store2.initialize()
        
        entries = await store2.get_all_entries()
        state = await store2.load_state()
        
        assert len(entries) == 1
        assert entries[0]['command'] == {"test": "data"}
        assert state['current_term'] == 3
        assert state['voted_for'] == 2
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_get_log_count(self, temp_store):
        """Test: Contar entradas en el log"""
        for i in range(1, 8):
            await temp_store.append_entry(1, i, {}, float(i))
        
        count = await temp_store.get_log_count()
        assert count == 7