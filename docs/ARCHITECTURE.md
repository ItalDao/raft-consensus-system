# System Architecture

## Overview

This document describes the architecture and implementation details of the Raft Consensus System, a distributed system that maintains consistency across multiple nodes using the Raft consensus protocol.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│              (Web Browser, CLI, API Clients)                │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Web Server                              │
│                   (aiohttp, port 8080)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ /api/status  │  │ /api/logs    │  │ /api/command │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Raft Cluster Manager                       │
│              (Coordinates all nodes)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┐
        ▼            ▼            ▼            ▼
    ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐
    │Node 1 │   │Node 2 │   │Node 3 │   │Node 4 │ ...
    │LEADER │   │FOLLOW │   │FOLLOW │   │FOLLOW │
    └───┬───┘   └───┬───┘   └───┬───┘   └───┬───┘
        │           │           │           │
        └───────────┴───────────┴───────────┘
                    │
                    ▼
            ┌───────────────┐
            │ Persistent    │
            │ Storage       │
            │ (SQLite)      │
            └───────────────┘
```

## Component Details

### 1. Raft Node (`src/raft/node.py`)

**Purpose**: Core implementation of a single Raft node with full state machine.

**States**:
- `FOLLOWER`: Default state, replicates entries from leader
- `CANDIDATE`: Transitional state during leader election
- `LEADER`: Coordinates the cluster and handles all writes

**Key Responsibilities**:
- State transitions (Follower ↔ Candidate ↔ Leader)
- Election timeout management with randomization
- Heartbeat generation (leaders only)
- Vote handling and majority calculation
- Log entry management

**Critical Methods**:
```python
handle_request_vote(request)      # Process vote requests
handle_append_entries(request)    # Handle log replication
_transition_to_leader()          # Become leader after winning election
send_heartbeats()                # Keep followers synchronized
```

**State Variables**:
```python
# Persistent state (survives crashes)
current_term: int                 # Latest term seen
voted_for: Optional[int]         # Candidate ID voted for in current term
log: List[LogEntry]              # Log entries

# Volatile state (all nodes)
commit_index: int                # Index of highest log entry committed
last_applied: int                # Index of highest log entry applied
state: NodeState                 # Current node state

# Volatile state (leaders only)
next_index: Dict[int, int]       # Next log index to send to each follower
match_index: Dict[int, int]      # Highest log index replicated on each follower
```

---

### 2. Network Layer (`src/network/rpc.py`)

**Purpose**: Defines RPC message structures for inter-node communication.

**RPC Types**:

**RequestVote**:
```python
RequestVoteRequest:
  - term: int              # Candidate's term
  - candidate_id: int      # Candidate requesting vote
  - last_log_index: int    # Index of candidate's last log entry
  - last_log_term: int     # Term of candidate's last log entry

RequestVoteResponse:
  - term: int              # Current term
  - vote_granted: bool     # True if vote granted
```

**AppendEntries**:
```python
AppendEntriesRequest:
  - term: int              # Leader's term
  - leader_id: int         # So follower can redirect clients
  - prev_log_index: int    # Index of log entry immediately preceding new ones
  - prev_log_term: int     # Term of prev_log_index entry
  - entries: List[dict]    # Log entries to store (empty for heartbeat)
  - leader_commit: int     # Leader's commit_index

AppendEntriesResponse:
  - term: int              # Current term
  - success: bool          # True if follower contained entry matching prev_log_index
```

---

### 3. Persistent Storage (`src/storage/log_store.py`)

**Purpose**: Durable log storage using SQLite for crash recovery.

**Database Schema**:

```sql
-- Log entries table
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term INTEGER NOT NULL,
    index_ INTEGER NOT NULL UNIQUE,
    command TEXT NOT NULL,          -- JSON-encoded command
    timestamp REAL NOT NULL
);

-- Node state table
CREATE TABLE node_state (
    key TEXT PRIMARY KEY,            -- 'current_term' or 'voted_for'
    value TEXT NOT NULL
);

-- Index for fast lookups
CREATE INDEX idx_log_index ON logs(index_);
```

**Key Operations**:
- `append_entry()`: Write-ahead logging for durability
- `get_all_entries()`: Full log recovery on restart
- `delete_from_index()`: Handle log conflicts (Raft requirement)
- `save_state()` / `load_state()`: Persist Raft state across crashes

**Durability Guarantee**: All writes committed to disk before acknowledging, ensuring ACID compliance.

---

### 4. Cluster Coordinator (`src/cluster.py`)

**Purpose**: Simulates network communication between nodes.

**Key Functions**:
```python
broadcast_request_vote(sender, request)
  → Sends vote request to all nodes
  → Collects responses
  → Updates sender's vote count

broadcast_append_entries(sender, request)
  → Sends log entries to all followers
  → Simulates leader → follower replication

