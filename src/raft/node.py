"""
Raft Node Implementation with Heartbeats and Log Replication
Implementación completa con heartbeats y replicación
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
    Nodo Raft completo con:
    - Elección de líder
    - Heartbeats
    - Replicación de log
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
        self.heartbeat_interval = heartbeat_interval / 1000.0  # ms a segundos
        self.last_heartbeat = time.time()
        
        # Estado de runtime
        self.running = False
        self.current_leader: Optional[int] = None
        self.votes_received = set()
        
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
        self.votes_received = {self.node_id}
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
        """¿El log del candidato está al menos tan actualizado como el mío?"""
        my_last_term = self.get_last_log_term()
        my_last_index = self.get_last_log_index()
        
        if last_log_term != my_last_term:
            return last_log_term >= my_last_term
            
        return last_log_index >= my_last_index
        
    def handle_request_vote(self, request: RequestVoteRequest) -> RequestVoteResponse:
        """Maneja una solicitud de voto"""
        print(f"[Node {self.node_id}] Recibí RequestVote de Node {request.candidate_id} (term {request.term})")
        
        if request.term > self.current_term:
            self._transition_to_follower(request.term)
        
        vote_granted = False
        
        if request.term == self.current_term:
            if self.voted_for is None or self.voted_for == request.candidate_id:
                if self._is_log_up_to_date(request.last_log_index, request.last_log_term):
                    vote_granted = True
                    self.voted_for = request.candidate_id
                    self._reset_election_timer()
                    print(f"[Node {self.node_id}] ✅ Voté por Node {request.candidate_id}")
                else:
                    print(f"[Node {self.node_id}] ❌ Log desactualizado")
            else:
                print(f"[Node {self.node_id}] ❌ Ya voté por Node {self.voted_for}")
        
        return RequestVoteResponse(
            term=self.current_term,
            vote_granted=vote_granted
        )
    
    def handle_request_vote_response(self, response: RequestVoteResponse):
        """Maneja la respuesta a mi solicitud de voto"""
        if response.term > self.current_term:
            self._transition_to_follower(response.term)
            return
        
        if self.state != NodeState.CANDIDATE:
            return
        
        if response.vote_granted:
            self.votes_received.add(response.term)
            
            majority = (self.cluster_size // 2) + 1
            
            if len(self.votes_received) >= majority:
                print(f"[Node {self.node_id}] ¡Gané! ({len(self.votes_received)}/{self.cluster_size} votos)")
                self._transition_to_leader()
    
    def handle_append_entries(self, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """
        Maneja un AppendEntries del líder
        
        Puede ser:
        1. Heartbeat (sin entradas) - "Estoy vivo"
        2. Replicación (con entradas) - "Agrega esto a tu log"
        """
        # Si el líder tiene un term mayor, me actualizo
        if request.term > self.current_term:
            self._transition_to_follower(request.term)
        
        # Reseteo el timer - recibí señal del líder
        self._reset_election_timer()
        self.current_leader = request.leader_id
        
        # Si el term es menor al mío, rechazo
        if request.term < self.current_term:
            print(f"[Node {self.node_id}] ❌ Rechacé AppendEntries de term viejo")
            return AppendEntriesResponse(
                term=self.current_term,
                success=False
            )
        
        # Si es un heartbeat vacío
        if not request.entries:
            print(f"[Node {self.node_id}] 💓 Heartbeat de Leader {request.leader_id}")
            return AppendEntriesResponse(
                term=self.current_term,
                success=True
            )
        
        # Verifico que mi log coincida con el del líder
        if request.prev_log_index > 0:
            # Debo tener esa entrada
            if request.prev_log_index > len(self.log):
                print(f"[Node {self.node_id}] ❌ No tengo entrada en índice {request.prev_log_index}")
                return AppendEntriesResponse(
                    term=self.current_term,
                    success=False
                )
            
            # Y el term debe coincidir
            if self.log[request.prev_log_index - 1].term != request.prev_log_term:
                print(f"[Node {self.node_id}] ❌ Conflicto en índice {request.prev_log_index}")
                # Borro entradas conflictivas
                self.log = self.log[:request.prev_log_index - 1]
                return AppendEntriesResponse(
                    term=self.current_term,
                    success=False
                )
        
        # Agrego las nuevas entradas
        for entry_dict in request.entries:
            entry = LogEntry(
                term=entry_dict['term'],
                index=entry_dict['index'],
                command=entry_dict['command']
            )
            self.log.append(entry)
            print(f"[Node {self.node_id}] ✅ Replicé entrada: {entry.command}")
        
        # Actualizo mi commit index
        if request.leader_commit > self.commit_index:
            self.commit_index = min(request.leader_commit, len(self.log))
        
        return AppendEntriesResponse(
            term=self.current_term,
            success=True
        )
    
    async def send_heartbeats(self):
        """
        Líder envía heartbeats a todos los followers
        
        Esto les dice: "Estoy vivo, no hagan elección"
        """
        if self.state != NodeState.LEADER:
            return
        
        # Creo el heartbeat (AppendEntries vacío)
        heartbeat = AppendEntriesRequest(
            term=self.current_term,
            leader_id=self.node_id,
            prev_log_index=self.get_last_log_index(),
            prev_log_term=self.get_last_log_term(),
            entries=[],  # Vacío = heartbeat
            leader_commit=self.commit_index
        )
        
        print(f"[Node {self.node_id}] 💓 Enviando heartbeats...")
        
        # En sistema real, enviaría a todos los nodos
        # Por ahora solo lo logueamos
        return heartbeat
    
    async def start_election(self):
        """Inicio una nueva elección"""
        self._transition_to_candidate()
        
        request = RequestVoteRequest(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=self.get_last_log_index(),
            last_log_term=self.get_last_log_term()
        )
        
        print(f"[Node {self.node_id}] 🗳️  Pidiendo votos para term {self.current_term}...")
        return request
        
    async def append_entry(self, command: Dict) -> bool:
        """Agrega una entrada al log (solo el líder puede)"""
        if self.state != NodeState.LEADER:
            print(f"[Node {self.node_id}] ❌ No soy líder")
            return False
            
        entry = LogEntry(
            term=self.current_term,
            index=len(self.log) + 1,
            command=command
        )
        self.log.append(entry)
        
        print(f"[Node {self.node_id}] ✅ Agregué: {command}")
        return True
    
    async def run(self):
        """
        Loop principal del nodo
        
        FOLLOWER: Espera heartbeats, si timeout → elección
        CANDIDATE: Espera votos, si timeout → re-elección
        LEADER: Envía heartbeats constantemente
        """
        print(f"[Node {self.node_id}] 🚀 Iniciando loop principal...")
        
        while self.running:
            if self.state == NodeState.LEADER:
                # Soy líder: envío heartbeats
                await self.send_heartbeats()
                await asyncio.sleep(self.heartbeat_interval)
                
            elif self.state == NodeState.FOLLOWER:
                # Soy follower: espero heartbeats
                if self._has_election_timeout_elapsed():
                    print(f"[Node {self.node_id}] ⏰ Timeout! Iniciando elección...")
                    await self.start_election()
                await asyncio.sleep(0.1)  # Check cada 100ms
                
            elif self.state == NodeState.CANDIDATE:
                # Soy candidato: espero votos
                if self._has_election_timeout_elapsed():
                    print(f"[Node {self.node_id}] ⏰ Re-elección...")
                    await self.start_election()
                await asyncio.sleep(0.1)
        
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
        
        # Inicia el loop principal
        asyncio.create_task(self.run())
        
    async def stop(self):
        """Detiene el nodo"""
        self.running = False
        print(f"[Node {self.node_id}] ⏹️  Detenido")