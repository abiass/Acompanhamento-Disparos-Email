```md
# 📧 API Flowbiz – Documentação de Integração

## 📌 Visão Geral

A **API Flowbiz** permite conectar seus sistemas ao ecossistema de marketing da plataforma, possibilitando automações, integração de dados e criação de fluxos inteligentes entre aplicações como:

- CRM  
- ERP  
- E-commerce  
- Chatbots  
- Sistemas internos  
- Formulários externos  

### O que você pode fazer com a API

Através da API Flowbiz, você pode gerenciar programaticamente:

- **Contatos** – Criar, atualizar e consultar clientes  
- **Listas** – Agrupar contatos para campanhas  
- **Campanhas** – Criar e acompanhar envios de e-mail  
- **Segmentos** – Criar públicos dinâmicos  
- **Campos personalizados** – Enriquecer perfis de contatos  
- **Arquivos (Media)** – Importar ou enviar dados em lote  
- **Tags** – Classificar contatos e campanhas  

### Exemplos práticos de uso

Você pode usar a API para:

- Inserir leads automaticamente vindos de formulários externos  
- Sincronizar dados entre sistemas sem planilhas manuais  
- Disparar campanhas baseadas em eventos de outros sistemas  
- Integrar Flowbiz com seu próprio software  

---

## ⚙️ Como funciona a API

### Métodos HTTP suportados

A API utiliza padrões REST básicos:

| Método | Uso |
|--------|-----|
| **GET** | Consultar dados |
| **POST** | Criar ou atualizar dados |

### Formato de resposta

Todas as respostas são retornadas em **JSON**.

---

## 🔑 Autenticação

### Chave de API

Para usar a API, você precisa de uma **Chave de API (APIKey)**.

### Como obter sua chave

No painel Flowbiz:

👉 Clique em:

```

[Nome do Usuário] → Chaves da API

```

E gere sua chave.

### Como autenticar nas requisições

Em todas as chamadas, envie o parâmetro:

```

APIKey = SUA_CHAVE_AQUI

```

### Segurança

- Sempre utilize **HTTPS** em produção 🔒  
- Nunca compartilhe sua chave de API publicamente  

---

## 🧠 Conceitos básicos

### Contato

Um **Contato** é um registro dentro de uma lista.

- Campo obrigatório mínimo: **E-mail**
- Pode conter campos personalizados adicionais  

### Campo personalizado

São informações extras criadas dentro de uma lista, como:

- Nome  
- Telefone  
- Cidade  
- Origem do lead  
- Produto interesse  

### Usuário

É o cliente contratante da Flowbiz.

### Lista

Local onde ficam armazenados os contatos.

Exemplos padrão:

- Clientes  
- Assinantes  

### Segmento

Filtro dinâmico dentro de uma lista baseado em regras definidas pelo usuário.

### Campanha

Ação de marketing por e-mail enviada para uma ou mais listas ou segmentos.

---

## 🚧 Importante sobre Endpoints

Os **endpoints podem variar por cliente**.

Exemplos de endpoints possíveis:

```

[https://mbiz.mailclick.me/api.php](https://mbiz.mailclick.me/api.php)
[https://news.mailclick.me/api.php](https://news.mailclick.me/api.php)

```

Para testes no ReadMe, use:

```

[https://mbiz.mailclick.me/api.php](https://mbiz.mailclick.me/api.php)

```

---

# 📑 Endpoints da API

## 👥 Contatos (Subscribers)

> OBS: Para cadastrar novos contatos, use **Subscriber.Subscribe** quando o opt-in for *simples*.

### Disponíveis:

- Subscriber.Get  
- Subscriber.Subscribe  
- Subscriber.Optin  
- Subscriber.Unsubscribe  
- Subscriber.Update  
- Subscriber.Login  
- Subscriber.GetLists  
- Subscribers.Delete  
- Subscribers.Get  
- Subscribers.Import  
- Subscriber.Interactions  
- Subscriber.GetOptOut  

---

## 📁 Arquivos (Media)

- Media.Upload  
- Media.Retrieve  
- Media.Browse  

---

## 📢 Campanhas

- Campaign.Get  
- Campaign.Create  
- Campaign.Update  
- Campaigns.Get  
- Campaigns.Delete  
- Campaigns.Archive.GetURL  

---

## 🏷️ Campos Personalizados

- CustomField.Create  
- CustomField.Update  
- CustomFields.Copy  
- CustomFields.Delete  
- CustomFields.Get  

---

## 🤖 Envios Automáticos (AutoResponder)

- AutoResponder.Create  
- AutoResponder.Update  
- AutoResponder.Get  
- AutoResponder.Delete  
- AutoResponder.Webhook  
- AutoResponder.Sequences  

---

## 📋 Listas

- List.Create  
- List.Update  
- Lists.Get  
- List.Get  
- Lists.Delete  

---

## 🎯 Segmentos

- Segment.Create  
- Segment.Update  
- Segment.Get  
- Segments.Delete  
- Segments.Copy  

---

## 🏷️ Tags

- Tag.Create  
- Tags.Get  
- Tag.Update  
- Tags.Delete  
- Tag.AssignToCampaigns  
- Tag.UnassignFromCampaigns  

---

## ✅ Próximos Passos

Para integrar com sua aplicação:

1. Gere sua **APIKey**
2. Escolha o **Endpoint correto**
3. Teste via Postman ou Insomnia  
4. Implemente no seu código  


- criar exemplos em **Python**
- montar um **client pronto em JavaScript**
- ou gerar um **arquivo OpenAPI (Swagger)** 🚀
```
