"""
Tests para el sistema de votación de Raft
Verifican que las elecciones funcionen correctamente
"""

import pytest
from src.raft.node import RaftNode, NodeState
from src.network.rpc import RequestVoteRequest, RequestVoteResponse


class TestVoting:
    """Suite de tests para elecciones"""
    
    def test_follower_grants_vote_to_candidate(self):
        """
        Test: Un follower vota por el primer candidato que le pida
        """
        # Creo un nodo follower
        follower = RaftNode(node_id=1, cluster_size=5)
        
        # Llega una solicitud de voto
        request = RequestVoteRequest(
            term=1,
            candidate_id=2,
            last_log_index=0,
            last_log_term=0
        )
        
        response = follower.handle_request_vote(request)
        
        # El follower debe dar su voto
        assert response.vote_granted is True
        assert follower.voted_for == 2
        assert follower.current_term == 1
        
    def test_follower_only_votes_once_per_term(self):
        """
        Test: Un nodo solo puede votar UNA vez por term
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        
        # Primera solicitud de voto
        request1 = RequestVoteRequest(
            term=1,
            candidate_id=2,
            last_log_index=0,
            last_log_term=0
        )
        response1 = follower.handle_request_vote(request1)
        
        # Segunda solicitud (diferente candidato, mismo term)
        request2 = RequestVoteRequest(
            term=1,
            candidate_id=3,
            last_log_index=0,
            last_log_term=0
        )
        response2 = follower.handle_request_vote(request2)
        
        # Solo debe haber votado por el primero
        assert response1.vote_granted is True
        assert response2.vote_granted is False
        assert follower.voted_for == 2
        
    def test_node_updates_term_on_higher_term_request(self):
        """
        Test: Si recibo un request con term mayor, actualizo mi term
        """
        node = RaftNode(node_id=1, cluster_size=5)
        node.current_term = 1
        
        # Llega request con term mayor
        request = RequestVoteRequest(
            term=5,
            candidate_id=2,
            last_log_index=0,
            last_log_term=0
        )
        
        response = node.handle_request_vote(request)
        
        # Debo actualizar mi term y volver a follower
        assert node.current_term == 5
        assert node.state == NodeState.FOLLOWER
        assert response.vote_granted is True
        
    def test_candidate_rejects_vote_for_outdated_log(self):
        """
        Test: No voto por alguien con log menos actualizado que el mío
        """
        follower = RaftNode(node_id=1, cluster_size=5)
        
        # Mi log tiene 3 entradas en term 2
        follower.current_term = 2
        follower.log = [
            type('obj', (object,), {'term': 1, 'index': 1})(),
            type('obj', (object,), {'term': 2, 'index': 2})(),
            type('obj', (object,), {'term': 2, 'index': 3})()
        ]
        
        # Llega candidato con log menos actualizado
        request = RequestVoteRequest(
            term=2,
            candidate_id=2,
            last_log_index=1,  # Solo tiene 1 entrada
            last_log_term=1
        )
        
        response = follower.handle_request_vote(request)
        
        # NO debo votar por él
        assert response.vote_granted is False
        
    @pytest.mark.asyncio
    async def test_candidate_starts_election(self):
        """
        Test: Un candidato puede iniciar una elección
        """
        node = RaftNode(node_id=1, cluster_size=5)
        
        # Inicio elección
        request = await node.start_election()
        
        # Verifico que se convirtió en candidato
        assert node.state == NodeState.CANDIDATE
        assert node.current_term == 1
        assert node.voted_for == 1
        assert 1 in node.votes_received  # Se votó a sí mismo
        assert request.candidate_id == 1
        
    def test_candidate_becomes_leader_with_majority(self):
        """
        Test: Un candidato con mayoría de votos se vuelve líder
        """
        node = RaftNode(node_id=1, cluster_size=5)
        node._transition_to_candidate()
        
        # Simulo que recibo votos (necesito 3 de 5)
        node.votes_received = {1, 2, 3}  # 3 votos
        
        # Proceso una respuesta más
        response = RequestVoteResponse(term=1, vote_granted=True)
        node.handle_request_vote_response(response)
        
        # Debo convertirme en líder
        assert node.state == NodeState.LEADER
        assert node.current_leader == 1
        
    def test_candidate_loses_election_reverts_to_follower(self):
        """
        Test: Si aparece un líder, vuelvo a follower
        """
        node = RaftNode(node_id=1, cluster_size=5)
        node._transition_to_candidate()
        
        # Recibo respuesta con term mayor (otro ganó)
        response = RequestVoteResponse(term=2, vote_granted=False)
        node.handle_request_vote_response(response)
        
        # Debo volver a follower
        assert node.state == NodeState.FOLLOWER
        assert node.current_term == 2
        
    def test_log_comparison_same_term_different_length(self):
        """
        Test: Entre logs con mismo term, el más largo está más actualizado
        """
        node = RaftNode(node_id=1, cluster_size=5)
        node.log = [
            type('obj', (object,), {'term': 1, 'index': 1})(),
            type('obj', (object,), {'term': 1, 'index': 2})()
        ]
        
        # Candidato con log más corto
        assert node._is_log_up_to_date(1, 1) is False
        
        # Candidato con log igual o más largo
        assert node._is_log_up_to_date(2, 1) is True
        assert node._is_log_up_to_date(3, 1) is True
        
    def test_log_comparison_different_terms(self):
        """
        Test: Entre logs con diferentes terms, el term mayor gana
        """
        node = RaftNode(node_id=1, cluster_size=5)
        node.log = [
            type('obj', (object,), {'term': 1, 'index': 1})(),
            type('obj', (object,), {'term': 1, 'index': 2})()
        ]
        
        # Candidato con term menor (aunque tenga más entradas)
        assert node._is_log_up_to_date(5, 0) is False
        
        # Candidato con term mayor (aunque tenga menos entradas)
        assert node._is_log_up_to_date(1, 2) is True