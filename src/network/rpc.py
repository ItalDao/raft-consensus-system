"""
RPC Messages for Raft Protocol
Sistema de mensajes entre nodos
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class RequestVoteRequest:
    """
    Solicitud de voto enviada por un Candidate
    
    Es como decir: "Oye, quiero ser líder. ¿Votas por mí?"
    """
    term: int              # En qué período electoral estamos
    candidate_id: int      # Quién está pidiendo el voto
    last_log_index: int    # Hasta qué posición tiene su log
    last_log_term: int     # Qué term tiene su última entrada
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para enviar por red"""
        return {
            "type": "RequestVote",
            "term": self.term,
            "candidate_id": self.candidate_id,
            "last_log_index": self.last_log_index,
            "last_log_term": self.last_log_term
        }


@dataclass
class RequestVoteResponse:
    """
    Respuesta a una solicitud de voto
    
    Es como decir: "Sí, voto por ti" o "No, ya voté por otro"
    """
    term: int          # Mi term actual
    vote_granted: bool # True = te di mi voto, False = no puedo votar por ti
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para enviar por red"""
        return {
            "type": "RequestVoteResponse",
            "term": self.term,
            "vote_granted": self.vote_granted
        }


@dataclass
class AppendEntriesRequest:
    """
    Solicitud para agregar entradas al log (o heartbeat)
    
    El líder usa esto para:
    1. Decir "estoy vivo" (heartbeat vacío)
    2. Replicar operaciones a los followers
    """
    term: int              # Term actual del líder
    leader_id: int         # Quién es el líder
    prev_log_index: int    # Índice de la entrada anterior
    prev_log_term: int     # Term de la entrada anterior
    entries: list          # Nuevas entradas (vacío = heartbeat)
    leader_commit: int     # Hasta dónde ha confirmado el líder
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para enviar por red"""
        return {
            "type": "AppendEntries",
            "term": self.term,
            "leader_id": self.leader_id,
            "prev_log_index": self.prev_log_index,
            "prev_log_term": self.prev_log_term,
            "entries": self.entries,
            "leader_commit": self.leader_commit
        }


@dataclass
class AppendEntriesResponse:
    """
    Respuesta a AppendEntries
    
    Es como decir: "OK, agregué las entradas" o "Error, no coincide mi log"
    """
    term: int      # Mi term actual
    success: bool  # True = todo OK, False = hay conflicto
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para enviar por red"""
        return {
            "type": "AppendEntriesResponse",
            "term": self.term,
            "success": self.success
        }