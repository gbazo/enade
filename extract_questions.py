import re
import json
import os
import pdfplumber

def clean_text(text):
    """
    Limpa o texto removendo espaços extras e caracteres indesejados.
    
    Args:
        text (str): Texto a ser limpo
    
    Returns:
        str: Texto limpo
    """
    if not text:
        return ""
    # Remover números de página
    text = re.sub(r'\d+\s*$', '', text)
    # Remover espaços extras
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_questions_from_pdf(pdf_path):
    """
    Extrai questões de forma mais robusta de um PDF do ENADE.
    
    Args:
        pdf_path (str): Caminho para o arquivo PDF
    
    Returns:
        list: Lista de questões extraídas
    """
    questions = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Texto completo do PDF
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() or ""
            
            # Limpar texto
            full_text = full_text.replace('\n', ' ')
            
            # Padrão para encontrar questões
            # Captura: número da questão, texto da questão, opções
            question_pattern = r'(\d+)\s*(.*?)\s*(?:A\s*\(\s*\)|\n|$)'
            
            # Encontrar todas as questões
            matches = list(re.finditer(question_pattern, full_text, re.DOTALL))
            
            for i, match in enumerate(matches):
                question_number = int(match.group(1))
                question_text = clean_text(match.group(2))
                
                # Determinar próximo match para limitar o texto da questão
                next_match = matches[i+1] if i+1 < len(matches) else None
                
                # Extrair opções
                options_text = full_text[match.end():next_match.start() if next_match else None]
                
                # Padrão para extrair opções
                option_pattern = r'([A-Z])\s*\(\s*\)\s*([^A-Z\(\)]+)(?=[A-Z]\s*\(\s*\)|$)'
                option_matches = re.findall(option_pattern, options_text, re.DOTALL)
                
                # Processar opções
                options = []
                for label, text in option_matches:
                    cleaned_text = clean_text(text)
                    if cleaned_text:
                        options.append({
                            "label": label,
                            "text": cleaned_text
                        })
                
                # Determinar categoria
                category = ""
                if question_number <= 10:
                    category = "dados-pessoais" if question_number <= 4 else "financeiro"
                elif question_number <= 19:
                    category = "formacao"
                elif question_number <= 44:
                    category = "academico"
                else:
                    category = "licenciatura"
                
                # Determinar tipo de questão
                question_type = "multiple-choice" if options and len(options[0]['text']) < 100 else "likert"
                
                # Adicionar questão se tiver texto e opções
                if question_text and options:
                    questions.append({
                        "id": question_number,
                        "number": question_number,
                        "text": question_text,
                        "type": question_type,
                        "category": category,
                        "options": options
                    })
            
            # Remover duplicatas mantendo a primeira ocorrência
            unique_questions = []
            seen_ids = set()
            for q in questions:
                if q['id'] not in seen_ids:
                    unique_questions.append(q)
                    seen_ids.add(q['id'])
            
            # Ordenar questões
            unique_questions.sort(key=lambda x: x['number'])
            
            return unique_questions
    
    except Exception as e:
        print(f"Erro ao extrair questões: {e}")
        return []

def save_questions_to_json(questions, output_path):
    """
    Salva questões em um arquivo JSON.
    
    Args:
        questions (list): Lista de questões
        output_path (str): Caminho para salvar o arquivo JSON
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"Questões salvas em {output_path}")

if __name__ == "__main__":
    # Caminho para o PDF do ENADE
    pdf_path = "enade_questionnaire.pdf"
    output_path = "questions.json"
    
    # Extrair questões
    questions = extract_questions_from_pdf(pdf_path)
    
    # Salvar questões
    save_questions_to_json(questions, output_path)