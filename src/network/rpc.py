"""
Raft Node Implementation with Voting
Implementación completa con sistema de elección de líder
"""

import asyncio
import random
import time
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.network.rpc import (
    RequestVoteRequest, 
    RequestVoteResponse,
    AppendEntriesRequest,
    AppendEntriesResponse
)


class NodeState(Enum):
    """Posibles estados de un nodo Raft"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    """Una entrada en el log replicado"""
    term: int
    index: int
    command: Dict
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class RaftNode:
    """
    Nodo Raft con capacidad de elección de líder
    
    Responsabilidades:
    - Mantener estado del nodo
    - Participar en elecciones
    - Votar por candidatos
    - Replicar log
    """
    
    def __init__(
        self,
        node_id: int,
        cluster_size: int,
        election_timeout_min: int = 150,
        election_timeout_max: int = 300,
        heartbeat_interval: int = 50
    ):
        self.node_id = node_id
        self.cluster_size = cluster_size
        
        # Estado persistente
        self.current_term = 0
        self.voted_for: Optional[int] = None
        self.log: List[LogEntry] = []
        
        # Estado volátil
        self.commit_index = 0
        self.last_applied = 0
        self.state = NodeState.FOLLOWER
        
        # Estado volátil (solo líderes)
        self.next_index: Dict[int, int] = {}
        self.match_index: Dict[int, int] = {}
        
        # Configuración de timeouts
        self.election_timeout_min = election_timeout_min
        self.election_timeout_max = election_timeout_max
        self.heartbeat_interval = heartbeat_interval
        self.last_heartbeat = time.time()
        
        # Estado de runtime
        self.running = False
        self.current_leader: Optional[int] = None
        self.votes_received = set()  # Votos recibidos en esta elección
        
    def _reset_election_timer(self):
        """Resetea el timer de elección con valor random"""
        timeout = random.randint(
            self.election_timeout_min,
            self.election_timeout_max
        )
        self.election_timeout = timeout / 1000.0
        self.last_heartbeat = time.time()
        
    def _get_election_timeout_elapsed(self) -> float:
        """Tiempo transcurrido desde último heartbeat"""
        return time.time() - self.last_heartbeat
        
    def _has_election_timeout_elapsed(self) -> bool:
        """¿Ya pasó el timeout? ¿El líder murió?"""
        return self._get_election_timeout_elapsed() >= self.election_timeout
        
    def _transition_to_follower(self, term: int):
        """Transición a estado Follower"""
        self.state = NodeState.FOLLOWER
        self.current_term = term
        self.voted_for = None
        self.current_leader = None
        self.votes_received.clear()
        self._reset_election_timer()
        print(f"[Node {self.node_id}] → FOLLOWER (term {term})")
        
    def _transition_to_candidate(self):
        """Transición a estado Candidate - Inicio de elección"""
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}  # Me voto a mí mismo
        self._reset_election_timer()
        print(f"[Node {self.node_id}] → CANDIDATE (term {self.current_term})")
        
    def _transition_to_leader(self):
        """Transición a estado Leader - Gané la elección"""
        self.state = NodeState.LEADER
        self.current_leader = self.node_id
        
        # Inicializo índices para cada follower
        for node_id in range(1, self.cluster_size + 1):
            if node_id != self.node_id:
                self.next_index[node_id] = len(self.log) + 1
                self.match_index[node_id] = 0
                
        print(f"[Node {self.node_id}] → LEADER (term {self.current_term}) 👑")
        
    def get_last_log_index(self) -> int:
        """Índice de la última entrada del log"""
        return len(self.log)
        
    def get_last_log_term(self) -> int:
        """Term de la última entrada del log"""
        if not self.log:
            return 0
        return self.log[-1].term
    
    def _is_log_up_to_date(self, last_log_index: int, last_log_term: int) -> bool:
        """
        ¿El log del candidato está al menos tan actualizado como el mío?
        
        Regla de Raft: 
        - Si los terms son diferentes, el que tiene mayor term está más actualizado
        - Si los terms son iguales, el que tiene más entradas está más actualizado
        """
        my_last_term = self.get_last_log_term()
        my_last_index = self.get_last_log_index()
        
        # Si el candidato tiene un term más alto, está más actualizado
        if last_log_term != my_last_term:
            return last_log_term >= my_last_term
            
        # Si tienen el mismo term, el que tiene más entradas está más actualizado
        return last_log_index >= my_last_index
        
    def handle_request_vote(self, request: RequestVoteRequest) -> RequestVoteResponse:
        """
        Maneja una solicitud de voto
        
        Reglas para dar mi voto:
        1. El candidato debe tener un term >= al mío
        2. Yo no debo haber votado por nadie más en este term
        3. El log del candidato debe estar al menos tan actualizado como el mío
        """
        print(f"[Node {self.node_id}] Recibí RequestVote de Node {request.candidate_id} (term {request.term})")
        
        # Si el candidato tiene un term mayor, actualizo mi term
        if request.term > self.current_term:
            self._transition_to_follower(request.term)
        
        # Decido si voto por este candidato
        vote_granted = False
        
        if request.term == self.current_term:
            # ¿Ya voté por alguien?
            if self.voted_for is None or self.voted_for == request.candidate_id:
                # ¿Su log está actualizado?
                if self._is_log_up_to_date(request.last_log_index, request.last_log_term):
                    vote_granted = True
                    self.voted_for = request.candidate_id
                    self._reset_election_timer()
                    print(f"[Node {self.node_id}]  Voté por Node {request.candidate_id}")
                else:
                    print(f"[Node {self.node_id}]  Log desactualizado, no voto")
            else:
                print(f"[Node {self.node_id}] Ya voté por Node {self.voted_for}")
        
        return RequestVoteResponse(
            term=self.current_term,
            vote_granted=vote_granted
        )
    
    def handle_request_vote_response(self, response: RequestVoteResponse):
        """
        Maneja la respuesta a mi solicitud de voto
        
        Si recibo suficientes votos (mayoría), me convierto en líder
        """
        # Si la respuesta tiene un term mayor, vuelvo a follower
        if response.term > self.current_term:
            self._transition_to_follower(response.term)
            return
        
        # Solo proceso votos si soy candidato
        if self.state != NodeState.CANDIDATE:
            return
        
        # Si me dieron el voto, lo cuento
        if response.vote_granted:
            self.votes_received.add(response.term)  # Simplificado para demo
            
            # ¿Tengo mayoría? (más de la mitad del cluster)
            majority = (self.cluster_size // 2) + 1
            
            if len(self.votes_received) >= majority:
                print(f"[Node {self.node_id}] ¡Gané la elección! ({len(self.votes_received)}/{self.cluster_size} votos)")
                self._transition_to_leader()
    
    async def start_election(self):
        """
        Inicio una nueva elección
        
        1. Me convierto en candidato
        2. Incremento mi term
        3. Voto por mí mismo
        4. Pido votos a todos los demás nodos
        """
        self._transition_to_candidate()
        
        # Creo la solicitud de voto
        request = RequestVoteRequest(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=self.get_last_log_index(),
            last_log_term=self.get_last_log_term()
        )
        
        print(f"[Node {self.node_id}] Pidiendo votos para term {self.current_term}...")
        
        # En un sistema real, aquí enviaríamos RPCs a todos los nodos
        # Por ahora solo simulamos
        return request
        
    async def append_entry(self, command: Dict) -> bool:
        """Agrega una entrada al log (solo el líder puede)"""
        if self.state != NodeState.LEADER:
            print(f"[Node {self.node_id}] ❌ No soy líder, no puedo agregar entradas")
            return False
            
        entry = LogEntry(
            term=self.current_term,
            index=len(self.log) + 1,
            command=command
        )
        self.log.append(entry)
        
        print(f"[Node {self.node_id}] ✅ Agregué entrada: {command}")
        return True
        
    def get_status(self) -> Dict:
        """Estado actual del nodo"""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "term": self.current_term,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "leader": self.current_leader,
            "voted_for": self.voted_for,
            "votes_received": len(self.votes_received)
        }
        
    async def start(self):
        """Inicia el nodo"""
        self.running = True
        self._reset_election_timer()
        print(f"[Node {self.node_id}] ✅ Iniciado como FOLLOWER")
        
    async def stop(self):
        """Detiene el nodo"""
        self.running = False
        print(f"[Node {self.node_id}] ⏹️  Detenido")