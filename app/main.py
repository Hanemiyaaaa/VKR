from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, APIRouter
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import (
    File as FileModel, DataRow, Correction, CorrectionLog,
    Account, InitialBalance, Transaction, Loan, Deposit,
    CapitalComponent, ExchangeRate, Bond, RiskCategory,
    FileRegistry, ETLLog
)
import pandas as pd
import datetime
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from decimal import Decimal
from sqlalchemy import func
import requests
import xml.etree.ElementTree as ET
import os

app = FastAPI()
Base.metadata.create_all(bind=engine)

UPLOAD_FOLDER = "/app/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

api_router = APIRouter(prefix="/api")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API ЭНДПОИНТЫ 

@api_router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        business_date_parsed = datetime.datetime.strptime(business_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Неверный формат даты. Используй YYYY-MM-DD"}
    upload_date = datetime.datetime.now()
    file_record = FileModel(
        filename=file.filename,
        business_date=business_date_parsed,
        user_name=user_name,
        upload_date=upload_date,
        data_type="main"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    file.file.seek(0)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="main",
        status="pending"
    )
    db.add(registry)
    db.commit()

    chunk_size = 100_000
    try:
        for chunk in pd.read_csv(file_path, chunksize=chunk_size, dtype=str):
            required_columns = ["account_id", "client_type", "product_type", "balance", "currency", "risk_flag"]
            if not all(col in chunk.columns for col in required_columns):
                return {"error": f"Неверный формат CSV. Ожидаются колонки: {required_columns}"}
            chunk = chunk.where(pd.notnull(chunk), None)
            rows_to_add = [
                DataRow(
                    file_id=file_record.id,
                    account_id=row["account_id"],
                    client_type=row["client_type"],
                    product_type=row["product_type"],
                    balance=Decimal(str(row["balance"])) if row["balance"] is not None else Decimal(0),
                    currency=row["currency"] if row["currency"] is not None else "RUB",
                    risk_flag=row["risk_flag"] if row["risk_flag"] is not None else "LOW",
                    version="original"
                )
                for _, row in chunk.iterrows()
            ]
            db.bulk_save_objects(rows_to_add)
            db.commit()
    except Exception as e:
        return {"error": f"Ошибка чтения или записи CSV: {str(e)}"}
    return {"message": "File uploaded successfully", "file_id": file_record.id}

@api_router.get("/files")
def get_files(db: Session = Depends(get_db)):
    files = db.query(FileModel).all()
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "business_date": f.business_date,
            "user_name": f.user_name,
            "upload_date": f.upload_date,
            "data_type": f.data_type
        }
        for f in files
    ]

@api_router.get("/files/filter")
def filter_files(
    business_date: str = None,
    user_name: str = None,
    upload_date: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(FileModel)
    if business_date:
        try:
            date_parsed = datetime.datetime.strptime(business_date, "%Y-%m-%d").date()
            query = query.filter(FileModel.business_date == date_parsed)
        except:
            return JSONResponse(status_code=400, content={"error": "Invalid business_date format"})
    if user_name:
        query = query.filter(FileModel.user_name == user_name)
    if upload_date:
        try:
            date_parsed = datetime.datetime.strptime(upload_date, "%Y-%m-%d").date()
            query = query.filter(FileModel.upload_date == date_parsed)
        except:
            return JSONResponse(status_code=400, content={"error": "Invalid upload_date format"})
    files = query.all()
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "business_date": f.business_date,
            "user_name": f.user_name,
            "upload_date": f.upload_date,
            "data_type": f.data_type
        }
        for f in files
    ]

