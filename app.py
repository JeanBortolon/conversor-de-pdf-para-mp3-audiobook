# ==============================================================================
# IMPORTAÇÕES E EXPLICAÇÃO DO PORQUÊ CADA RECURSO É UTILIZADO
# ==============================================================================

# asyncio: necessário porque a biblioteca 'edge-tts' trabalha de forma assíncrona (async/await)
import asyncio

# base64: usado para decodificar o áudio que a API do Google Gemini retorna em texto Base64
import base64

# concurrent.futures: permite rodar funções assíncronas em uma thread separada sem conflitar com o loop do Streamlit
import concurrent.futures

# hashlib: gera códigos únicos (hashes SHA-256) para identificar cada livro e evitar reprocessamento repetido
import hashlib

# json: salva e lê o arquivo 'metadata.json' no disco para lembrar onde a narração parou caso o PC desligue
import json

# math: fornece o valor de infinito (-math.inf) usado no algoritmo que separa palavras coladas em títulos
import math

# re (Expressões Regulares): essencial para limpar ruídos do PDF, expandir abreviações e dividir frases
import re

# subprocess: executa o binário do FFmpeg em segundo plano para converter WAV em MP3 e unir os trechos do livro
import subprocess

# time: controla as pausas de segurança (backoff) entre tentativas quando a internet oscila ou a API pede espera
import time

# wave: biblioteca nativa para empacotar o áudio bruto (PCM 24kHz) do Google Gemini em um arquivo WAV válido
import wave

# Counter: calcula estatisticamente qual é o tamanho de fonte padrão do corpo do livro e quais cabeçalhos se repetem
from collections import Counter

# datetime: registra a data e hora exata do último backup salvo no computador
from datetime import datetime

# Path: manipula caminhos de pastas e arquivos de um jeito que funciona igual no Windows, Linux e macOS
from pathlib import Path

# typing: adiciona dicas de tipo (type hints) para deixar o código legível e fácil de dar manutenção
from typing import Dict, List, Optional, Tuple

# edge_tts: cliente gratuito de síntese de voz neural da Microsoft (não exige chave de API)
import edge_tts

# fitz (PyMuPDF): responsável por abrir o PDF e extrair textos junto com a posição e tamanho da fonte de cada linha
import fitz

# imageio_ffmpeg: entrega o executável do FFmpeg pronto para uso sem o usuário precisar instalar nada no Windows
import imageio_ffmpeg

# requests: faz as requisições HTTP para as APIs de voz em nuvem (Google Gemini, OpenAI e ElevenLabs)
import requests

# streamlit: constrói toda a interface visual no navegador usando apenas código Python
import streamlit as st

# wordfreq: consulta a frequência real das palavras em português para separar títulos que vieram grudados no PDF
try:
    from wordfreq import zipf_frequency as _zipf_freq
except ImportError:
    # Caso o usuário ainda não tenha instalado o wordfreq, o código usa nosso dicionário interno de segurança
    _zipf_freq = None


# ==============================================================================
# DIRETÓRIO DE BACKUP E CATÁLOGOS DE VOZES E REGRAS LINGUÍSTICAS
# ==============================================================================

# Define a pasta permanente de projetos ao lado do arquivo app.py (sobrevive ao desligamento do PC)
PROJECTS_ROOT = Path(__file__).resolve().parent / "projetos_audiobook"
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

# Catálogo de vozes masculinas do Google Gemini TTS focadas em leitura natural e contação de histórias
GEMINI_MALE_VOICES: Dict[str, str] = {
    "Charon — Masculina Calma, Grave e Humana (Estilo Contador de Histórias)": "Charon",
    "Orus — Masculina Firme, Madura e Neutra": "Orus",
    "Puck — Masculina Acolhedora e Natural": "Puck",
    "Fenrir — Masculina Profunda e Imponente": "Fenrir",
}

# Catálogo de vozes masculinas da OpenAI com sotaque neutro em português brasileiro
OPENAI_MALE_VOICES: Dict[str, str] = {
    "Onyx — Masculina Grave, Firme e Humana (pt-BR Neutro)": "onyx",
    "Ash — Masculina Clara, Tranquila e Natural (pt-BR Neutro)": "ash",
    "Echo — Masculina Suave de Contação de História": "echo",
}

# Em português, apenas estas vogais existem como palavras reais de 1 única letra.
# Qualquer consoante solta ('b', 'c', 'p', 'r') é resíduo visual do PDF e seria soletrada pelo narrador.
VALID_1LETTER_PT = {"a", "e", "o", "à", "é", "ó"}

# Conjunto fechado das palavras válidas de 2 letras no português (evita quebrar palavras em sílabas soltas)
VALID_2LETTER_PT = {
    "ao", "as", "às", "da", "de", "do", "em", "eu", "fé", "ir", "já", "lá",
    "lê", "me", "na", "no", "nu", "os", "ou", "pé", "pó", "ré", "ri", "sé",
    "se", "só", "te", "ti", "tu", "um", "vá", "vê", "vi", "vó", "vô",
}

