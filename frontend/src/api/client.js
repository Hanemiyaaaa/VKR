// frontend/src/api/client.js
const API_BASE = '/api';

async function request(url, options = {}) {
    const res = await fetch(`${API_BASE}${url}`, options);
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
    }
    return res.json();
}

export const api = {
    // Файлы
    uploadFile: (formData) => request('/upload', { method: 'POST', body: formData }),
    uploadAccounts: (formData) => request('/upload-accounts', { method: 'POST', body: formData }),
    uploadInitialBalances: (formData) => request('/upload-initial-balances', { method: 'POST', body: formData }),
    uploadTransactions: (formData) => request('/upload-transactions', { method: 'POST', body: formData }),
    uploadLoans: (formData) => request('/upload-loans', { method: 'POST', body: formData }),
    uploadDeposits: (formData) => request('/upload-deposits', { method: 'POST', body: formData }),
    uploadCapital: (formData) => request('/upload-capital', { method: 'POST', body: formData }),
    uploadExchangeRates: (formData) => request('/upload-exchange-rates', { method: 'POST', body: formData }),
    uploadBonds: (formData) => request('/upload-bonds', { method: 'POST', body: formData }),

    getFiles: (params = {}) => {
        const qs = new URLSearchParams(params).toString();
        return request(`/files/filter${qs ? '?' + qs : ''}`);
    },
    getFileData: (fileId, version, limit, offset) =>
        request(`/file-data/${fileId}?version=${version}&limit=${limit}&offset=${offset}`),

    // Корректировки
    createCorrection: (formData) => request('/corrections', { method: 'POST', body: formData }),
    applyCorrections: (fileId, appliedBy) => {
        const fd = new FormData();
        fd.append('applied_by', appliedBy);
        return request(`/apply-corrections/${fileId}`, { method: 'POST', body: fd });
    },
    getCorrectionLogs: (fileId) => {
        const url = fileId ? `/correction-logs?file_id=${fileId}` : '/correction-logs';
        return request(url);
    },

    // Балансы, счета
    getAccounts: () => request('/accounts'),
    getBalances: (asOfDate) => request(`/balances?as_of_date=${asOfDate}`),
    getAccountHistory: (accountNumber) => request(`/account/${accountNumber}/history`),

    // Регулятивные отчёты
    getRegulatoryCapital: () => request('/regulatory-capital'),
    getAssets: (asOfDate) => request(`/assets?as_of_date=${asOfDate}`),
    getLiabilities: (asOfDate) => request(`/liabilities?as_of_date=${asOfDate}`),
    getLiquidity: (asOfDate) => request(`/liquidity?as_of_date=${asOfDate}`),
    getLargeRisks: (asOfDate) => request(`/large-risks?as_of_date=${asOfDate}`),

    // Кредиты/депозиты
    getLoans: () => request('/loans'),
    getDeposits: () => request('/deposits'),
    getLoanProfit: (loanId, asOfDate) => {
        let url = `/loan-profit/${loanId}`;
        if (asOfDate) url += `?as_of_date=${asOfDate}`;
        return request(url);
    },
    applyLoanInterest: (loanId, asOfDate) => {
        const fd = new FormData();
        fd.append('as_of_date', asOfDate);
        return request(`/apply-loan-interest/${loanId}`, { method: 'POST', body: fd });
    },
    getDepositCost: (depositId, asOfDate) => {
        let url = `/deposit-cost/${depositId}`;
        if (asOfDate) url += `?as_of_date=${asOfDate}`;
        return request(url);
    },
    applyDepositInterest: (depositId, asOfDate) => {
        const fd = new FormData();
        fd.append('as_of_date', asOfDate);
        return request(`/apply-deposit-interest/${depositId}`, { method: 'POST', body: fd });
    },

    // Инструменты
    convertCurrency: (amount, fromCurr, toCurr, date, source) =>
        request(`/convert-currency?amount=${amount}&from_currency=${fromCurr}&to_currency=${toCurr}&date=${date}&source=${source}`),
    getFinancialSummaryInCurrency: (targetCurrency, asOfDate, source) =>
        request(`/financial-summary-in-currency?target_currency=${targetCurrency}&as_of_date=${asOfDate}&source=${source}`),
};