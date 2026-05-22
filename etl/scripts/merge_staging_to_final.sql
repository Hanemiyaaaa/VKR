BEGIN;

-- Accounts (без version и file_id)
INSERT INTO accounts (account_number, name, account_type, currency, created_at)
SELECT account_number, name, account_type, currency, NOW()
FROM staging_accounts
ON CONFLICT (account_number) DO UPDATE SET
    name = EXCLUDED.name,
    account_type = EXCLUDED.account_type,
    currency = EXCLUDED.currency,
    created_at = EXCLUDED.created_at;

-- Bonds (с version и file_id)
INSERT INTO bonds (issuer, face_value, purchase_date, maturity_date,
                   coupon_rate, risk_category, currency, created_at, version, file_id)
SELECT issuer, face_value, purchase_date, maturity_date,
       coupon_rate, risk_category::riskcategory, currency, NOW(), 'original', file_id
FROM staging_bonds
ON CONFLICT (issuer, purchase_date) DO UPDATE SET
    face_value = EXCLUDED.face_value,
    maturity_date = EXCLUDED.maturity_date,
    coupon_rate = EXCLUDED.coupon_rate,
    risk_category = EXCLUDED.risk_category,
    currency = EXCLUDED.currency,
    created_at = EXCLUDED.created_at,
    version = EXCLUDED.version,
    file_id = EXCLUDED.file_id;

-- Capital Components
INSERT INTO capital_components (component_type, value, as_of_date, currency, created_at, version, file_id)
SELECT component_type, value, as_of_date, currency, NOW(), version, file_id
FROM staging_capital
ON CONFLICT (component_type, as_of_date) DO UPDATE SET
    value = EXCLUDED.value,
    currency = EXCLUDED.currency,
    created_at = EXCLUDED.created_at,
    version = EXCLUDED.version,
    file_id = EXCLUDED.file_id;

-- Deposits
INSERT INTO deposits (deposit_account_id, amount, interest_rate, start_date, end_date,
                      term_type, accrued_interest, currency, created_at, version, file_id)
SELECT acc.id, s.amount, s.interest_rate, s.start_date, s.end_date,
       s.term_type, 0, s.currency, NOW(), s.version, s.file_id
FROM staging_deposits s
JOIN accounts acc ON acc.account_number = s.deposit_account_number
ON CONFLICT (deposit_account_id, start_date) DO UPDATE SET
    amount = EXCLUDED.amount,
    interest_rate = EXCLUDED.interest_rate,
    end_date = EXCLUDED.end_date,
    term_type = EXCLUDED.term_type,
    currency = EXCLUDED.currency,
    created_at = EXCLUDED.created_at,
    version = EXCLUDED.version,
    file_id = EXCLUDED.file_id;

-- Exchange Rates
INSERT INTO exchange_rates (currency, rate_to_rub, date, created_at, version, file_id)
SELECT currency, rate_to_rub, date, NOW(), version, file_id
FROM staging_exchange_rates
ON CONFLICT (currency, date) DO UPDATE SET
    rate_to_rub = EXCLUDED.rate_to_rub,
    created_at = EXCLUDED.created_at,
    version = EXCLUDED.version,
    file_id = EXCLUDED.file_id;

-- Initial Balances
INSERT INTO initial_balances (account_id, balance, date, version, file_id, created_at)
SELECT account_id, balance, date, version, file_id, NOW()
FROM staging_initial_balances
ON CONFLICT (account_id, date) DO UPDATE SET
    balance = EXCLUDED.balance,
    version = EXCLUDED.version,
    file_id = EXCLUDED.file_id,
    created_at = EXCLUDED.created_at;

-- Loans
INSERT INTO loans (loan_account_id, amount, interest_rate, start_date, end_date,
                   repayment_day, remaining_balance, status, risk_category, currency, created_at, version, file_id)
SELECT acc.id, s.amount, s.interest_rate, s.start_date, s.end_date,
       s.repayment_day, s.remaining_balance, s.status, s.risk_category::riskcategory, s.currency, NOW(), s.version, s.file_id
FROM staging_loans s
JOIN accounts acc ON acc.account_number = s.loan_account_number
ON CONFLICT (loan_account_id, start_date) DO UPDATE SET
    amount = EXCLUDED.amount,
    interest_rate = EXCLUDED.interest_rate,
    end_date = EXCLUDED.end_date,
    repayment_day = EXCLUDED.repayment_day,
    remaining_balance = EXCLUDED.remaining_balance,
    status = EXCLUDED.status,
    risk_category = EXCLUDED.risk_category,
    currency = EXCLUDED.currency,
    created_at = EXCLUDED.created_at,
    version = EXCLUDED.version,
    file_id = EXCLUDED.file_id;

-- Transactions
INSERT INTO transactions (transaction_date, from_account_id, to_account_id,
                          amount, currency, description, file_id, version, created_at)
SELECT s.transaction_date, from_acc.id, to_acc.id,
       s.amount, s.currency, s.description, s.file_id, s.version, NOW()
FROM staging_transactions s
JOIN accounts from_acc ON from_acc.account_number = s.from_account
JOIN accounts to_acc ON to_acc.account_number = s.to_account
ON CONFLICT (id) DO NOTHING;

-- Main (data_table)
INSERT INTO data_table (account_id, client_type, product_type, balance,
                        currency, risk_flag, file_id, version)
SELECT account_id, client_type, product_type, balance::numeric,
       currency, risk_flag, file_id, version
FROM staging_main
ON CONFLICT (id) DO NOTHING;

-- Обновляем статусы для accounts и bonds
UPDATE file_registry SET status = 'merged'
WHERE data_type IN ('accounts', 'bonds', 'capital', 'deposits', 'exchange_rates', 'initial_balances', 'loans', 'transactions', 'main') AND status = 'staged';

COMMIT;