from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import Product, get_db


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    keywords: str = Field(default="", max_length=2000)
    price: str = Field(default="", max_length=100)
    selling_points: str = Field(default="", max_length=5000)
    custom_script: str = Field(default="", max_length=5000)
    product_link: str = Field(default="", max_length=500)


router = APIRouter()


@router.get("/api/products")
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@router.post("/api/products")
def create_product(prod: ProductCreate, db: Session = Depends(get_db)):
    db_prod = Product(**prod.model_dump())
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    return db_prod


@router.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(Product).filter(Product.id == product_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_prod)
    db.commit()
    return {"status": "deleted"}