node_loop(node)
  → Main event loop for each node
  → Handles: heartbeats, timeouts, elections
```

**Network Simulation**: In production, replace with actual RPC (gRPC, HTTP, TCP).

---

### 5. Web Dashboard (`src/web/server.py`)

**Purpose**: REST API + HTML interface for cluster visualization.

**Endpoints**:

```
GET  /                    → Dashboard HTML
GET  /api/status          → Cluster status (all nodes)
GET  /api/logs            → All replicated logs
POST /api/command         → Execute command on leader
```

**Dashboard Features**:
- Real-time cluster state visualization
- Live log viewer with auto-refresh
- Interactive command execution
- Node health indicators
- Leader identification

**Update Mechanism**: JavaScript polls `/api/status` every 1 second for live updates.

---

## Raft Algorithm Flow

### Leader Election

```
1. Follower timeout expires (150-300ms)
   ↓
2. Transition to CANDIDATE
   ↓
3. Increment current_term
   ↓
4. Vote for self
   ↓
5. Send RequestVote to all nodes
   ↓
6. Wait for majority votes
   ↓
7a. Majority achieved → Become LEADER
7b. Higher term seen → Become FOLLOWER
7c. Split vote → Timeout and retry
```

### Log Replication

```
1. Client sends command to leader
   ↓
2. Leader appends to local log
   ↓
3. Leader sends AppendEntries to all followers
   ↓
4. Followers append to their logs
   ↓
5. Followers respond with success
   ↓
6. Leader waits for majority
   ↓
7. Leader commits entry
   ↓
8. Leader notifies followers of commit
   ↓
9. Followers apply committed entry
```

### Heartbeat Mechanism

```
Leader (every 100ms):
  → Send empty AppendEntries (heartbeat)
  → Reset election timeout on followers

Follower:
  → If heartbeat received: Reset timeout
  → If timeout expires: Start election
```

---

## Failure Scenarios

### 1. Leader Failure

```
Before:
  Node 1 (LEADER) ━━━ heartbeats ━━━▶ Followers

After crash:
  Node 1 (DEAD) ✗
  Node 2 (FOLLOWER) → timeout → CANDIDATE → wins election → LEADER
```

**Recovery Time**: 150-300ms (election timeout)

### 2. Follower Failure

```
Leader continues operating normally
Failed follower misses log entries
On recovery: Catches up via AppendEntries
```

**Recovery**: Automatic, no data loss

### 3. Network Partition

```
Scenario: [Node1, Node2] ━✗━ [Node3, Node4, Node5]

Minority partition (1,2):
  - Cannot elect leader (need 3/5 votes)
  - Rejects writes

Majority partition (3,4,5):
  - Elects new leader
  - Continues processing writes
```

**Safety**: Minority partition cannot make progress → prevents split-brain

---

## Performance Characteristics

### Latency
- **Write latency**: ~100ms (RTT + majority ACK)
- **Read latency**: ~1ms (local read from leader)
- **Election time**: 150-300ms

### Throughput
- **Writes**: Limited by leader (single-threaded log append)
- **Reads**: Scales with number of nodes (read from any node)

### Scalability
- **Tested**: 5 nodes
- **Recommended**: 3-7 nodes (odd numbers for majority)
- **Limitation**: More nodes = slower consensus

---

## Testing Strategy

### Unit Tests (48 total)
```
test_node.py       - 11 tests (state machine)
test_voting.py     -  9 tests (leader election)
test_heartbeat.py  - 10 tests (failure detection)
test_storage.py    - 12 tests (persistence)
test_api.py        -  6 tests (REST API)
```

### Test Coverage
- All state transitions
- All RPC handlers
- Log conflict resolution
- Persistence and recovery
- API endpoints

---

## Deployment

### Local Development
```bash
python -m src.main
```

### Docker
```bash
docker-compose up --build
```

### Production Considerations
- Use external service discovery (Consul, etcd)
- Implement actual RPC (replace cluster simulation)
- Add TLS for secure communication
- Implement log compaction for long-running systems
- Add monitoring (Prometheus + Grafana)

---

## Future Enhancements

1. **Membership Changes**: Dynamic cluster resizing
2. **Log Compaction**: Snapshots to bound log size
3. **Read Optimization**: Follower reads with lease mechanism
4. **Multi-Raft**: Partition data across multiple Raft groups
5. **Optimizations**: Batch log replication, pipeline RPCs

---

## References

- [Raft Paper](https://raft.github.io/raft.pdf) - Original specification
- [etcd](https://etcd.io) - Production Raft implementation
- [Consul](https://www.consul.io) - Service mesh using Raft
- [CockroachDB](https://www.cockroachlabs.com) - Distributed SQL with Raft