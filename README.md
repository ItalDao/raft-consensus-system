# Raft Consensus System

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

A production-grade implementation of the Raft consensus algorithm for distributed systems. Built to understand how industry leaders like Google (Kubernetes/etcd), HashiCorp (Consul), and Cockroach Labs maintain consistency across distributed clusters.

## Overview

This project implements the Raft consensus protocol, which provides:

- **Fault Tolerance**: System continues operating despite node failures
- **Strong Consistency**: All nodes maintain identical state
- **Leader Election**: Democratic selection without single points of failure
- **Log Replication**: Every operation is logged and replicated across the cluster

## System Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Node 1    │────▶│   Node 2    │────▶│   Node 3    │
│  (Leader)   │     │ (Follower)  │     │ (Follower)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
              Log Replication Protocol
```

### Node States

Each node in the cluster operates in one of three states:

| State | Description |
|-------|-------------|
| **Follower** | Initial state, receives and replicates log entries from leader |
| **Candidate** | Temporary state during leader election |
| **Leader** | Coordinates cluster operations and log replication |

## Technology Stack

- **Python 3.11+**: Core implementation language
- **asyncio**: Asynchronous inter-node communication
- **Docker**: Multi-node cluster simulation
- **pytest**: Comprehensive test coverage
- **aiosqlite**: Persistent log storage

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git

### Installation

```bash
git clone https://github.com/ItalDao/raft-consensus-system.git
cd raft-consensus-system
pip install -r requirements.txt
```

### Running the Cluster

```bash
# Start a 5-node cluster
docker-compose up

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f
```

### Basic Usage

```python
from src.raft.node import RaftNode

# Initialize a node
node = RaftNode(node_id=1, cluster_size=5)

# Start the node
await node.start()

# Append entry (only leader can write)
await node.append_entry({"command": "SET x=10"})
```

## Implementation Roadmap

### Phase 1: Foundation ✅ COMPLETED
- [x] Professional project structure
- [x] Node state machine (Follower, Candidate, Leader)
- [x] Persistent log storage system

### Phase 2: Consensus Protocol ✅ COMPLETED
- [x] Leader election (RequestVote RPC)
- [x] Log replication (AppendEntries RPC)
- [x] Heartbeat mechanism and timeout detection

### Phase 3: Fault Tolerance ✅ COMPLETED
- [x] Node failure detection
- [x] Automatic leader designation
- [x] Log synchronization

### Phase 4: Production Features ✅ COMPLETED
- [x] Real-time cluster dashboard
- [x] REST API for cluster control
- [x] Visual log viewer
- [ ] Metrics and monitoring (Future)
- [ ] Log compaction and snapshots (Future)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test suite
pytest tests/test_consensus.py
```

## Project Structure

```
raft-consensus-system/
├── src/
│   ├── raft/           # Core Raft implementation
│   ├── network/        # RPC and networking layer
│   └── storage/        # Persistent log storage
├── tests/              # Comprehensive test suite
├── docs/               # Architecture documentation
├── docker-compose.yml  # Multi-node deployment
└── requirements.txt    # Python dependencies
```

## References

> **Note**: This implementation follows the original Raft specification

- [In Search of an Understandable Consensus Algorithm](https://raft.github.io/raft.pdf) - Ongaro & Ousterhout, Stanford (2014)
- [Raft Consensus Algorithm Visualization](http://thesecretlivesofdata.com/raft/)
- [Consul Architecture](https://www.consul.io/docs/architecture/consensus) - Production Raft implementation

## Contributing

Contributions are welcome. Areas of interest:

- Performance optimizations
- Additional test coverage
- Documentation improvements
- Advanced features (snapshots, membership changes)

Please ensure all tests pass and code follows PEP 8 style guidelines.

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Author

**Italo D.**  
GitHub: [@ItalDao](https://github.com/ItalDao)

Built as a deep dive into distributed systems consensus algorithms used in production infrastructure.

---

**Industry Applications**: This algorithm powers critical infrastructure at Google (etcd in Kubernetes), HashiCorp (Consul service mesh), CockroachDB (distributed SQL), and many other large-scale systems requiring strong consistency guarantees.