# Vocabulário base de segurança para separar títulos colados mesmo sem o pacote 'wordfreq'
FALLBACK_PT_WORDS = {
    "a", "as", "ao", "aos", "carta", "iniciado", "prólogo", "epílogo", "capítulo",
    "parte", "livro", "grimório", "proibido", "como", "seduzir", "qualquer",
    "mulher", "com", "uma", "única", "frase", "faça", "te", "desejar", "ordem",
    "da", "rosa", "documento", "interno", "não", "reproduzir", "introdução",
    "conclusão", "segredo", "segredos", "poder", "mente", "homem", "homens",
    "vida", "mundo", "tempo", "forma", "modo", "tudo", "nada", "sempre", "nunca",
    "para", "pelo", "pela", "pelos", "pelas", "sobre", "entre", "contra", "desde",
    "sem", "sob", "após", "até", "mais", "menos", "muito", "pouco", "todo",
    "toda", "todos", "todas", "outro", "outra", "outros", "outras", "mesmo",
    "mesma", "este", "esta", "isto", "esse", "essa", "isso", "aquele", "aquela",
    "aquilo", "seu", "sua", "seus", "suas", "meu", "minha", "meus", "minhas",
    "nosso", "nossa", "quem", "qual", "quais", "onde", "quando", "porque",
    "por", "que", "se", "em", "no", "na", "nos", "nas", "do", "dos", "das",
    "de", "um", "uns", "umas", "o", "os", "e", "ou", "mas", "nem", "já", "só",
    "eu", "tu", "ele", "ela", "nós", "vós", "eles", "elas", "me", "ti", "si",
    "lhe", "lhes", "ser", "estar", "ter", "haver", "fazer", "dizer", "ver",
    "ir", "vir", "dar", "saber", "querer", "dever", "falar", "olhar", "sentir",
    "pensar", "deixar", "passar", "chegar", "ficar", "parecer", "conhecer",
    "viver", "encontrar", "chamar", "tomar", "começar", "entender", "olhos",
    "voz", "mão", "mãos", "corpo", "noite", "dia", "vez", "casa", "caminho",
    "verdade", "medo", "desejo", "amor", "força", "silêncio", "palavra",
    "palavras", "história", "atenção", "primeiro", "primeira", "segundo",
    "segunda", "terceiro", "terceira", "quarto", "quarta", "quinto", "lei",
    "regra", "passo", "arte", "jogo", "sombra", "luz", "fogo", "alma",
    "coração", "instinto", "presença", "energia", "mistério", "chave", "porta",
}

# Mapeia algarismos romanos de capítulos para números arábicos (evita que 'Capítulo IV' seja lido como 'i-vê')
ROMAN_TO_TEXT = {
    "I": "1", "II": "2", "III": "3", "IV": "4", "V": "5",
    "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10",
    "XI": "11", "XII": "12", "XIII": "13", "XIV": "14", "XV": "15",
    "XVI": "16", "XVII": "17", "XVIII": "18", "XIX": "19", "XX": "20",
}

# Abreviações comuns em livros que cortam a cadência da frase ou induzem pronúncia em inglês se não forem expandidas
ABBREVIATIONS_PT = [
    (r"\bp\.\s*ex\.", "por exemplo"),
    (r"\bpágs\.", "páginas"),
    (r"\bpág\.", "página"),
    (r"\bcaps\.", "capítulos"),
    (r"\bcap\.", "capítulo"),
    (r"\bobs\.", "observação"),
    (r"\bsra\.", "senhora"),
    (r"\bsrta\.", "senhorita"),
    (r"\bsr\.", "senhor"),
    (r"\bdra\.", "doutora"),
    (r"\bdr\.", "doutor"),
    (r"\bprofa\.", "professora"),
    (r"\bprof\.", "professor"),
    (r"\bsécs\.", "séculos"),
    (r"\bséc\.", "século"),
    (r"\betc\.", "etcétera"),
    (r"\bn\.?[º°]", "número "),
    (r"\bvol\.", "volume"),
    (r"\bfig\.", "figura"),
]

# Expressão regular para checar se uma palavra possui pelo menos uma vogal (evita soletração de siglas sem vogal)
VOWEL_RE = re.compile(r"[aeiouáéíóúâêôãõüAEIOUÁÉÍÓÚÂÊÔÃÕÜ]")


# ==============================================================================
# FUNÇÕES UTILITÁRIAS DE EXECUÇÃO ASSÍNCRONA E GERENCIAMENTO DE BACKUP EM DISCO
# ==============================================================================

