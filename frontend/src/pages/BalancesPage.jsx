import { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function BalancesPage() {
    const [balanceDate, setBalanceDate] = useState('2025-03-15');
    const [balances, setBalances] = useState([]);
    const [accounts, setAccounts] = useState([]);
    const [modalHistory, setModalHistory] = useState(null);
    const [modalOpen, setModalOpen] = useState(false);

    const fetchBalances = async () => {
        const data = await api.getBalances(balanceDate);
        setBalances(data);
    };
    const fetchAccounts = async () => {
        const data = await api.getAccounts();
        setAccounts(data);
    };
    const fetchHistory = async (accNumber) => {
        const data = await api.getAccountHistory(accNumber);
        setModalHistory(data);
        setModalOpen(true);
    };
    const closeModal = () => {
        setModalOpen(false);
        setModalHistory(null);
    };

    useEffect(() => {
        fetchBalances();
        fetchAccounts();
    }, [balanceDate]);

    return (
        <div>
            {/* Фильтр даты */}
            <div className="filter-card">
                <h3>📅 Баланс на дату</h3>
                <div className="filters">
                    <div className="filter-group">
                        <label>ДАТА</label>
                        <input type="date" value={balanceDate} onChange={e => setBalanceDate(e.target.value)} />
                    </div>
                    <div className="filter-actions">
                        <button onClick={fetchBalances}>Показать</button>
                    </div>
                </div>
            </div>

            {/* Таблица балансов */}
            <div className="data-card">
                <h3>💵 Балансы счетов</h3>
                <div className="table-container">
                    <table className="data-table">
                        <thead><tr><th>Счёт</th><th>Наименование</th><th>Баланс</th><th>Валюта</th></tr></thead>
                        <tbody>
                            {balances.map(b => (
                                <tr key={b.account_number}>
                                    <td>{b.account_number}</td>
                                    <td>{b.name}</td>
                                    <td>{b.balance.toFixed(2)}</td>
                                    <td>{b.currency}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Справочник счетов */}
            <div className="data-card">
                <h3>📋 Справочник счетов</h3>
                <div className="table-container">
                    <table className="data-table">
                        <thead><tr><th>Номер</th><th>Наименование</th><th>Тип</th><th>Валюта</th><th></th></tr></thead>
                        <tbody>
                            {accounts.map(acc => (
                                <tr key={acc.id}>
                                    <td>{acc.account_number}</td>
                                    <td>{acc.name}</td>
                                    <td>{acc.account_type}</td>
                                    <td>{acc.currency}</td>
                                    <td><button className="history-btn" onClick={() => fetchHistory(acc.account_number)}>📜 История</button></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Модальное окно */}
            {modalOpen && modalHistory && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>📜 История счёта {modalHistory.account} — {modalHistory.name}</h3>
                            <button className="modal-close" onClick={closeModal}>✕</button>
                        </div>
                        <div className="modal-body table-container">
                            <table className="data-table">
                                <thead>
                                    <tr><th>Дата</th><th>Описание</th><th>Контрагент</th><th>Сумма</th><th>Изменение</th><th>Баланс после</th></tr>
                                </thead>
                                <tbody>
                                    {modalHistory.history.map((tx, i) => (
                                        <tr key={i}>
                                            <td>{tx.date}</td>
                                            <td>{tx.description}</td>
                                            <td>{tx.counterparty_account}</td>
                                            <td>{tx.amount.toFixed(2)}</td>
                                            <td>{tx.delta.toFixed(2)}</td>
                                            <td>{tx.balance_after.toFixed(2)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}