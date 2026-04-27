import httpx
import logging

class FortiGateDiscovery:
    def __init__(self, fgt_ip: str, api_key: str):
        self.fgt_ip = fgt_ip
        self.api_key = api_key
        # Ruta exacta del Swagger: /api/v2/monitor/switch-controller/managed-switch/status
        self.url = f"https://{fgt_ip}/api/v2/monitor/switch-controller/managed-switch/status"

    async def llistar_switches(self) -> list:
        #params = {"access_token": self.api_key}
        switches_trobats = []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

        """ Forcem vdom root a l'espera de la versió 2 on serà parametritzable. Es possible que el vdom root no sigui el gestor dels FSW """
        params = {
            "vdom": "root"
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                response = await client.get(self.url, headers=headers, params=params)
                #print(f"DEBUG API: Status Code {response.status_code}")
                
                if response.status_code == 200:
                    # El Swagger diu que les dades venen a 'results'
                    dades_crues = response.json()
                    results = response.json().get('results', [])
                    
                    # DEBUG: Imprimim el primer objecte per veure les claus reals
                    #if results:
                    #    logging.info(f"DEBUG - Claus reals al JSON: {results[0].keys()}")

                    for s in results:
                        switches_trobats.append({
  				  "name": s.get('switch-id'), 
    			          "serial": s.get('serial'),
    	                          "status": s.get('status'),
                                  "version": s.get('os_version'),
                                  "ip": s.get('connecting_from'),
                                  # Extraiem el model de la versió (ex: 'S448EN-v7.4...' -> 'S448EN')
                                  "model_profile": s.get('os_version', '').split('-')[0] if s.get('os_version') else 'Unknown'
                        })
                else:
                    logging.error(f"Error FGT: {response.status_code}")
        except Exception as e:
            logging.error(f"Error de connexió: {str(e)}")

        return switches_trobats
