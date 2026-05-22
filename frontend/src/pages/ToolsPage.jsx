import { useState } from 'react';
import { api } from '../api/client';

export default function ToolsPage() {
    // Конвертер валют
    const [convAmount, setConvAmount] = useState(100);
    const [convFrom, setConvFrom] = useState('USD');
    const [convTo, setConvTo] = useState('RUB');
    const [convDate, setConvDate] = useState(new Date().toISOString().split('T')[0]);
    const [convSource, setConvSource] = useState('db');
    const [convResult, setConvResult] = useState(null);

    // Приведение к единой валюте
    const [targetCurrency, setTargetCurrency] = useState('RUB');
    const [summaryDate, setSummaryDate] = useState(new Date().toISOString().split('T')[0]);
    const [summarySource, setSummarySource] = useState('db');
    const [summaryResult, setSummaryResult] = useState(null);
    const [summaryModalOpen, setSummaryModalOpen] = useState(false);

    // Корректировки
    const [correctionFileId, setCorrectionFileId] = useState('');
    const [fieldToUpdate, setFieldToUpdate] = useState('risk_flag');
    const [newValue, setNewValue] = useState('');
    const [conditionField, setConditionField] = useState('client_type');
    const [operator, setOperator] = useState('equals');
    const [conditionValue, setConditionValue] = useState('');
    const [applyUser, setApplyUser] = useState('');

    // Аудит
    const [auditFileId, setAuditFileId] = useState('');
    const [auditLogs, setAuditLogs] = useState([]);
    const [auditLoading, setAuditLoading] = useState(false);

    // Конвертер
    const handleConvert = async () => {
        try {
            const data = await api.convertCurrency(convAmount, convFrom, convTo, convDate, convSource);
            setConvResult(data);
        } catch (err) {
            alert('Ошибка конвертации: ' + err.message);
        }
    };

    // Приведение к единой валюте
    const handleSummary = async () => {
        try {
            const data = await api.getFinancialSummaryInCurrency(targetCurrency, summaryDate, summarySource);
            setSummaryResult(data);
            setSummaryModalOpen(true);
        } catch (err) {
            alert('Ошибка: ' + err.message);
        }
    };

    // Корректировки
    const handleCreateCorrection = async (e) => {
        e.preventDefault();
        const fd = new FormData();
        fd.append('file_id', correctionFileId);
        fd.append('field_to_update', fieldToUpdate);
        fd.append('new_value', newValue);
        fd.append('condition_field', conditionField);
        fd.append('operator', operator);
        fd.append('condition_value', conditionValue);
        try {
            const res = await api.createCorrection(fd);
            alert(res.message);
        } catch (err) {
            alert('Ошибка: ' + err.message);
        }
    };

    const handleApplyCorrections = async () => {
        if (!correctionFileId || !applyUser) {
            alert('Укажите File ID и имя пользователя');
            return;
        }
        try {
            const res = await api.applyCorrections(Number(correctionFileId), applyUser);
            alert(res.message);
        } catch (err) {
            alert('Ошибка: ' + err.message);
        }
    };

    // Аудит 
    const loadAuditLogs = async () => {
        setAuditLoading(true);
        try {
            const logs = await api.getCorrectionLogs(auditFileId ? Number(auditFileId) : undefined);
            setAuditLogs(logs);
        } catch (err) {
            alert('Ошибка загрузки: ' + err.message);
        } finally {
            setAuditLoading(false);
        }
    };

    return (
        <div>
            {/* 1. Конвертер валют */}
            <div className="data-card">
                <h3>💱 Конвертер валют</h3>
                <div className="filters" style={{ marginBottom: '0.5rem' }}>
                    <div className="filter-group">
                        <label>СУММА</label>
                        <input type="number" value={convAmount} onChange={e => setConvAmount(Number(e.target.value))} />
                    </div>
                    <div className="filter-group">
                        <label>ИЗ</label>
                        <input type="text" value={convFrom} onChange={e => setConvFrom(e.target.value.toUpperCase())} />
                    </div>
                    <div className="filter-group">
                        <label>В</label>
                        <input type="text" value={convTo} onChange={e => setConvTo(e.target.value.toUpperCase())} />
                    </div>
                    <div className="filter-group">
                        <label>ДАТА</label>
                        <input type="date" value={convDate} onChange={e => setConvDate(e.target.value)} />
                    </div>
                </div>
                <div className="filter-group" style={{ marginBottom: '0.5rem' }}>
                    <label>ИСТОЧНИК КУРСОВ</label>
                    <div style={{ display: 'flex', gap: '1rem', marginTop: '0.2rem' }}>
                        <label><input type="radio" name="convSource" value="db" checked={convSource === 'db'} onChange={() => setConvSource('db')} /> База данных</label>
                        <label><input type="radio" name="convSource" value="api" checked={convSource === 'api'} onChange={() => setConvSource('api')} /> API ЦБ РФ</label>
                    </div>
                </div>
                <div className="filter-actions">
                    <button onClick={handleConvert}>Конвертировать</button>
                </div>
                {convResult && (
                    <div className="result-card">
                        <div className="result-main">
                            {convResult.original_amount} {convResult.from_currency} = <strong>{convResult.converted_amount.toFixed(2)} {convResult.to_currency}</strong>
                        </div>
                        <div className="result-detail">Курс {convResult.rate_used} ({convResult.from_currency} → RUB), источник: {convResult.source}</div>
                    </div>
                )}
            </div>

            {/* 2. Приведение к единой валюте */}
            <div className="data-card">
                <h3>🏦 Привести все показатели к единой валюте</h3>
                <div className="filters" style={{ marginBottom: '0.5rem' }}>
                    <div className="filter-group">
                        <label>ЦЕЛЕВАЯ ВАЛЮТА</label>
                        <input type="text" value={targetCurrency} onChange={e => setTargetCurrency(e.target.value.toUpperCase())} />
                    </div>
                    <div className="filter-group">
                        <label>ДАТА</label>
                        <input type="date" value={summaryDate} onChange={e => setSummaryDate(e.target.value)} />
                    </div>
                </div>
                <div className="filter-group" style={{ marginBottom: '0.5rem' }}>
                    <label>ИСТОЧНИК КУРСОВ</label>
                    <div style={{ display: 'flex', gap: '1rem', marginTop: '0.2rem' }}>
                        <label><input type="radio" name="summarySource" value="db" checked={summarySource === 'db'} onChange={() => setSummarySource('db')} /> База данных</label>
                        <label><input type="radio" name="summarySource" value="api" checked={summarySource === 'api'} onChange={() => setSummarySource('api')} /> API ЦБ РФ</label>
                    </div>
                </div>
                <div className="filter-actions">
                    <button onClick={handleSummary}>Пересчитать всё</button>
                </div>
            </div>

            {/* 3. Корректировки данных */}
            <div className="data-card">
                <h3>⚙️ Корректировки данных</h3>

                {/* Форма создания правила */}
                <form onSubmit={handleCreateCorrection} className="correction-form">
                    <div className="filters" style={{ marginBottom: '0.8rem' }}>
                        <div className="filter-group">
                            <label>FILE ID</label>
                            <input type="number" value={correctionFileId} onChange={e => setCorrectionFileId(e.target.value)} required placeholder="ID файла" />
                        </div>
                        <div className="filter-group">
                            <label>НОВОЕ ЗНАЧЕНИЕ</label>
                            <input type="text" value={newValue} onChange={e => setNewValue(e.target.value)} required placeholder="Новое значение" />
                        </div>
                    </div>

                    <div className="filters filters-three">
                        <div className="filter-group">
                            <label>ПОЛЕ</label>
                            <select value={fieldToUpdate} onChange={e => setFieldToUpdate(e.target.value)}>
                                <option value="risk_flag">risk_flag</option>
                                <option value="balance">balance</option>
                            </select>
                        </div>
                        <div className="filter-group">
                            <label>ПОЛЕ УСЛОВИЯ</label>
                            <select value={conditionField} onChange={e => setConditionField(e.target.value)}>
                                <option value="client_type">client_type</option>
                                <option value="currency">currency</option>
                                <option value="balance">balance</option>
                            </select>
                        </div>
                        <div className="filter-group">
                            <label>ОПЕРАТОР</label>
                            <select value={operator} onChange={e => setOperator(e.target.value)}>
                                <option value="equals">equals</option>
                                <option value="contains">contains</option>
                                <option value="upper_equals">upper_equals</option>
                            </select>
                        </div>
                        <div className="filters" style={{ marginBottom: 0 }}>
                            <div className="filter-group" style={{ flex: 1 }}>
                                <label>ЗНАЧЕНИЕ УСЛОВИЯ</label>
                                <input type="text" value={conditionValue} onChange={e => setConditionValue(e.target.value)} required placeholder="Пример: physical" />
                            </div>
                        </div>
                        <div className="filter-actions">
                            <button type="submit">Создать правило</button>
                        </div>
                    </div>
                </form>

                {/* Блок применения правил */}
                <div className="correction-apply-simple">
                    <div className="filters" style={{ marginBottom: 0 }}>
                        <div className="filter-group">
                            <label>FILE ID (для применения)</label>
                            <input type="number" value={correctionFileId} onChange={e => setCorrectionFileId(e.target.value)} placeholder="ID файла" />
                        </div>
                        <div className="filter-group">
                            <label>КТО ПРИМЕНЯЕТ</label>
                            <input type="text" value={applyUser} onChange={e => setApplyUser(e.target.value)} placeholder="Ваше имя" />
                        </div>
                        <div className="filter-actions">
                            <button type="button" onClick={handleApplyCorrections}>Применить корректировки</button>
                        </div>
                    </div>
                </div>
            </div>

            {/* 4. Аудит */}
            <div className="data-card">
                <h3>📜 История изменений (аудит)</h3>
                <div className="filters" style={{ marginBottom: '0.5rem' }}>
                    <div className="filter-group">
                        <label>FILTER BY FILE ID</label>
                        <input type="number" value={auditFileId} onChange={e => setAuditFileId(e.target.value)} placeholder="Необязательно" />
                    </div>
                    <div className="filter-actions">
                        <button onClick={loadAuditLogs}>Показать историю</button>
                    </div>
                </div>
                {auditLoading && <div className="loading-trigger">Загрузка...</div>}
                {!auditLoading && auditLogs.length > 0 && (
                    <div className="table-container">
                        <table className="data-table">
                            <thead>
                                <tr><th>ID файла</th><th>ID строки</th><th>Поле</th><th>Старое значение</th><th>Новое значение</th><th>Кто изменил</th><th>Дата/время</th></tr>
                            </thead>
                            <tbody>
                                {auditLogs.map(log => (
                                    <tr key={log.id}>
                                        <td>{log.file_id}</td>
                                        <td>{log.row_id || '—'}</td>
                                        <td>{log.field_name}</td>
                                        <td>{log.old_value || '—'}</td>
                                        <td>{log.new_value || '—'}</td>
                                        <td>{log.applied_by}</td>
                                        <td>{new Date(log.applied_at).toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {!auditLoading && auditLogs.length === 0 && (
                    <div className="empty-state">Нет записей об изменениях</div>
                )}
            </div>

            {/* Модальное окно для отчёта "Приведение к единой валюте" */}
            {summaryModalOpen && summaryResult && (
                <div className="modal-overlay" onClick={() => setSummaryModalOpen(false)}>
                    <div className="modal-content large-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>📊 Сводка в {summaryResult.target_currency} на {summaryResult.as_of_date} (источник: {summaryResult.source})</h3>
                            <button className="modal-close" onClick={() => setSummaryModalOpen(false)}>✕</button>
                        </div>
                        <div className="modal-body">
                            {/* Балансы счетов */}
                            <div className="data-card" style={{ marginBottom: '1rem' }}>
                                <h4>💰 Балансы счетов (итого: {summaryResult.balances.total_balance_converted.toFixed(2)})</h4>
                                <div className="table-container">
                                    <table className="data-table">
                                        <thead>
                                            <tr><th>Счёт</th><th>Наименование</th><th>Исходный баланс</th><th>Исх. валюта</th><th>В {summaryResult.target_currency}</th></tr>
                                        </thead>
                                        <tbody>
                                            {summaryResult.balances.details.slice(0, 20).map(acc => (
                                                <tr key={acc.account_number}>
                                                    <td>{acc.account_number}</td>
                                                    <td>{acc.name}</td>
                                                    <td>{acc.original_balance.toFixed(2)}</td>
                                                    <td>{acc.original_currency}</td>
                                                    <td>{acc.balance_converted.toFixed(2)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Регулятивный капитал */}
                            <div className="data-card">
                                <h4>🏦 Регулятивный капитал ({summaryResult.target_currency})</h4>
                                <table className="data-table">
                                    <tbody>
                                        <tr><th>Tier 1</th><td>{summaryResult.regulatory_capital.tier1.toFixed(2)}</td></tr>
                                        <tr><th>Tier 2</th><td>{summaryResult.regulatory_capital.tier2.toFixed(2)}</td></tr>
                                        <tr><th>Вычеты</th><td>{summaryResult.regulatory_capital.deductions.toFixed(2)}</td></tr>
                                        <tr className="total-row"><th>Итого капитал</th><td><strong>{summaryResult.regulatory_capital.total.toFixed(2)}</strong></td></tr>
                                    </tbody>
                                </table>
                            </div>

                            {/* Активы и обязательства */}
                            <div className="data-card">
                                <h4>📈 Активы / 📋 Обязательства</h4>
                                <table className="data-table">
                                    <tbody>
                                        <tr><th>Кредиты</th><td>{summaryResult.assets.total_loans.toFixed(2)}</td></tr>
                                        <tr><th>Облигации</th><td>{summaryResult.assets.total_bonds.toFixed(2)}</td></tr>
                                        <tr><th>Итого активы</th><td><strong>{summaryResult.assets.total_assets.toFixed(2)}</strong></td></tr>
                                        <tr><th>Расчётные счета</th><td>{summaryResult.liabilities.settlement_accounts.toFixed(2)}</td></tr>
                                        <tr><th>Депозиты до востребования</th><td>{summaryResult.liabilities.deposits.on_demand.toFixed(2)}</td></tr>
                                        <tr><th>Депозиты до 30 дней</th><td>{summaryResult.liabilities.deposits['30_days'].toFixed(2)}</td></tr>
                                        <tr><th>Депозиты до 1 года</th><td>{summaryResult.liabilities.deposits['1_year'].toFixed(2)}</td>
                                        </tr>
                                        <tr><th>Итого обязательства</th><td><strong>{summaryResult.liabilities.total_liabilities.toFixed(2)}</strong></td></tr>
                                    </tbody>
                                </table>
                            </div>

                            {/* Крупные риски */}
                            <div className="data-card">
                                <h4>⚠️ Крупные риски (&gt;5% капитала)</h4>
                                {summaryResult.large_risks.large_risks.length === 0 ? (
                                    <div className="empty-state">Нет заёмщиков, превышающих порог {summaryResult.large_risks.threshold_5_percent.toFixed(2)}</div>
                                ) : (
                                    <div className="table-container">
                                        <table className="data-table">
                                            <thead>
                                                <tr><th>Заёмщик</th><th>Задолженность</th><th>% капитала</th></tr>
                                            </thead>
                                            <tbody>
                                                {summaryResult.large_risks.large_risks.map((risk, i) => (
                                                    <tr key={i}>
                                                        <td>{risk.borrower_name} (ID: {risk.borrower_id})</td>
                                                        <td>{risk.total_exposure_converted.toFixed(2)}</td>
                                                        <td className={risk.percent_of_capital > 25 ? 'negative-gap' : ''}>{risk.percent_of_capital.toFixed(2)}%</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>

                            {/* Ликвидность (GAP) */}
                            <div className="data-card">
                                <h4>⏳ Ликвидность (GAP) в {summaryResult.target_currency}</h4>
                                <div className="table-container">
                                    <table className="data-table">
                                        <thead>
                                            <tr><th>Срок</th><th>Требования</th><th>Обязательства</th><th>Разрыв</th></tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(summaryResult.liquidity_gap.assets_by_bucket).map(([bucket, assets]) => {
                                                const bucketNames = {
                                                    on_demand: 'До востребования',
                                                    '0-30_days': 'до 30 дней',
                                                    '31-90_days': '31-90 дней',
                                                    '91-365_days': '91-365 дней',
                                                    over_365_days: 'свыше 365 дней',
                                                };
                                                const liabilities = summaryResult.liquidity_gap.liabilities_by_bucket[bucket] || 0;
                                                const gap = summaryResult.liquidity_gap.gap_by_bucket[bucket] || 0;
                                                return (
                                                    <tr key={bucket}>
                                                        <td>{bucketNames[bucket]}</td>
                                                        <td>{assets.toFixed(2)}</td>
                                                        <td>{liabilities.toFixed(2)}</td>
                                                        <td className={gap >= 0 ? 'positive-gap' : 'negative-gap'}>{gap.toFixed(2)}</td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}