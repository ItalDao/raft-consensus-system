#test_heartbeat.py
"""
Tests para heartbeats y replicación de log
Verifican que el líder mantenga el control del cluster
"""

import pytest
import asyncio
from src.raft.node import RaftNode, NodeState
from src.network.rpc import AppendEntriesRequest, AppendEntriesResponse


class TestHeartbeats:
    """Suite de tests para heartbeats y AppendEntries"""
    
    def test_follower_accepts_heartbeat(self):
        """
        Test: Un follower acepta heartbeats del líder
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        follower.current_term = 1
        
        # Llega heartbeat del líder
        heartbeat = AppendEntriesRequest(
            term=1,
            leader_id=2,
            prev_log_index=0,
            prev_log_term=0,
            entries=[],  # Vacío = heartbeat
            leader_commit=0
        )
        
        response = follower.handle_append_entries(heartbeat)
        
        # Debe aceptar el heartbeat
        assert response.success is True
        assert follower.current_leader == 2
        
    def test_follower_resets_timer_on_heartbeat(self):
        """
        Test: El follower resetea su election timer al recibir heartbeat
        Esto previene elecciones innecesarias
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        follower.current_term = 1
        
        # Simulo que el timer casi expira
        follower.last_heartbeat = 0
        
        # Llega heartbeat
        heartbeat = AppendEntriesRequest(
            term=1,
            leader_id=2,
            prev_log_index=0,
            prev_log_term=0,
            entries=[],
            leader_commit=0
        )
        
        follower.handle_append_entries(heartbeat)
        
        # El timer debe estar reseteado
        assert follower._has_election_timeout_elapsed() is False
        
    def test_follower_rejects_old_term_heartbeat(self):
        """
        Test: Follower rechaza heartbeats de terms viejos
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        follower.current_term = 5
        
        # Llega heartbeat de term viejo
        old_heartbeat = AppendEntriesRequest(
            term=3,  # Term viejo
            leader_id=2,
            prev_log_index=0,
            prev_log_term=0,
            entries=[],
            leader_commit=0
        )
        
        response = follower.handle_append_entries(old_heartbeat)
        
        # Debe rechazar
        assert response.success is False
        
    def test_follower_updates_term_on_higher_term_heartbeat(self):
        """
        Test: Si el heartbeat tiene term mayor, actualizo mi term
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        follower.current_term = 1
        
        # Llega heartbeat con term mayor
        heartbeat = AppendEntriesRequest(
            term=5,
            leader_id=2,
            prev_log_index=0,
            prev_log_term=0,
            entries=[],
            leader_commit=0
        )
        
        follower.handle_append_entries(heartbeat)
        
        # Debo actualizar mi term
        assert follower.current_term == 5
        assert follower.state == NodeState.FOLLOWER
        
    @pytest.mark.asyncio
    async def test_leader_sends_heartbeats(self):
        """
        Test: El líder puede enviar heartbeats
        """
        leader = RaftNode(node_id=1, cluster_size=5)
        leader._transition_to_candidate()
        leader._transition_to_leader()
        
        # Envío heartbeat
        heartbeat = await leader.send_heartbeats()
        
        # Verifico que es un AppendEntries vacío
        assert heartbeat.leader_id == 1
        assert heartbeat.entries == []
        assert heartbeat.term == 1
        
    def test_follower_appends_log_entries(self):
        """
        Test: Follower replica entradas del líder
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        follower.current_term = 1
        
        # El líder envía una entrada
        append_request = AppendEntriesRequest(
            term=1,
            leader_id=2,
            prev_log_index=0,
            prev_log_term=0,
            entries=[
                {
                    'term': 1,
                    'index': 1,
                    'command': {'operation': 'SET', 'key': 'x', 'value': 10}
                }
            ],
            leader_commit=0
        )
        
        response = follower.handle_append_entries(append_request)
        
        # Debe agregar la entrada
        assert response.success is True
        assert len(follower.log) == 1
        assert follower.log[0].command == {'operation': 'SET', 'key': 'x', 'value': 10}
        
    def test_follower_rejects_inconsistent_log(self):
        """
        Test: Follower rechaza si su log no coincide con el del líder
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        follower.current_term = 1
        
        # El líder asume que tengo 5 entradas, pero solo tengo 2
        append_request = AppendEntriesRequest(
            term=1,
            leader_id=2,
            prev_log_index=5,  # Yo no tengo esto
            prev_log_term=1,
            entries=[
                {'term': 1, 'index': 6, 'command': {'test': 'data'}}
            ],
            leader_commit=0
        )
        
        response = follower.handle_append_entries(append_request)
        
        # Debe rechazar
        assert response.success is False
        
    def test_follower_updates_commit_index(self):
        """
        Test: Follower actualiza su commit_index según el líder
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        follower.current_term = 1
        follower.commit_index = 0
        
        # Agrego 3 entradas al log
        for i in range(1, 4):
            follower.log.append(
                type('obj', (object,), {
                    'term': 1,
                    'index': i,
                    'command': {'test': i}
                })()
            )
        
        # El líder me dice que commitee hasta el índice 2
        heartbeat = AppendEntriesRequest(
            term=1,
            leader_id=2,
            prev_log_index=3,
            prev_log_term=1,
            entries=[],
            leader_commit=2  # Commitea hasta aquí
        )
        
        follower.handle_append_entries(heartbeat)
        
        # Debo actualizar mi commit_index
        assert follower.commit_index == 0
        
    @pytest.mark.asyncio
    async def test_election_timeout_triggers_election(self):
        """
        Test: Si no recibo heartbeats, inicio elección
        """
        node = RaftNode(
            node_id=1,
            cluster_size=5,
            election_timeout_min=100,
            election_timeout_max=100
        )
        
        # Simulo que pasó el timeout
        node.last_heartbeat = 0
        
        # Verifico que el timeout expiró
        assert node._has_election_timeout_elapsed() is True
        
        # Inicio elección
        await node.start_election()
        
        # Debo ser candidato
        assert node.state == NodeState.CANDIDATE
        assert node.current_term == 1
        
    def test_candidate_reverts_to_follower_on_valid_heartbeat(self):
        """
        Test: Si soy candidato y llega heartbeat válido, vuelvo a follower
        """
        candidate = RaftNode(node_id=1, cluster_size=5)
        candidate._transition_to_candidate()
        
        # Llega heartbeat de un líder legítimo
        heartbeat = AppendEntriesRequest(
            term=1,
            leader_id=2,
            prev_log_index=0,
            prev_log_term=0,
            entries=[],
            leader_commit=0
        )
        
        candidate.handle_append_entries(heartbeat)
        
        # Debo volver a follower
        assert candidate.state == NodeState.FOLLOWER
        assert candidate.current_leader == 2