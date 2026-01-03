"""
Tests de integración para la API REST
Verifican que el servidor web funcione correctamente
"""

import pytest
from aiohttp import web
from src.raft.node import RaftNode
from src.web.server import RaftWebServer


class TestAPI:
    """Test suite para la API REST"""
    
    @pytest.fixture
    async def cluster_nodes(self):
        """Crea un cluster de 3 nodos para tests"""
        nodes = []
        for i in range(1, 4):
            node = RaftNode(
                node_id=i,
                cluster_size=3,
                election_timeout_min=300,
                election_timeout_max=500
            )
            await node.start()
            nodes.append(node)
        
        # Designar Node 1 como líder
        nodes[0]._transition_to_candidate()
        nodes[0].votes_received = {1, 2, 3}
        nodes[0]._transition_to_leader()
        
        yield nodes
        
        # Cleanup
        for node in nodes:
            await node.stop()
    
    @pytest.fixture
    async def web_server(self, cluster_nodes):
        """Crea servidor web con el cluster"""
        server = RaftWebServer(cluster_nodes, port=8888)
        yield server
    
    @pytest.mark.asyncio
    async def test_get_cluster_status(self, web_server, aiohttp_client):
        """Test: GET /api/status retorna estado del cluster"""
        client = await aiohttp_client(web_server.app)
        
        resp = await client.get('/api/status')
        
        assert resp.status == 200
        data = await resp.json()
        
        assert 'cluster_size' in data
        assert 'nodes' in data
        assert data['cluster_size'] == 3
        assert len(data['nodes']) == 3
    
    @pytest.mark.asyncio
    async def test_status_includes_leader(self, web_server, aiohttp_client):
        """Test: Estado incluye información del líder"""
        client = await aiohttp_client(web_server.app)
        
        resp = await client.get('/api/status')
        data = await resp.json()
        
        nodes = data['nodes']
        leader_nodes = [n for n in nodes if n['state'] == 'leader']
        
        assert len(leader_nodes) == 1
        assert leader_nodes[0]['node_id'] == 1
    
    @pytest.mark.asyncio
    async def test_get_cluster_logs(self, web_server, cluster_nodes, aiohttp_client):
        """Test: GET /api/logs retorna logs del cluster"""
        # Agregar algunas entradas
        await cluster_nodes[0].append_entry({"test": "entry1"})
        await cluster_nodes[0].append_entry({"test": "entry2"})
        
        client = await aiohttp_client(web_server.app)
        resp = await client.get('/api/logs')
        
        assert resp.status == 200
        data = await resp.json()
        
        assert 'logs' in data
        assert 'node_1' in data['logs']
        assert len(data['logs']['node_1']) == 2
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, web_server, aiohttp_client):
        """Test: POST /api/command ejecuta comando exitosamente"""
        client = await aiohttp_client(web_server.app)
        
        resp = await client.post('/api/command', json={
            'command': {'operation': 'SET', 'key': 'x', 'value': 10}
        })
        
        assert resp.status == 200
        data = await resp.json()
        
        assert data['success'] is True
        assert data['leader_id'] == 1
    
    @pytest.mark.asyncio
    async def test_execute_command_missing_command(self, web_server, aiohttp_client):
        """Test: POST /api/command sin comando retorna error"""
        client = await aiohttp_client(web_server.app)
        
        resp = await client.post('/api/command', json={})
        
        assert resp.status == 400
        data = await resp.json()
        
        assert 'error' in data
    
    @pytest.mark.asyncio
    async def test_dashboard_html(self, web_server, aiohttp_client):
        """Test: GET / retorna el dashboard HTML"""
        client = await aiohttp_client(web_server.app)
        
        resp = await client.get('/')
        
        assert resp.status == 200
        text = await resp.text()
        
        assert 'Raft Cluster Dashboard' in text
        assert 'DOCTYPE html' in text