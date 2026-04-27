import httpx
import logging
from app.core.config import settings
from app.database import check_port_frozen

class FortiSwitchClient:
    def __init__(self, fsw_ip: str, password: str):
        self.fsw_ip = fsw_ip
        self.password = password
        self.base_url = f"https://{fsw_ip}/api/v2"
        self.client = httpx.AsyncClient(verify=False, timeout=60.0, follow_redirects=False)

    async def login(self) -> bool:
      url = f"{self.base_url.replace('/api/v2', '')}/logincheck"
      payload = f"username={settings.SWITCH_USER}&secretkey={self.password}"
    
      try:
        res = await self.client.post(url, data=payload, timeout=10.0)
        if res.status_code == 200:
            csrf_token = self.client.cookies.get("ccsrftoken")
            if csrf_token:
                self.client.headers.update({
                    "X-CSRFTOKEN": csrf_token.strip('"'),
                    "Referer": self.base_url.split('/api')[0] + "/"
                })
            return True
        return False
      except Exception:
        return False

    def _get_headers(self):
        token = self.client.cookies.get("ccsrftoken")
        if token:
            token = token.strip('"')
        return {"X-CSRFTOKEN": token} if token else {}

    async def obtenir_ports_fisics(self) -> list:
        url = f"{self.base_url}/monitor/switch/port"
        try:
            res = await self.client.get(url)
            if res.status_code == 200:
                data = res.json()
                results = data.get('results', {})
                if isinstance(results, list):
                    return [p['name'] for p in results if 'name' in p]
                elif isinstance(results, dict):
                    sub = results.get('port') or results.get('interfaces')
                    if isinstance(sub, list):
                        return [p['name'] for p in sub if 'name' in p]
                    return [k for k in results.keys() if k.startswith('port')]
            return []
        except Exception: return []

    async def configurar_servicios_custom(self, custom_services_data: list) -> bool:
        url_svc = f"{self.base_url}/cmdb/switch.acl.service/custom"
        
        try:
            r = await self.client.get(url_svc)
            existents = [s.get('name') for s in r.json().get('results', [])] if r.status_code == 200 else []

            for svc in custom_services_data:
                if svc.get("name") not in existents:
                    await self.client.post(url_svc, json=svc, headers=self._get_headers())
            return True
        except Exception: return False

    async def aplicar_acls_prelookup(self, serial: str, lista_puertos: list, standard_acls: list) -> bool:
        url_base = f"{self.base_url}/cmdb/switch.acl/prelookup"
 
        id_counter = 1
        for regla in standard_acls:
            for puerto in lista_puertos:
                if await check_port_frozen(serial, puerto):
                    continue

                payload = {
                    "id": id_counter,
                    "description": regla.get('name', 'N/A'),
                    "classifier": regla.get('classifier', {}),
                    "action": regla.get('action', {}),
                    "interface": puerto
                }

                url_id = f"{url_base}/{id_counter}"
                headers = self._get_headers()

                res = await self.client.post(url_base, json=payload, headers=headers)

                if res.status_code >= 400:
                    logging.error(f"Fallo a ID {id_counter} ({puerto}): {res.status_code} - {res.text}")
                    return False

                id_counter += 1
                
        return True

    async def crear_segell_sincro(self) -> bool:
        url = f"{self.base_url}/cmdb/switch.acl.service/custom"
        target_name = f"SYNC_{settings.current_version}"
        
        payload = {
            "name": target_name, 
            "protocol": "TCP/UDP/SCTP",
            "comment": f"Sincronitzat per Oriol - v{settings.current_version}"
        }
        
        res = await self.client.post(url, json=payload, headers=self._get_headers())
        return res.status_code in [200, 500, 424]

    async def obtenir_versio_segell(self) -> str:
        url = f"{self.base_url}/cmdb/switch.acl.service/custom"
        try:
            res = await self.client.get(url)
            if res.status_code == 200:
                serveis = res.json().get('results', [])
                for s in serveis:
                    if s['name'].startswith('SYNC_'):
                        return s['name'].replace('SYNC_', '')
            return "Mai"
        except Exception:
            return "Error"
    
    async def eliminar_servei_si_existeix(self, name: str) -> bool:
        url = f"{self.base_url}/cmdb/switch.acl.service/custom/{name}"
        try:
           res = await self.client.delete(url)
           if res.status_code in [200, 404]:
              return True
           return False
        except Exception:
           return False   
    async def netejar_segells_antics(self):
      url = f"{self.base_url}/cmdb/switch.acl.service/custom"
      try:
        res = await self.client.get(url)
        if res.status_code == 200:
            data = res.json()
            segells = [s['name'] for s in data.get('results', []) if s.get('name', '').startswith('SYNC_')]

            for segell in segells:
                delete_url = f"{url}/{segell}"
                await self.client.delete(delete_url)
                
        return True
      except Exception as e:
        logging.error(f"Error netejant segells: {str(e)}")
        return False


    async def buidar_politiques_acl(self) -> bool:
        url = f"{self.base_url}/cmdb/switch.acl/prelookup"
        try:
            res = await self.client.get(url)
            if res.status_code == 200:
                data = res.json()
                results = data.get('results', [])

                for policy in results:
                    p_id = policy.get('id')
                    if p_id is not None:
                        delete_url = f"{url}/{p_id}"
                        await self.client.delete(delete_url)
            
            return True
        except Exception as e:
            return False


    async def close(self):
       await self.client.aclose()
    
    async def obtenir_acl_stats_prelookup(self) -> list[dict]:
        url = f"{self.base_url}/monitor/switch/acl-stats-prelookup/"
        resp = await self.client.get(url)
        resp.raise_for_status()
    
        data = resp.json()
    
        if isinstance(data, dict):
            if "results" in data and isinstance(data["results"], list):
                return data["results"]
            if {"policy_id", "packets", "bytes"} <= set(data.keys()):
                return [data]
    
        if isinstance(data, list):
            return data
    
        return []
    
    
    async def obtenir_acl_prelookup_policy_map(self) -> dict[int, str]:
        url = f"{self.base_url}/cmdb/switch.acl/prelookup"
        resp = await self.client.get(url)
        resp.raise_for_status()
    
        data = resp.json()
    
        if isinstance(data, dict):
            items = data.get("results", [])
        elif isinstance(data, list):
            items = data
        else:
            items = []
    
        result = {}
    
        for item in items:
            if not isinstance(item, dict):
                continue
    
            policy_id = item.get("policyid") or item.get("policy_id") or item.get("id")
            nom_acl = item.get("description") or item.get("name") or item.get("policy-name") or item.get("policy_name")
    
            if policy_id is None:
                continue
    
            try:
                policy_id = int(policy_id)
            except (TypeError, ValueError):
                continue
    
            if nom_acl:
                result[policy_id] = str(nom_acl)
    
        return result
    
    
    async def obtenir_acl_matches(self) -> list[dict]:
        stats = await self.obtenir_acl_stats_prelookup()
    
        policy_map = None
        matches = []
    
        for stat in stats:
            try:
                packets = int(stat.get("packets", 0))
            except (TypeError, ValueError):
                packets = 0
    
            if packets <= 0:
                continue
    
            policy_id = stat.get("policy_id")
            try:
                policy_id = int(policy_id)
            except (TypeError, ValueError):
                continue
    
            nom_acl = stat.get("description")
    
            if not nom_acl:
                if policy_map is None:
                    policy_map = await self.obtenir_acl_prelookup_policy_map()
                nom_acl = policy_map.get(policy_id, f"policy_{policy_id}")
    
            matches.append({
                "policy_id": policy_id,
                "nom": nom_acl,
                "packets": packets
            })
    
        return matches
