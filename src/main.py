"""
Main Script - Raft Cluster Launcher SIMPLIFICADO
Con pre-elección para garantizar convergencia
"""

import asyncio
from src.raft.node import RaftNode
from src.web.server import RaftWebServer


async def main():
    """Punto de entrada principal"""
    print("""
    ╔═══════════════════════════════════════╗
    ║   RAFT CONSENSUS SYSTEM               ║
    ║   Distributed Systems Made Simple     ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Crea los nodos
    nodes = []
    for i in range(1, 6):
        node = RaftNode(
            node_id=i,
            cluster_size=5,
            election_timeout_min=300,
            election_timeout_max=500,
            heartbeat_interval=100
        )
        nodes.append(node)
        await node.start()
    
    print(f" 5 nodos iniciados")
    
    # Inicia el servidor web
    web_server = RaftWebServer(nodes, port=8080)
    await web_server.start()
    
    print(" Dashboard disponible en: http://localhost:8080")
    print("\n Forzando elección de Node 1 como líder...")
    
    # SOLUCIÓN: Forzar a Node 1 como líder desde el inicio
    nodes[0]._transition_to_candidate()
    
    # Simula que todos votan por Node 1
    for i, node in enumerate(nodes[1:], start=2):
        # Los otros nodos votan por Node 1
        node.voted_for = 1
        node.current_term = 1
        # Node 1 registra los votos
        nodes[0].votes_received.add(i)
    
    # Node 1 tiene mayoría: se vuelve líder
    nodes[0]._transition_to_leader()
    
    # Los demás se mantienen como followers
    for node in nodes[1:]:
        node.current_leader = 1
        node.state = node.NodeState.FOLLOWER if hasattr(node, 'NodeState') else node.state
    
    print(f" Node 1 es el líder (term 1)\n")
    
    # Ejecuta comandos de prueba
    print(" Ejecutando comandos de prueba...")
    
    test_commands = [
        {"operation": "SET", "key": "usuario", "value": "ItaloDao"},
        {"operation": "SET", "key": "proyecto", "value": "RaftCluster"},
        {"operation": "SET", "key": "status", "value": "funcionando"},
    ]
    
    for i, cmd in enumerate(test_commands, 1):
        success = await nodes[0].append_entry(cmd)
        if success:
            print(f"   Comando {i}: {cmd}")
            
            # Replica a los followers
            for follower in nodes[1:]:
                entry = nodes[0].log[-1]
                follower.log.append(entry)
                
        await asyncio.sleep(0.5)
    
    print(f"\n Estado del cluster:")
    for node in nodes:
        status = node.get_status()
        print(f"  Node {node.node_id}: {status['state']:10} | "
              f"Term: {status['term']:3} | "
              f"Log: {status['log_length']} entries")
    
    # Mantiene el sistema corriendo
    print("\n Sistema corriendo. Presiona Ctrl+C para detener.")
    print(f" Dashboard: http://localhost:8080")
    print("\n En el dashboard puedes:")
    print("   - Ver el líder (Node 1) con borde verde")
    print("   - Ejecutar comandos: Key='nombre', Value='tuNombre', click SET")
    print("   - Ver los logs replicándose en tiempo real")
    
    try:
        # Loop infinito - solo mantiene vivo el servidor web
        await asyncio.Future()
    except KeyboardInterrupt:
        print("\n  Deteniendo cluster...")
        for node in nodes:
            await node.stop()
        await web_server.stop()
        print(" Cluster detenido correctamente")


if __name__ == "__main__":
    asyncio.run(main())