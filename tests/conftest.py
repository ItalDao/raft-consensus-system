"""
Configuración de pytest para tests del sistema Raft
Incluye fixtures y limpieza de tasks asyncio
"""

import pytest
import asyncio
import warnings


@pytest.fixture
def event_loop():
    """Crea un nuevo event loop para cada test"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    
    # Limpia todas las tasks pendientes
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    
    # Ejecuta las cancelaciones
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    
    # Cierra el loop
    loop.close()


@pytest.fixture(autouse=True)
def suppress_task_warnings():
    """Suprime warnings sobre tasks destruidas"""
    warnings.filterwarnings(
        "ignore",
        message=".*Task was destroyed but it is pending.*",
        category=RuntimeWarning
    )


@pytest.fixture
async def cleanup_nodes():
    """Fixture para limpiar nodos después de cada test"""
    nodes = []
    
    yield nodes
    
    # Limpia todos los nodos creados
    for node in nodes:
        try:
            await node.stop()
        except Exception:
            pass


def pytest_configure(config):
    """Configuración global de pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio coroutine"
    )