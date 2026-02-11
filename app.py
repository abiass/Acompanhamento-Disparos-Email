import os
import io
import csv
from typing import Any, Dict, Tuple, List

import requests
from flask import Flask, jsonify, request
import dotenv
try:
	import psycopg2
	import psycopg2.extras
except ImportError:
	psycopg2 = None
try:
	import openpyxl
except ImportError:
	openpyxl = None


def _get_db_campaign_stats_by_flowbiz_id(flowbiz_campaign_id: str) -> Dict[str, int]:
	"""Busca Qtd Acessos e Qtd Leads usando o id_campanha_flowbiz."""
	if not psycopg2:
		return {"QtdAcessos": 0, "QtdLeads": 0}
	
	try:
		conn = psycopg2.connect(
			dbname=os.getenv('DB_NAME'),
			user=os.getenv('DB_USER'),
			password=os.getenv('DB_PASSWORD'),
			host=os.getenv('DB_HOST'),
			port=os.getenv('DB_PORT')
		)
		cur = conn.cursor()
		
		# Contar acessos
		cur.execute(
			"""
			SELECT COUNT(*)
			FROM autobot.campanha_acessos ca
			JOIN autobot.campanhas c ON c.id = ca.campanha_id
			WHERE c.id_campanha_flowbiz = %s
			""",
			(flowbiz_campaign_id,)
		)
		qtd_acessos = cur.fetchone()[0]
		
		# Contar leads (formularios)
		cur.execute(
			"""
			SELECT COUNT(*)
			FROM autobot.formulario f
			JOIN autobot.campanhas c ON c.id = f.campanha_id
			WHERE c.id_campanha_flowbiz = %s
			""",
			(flowbiz_campaign_id,)
		)
		qtd_leads = cur.fetchone()[0]
		
		cur.close()
		conn.close()
		
		return {"QtdAcessos": qtd_acessos, "QtdLeads": qtd_leads}
	except Exception as e:
		print(f"Erro ao buscar stats da campanha {flowbiz_campaign_id}: {e}")
		return {"QtdAcessos": 0, "QtdLeads": 0}

