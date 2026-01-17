# JogaJunto Listing Generator

Script para gerar uma listagem em TXT de usuários e dos jogos que os mesmos irão trazer, a partir dos dados do DynamoDB.

## Instalação

### Método rápido (recomendado)

Use o script de setup automático:

```bash
./setup.sh
```

Isso criará o ambiente virtual e instalará todas as dependências automaticamente.

### Método manual

Para sistemas com Python gerenciado externamente (Debian/Ubuntu), é necessário criar um ambiente virtual:

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Instalação direta (não recomendado)

Se preferir instalar diretamente no sistema (pode causar conflitos):

```bash
pip install -r requirements.txt --break-system-packages
```

**Nota**: Sempre ative o ambiente virtual antes de executar o script:
```bash
source venv/bin/activate
python generate_listing.py
```

## Configuração

### Arquivo .env (recomendado)

Crie um arquivo `.env` na raiz do projeto com suas configurações:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e configure suas credenciais:

```env
# AWS Credentials
AWS_ACCESS_KEY_ID=sua-access-key-id
AWS_SECRET_ACCESS_KEY=sua-secret-access-key
AWS_REGION=us-east-1

# DynamoDB Configuration
DYNAMODB_TABLE=JogaJuntoRegistrations

# Output Configuration
GAMES_LISTING_FILE=games_listing.txt
GAMERS_FILE=gamers.txt
CSV_FILE=registrations.csv
```

**Importante**: O arquivo `.env` está no `.gitignore` e não será commitado. Nunca compartilhe suas credenciais!

### Outras formas de configurar credenciais AWS

Se preferir não usar o arquivo `.env`, você pode configurar as credenciais de outras formas:

1. **Variáveis de ambiente do sistema:**
```bash
export AWS_ACCESS_KEY_ID="sua-access-key"
export AWS_SECRET_ACCESS_KEY="sua-secret-key"
export AWS_REGION="us-east-1"
```

2. **Arquivo de credenciais AWS CLI** (`~/.aws/credentials`):
```ini
[default]
aws_access_key_id = sua-access-key
aws_secret_access_key = sua-secret-key
```

3. **IAM Role** (se executando em EC2/Lambda)

### Valores padrão

Se não configurados, os valores padrão são:
- Table name: `JogaJuntoRegistrations`
- AWS Region: `us-east-1`
- Games listing file: `games_listing.txt`
- Gamers file: `gamers.txt`
- CSV file: `registrations.csv`

## Uso

### Método rápido

Use o script de execução que ativa automaticamente o ambiente virtual:

```bash
./run.sh
```

### Método manual

Certifique-se de que o ambiente virtual está ativado (se estiver usando um):

```bash
# Se estiver usando ambiente virtual, ative primeiro
source venv/bin/activate

# Executar o script
python generate_listing.py
```

O script irá:
1. Conectar ao DynamoDB
2. Buscar dados da tabela `JogaJuntoRegistrations`
3. Processar e agrupar jogos por usuário
4. Gerar três arquivos:
   - `games_listing.txt`: Lista de jogos numerados por usuário
   - `gamers.txt`: Lista de participantes em ordem alfabética
   - `registrations.csv`: Exportação completa dos dados do DynamoDB em formato CSV

## Arquivos Gerados

### games_listing.txt

Lista de jogos numerados por usuário:

```
- Usuário A
   1) Carcassonne
   2) Pandemic
   3) Ticket Ride
- Usuário B
   4) Carcassonne
   5) Pandemic
   6) Ticket Ride
- Joga Junto (Jogos da Casa)
   7) Azul
   8) Dixit
   ...
```

Os jogos são numerados sequencialmente em toda a listagem, continuando a numeração entre diferentes usuários. Ao final, são incluídos os jogos fixos da casa.

### gamers.txt

Lista de participantes em ordem alfabética crescente:

```
Fulano de Tal
João Silva
Maria Santos
...
```

### registrations.csv

Arquivo CSV com todos os dados do DynamoDB. Contém todas as colunas dos registros, incluindo:
- id
- nomeCompleto
- email
- celular
- cidade
- dataNascimento
- edicao
- jogos
- possuiJogos
- interesseRPG
- status
- createdAt
- instagram
- protecaoDados
- usoImagem
- E outros campos presentes nos registros

## Notas

O script tenta identificar automaticamente os campos de nome de usuário e jogos. Ele procura por campos comuns como:
- Nome: `name`, `userName`, `user_name`, `nome`, `username`, `Name`, `UserName`
- Jogos: `games`, `jogos`, `gameList`, `game_list`, `gamesToBring`, `game`, `jogo`, `Games`, `Jogos`

O script também lida automaticamente com o formato de atributos do DynamoDB (tipos S, N, L, SS, etc.).

