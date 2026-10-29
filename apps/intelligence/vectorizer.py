import re
import unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings

_TRANSFORMER_MODEL = None
_TRANSFORMER_INITIALIZED = False

def normalize_text(text):
    """
    Unicode-aware text normalization preserving multilingual scripts
    (English, Tamil, Hindi, Devanagari, Bengali, Telugu, etc.) while stripping
    punctuation and collapsing whitespace. Original text is never mutated.
    """
    if not text:
        return ""
    # Unicode NFKC normalization
    normalized = unicodedata.normalize('NFKC', text)
    # Strip symbols and punctuation (Unicode categories starting with P or S), preserving letters, marks, numbers
    cleaned = ''.join(' ' if unicodedata.category(c).startswith(('P', 'S')) else c for c in normalized.lower())
    return ' '.join(cleaned.split())

def _get_sentence_transformer():
    global _TRANSFORMER_MODEL, _TRANSFORMER_INITIALIZED
    if _TRANSFORMER_INITIALIZED:
        return _TRANSFORMER_MODEL

    _TRANSFORMER_INITIALIZED = True
    if getattr(settings, 'USE_SENTENCE_TRANSFORMERS', False):
        try:
            from sentence_transformers import SentenceTransformer
            model_name = getattr(settings, 'TRANSFORMER_MODEL_NAME', 'all-MiniLM-L6-v2')
            _TRANSFORMER_MODEL = SentenceTransformer(model_name)
        except Exception as e:
            import logging
            logging.getLogger('augis.intelligence').warning(
                f"SentenceTransformer not available or model load deferred: {e}. Falling back to TF-IDF."
            )
            _TRANSFORMER_MODEL = None

    return _TRANSFORMER_MODEL

def compute_similarity(text1, text2):
    """
    Computes semantic text similarity between two descriptions:
    1. Tries SentenceTransformer dense vector cosine similarity if available.
    2. Falls back to Unicode-aware Scikit-Learn TF-IDF (word + char_wb blend) cosine similarity.
    3. Graceful Jaccard word-set fallback.
    Returns: (similarity_score: float in [0.0, 1.0], method: str)
    """
    clean1 = normalize_text(text1)
    clean2 = normalize_text(text2)

    if not clean1 or not clean2:
        return 0.0, 'empty_text'

    if clean1 == clean2:
        return 1.0, 'exact_match'

    # 1. Try Transformer Model if available
    model = _get_sentence_transformer()
    if model is not None:
        try:
            embeddings = model.encode([clean1, clean2])
            sim = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
            return max(0.0, min(1.0, sim)), 'sentence-transformers/all-MiniLM-L6-v2'
        except Exception:
            pass

    # 2. Unicode-aware Scikit-Learn TF-IDF Fallback (word + char_wb blend)
    try:
        vw = TfidfVectorizer(token_pattern=r'(?u)\S+', ngram_range=(1, 2))
        vc = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
        sw = float(cosine_similarity(vw.fit_transform([clean1, clean2]))[0, 1])
        sc = float(cosine_similarity(vc.fit_transform([clean1, clean2]))[0, 1])
        sim = 0.5 * sw + 0.5 * sc
        return max(0.0, min(1.0, round(sim, 4))), 'scikit-learn-tfidf-unicode-hybrid'
    except Exception:
        # 3. Jaccard word set fallback if vocabulary is too sparse
        words1 = set(clean1.split())
        words2 = set(clean2.split())
        if not words1 or not words2:
            return 0.0, 'empty_words'
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard = len(intersection) / len(union) if union else 0.0
        return jaccard, 'jaccard_fallback'

def extract_shared_keywords(text1, text2, top_n=5):
    """
    Extracts salient shared keywords across two descriptions, respecting Unicode.
    """
    clean1 = set(normalize_text(text1).split())
    clean2 = set(normalize_text(text2).split())

    stopwords = {
        'the', 'and', 'for', 'are', 'was', 'this', 'that', 'with', 'from',
        'has', 'have', 'been', 'which', 'about', 'under', 'their', 'there',
        'complaint', 'grievance', 'aicte', 'institution', 'college', 'regarding'
    }

    shared = [w for w in (clean1 & clean2) if len(w) > 2 and w not in stopwords]
    return shared[:top_n]
