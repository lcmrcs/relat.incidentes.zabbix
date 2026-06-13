"""
Cliente mínimo para a API JSON-RPC do Zabbix.

Este módulo concentra chamadas HTTP e payloads da API. O script principal passa
a pedir "busque problemas", "busque hosts" e "busque catálogo" sem carregar
todos os detalhes JSON-RPC no meio do fluxo do relatório.
"""

from datetime import datetime

import requests


REQUEST_TIMEOUT = 60


class ZabbixClient:
    """
    Encapsula URL, token e cabeçalhos usados nas chamadas ao Zabbix.

    A classe não guarda regra visual do relatório. Ela apenas conversa com a API
    e devolve dicionários Python já validados.
    """

    def __init__(self, url, token, timeout=REQUEST_TIMEOUT):
        self.url = url
        self.token = token
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json-rpc",
        }

    def call(self, payload, error_context):
        """
        Envia um payload JSON-RPC para o Zabbix e devolve o JSON validado.

        Esta função concentra timeout, erros de conexão, validação HTTP,
        conversão JSON e erro retornado pela API. Assim, as chamadas problem.get
        e trigger.get seguem o mesmo padrão de segurança.
        """

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )

        except requests.exceptions.ConnectionError:
            print(f"ERRO: não foi possível conectar ao Zabbix ({error_context}).")
            raise SystemExit(1)

        except requests.exceptions.Timeout:
            print(f"ERRO: tempo de conexão excedido ({error_context}).")
            raise SystemExit(1)

        except requests.exceptions.RequestException as error:
            print(f"ERRO: falha na requisição ao Zabbix ({error_context}).")
            print(error)
            raise SystemExit(1)

        if response.status_code != 200:
            print(f"Erro HTTP em {error_context}: {response.status_code}")
            print(response.text)
            raise SystemExit(1)

        try:
            data = response.json()

        except ValueError:
            print(f"ERRO: resposta JSON inválida em {error_context}.")
            print(response.text)
            raise SystemExit(1)

        if "error" in data:
            print(f"Erro retornado pela API Zabbix em {error_context}:")
            print(data["error"])
            raise SystemExit(1)

        return data

    def get_problems(self, status, time_from, time_till):
        """
        Busca eventos/problemas do Zabbix conforme o status solicitado.

        Quando o relatório quer somente incidentes abertos, problem.get é mais
        eficiente porque não traz eventos resolvidos para descarte posterior.
        Para os demais cenários, event.get preserva o histórico do período.
        """

        if status == "abertos":
            request_method = "problem.get"
            request_context = "buscar problemas abertos"
            request_params = {
                "output": [
                    "eventid",
                    "clock",
                    "name",
                    "severity",
                    "objectid",
                ],
                "sortfield": ["eventid"],
                "sortorder": "DESC",
                "time_till": time_till,
            }

        else:
            request_method = "event.get"
            request_context = "buscar eventos de problema"
            request_params = {
                "output": [
                    "eventid",
                    "clock",
                    "name",
                    "severity",
                    "objectid",
                    "r_eventid",
                ],
                "source": 0,
                "object": 0,
                "value": 1,
                "sortfield": ["clock", "eventid"],
                "sortorder": "DESC",
                "time_till": time_till,
            }

        if time_from is not None:
            request_params["time_from"] = time_from

        payload = {
            "jsonrpc": "2.0",
            "method": request_method,
            "params": request_params,
            "auth": self.token,
            "id": 1,
        }

        return self.call(payload, request_context).get("result", [])

    def get_recovery_dates(self, problems):
        """
        Busca a data de resolução dos eventos que possuem r_eventid.

        O retorno é um dicionário no formato {eventid_recuperacao: data_formatada}.
        """

        recovery_event_ids = sorted({
            item.get("r_eventid")
            for item in problems
            if item.get("r_eventid") and item.get("r_eventid") != "0"
        })
        resolved_at_by_event = {}

        if not recovery_event_ids:
            return resolved_at_by_event

        payload = {
            "jsonrpc": "2.0",
            "method": "event.get",
            "params": {
                "output": ["eventid", "clock"],
                "eventids": recovery_event_ids,
            },
            "auth": self.token,
            "id": 2,
        }

        data = self.call(payload, "buscar datas de resolução")

        for event in data.get("result", []):
            resolved_at_by_event[event["eventid"]] = datetime.fromtimestamp(
                int(event["clock"])
            ).strftime("%d/%m/%Y %H:%M")

        return resolved_at_by_event

    def get_trigger_hosts(self, problems):
        """
        Descobre o host relacionado a cada trigger dos problemas retornados.

        Retorna três dicionários:
        - hosts_by_trigger: triggerid -> nome técnico do host
        - host_ids_by_trigger: triggerid -> hostid
        - host_details_by_id: hostid -> host com tags
        """

        trigger_ids = sorted({
            item.get("objectid")
            for item in problems
            if item.get("objectid")
        })

        hosts_by_trigger = {}
        host_ids_by_trigger = {}
        host_details_by_id = {}

        if not trigger_ids:
            return hosts_by_trigger, host_ids_by_trigger, host_details_by_id

        trigger_payload = {
            "jsonrpc": "2.0",
            "method": "trigger.get",
            "params": {
                "output": ["triggerid"],
                "triggerids": trigger_ids,
                "selectHosts": ["hostid", "host", "name"],
            },
            "auth": self.token,
            "id": 3,
        }

        trigger_data = self.call(trigger_payload, "buscar hosts das triggers")

        for trigger in trigger_data.get("result", []):
            hosts = trigger.get("hosts", [])

            if hosts:
                host = hosts[0]
                hosts_by_trigger[trigger["triggerid"]] = host.get("host", "N/A")
                host_ids_by_trigger[trigger["triggerid"]] = host.get("hostid")

        host_ids = sorted({
            hostid
            for hostid in host_ids_by_trigger.values()
            if hostid
        })

        if not host_ids:
            return hosts_by_trigger, host_ids_by_trigger, host_details_by_id

        host_payload = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "output": ["hostid", "host", "name"],
                "hostids": host_ids,
                "selectTags": ["tag", "value"],
            },
            "auth": self.token,
            "id": 4,
        }

        host_data = self.call(host_payload, "buscar tags unidade")

        for host in host_data.get("result", []):
            host_details_by_id[host["hostid"]] = host

        return hosts_by_trigger, host_ids_by_trigger, host_details_by_id

    def get_all_hosts_with_tags(self):
        """
        Busca todos os hosts com tags para montar o catálogo de unidades.

        Essa consulta permite descobrir nome de unidade mesmo quando a unidade
        não teve incidente no período pesquisado.
        """

        payload = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "output": ["hostid", "host", "name"],
                "selectTags": ["tag", "value"],
            },
            "auth": self.token,
            "id": 5,
        }

        data = self.call(payload, "buscar catálogo de unidades")

        return {
            host["hostid"]: host
            for host in data.get("result", [])
        }
