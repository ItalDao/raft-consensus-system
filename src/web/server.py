"""
Web Server for Raft Dashboard
Servidor web para visualizar el cluster en tiempo real
"""

from aiohttp import web
import json
from datetime import datetime
from typing import List
from src.raft.node import RaftNode


class RaftWebServer:
    """
    Servidor web que expone el estado del cluster
    
    Endpoints:
    - GET /api/status: Estado de todos los nodos
    - GET /api/logs: Logs de todos los nodos
    - POST /api/command: Ejecuta un comando (solo líder)
    - GET /: Dashboard HTML
    """
    
    def __init__(self, nodes: List[RaftNode], port: int = 8080):
        """
        Args:
            nodes: Lista de nodos del cluster
            port: Puerto del servidor web
        """
        self.nodes = {node.node_id: node for node in nodes}
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        
    def _setup_routes(self):
        """Configura las rutas del servidor"""
        self.app.router.add_get('/api/status', self.get_cluster_status)
        self.app.router.add_get('/api/logs', self.get_cluster_logs)
        self.app.router.add_post('/api/command', self.execute_command)
        self.app.router.add_get('/', self.serve_dashboard)
        
    async def get_cluster_status(self, request):
        """
        GET /api/status
        
        Retorna el estado actual de todos los nodos:
        - Quién es el líder
        - En qué term están
        - Cuántas entradas tienen
        """
        status = []
        
        for node_id, node in self.nodes.items():
            node_status = node.get_status()
            node_status['is_alive'] = node.running
            status.append(node_status)
        
        return web.json_response({
            'cluster_size': len(self.nodes),
            'nodes': status,
            'timestamp': datetime.now().isoformat()
        })
    
    async def get_cluster_logs(self, request):
        """
        GET /api/logs
        
        Retorna el log completo de cada nodo
        Útil para ver si están sincronizados
        """
        logs = {}
        
        for node_id, node in self.nodes.items():
            logs[f'node_{node_id}'] = [
                {
                    'term': entry.term,
                    'index': entry.index,
                    'command': entry.command,
                    'timestamp': entry.timestamp
                }
                for entry in node.log
            ]
        
        return web.json_response({'logs': logs})
    
    async def execute_command(self, request):
        """
        POST /api/command
        
        Ejecuta un comando en el cluster
        
        Body: {"command": {"operation": "SET", "key": "x", "value": 10}}
        """
        try:
            data = await request.json()
            command = data.get('command')
            
            if not command:
                return web.json_response(
                    {'error': 'Missing command'},
                    status=400
                )
            
            # Busco al líder
            leader = None
            for node in self.nodes.values():
                if node.state.value == 'leader':
                    leader = node
                    break
            
            if not leader:
                return web.json_response(
                    {'error': 'No leader available'},
                    status=503
                )
            
            # Ejecuto el comando
            success = await leader.append_entry(command)
            
            if success:
                return web.json_response({
                    'success': True,
                    'leader_id': leader.node_id,
                    'log_index': len(leader.log)
                })
            else:
                return web.json_response(
                    {'error': 'Failed to append entry'},
                    status=500
                )
                
        except Exception as e:
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    async def serve_dashboard(self, request):
        """
        GET /
        
        Sirve el dashboard HTML
        """
        html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raft Cluster Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .cluster-info {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .nodes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .node-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .node-card:hover {
            transform: translateY(-5px);
        }
        
        .node-card.leader {
            border: 3px solid #4CAF50;
            background: linear-gradient(135deg, #f5fff5 0%, #e8f5e9 100%);
        }
        
        .node-card.candidate {
            border: 3px solid #FF9800;
            background: linear-gradient(135deg, #fff8f5 0%, #fff3e0 100%);
        }
        
        .node-card.follower {
            border: 3px solid #2196F3;
            background: linear-gradient(135deg, #f5f9ff 0%, #e3f2fd 100%);
        }
        
        .node-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .node-id {
            font-size: 1.5em;
            font-weight: bold;
        }
        
        .node-state {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.85em;
        }
        
        .state-leader {
            background: #4CAF50;
            color: white;
        }
        
        .state-candidate {
            background: #FF9800;
            color: white;
        }
        
        .state-follower {
            background: #2196F3;
            color: white;
        }
        
        .node-info {
            margin-top: 15px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .info-label {
            font-weight: 600;
            color: #666;
        }
        
        .info-value {
            color: #333;
        }
        
        .command-panel {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .command-panel h2 {
            margin-bottom: 15px;
            color: #333;
        }
        
        .command-form {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        input, button {
            padding: 10px 15px;
            border-radius: 5px;
            border: 1px solid #ddd;
            font-size: 1em;
        }
        
        input {
            flex: 1;
        }
        
        button {
            background: #667eea;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s;
        }
        
        button:hover {
            background: #5568d3;
        }
        
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .status-online {
            background: #4CAF50;
        }
        
        .status-offline {
            background: #f44336;
        }
        
        .logs-section {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-height: 400px;
            overflow-y: auto;
        }
        
        .log-entry {
            padding: 10px;
            background: #f5f5f5;
            margin-bottom: 5px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1> Raft Consensus Cluster Dashboard</h1>
        
        <div class="cluster-info">
            <h2>Cluster Status</h2>
            <div id="cluster-stats"></div>
        </div>
        
        <div class="nodes-grid" id="nodes-container"></div>
        
        <div class="command-panel">
            <h2>Execute Command</h2>
            <div class="command-form">
                <input type="text" id="key-input" placeholder="Key (e.g., x)">
                <input type="text" id="value-input" placeholder="Value (e.g., 10)">
                <button onclick="executeCommand()">SET</button>
            </div>
            <div id="command-result"></div>
        </div>
        
        <div class="logs-section">
            <h2>Cluster Logs</h2>
            <div id="logs-container"></div>
        </div>
    </div>
    
    <script>
        // Actualiza el dashboard cada segundo
        setInterval(updateDashboard, 1000);
        updateDashboard();
        
        async function updateDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                renderClusterStats(data);
                renderNodes(data.nodes);
                
                // También actualiza logs
                const logsResponse = await fetch('/api/logs');
                const logsData = await logsResponse.json();
                renderLogs(logsData.logs);
                
            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }
        
        function renderClusterStats(data) {
            const stats = document.getElementById('cluster-stats');
            const leader = data.nodes.find(n => n.state === 'leader');
            
            stats.innerHTML = `
                <div class="info-row">
                    <span class="info-label">Cluster Size:</span>
                    <span class="info-value">${data.cluster_size} nodes</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Current Leader:</span>
                    <span class="info-value">${leader ? 'Node ' + leader.node_id : 'No leader'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Current Term:</span>
                    <span class="info-value">${leader ? leader.term : 'N/A'}</span>
                </div>
            `;
        }
        
        function renderNodes(nodes) {
            const container = document.getElementById('nodes-container');
            
            container.innerHTML = nodes.map(node => `
                <div class="node-card ${node.state}">
                    <div class="node-header">
                        <div class="node-id">Node ${node.node_id}</div>
                        <div class="node-state state-${node.state}">${node.state}</div>
                    </div>
                    <div class="node-info">
                        <div class="info-row">
                            <span class="info-label">Status:</span>
                            <span class="info-value">
                                <span class="status-indicator ${node.is_alive ? 'status-online' : 'status-offline'}"></span>
                                ${node.is_alive ? 'Online' : 'Offline'}
                            </span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Term:</span>
                            <span class="info-value">${node.term}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Log Entries:</span>
                            <span class="info-value">${node.log_length}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Committed:</span>
                            <span class="info-value">${node.commit_index}</span>
                        </div>
                        ${node.voted_for ? `
                        <div class="info-row">
                            <span class="info-label">Voted For:</span>
                            <span class="info-value">Node ${node.voted_for}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `).join('');
        }
        
        function renderLogs(logs) {
            const container = document.getElementById('logs-container');
            const allLogs = [];
            
            for (const [nodeId, entries] of Object.entries(logs)) {
                entries.forEach(entry => {
                    allLogs.push({
                        node: nodeId,
                        ...entry
                    });
                });
            }
            
            // Ordena por timestamp
            allLogs.sort((a, b) => b.timestamp - a.timestamp);
            
            container.innerHTML = allLogs.slice(0, 20).map(log => `
                <div class="log-entry">
                    [${log.node}] Term ${log.term}, Index ${log.index}: ${JSON.stringify(log.command)}
                </div>
            `).join('') || '<p>No logs yet</p>';
        }
        
        async function executeCommand() {
            const key = document.getElementById('key-input').value;
            const value = document.getElementById('value-input').value;
            
            if (!key || !value) {
                alert('Please enter both key and value');
                return;
            }
            
            try {
                const response = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        command: {
                            operation: 'SET',
                            key: key,
                            value: value
                        }
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('command-result').innerHTML = 
                        `<p style="color: green;"> Command executed on Leader ${result.leader_id}</p>`;
                    document.getElementById('key-input').value = '';
                    document.getElementById('value-input').value = '';
                } else {
                    document.getElementById('command-result').innerHTML = 
                        `<p style="color: red;"> ${result.error}</p>`;
                }
            } catch (error) {
                document.getElementById('command-result').innerHTML = 
                    `<p style="color: red;"> Error: ${error.message}</p>`;
            }
        }
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def start(self):
        """Inicia el servidor web"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        print(f" Dashboard disponible en: http://localhost:{self.port}")
        
    async def stop(self):
        """Detiene el servidor web"""
        await self.app.shutdown()
        await self.app.cleanup()