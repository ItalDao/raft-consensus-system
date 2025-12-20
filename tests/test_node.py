"""
Tests for Raft Node Implementation
"""

import pytest
from src.raft.node import RaftNode, NodeState, LogEntry


class TestRaftNode:
    """Test suite for RaftNode"""
    
    def test_node_initialization(self):
        """Test that node initializes in FOLLOWER state"""
        node = RaftNode(node_id=1, cluster_size=5)
        
        assert node.node_id == 1
        assert node.cluster_size == 5
        assert node.state == NodeState.FOLLOWER
        assert node.current_term == 0
        assert node.voted_for is None
        assert len(node.log) == 0
        
    def test_transition_to_candidate(self):
        """Test transition to CANDIDATE state"""
        node = RaftNode(node_id=1, cluster_size=5)
        node._transition_to_candidate()
        
        assert node.state == NodeState.CANDIDATE
        assert node.current_term == 1
        assert node.voted_for == 1
        
    def test_transition_to_leader(self):
        """Test transition to LEADER state"""
        node = RaftNode(node_id=1, cluster_size=5)
        node._transition_to_candidate()
        node._transition_to_leader()
        
        assert node.state == NodeState.LEADER
        assert node.current_leader == 1
        assert len(node.next_index) == 4  # cluster_size - 1
        
    def test_transition_to_follower(self):
        """Test transition back to FOLLOWER state"""
        node = RaftNode(node_id=1, cluster_size=5)
        node._transition_to_candidate()
        node._transition_to_follower(term=2)
        
        assert node.state == NodeState.FOLLOWER
        assert node.current_term == 2
        assert node.voted_for is None
        
    @pytest.mark.asyncio
    async def test_append_entry_as_leader(self):
        """Test that leader can append entries"""
        node = RaftNode(node_id=1, cluster_size=5)
        node._transition_to_candidate()
        node._transition_to_leader()
        
        command = {"operation": "SET", "key": "x", "value": 10}
        success = await node.append_entry(command)
        
        assert success is True
        assert len(node.log) == 1
        assert node.log[0].command == command
        assert node.log[0].term == 1
        
    @pytest.mark.asyncio
    async def test_append_entry_as_follower_fails(self):
        """Test that follower cannot append entries"""
        node = RaftNode(node_id=1, cluster_size=5)
        
        command = {"operation": "SET", "key": "x", "value": 10}
        success = await node.append_entry(command)
        
        assert success is False
        assert len(node.log) == 0
        
    def test_log_entry_creation(self):
        """Test LogEntry dataclass"""
        entry = LogEntry(term=1, index=1, command={"test": "data"})
        
        assert entry.term == 1
        assert entry.index == 1
        assert entry.command == {"test": "data"}
        assert entry.timestamp is not None
        
    def test_get_last_log_index_empty(self):
        """Test getting last log index when log is empty"""
        node = RaftNode(node_id=1, cluster_size=5)
        assert node.get_last_log_index() == 0
        
    def test_get_last_log_term_empty(self):
        """Test getting last log term when log is empty"""
        node = RaftNode(node_id=1, cluster_size=5)
        assert node.get_last_log_term() == 0
        
    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test node status reporting"""
        node = RaftNode(node_id=1, cluster_size=5)
        status = node.get_status()
        
        assert status["node_id"] == 1
        assert status["state"] == "follower"
        assert status["term"] == 0
        assert status["log_length"] == 0
        
    def test_election_timeout_randomization(self):
        """Test that election timeout is randomized"""
        node1 = RaftNode(node_id=1, cluster_size=5)
        node2 = RaftNode(node_id=2, cluster_size=5)
        
        node1._reset_election_timer()
        node2._reset_election_timer()
        
        # Timeouts should be different (with very high probability)
        assert node1.election_timeout != node2.election_timeout