def create_app() -> Flask:
	dotenv.load_dotenv()
	app = Flask(__name__)

	app.config["FLOWBIZ_ENDPOINT"] = os.getenv(
		"FLOWBIZ_ENDPOINT", "https://mbiz.mailclick.me/api.php"
	)
	app.config["FLOWBIZ_API_KEY_Voxcall"] = os.getenv("FLOWBIZ_API_KEY_Voxcall", "")
	app.config["FLOWBIZ_METHOD_PARAM"] = os.getenv("FLOWBIZ_METHOD_PARAM", "Command")
	app.config["FLOWBIZ_RESPONSE_FORMAT"] = os.getenv(
		"FLOWBIZ_RESPONSE_FORMAT", "JSON"
	)
	app.config["FLOWBIZ_APPEND_METHOD_PATH"] = os.getenv(
		"FLOWBIZ_APPEND_METHOD_PATH", "false"
	).strip().lower() in {"1", "true", "yes"}
	app.config["FLOWBIZ_TIMEOUT_SECONDS"] = float(
		os.getenv("FLOWBIZ_TIMEOUT_SECONDS", "20")
	)

	# Coletar todas as chaves da forma FLOWBIZ_API_KEY_* (várias contas)
	api_keys = {k: v for k, v in os.environ.items() if k.startswith("FLOWBIZ_API_KEY_") and v}
	# Remover possíveis entradas em branco
	api_keys = {k: v.strip().strip('"') for k, v in api_keys.items() if v and v.strip()}
	app.config["FLOWBIZ_API_KEYS"] = api_keys

	# Map our internal endpoints to Flowbiz API methods.
	route_map = {
		"subscribers/get": "Subscribers.Get",
		"subscribers/delete": "Subscribers.Delete",
		"subscribers/import": "Subscribers.Import",
		"subscriber/get": "Subscriber.Get",
		"subscriber/subscribe": "Subscriber.Subscribe",
		"subscriber/optin": "Subscriber.Optin",
		"subscriber/unsubscribe": "Subscriber.Unsubscribe",
		"subscriber/update": "Subscriber.Update",
		"subscriber/login": "Subscriber.Login",
		"subscriber/get-lists": "Subscriber.GetLists",
		"subscriber/interactions": "Subscriber.Interactions",
		"subscriber/get-optout": "Subscriber.GetOptOut",
		"media/upload": "Media.Upload",
		"media/retrieve": "Media.Retrieve",
		"media/browse": "Media.Browse",
		"campaign/get": "Campaign.Get",
		"campaign/create": "Campaign.Create",
		"campaign/update": "Campaign.Update",
		"campaigns/get": "Campaigns.Get",
		"campaigns/delete": "Campaigns.Delete",
		"campaigns/archive-url": "Campaigns.Archive.GetURL",
		"custom-field/create": "CustomField.Create",
		"custom-field/update": "CustomField.Update",
		"custom-fields/copy": "CustomFields.Copy",
		"custom-fields/delete": "CustomFields.Delete",
		"custom-fields/get": "CustomFields.Get",
		"autoresponder/create": "AutoResponder.Create",
		"autoresponder/update": "AutoResponder.Update",
		"autoresponder/get": "AutoResponder.Get",
		"autoresponder/delete": "AutoResponder.Delete",
		"autoresponder/webhook": "AutoResponder.Webhook",
		"autoresponder/sequences": "AutoResponder.Sequences",
		"list/create": "List.Create",
		"list/update": "List.Update",
		"list/get": "List.Get",
		"lists/get": "Lists.Get",
		"lists/delete": "Lists.Delete",
		"segment/create": "Segment.Create",
		"segment/update": "Segment.Update",
		"segment/get": "Segment.Get",
		"segments/delete": "Segments.Delete",
		"segments/copy": "Segments.Copy",
		"tag/create": "Tag.Create",
		"tag/update": "Tag.Update",
		"tags/get": "Tags.Get",
		"tags/delete": "Tags.Delete",
		"tag/assign-to-campaigns": "Tag.AssignToCampaigns",
		"tag/unassign-from-campaigns": "Tag.UnassignFromCampaigns",
	}

	def build_payload(method: str, data: Dict[str, Any]) -> Dict[str, Any]:
		api_key = app.config["FLOWBIZ_API_KEY_Voxcall"].strip()
		if not api_key:
			raise ValueError("FLOWBIZ_API_KEY_Voxcall is not configured")

		payload = {"APIKey": api_key}
		payload[app.config["FLOWBIZ_METHOD_PARAM"]] = method
		payload.setdefault("ResponseFormat", app.config["FLOWBIZ_RESPONSE_FORMAT"])
		payload.update(data)
		return payload

	def call_flowbiz(method: str, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
		try:
			payload = build_payload(method, data)
		except ValueError as exc:
			return {"error": str(exc)}, 500

		endpoint = app.config["FLOWBIZ_ENDPOINT"]
		if app.config["FLOWBIZ_APPEND_METHOD_PATH"]:
			endpoint = endpoint.rstrip("/") + f"/{method}"
		timeout = app.config["FLOWBIZ_TIMEOUT_SECONDS"]

		try:
			response = requests.post(endpoint, data=payload, timeout=timeout)
		except requests.RequestException as exc:
			return {"error": "Flowbiz request failed", "detail": str(exc)}, 502

		try:
			return response.json(), response.status_code
		except ValueError:
			return {"raw": response.text}, response.status_code

	@app.get("/health")
	def health() -> Tuple[Dict[str, Any], int]:
		return {"status": "ok"}, 200

	@app.get("/api")
	def list_routes() -> Tuple[Dict[str, Any], int]:
		return {"routes": sorted(route_map.keys())}, 200

	@app.post("/api/<path:route_key>")
	def proxy(route_key: str) -> Tuple[Dict[str, Any], int]:
		method = route_map.get(route_key)
		if not method:
			return {"error": "Unknown route", "route": route_key}, 404

		data = request.get_json(silent=True) or {}
		if not isinstance(data, dict):
			return {"error": "Invalid JSON body, expected object"}, 400

		payload, status = call_flowbiz(method, data)
		return jsonify(payload), status


	def _manage_campaigns(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
		action = str(data.pop("action", "")).strip().lower().replace("_", "-")
		
		# Se for create com lista nova (FieldMappings ou ListName), usar lógica com mapeamento
		if action == "create" and ("FieldMappings" in data or "ListName" in data):
			campaign_name = data.get('CampaignName', '').strip()
			subject = data.get('Subject', '').strip()
			list_name = data.get('ListName', '').strip()
			segment_name = data.get('SegmentName', '').strip()
			field_mappings = data.get('FieldMappings', {})
			custom_fields = data.get('CustomFields', [])
			from_email = data.get('FromEmail', '').strip()
			
			if not campaign_name or not subject:
				return {
					"error": "CampaignName e Subject são obrigatórios"
				}, 400
			
			try:
				api_key = app.config["FLOWBIZ_API_KEY_Voxcall"].strip()
				endpoint = app.config["FLOWBIZ_ENDPOINT"]
				timeout = app.config["FLOWBIZ_TIMEOUT_SECONDS"]
				
				list_id = None
				segment_id = None
				
				# 1. Criar lista se for novo
				if list_name:
					list_payload = {
						"APIKey": api_key,
						"Command": "List.Create",
						"ListName": list_name,
						"ResponseFormat": "JSON"
					}
					list_res = requests.post(endpoint, data=list_payload, timeout=timeout)
					list_data = list_res.json()
					
					if list_data.get("Success") or list_data.get("ListID"):
						list_id = list_data.get("ListID")
					else:
						return {"error": f"Erro ao criar lista: {list_data.get('ErrorText', 'Desconhecido')}"}, 400
				
				# 2. Criar campos customizados com base no mapeamento
				if field_mappings and list_id:
					for original_col, mapped_name in field_mappings.items():
						if mapped_name.lower() not in ['email', 'name', 'nome']:  # Pular campos padrão
							field_payload = {
								"APIKey": api_key,
								"Command": "CustomField.Create",
								"FieldName": mapped_name,
								"FieldType": "text",
								"ListID": list_id,
								"ResponseFormat": "JSON"
							}
							try:
								requests.post(endpoint, data=field_payload, timeout=timeout)
							except:
								pass  # Continuar mesmo se falhar em alguns campos
				
				# 2.1. Criar campos customizados adicionais
				if custom_fields and list_id:
					for field_name in custom_fields:
						if field_name.strip():
							field_payload = {
								"APIKey": api_key,
								"Command": "CustomField.Create",
								"FieldName": field_name.strip(),
								"FieldType": "text",
								"ListID": list_id,
								"ResponseFormat": "JSON"
							}
							try:
								requests.post(endpoint, data=field_payload, timeout=timeout)
							except:
								pass  # Continuar mesmo se falhar em alguns campos
				
				# 3. Criar segmento se solicitado
				if segment_name and list_id:
					segment_payload = {
						"APIKey": api_key,
						"Command": "Segment.Create",
						"SegmentName": segment_name,
						"ListID": list_id,
						"ResponseFormat": "JSON"
					}
					try:
						seg_res = requests.post(endpoint, data=segment_payload, timeout=timeout)
						seg_data = seg_res.json()
						segment_id = seg_data.get("SegmentID")
					except:
						pass  # Continuar mesmo se segmento falhar
				
				# 4. Criar campanha
				campaign_payload = {
					"APIKey": api_key,
					"Command": "Campaign.Create",
					"CampaignName": campaign_name,
					"Subject": subject,
					"ResponseFormat": "JSON"
				}
				
				if list_id:
					campaign_payload["ListID"] = list_id
				
				if segment_id:
					campaign_payload["SegmentID"] = segment_id
				
				if from_email:
					campaign_payload["FromEmail"] = from_email
				
				camp_res = requests.post(endpoint, data=campaign_payload, timeout=timeout)
				camp_data = camp_res.json()
				
				return jsonify(camp_data), camp_res.status_code
			
			except Exception as e:
				return {"error": str(e)}, 502
		
		# Caso contrário, usar a lógica padrão
		actions_map = {
			"get": "Campaign.Get",
			"create": "Campaign.Create",
			"update": "Campaign.Update",
			"list": "Campaigns.Get",
			"delete": "Campaigns.Delete",
			"archive-url": "Campaigns.Archive.GetURL",
		}
		method = actions_map.get(action)
		if not method:
			return {
				"error": "Invalid action",
				"allowed": sorted(actions_map.keys()),
			}, 400
		# Apply defaults for list action
		if action == "list":
			data.setdefault("RecordsPerRequest", "10")
			data.setdefault("RecordsFrom", "0")
			# Ordenar por data de envio por padrão (mais recentes primeiro)
			data.setdefault("OrderField", "SendProcessFinishedOn")
			data.setdefault("OrderType", "DESC")
			
			# Agregar campanhas de todas as contas configuradas (paginação feita depois da união)
			per_page = int(str(data.get("RecordsPerRequest", "10")))
			start = int(str(data.get("RecordsFrom", "0")))
			api_keys = app.config.get("FLOWBIZ_API_KEYS", {})
			merged = []
			endpoint = app.config["FLOWBIZ_ENDPOINT"]
			timeout = app.config["FLOWBIZ_TIMEOUT_SECONDS"]
			for name, key in api_keys.items():
				try:
					# Escolher quantos registros requisitar por conta.
					# Antes: max(per_page * 3, per_page) — às vezes omitia envios recentes.
					# Agora: buscar mais (multiplicador 10), com limites para evitar cargas excessivas.
					local_records = min(max(per_page * 10, 100), 500)
					local_payload = {
						"APIKey": key,
						"Command": "Campaigns.Get",
						"RecordsPerRequest": str(local_records),
						"ResponseFormat": "JSON"
					}
					# aplicar filtro de status se presente
					if "CampaignStatus" in data:
						local_payload["CampaignStatus"] = data["CampaignStatus"]
					res = requests.post(endpoint, data=local_payload, timeout=timeout)
					app.logger.debug(f"Account {name} response status: {res.status_code} (requested {local_records})")
					d = res.json()
					campaigns = d.get("Campaigns") if isinstance(d, dict) else None
					app.logger.debug(f"Account {name} returned campaigns count: {len(campaigns) if campaigns else 0}")
					if campaigns:
						for c in campaigns:
							# Keep raw origin key and add a display-friendly Origin field
							c["_origin_api"] = name
							try:
								c["Origin"] = name.replace('FLOWBIZ_API_KEY_', '')
							except Exception:
								c["Origin"] = name
							merged.append(c) 
				except Exception as e:
					app.logger.exception(f"Error fetching campaigns for {name}: {e}")
			# ordenar por data de envio (SendProcessFinishedOn / SendDate / CreateDateTime)
			import datetime as _dt
			def _parse_dt(c):
				s = c.get("SendProcessFinishedOn") or c.get("SendDate") or c.get("CreateDateTime")
				if not s:
					return _dt.datetime.min
				s_str = str(s).strip()
				# Normalizar separadores e formatos comuns (ex.: "10/02/2026 - 09:32")
				s_clean = s_str.replace(' - ', ' ').replace('/', '-').replace('.', '-')
				# Tentar múltiplos formatos: ISO/ano-mês-dia e dia-mês-ano
				formats = (
					"%Y-%m-%d %H:%M:%S",
					"%Y-%m-%dT%H:%M:%S",
					"%Y-%m-%d",
					"%d-%m-%Y %H:%M:%S",
					"%d-%m-%Y %H:%M",
					"%d-%m-%Y",
				)
				for fmt in formats:
					try:
						return _dt.datetime.strptime(s_clean, fmt)
					except Exception:
						continue
				# Tentativa final com ISO no texto original
				try:
					return _dt.datetime.fromisoformat(s_str.replace(' ', 'T'))
				except Exception:
						pass
			# Se nada funcionar, retornar a data mínima para tratar como mais antiga
				return _dt.datetime.min
			merged_sorted = sorted(merged, key=_parse_dt, reverse=True)
			total = len(merged_sorted)
			payload = {"TotalCampaigns": total, "Campaigns": merged_sorted[start:start+per_page]}
			status = 200
		else:
			payload, status = call_flowbiz(method, data)
		
		# Se for list de campanhas, enriquecer com estatísticas
		if action == "list" and status == 200 and isinstance(payload, dict) and "Campaigns" in payload:
			try:
				api_keys = app.config.get("FLOWBIZ_API_KEYS", {})
				endpoint = app.config["FLOWBIZ_ENDPOINT"]
				timeout = app.config["FLOWBIZ_TIMEOUT_SECONDS"]
				default_api_key = app.config.get("FLOWBIZ_API_KEY_Voxcall", "").strip()
				
				for campaign in payload.get("Campaigns", []):
					# Assegurar que exista campo legível de origem
					origin_key = campaign.get("_origin_api")
					if not campaign.get("Origin"):
						try:
							campaign["Origin"] = origin_key.replace('FLOWBIZ_API_KEY_', '') if origin_key else '-'
						except Exception:
							campaign["Origin"] = origin_key or '-'
					
					# Inicializar campos de contagem
					campaign["QtdLeads"] = 0
					campaign["QtdAcessos"] = 0
					
					# Buscar stats direto pelo id_campanha_flowbiz
					campaign_flowbiz_id = str(campaign.get("CampaignID", ""))
					if campaign_flowbiz_id:
						stats = _get_db_campaign_stats_by_flowbiz_id(campaign_flowbiz_id)
						campaign["QtdLeads"] = stats.get("QtdLeads", 0)
						campaign["QtdAcessos"] = stats.get("QtdAcessos", 0)
					
					# Usar métricas já presentes na listagem quando disponíveis
					try:
						existing_sent = int(campaign.get("TotalSent", 0) or 0)
						existing_opens = int(campaign.get("TotalOpens", 0) or 0)
						# Preferir UniqueClicks quando disponível (clicadores únicos)
						existing_clicks = int(campaign.get("UniqueClicks", campaign.get("TotalClicks", 0) or 0) or 0)
					except Exception:
						existing_sent = existing_opens = existing_clicks = 0
					if existing_sent > 0 or existing_opens > 0 or existing_clicks > 0:
						# Se já existem métricas na listagem, mapeá-las para os nomes usados pelo front
						campaign["EmailsSent"] = existing_sent
						campaign["TotalOpens"] = existing_opens
						# Mapear TotalClicks para clicadores únicos para o front mostrar "clicks únicos"
						campaign["TotalClicks"] = existing_clicks
					continue
					campaign_id = campaign.get("CampaignID")
					if campaign_id:
						# Usar a chave correta da conta de origem quando disponível
						used_api_key = api_keys.get(origin_key, default_api_key)
						try:
							stats_payload = {
								"APIKey": used_api_key,
								"Command": "Campaign.Get",
								"CampaignID": campaign_id,
								"ResponseFormat": "JSON"
							}
							stats_res = requests.post(endpoint, data=stats_payload, timeout=timeout)
							stats_data = stats_res.json()
							campaign_info = stats_data.get("Campaign", {})
							campaign["EmailsSent"] = int(campaign_info.get("TotalSent", 0) or 0)
							campaign["TotalOpens"] = int(campaign_info.get("TotalOpens", 0) or 0)
						# Priorizar UniqueClicks (clicadores únicos) quando disponível
							campaign["TotalClicks"] = int(campaign_info.get("UniqueClicks", campaign_info.get("TotalClicks", 0) or 0) or 0)
						# Também expor UniqueClicks explicitamente para referência
							campaign["UniqueClicks"] = int(campaign_info.get("UniqueClicks", 0) or 0)
						except:
							campaign["EmailsSent"] = 0
							campaign["TotalOpens"] = 0
							campaign["TotalClicks"] = 0
			except Exception:
				# Se houver erro geral, apenas retornar sem as estadísticas
				pass
		
			return jsonify(payload), status

	# Listas e contatos removidos: _manage_lists, _manage_contacts, rotas e helper de importação foram excluídos conforme solicitado.
	# (Mantendo apenas funcionalidades relacionadas a campanhas)

	@app.post("/api/campaigns/manage")
	def manage_campaigns_post() -> Tuple[Dict[str, Any], int]:
		data = request.get_json(silent=True) or {}
		if not isinstance(data, dict):
			return {"error": "Invalid JSON body, expected object"}, 400
		return _manage_campaigns(data)

	@app.get("/api/campaigns/manage")
	def manage_campaigns_get() -> Tuple[Dict[str, Any], int]:
		data = dict(request.args)
		return _manage_campaigns(data)


	@app.post("/api/campaigns/clone")
	def clone_campaign() -> Tuple[Dict[str, Any], int]:
		"""Clona uma campanha existente"""
		data = request.get_json(silent=True) or {}
		
		clone_from_id = data.get('CloneCampaignID')
		new_name = data.get('CampaignName')
		new_subject = data.get('Subject')
		list_id = data.get('ListID')
		
		if not clone_from_id or not new_name:
			return {"error": "CloneCampaignID and CampaignName are required"}, 400
		
		# 1. Buscar a campanha original
		get_payload = {
			"APIKey": app.config["FLOWBIZ_API_KEY_Voxcall"],
			"Command": "Campaign.Get",
			"CampaignID": clone_from_id,
			"ResponseFormat": "JSON"
		}
		
		try:
			get_res = requests.post(app.config["FLOWBIZ_ENDPOINT"], data=get_payload, timeout=20)
			original_data = get_res.json()
			
			# 2. Criar nova campanha baseada na original
			create_payload = {
				"APIKey": app.config["FLOWBIZ_API_KEY_Voxcall"],
				"Command": "Campaign.Create",
				"CampaignName": new_name,
				"Subject": new_subject or original_data.get('Subject'),
				"ListID": list_id or original_data.get('ListID'),
				"ResponseFormat": "JSON"
			}
			
			if original_data.get('FromEmail'):
				create_payload['FromEmail'] = original_data.get('FromEmail')
			
			create_res = requests.post(app.config["FLOWBIZ_ENDPOINT"], data=create_payload, timeout=20)
			return create_res.json(), create_res.status_code
		except Exception as e:
			return {"error": str(e)}, 502

	# Serve index.html na raiz
	@app.route("/")
	def serve_index():
		from flask import send_from_directory
		return send_from_directory(os.path.dirname(__file__), "templates/campanhas.html")
	
	@app.route("/campanhas")
	def serve_campanhas():
		from flask import send_from_directory
		return send_from_directory(os.path.dirname(__file__), "templates/campanhas.html")
	
	@app.route("/dashboard")
	def serve_dashboard():
		from flask import send_from_directory
		return send_from_directory(os.path.dirname(__file__), "templates/dashboard.html")
	
	
	@app.route("/static/<path:filename>")
	def serve_static(filename):
		from flask import send_from_directory
		return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), filename)

	# Inicializar Dash (opcional). Se o módulo não existir ou houver erro, apenas logar e continuar.
	try:
		from dashboard_app import init_dash
		init_dash(app)
	except Exception as e:
		app.logger.warning(f"Dash não inicializado: {e}")
		msg = str(e)
		# Rota fallback amigável para informar que o Dash não está disponível
		@app.route("/dash")
		def _dash_redirect():
			from flask import redirect
			# Redireciona para a versão com barra
			return redirect("/dash/")

		@app.route("/dash/")
		def _dash_unavailable():
			return (
				"<h3>Dash não inicializado</h3>"
				f"<p>Motivo: {msg}</p>"
				"<p>Instale as dependências: <code>pip install dash plotly dash-bootstrap-components pandas</code></p>"
				"<p>Após, reinicie a aplicação e abra <a href='/dash/'>/dash/</a>.</p>"
			), 200

		@app.route('/dash/status')
		def _dash_status():
			return {"status": "dash-unavailable", "reason": msg}, 200

	return app


app = create_app()

if __name__ == "__main__":
	app.run(debug=True, host="0.0.0.0", port=5001)