@api_router.get("/file-data/{file_id}")
def get_file_data(
    file_id: int,
    version: str = "original",
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file_record:
        raise HTTPException(404, "Файл не найден")
    data_type = file_record.data_type
    if not data_type:
        raise HTTPException(400, "У файла не указан тип данных")

    models_map = {
        "main": DataRow,
        "accounts": Account,
        "initial_balances": InitialBalance,
        "transactions": Transaction,
        "loans": Loan,
        "deposits": Deposit,
        "capital": CapitalComponent,
        "exchange_rates": ExchangeRate,
        "bonds": Bond,
    }
    model = models_map.get(data_type)
    if not model:
        raise HTTPException(400, f"Неизвестный тип данных: {data_type}")

    query = db.query(model)
    if hasattr(model, "version") and hasattr(model, "file_id"):
        query = query.filter(model.version == version, model.file_id == file_id)
    elif hasattr(model, "file_id"):
        query = query.filter(model.file_id == file_id)

    rows = query.offset(offset).limit(limit).all()
    result = []
    for row in rows:
        d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
        result.append(d)
    return result

# ЗАГРУЗКА ФАЙЛОВ БЕЗ ЗАПИСИ В ФИНАЛЬНЫЕ ТАБЛИЦЫ
# Все эндпоинты ниже только сохраняют файл на диск и регистрируют в file_registry.

@api_router.post("/upload-accounts")
def upload_accounts(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    file_record = FileModel(
        filename=file.filename,
        business_date=datetime.datetime.strptime(business_date, "%Y-%m-%d").date(),
        user_name=user_name,
        upload_date=datetime.datetime.now().date(),
        data_type="accounts"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="accounts",
        status="pending"
    )
    db.add(registry)
    db.commit()

    return {"message": "File uploaded and registered for ETL", "file_id": file_record.id}

@api_router.post("/upload-initial-balances")
def upload_initial_balances(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    file_record = FileModel(
        filename=file.filename,
        business_date=datetime.datetime.strptime(business_date, "%Y-%m-%d").date(),
        user_name=user_name,
        upload_date=datetime.datetime.now().date(),
        data_type="initial_balances"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="initial_balances",
        status="pending"
    )
    db.add(registry)
    db.commit()

    return {"message": "File uploaded and registered for ETL", "file_id": file_record.id}

@api_router.post("/upload-transactions")
def upload_transactions(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    file_record = FileModel(
        filename=file.filename,
        business_date=datetime.datetime.strptime(business_date, "%Y-%m-%d").date(),
        user_name=user_name,
        upload_date=datetime.datetime.now().date(),
        data_type="transactions"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="transactions",
        status="pending"
    )
    db.add(registry)
    db.commit()

    return {"message": "File uploaded and registered for ETL", "file_id": file_record.id}

@api_router.post("/upload-loans")
def upload_loans(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    file_record = FileModel(
        filename=file.filename,
        business_date=datetime.datetime.strptime(business_date, "%Y-%m-%d").date(),
        user_name=user_name,
        upload_date=datetime.datetime.now().date(),
        data_type="loans"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="loans",
        status="pending"
    )
    db.add(registry)
    db.commit()

    return {"message": "File uploaded and registered for ETL", "file_id": file_record.id}

@api_router.post("/upload-deposits")
def upload_deposits(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    file_record = FileModel(
        filename=file.filename,
        business_date=datetime.datetime.strptime(business_date, "%Y-%m-%d").date(),
        user_name=user_name,
        upload_date=datetime.datetime.now().date(),
        data_type="deposits"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="deposits",
        status="pending"
    )
    db.add(registry)
    db.commit()

    return {"message": "File uploaded and registered for ETL", "file_id": file_record.id}

@api_router.post("/upload-capital")
def upload_capital(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    file_record = FileModel(
        filename=file.filename,
        business_date=datetime.datetime.strptime(business_date, "%Y-%m-%d").date(),
        user_name=user_name,
        upload_date=datetime.datetime.now().date(),
        data_type="capital"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="capital",
        status="pending"
    )
    db.add(registry)
    db.commit()

    return {"message": "File uploaded and registered for ETL", "file_id": file_record.id}

@api_router.post("/upload-exchange-rates")
def upload_exchange_rates(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    file_record = FileModel(
        filename=file.filename,
        business_date=datetime.datetime.strptime(business_date, "%Y-%m-%d").date(),
        user_name=user_name,
        upload_date=datetime.datetime.now().date(),
        data_type="exchange_rates"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="exchange_rates",
        status="pending"
    )
    db.add(registry)
    db.commit()

    return {"message": "File uploaded and registered for ETL", "file_id": file_record.id}

@api_router.post("/upload-bonds")
def upload_bonds(
    file: UploadFile = File(...),
    business_date: str = Form(...),
    user_name: str = Form(...),
    db: Session = Depends(get_db)
):
    file_record = FileModel(
        filename=file.filename,
        business_date=datetime.datetime.strptime(business_date, "%Y-%m-%d").date(),
        user_name=user_name,
        upload_date=datetime.datetime.now().date(),
        data_type="bonds"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    file_path = os.path.join(UPLOAD_FOLDER, f"{file_record.id}_{file.filename}")
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    registry = FileRegistry(
        file_id=file_record.id,
        file_path=file_path,
        data_type="bonds",
        status="pending"
    )
    db.add(registry)
    db.commit()

    return {"message": "File uploaded and registered for ETL", "file_id": file_record.id}

@api_router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()

@api_router.get("/transactions")
def get_transactions(
    from_account: str = None,
    to_account: str = None,
    start_date: str = None,
    end_date: str = None,
    version: str = "original",
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.version == version)
    if from_account:
        acc = db.query(Account).filter(Account.account_number == from_account).first()
        if acc:
            query = query.filter(Transaction.from_account_id == acc.id)
    if to_account:
        acc = db.query(Account).filter(Account.account_number == to_account).first()
        if acc:
            query = query.filter(Transaction.to_account_id == acc.id)
    if start_date:
        query = query.filter(Transaction.transaction_date >= datetime.datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(Transaction.transaction_date <= datetime.datetime.strptime(end_date, "%Y-%m-%d").date())
    return query.order_by(Transaction.transaction_date).all()

@api_router.get("/balances")
def get_balances(as_of_date: str, db: Session = Depends(get_db)):
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    accounts = db.query(Account).all()
    result = []
    for acc in accounts:
        ib = db.query(InitialBalance).filter(
            InitialBalance.account_id == acc.id,
            InitialBalance.version == "original",
            InitialBalance.date <= date_obj
        ).order_by(InitialBalance.date.desc()).first()
        balance = ib.balance if ib else Decimal(0)
        outgoing = db.query(Transaction).filter(
            Transaction.from_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        incoming = db.query(Transaction).filter(
            Transaction.to_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        balance = balance - Decimal(outgoing) + Decimal(incoming)
        result.append({
            "account_number": acc.account_number,
            "name": acc.name,
            "balance": float(balance),
            "currency": acc.currency
        })
    return result

@api_router.get("/account/{account_number}/history")
def account_history(account_number: str, from_date: str = None, to_date: str = None, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.account_number == account_number).first()
    if not acc:
        raise HTTPException(404, "Счёт не найден")
    query = db.query(Transaction).filter(
        (Transaction.from_account_id == acc.id) | (Transaction.to_account_id == acc.id),
        Transaction.version == "original"
    )
    if from_date:
        query = query.filter(Transaction.transaction_date >= datetime.datetime.strptime(from_date, "%Y-%m-%d").date())
    if to_date:
        query = query.filter(Transaction.transaction_date <= datetime.datetime.strptime(to_date, "%Y-%m-%d").date())
    transactions = query.order_by(Transaction.transaction_date).all()
    first_date = transactions[0].transaction_date if transactions else datetime.date.today()
    ib = db.query(InitialBalance).filter(
        InitialBalance.account_id == acc.id,
        InitialBalance.version == "original",
        InitialBalance.date <= first_date
    ).order_by(InitialBalance.date.desc()).first()
    running_balance = ib.balance if ib else Decimal(0)
    history = []
    for tx in transactions:
        if tx.from_account_id == acc.id:
            delta = -tx.amount
            opposite = db.query(Account).filter(Account.id == tx.to_account_id).first().account_number
        else:
            delta = tx.amount
            opposite = db.query(Account).filter(Account.id == tx.from_account_id).first().account_number
        running_balance += delta
        history.append({
            "date": tx.transaction_date,
            "description": tx.description,
            "counterparty_account": opposite,
            "amount": float(tx.amount),
            "delta": float(delta),
            "balance_after": float(running_balance)
        })
    return {
        "account": account_number,
        "name": acc.name,
        "currency": acc.currency,
        "history": history
    }

@api_router.get("/loans")
def get_loans(version: str = "original", db: Session = Depends(get_db)):
    return db.query(Loan).filter(Loan.version == version).all()

@api_router.get("/loan-profit/{loan_id}")
def loan_profit(loan_id: int, as_of_date: str = None, db: Session = Depends(get_db)):
    loan = db.query(Loan).filter(Loan.id == loan_id, Loan.version == "original").first()
    if not loan:
        raise HTTPException(404, "Кредит не найден")
    if not as_of_date:
        as_of_date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    days = (date_obj - loan.start_date).days
    if days < 0:
        profit = 0
    else:
        profit = float(loan.remaining_balance) * (float(loan.interest_rate) / 100) * (days / 365)
    return {"loan_id": loan_id, "profit": profit, "currency": loan.currency}

@api_router.get("/deposits")
def get_deposits(version: str = "original", db: Session = Depends(get_db)):
    return db.query(Deposit).filter(Deposit.version == version).all()

@api_router.get("/deposit-cost/{deposit_id}")
def deposit_cost(deposit_id: int, as_of_date: str = None, db: Session = Depends(get_db)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.version == "original").first()
    if not deposit:
        raise HTTPException(404, "Депозит не найден")
    if not as_of_date:
        as_of_date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    days = (date_obj - deposit.start_date).days
    if days < 0:
        cost = 0
    else:
        cost = float(deposit.amount) * (float(deposit.interest_rate) / 100) * (days / 365)
    return {"deposit_id": deposit_id, "cost": cost, "currency": deposit.currency}

@api_router.get("/regulatory-capital")
def regulatory_capital(as_of_date: str = None, db: Session = Depends(get_db)):
    if not as_of_date:
        as_of_date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    share_capital = db.query(CapitalComponent).filter(
        CapitalComponent.component_type == "tier1_share_capital",
        CapitalComponent.version == "original",
        CapitalComponent.as_of_date <= date_obj
    ).order_by(CapitalComponent.as_of_date.desc()).first()
    retained_earnings = db.query(CapitalComponent).filter(
        CapitalComponent.component_type == "tier1_retained_earnings",
        CapitalComponent.version == "original",
        CapitalComponent.as_of_date <= date_obj
    ).order_by(CapitalComponent.as_of_date.desc()).first()
    share_premium = db.query(CapitalComponent).filter(
        CapitalComponent.component_type == "tier1_share_premium",
        CapitalComponent.version == "original",
        CapitalComponent.as_of_date <= date_obj
    ).order_by(CapitalComponent.as_of_date.desc()).first()
    sub_debt = db.query(CapitalComponent).filter(
        CapitalComponent.component_type == "tier2_subordinated_debt",
        CapitalComponent.version == "original",
        CapitalComponent.as_of_date <= date_obj
    ).order_by(CapitalComponent.as_of_date.desc()).first()
    losses = db.query(CapitalComponent).filter(
        CapitalComponent.component_type == "deduction_uncovered_losses",
        CapitalComponent.version == "original",
        CapitalComponent.as_of_date <= date_obj
    ).order_by(CapitalComponent.as_of_date.desc()).first()
    treasury = db.query(CapitalComponent).filter(
        CapitalComponent.component_type == "deduction_treasury_shares",
        CapitalComponent.version == "original",
        CapitalComponent.as_of_date <= date_obj
    ).order_by(CapitalComponent.as_of_date.desc()).first()
    tier1 = (share_capital.value if share_capital else 0) + (retained_earnings.value if retained_earnings else 0) + (share_premium.value if share_premium else 0)
    tier2 = sub_debt.value if sub_debt else 0
    deductions = (losses.value if losses else 0) + (treasury.value if treasury else 0)
    total_capital = tier1 + tier2 - deductions
    return {"tier1": float(tier1), "tier2": float(tier2), "deductions": float(deductions), "total": float(total_capital)}

@api_router.get("/assets")
def get_assets(as_of_date: str = None, db: Session = Depends(get_db)):
    if not as_of_date:
        as_of_date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    loans = db.query(Loan).filter(
        Loan.version == "original",
        Loan.start_date <= date_obj,
        Loan.end_date >= date_obj,
        Loan.status == "active"
    ).all()
    loans_data = []
    total_loans_amount = 0
    total_loans_risk_weighted = 0
    for loan in loans:
        risk_weight = 1.0 if loan.risk_category == RiskCategory.unsecured else 0.0
        amount = float(loan.remaining_balance)
        total_loans_amount += amount
        total_loans_risk_weighted += amount * risk_weight
        loans_data.append({
            "type": "Кредит",
            "account_number": db.query(Account).filter(Account.id == loan.loan_account_id).first().account_number,
            "amount": amount,
            "risk_category": loan.risk_category.value if loan.risk_category else "не указана",
            "risk_weight": risk_weight,
            "risk_weighted_amount": amount * risk_weight,
            "start_date": loan.start_date,
            "end_date": loan.end_date
        })
    bonds = db.query(Bond).filter(
        Bond.version == "original",
        Bond.purchase_date <= date_obj,
        Bond.maturity_date >= date_obj
    ).all()
    bonds_data = []
    total_bonds_amount = 0
    total_bonds_risk_weighted = 0
    for bond in bonds:
        risk_weight = 1.0 if bond.risk_category == RiskCategory.unsecured else 0.0
        amount = float(bond.face_value)
        total_bonds_amount += amount
        total_bonds_risk_weighted += amount * risk_weight
        bonds_data.append({
            "type": "Облигация",
            "issuer": bond.issuer,
            "face_value": amount,
            "risk_category": bond.risk_category.value,
            "risk_weight": risk_weight,
            "risk_weighted_amount": amount * risk_weight,
            "purchase_date": bond.purchase_date,
            "maturity_date": bond.maturity_date,
            "coupon_rate": float(bond.coupon_rate)
        })
    total_assets = total_loans_amount + total_bonds_amount
    total_risk_weighted_assets = total_loans_risk_weighted + total_bonds_risk_weighted
    return {
        "as_of_date": as_of_date,
        "loans": loans_data,
        "bonds": bonds_data,
        "summary": {
            "total_loans_amount": total_loans_amount,
            "total_bonds_amount": total_bonds_amount,
            "total_assets": total_assets,
            "total_risk_weighted_assets": total_risk_weighted_assets
        }
    }

@api_router.get("/liabilities")
def get_liabilities(as_of_date: str = None, db: Session = Depends(get_db)):
    if not as_of_date:
        as_of_date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    settlement_accounts = db.query(Account).filter(Account.account_type == "settlement").all()
    settlement_balance = 0
    for acc in settlement_accounts:
        ib = db.query(InitialBalance).filter(
            InitialBalance.account_id == acc.id,
            InitialBalance.version == "original",
            InitialBalance.date <= date_obj
        ).order_by(InitialBalance.date.desc()).first()
        balance = ib.balance if ib else Decimal(0)
        outgoing = db.query(Transaction).filter(
            Transaction.from_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        incoming = db.query(Transaction).filter(
            Transaction.to_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        balance = balance - Decimal(outgoing) + Decimal(incoming)
        settlement_balance += float(balance)
    deposits = db.query(Deposit).filter(
        Deposit.version == "original",
        Deposit.start_date <= date_obj,
        Deposit.end_date >= date_obj
    ).all()
    deposit_by_term = {"on_demand": 0, "30_days": 0, "1_year": 0}
    for dep in deposits:
        if dep.term_type == "on_demand":
            deposit_by_term["on_demand"] += float(dep.amount)
        elif dep.term_type == "30_days":
            deposit_by_term["30_days"] += float(dep.amount)
        elif dep.term_type == "1_year":
            deposit_by_term["1_year"] += float(dep.amount)
    return {
        "as_of_date": as_of_date,
        "settlement_accounts_balance": settlement_balance,
        "deposits": deposit_by_term,
        "total_liabilities": settlement_balance + sum(deposit_by_term.values())
    }

@api_router.get("/convert-currency")
def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str = "RUB",
    date: str = None,
    source: str = "db",
    db: Session = Depends(get_db)
):
    if not date:
        date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    
    if from_currency == to_currency:
        return {"converted_amount": amount, "source": source}
    
    if source == "api":
        try:
            date_parts = date.split('-')
            formatted_date = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
            api_url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={formatted_date}"
            resp = requests.get(api_url, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            rates = {"RUB": 1.0}
            for valute in root.findall("Valute"):
                char_code = valute.find("CharCode").text
                value = valute.find("Value").text.replace(',', '.')
                nominal = valute.find("Nominal").text
                rates[char_code] = float(value) / float(nominal)
            rate_from = rates.get(from_currency)
            if rate_from is None:
                raise HTTPException(404, f"Валюта {from_currency} не найдена в XML ЦБ")
            if to_currency == "RUB":
                converted = amount * rate_from
                rate_used = rate_from
            else:
                rate_to = rates.get(to_currency)
                if rate_to is None:
                    raise HTTPException(404, f"Валюта {to_currency} не найдена в XML ЦБ")
                converted = amount * (rate_from / rate_to)
                rate_used = rate_from
        except Exception as e:
            raise HTTPException(503, f"Ошибка при получении курсов из ЦБ РФ: {str(e)}")
    else:
        rate_from = db.query(ExchangeRate).filter(
            ExchangeRate.currency == from_currency,
            ExchangeRate.date <= date_obj,
            ExchangeRate.version == "original"
        ).order_by(ExchangeRate.date.desc()).first()
        if not rate_from:
            raise HTTPException(404, f"Курс для {from_currency} на {date} не найден в БД")
        if to_currency == "RUB":
            converted = amount * float(rate_from.rate_to_rub)
            rate_used = float(rate_from.rate_to_rub)
        else:
            rate_to = db.query(ExchangeRate).filter(
                ExchangeRate.currency == to_currency,
                ExchangeRate.date <= date_obj,
                ExchangeRate.version == "original"
            ).order_by(ExchangeRate.date.desc()).first()
            if not rate_to:
                raise HTTPException(404, f"Курс для {to_currency} на {date} не найден в БД")
            converted = amount * (float(rate_from.rate_to_rub) / float(rate_to.rate_to_rub))
            rate_used = float(rate_from.rate_to_rub)
    
    return {
        "original_amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "converted_amount": converted,
        "rate_used": rate_used,
        "source": source
    }

@api_router.post("/apply-loan-interest/{loan_id}")
def apply_loan_interest(
    loan_id: int,
    as_of_date: str = Form(...),
    db: Session = Depends(get_db)
):
    loan = db.query(Loan).filter(Loan.id == loan_id, Loan.version == "original").first()
    if not loan:
        raise HTTPException(404, "Кредит не найден")
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    days = (date_obj - loan.start_date).days
    if days < 0:
        return {"message": "Дата раньше начала кредита", "interest": 0}
    interest = float(loan.remaining_balance) * (float(loan.interest_rate) / 100) * (days / 365)
    if interest <= 0:
        return {"message": "Проценты не начислены", "interest": 0}
    income_account = db.query(Account).filter(Account.account_number == "9991").first()
    if not income_account:
        raise HTTPException(500, "Не найден счёт процентных доходов (9991). Загрузите счета с номером 9991.")
    tx = Transaction(
        file_id=loan.file_id,
        version="original",
        transaction_date=date_obj,
        from_account_id=loan.loan_account_id,
        to_account_id=income_account.id,
        amount=Decimal(str(interest)),
        currency=loan.currency,
        description=f"Начисление процентов по кредиту {loan_id} за период до {as_of_date}"
    )
    db.add(tx)
    db.commit()
    return {"message": "Проценты по кредиту начислены", "interest": interest, "transaction_id": tx.id}

@api_router.post("/apply-deposit-interest/{deposit_id}")
def apply_deposit_interest(
    deposit_id: int,
    as_of_date: str = Form(...),
    db: Session = Depends(get_db)
):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.version == "original").first()
    if not deposit:
        raise HTTPException(404, "Депозит не найден")
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    days = (date_obj - deposit.start_date).days
    if days < 0:
        return {"message": "Дата раньше начала депозита", "interest": 0}
    interest = float(deposit.amount) * (float(deposit.interest_rate) / 100) * (days / 365)
    if interest <= 0:
        return {"message": "Проценты не начислены", "interest": 0}
    expense_account = db.query(Account).filter(Account.account_number == "9992").first()
    if not expense_account:
        raise HTTPException(500, "Не найден счёт процентных расходов (9992). Загрузите счета с номером 9992.")
    tx = Transaction(
        file_id=deposit.file_id,
        version="original",
        transaction_date=date_obj,
        from_account_id=expense_account.id,
        to_account_id=deposit.deposit_account_id,
        amount=Decimal(str(interest)),
        currency=deposit.currency,
        description=f"Начисление процентов по депозиту {deposit_id} за период до {as_of_date}"
    )
    db.add(tx)
    db.commit()
    return {"message": "Проценты по депозиту начислены", "interest": interest, "transaction_id": tx.id}

@api_router.get("/liquidity")
def get_liquidity(as_of_date: str = None, db: Session = Depends(get_db)):
    if not as_of_date:
        as_of_date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    loans = db.query(Loan).filter(
        Loan.version == "original",
        Loan.status == "active",
        Loan.start_date <= date_obj,
        Loan.end_date >= date_obj
    ).all()
    loan_details = []
    for loan in loans:
        days_to_maturity = (loan.end_date - date_obj).days
        loan_details.append({
            "type": "Кредит",
            "account_number": db.query(Account).filter(Account.id == loan.loan_account_id).first().account_number,
            "amount": float(loan.remaining_balance),
            "start_date": loan.start_date.isoformat(),
            "end_date": loan.end_date.isoformat(),
            "days_to_maturity": days_to_maturity
        })
    deposits = db.query(Deposit).filter(
        Deposit.version == "original",
        Deposit.start_date <= date_obj,
        Deposit.end_date >= date_obj
    ).all()
    deposit_details = []
    for dep in deposits:
        days_to_maturity = (dep.end_date - date_obj).days
        deposit_details.append({
            "type": "Депозит",
            "account_number": db.query(Account).filter(Account.id == dep.deposit_account_id).first().account_number,
            "amount": float(dep.amount),
            "start_date": dep.start_date.isoformat(),
            "end_date": dep.end_date.isoformat(),
            "days_to_maturity": days_to_maturity,
            "term_type": dep.term_type
        })
    settlement_accounts = db.query(Account).filter(Account.account_type == "settlement").all()
    settlement_balance_total = 0.0
    for acc in settlement_accounts:
        ib = db.query(InitialBalance).filter(
            InitialBalance.account_id == acc.id,
            InitialBalance.version == "original",
            InitialBalance.date <= date_obj
        ).order_by(InitialBalance.date.desc()).first()
        balance = ib.balance if ib else Decimal(0)
        outgoing = db.query(Transaction).filter(
            Transaction.from_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        incoming = db.query(Transaction).filter(
            Transaction.to_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        balance = balance - Decimal(outgoing) + Decimal(incoming)
        settlement_balance_total += float(balance)
    buckets = {
        "on_demand": (0, 0),
        "0-30_days": (1, 30),
        "31-90_days": (31, 90),
        "91-365_days": (91, 365),
        "over_365_days": (366, 10**6)
    }
    assets_by_bucket = {key: 0.0 for key in buckets}
    for loan in loans:
        days = (loan.end_date - date_obj).days
        for bucket, (low, high) in buckets.items():
            if low <= days <= high:
                assets_by_bucket[bucket] += float(loan.remaining_balance)
                break
    liabilities_by_bucket = {key: 0.0 for key in buckets}
    for dep in deposits:
        days = (dep.end_date - date_obj).days
        for bucket, (low, high) in buckets.items():
            if low <= days <= high:
                liabilities_by_bucket[bucket] += float(dep.amount)
                break
    liabilities_by_bucket["on_demand"] += settlement_balance_total
    gap_by_bucket = {k: assets_by_bucket[k] - liabilities_by_bucket[k] for k in buckets}
    return {
        "as_of_date": as_of_date,
        "summary": {
            "assets_by_bucket": assets_by_bucket,
            "liabilities_by_bucket": liabilities_by_bucket,
            "gap_by_bucket": gap_by_bucket
        },
        "details": {
            "loans": loan_details,
            "deposits": deposit_details,
            "settlement_accounts_balance": settlement_balance_total
        }
    }

# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПРОВЕРКИ УСЛОВИЙ (корректировки)
def check_condition(row, rule):
    value = str(row.get(rule.condition_field, ""))
    if rule.operator == "equals":
        return value == rule.condition_value
    if rule.operator == "contains":
        return rule.condition_value in value
    if rule.operator == "upper_equals":
        return value.upper() == rule.condition_value.upper()
    return False

# СОЗДАНИЕ КОРРЕКТИРОВКИ (ПРАВИЛА)
@api_router.post("/corrections")
def create_correction(
    file_id: int = Form(...),
    field_to_update: str = Form(...),
    new_value: str = Form(...),
    condition_field: str = Form(...),
    operator: str = Form(...),
    condition_value: str = Form(...),
    db: Session = Depends(get_db)
):
    db.query(Correction).filter(Correction.file_id == file_id).delete()
    correction = Correction(
        file_id=file_id,
        field_to_update=field_to_update,
        new_value=new_value,
        condition_field=condition_field,
        operator=operator,
        condition_value=condition_value
    )
    db.add(correction)
    db.commit()
    return {"message": "Correction created (old rules removed)"}

@api_router.post("/apply-corrections/{file_id}")
def apply_corrections(
    file_id: int,
    applied_by: str = Form(...),
    db: Session = Depends(get_db)
):
    db.query(DataRow).filter(
        DataRow.file_id == file_id,
        DataRow.version == "corrected"
    ).delete(synchronize_session=False)
    db.commit()
    rows = db.query(DataRow).filter(
        DataRow.file_id == file_id,
        DataRow.version == "original"
    ).all()
    rules = db.query(Correction).filter(Correction.file_id == file_id).all()
    rows_to_add = []
    updated_count = 0
    for row in rows:
        current_dict = {
            "account_id": row.account_id,
            "client_type": row.client_type,
            "product_type": row.product_type,
            "balance": str(row.balance) if row.balance is not None else "",
            "currency": row.currency,
            "risk_flag": row.risk_flag
        }
        new_dict = current_dict.copy()
        row_updated = False
        for rule in rules:
            if check_condition(new_dict, rule):
                field = rule.field_to_update
                old_val = str(new_dict.get(field, ""))
                new_val = rule.new_value
                if old_val != new_val:
                    log = CorrectionLog(
                        correction_id=rule.id,
                        file_id=file_id,
                        row_id=row.id,
                        field_name=field,
                        old_value=old_val,
                        new_value=new_val,
                        applied_by=applied_by
                    )
                    db.add(log)
                    new_dict[field] = new_val
                    row_updated = True
        if row_updated:
            updated_count += 1
        balance_val = new_dict["balance"]
        if balance_val == "" or balance_val is None:
            balance_val = "0"
        try:
            balance_decimal = Decimal(str(balance_val))
        except:
            balance_decimal = Decimal("0")
        rows_to_add.append(
            DataRow(
                file_id=file_id,
                account_id=new_dict["account_id"],
                client_type=new_dict["client_type"],
                product_type=new_dict["product_type"],
                balance=balance_decimal,
                currency=new_dict["currency"],
                risk_flag=new_dict["risk_flag"],
                version="corrected"
            )
        )
    if rows_to_add:
        db.bulk_save_objects(rows_to_add)
        db.commit()
    return {
        "message": "Corrections applied",
        "updated_rows": updated_count
    }

@api_router.get("/correction-logs")
def get_correction_logs(file_id: int = None, db: Session = Depends(get_db)):
    query = db.query(CorrectionLog).order_by(CorrectionLog.applied_at.desc())
    if file_id:
        query = query.filter(CorrectionLog.file_id == file_id)
    logs = query.all()
    return [
        {
            "id": log.id,
            "file_id": log.file_id,
            "row_id": log.row_id,
            "field_name": log.field_name,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "applied_by": log.applied_by,
            "applied_at": log.applied_at.isoformat()
        }
        for log in logs
    ]

@api_router.get("/large-risks")
def get_large_risks(as_of_date: str = None, db: Session = Depends(get_db)):
    if not as_of_date:
        as_of_date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    capital_resp = regulatory_capital(as_of_date, db)
    total_capital = capital_resp["total"]
    if total_capital == 0:
        return {
            "as_of_date": as_of_date,
            "total_capital": 0,
            "threshold_5_percent": 0,
            "large_risks": [],
            "warning": "На указанную дату капитал не рассчитан (нет данных). Загрузите компоненты капитала через CSV."
        }
    threshold = total_capital * 0.05
    loans = db.query(Loan).filter(
        Loan.version == "original",
        Loan.status == "active",
        Loan.start_date <= date_obj,
        Loan.end_date >= date_obj
    ).all()
    borrower_exposure = {}
    for loan in loans:
        acc = db.query(Account).filter(Account.id == loan.loan_account_id).first()
        if not acc:
            continue
        borrower_key = acc.account_number
        borrower_name = acc.name
        amount = float(loan.remaining_balance)
        if borrower_key not in borrower_exposure:
            borrower_exposure[borrower_key] = {
                "borrower_id": borrower_key,
                "borrower_name": borrower_name,
                "total_exposure": 0.0
            }
        borrower_exposure[borrower_key]["total_exposure"] += amount
    large_risks = []
    for borrower in borrower_exposure.values():
        if borrower["total_exposure"] > threshold:
            percent_of_capital = (borrower["total_exposure"] / total_capital) * 100
            large_risks.append({
                "borrower_id": borrower["borrower_id"],
                "borrower_name": borrower["borrower_name"],
                "total_exposure": borrower["total_exposure"],
                "percent_of_capital": percent_of_capital
            })
    large_risks.sort(key=lambda x: x["total_exposure"], reverse=True)
    return {
        "as_of_date": as_of_date,
        "total_capital": total_capital,
        "threshold_5_percent": threshold,
        "large_risks": large_risks
    }

# ПРИВЕДЕНИЕ ВСЕХ ПОКАЗАТЕЛЕЙ К ЕДИНОЙ ВАЛЮТЕ
@api_router.get("/financial-summary-in-currency")
def get_financial_summary_in_currency(
    target_currency: str = "RUB",
    as_of_date: str = None,
    source: str = "db",
    db: Session = Depends(get_db)
):
    if not as_of_date:
        as_of_date = datetime.date.today().isoformat()
    date_obj = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
    if source == "api":
        try:
            date_parts = as_of_date.split('-')
            formatted_date = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
            api_url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={formatted_date}"
            resp = requests.get(api_url, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            rate_to_rub = {"RUB": 1.0}
            for valute in root.findall("Valute"):
                char_code = valute.find("CharCode").text
                value = valute.find("Value").text.replace(',', '.')
                nominal = valute.find("Nominal").text
                rate_to_rub[char_code] = float(value) / float(nominal)
        except Exception as e:
            raise HTTPException(503, f"Не удалось получить курсы из официального XML ЦБ РФ: {str(e)}")
    else:
        rates_db = db.query(ExchangeRate).filter(
            ExchangeRate.version == "original",
            ExchangeRate.date <= date_obj
        ).all()
        rate_to_rub = {r.currency: float(r.rate_to_rub) for r in rates_db}
        rate_to_rub["RUB"] = 1.0
    if target_currency != "RUB" and target_currency not in rate_to_rub:
        raise HTTPException(404, f"Нет курса для {target_currency} на {as_of_date}")
    def convert(amount: float, from_currency: str) -> float:
        if from_currency == target_currency:
            return amount
        if from_currency not in rate_to_rub:
            return amount
        amount_rub = amount * rate_to_rub[from_currency]
        if target_currency == "RUB":
            return amount_rub
        return amount_rub / rate_to_rub[target_currency]
    accounts = db.query(Account).all()
    balances = []
    total_balance_converted = 0.0
    for acc in accounts:
        ib = db.query(InitialBalance).filter(
            InitialBalance.account_id == acc.id,
            InitialBalance.version == "original",
            InitialBalance.date <= date_obj
        ).order_by(InitialBalance.date.desc()).first()
        balance = ib.balance if ib else Decimal(0)
        outgoing = db.query(Transaction).filter(
            Transaction.from_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        incoming = db.query(Transaction).filter(
            Transaction.to_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        balance = float(balance) - float(outgoing) + float(incoming)
        balance_converted = convert(balance, acc.currency)
        total_balance_converted += balance_converted
        balances.append({
            "account_number": acc.account_number,
            "name": acc.name,
            "original_balance": balance,
            "original_currency": acc.currency,
            "balance_converted": balance_converted,
            "target_currency": target_currency
        })
    capital_components = db.query(CapitalComponent).filter(
        CapitalComponent.version == "original",
        CapitalComponent.as_of_date <= date_obj
    ).all()
    tier1_sum = 0.0
    tier2_sum = 0.0
    deductions_sum = 0.0
    for comp in capital_components:
        val = convert(float(comp.value), comp.currency)
        if comp.component_type.startswith("tier1"):
            tier1_sum += val
        elif comp.component_type == "tier2_subordinated_debt":
            tier2_sum += val
        elif comp.component_type.startswith("deduction"):
            deductions_sum += val
    total_capital_converted = tier1_sum + tier2_sum - deductions_sum
    loans = db.query(Loan).filter(
        Loan.version == "original",
        Loan.status == "active",
        Loan.start_date <= date_obj,
        Loan.end_date >= date_obj
    ).all()
    total_loans_converted = 0.0
    for loan in loans:
        total_loans_converted += convert(float(loan.remaining_balance), loan.currency)
    bonds = db.query(Bond).filter(
        Bond.version == "original",
        Bond.purchase_date <= date_obj,
        Bond.maturity_date >= date_obj
    ).all()
    total_bonds_converted = 0.0
    for bond in bonds:
        total_bonds_converted += convert(float(bond.face_value), bond.currency)
    total_assets_converted = total_loans_converted + total_bonds_converted
    settlement_accounts = db.query(Account).filter(Account.account_type == "settlement").all()
    settlement_balance_converted = 0.0
    for acc in settlement_accounts:
        ib = db.query(InitialBalance).filter(
            InitialBalance.account_id == acc.id,
            InitialBalance.version == "original",
            InitialBalance.date <= date_obj
        ).order_by(InitialBalance.date.desc()).first()
        balance = ib.balance if ib else Decimal(0)
        outgoing = db.query(Transaction).filter(
            Transaction.from_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        incoming = db.query(Transaction).filter(
            Transaction.to_account_id == acc.id,
            Transaction.version == "original",
            Transaction.transaction_date <= date_obj
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0
        balance = float(balance) - float(outgoing) + float(incoming)
        settlement_balance_converted += convert(balance, acc.currency)
    deposits = db.query(Deposit).filter(
        Deposit.version == "original",
        Deposit.start_date <= date_obj,
        Deposit.end_date >= date_obj
    ).all()
    deposit_by_term_converted = {"on_demand": 0.0, "30_days": 0.0, "1_year": 0.0}
    for dep in deposits:
        amount_converted = convert(float(dep.amount), dep.currency)
        if dep.term_type == "on_demand":
            deposit_by_term_converted["on_demand"] += amount_converted
        elif dep.term_type == "30_days":
            deposit_by_term_converted["30_days"] += amount_converted
        elif dep.term_type == "1_year":
            deposit_by_term_converted["1_year"] += amount_converted
    total_liabilities_converted = settlement_balance_converted + sum(deposit_by_term_converted.values())
    threshold = total_capital_converted * 0.05
    borrower_exposure = {}
    for loan in loans:
        acc = db.query(Account).filter(Account.id == loan.loan_account_id).first()
        if not acc:
            continue
        exposure_original = float(loan.remaining_balance)
        exposure_converted = convert(exposure_original, loan.currency)
        borrower_key = acc.account_number
        if borrower_key not in borrower_exposure:
            borrower_exposure[borrower_key] = {
                "borrower_id": borrower_key,
                "borrower_name": acc.name,
                "total_exposure_converted": 0.0
            }
        borrower_exposure[borrower_key]["total_exposure_converted"] += exposure_converted
    large_risks = []
    for borrower in borrower_exposure.values():
        if borrower["total_exposure_converted"] > threshold:
            percent_of_capital = (borrower["total_exposure_converted"] / total_capital_converted) * 100 if total_capital_converted > 0 else 0
            large_risks.append({
                "borrower_id": borrower["borrower_id"],
                "borrower_name": borrower["borrower_name"],
                "total_exposure_converted": borrower["total_exposure_converted"],
                "percent_of_capital": percent_of_capital
            })
    large_risks.sort(key=lambda x: x["total_exposure_converted"], reverse=True)
    buckets = {
        "on_demand": (0, 0),
        "0-30_days": (1, 30),
        "31-90_days": (31, 90),
        "91-365_days": (91, 365),
        "over_365_days": (366, 10**6)
    }
    assets_by_bucket = {key: 0.0 for key in buckets}
    for loan in loans:
        days = (loan.end_date - date_obj).days
        amount_converted = convert(float(loan.remaining_balance), loan.currency)
        for bucket, (low, high) in buckets.items():
            if low <= days <= high:
                assets_by_bucket[bucket] += amount_converted
                break
    liabilities_by_bucket = {key: 0.0 for key in buckets}
    for dep in deposits:
        days = (dep.end_date - date_obj).days
        amount_converted = convert(float(dep.amount), dep.currency)
        for bucket, (low, high) in buckets.items():
            if low <= days <= high:
                liabilities_by_bucket[bucket] += amount_converted
                break
    liabilities_by_bucket["on_demand"] += settlement_balance_converted
    gap_by_bucket = {k: assets_by_bucket[k] - liabilities_by_bucket[k] for k in buckets}
    return {
        "target_currency": target_currency,
        "as_of_date": as_of_date,
        "source": source,
        "exchange_rates_used": {cur: rate for cur, rate in rate_to_rub.items() if cur != "RUB"},
        "balances": {
            "details": balances[:100],
            "total_balance_converted": total_balance_converted
        },
        "regulatory_capital": {
            "tier1": tier1_sum,
            "tier2": tier2_sum,
            "deductions": deductions_sum,
            "total": total_capital_converted
        },
        "assets": {
            "total_loans": total_loans_converted,
            "total_bonds": total_bonds_converted,
            "total_assets": total_assets_converted
        },
        "liabilities": {
            "settlement_accounts": settlement_balance_converted,
            "deposits": deposit_by_term_converted,
            "total_liabilities": total_liabilities_converted
        },
        "large_risks": {
            "threshold_5_percent": threshold,
            "large_risks": large_risks
        },
        "liquidity_gap": {
            "assets_by_bucket": assets_by_bucket,
            "liabilities_by_bucket": liabilities_by_bucket,
            "gap_by_bucket": gap_by_bucket
        }
    }

# ПОЛУЧЕНИЕ КУРСОВ ИЗ ВНЕШНЕГО API 
@api_router.get("/fetch-exchange-rates")
def fetch_exchange_rates_from_api(date: str = None):
    if date:
        url = f"https://www.cbr-xml-daily.ru/archive/{date}/daily_json.js"
    else:
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        effective_date = data.get("Date", datetime.date.today().isoformat())
        rates = {"RUB": 1.0}
        for code, val_info in data.get("Valute", {}).items():
            rates[code] = float(val_info["Value"])
        return {
            "date": effective_date,
            "rates": rates,
            "source": "cbr_api"
        }
    except Exception as e:
        raise HTTPException(500, f"Не удалось получить курсы из внешнего API: {str(e)}")

# Подключаем роутер с префиксом /api
app.include_router(api_router)

# РАЗДАЧА REACT (СТАТИКИ)
REACT_DIST = os.path.join(os.path.dirname(__file__), "react-static", "dist")
ASSETS_DIR = os.path.join(REACT_DIST, "assets")

if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="react-assets")

    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(os.path.join(REACT_DIST, "favicon.svg"))
    
    @app.get("/icons.svg")
    async def icons():
        return FileResponse(os.path.join(REACT_DIST, "icons.svg"))

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(REACT_DIST, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(REACT_DIST, "index.html"))
else:
    print(f"WARNING: React assets not found at {ASSETS_DIR}")