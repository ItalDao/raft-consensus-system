# Contributing to Raft Consensus System

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git

### Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/YourUsername/raft-consensus-system.git
cd raft-consensus-system

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests to verify setup
pytest
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Write clean, readable code
- Follow PEP 8 style guidelines
- Add docstrings to new functions/classes
- Update tests for changed functionality

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_voting.py

# Run with verbose output
pytest -v
```

### 4. Lint Your Code

```bash
# Check style
flake8 src/ tests/

# Format code (optional)
black src/ tests/
```

### 5. Commit Your Changes

Use conventional commit messages:

```bash
git commit -m "feat: add log compaction"
git commit -m "fix: resolve election timeout bug"
git commit -m "docs: update architecture diagram"
git commit -m "test: add tests for membership changes"
```

Commit types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding or updating tests
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `chore`: Changes to build process or auxiliary tools

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Reference any related issues
- Screenshots (if UI changes)
- Test results

## Code Style

### Python Style

Follow PEP 8 with these specifics:

```python
# Use descriptive variable names
node_id = 1  # Good
n = 1        # Bad

# Add docstrings to public functions
def handle_request_vote(request: RequestVoteRequest) -> RequestVoteResponse:
    """
    Process a vote request from a candidate.
    
    Args:
        request: Vote request containing candidate info
        
    Returns:
        Response indicating if vote was granted
    """
    pass

# Use type hints
def append_entry(self, command: Dict) -> bool:
    pass

# Keep functions focused and small (< 50 lines)
```

### Naming Conventions

- Classes: `PascalCase` (e.g., `RaftNode`, `LogStore`)
- Functions: `snake_case` (e.g., `handle_request_vote`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `ELECTION_TIMEOUT_MIN`)
- Private methods: `_leading_underscore` (e.g., `_transition_to_leader`)

## Testing Guidelines

### Writing Tests

```python
import pytest
from src.raft.node import RaftNode

class TestRaftNode:
    """Test suite for RaftNode"""
    
    def test_node_initialization(self):
        """Test that node initializes correctly"""
        node = RaftNode(node_id=1, cluster_size=5)
        
        assert node.node_id == 1
        assert node.state.value == "follower"
        assert len(node.log) == 0
        
    @pytest.mark.asyncio
    async def test_leader_election(self):
        """Test leader election process"""
        node = RaftNode(node_id=1, cluster_size=5)
        await node.start_election()
        
        assert node.state.value == "candidate"
        assert node.current_term == 1
```

### Test Coverage Goals

- Aim for > 90% code coverage
- Test all public methods
- Test edge cases and error conditions
- Test state transitions
- Test concurrent scenarios

## Areas for Contribution

### High Priority

1. **Log Compaction**: Implement snapshotting to bound log size
2. **Membership Changes**: Allow dynamic addition/removal of nodes
3. **Performance Optimization**: Batch log replication
4. **Monitoring**: Prometheus metrics export

### Medium Priority

5. **Read Optimization**: Implement follower reads with leases
6. **Security**: Add TLS support for RPC
7. **Testing**: Add chaos engineering tests
8. **Documentation**: Add more examples and tutorials

### Low Priority (Good First Issues)

9. **UI Improvements**: Enhance dashboard visualization
10. **CLI Tool**: Add command-line interface
11. **Benchmarks**: Add performance benchmarking suite
12. **Examples**: Add usage examples for different scenarios

## Project Structure

```
raft-consensus-system/
├── src/
│   ├── raft/           # Core Raft implementation
│   │   ├── node.py     # Node state machine
│   │   └── config.py   # Configuration
│   ├── network/        # RPC layer
│   │   └── rpc.py      # Message definitions
│   ├── storage/        # Persistence
│   │   └── log_store.py
│   ├── web/            # REST API + Dashboard
│   │   └── server.py
│   ├── cluster.py      # Cluster coordinator
│   └── main.py         # Entry point
├── tests/              # Test suite
│   ├── test_node.py
│   ├── test_voting.py
│   ├── test_heartbeat.py
│   ├── test_storage.py
│   └── test_api.py
├── docs/               # Documentation
└── .github/            # CI/CD workflows
```

## Documentation

When adding new features:

1. Update relevant docstrings
2. Add/update tests
3. Update ARCHITECTURE.md if changing design
4. Update README.md if adding user-facing features
5. Add examples if appropriate

## Questions or Problems?

- Check existing issues on GitHub
- Read the [ARCHITECTURE.md](ARCHITECTURE.md) document
- Open a new issue with detailed description
- Tag issues appropriately (bug, enhancement, question)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Accept criticism gracefully
- Put the project's interests first

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

---

Thank you for contributing to make this project better! 🚀