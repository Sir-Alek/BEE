"""
Copyright (c) 2025 Alejandro Ramírez  
Bajo la Licencia de Autor Restringida (LAR) v1.0  
Más detalles en LICENSE
""" 

import json
import time
import requests
import logging
import configparser
from base64 import b64encode
from typing import Dict, Optional, List
from pathlib import Path
import sys
import os

# Configuración avanzada de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s @ %(module)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class JiraExtractor:
    def __init__(self, url: str, email: str, api_token: str):
        self.url = url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.session = requests.Session()
        self.auth_header = self._get_auth_header()
        logger.info("Inicializado extractor JIRA para: %s", self.url)

    def _get_auth_header(self) -> str:
        credentials = f"{self.email}:{self.api_token}"
        encoded_credentials = b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f"Basic {encoded_credentials}"

    def check_connection(self) -> bool:
        try:
            response = self.session.get(
                f"{self.url}/rest/api/3/myself",
                headers={"Authorization": self.auth_header},
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                logger.info(
                    "Conexión exitosa | Usuario: %s | Correo: %s",
                    user_data.get('displayName'),
                    user_data.get('emailAddress')
                )
                return True
                
            logger.error(
                "Error de autenticación | Código: %d | Respuesta: %s",
                response.status_code,
                response.text[:100] + "..." if len(response.text) > 100 else response.text
            )
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error("Error de conexión | Detalles: %s", str(e))
            return False
        except Exception as e:
            logger.exception("Error inesperado durante check_connection: %s", str(e))
            return False

    def get_issue(self, issue_id: str) -> Optional[Dict]:
        try:
            logger.info("Solicitando issue: %s", issue_id)
            response = self.session.get(
                f"{self.url}/rest/api/3/issue/{issue_id}",
                headers={"Authorization": self.auth_header},
                params={"expand": "renderedFields,names"}
            )
            
            if response.status_code == 200:
                logger.debug("Respuesta exitosa para issue %s", issue_id)
                return response.json()
                
            logger.warning(
                "Error obteniendo issue %s | Código: %d | Respuesta: %s",
                issue_id,
                response.status_code,
                response.text[:200] + "..." if len(response.text) > 200 else response.text
            )
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error("Error de red obteniendo issue %s: %s", issue_id, str(e))
            return None
        except Exception as e:
            logger.exception("Error crítico obteniendo issue %s: %s", issue_id, str(e))
            return None

    def get_all_issues(self, project_key: str) -> Optional[List[str]]:
        try:
            issues = []
            start_at = 0
            max_results = 100
            total = None
            
            logger.info("Iniciando extracción masiva para proyecto: %s", project_key)
            
            while True:
                params = {
                    "jql": f"project = {project_key} ORDER BY created ASC",
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": "key,created"
                }
                
                response = self.session.get(
                    f"{self.url}/rest/api/3/search",
                    headers={"Authorization": self.auth_header},
                    params=params,
                    timeout=15
                )
                
                if response.status_code != 200:
                    logger.error(
                        "Error en extracción masiva | Código: %d | Respuesta: %s",
                        response.status_code,
                        response.text[:200] + "..." if len(response.text) > 200 else response.text
                    )
                    return None
                    
                data = response.json()
                if total is None:
                    total = data.get('total', 0)
                    logger.info("Total de issues detectados: %d", total)
                    
                batch = [issue["key"] for issue in data.get("issues", [])]
                issues.extend(batch)
                logger.debug(
                    "Procesado lote %d-%d | Total acumulado: %d",
                    start_at,
                    start_at + max_results,
                    len(issues)
                )
                
                if data.get('startAt', 0) + data.get('maxResults', 0) >= total:
                    break
                    
                start_at += max_results
                # Throttling para evitar bloqueos
                time.sleep(0.5)
            
            logger.info("Extracción masiva completada | Issues obtenidos: %d", len(issues))
            return issues
            
        except requests.exceptions.RequestException as e:
            logger.error("Error de red en extracción masiva: %s", str(e))
            return None
        except Exception as e:
            logger.exception("Error crítico en extracción masiva: %s", str(e))
            return None

    def save_issue(self, issue: Dict, output_dir: str = "jira_issues") -> None:
        try:
            issue_key = issue.get("key", "unknown_issue")
            safe_project_key = issue_key.split('-')[0]
            final_output_dir = os.path.join(output_dir, safe_project_key)
            
            Path(final_output_dir).mkdir(parents=True, exist_ok=True)
            
            file_path = Path(final_output_dir) / f"{issue_key}.json"
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(issue, f, indent=2, ensure_ascii=False)
                
            logger.info(
                "Issue guardado | Ruta: %s | Tamaño: %.2f KB",
                file_path,
                os.path.getsize(file_path)/1024
            )
            
        except json.JSONEncodeError as e:
            logger.error("Error serializando issue %s: %s", issue_key, str(e))
        except OSError as e:
            logger.error("Error de escritura en %s: %s", file_path, str(e))
        except Exception as e:
            logger.exception("Error crítico guardando issue %s: %s", issue_key, str(e))

def main():
    """Función CLI mantenida para compatibilidad"""
    print("\n" + "="*40)
    print("JIRA Extractor (Modo Línea de Comandos)")
    print("="*40 + "\n")
    
    try:
        config = configparser.ConfigParser()
        config.read('secrets/secrets.ini', encoding='utf-8')
        
        extractor = JiraExtractor(
            config.get('JIRA', 'URL'),
            config.get('JIRA', 'EMAIL'),
            config.get('JIRA', 'API_TOKEN')
        )
        
        if not extractor.check_connection():
            print("\n❌ Error: No se pudo conectar a JIRA")
            return
            
        project_key = input("\n▶ Clave del proyecto (ej: BT115): ").strip().upper()
        
        print("\n" + "-"*40)
        print("1. Extraer issue específico")
        print("2. Extraer todos los issues")
        print("-"*40)
        option = input("▶ Seleccione una opción: ").strip()
        
        if option == "1":
            issue_number = input("\n▶ Número del issue (ej: 123): ").strip()
            issue_id = f"{project_key}-{issue_number}"
            
            print(f"\n🔄 Buscando issue {issue_id}...")
            if issue := extractor.get_issue(issue_id):
                extractor.save_issue(issue)
                print(f"\n✅ Issue {issue_id} guardado en:")
                print(f"   {os.path.abspath('jira_issues')}")
            else:
                print("\n❌ No se encontró el issue")
                
        elif option == "2":
            print(f"\n🔄 Buscando todos los issues de {project_key}...")
            if issues := extractor.get_all_issues(project_key):
                print(f"\n🔍 Encontrados {len(issues)} issues")
                print("⏳ Guardando... (esto puede tomar tiempo)")
                
                for i, issue_id in enumerate(issues, 1):
                    issue = extractor.get_issue(issue_id)
                    extractor.save_issue(issue)
                    print(f"   [{i}/{len(issues)}] {issue_id}")
                    
                print(f"\n✅ Todos los issues guardados en:")
                print(f"   {os.path.abspath('jira_issues')}")
            else:
                print("\n❌ No se encontraron issues")
                
        else:
            print("\n⚠ Opción no válida")
            
    except KeyboardInterrupt:
        print("\n\n⚠ Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n🔥 Error crítico: {str(e)}")
    finally:
        print("\n" + "="*40)
        print("Proceso finalizado")

if __name__ == "__main__":
    main()