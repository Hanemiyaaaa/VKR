import { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function LoansDepositsPage() {
    const [loans, setLoans] = useState([]);
    const [deposits, setDeposits] = useState([]);
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState({ loans: false, deposits: false });

    const loadData = async () => {
        setLoading({ loans: true, deposits: true });
        try {
            const [loansData, depositsData, accountsData] = await Promise.all([
                api.getLoans(),
                api.getDeposits(),
                api.getAccounts()
            ]);
            setLoans(loansData);
            setDeposits(depositsData);
            setAccounts(accountsData);
        } catch (err) {
            console.error(err);
            alert('Ошибка загрузки данных: ' + err.message);
        } finally {
            setLoading({ loans: false, deposits: false });
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const getAccountNumber = (accountId) => {
        const acc = accounts.find(a => a.id === accountId);
        return acc ? acc.account_number : accountId;
    };

    // Кредиты
    const handleLoanProfit = async (loanId) => {
        const date = prompt('Введите дату (YYYY-MM-DD) или оставьте пустым для текущей:', '');
        try {
            const data = await api.getLoanProfit(loanId, date || undefined);
            alert(`Прибыль по кредиту: ${data.profit.toFixed(2)} ${data.currency}`);
        } catch (err) {
            alert('Ошибка: ' + err.message);
        }
    };

    const handleLoanInterest = async (loanId) => {
        const date = prompt('Введите дату начисления процентов (YYYY-MM-DD):', '');
        if (!date) return;
        try {
            const data = await api.applyLoanInterest(loanId, date);
            alert(data.message + `\nСумма: ${data.interest.toFixed(2)}`);
            loadData();
        } catch (err) {
            alert('Ошибка: ' + err.message);
        }
    };

    // Депозиты
    const handleDepositCost = async (depositId) => {
        const date = prompt('Введите дату (YYYY-MM-DD) или оставьте пустым для текущей:', '');
        try {
            const data = await api.getDepositCost(depositId, date || undefined);
            alert(`Выплаты по депозиту (проценты): ${data.cost.toFixed(2)} ${data.currency}`);
        } catch (err) {
            alert('Ошибка: ' + err.message);
        }
    };

    const handleDepositInterest = async (depositId) => {
        const date = prompt('Введите дату начисления процентов (YYYY-MM-DD):', '');
        if (!date) return;
        try {
            const data = await api.applyDepositInterest(depositId, date);
            alert(data.message + `\nСумма: ${data.interest.toFixed(2)}`);
            loadData();
        } catch (err) {
            alert('Ошибка: ' + err.message);
        }
    };

    return (
        <div>
            {/* Кредиты */}
            <div className="data-card">
                <h3>💰 Кредиты</h3>
                {loading.loans && <div className="loading-trigger">Загрузка...</div>}
                {!loading.loans && loans.length === 0 && (
                    <div className="empty-state">Нет кредитов. Загрузите файл с кредитами.</div>
                )}
                {loans.length > 0 && (
                    <div className="table-container">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>ID</th><th>Счёт</th><th>Сумма</th><th>Ставка %</th>
                                    <th>Начало</th><th>Конец</th><th>Остаток</th><th>Статус</th><th>Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loans.map(loan => (
                                    <tr key={loan.id}>
                                        <td>{loan.id}</td>
                                        <td>{getAccountNumber(loan.loan_account_id)}</td>
                                        <td>{Number(loan.amount).toFixed(2)}</td>
                                        <td>{loan.interest_rate}%</td>
                                        <td>{loan.start_date}</td>
                                        <td>{loan.end_date}</td>
                                        <td>{Number(loan.remaining_balance).toFixed(2)}</td>
                                        <td>{loan.status}</td>
                                        <td className="action-buttons">
                                            <button className="action-btn profit" onClick={() => handleLoanProfit(loan.id)}>📈 Прибыль</button>
                                            <button className="action-btn interest" onClick={() => handleLoanInterest(loan.id)}>💰 Начислить %</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Депозиты */}
            <div className="data-card">
                <h3>🏦 Депозиты</h3>
                {loading.deposits && <div className="loading-trigger">Загрузка...</div>}
                {!loading.deposits && deposits.length === 0 && (
                    <div className="empty-state">Нет депозитов. Загрузите файл с депозитами.</div>
                )}
                {deposits.length > 0 && (
                    <div className="table-container">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>ID</th><th>Счёт</th><th>Сумма</th><th>Ставка %</th>
                                    <th>Начало</th><th>Конец</th><th>Тип срока</th><th>Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                {deposits.map(dep => (
                                    <tr key={dep.id}>
                                        <td>{dep.id}</td>
                                        <td>{getAccountNumber(dep.deposit_account_id)}</td>
                                        <td>{Number(dep.amount).toFixed(2)}</td>
                                        <td>{dep.interest_rate}%</td>
                                        <td>{dep.start_date}</td>
                                        <td>{dep.end_date}</td>
                                        <td>{dep.term_type}</td>
                                        <td className="action-buttons">
                                            <button className="action-btn cost" onClick={() => handleDepositCost(dep.id)}>💸 Выплаты</button>
                                            <button className="action-btn interest" onClick={() => handleDepositInterest(dep.id)}>💰 Начислить %</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}