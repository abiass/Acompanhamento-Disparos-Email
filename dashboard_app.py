import os
import requests
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, callback_context
from dash import dash_table
import dash_bootstrap_components as dbc


def init_dash(flask_app):
    """Inicializa um app Dash montado no Flask `flask_app`.
    Busca campanhas diretamente da API Flowbiz (não passa pelo Flask para evitar deadlocks).
    """
    server = flask_app
    prefix = "/dash/"

    external_stylesheets = [dbc.themes.BOOTSTRAP]
    # Montar Dash em sub-path /dash/ — garantir requests_pathname_prefix para roteamento correto
    app = Dash(
        __name__,
        server=server,
        routes_pathname_prefix=prefix,
        requests_pathname_prefix=prefix,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
    )
    server.logger.info("Dash inicializado (prefix: %s)", prefix)

    def fetch_campaigns_from_flowbiz():
        """Busca campanhas diretamente da API Flowbiz (mesma lógica do app.py)"""
        try:
            flowbiz_endpoint = os.getenv("FLOWBIZ_ENDPOINT", "https://mbiz.mailclick.me/api.php")
            api_keys = {k: v for k, v in os.environ.items() if k.startswith("FLOWBIZ_API_KEY_") and v}
            
            if not api_keys:
                server.logger.warning("fetch_campaigns_from_flowbiz: nenhuma API key encontrada")
                return []
            
            merged = []
            timeout = 20
            per_page = 100  # buscar menos para ser mais rápido
            
            failed_accounts = []
            for name, key in api_keys.items():
                local_payload = {
                    "APIKey": key.strip().strip('"'),
                    "Command": "Campaigns.Get",
                    "RecordsPerRequest": str(per_page),
                    "ResponseFormat": "JSON"
                }
                attempt = 0
                max_attempts = 3
                backoff = 1
                last_exc = None
                while attempt < max_attempts:
                    attempt += 1
                    try:
                        server.logger.debug("Fetching campaigns for %s attempt %d", name, attempt)
                        res = requests.post(flowbiz_endpoint, data=local_payload, timeout=timeout)
                        if res.status_code != 200:
                            server.logger.warning("Account %s returned status %s", name, res.status_code)
                            last_exc = Exception(f"HTTP {res.status_code}")
                            raise last_exc
                        d = res.json()
                        campaigns = d.get("Campaigns") if isinstance(d, dict) else None
                        if campaigns:
                            for c in campaigns:
                                c["_origin_api"] = name
                                try:
                                    c["Origin"] = name.replace('FLOWBIZ_API_KEY_', '')
                                except Exception:
                                    c["Origin"] = name
                                merged.append(c)
                        last_exc = None
                        break
                    except requests.exceptions.ReadTimeout as rte:
                        server.logger.warning("Timeout fetching campaigns for %s (attempt %d): %s", name, attempt, rte)
                        last_exc = rte
                    except requests.exceptions.ConnectionError as ce:
                        server.logger.warning("Connection error for %s (attempt %d): %s", name, attempt, ce)
                        last_exc = ce
                    except Exception as e:
                        server.logger.exception("Erro buscando campanhas de %s (attempt %d): %s", name, attempt, e)
                        last_exc = e
                    # Exponential backoff before retrying
                    if attempt < max_attempts:
                        import time
                        time.sleep(backoff)
                        backoff *= 2
                if last_exc is not None:
                    failed_accounts.append({"account": name, "error": str(last_exc)})
            if failed_accounts:
                server.logger.warning("Algumas contas falharam ao buscar campanhas: %s", failed_accounts)
            
            server.logger.debug("fetch_campaigns_from_flowbiz: retornou %d campanhas", len(merged))
            return merged
        except Exception as e:
            server.logger.exception("Erro em fetch_campaigns_from_flowbiz: %s", e)
            return []

    def fetch_campaigns():
        """Wrapper que usa a função de busca direta"""
        return fetch_campaigns_from_flowbiz()

    def campaigns_to_df(campaigns: list):
        if not campaigns:
            return pd.DataFrame()

        # Normalizar e agregar métricas que podem vir em formatos diferentes
        normalized = []
        for c in campaigns:
            item = dict(c)  # copiar para não alterar original
            # EmailsSent
            try:
                item['EmailsSent'] = int(item.get('TotalSent') or item.get('EmailsSent') or 0)
            except Exception:
                item['EmailsSent'] = 0
            # UniqueClicks: priorizar 'UniqueClicks' quando disponível; caso contrário derivar de ClickStatistics/Clicks
            try:
                if item.get('UniqueClicks') is not None:
                    item['UniqueClicks'] = int(item.get('UniqueClicks') or 0)
                else:
                    unique_clicks = 0
                    cs = item.get('ClickStatistics') or item.get('ClickStats') or item.get('Clicks')
                    if isinstance(cs, dict):
                        for v in cs.values():
                            if isinstance(v, dict):
                                unique_clicks += int(v.get('Unique', v.get('Total', 0) or 0) or 0)
                            else:
                                try:
                                    unique_clicks += int(v or 0)
                                except Exception:
                                    pass
                    elif isinstance(cs, list):
                        for it in cs:
                            if isinstance(it, dict):
                                unique_clicks += int(it.get('Unique', it.get('Total', it.get('Clicks', 0) or 0) or 0) or 0)
                    item['UniqueClicks'] = int(unique_clicks)
            except Exception:
                item['UniqueClicks'] = 0

            # Manter TotalClicks para compatibilidade, mas usar UniqueClicks como fallback
            try:
                if item.get('TotalClicks') is None:
                    item['TotalClicks'] = int(item.get('UniqueClicks', 0) or 0)
                else:
                    item['TotalClicks'] = int(item.get('TotalClicks') or 0)
            except Exception:
                item['TotalClicks'] = int(item.get('UniqueClicks', 0) or 0)
            # TotalOpens: similar a opens
            if not item.get('TotalOpens'):
                total_opens = 0
                osd = item.get('OpenStatistics') or item.get('OpenStats') or item.get('Opens')
                if isinstance(osd, dict):
                    for v in osd.values():
                        if isinstance(v, dict):
                            total_opens += int(v.get('Unique', v.get('Total', 0) or 0) or 0)
                        else:
                            try:
                                total_opens += int(v or 0)
                            except Exception:
                                pass
                try:
                    item['TotalOpens'] = int(total_opens)
                except Exception:
                    item['TotalOpens'] = 0
            else:
                try:
                    item['TotalOpens'] = int(item.get('TotalOpens') or 0)
                except Exception:
                    item['TotalOpens'] = 0

            # Garantir campos de leads e acessos
            try:
                item['QtdLeads'] = int(item.get('QtdLeads', 0) or 0)
            except Exception:
                item['QtdLeads'] = 0
            try:
                item['QtdAcessos'] = int(item.get('QtdAcessos', 0) or 0)
            except Exception:
                item['QtdAcessos'] = 0

            normalized.append(item)

        df = pd.DataFrame(normalized)

        # Tentar parse de datas
        for date_field in ["SendProcessFinishedOn", "SendDate", "CreateDateTime"]:
            if date_field in df.columns:
                try:
                    df[date_field] = pd.to_datetime(df[date_field], errors="coerce", dayfirst=True)
                except Exception:
                    df[date_field] = pd.NaT
        # Escolher data representativa
        date_cols = [c for c in ["SendProcessFinishedOn", "SendDate", "CreateDateTime"] if c in df.columns]
        if date_cols:
            df["send_date"] = df[date_cols].bfill(axis=1).iloc[:, 0]
        else:
            df["send_date"] = pd.NaT

        # Nome
        df["CampaignName"] = df.get("CampaignName")
        # Garantir tipos
        df["EmailsSent"] = pd.to_numeric(df.get("EmailsSent", 0), errors="coerce").fillna(0).astype(int)
        df["TotalOpens"] = pd.to_numeric(df.get("TotalOpens", 0), errors="coerce").fillna(0).astype(int)
        df["TotalClicks"] = pd.to_numeric(df.get("TotalClicks", 0), errors="coerce").fillna(0).astype(int)
        df["UniqueClicks"] = pd.to_numeric(df.get("UniqueClicks", 0), errors="coerce").fillna(0).astype(int)
        return df

    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col(html.H3("Painel de Métricas de E-mails"), md=8),
            dbc.Col([
                html.Div("Inicializando...", id="dash-status", style={"textAlign": "right", "paddingTop": "6px", "fontSize": "0.9rem", "color": "#4B5563"})
            ], md=4),
        ], align="center", className="my-2"),

        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Filtros", className="card-title"),
                    dcc.Dropdown(id="origin-filter", placeholder="Filtrar por origem (conta)", multi=False),
                    dcc.Dropdown(id="campaign-filter", placeholder="Filtrar por nome da campanha", multi=True, options=[]),
                    dcc.DatePickerRange(id="date-range"),
                    html.Div(dbc.Button("Filtrar", id="apply-filters", color="primary", className="mt-2"), style={"marginTop": "8px"}),
                    dcc.Location(id='url', refresh=False)
                ])
            ]), md=3),

            dbc.Col(dcc.Loading(
                dbc.Card(dbc.CardBody(dcc.Graph(id="bar-emails-sent"))),
                id='loading-bar', type='circle', fullscreen=False
            ), md=9)
        ], className="my-2"),

        dbc.Row([
            dbc.Col(dcc.Loading(dbc.Card(dbc.CardBody(dcc.Graph(id="pie-opens-clicks"))), id='loading-pie', type='circle'), md=6),
            dbc.Col(dcc.Loading(dbc.Card(dbc.CardBody(dcc.Graph(id="time-opens"))), id='loading-time', type='circle'), md=6),
        ], className="my-2"),

        dbc.Row([
            dbc.Col(dcc.Loading(
                dbc.Card(dbc.CardBody([
                    html.H5("Campanhas"),
                    dash_table.DataTable(
                        id="table-campaigns",
                        columns=[
                            {"name": "Campanha", "id": "CampaignName"},
                            {"name": "Origem", "id": "Origin"},
                            {"name": "E-mails enviados", "id": "EmailsSent", "type": "numeric"},
                            {"name": "Aberturas", "id": "TotalOpens", "type": "numeric"},
                            {"name": "Cliques (únicos)", "id": "UniqueClicks", "type": "numeric"},
                            {"name": "Leads", "id": "QtdLeads", "type": "numeric"},
                            {"name": "Acessos", "id": "QtdAcessos", "type": "numeric"},
                        ],
                        page_size=10,
                        sort_action="native",
                        filter_action="native",
                        style_table={"overflowX": "auto"}
                    )
                ])), id='loading-table', type='dot'), md=12)
        ], className="my-2")

    ], fluid=True)


    from dash import State

    @app.callback(
        Output("origin-filter", "options"),
        Output("origin-filter", "value"),
        Output("campaign-filter", "options"),
        Output("campaign-filter", "value"),
        Input("url", "pathname"),
        Input("apply-filters", "n_clicks"),
        State("origin-filter", "value"),
        State("campaign-filter", "value")
    )
    def update_origins(pathname, n_clicks, current_origin_value, current_campaign_value):
        try:
            campaigns = fetch_campaigns()
            df = campaigns_to_df(campaigns)
            if df.empty:
                return [], None, [], current_campaign_value if current_campaign_value else None
            origin_values = sorted(df.get("Origin", df.get("_origin_api", [])).dropna().unique())
            origin_opts = [{"label": o, "value": o} for o in origin_values]
            # Campaign options for dropdown (unique campaign names)
            names = sorted(df.get("CampaignName", pd.Series(dtype=str)).dropna().unique())
            campaign_opts = [{"label": str(n), "value": str(n)} for n in names]
            # Preserve previous selections when still available
            origin_value = current_origin_value if (current_origin_value in origin_values) else None
            # campaign value can be list or single
            if not current_campaign_value:
                campaign_value = None
            else:
                # normalize to list
                if isinstance(current_campaign_value, (list, tuple)):
                    campaign_value = [str(v) for v in current_campaign_value if str(v) in names]
                    if not campaign_value:
                        campaign_value = None
                else:
                    campaign_value = str(current_campaign_value) if str(current_campaign_value) in names else None
            return origin_opts, origin_value, campaign_opts, campaign_value
        except Exception as exc:
            # Log the exception and return safe defaults so the callback doesn't fail
            server.logger.exception("Erro em update_origins: %s", exc)
            return [], current_origin_value, [], current_campaign_value


    @app.callback(
        Output("bar-emails-sent", "figure"),
        Output("pie-opens-clicks", "figure"),
        Output("time-opens", "figure"),
        Output("table-campaigns", "data"),
        Output("dash-status", "children"),
        Input("url", "pathname"),
        Input("apply-filters", "n_clicks"),
        State("origin-filter", "value"),
        State("campaign-filter", "value"),
        State("date-range", "start_date"),
        State("date-range", "end_date")
    )
    def update_metrics(pathname, n_clicks, origin, campaign_names, start_date, end_date):
        # Determine trigger (page load or button) for better status messaging
        trigger = callback_context.triggered[0]['prop_id'] if callback_context.triggered else ''
        applying = 'apply-filters' in trigger
        if applying:
            server.logger.info('Aplicando filtros (botão)')
        else:
            server.logger.debug('Atualizando métricas (carregamento de página)')
        try:
            campaigns = fetch_campaigns()
            df = campaigns_to_df(campaigns)
            now = datetime.now().strftime('%H:%M:%S')
            if df.empty:
                # figuras com anotação "nenhum dado" para o usuário ver a situação
                empty_fig = px.scatter()
                empty_fig.update_layout(
                    annotations=[{
                        'text': 'Nenhuma campanha encontrada.<br>Verifique se o servidor está rodando e se há dados disponíveis.',
                        'xref': 'paper', 'yref': 'paper', 'showarrow': False,
                        'font': {'size': 14}
                    }],
                    xaxis={'visible': False},
                    yaxis={'visible': False}
                )
                server.logger.info("update_metrics: sem campanhas para mostrar")
                status_msg = f"⚠️ {now} — 0 campanhas encontradas"
                return empty_fig, empty_fig, empty_fig, [], status_msg

            # If called by button, add an informational status while processing
            if applying:
                working_status = 'Aplicando filtros...'
            else:
                working_status = 'Atualizando métricas...'

            # Filtrar por origem
            if origin:
                df = df[df.get("Origin") == origin]
            # Filtrar por nome da campanha
            if campaign_names:
                # Se for lista (multi-select), filtrar por correspondência exata nas opções selecionadas
                if isinstance(campaign_names, (list, tuple)):
                    df = df[df.get("CampaignName").isin([str(x) for x in campaign_names])]
                else:
                    # Compatibilidade: aceitar string como fallback (contains)
                    q = str(campaign_names).strip()
                    if q:
                        df = df[df.get("CampaignName", "").str.contains(q, case=False, na=False)]
            # Filtrar por intervalo de datas (aplicar somente se send_date estiver disponível)
            if "send_date" in df.columns and not df["send_date"].isna().all():
                if start_date:
                    df = df[df["send_date"] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df["send_date"] <= pd.to_datetime(end_date)]
            else:
                if start_date or end_date:
                    server.logger.warning("Filtro de data ignorado: 'send_date' ausente nos dados")
            # Bar: top 15 por EmailsSent
            top = df.sort_values("EmailsSent", ascending=False).head(15)
            top_plot = top.copy()
            top_plot['Aberturas'] = top_plot['TotalOpens']
            top_plot['Cliques (únicos)'] = top_plot['UniqueClicks']
            fig_bar = px.bar(top_plot, x="CampaignName", y="EmailsSent", hover_data=["Aberturas", "Cliques (únicos)"], title="E-mails enviados por campanha")
            fig_bar.update_layout(xaxis_tickangle=-45)
            # Pizza: Aberturas vs Cliques (únicos)
            total_opens = int(df["TotalOpens"].sum())
            total_clicks = int(df["UniqueClicks"].sum())
            fig_pie = px.pie(names=["Aberturas", "Cliques (únicos)"], values=[total_opens, total_clicks], title="Aberturas vs Cliques (únicos) — total")
            # Top de cliques: ordenar campanhas por Cliques (únicos) (do maior para o menor)
            try:
                clicks_top = df.sort_values("UniqueClicks", ascending=False).head(15)
                if clicks_top.empty:
                    fig_time = px.scatter()
                    fig_time.update_layout(
                        annotations=[{
                            'text': 'Nenhum dado de cliques disponível para as campanhas filtradas',
                            'xref': 'paper', 'yref': 'paper', 'showarrow': False,
                            'font': {'size': 14}
                        }],
                        xaxis={'visible': False},
                        yaxis={'visible': False}
                    )
                else:
                    clicks_plot = clicks_top.copy()
                    clicks_plot['Cliques (únicos)'] = clicks_plot['UniqueClicks']
                    fig_time = px.bar(clicks_plot, x='Cliques (únicos)', y='CampaignName', orientation='h', title='Top campanhas por Cliques (únicos)', text='Cliques (únicos)')
                    fig_time.update_layout(yaxis={'autorange':'reversed'}, xaxis_title='Cliques (únicos)', yaxis_title='Campanha')
            except Exception as ee:
                server.logger.exception('Erro ao gerar top de cliques: %s', ee)
                fig_time = px.scatter()
                fig_time.update_layout(
                    annotations=[{
                        'text': 'Erro ao gerar relatório de top de cliques',
                        'xref': 'paper', 'yref': 'paper', 'showarrow': False,
                        'font': {'size': 12, 'color': 'red'}
                    }]
                )
            # Table data
            table_data = df.sort_values("send_date", ascending=False).fillna("-").to_dict("records")
            now = datetime.now().strftime('%H:%M:%S')
            status_msg = f"✓ {now} — {len(df)} campanhas"
            return fig_bar, fig_pie, fig_time, table_data, status_msg
        except Exception as exc:
            server.logger.exception("Erro em update_metrics: %s", exc)
            empty_fig = px.scatter()
            empty_fig.update_layout(
                annotations=[{
                    'text': f'Erro ao carregar dados:<br>{str(exc)[:100]}',
                    'xref': 'paper', 'yref': 'paper', 'showarrow': False,
                    'font': {'size': 12, 'color': 'red'}
                }],
                xaxis={'visible': False},
                yaxis={'visible': False}
            )
            # retornar figuras vazias e dados vazios para evitar "Callback failed"
            now = datetime.now().strftime('%H:%M:%S')
            status_msg = f"❌ {now} — Erro: {str(exc)[:80]}"
            return empty_fig, empty_fig, empty_fig, [], status_msg

    # Expor uma rota simples informando que o Dash está ativo
    @server.route(prefix.rstrip('/'))
    def _dash_index():
        return "Painel disponível em <a href='{}'>{}</a>".format(prefix, prefix)

    # Rota de diagnóstico: quantas campanhas o Dash enxerga agora
    from flask import jsonify
    @server.route(prefix + 'metrics')
    def _dash_metrics():
        try:
            campaigns = fetch_campaigns_from_flowbiz()
            # Tentar obter informações sobre contas que falharam (se houver registro nos logs, retornará só count)
            return jsonify({"count": len(campaigns), "status": "ok"}), 200
        except Exception as exc:
            server.logger.exception("Erro em /dash/metrics: %s", exc)
            return jsonify({"count": 0, "error": str(exc), "status": "exception"}), 500

    return app
