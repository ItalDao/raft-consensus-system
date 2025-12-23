"""
Raft Cluster Manager
Maneja la comunicación entre nodos del cluster
"""

import asyncio
from typing import List, Dict
from src.raft.node import RaftNode
from src.network.rpc import RequestVoteRequest, AppendEntriesRequest


class RaftCluster:
    """
    Simula un cluster de Raft con comunicación real entre nodos
    
    En un sistema real, esto sería reemplazado por RPCs sobre la red.
    Aquí simulamos la red con llamadas directas a métodos.
    """
    
    def __init__(self, cluster_size: int = 5):
        self.cluster_size = cluster_size
        self.nodes: List[RaftNode] = []
        
    def initialize_nodes(self):
        """Crea todos los nodos del cluster"""
        print(f" Inicializando cluster con {self.cluster_size} nodos...")
        
        for i in range(1, self.cluster_size + 1):
            node = RaftNode(
                node_id=i,
                cluster_size=self.cluster_size,
                election_timeout_min=300,  # Aumentado a 300ms
                election_timeout_max=500,  # Aumentado a 500ms
                heartbeat_interval=100     # Aumentado a 100ms
            )
            self.nodes.append(node)
        
        print(f" {self.cluster_size} nodos creados")
    
    async def broadcast_request_vote(self, sender: RaftNode, request: RequestVoteRequest):
        """
        Envía RequestVote de un candidato a todos los demás nodos
        
        Esto simula enviar RPCs por la red
        """
        responses = []
        
        for node in self.nodes:
            if node.node_id == sender.node_id:
                continue  # No me envío a mí mismo
            
            # Simulo el RPC: el nodo recibe y responde
            response = node.handle_request_vote(request)
            responses.append(response)
            
            # El sender procesa la respuesta CON EL ID del votante
            sender.handle_request_vote_response(response, node.node_id)
        
        return responses
    
    async def broadcast_append_entries(self, sender: RaftNode, request: AppendEntriesRequest):
        """
        Envía AppendEntries (heartbeat o log) del líder a todos los followers
        """
        responses = []
        
        for node in self.nodes:
            if node.node_id == sender.node_id:
                continue
            
            # Simulo el RPC
            response = node.handle_append_entries(request)
            responses.append(response)
        
        return responses
    
    async def node_loop(self, node: RaftNode):
        """
        Loop principal de cada nodo
        
        Simula el comportamiento asíncrono de cada nodo
        """
        # IMPORTANTE: Delay inicial para evitar empate
        await asyncio.sleep(node.initial_delay)
        
        while node.running:
            if node.state.value == 'leader':
                # Soy líder: envío heartbeats
                heartbeat = await node.send_heartbeats()
                if heartbeat:
                    await self.broadcast_append_entries(node, heartbeat)
                await asyncio.sleep(node.heartbeat_interval)
                
            elif node.state.value == 'follower':
                # Soy follower: espero heartbeats
                if node._has_election_timeout_elapsed():
                    # Timeout! Inicio elección
                    vote_request = await node.start_election()
                    await self.broadcast_request_vote(node, vote_request)
                await asyncio.sleep(0.1)
                
            elif node.state.value == 'candidate':
                # Soy candidato: espero votos
                if node._has_election_timeout_elapsed():
                    # Re-elección
                    vote_request = await node.start_election()
                    await self.broadcast_request_vote(node, vote_request)
                await asyncio.sleep(0.1)
    
    async def start_all_nodes(self):
        """Inicia todos los nodos del cluster"""
        tasks = []
        
        for node in self.nodes:
            await node.start()
            # Crea un task para el loop de cada nodo
            task = asyncio.create_task(self.node_loop(node))
            tasks.append(task)
        
        return tasks
    
    async def stop_all_nodes(self):
        """Detiene todos los nodos"""
        for node in self.nodes:
            await node.stop()
    
    def get_leader(self) -> RaftNode:
        """Retorna el nodo líder actual"""
        for node in self.nodes:
            if node.state.value == 'leader':
                return node
        return None
    
    async def wait_for_leader(self, timeout: float = 10.0):
        """Espera hasta que se elija un líder"""
        print(" Esperando elección de líder...")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            leader = self.get_leader()
            if leader:
                print(f" Node {leader.node_id} es el líder (term {leader.current_term})")
                return leader
            
            # Timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                print("  Timeout esperando líder")
                return None
            
            await asyncio.sleep(0.5)
    
    async def execute_command(self, command: Dict):
        """Ejecuta un comando en el cluster"""
        leader = self.get_leader()
        
        if not leader:
            return False, "No hay líder disponible"
        
        success = await leader.append_entry(command)
        
        if success:
            # Replica a todos los followers
            append_request = AppendEntriesRequest(
                term=leader.current_term,
                leader_id=leader.node_id,
                prev_log_index=leader.get_last_log_index() - 1,
                prev_log_term=leader.get_last_log_term() if leader.get_last_log_index() > 1 else 0,
                entries=[{
                    'term': command.get('term', leader.current_term),
                    'index': leader.get_last_log_index(),
                    'command': command
                }],
                leader_commit=leader.commit_index
            )
            
            await self.broadcast_append_entries(leader, append_request)
            return True, f"Comando ejecutado en Node {leader.node_id}"
        
        return False, "Error al ejecutar comando"