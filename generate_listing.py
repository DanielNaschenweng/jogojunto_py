#!/usr/bin/env python3
"""
Script to generate a text listing of users and the games they will bring.
Data is fetched from DynamoDB table JogaJuntoRegistrations.
"""

import os
import sys
import re
import csv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_dynamodb_client():
    """Get DynamoDB client from environment variables or default values."""
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    try:
        if aws_access_key_id and aws_secret_access_key:
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=aws_region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        else:
            # Use default credentials (from ~/.aws/credentials or IAM role)
            dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        
        return dynamodb
    except NoCredentialsError:
        print("Error: AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or configure AWS CLI.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error connecting to DynamoDB: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_registrations(dynamodb, table_name='JogaJuntoRegistrations'):
    """Fetch all registrations from JogaJuntoRegistrations table."""
    try:
        table = dynamodb.Table(table_name)
        
        # Scan the entire table
        registrations = []
        response = table.scan()
        registrations.extend(response.get('Items', []))
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            registrations.extend(response.get('Items', []))
        
        return registrations
    except ClientError as e:
        print(f"Error fetching registrations from DynamoDB: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching registrations: {e}", file=sys.stderr)
        sys.exit(1)


def extract_dynamodb_value(value):
    """Extract value from DynamoDB attribute format."""
    if isinstance(value, dict):
        # DynamoDB uses type descriptors like {'S': 'string'}, {'L': [...]}, {'SS': [...]}
        if 'S' in value:  # String
            return value['S']
        elif 'N' in value:  # Number
            return value['N']
        elif 'BOOL' in value:  # Boolean
            return value['BOOL']
        elif 'L' in value:  # List
            return [extract_dynamodb_value(item) for item in value['L']]
        elif 'SS' in value:  # String Set
            return list(value['SS'])
        elif 'NS' in value:  # Number Set
            return list(value['NS'])
        else:
            # Try to get first value if unknown format
            return list(value.values())[0] if value else None
    return value


def capitalize_name(name):
    """Capitalize name: first letter uppercase, rest lowercase."""
    if not name:
        return name
    return name.capitalize()


def process_registrations(registrations):
    """Process registrations and group games by user."""
    user_games = defaultdict(list)
    
    for reg in registrations:
        # Extract user name - prioritize nomeCompleto
        user_name = None
        if 'nomeCompleto' in reg:
            user_name = extract_dynamodb_value(reg['nomeCompleto'])
        
        # If no nomeCompleto found, try other common field names
        if not user_name:
            for field in ['name', 'userName', 'user_name', 'nome', 'username', 'Name', 'UserName']:
                if field in reg:
                    user_name = extract_dynamodb_value(reg[field])
                    if user_name:
                        break
        
        if not user_name:
            continue
        
        # Capitalize user name
        user_name = capitalize_name(str(user_name))
        
        # Extract games from 'jogos' field (string with line breaks, commas, or semicolons)
        games = []
        if 'jogos' in reg:
            games_raw = extract_dynamodb_value(reg['jogos'])
            if isinstance(games_raw, str):
                # Ignore "N/A" and empty values
                games_raw = games_raw.strip()
                if games_raw and games_raw.upper() != 'N/A':
                    # Split by newline, comma, or semicolon - each game on a separate line
                    # Use regex to split by any of these delimiters
                    games = [g.strip() for g in re.split(r'[,\n;]+', games_raw) if g.strip()]
        
        # Only add user if they have valid games
        if games:
            # Add games to user's list (avoid duplicates)
            for game in games:
                game_str = str(game).strip()
                if game_str and game_str not in user_games[user_name]:
                    user_games[user_name].append(game_str)
    
    return user_games


def generate_listing(user_games, output_file='games_listing.txt'):
    """Generate text listing file with numbered games."""
    # Fixed games list to be added at the end
    fixed_games = [
        "Joga Junto",
        "Mind Invaders",
        "Amazoom",
        "Frost Shelter",
        "Pool Party",
        "Azul",
        "Dixit",
        "Scrap Racer",
        "Beaver Creek",
        "Yozu",
        "Café da tarde",
        "Dobrões",
        "Carcasone",
        "Caveiras de Sedlec",
        "Codinames",
        "Bugô",
        "Balde de caranguejo.",
        "Não testamos esse troço/cinético",
        "Lálálá",
        "Sapotagem",
        "Cultive",
        "Exploding Kittens",
        "Revelando Emoções",
        "Dobble",
        "Coup",
        "O Cerco de Runedar",
        "Dogs"
    ]
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            game_counter = 1
            # Sort users alphabetically
            for user_name in sorted(user_games.keys()):
                f.write(f"- {user_name}\n")
                # Sort games alphabetically
                for game in sorted(user_games[user_name]):
                    f.write(f"   {game_counter}) {game}\n")
                    game_counter += 1
                f.write("\n")
            
            # Add fixed games at the end
            if fixed_games:
                f.write("- Joga Junto (Jogos da Casa)\n")
                for game in fixed_games:
                    f.write(f"   {game_counter}) {game}\n")
                    game_counter += 1
                f.write("\n")
        
        print(f"Listing generated successfully: {output_file}")
        print(f"Total users: {len(user_games)}")
        total_games = sum(len(games) for games in user_games.values())
        print(f"Total games: {total_games} (including {len(fixed_games)} fixed games)")
    except Exception as e:
        print(f"Error generating listing file: {e}", file=sys.stderr)
        sys.exit(1)


def generate_gamers_list(registrations, output_file='gamers.txt'):
    """Generate list of participants in ascending order."""
    try:
        participants = []
        
        for reg in registrations:
            # Extract user name - prioritize nomeCompleto
            user_name = None
            if 'nomeCompleto' in reg:
                user_name = extract_dynamodb_value(reg['nomeCompleto'])
            
            # If no nomeCompleto found, try other common field names
            if not user_name:
                for field in ['name', 'userName', 'user_name', 'nome', 'username', 'Name', 'UserName']:
                    if field in reg:
                        user_name = extract_dynamodb_value(reg[field])
                        if user_name:
                            break
            
            if user_name:
                # Capitalize user name
                user_name = capitalize_name(str(user_name))
                if user_name not in participants:
                    participants.append(user_name)
        
        # Sort participants alphabetically
        participants.sort()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for participant in participants:
                f.write(f"{participant}\n")
        
        print(f"Gamers list generated successfully: {output_file}")
        print(f"Total participants: {len(participants)}")
    except Exception as e:
        print(f"Error generating gamers list file: {e}", file=sys.stderr)
        sys.exit(1)


def generate_csv(registrations, output_file='registrations.csv'):
    """Generate CSV file with all DynamoDB data."""
    try:
        if not registrations:
            print("No registrations to export.", file=sys.stderr)
            return
        
        # Get all unique field names from all registrations
        all_fields = set()
        for reg in registrations:
            all_fields.update(reg.keys())
        
        # Sort fields for consistent column order
        # Put common fields first
        common_fields = ['id', 'nomeCompleto', 'email', 'celular', 'cidade', 'dataNascimento', 
                        'edicao', 'jogos', 'possuiJogos', 'interesseRPG', 'status', 
                        'createdAt', 'instagram', 'protecaoDados', 'usoImagem']
        ordered_fields = []
        for field in common_fields:
            if field in all_fields:
                ordered_fields.append(field)
                all_fields.remove(field)
        # Add remaining fields
        ordered_fields.extend(sorted(all_fields))
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fields)
            writer.writeheader()
            
            for reg in registrations:
                row = {}
                for field in ordered_fields:
                    if field in reg:
                        value = extract_dynamodb_value(reg[field])
                        # Convert boolean and other types to string
                        if isinstance(value, bool):
                            row[field] = str(value)
                        elif isinstance(value, list):
                            row[field] = '; '.join(str(v) for v in value)
                        elif value is None:
                            row[field] = ''
                        else:
                            row[field] = str(value)
                    else:
                        row[field] = ''
                writer.writerow(row)
        
        print(f"CSV file generated successfully: {output_file}")
        print(f"Total records: {len(registrations)}")
        print(f"Total columns: {len(ordered_fields)}")
    except Exception as e:
        print(f"Error generating CSV file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function."""
    print("Connecting to DynamoDB...")
    dynamodb = get_dynamodb_client()
    
    table_name = os.getenv('DYNAMODB_TABLE', 'JogaJuntoRegistrations')
    print(f"Fetching registrations from table: {table_name}...")
    registrations = fetch_registrations(dynamodb, table_name)
    print(f"Found {len(registrations)} registration(s)")
    
    print("Processing data...")
    user_games = process_registrations(registrations)
    
    # Generate games listing
    games_listing_file = os.getenv('GAMES_LISTING_FILE', 'games_listing.txt')
    print(f"Generating games listing to {games_listing_file}...")
    generate_listing(user_games, games_listing_file)
    
    # Generate gamers list
    gamers_file = os.getenv('GAMERS_FILE', 'gamers.txt')
    print(f"Generating gamers list to {gamers_file}...")
    generate_gamers_list(registrations, gamers_file)
    
    # Generate CSV
    csv_file = os.getenv('CSV_FILE', 'registrations.csv')
    print(f"Generating CSV to {csv_file}...")
    generate_csv(registrations, csv_file)


if __name__ == '__main__':
    main()