def run_async(coro):
    """Executa uma corrotina async mesmo quando o Streamlit já mantém um loop de eventos ativo."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    # Se já houver um loop ativo na thread atual, executamos a corrotina em uma thread dedicada
    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def save_project_meta(proj_dir: Path, meta: dict) -> None:
    """Salva o estado atual do projeto em disco de forma atômica (evita corromper se faltar luz durante a gravação)."""
    meta["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    meta_path = proj_dir / "metadata.json"
    tmp_meta = proj_dir / "metadata_tmp.json"
    # Primeiro grava em arquivo temporário e só depois substitui o oficial
    tmp_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_meta.replace(meta_path)


def load_project_meta(proj_dir: Path) -> Optional[dict]:
    """Lê os dados de um projeto salvo anteriormente no disco."""
    meta_path = proj_dir / "metadata.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_saved_projects() -> List[Tuple[Path, dict, int]]:
    """Varre a pasta 'projetos_audiobook' e lista todos os livros com backup disponível para retomada."""
    projects: List[Tuple[Path, dict, int]] = []
    if not PROJECTS_ROOT.exists():
        return projects
    # Ordena do projeto modificado mais recentemente para o mais antigo
    for d in sorted(PROJECTS_ROOT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        meta = load_project_meta(d)
        txt_file = d / "texto_extraido.txt"
        if not meta or not txt_file.exists():
            continue
        chunks_dir = d / "chunks"
        done_count = 0
        # Conta quantos trechos MP3 válidos (> 100 bytes) já estão prontos no disco
        if chunks_dir.exists():
            done_count = sum(1 for f in chunks_dir.glob("chunk_*.mp3") if f.stat().st_size > 100)
        projects.append((d, meta, done_count))
    return projects


@st.cache_data(ttl=3600, show_spinner=False)
def get_active_edge_pt_male_voices() -> Dict[str, str]:
    """Consulta o servidor da Microsoft para exibir apenas vozes masculinas em Português realmente ativas."""
    fallback = {
        "Antônio (Português Brasil Nativo — Voz Masculina Limpa)": "pt-BR-AntonioNeural",
        "Duarte (Português — Voz Masculina Firme e Neutra)": "pt-PT-DuarteNeural",
    }
    try:
        voices = run_async(edge_tts.list_voices())
        found: Dict[str, str] = {}
        for v in voices:
            short_name = v.get("ShortName", "")
            locale = v.get("Locale", "")
            gender = v.get("Gender", "")
            if gender == "Male" and locale.startswith("pt-"):
                friendly = (
                    short_name.replace("Neural", "")
                    .replace("pt-BR-", "Português BR — ")
                    .replace("pt-PT-", "Português PT — ")
                )
                found[f"{friendly} ({short_name})"] = short_name
        return found if found else fallback
    except Exception:
        return fallback


# ==============================================================================
# EXTRAÇÃO FIEL E RECONSTRUÇÃO INTELIGENTE DO TEXTO DO PDF
# ==============================================================================

def _pt_word_score(w: str) -> float:
    """Atribui uma nota para saber se um pedaço de texto é uma palavra real do português."""
    wl = w.lower()
    n = len(wl)
    if n == 1:
        return 12.0 if wl in VALID_1LETTER_PT else -1000.0
    if n == 2:
        return 22.0 if wl in VALID_2LETTER_PT else -1000.0
    if not VOWEL_RE.search(wl):
        return -1000.0
    if _zipf_freq is not None:
        z = _zipf_freq(wl, "pt")
        if z >= 2.15 or wl in FALLBACK_PT_WORDS:
            eff_z = max(z, 3.8 if wl in FALLBACK_PT_WORDS else z)
            return (eff_z + 1.0) * (n ** 1.38)
        return -1000.0
    return 5.0 * (n ** 1.38) if wl in FALLBACK_PT_WORDS else -1000.0


def segment_glued_portuguese(token: str) -> str:
    """
    Usa Programação Dinâmica para separar títulos em maiúsculas que ficaram colados
    após remover o espaçamento artístico entre letras (ex: 'ACARTAAOINICIADO' -> 'A CARTA AO INICIADO').
    """
    clean = token.strip()
    # Se for curta ou já for uma única palavra válida em português, não mexe em nada
    if len(clean) < 4 or not clean.isalpha() or _pt_word_score(clean) > 0:
        return token

    s = clean.lower()
    n = len(s)
    dp = [-math.inf] * (n + 1)
    back = [-1] * (n + 1)
    dp[0] = 0.0

    for i in range(n):
        if dp[i] == -math.inf:
            continue
        for j in range(i + 1, min(n, i + 20) + 1):
            sc = _pt_word_score(s[i:j])
            if sc > 0:
                cand = dp[i] + sc - 7.5  # Penalidade leve para preferir palavras inteiras maiores
                if cand > dp[j]:
                    dp[j] = cand
                    back[j] = i

    if dp[n] == -math.inf:
        return token

    parts: List[str] = []
    curr = n
    while curr > 0:
        prev = back[curr]
        if prev < 0:
            return token
        parts.append(clean[prev:curr])
        curr = prev
    parts.reverse()
    return " ".join(parts)


def _fix_spaced_uppercase_only(line: str) -> str:
    """
    Junta letras MAIÚSCULAS que foram separadas por espaço na diagramação do PDF
    (ex: 'P R Ó L O G O' -> 'PRÓLOGO'), sem tocar no texto normal em minúsculas.
    """
    if not re.search(r"[A-ZÀ-Ý][ \t]+[A-ZÀ-Ý][ \t]+[A-ZÀ-Ý]", line):
        return re.sub(r"[ \t]{2,}", " ", line.strip())

    # Preserva espaços múltiplos como divisores explícitos entre palavras
    s = re.sub(r"[ \t]{2,}", " \x00 ", line.strip())

    def _join_upper(m: re.Match) -> str:
        glued = re.sub(r"[ \t]+", "", m.group(0))
        return segment_glued_portuguese(glued)

    s = re.sub(r"(?<![A-Za-zÀ-ÿ])(?:[A-ZÀ-Ý][ \t]+){2,}[A-ZÀ-Ý](?![A-Za-zÀ-ÿ])", _join_upper, s)
    s = s.replace("\x00", " ")
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def _expand_abbreviations_and_clean(paragraph: str, is_heading: bool = False) -> str:
    """
    Prepara o parágrafo para leitura humana fluida:
    1. Expande abreviações (sr., dr., cap., p. ex.);
    2. Converte CAIXA ALTA para escrita normal (evita que o narrador soletre siglas);
    3. Garante pontuação final em títulos e subtítulos.
    """
    text = paragraph.strip()
    if not text:
        return ""

    # Remove acentos soltos sem letra que travam alguns sintetizadores
    text = re.sub(r"[´`¨]", "", text)

    for pattern, replacement in ABBREVIATIONS_PT:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    alpha_chars = [c for c in text if c.isalpha()]
    is_all_caps = bool(alpha_chars) and (sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars) > 0.80)

    def _fix_word(match: re.Match) -> str:
        w = match.group(0)
        if w in ROMAN_TO_TEXT and (is_heading or is_all_caps):
            return ROMAN_TO_TEXT[w]
        # Passa palavras em CAIXA ALTA (como 'FAÇA', 'AO', 'SE') para minúscula para leitura natural
        if len(w) >= 2 and w.isupper():
            return w.lower()
        return w

    text = re.sub(r"\b[A-Za-zÀ-ÿ]+\b", _fix_word, text)

    # Filtra tokens sem vogais ou consoantes soltas para que o narrador nunca soletre letra por letra
    cleaned_tokens: List[str] = []
    for tok in text.split():
        letters_only = re.sub(r"[^A-Za-zÀ-ÿ]", "", tok)
        if letters_only:
            if len(letters_only) == 1 and letters_only.lower() not in VALID_1LETTER_PT:
                continue
            if len(letters_only) >= 2 and not VOWEL_RE.search(letters_only):
                continue
        cleaned_tokens.append(tok)

    text = " ".join(cleaned_tokens).strip()
    if not text:
        return ""

    # Restaura letra maiúscula no começo do parágrafo e após ponto final
    text = text[0].upper() + text[1:]
    text = re.sub(r"([.!?…]\s+)([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), text)

    # Adiciona ponto final em títulos soltos para dar pausa e entonação conclusiva antes do texto
    if (is_heading or is_all_caps) and not re.search(r'[.!?…:»”"\')]$', text):
        text += "."
    return text


def _normalize_margin_signature(text: str) -> str:
    """Cria uma assinatura simplificada da linha para detectar cabeçalhos e rodapés repetidos."""
    s = _fix_spaced_uppercase_only(text).lower()
    s = re.sub(r"\d+", "#", s)
    return re.sub(r"[^a-zà-ÿ#]+", "", s)


def extract_book_text(pdf_bytes: bytes) -> Tuple[str, int]:
    """
    Percorre todas as páginas do PDF extraindo o texto fiel do livro,
    removendo cabeçalhos/rodapés repetidos e juntando linhas quebradas da mesma frase.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    if total_pages == 0:
        raise ValueError("O arquivo PDF está vazio.")

    pages_lines: List[List[Tuple[float, float, float, str, float]]] = []
    margin_counter: Counter = Counter()
    all_font_sizes: List[float] = []

    for page in doc:
        page_height = float(page.rect.height) or 800.0
        d = page.get_text("dict")
        raw_lines: List[Tuple[float, float, float, float, str]] = []

        for block in d.get("blocks", []):
            # Ignora blocos de imagem (type != 0), lendo apenas blocos de texto
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                l_bbox = line.get("bbox", (0, 0, 0, 0))
                lx0, ly0, ly1 = float(l_bbox[0]), float(l_bbox[1]), float(l_bbox[3])
                spans = line.get("spans", [])
                if not spans:
                    continue
                span_texts = [sp.get("text", "") for sp in spans if sp.get("text")]
                if not span_texts:
                    continue
                avg_sz = sum(float(sp.get("size", 11.0)) for sp in spans) / len(spans)
                raw_lines.append((ly0, ly1, lx0, avg_sz, "".join(span_texts)))

        # Ordena as linhas da página de cima para baixo e da esquerda para a direita
        raw_lines.sort(key=lambda item: (round(item[0], 1), item[2]))

        # Une pedaços da mesma linha horizontal (ex: uma palavra em itálico no meio da frase)
        merged_lines: List[Tuple[float, float, float, str]] = []
        for ly0, ly1, lx0, avg_sz, txt in raw_lines:
            if merged_lines and abs(ly0 - merged_lines[-1][0]) <= max(avg_sz * 0.35, 3.0):
                py0, py1, psz, ptxt = merged_lines[-1]
                sep = "" if (ptxt.endswith(" ") or txt.startswith(" ")) else " "
                merged_lines[-1] = (min(py0, ly0), max(py1, ly1), (psz + avg_sz) / 2.0, ptxt + sep + txt)
            else:
                merged_lines.append((ly0, ly1, avg_sz, txt))

        page_extracted: List[Tuple[float, float, float, str, float]] = []
        seen_sigs = set()

        for ly0, ly1, avg_sz, txt in merged_lines:
            line_text = re.sub(r"[\u00ad\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u2028\u2029]", "", txt)
            line_text = _fix_spaced_uppercase_only(line_text)
            # Pula divisores puramente decorativos (* * *, ---)
            if not line_text or re.fullmatch(r"[\s*\-–—•·~=_.#♦❖✧★]+", line_text):
                continue

            # Identifica se a linha está no topo (12%) ou rodapé (12%) da página
            in_margin = (ly0 < page_height * 0.12) or (ly1 > page_height * 0.88)
            if in_margin and re.fullmatch(r"[-–—|\s]*(?:pág\.?|página)?\s*\d{1,5}[-–—|\s]*", line_text.lower()):
                continue

            if in_margin and len(line_text) <= 115:
                sig = _normalize_margin_signature(line_text)
                if len(sig) >= 4 and sig not in seen_sigs:
                    margin_counter[sig] += 1
                    seen_sigs.add(sig)

            all_font_sizes.append(round(avg_sz, 1))
            page_extracted.append((ly0, ly1, avg_sz, line_text, page_height))

        pages_lines.append(page_extracted)

    doc.close()

    # Descobre o tamanho da fonte principal do corpo do livro (o tamanho mais frequente)
    body_font_size = Counter(all_font_sizes).most_common(1)[0][0] if all_font_sizes else 11.0
    # Qualquer texto de margem que apareça em 2 ou mais páginas é cabeçalho/rodapé repetitivo
    repeating_headers = {sig for sig, cnt in margin_counter.items() if cnt >= 2}
    raw_paragraphs: List[Tuple[str, bool]] = []

    for page_extracted in pages_lines:
        filtered_lines: List[Tuple[float, float, float, str]] = []
        for ly0, ly1, avg_sz, line_text, page_height in page_extracted:
            in_margin = (ly0 < page_height * 0.12) or (ly1 > page_height * 0.88)
            if in_margin and len(line_text) <= 115 and _normalize_margin_signature(line_text) in repeating_headers:
                continue
            filtered_lines.append((ly0, ly1, avg_sz, line_text))

        for idx, (ly0, ly1, avg_sz, line_text) in enumerate(filtered_lines):
            # Considera título/subtítulo se a fonte for pelo menos 18% maior que o texto normal
            is_heading = avg_sz >= body_font_size * 1.18
            if not raw_paragraphs:
                raw_paragraphs.append((line_text, is_heading))
                continue

            prev_text, prev_is_heading = raw_paragraphs[-1]
            if idx > 0:
                prev_ly0, prev_ly1, prev_sz, _ = filtered_lines[idx - 1]
                vertical_gap = max(0.0, ly0 - prev_ly1)
                line_height = max(prev_ly1 - prev_ly0, prev_sz, 10.0)
                same_font_tier = abs(avg_sz - prev_sz) <= 1.6
            else:
                vertical_gap = body_font_size * 0.8
                line_height = body_font_size
                same_font_tier = (is_heading == prev_is_heading)

            prev_ends_sentence = bool(re.search(r'[.!?…:»”"\')]$', prev_text))
            # Reconstrói palavras separadas por hífen no fim da linha (ex: "histó-" + "ria" -> "história")
            if prev_text.endswith("-") and re.match(r"^[a-zà-ÿ]", line_text):
                raw_paragraphs[-1] = (prev_text[:-1] + line_text, prev_is_heading)
                continue

            # Junta linhas consecutivas da mesma frase para não cortar preposições no fim da linha
            should_join = False
            if same_font_tier:
                if is_heading and prev_is_heading:
                    if not prev_ends_sentence and vertical_gap <= line_height * 2.2:
                        should_join = True
                elif not is_heading and not prev_is_heading:
                    if not prev_ends_sentence or (idx > 0 and vertical_gap <= line_height * 1.38):
                        should_join = True

            if should_join:
                raw_paragraphs[-1] = (f"{prev_text} {line_text}", prev_is_heading)
            else:
                raw_paragraphs.append((line_text, is_heading))

    final_paragraphs: List[str] = []
    for para_text, is_heading in raw_paragraphs:
        norm = _expand_abbreviations_and_clean(para_text, is_heading=is_heading)
        if not norm:
            continue
        # Evita ler um título duplicado duas vezes seguidas
        if final_paragraphs and _normalize_margin_signature(final_paragraphs[-1]) == _normalize_margin_signature(norm):
            continue
        final_paragraphs.append(norm)

    full_text = "\n\n".join(final_paragraphs).strip()
    if not re.search(r"[A-Za-zÀ-ÿ0-9]", full_text):
        raise ValueError("Não foi possível extrair texto legível deste PDF.")
    return full_text, total_pages


