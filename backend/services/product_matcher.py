import re
from typing import Optional, List
from sqlalchemy.orm import Session
from database import Product

class ProductMatcher:
    def __init__(self, db: Session):
        self.db = db

    def match_comment(self, comment: str) -> Optional[Product]:
        """
        Finds best matching product based on comment text keywords.
        """
        products = self.db.query(Product).all()
        if not products:
            return None

        comment_lower = comment.lower()

        # Exact keyword search
        for product in products:
            if not product.keywords:
                continue
            keywords = [k.strip().lower() for k in product.keywords.split(",") if k.strip()]
            for kw in keywords:
                if kw and kw in comment_lower:
                    return product
                
            # Also check product name match
            if product.name.lower() in comment_lower:
                return product

        return None
