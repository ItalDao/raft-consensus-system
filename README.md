# 🔥 Raft Consensus System

> Implementación educativa del algoritmo de consenso Raft para sistemas distribuidos

## 🎯 ¿Qué es esto?

Este proyecto implementa el **algoritmo de consenso Raft**, usado por gigantes como Google (Kubernetes/etcd), HashiCorp (Consul), y Cockroach Labs (CockroachDB) para mantener consistencia en sistemas distribuidos.

### ¿Por qué Raft?

- ✅ **Tolerancia a fallos**: El sistema sigue funcionando aunque fallen nodos
- ✅ **Consistencia fuerte**: Todos los nodos ven los mismos datos
- ✅ **Líder electo democráticamente**: Sin punto único de fallo
- ✅ **Log replicado**: Cada operación queda registrada y replicada

## 🏗️ Arquitectura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Node 1    │────▶│   Node 2    │────▶│   Node 3    │
│  (Leader)   │     │ (Follower)  │     │ (Follower)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
              Replicación de Logs
```

### Estados de un Nodo

1. **Follower**: Estado inicial, escucha al líder
2. **Candidate**: Compite para ser líder
3. **Leader**: Coordina todo el cluster

## 🛠️ Stack Tecnológico

- **Python 3.11+**: Lenguaje principal
- **asyncio**: Comunicación asíncrona entre nodos
- **Docker**: Simulación de nodos distribuidos
- **pytest**: Testing exhaustivo

## 📦 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/raft-consensus-system.git
cd raft-consensus-system

# Instalar dependencias
pip install -r requirements.txt

# Correr el cluster (5 nodos)
docker-compose up
```

## 🚀 Uso Rápido

```python
from src.raft.node import RaftNode

# Crear un nodo
node = RaftNode(node_id=1, cluster_size=5)

# Iniciar el nodo
await node.start()

# Escribir datos (solo el líder puede)
await node.append_entry({"command": "SET x=10"})
```

## 📚 Conceptos Implementados

### ✅ Fase 1: Fundamentos (Actual)
- [x] Estructura de proyecto profesional
- [ ] Estados del nodo (Follower, Candidate, Leader)
- [ ] Sistema de logs persistentes

### 🔄 Fase 2: Consenso
- [ ] Elección de líder (RequestVote RPC)
- [ ] Replicación de logs (AppendEntries RPC)
- [ ] Heartbeats y timeouts

### 🛡️ Fase 3: Tolerancia a Fallos
- [ ] Detección de nodos caídos
- [ ] Re-elección automática
- [ ] Recuperación de particiones de red

### 🎨 Fase 4: Visualización
- [ ] Dashboard web en tiempo real
- [ ] Métricas del cluster
- [ ] Logs visuales

## 📖 Recursos de Aprendizaje

- [Paper original de Raft](https://raft.github.io/raft.pdf) - Diego Ongaro & John Ousterhout
- [Raft Visualization](http://thesecretlivesofdata.com/raft/) - Animación interactiva
- [Raft en producción](https://www.consul.io/docs/architecture/consensus) - HashiCorp Consul

## 🤝 Contribuciones

Este es un proyecto educativo. Pull requests bienvenidos para:
- Optimizaciones
- Tests adicionales
- Documentación
- Nuevas features (snapshots, compactación de logs)

## 📝 Licencia

MIT License - Úsalo, aprende, mejóralo

## 👤 Autor

Construido con 🧠 para entender cómo funcionan los sistemas distribuidos en el mundo real.

---

**⭐ Si te sirvió, deja una estrella - ayuda a otros developers a encontrarlo**