# ==============================================================================
# DIVISÃO DO LIVRO EM TRECHOS (CHUNKS) RESPEITANDO PARÁGRAFOS E FRASES
# ==============================================================================

def _split_long_sentence(sentence: str, max_chars: int) -> List[str]:
    """Divide uma frase gigante nas fronteiras de palavras sem cortar nenhuma palavra ao meio."""
    words = sentence.split()
    parts: List[str] = []
    current = ""
    for w in words:
        cand = f"{current} {w}".strip() if current else w
        if len(cand) <= max_chars:
            current = cand
        else:
            if current:
                parts.append(current)
            current = w
    if current:
        parts.append(current)
    return parts


def split_text_into_chunks(text: str, max_chars: int = 1800) -> List[str]:
    """Agrupa parágrafos até o limite seguro de cada API, garantindo cortes apenas em finais de frase."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""

    def flush():
        nonlocal current
        if current and re.search(r"[A-Za-zÀ-ÿ0-9]", current):
            chunks.append(current.strip())
        current = ""

    for para in paragraphs:
        cand = f"{current}\n\n{para}" if current else para
        if len(cand) <= max_chars:
            current = cand
            continue
        flush()
        if len(para) <= max_chars:
            current = para
            continue
        for sent in re.split(r"(?<=[.!?…»”])\s+", para):
            sent = sent.strip()
            if not sent:
                continue
            cand_s = f"{current} {sent}".strip() if current else sent
            if len(cand_s) <= max_chars:
                current = cand_s
            else:
                flush()
                if len(sent) <= max_chars:
                    current = sent
                else:
                    chunks.extend(_split_long_sentence(sent, max_chars))
    flush()
    return chunks


# ==============================================================================
# MOTORES DE SÍNTESE DE VOZ (EDGE TTS, GOOGLE GEMINI, OPENAI E ELEVENLABS)
# ==============================================================================

def _sanitize_for_edge(text: str) -> str:
    """Remove quebras de linha brutas e caracteres invisíveis que poderiam falhar no Edge TTS."""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u2028\u2029\ufeff]", " ", text)
    s = re.sub(r"\s*\n+\s*", " ", s)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


async def _edge_tts_save(text: str, voice: str, rate: str, pitch: str, out_path: Path) -> None:
    """Envia o texto ao serviço neural da Microsoft e salva o fluxo MP3 resultante."""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(out_path))


def synthesize_chunk_edge(text: str, voice: str, rate: str, pitch: str, out_path: Path, max_retries: int = 4) -> None:
    """Gera o áudio de um trecho via Edge TTS com retentativa automática e gravação atômica."""
    clean_text = _sanitize_for_edge(text)
    if not re.search(r"[A-Za-zÀ-ÿ0-9]", clean_text):
        clean_text = "."
    tmp_path = out_path.with_name(f"{out_path.stem}_tmp.mp3")
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            if tmp_path.exists():
                tmp_path.unlink()
            use_voice = "pt-BR-AntonioNeural" if attempt == max_retries - 1 else voice
            use_rate = "+0%" if attempt == max_retries - 1 else rate
            run_async(_edge_tts_save(clean_text, use_voice, use_rate, "+0Hz", tmp_path))
            if tmp_path.exists() and tmp_path.stat().st_size > 100:
                tmp_path.replace(out_path)
                return
            raise RuntimeError("Áudio vazio retornado pelo Edge TTS.")
        except Exception as exc:
            last_err = exc
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Falha no Edge TTS: {last_err}")


def synthesize_chunk_gemini(text: str, api_key: str, voice_name: str, out_path: Path, max_retries: int = 8) -> None:
    """Sintetiza voz humana via Google Gemini 2.5 Flash TTS, empacota em WAV e converte para MP3."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key.strip()}"
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}},
        },
    }
    tmp_wav = out_path.with_name(f"{out_path.stem}_tmp.wav")
    tmp_mp3 = out_path.with_name(f"{out_path.stem}_tmp.mp3")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    last_err = ""
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                inline_data = data["candidates"][0]["content"]["parts"][0]["inlineData"]
                pcm_bytes = base64.b64decode(inline_data["data"])
                # Salva o áudio PCM 24kHz mono 16-bit em um container WAV padrão
                with wave.open(str(tmp_wav), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(pcm_bytes)
                # Converte o WAV para MP3 128kbps usando o FFmpeg embutido
                cmd = [
                    ffmpeg_exe, "-y", "-i", str(tmp_wav),
                    "-c:a", "libmp3lame", "-b:a", "128k", "-f", "mp3", str(tmp_mp3),
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if tmp_wav.exists():
                    tmp_wav.unlink()
                if proc.returncode == 0 and tmp_mp3.exists() and tmp_mp3.stat().st_size > 100:
                    tmp_mp3.replace(out_path)
                    return
                raise RuntimeError(f"Erro ffmpeg: {proc.stderr[-300:]}")
            if resp.status_code in (400, 401, 403):
                raise ValueError(f"Erro na chave/API Google Gemini ({resp.status_code}): {resp.text[:250]}")
            if resp.status_code == 429:
                # Aguarda automaticamente o reset do limite por minuto na conta gratuita
                time.sleep(12.0 * (attempt + 1))
                last_err = "Limite de requisições por minuto (429) atingido."
                continue
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            time.sleep(3.0 * (attempt + 1))
        except ValueError:
            raise
        except Exception as exc:
            last_err = str(exc)
            if attempt < max_retries - 1:
                time.sleep(3.0 * (attempt + 1))
    raise RuntimeError(f"Falha no Gemini TTS: {last_err}")


def synthesize_chunk_openai(text: str, api_key: str, voice: str, out_path: Path, max_retries: int = 4) -> None:
    """Sintetiza áudio via API OpenAI (gpt-4o-mini-tts) com instruções de português neutro."""
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": voice,
        "input": text,
        "instructions": (
            "Narre em português brasileiro nativo e neutro, sem sotaque carioca, "
            "com voz masculina tranquila, firme e humana, no ritmo calmo de alguém contando uma história."
        ),
        "response_format": "mp3",
    }
    tmp_path = out_path.with_name(f"{out_path.stem}_tmp.mp3")
    last_err = ""
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 100:
                tmp_path.write_bytes(resp.content)
                tmp_path.replace(out_path)
                return
            if resp.status_code in (401, 403):
                raise ValueError("Chave da API OpenAI inválida.")
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            time.sleep(2.0 * (2**attempt))
        except ValueError:
            raise
        except Exception as exc:
            last_err = str(exc)
            if attempt < max_retries - 1:
                time.sleep(2.0 * (2**attempt))
    raise RuntimeError(f"Falha no OpenAI TTS: {last_err}")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_elevenlabs_voices(api_key: str) -> List[Tuple[str, str]]:
    """Lista as vozes disponíveis na conta ElevenLabs do usuário, priorizando vozes masculinas."""
    resp = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": api_key.strip()}, timeout=20)
    resp.raise_for_status()
    items: List[Tuple[int, str, str]] = []
    for v in resp.json().get("voices", []):
        labels = v.get("labels", {}) or {}
        gender = str(labels.get("gender", ""))
        meta = ", ".join(str(labels.get(k, "")) for k in ("gender", "description", "accent") if labels.get(k))
        label = f"{v['name']} ({meta})" if meta else v["name"]
        items.append((0 if gender.lower() == "male" else 1, label, v["voice_id"]))
    items.sort(key=lambda x: (x[0], x[1].lower()))
    return [(label, vid) for _, label, vid in items]


def synthesize_chunk_elevenlabs(
    text: str, api_key: str, voice_id: str, out_path: Path,
    previous_text: str = "", next_text: str = "", max_retries: int = 4,
) -> None:
    """Sintetiza áudio via ElevenLabs usando contexto anterior/posterior para manter a entonação."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
    headers = {"xi-api-key": api_key.strip(), "Content-Type": "application/json", "Accept": "audio/mpeg"}
    payload: dict = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.62, "similarity_boost": 0.80, "style": 0.15, "use_speaker_boost": True},
    }
    if previous_text:
        payload["previous_text"] = previous_text[-350:]
    if next_text:
        payload["next_text"] = next_text[:350]
    tmp_path = out_path.with_name(f"{out_path.stem}_tmp.mp3")
    last_err = ""
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 100:
                tmp_path.write_bytes(resp.content)
                tmp_path.replace(out_path)
                return
            if resp.status_code in (401, 403):
                raise ValueError("Chave da API ElevenLabs inválida.")
            if resp.status_code in (400, 422):
                raise ValueError(f"Erro ElevenLabs ({resp.status_code}): {resp.text}")
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            time.sleep(2.0 * (2**attempt))
        except ValueError:
            raise
        except Exception as exc:
            last_err = str(exc)
            if attempt < max_retries - 1:
                time.sleep(2.0 * (2**attempt))
    raise RuntimeError(f"Falha no ElevenLabs: {last_err}")


def concatenate_mp3_chunks(chunk_paths: List[Path], output_path: Path, work_dir: Path) -> None:
    """
    Une todas as partes MP3 diretamente em disco via FFmpeg (concat demuxer),
    sem carregar o livro inteiro na memória RAM.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    filelist_path = work_dir / "filelist.txt"
    with open(filelist_path, "w", encoding="utf-8") as f:
        for p in chunk_paths:
            safe_relative = p.relative_to(work_dir).as_posix().replace("'", "'\\''")
            f.write(f"file '{safe_relative}'\n")

    # Tenta primeiro cópia direta de stream (-c copy), que é instantânea e sem perda de qualidade
    cmd_copy = [ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", "filelist.txt", "-c", "copy", output_path.name]
    res = subprocess.run(cmd_copy, cwd=str(work_dir), capture_output=True, text=True)
    if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 100:
        return

    # Caso algum trecho tenha taxa de amostragem diferente, recodifica de forma padronizada em 128kbps
    cmd_enc = [
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", "filelist.txt",
        "-c:a", "libmp3lame", "-b:a", "128k", output_path.name,
    ]
    res2 = subprocess.run(cmd_enc, cwd=str(work_dir), capture_output=True, text=True)
    if res2.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"Erro ao unir MP3 via ffmpeg: {res2.stderr}")


def synthesize_single_segment(
    text: str, engine: str, voice_id: str, api_key: str,
    edge_rate: str, edge_pitch: str, out_path: Path,
    prev_txt: str = "", next_txt: str = "",
) -> None:
    """Roteia a síntese do trecho atual para o motor de voz escolhido pelo usuário."""
    if engine.startswith("Edge TTS"):
        synthesize_chunk_edge(text, voice_id, edge_rate, edge_pitch, out_path)
    elif engine.startswith("Google Gemini"):
        synthesize_chunk_gemini(text, api_key, voice_id, out_path)
    elif engine.startswith("OpenAI"):
        synthesize_chunk_openai(text, api_key, voice_id, out_path)
    else:
        synthesize_chunk_elevenlabs(text, api_key, voice_id, out_path, prev_txt, next_txt)


# ==============================================================================
# INTERFACE WEB PRINCIPAL (STREAMLIT)
# ==============================================================================

def main() -> None:
    st.set_page_config(page_title="PDF para Audiobook MP3", page_icon="🎧", layout="centered")
    st.title("PDF para Audiobook (MP3)")
    st.caption(f"💾 Backup automático ativo na pasta: `{PROJECTS_ROOT}`")

    # 1. Lista projetos já salvos no disco para retomar caso o PC tenha sido desligado
    saved_projects = list_saved_projects()
    if saved_projects:
        with st.expander("💾 Projetos Salvos no Computador (Retomar de onde parou)", expanded=True):
            for proj_dir, meta, done_count in saved_projects:
                total_c = meta.get("total_chunks", 0)
                pct = int((done_count / total_c) * 100) if total_c > 0 else 0
                c1, c2 = st.columns([3, 1])
                c1.markdown(
                    f"**📖 {meta.get('book_name', proj_dir.name)}** ({meta.get('total_pages', '?')} págs)  \n"
                    f"Progresso salvo: **{done_count} de {total_c or '?'} trechos ({pct}%)** — "
                    f"*Último backup: {meta.get('updated_at', '-')}*"
                )
                if c2.button("📂 Abrir / Retomar", key=f"load_{proj_dir.name}", use_container_width=True):
                    st.session_state["active_proj_dir"] = str(proj_dir)
                    st.session_state["cached_book_text"] = (proj_dir / "texto_extraido.txt").read_text(encoding="utf-8")
                    st.session_state["cached_total_pages"] = meta.get("total_pages", 0)
                    st.session_state["cached_book_name"] = meta.get("book_name", "livro.pdf")
                    st.session_state["cached_text_hash"] = meta.get("text_hash", proj_dir.name[-12:])
                    st.rerun()

    # 2. Upload de um novo livro em PDF
    uploaded_file = st.file_uploader("Ou carregue um novo arquivo de livro (.pdf)", type=["pdf"])
    if uploaded_file:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        # Só extrai o PDF se ele ainda não estiver carregado na memória da sessão atual
        if st.session_state.get("cached_file_id") != file_id:
            pdf_bytes = uploaded_file.getvalue()
            try:
                with st.spinner("Extraindo o texto do PDF e criando backup automático no disco..."):
                    book_text, total_pages = extract_book_text(pdf_bytes)
                text_hash = hashlib.sha256(book_text.encode("utf-8")).hexdigest()[:12]
                safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(uploaded_file.name).stem)[:35]
                proj_dir = PROJECTS_ROOT / f"{safe_stem}_{text_hash}"
                proj_dir.mkdir(parents=True, exist_ok=True)
                (proj_dir / "chunks").mkdir(parents=True, exist_ok=True)
                (proj_dir / "texto_extraido.txt").write_text(book_text, encoding="utf-8")

                existing_meta = load_project_meta(proj_dir) or {}
                existing_meta.update({
                    "book_name": uploaded_file.name,
                    "total_pages": total_pages,
                    "total_chars": len(book_text),
                    "text_hash": text_hash,
                })
                save_project_meta(proj_dir, existing_meta)

                st.session_state["cached_file_id"] = file_id
                st.session_state["active_proj_dir"] = str(proj_dir)
                st.session_state["cached_book_text"] = book_text
                st.session_state["cached_total_pages"] = total_pages
                st.session_state["cached_book_name"] = uploaded_file.name
                st.session_state["cached_text_hash"] = text_hash
            except Exception as exc:
                st.error(str(exc))
                return

    if not st.session_state.get("active_proj_dir"):
        return

    proj_dir = Path(st.session_state["active_proj_dir"])
    chunks_dir = proj_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    book_text = st.session_state["cached_book_text"]
    total_pages = st.session_state["cached_total_pages"]
    book_name = st.session_state["cached_book_name"]
    base_name = Path(book_name).stem

    st.info(f"📂 **Projeto ativo:** `{book_name}` — salvo em `{proj_dir}`")
    col1, col2 = st.columns(2)
    col1.metric("Páginas no PDF", total_pages)
    col2.metric("Caracteres para narração", f"{len(book_text):,}".replace(",", "."))

    with st.expander("Prévia do texto extraído (verificação de fidelidade)", expanded=False):
        preview = book_text[:2500] + ("..." if len(book_text) > 2500 else "")
        st.text(preview)

    # 3. Seleção do motor de voz e parâmetros
    st.subheader("Configuração da Voz (Português Brasileiro)")
    engine = st.radio(
        "Motor de narração",
        options=[
            "Edge TTS (Gratuito — Voz Nativa pt-BR, sem chave e sem limite)",
            "Google Gemini TTS (Voz Humana Contadora de História — Chave AIza... no Google AI Studio)",
            "OpenAI TTS (Altíssimo realismo em pt-BR — requer API Key OpenAI)",
            "ElevenLabs (Estúdio — requer API Key ElevenLabs)",
        ],
    )

    selected_voice_id = ""
    api_key = ""
    edge_rate = "-2%"
    edge_pitch = "+0Hz"

    if engine.startswith("Edge TTS"):
        active_edge_voices = get_active_edge_pt_male_voices()
        voice_label = st.selectbox("Voz masculina ativa na Microsoft", options=list(active_edge_voices.keys()))
        selected_voice_id = active_edge_voices[voice_label]
        rate_choice = st.select_slider(
            "Ritmo da leitura",
            options=["Pausada (-5%)", "Contando história (-2%)", "Natural (0%)"],
            value="Contando história (-2%)",
        )
        edge_rate = {"Pausada (-5%)": "-5%", "Contando história (-2%)": "-2%", "Normal (0%)": "+0%"}.get(rate_choice, "-2%")
    elif engine.startswith("Google Gemini"):
        st.caption("Crie uma chave permanente (começa com 'AIza...') em: https://aistudio.google.com/apikey")
        api_key = st.text_input("Sua API Key do Google AI Studio (Gemini)", type="password")
        voice_label = st.selectbox("Voz masculina Gemini", options=list(GEMINI_MALE_VOICES.keys()))
        selected_voice_id = GEMINI_MALE_VOICES[voice_label]
    elif engine.startswith("OpenAI"):
        api_key = st.text_input("Sua API Key da OpenAI", type="password")
        voice_label = st.selectbox("Voz masculina OpenAI", options=list(OPENAI_MALE_VOICES.keys()))
        selected_voice_id = OPENAI_MALE_VOICES[voice_label]
    else:
        api_key = st.text_input("Sua API Key da ElevenLabs", type="password")
        if api_key.strip():
            try:
                voices = fetch_elevenlabs_voices(api_key.strip())
                if voices:
                    labels = [v[0] for v in voices]
                    idx = st.selectbox("Voz ElevenLabs", options=range(len(labels)), format_func=lambda i: labels[i])
                    selected_voice_id = voices[idx][1]
            except Exception as exc:
                st.warning(f"Não foi possível listar vozes automaticamente: {exc}")
                selected_voice_id = st.text_input("Informe o Voice ID manualmente")

    max_chars = 3500 if engine.startswith("Google Gemini") else (2000 if engine.startswith("Edge TTS") else 1800)
    chunks = split_text_into_chunks(book_text, max_chars=max_chars)
    total_chunks = len(chunks)

    # Verifica quantos trechos já estão prontos no disco para exibir o progresso real
    done_chunks_now = [
        chunks_dir / f"chunk_{i:05d}.mp3"
        for i in range(total_chunks)
        if (chunks_dir / f"chunk_{i:05d}.mp3").exists() and (chunks_dir / f"chunk_{i:05d}.mp3").stat().st_size > 100
    ]
    st.progress(
        len(done_chunks_now) / max(1, total_chunks),
        text=f"Progresso já salvo no disco: {len(done_chunks_now)} de {total_chunks} trechos",
    )

    btn_col1, btn_col2 = st.columns(2)

    # Botão para ouvir rapidamente uma amostra dos primeiros parágrafos do livro
    if btn_col1.button("🔊 Testar Voz neste Livro (Amostra)", use_container_width=True):
        if not selected_voice_id or (not engine.startswith("Edge TTS") and not api_key.strip()):
            st.error("Configure a voz / chave da API antes de testar.")
        else:
            sample_text = "\n\n".join(book_text.split("\n\n")[:6])[:900]
            sample_path = proj_dir / "sample_test.mp3"
            try:
                with st.spinner("Gerando amostra com os primeiros parágrafos do livro..."):
                    synthesize_single_segment(
                        sample_text, engine, selected_voice_id, api_key,
                        edge_rate, edge_pitch, sample_path,
                    )
                st.audio(str(sample_path), format="audio/mpeg")
            except Exception as exc:
                st.error(f"Erro ao gerar amostra: {exc}")

    # Botão principal que gera ou retoma a narração do livro de onde parou
    if btn_col2.button("🎧 Gerar / Continuar Audiobook (.mp3)", type="primary", use_container_width=True):
        if not selected_voice_id or (not engine.startswith("Edge TTS") and not api_key.strip()):
            st.error("Selecione uma voz válida (e informe a API Key se aplicável).")
            return

        meta = load_project_meta(proj_dir) or {"book_name": book_name, "total_pages": total_pages}
        meta["total_chunks"] = total_chunks
        meta["engine"] = engine
        meta["voice_id"] = selected_voice_id
        save_project_meta(proj_dir, meta)

        progress_bar = st.progress(0.0, text="Verificando trechos salvos no disco...")
        chunk_paths: List[Path] = []

        try:
            for idx, chunk in enumerate(chunks):
                chunk_path = chunks_dir / f"chunk_{idx:05d}.mp3"
                chunk_paths.append(chunk_path)

                if not (chunk_path.exists() and chunk_path.stat().st_size > 100):
                    progress_bar.progress(idx / total_chunks, text=f"Narrando e salvando trecho {idx + 1} de {total_chunks}...")
                    prev_txt = chunks[idx - 1] if idx > 0 else ""
                    next_txt = chunks[idx + 1] if idx + 1 < total_chunks else ""
                    synthesize_single_segment(
                        chunk, engine, selected_voice_id, api_key,
                        edge_rate, edge_pitch, chunk_path, prev_txt, next_txt,
                    )
                    save_project_meta(proj_dir, meta)
                else:
                    progress_bar.progress(
                        idx / total_chunks,
                        text=f"Trecho {idx + 1} de {total_chunks} recuperado do backup...",
                    )

            progress_bar.progress(0.98, text="Unindo todos os trechos no arquivo MP3 final...")
            output_mp3 = proj_dir / f"{base_name}_audiobook.mp3"
            concatenate_mp3_chunks(chunk_paths, output_mp3, proj_dir)
            progress_bar.progress(1.0, text="Audiobook concluído e salvo no disco!")
            st.rerun()
        except Exception as exc:
            st.error(
                f"A geração parou no trecho {idx + 1} ({exc}). "
                f"Tudo até o trecho {idx} já está salvo no disco! Basta clicar em 'Gerar / Continuar' para retomar."
            )
            return

    # 4. Player e botão de download do MP3 completo (ou parcial, se ainda estiver em andamento)
    final_mp3 = proj_dir / f"{base_name}_audiobook.mp3"
    if final_mp3.exists() and final_mp3.stat().st_size > 100:
        st.success(f"✅ Audiobook completo salvo em: `{final_mp3}`")
        st.audio(str(final_mp3), format="audio/mpeg")
        with open(final_mp3, "rb") as f:
            st.download_button(
                label="⬇️ Baixar Audiobook Completo (.mp3)",
                data=f,
                file_name=f"{base_name}_audiobook.mp3",
                mime="audio/mpeg",
                use_container_width=True,
            )
    elif done_chunks_now:
        if st.button(f"🎵 Montar e Baixar MP3 Parcial ({len(done_chunks_now)} trechos já prontos)", use_container_width=True):
            partial_mp3 = proj_dir / f"{base_name}_parcial_{len(done_chunks_now)}_de_{total_chunks}.mp3"
            concatenate_mp3_chunks(done_chunks_now, partial_mp3, proj_dir)
            st.audio(str(partial_mp3), format="audio/mpeg")
            with open(partial_mp3, "rb") as f:
                st.download_button(
                    label="⬇️ Baixar MP3 Parcial",
                    data=f,
                    file_name=partial_mp3.name,
                    mime="audio/mpeg",
                    use_container_width=True,
                )


if __name__ == "__main__":
    main()