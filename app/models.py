from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Numeric, Enum as SQLEnum, Text
from .database import Base
import datetime
import enum

class RiskCategory(enum.Enum):
    unsecured = "unsecured"                # 100% риска
    government_guaranteed = "government_guaranteed"  # 0% риска

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    data_type = Column(String, nullable=True)
    business_date = Column(Date)
    upload_date = Column(Date, default=datetime.date.today)
    user_name = Column(String)

class DataRow(Base):
    __tablename__ = "data_table"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    account_id = Column(String)
    client_type = Column(String)
    product_type = Column(String)
    balance = Column(Numeric(15,2))
    currency = Column(String)
    risk_flag = Column(String)
    version = Column(String, default="original")

class Correction(Base):
    __tablename__ = "corrections"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer)
    field_to_update = Column(String)
    new_value = Column(String)
    condition_field = Column(String)
    operator = Column(String)
    condition_value = Column(String)

class CorrectionLog(Base):
    __tablename__ = "correction_logs"
    id = Column(Integer, primary_key=True, index=True)
    correction_id = Column(Integer)           # ID применённого правила
    file_id = Column(Integer)                 # ID файла
    row_id = Column(Integer, nullable=True)   # ID записи в data_table, к которой применено изменение
    field_name = Column(String, nullable=True)   # какое поле изменили (account_id, balance, etc.)
    old_value = Column(String, nullable=True)    # старое значение
    new_value = Column(String, nullable=True)    # новое значение
    applied_by = Column(String)               # кто применил
    applied_at = Column(DateTime, default=datetime.datetime.utcnow)

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String, unique=True, index=True)
    name = Column(String)
    account_type = Column(String, default="asset")  # "settlement", "deposit", "loan", "cash", "other"
    currency = Column(String, default="RUB")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InitialBalance(Base):
    __tablename__ = "initial_balances"
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    version = Column(String, default="original")
    account_id = Column(Integer, ForeignKey("accounts.id"))
    balance = Column(Numeric(15,2))
    date = Column(Date)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    version = Column(String, default="original")
    transaction_date = Column(Date)
    from_account_id = Column(Integer, ForeignKey("accounts.id"))
    to_account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(Numeric(15,2))
    currency = Column(String, default="RUB")
    description = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Loan(Base):
    __tablename__ = "loans"
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    version = Column(String, default="original")
    loan_account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(Numeric(15,2))
    interest_rate = Column(Numeric(5,2))    # годовая процентная ставка
    start_date = Column(Date)
    end_date = Column(Date)
    repayment_day = Column(Integer)         # день месяца для платежа
    remaining_balance = Column(Numeric(15,2))
    status = Column(String, default="active")
    risk_category = Column(SQLEnum(RiskCategory), nullable=True) 
    currency = Column(String, default="RUB")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Deposit(Base):
    __tablename__ = "deposits"
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    version = Column(String, default="original")
    deposit_account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(Numeric(15,2))
    interest_rate = Column(Numeric(5,2))
    start_date = Column(Date)
    end_date = Column(Date)
    term_type = Column(String)   # "on_demand", "30_days", "1_year"
    accrued_interest = Column(Numeric(15,2), default=0)
    currency = Column(String, default="RUB")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CapitalComponent(Base):
    __tablename__ = "capital_components"
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    version = Column(String, default="original")
    component_type = Column(String)   # "tier1_share_capital", "tier1_retained_earnings", "tier1_share_premium", "tier2_subordinated_debt", "deduction_uncovered_losses", "deduction_treasury_shares"
    value = Column(Numeric(15,2))
    currency = Column(String, default="RUB")
    as_of_date = Column(Date)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    version = Column(String, default="original")
    currency = Column(String)
    rate_to_rub = Column(Numeric(12,4))
    date = Column(Date)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Bond(Base):
    __tablename__ = "bonds"
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    version = Column(String, default="original")
    issuer = Column(String)                # эмитент
    face_value = Column(Numeric(15,2))     # номинал
    purchase_date = Column(Date)
    maturity_date = Column(Date)
    coupon_rate = Column(Numeric(5,2))     # купонная ставка, %
    risk_category = Column(SQLEnum(RiskCategory))
    currency = Column(String, default="RUB")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class FileRegistry(Base):
    __tablename__ = "file_registry"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    file_path = Column(String)          # путь внутри общего тома
    data_type = Column(String)          # accounts, loans, deposits, ...
    status = Column(String, default="pending")  # pending, processing, done, error
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)

class ETLLog(Base):
    __tablename__ = "etl_logs"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    data_type = Column(String)
    status = Column(String)              # started, success, failed
    rows_read = Column(Integer)
    rows_written = Column(Integer)
    errors = Column(Text)                # JSON или текст ошибки
    started_at = Column(DateTime)
    finished_at = Column(DateTime)