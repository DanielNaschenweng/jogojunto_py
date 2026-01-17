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
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# ============================================================
# CONSTANTES DO EVENTO - Altere aqui para atualizar as datas
# ============================================================
EVENTO_NOME = "Encontro de Jogos de Tabuleiro - Joga Junto"
EVENTO_DATA = "17 de janeiro de 2026"
EVENTO_LOCAL = "Shopping 13 de Maio"
EVENTO_CIDADE = "Indaiatuba"

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


def generate_attendance_pdf(registrations, output_file='lista_presenca.pdf'):
    """Generate PDF attendance list with participant names in alphabetical order."""
    try:
        participants = []

        for reg in registrations:
            user_name = None
            if 'nomeCompleto' in reg:
                user_name = extract_dynamodb_value(reg['nomeCompleto'])

            if not user_name:
                for field in ['name', 'userName', 'user_name', 'nome', 'username', 'Name', 'UserName']:
                    if field in reg:
                        user_name = extract_dynamodb_value(reg[field])
                        if user_name:
                            break

            if user_name:
                user_name = capitalize_name(str(user_name))
                if user_name not in participants:
                    participants.append(user_name)

        participants.sort()

        doc = SimpleDocTemplate(
            output_file,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        elements = []
        styles = getSampleStyleSheet()

        title = Paragraph("<b>Lista de Presença - Joga Junto</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*cm))

        table_data = [['#', 'Nome', 'Presença']]

        for i, participant in enumerate(participants, 1):
            table_data.append([str(i), participant, ''])

        col_widths = [1.5*cm, 12*cm, 3*cm]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90a4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 1*cm))

        footer = Paragraph(f"<i>Total de participantes: {len(participants)}</i>", styles['Normal'])
        elements.append(footer)

        doc.build(elements)

        print(f"Attendance PDF generated successfully: {output_file}")
        print(f"Total participants: {len(participants)}")
    except Exception as e:
        print(f"Error generating attendance PDF: {e}", file=sys.stderr)
        sys.exit(1)


def generate_termo_pdf(output_file='termo_responsabilidade.pdf', num_linhas=30):
    """Generate PDF with responsibility term and signature lines for on-site registrations."""
    try:
        doc = SimpleDocTemplate(
            output_file,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )

        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=6
        )

        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER,
            spaceAfter=12
        )

        section_style = ParagraphStyle(
            'Section',
            parent=styles['Heading2'],
            fontSize=11,
            spaceBefore=12,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            leading=14
        )

        # Title
        title = Paragraph("<b>Termo de Responsabilidade e Autorização de Uso de Imagem</b>", title_style)
        elements.append(title)

        subtitle = Paragraph(f"<b>Evento:</b> {EVENTO_NOME}", subtitle_style)
        elements.append(subtitle)

        event_info = Paragraph(f"<b>Data:</b> {EVENTO_DATA} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Local:</b> {EVENTO_LOCAL}", subtitle_style)
        elements.append(event_info)

        elements.append(Spacer(1, 0.3*cm))

        # Section 1
        section1 = Paragraph("<b>1. Autorização de Uso de Imagem</b>", section_style)
        elements.append(section1)

        text1 = Paragraph(
            f'Eu autorizo o uso da minha imagem, voz e nome, bem como de quaisquer materiais audiovisuais '
            f'(fotos e vídeos) capturados durante o evento "{EVENTO_NOME}", a ser realizado em {EVENTO_DATA}, '
            f'no {EVENTO_LOCAL}. Esta autorização é concedida para fins de divulgação e promoção do evento e de '
            f'futuras edições, em quaisquer mídias, incluindo, mas não se limitando a, redes sociais, websites, '
            f'materiais impressos e vídeos institucionais, sem qualquer ônus ou compensação financeira.',
            body_style
        )
        elements.append(text1)

        # Section 2
        section2 = Paragraph("<b>2. Responsabilidade pelos Jogos</b>", section_style)
        elements.append(section2)

        text2 = Paragraph(
            f'Declaro que os jogos de tabuleiro trazidos por mim para o evento "{EVENTO_NOME}" são de minha '
            f'inteira responsabilidade. Estou ciente de que a organização do evento não se responsabiliza por '
            f'perdas, danos, furtos ou quaisquer outros incidentes que possam ocorrer com os meus jogos durante '
            f'o período do evento. Comprometo-me a zelar pelos meus pertences e a tomar as precauções necessárias '
            f'para sua segurança.',
            body_style
        )
        elements.append(text2)

        text3 = Paragraph(
            'Assim como concordo com os demais regulamentos do encontro constantes em: '
            '<link href="https://jogajunto.net.br/regulamento/">https://jogajunto.net.br/regulamento/</link>',
            body_style
        )
        elements.append(text3)

        # Section 3
        section3 = Paragraph("<b>3. Declaração e Assinatura</b>", section_style)
        elements.append(section3)

        text4 = Paragraph("Declaro que li e concordo com os termos acima.", body_style)
        elements.append(text4)

        text5 = Paragraph(f"{EVENTO_CIDADE}, {EVENTO_DATA}", body_style)
        elements.append(text5)

        elements.append(Spacer(1, 0.5*cm))

        # Signature table
        table_data = [['#', 'Nome Completo', 'Instagram', 'WhatsApp', 'Assinatura']]

        for i in range(1, num_linhas + 1):
            table_data.append([str(i), '', '', '', ''])

        col_widths = [0.8*cm, 5.5*cm, 3*cm, 3*cm, 4*cm]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90a4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))

        elements.append(table)

        doc.build(elements)

        print(f"Termo PDF generated successfully: {output_file}")
        print(f"Signature lines: {num_linhas}")
    except Exception as e:
        print(f"Error generating termo PDF: {e}", file=sys.stderr)
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

    # Generate attendance PDF
    attendance_pdf = os.getenv('ATTENDANCE_PDF_FILE', 'lista_presenca.pdf')
    print(f"Generating attendance PDF to {attendance_pdf}...")
    generate_attendance_pdf(registrations, attendance_pdf)

    # Generate termo de responsabilidade PDF
    termo_pdf = os.getenv('TERMO_PDF_FILE', 'termo_responsabilidade.pdf')
    num_linhas = int(os.getenv('TERMO_NUM_LINHAS', '30'))
    print(f"Generating termo PDF to {termo_pdf}...")
    generate_termo_pdf(termo_pdf, num_linhas)


if __name__ == '__main__':
    main()

