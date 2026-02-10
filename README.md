# API Email FlowBiz

Sistema de gerenciamento de campanhas de email marketing integrado com FlowBiz e banco de dados PostgreSQL. Interface web para visualizar campanhas com métricas em tempo real (Qtd Leads e Qtd Acessos).

##  Segurança

Este projeto está configurado para não vazar dados sensíveis no GitHub. As seguintes informações **nunca** são commitadas:

- Credenciais do banco de dados (`.env`)
- Chaves de API (`FLOWBIZ_API_KEY_*`)
- Mapeamento de campanhas com dados reais (`flowbiz_campaign_mapping.json`)
- Arquivos de cache e temporários

##  Pré-requisitos

- Python 3.8+
- PostgreSQL 12+
- pip (gerenciador de pacotes Python)

## Instalação

### 1. Clonar o repositório

```bash
git clone <seu-repo-url>
cd API_EMAIL_FLOWBIZ
```

### 2. Criar variáveis de ambiente

Copie o arquivo de exemplo e configure com seus dados reais:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```env
# Flowbiz API
FLOWBIZ_ENDPOINT=https://mbiz.mailclick.me/api.php
FLOWBIZ_API_KEY_Voxcall=SEU_APIKEY_AQUI

# Banco de dados
DB_HOST=seu_host_db
DB_PORT=5432
DB_NAME=seu_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
```

### 3. Criar mapeamento de campanhas

Copie o arquivo de exemplo:

```bash
cp flowbiz_campaign_mapping.example.json flowbiz_campaign_mapping.json
```

Edite `flowbiz_campaign_mapping.json` e adicione seus mapeamentos:

```json
{
  "flowbiz_campaign_mappings": [
    {
      "flowbiz_campaign_id": "123456",
      "db_campanha_id": "00000000-0000-0000-0000-000000000000"
    }
  ]
}
```

**Nota**: O `flowbiz_campaign_mapping.json` está no `.gitignore` e não será enviado ao GitHub.

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

Se o arquivo `requirements.txt` não existir, instale manualmente:

```bash
pip install Flask requests python-dotenv psycopg2-binary openpyxl
```

### 5. Executar a aplicação

```bash
python app.py
```

A aplicação estará disponível em: `http://localhost:5001`

##  Funcionalidades

- **Listagem de Campanhas**: Visualize todas as campanhas com suas métricas
- **Métricas em Tempo Real**:
  - Total de emails enviados
  - Taxa de aberturas
  - Taxa de cliques únicos
  - **Qtd Leads**: Quantidade de formulários preenchidos
  - **Qtd Acessos**: Quantidade de acessos registrados
- **Paginação**: Navegação através de múltiplas páginas de campanhas
- **Responsivo**: Interface otimizada para diferentes tamanhos de tela

##  Banco de Dados

O projeto espera as seguintes tabelas no PostgreSQL (schema `autobot`):

```sql
-- Campanhas
CREATE TABLE autobot.campanhas (
  id UUID PRIMARY KEY,
  nome VARCHAR(255),
  -- ... outros campos
);

-- Acessos
CREATE TABLE autobot.campanha_acessos (
  id SERIAL PRIMARY KEY,
  campanha_id UUID REFERENCES autobot.campanhas(id),
  -- ... outros campos
);

-- Leads/Formulários
CREATE TABLE autobot.formulario (
  id SERIAL PRIMARY KEY,
  campanha_id UUID REFERENCES autobot.campanhas(id),
  -- ... outros campos
);
```

##  Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `FLOWBIZ_ENDPOINT` | URL da API FlowBiz | `https://mbiz.mailclick.me/api.php` |
| `FLOWBIZ_API_KEY_Voxcall` | Chave de API do FlowBiz | `sua_chave_aqui` |
| `DB_HOST` | Host do PostgreSQL | `localhost` |
| `DB_PORT` | Porta do PostgreSQL | `5432` |
| `DB_NAME` | Nome do banco de dados | `seu_banco` |
| `DB_USER` | Usuário do banco | `seu_usuario` |
| `DB_PASSWORD` | Senha do banco | `sua_senha` |

##  Estrutura do Projeto

```
API_EMAIL_FLOWBIZ/
├── app.py                           # Aplicação Flask principal
├── .env.example                     # Exemplo de configuração
├── flowbiz_campaign_mapping.example.json  # Exemplo de mapeamento
├── .gitignore                       # Arquivos ignorados no Git
├── requirements.txt                 # Dependências Python
├── templates/
│   └── campanhas.html              # Interface de campanhas
├── static/
│   └── navbar.html                 # Navbar compartilhada
└── README.md                        # Este arquivo
```

## 🛠️ Desenvolvimento

### Executar em modo debug

```bash
export FLASK_DEBUG=1  # Linux/Mac
set FLASK_DEBUG=1     # Windows
python app.py
```

### Verificar logs

A aplicação exibe logs no console. Erros de banco de dados e requisições à API FlowBiz são registrados.

##  Boas Práticas de Segurança

1. **Nunca** commitar arquivos `.env` com credenciais reais
2. **Nunca** commitar `flowbiz_campaign_mapping.json` com IDs reais
3. Use `.env.example` como template para setup local
4. Revise o `.gitignore` regularmente
5. Mantenha as dependências atualizadas
6. Use variáveis de ambiente para todas as credenciais

##  Antes de fazer Push no GitHub

Execute esta checklist:

- [ ] `.env` está no `.gitignore` e não foi commitado
- [ ] `flowbiz_campaign_mapping.json` está no `.gitignore` e não foi commitado
- [ ] Não há chaves de API no código-fonte
- [ ] Não há credenciais de banco em comentários
- [ ] Executou `git status` para verificar arquivos pendentes

Para verificar se há arquivos sensíveis já no repositório:

```bash
git log --all --sources -- .env
git log --all --sources -- flowbiz_campaign_mapping.json
```

##  Licença

[Adicione sua licença aqui]

##  Contribuindo

1. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
2. Commit suas mudanças: `git commit -am 'Adiciona minha feature'`
3. Push para a branch: `git push origin feature/minha-feature`
4. Abra um Pull Request

##  Suporte

Para problemas ou dúvidas, abra uma issue no repositório.
