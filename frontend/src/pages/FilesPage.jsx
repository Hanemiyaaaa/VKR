import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import UploadForm from '../components/UploadForm';

export default function FilesPage() {
    const [files, setFiles] = useState([]);
    const [filters, setFilters] = useState({ user_name: '', business_date: '', upload_date: '' });
    const navigate = useNavigate();

    const loadFiles = async () => {
        try {
            const data = await api.getFiles(filters);
            setFiles(data);
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        loadFiles();
    }, [filters]);

    const handleFilterChange = (e) => {
        setFilters(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const clearFilters = () => {
        setFilters({ user_name: '', business_date: '', upload_date: '' });
    };

    return (
        <div className="files-page">
            <div className="upload-section">
                <UploadForm onUploadSuccess={loadFiles} />
            </div>

            <div className="filter-card">
                <h3>🔍 Фильтры файлов</h3>
                <div className="filters">
                    <div className="filter-group">
                        <label>Пользователь</label>
                        <input
                            type="text"
                            name="user_name"
                            placeholder="Например: Иван"
                            value={filters.user_name}
                            onChange={handleFilterChange}
                            title="Введите имя пользователя, загрузившего файл"
                        />
                    </div>
                    <div className="filter-group">
                        <label>Бизнес-дата</label>
                        <input
                            type="date"
                            name="business_date"
                            value={filters.business_date}
                            onChange={handleFilterChange}
                            title="Дата, к которой относятся данные в файле"
                        />
                    </div>
                    <div className="filter-group">
                        <label>Дата загрузки</label>
                        <input
                            type="date"
                            name="upload_date"
                            value={filters.upload_date}
                            onChange={handleFilterChange}
                            title="Дата, когда файл был загружен в систему"
                        />
                    </div>
                    <div className="filter-actions">
                        <button onClick={loadFiles}>Применить</button>
                        <button onClick={clearFilters} className="secondary">Сбросить</button>
                    </div>
                </div>
            </div>

            <h2>📁 Список файлов</h2>
            <div className="file-list">
                {files.length === 0 && <div className="empty-state">Нет файлов. Загрузите первый файл выше.</div>}
                {files.map(file => (
                    <div key={file.id} className="file-card" onClick={() => navigate(`/file/${file.id}`)}>
                        <div className="file-info">
                            <strong>{file.filename}</strong> <span className="file-id">ID: {file.id}</span>
                            <div className="file-meta">
                                <span>👤 {file.user_name}</span>
                                <span>📅 Загрузка: {new Date(file.upload_date).toLocaleDateString()}</span>
                                <span>🏢 Бизнес-дата: {file.business_date}</span>
                                <span>📂 Тип: {file.data_type || 'main'}</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}