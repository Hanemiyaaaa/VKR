import { useState } from 'react';
import { api } from '../api/client';

const dataTypes = [
    { value: 'main', label: 'Основные данные' },
    { value: 'accounts', label: 'Счета' },
    { value: 'initial_balances', label: 'Начальные остатки' },
    { value: 'transactions', label: 'Операции' },
    { value: 'loans', label: 'Кредиты' },
    { value: 'deposits', label: 'Депозиты' },
    { value: 'capital', label: 'Капитал' },
    { value: 'exchange_rates', label: 'Курсы валют' },
    { value: 'bonds', label: 'Облигации' },
];

export default function UploadForm({ onSuccess }) {
    const [file, setFile] = useState(null);
    const [businessDate, setBusinessDate] = useState('');
    const [userName, setUserName] = useState('');
    const [dataType, setDataType] = useState('main');
    const [loading, setLoading] = useState(false);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        setFile(selectedFile);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file || !businessDate || !userName) {
            alert('Заполните все поля');
            return;
        }
        const fd = new FormData();
        fd.append('file', file);
        fd.append('business_date', businessDate);
        fd.append('user_name', userName);
        setLoading(true);
        try {
            const uploadMap = {
                main: api.uploadFile,
                accounts: api.uploadAccounts,
                initial_balances: api.uploadInitialBalances,
                transactions: api.uploadTransactions,
                loans: api.uploadLoans,
                deposits: api.uploadDeposits,
                capital: api.uploadCapital,
                exchange_rates: api.uploadExchangeRates,
                bonds: api.uploadBonds,
            };
            await uploadMap[dataType](fd);
            alert('Файл загружен');
            if (onSuccess) onSuccess();
            setFile(null);
            setBusinessDate('');
            setUserName('');
            // Сбросить значение file input (чтобы имя файла исчезло)
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.value = '';
        } catch (err) {
            alert('Ошибка: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="upload-form">
            <div className="file-input-wrapper">
                <label htmlFor="fileInput" className="file-label">
                    📁 Выбрать файл
                </label>
                <input
                    id="fileInput"
                    type="file"
                    className="file-input"
                    onChange={handleFileChange}
                    required
                />
                <span className="file-name">{file ? file.name : 'Файл не выбран'}</span>
            </div>

            <input
                type="date"
                value={businessDate}
                onChange={(e) => setBusinessDate(e.target.value)}
                required
                placeholder="Бизнес-дата"
            />
            <input
                type="text"
                placeholder="Ваше имя"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                required
            />
            <select value={dataType} onChange={(e) => setDataType(e.target.value)}>
                {dataTypes.map((dt) => (
                    <option key={dt.value} value={dt.value}>
                        {dt.label}
                    </option>
                ))}
            </select>
            <button type="submit" disabled={loading}>
                {loading ? 'Загрузка...' : 'Загрузить'}
            </button>
        </form>
    );
}