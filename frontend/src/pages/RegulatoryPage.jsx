import { useState } from 'react';
import { api } from '../api/client';

export default function RegulatoryPage() {
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
    const [capital, setCapital] = useState(null);
    const [assets, setAssets] = useState(null);
    const [liabilities, setLiabilities] = useState(null);
    const [liquidity, setLiquidity] = useState(null);
    const [largeRisks, setLargeRisks] = useState(null);
    const [loading, setLoading] = useState({
        capital: false,
        assets: false,
        liabilities: false,
        liquidity: false,
        largeRisks: false,
    });

    const fetchCapital = async () => {
        setLoading(prev => ({ ...prev, capital: true }));
        try {
            const data = await api.getRegulatoryCapital();
            setCapital(data);
        } catch (err) {
            console.error(err);
            alert('Ошибка загрузки капитала');
        } finally {
            setLoading(prev => ({ ...prev, capital: false }));
        }
    };

    const fetchAssets = async () => {
        setLoading(prev => ({ ...prev, assets: true }));
        try {
            const data = await api.getAssets(date);
            setAssets(data);
        } catch (err) {
            console.error(err);
            alert('Ошибка загрузки активов');
        } finally {
            setLoading(prev => ({ ...prev, assets: false }));
        }
    };

    const fetchLiabilities = async () => {
        setLoading(prev => ({ ...prev, liabilities: true }));
        try {
            const data = await api.getLiabilities(date);
            setLiabilities(data);
        } catch (err) {
            console.error(err);
            alert('Ошибка загрузки обязательств');
        } finally {
            setLoading(prev => ({ ...prev, liabilities: false }));
        }
    };

    const fetchLiquidity = async () => {
        setLoading(prev => ({ ...prev, liquidity: true }));
        try {
            const data = await api.getLiquidity(date);
            setLiquidity(data);
        } catch (err) {
            console.error(err);
            alert('Ошибка загрузки ликвидности');
        } finally {
            setLoading(prev => ({ ...prev, liquidity: false }));
        }
    };

    const fetchLargeRisks = async () => {
        setLoading(prev => ({ ...prev, largeRisks: true }));
        try {
            const data = await api.getLargeRisks(date);
            setLargeRisks(data);
        } catch (err) {
            console.error(err);
            alert('Ошибка загрузки крупных рисков');
        } finally {
            setLoading(prev => ({ ...prev, largeRisks: false }));
        }
    };

    const fetchAll = () => {
        fetchCapital();
        fetchAssets();
        fetchLiabilities();
        fetchLiquidity();
        fetchLargeRisks();
    };

    return (
        <div>
            {/* Блок выбора даты и обновления */}
            <div className="filter-card">
                <h3>📅 Отчётная дата</h3>
                <div className="filters">
                    <div className="filter-group">
                        <label>ДАТА</label>
                        <input type="date" value={date} onChange={e => setDate(e.target.value)} />
                    </div>
                    <div className="filter-actions">
                        <button onClick={fetchAll}>Обновить все отчёты</button>
                    </div>
                </div>
            </div>

            {/* Регулятивный капитал */}
            <div className="data-card">
                <h3>🏦 Регулятивный капитал</h3>
                {loading.capital && <div className="loading-trigger">Загрузка...</div>}
                {capital && (
                    <div className="table-container">
                        <table className="data-table">
                            <tbody>
                                <tr><th>Основной капитал (Tier 1)</th><td>{capital.tier1.toFixed(2)}</td></tr>
                                <tr><th>Дополнительный капитал (Tier 2)</th><td>{capital.tier2.toFixed(2)}</td></tr>
                                <tr><th>Вычеты</th><td>{capital.deductions.toFixed(2)}</td></tr>
                                <tr className="total-row"><th>Итого капитал</th><td><strong>{capital.total.toFixed(2)}</strong></td></tr>
                            </tbody>
                        </table>
                    </div>
                )}
                {!capital && !loading.capital && (
                    <div className="empty-state">Нажмите «Обновить все отчёты» для загрузки</div>
                )}
            </div>

            {/* Активы */}
            <div className="data-card">
                <h3>📈 Активы (кредиты + облигации)</h3>
                {loading.assets && <div className="loading-trigger">Загрузка...</div>}
                {assets && (
                    <>
                        <div className="table-container">
                            <table className="data-table">
                                <thead>
                                    <tr><th>Тип</th><th>Контрагент/Эмитент</th><th>Сумма</th><th>Риск</th><th>Взвешенная сумма</th><th>Дата начала</th><th>Дата окончания</th></tr>
                                </thead>
                                <tbody>
                                    {assets.loans.map((loan, i) => (
                                        <tr key={`loan-${i}`}>
                                            <td>Кредит</td><td>{loan.account_number}</td><td>{loan.amount.toFixed(2)}</td>
                                            <td>{loan.risk_category}</td><td>{loan.risk_weighted_amount.toFixed(2)}</td>
                                            <td>{loan.start_date}</td><td>{loan.end_date}</td>
                                        </tr>
                                    ))}
                                    {assets.bonds.map((bond, i) => (
                                        <tr key={`bond-${i}`}>
                                            <td>Облигация</td><td>{bond.issuer}</td><td>{bond.face_value.toFixed(2)}</td>
                                            <td>{bond.risk_category}</td><td>{bond.risk_weighted_amount.toFixed(2)}</td>
                                            <td>{bond.purchase_date}</td><td>{bond.maturity_date}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div style={{ marginTop: '0.8rem', fontSize: '0.85rem' }}>
                            <strong>Итого активы:</strong> {assets.summary.total_assets.toFixed(2)}<br />
                            <strong>Взвешенные по риску:</strong> {assets.summary.total_risk_weighted_assets.toFixed(2)}
                        </div>
                    </>
                )}
                {!assets && !loading.assets && (
                    <div className="empty-state">Данные не загружены</div>
                )}
            </div>

            {/* Обязательства */}
            <div className="data-card">
                <h3>📋 Обязательства</h3>
                {loading.liabilities && <div className="loading-trigger">Загрузка...</div>}
                {liabilities && (
                    <div className="table-container">
                        <table className="data-table">
                            <tbody>
                                <tr><th>Расчётные счета клиентов</th><td>{liabilities.settlement_accounts_balance.toFixed(2)}</td></tr>
                                <tr><th>Депозиты до востребования</th><td>{liabilities.deposits.on_demand.toFixed(2)}</td></tr>
                                <tr><th>Депозиты на 30 дней</th><td>{liabilities.deposits['30_days'].toFixed(2)}</td></tr>
                                <tr><th>Депозиты на год</th><td>{liabilities.deposits['1_year'].toFixed(2)}</td></tr>
                                <tr className="total-row"><th>Итого обязательства</th><td><strong>{liabilities.total_liabilities.toFixed(2)}</strong></td></tr>
                            </tbody>
                        </table>
                    </div>
                )}
                {!liabilities && !loading.liabilities && (
                    <div className="empty-state">Данные не загружены</div>
                )}
            </div>

            {/* Ликвидность (GAP) */}
            <div className="data-card">
                <h3>⏳ Ликвидность (GAP-анализ)</h3>
                {loading.liquidity && <div className="loading-trigger">Загрузка...</div>}
                {liquidity && (
                    <>
                        <div className="table-container">
                            <table className="data-table">
                                <thead><tr><th>Срок</th><th>Требования (активы)</th><th>Обязательства</th><th>Разрыв (GAP)</th></tr></thead>
                                <tbody>
                                    {Object.entries(liquidity.summary.gap_by_bucket).map(([bucket, gap]) => {
                                        const bucketNames = {
                                            on_demand: 'До востребования',
                                            '0-30_days': 'до 30 дней',
                                            '31-90_days': '31-90 дней',
                                            '91-365_days': '91-365 дней',
                                            over_365_days: 'свыше 365 дней',
                                        };
                                        const assets = liquidity.summary.assets_by_bucket[bucket] || 0;
                                        const liabilitiesVal = liquidity.summary.liabilities_by_bucket[bucket] || 0;
                                        const gapClass = gap >= 0 ? 'positive-gap' : 'negative-gap';
                                        return (
                                            <tr key={bucket}>
                                                <td>{bucketNames[bucket]}</td>
                                                <td>{assets.toFixed(2)}</td>
                                                <td>{liabilitiesVal.toFixed(2)}</td>
                                                <td className={gapClass}>{gap.toFixed(2)}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                        <details style={{ marginTop: '0.8rem' }}>
                            <summary style={{ cursor: 'pointer', fontSize: '0.8rem', color: '#6b5b95' }}>📊 Детали по кредитам и депозитам</summary>
                            <div style={{ marginTop: '0.5rem' }}>
                                <h4>Кредиты</h4>
                                <div className="table-container">
                                    <table className="data-table">
                                        <thead><tr><th>Счёт</th><th>Сумма</th><th>Дата погашения</th><th>Дней до</th></tr></thead>
                                        <tbody>
                                            {liquidity.details.loans.map((l, i) => (
                                                <tr key={i}><td>{l.account_number}</td><td>{l.amount.toFixed(2)}</td><td>{l.end_date}</td><td>{l.days_to_maturity}</td></tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                <h4>Депозиты</h4>
                                <div className="table-container">
                                    <table className="data-table">
                                        <thead><tr><th>Счёт</th><th>Сумма</th><th>Дата закрытия</th><th>Дней до</th><th>Тип</th></tr></thead>
                                        <tbody>
                                            {liquidity.details.deposits.map((d, i) => (
                                                <tr key={i}><td>{d.account_number}</td><td>{d.amount.toFixed(2)}</td><td>{d.end_date}</td><td>{d.days_to_maturity}</td><td>{d.term_type}</td></tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </details>
                    </>
                )}
                {!liquidity && !loading.liquidity && (
                    <div className="empty-state">Данные не загружены</div>
                )}
            </div>

            {/* Крупные риски */}
            <div className="data-card">
                <h3>⚠️ Крупные риски ({">5%"} капитала)</h3>
                {loading.largeRisks && <div className="loading-trigger">Загрузка...</div>}
                {largeRisks && (
                    <>
                        <div>Порог 5%: {largeRisks.threshold_5_percent.toFixed(2)}</div>
                        {largeRisks.large_risks.length === 0 ? (
                            <div className="empty-state">Нет заёмщиков, превышающих порог</div>
                        ) : (
                            <div className="table-container">
                                <table className="data-table">
                                    <thead><tr><th>Заёмщик (ID)</th><th>Наименование</th><th>Задолженность</th><th>% капитала</th></tr></thead>
                                    <tbody>
                                        {largeRisks.large_risks.map((risk, i) => (
                                            <tr key={i}>
                                                <td>{risk.borrower_id}</td><td>{risk.borrower_name}</td>
                                                <td>{risk.total_exposure.toFixed(2)}</td>
                                                <td className={risk.percent_of_capital > 25 ? 'negative-gap' : ''}>{risk.percent_of_capital.toFixed(2)}%</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </>
                )}
                {!largeRisks && !loading.largeRisks && (
                    <div className="empty-state">Данные не загружены</div>
                )}
            </div>
        </div>
    );
}