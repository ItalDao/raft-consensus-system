"""
Main Script - Raft Cluster Launcher
Compatible con Windows y Linux
"""

import asyncio
import signal
import sys
import platform
from src.raft.node import RaftNode
from src.web.server import RaftWebServer


class RaftCluster:
    """Gestor del cluster Raft"""
    
    def __init__(self):
        self.nodes = []
        self.web_server = None
        self.running = False
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Inicia el cluster"""
        print("""
    ╔═══════════════════════════════════════╗
    ║   RAFT CONSENSUS SYSTEM               ║
    ║   Distributed Systems Made Simple     ║
    ╚═══════════════════════════════════════╝
        """)
        
        # Crea los 5 nodos
        print(" Iniciando nodos del cluster...")
        for i in range(1, 6):
            node = RaftNode(
                node_id=i,
                cluster_size=5,
                election_timeout_min=300,
                election_timeout_max=500,
                heartbeat_interval=100
            )
            self.nodes.append(node)
            await node.start()
        
        print(" 5 nodos iniciados correctamente")
        
        # Inicia el servidor web
        self.web_server = RaftWebServer(self.nodes, port=8080)
        await self.web_server.start()
        
        print(" Dashboard disponible en: http://0.0.0.0:8080")
        print("\n Esperando elección de líder (algoritmo Raft)...")
        
        # Espera a que se elija un líder naturalmente
        await self._wait_for_leader()
        
        # Comandos de prueba opcionales
        await self._run_test_commands()
        
        self.running = True
        print("\n Sistema listo y funcionando")
        print(" Dashboard: http://localhost:8080")
        print("\n En el dashboard puedes:")
        print("   - Ver el líder actual (borde verde)")
        print("   - Ejecutar comandos SET/DELETE")
        print("   - Ver los logs replicándose en tiempo real")
        print("   - Monitorear el estado del cluster")
        print("\n  Presiona Ctrl+C para detener el cluster\n")
        
    async def _wait_for_leader(self, timeout=10):
        """Espera a que se elija un líder"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            # Busca un líder en el cluster
            for node in self.nodes:
                if node.state.value == 'leader':
                    print(f" Node {node.node_id} elegido como líder (term {node.current_term})")
                    return True
            await asyncio.sleep(0.1)
        
        print("  No se eligió líder en el tiempo esperado (iniciará elección pronto)")
        return False
    
    async def _run_test_commands(self):
        """Ejecuta comandos de prueba en el líder"""
        # Encuentra el líder
        leader = None
        for node in self.nodes:
            if node.state.value == 'leader':
                leader = node
                break
        
        if not leader:
            return
        
        print("\n Ejecutando comandos de prueba...")
        
        test_commands = [
            {"operation": "SET", "key": "usuario", "value": "RaftCluster"},
            {"operation": "SET", "key": "proyecto", "value": "Consensus"},
            {"operation": "SET", "key": "status", "value": "operational"},
        ]
        
        for i, cmd in enumerate(test_commands, 1):
            success = await leader.append_entry(cmd)
            if success:
                print(f"  ✓ Comando {i}: {cmd['operation']} {cmd['key']}={cmd['value']}")
            await asyncio.sleep(0.5)
        
        # Muestra estado del cluster
        print(f"\n Estado del cluster:")
        for node in self.nodes:
            status = node.get_status()
            state_icon = "" if status['state'] == 'leader' else "👤"
            print(f"  {state_icon} Node {node.node_id}: {status['state']:10} | "
                  f"Term: {status['term']:3} | "
                  f"Log: {status['log_length']} entries")
    
    async def stop(self):
        """Detiene el cluster de forma limpia"""
        if not self.running:
            return
            
        self.running = False
        print("\n Deteniendo cluster...")
        
        # Detiene todos los nodos
        stop_tasks = [node.stop() for node in self.nodes]
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Detiene el servidor web
        if self.web_server:
            await self.web_server.stop()
        
        print(" Cluster detenido correctamente")
        
        # Señaliza que el shutdown está completo
        self._shutdown_event.set()
    
    async def run_forever(self):
        """Mantiene el cluster corriendo indefinidamente"""
        try:
            # Espera hasta que se señalice el shutdown
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            pass


async def main():
    """Punto de entrada principal"""
    cluster = RaftCluster()
    
    # Maneja señales de terminación (solo en Unix)
    if platform.system() != 'Windows':
        loop = asyncio.get_event_loop()
        
        def handle_shutdown(sig):
            print(f"\n Señal recibida: {sig}")
            asyncio.create_task(cluster.stop())
        
        # Registra handlers para SIGINT y SIGTERM
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s))
    
    try:
        await cluster.start()
        await cluster.run_forever()
    except KeyboardInterrupt:
        print("\n Interrupción de teclado detectada")
        await cluster.stop()
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        await cluster.stop()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Hasta luego!")
        sys.exit(0)