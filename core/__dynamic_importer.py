import importlib.util
import sys
from core import get_core_file

def load_obfuscated_module(module_name, package='core'):
    """
    Carga dinámicamente un módulo desde contenido ofuscado
    con mejor manejo de errores para PyInstaller
    """
    try:
        # Obtener el contenido desofuscado
        content = get_core_file(f'{module_name}.py')
        
        if content is None:
            # Intentar cargar desde archivo original como fallback
            try:
                module = __import__(f'{package}.{module_name}', fromlist=['*'])
                return module
            except ImportError:
                raise ImportError(f"No se pudo cargar el módulo ofuscado: {module_name}")
        
        # Crear un spec para el módulo
        spec = importlib.util.spec_from_loader(module_name, loader=None)
        module = importlib.util.module_from_spec(spec)
        
        # Ejecutar el código en el contexto del módulo
        exec(content, module.__dict__)
        
        # Registrar el módulo en sys.modules
        full_module_name = f'{package}.{module_name}'
        sys.modules[full_module_name] = module
        
        return module
    except Exception as e:
        # Fallback a importación tradicional
        try:
            module = __import__(f'{package}.{module_name}', fromlist=['*'])
            return module
        except ImportError:
            raise ImportError(f"No se pudo cargar el módulo {module_name}: {str(e)}")

# Cargar los módulos críticos al importar este archivo
try:
    puppeteer_script_converter = load_obfuscated_module('puppeteer_script_converter')
except ImportError as e:
    # Fallback extremo - crear módulos vacíos
    class FallbackPuppeteerConverter:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Módulo no cargado: PuppeteerToBehaveConverter")
    
    puppeteer_script_converter = type('Module', (), {
        'PuppeteerToBehaveConverter': FallbackPuppeteerConverter
    })

try:
    video_recorder = load_obfuscated_module('video_recorder')
except ImportError as e:
    # Fallback extremo - crear módulos vacíos
    class FallbackScreenRecorder:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Módulo no cargado: ScreenRecorder")
    
    video_recorder = type('Module', (), {
        'ScreenRecorder': FallbackScreenRecorder
    })
    
try:
    step_by_step_converter = load_obfuscated_module('step_by_step_converter')
except ImportError as e:
    # Fallback extremo - crear módulos vacíos
    class FallbackPuppeteerToStepByStepConverter:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Módulo no cargado: PuppeteerToStepByStepConverter")
    
    step_by_step_converter = type('Module', (), {
        'PuppeteerToStepByStepConverter': FallbackPuppeteerToStepByStepConverter
    })    