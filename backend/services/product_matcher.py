import re
import unicodedata
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from database import Product

def strip_accents(text: str) -> str:
    """Removes Vietnamese accents for accent-insensitive comparison."""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.replace('đ', 'd').replace('Đ', 'D').lower()

class ProductMatcher:
    def __init__(self, db: Session, score_threshold: int = 160):
        self.db = db
        self.score_threshold = score_threshold

    def match_comment(self, comment: str) -> Tuple[Optional[Product], int]:
        """
        Deterministic product scoring algorithm matching app-64 specification.
        - Exact product-name match: 1000 points.
        - Single token matches: +50 points per token.
        - 2-word phrase matches: +100 points per phrase.
        - Returns (best_matching_product, highest_score)
        """
        products = self.db.query(Product).all()
        if not products or not comment.strip():
            return None, 0

        comment_norm = strip_accents(comment)
        comment_tokens = set(re.findall(r'\w+', comment_norm))

        best_product = None
        highest_score = 0

        for product in products:
            score = 0
            prod_name_norm = strip_accents(product.name)
            keywords_norm = strip_accents(product.keywords or "")
            selling_norm = strip_accents(product.selling_points or "")

            # Rule 1: Exact product name inclusion = 1000 points
            if prod_name_norm and prod_name_norm in comment_norm:
                score += 1000

            # Rule 2: Check declared keywords (+150 points for keyword match)
            if keywords_norm:
                kw_list = [k.strip() for k in keywords_norm.split(",") if k.strip()]
                for kw in kw_list:
                    if kw in comment_norm:
                        score += 150

            # Rule 3: Single token overlap (+40 points per token)
            prod_tokens = set(re.findall(r'\w+', f"{prod_name_norm} {selling_norm}"))
            common_tokens = comment_tokens.intersection(prod_tokens)
            score += len(common_tokens) * 40

            # Rule 4: 2-word bigram phrase overlap (+80 points per phrase match)
            words = comment_norm.split()
            if len(words) >= 2:
                for i in range(len(words) - 1):
                    phrase = f"{words[i]} {words[i+1]}"
                    if phrase in prod_name_norm or phrase in selling_norm:
                        score += 80

            if score > highest_score:
                highest_score = score
                best_product = product

        # Score threshold rule: Minimum 160 points required to enrich prompt
        if highest_score >= self.score_threshold and best_product:
            return best_product, highest_score

        return None, highest_score
