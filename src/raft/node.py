"""
Raft Node Implementation
Core state machine for distributed consensus
"""

import asyncio
import random
import time
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class NodeState(Enum):
    """Possible states of a Raft node"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    """Single log entry in the replicated log"""
    term: int
    index: int
    command: Dict
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class RaftNode:
    """
    Implementation of a single Raft node.
    
    Key responsibilities:
    - Maintain node state (Follower/Candidate/Leader)
    - Handle leader election
    - Replicate log entries
    - Respond to RPC calls from other nodes
    """
    
    def __init__(
        self,
        node_id: int,
        cluster_size: int,
        election_timeout_min: int = 150,
        election_timeout_max: int = 300,
        heartbeat_interval: int = 50
    ):
        """
        Initialize a Raft node.
        
        Args:
            node_id: Unique identifier for this node
            cluster_size: Total number of nodes in cluster
            election_timeout_min: Minimum election timeout (ms)
            election_timeout_max: Maximum election timeout (ms)
            heartbeat_interval: Interval for leader heartbeats (ms)
        """
        self.node_id = node_id
        self.cluster_size = cluster_size
        
        # Persistent state (survives restarts)
        self.current_term = 0
        self.voted_for: Optional[int] = None
        self.log: List[LogEntry] = []
        
        # Volatile state (all nodes)
        self.commit_index = 0
        self.last_applied = 0
        self.state = NodeState.FOLLOWER
        
        # Volatile state (leaders only)
        self.next_index: Dict[int, int] = {}
        self.match_index: Dict[int, int] = {}
        
        # Timing configuration
        self.election_timeout_min = election_timeout_min
        self.election_timeout_max = election_timeout_max
        self.heartbeat_interval = heartbeat_interval
        self.last_heartbeat = time.time()
        
        # Runtime state
        self.running = False
        self.current_leader: Optional[int] = None
        
    def _reset_election_timer(self):
        """Reset election timeout with randomized value"""
        timeout = random.randint(
            self.election_timeout_min,
            self.election_timeout_max
        )
        self.election_timeout = timeout / 1000.0  # Convert to seconds
        self.last_heartbeat = time.time()
        
    def _get_election_timeout_elapsed(self) -> float:
        """Get time elapsed since last heartbeat"""
        return time.time() - self.last_heartbeat
        
    def _has_election_timeout_elapsed(self) -> bool:
        """Check if election timeout has occurred"""
        return self._get_election_timeout_elapsed() >= self.election_timeout
        
    def _transition_to_follower(self, term: int):
        """
        Transition node to Follower state.
        
        Args:
            term: The term to transition to
        """
        self.state = NodeState.FOLLOWER
        self.current_term = term
        self.voted_for = None
        self.current_leader = None
        self._reset_election_timer()
        print(f"[Node {self.node_id}] Transitioned to FOLLOWER (term {term})")
        
    def _transition_to_candidate(self):
        """Transition node to Candidate state and start election"""
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self._reset_election_timer()
        print(f"[Node {self.node_id}] Transitioned to CANDIDATE (term {self.current_term})")
        
    def _transition_to_leader(self):
        """Transition node to Leader state"""
        self.state = NodeState.LEADER
        self.current_leader = self.node_id
        
        # Initialize leader state
        for node_id in range(1, self.cluster_size + 1):
            if node_id != self.node_id:
                self.next_index[node_id] = len(self.log) + 1
                self.match_index[node_id] = 0
                
        print(f"[Node {self.node_id}] Became LEADER (term {self.current_term})")
        
    def get_last_log_index(self) -> int:
        """Get the index of the last log entry"""
        return len(self.log)
        
    def get_last_log_term(self) -> int:
        """Get the term of the last log entry"""
        if not self.log:
            return 0
        return self.log[-1].term
        
    async def append_entry(self, command: Dict) -> bool:
        """
        Append a new entry to the log.
        Only the leader can append entries.
        
        Args:
            command: The command to append
            
        Returns:
            True if successful, False otherwise
        """
        if self.state != NodeState.LEADER:
            print(f"[Node {self.node_id}] Cannot append - not the leader")
            return False
            
        entry = LogEntry(
            term=self.current_term,
            index=len(self.log) + 1,
            command=command
        )
        self.log.append(entry)
        
        print(f"[Node {self.node_id}] Appended entry: {command} (index {entry.index})")
        return True
        
    def get_status(self) -> Dict:
        """
        Get current node status.
        
        Returns:
            Dictionary with node state information
        """
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "term": self.current_term,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "leader": self.current_leader,
            "voted_for": self.voted_for
        }
        
    async def start(self):
        """Start the Raft node"""
        self.running = True
        self._reset_election_timer()
        print(f"[Node {self.node_id}] Started as FOLLOWER")
        
        # Main event loop would go here
        # This will be expanded in next commits
        
    async def stop(self):
        """Stop the Raft node"""
        self.running = False
        print(f"[Node {self.node_id}] Stopped")