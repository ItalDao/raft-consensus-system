"""
Raft Configuration
Centralized configuration for the Raft cluster
"""

import os
from dataclasses import dataclass


@dataclass
class RaftConfig:
    """Configuration parameters for Raft nodes"""
    
    # Election timeouts (milliseconds)
    ELECTION_TIMEOUT_MIN: int = 150
    ELECTION_TIMEOUT_MAX: int = 300
    
    # Heartbeat interval (milliseconds)
    HEARTBEAT_INTERVAL: int = 50
    
    # RPC timeouts (milliseconds)
    RPC_TIMEOUT: int = 100
    
    # Log compaction
    SNAPSHOT_THRESHOLD: int = 1000
    
    # Cluster configuration
    CLUSTER_SIZE: int = int(os.getenv("CLUSTER_SIZE", 5))
    NODE_ID: int = int(os.getenv("NODE_ID", 1))
    NODE_PORT: int = int(os.getenv("NODE_PORT", 8001))
    
    # Storage
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    
    @classmethod
    def from_env(cls) -> "RaftConfig":
        """Create configuration from environment variables"""
        return cls(
            CLUSTER_SIZE=int(os.getenv("CLUSTER_SIZE", 5)),
            NODE_ID=int(os.getenv("NODE_ID", 1)),
            NODE_PORT=int(os.getenv("NODE_PORT", 8001)),
            DATA_DIR=os.getenv("DATA_DIR", "./data")
        )