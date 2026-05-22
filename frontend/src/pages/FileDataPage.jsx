import { useParams } from 'react-router-dom';
import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';

export default function FileDataPage() {
    const { fileId } = useParams();
    const [version, setVersion] = useState('original');
    const [rows, setRows] = useState([]);
    const [offset, setOffset] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [loading, setLoading] = useState(false);
    const observerRef = useRef(null);
    const limit = 500;

    const loadMore = useCallback(async () => {
        if (loading || !hasMore) return;
        setLoading(true);
        try {
            const data = await api.getFileData(Number(fileId), version, limit, offset);
            if (data.length === 0) {
                setHasMore(false);
            } else {
                setRows(prev => (offset === 0 ? data : [...prev, ...data]));
                setOffset(prev => prev + data.length);
            }
        } catch (err) {
            console.error(err);
            alert('Ошибка загрузки данных: ' + err.message);
        } finally {
            setLoading(false);
        }
    }, [fileId, version, offset, loading, hasMore]);

    useEffect(() => {
        setRows([]);
        setOffset(0);
        setHasMore(true);
    }, [fileId, version]);

    useEffect(() => {
        loadMore();
    }, [loadMore]);

    useEffect(() => {
        if (!observerRef.current) return;
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && !loading && hasMore) {
                    loadMore();
                }
            },
            { threshold: 0.1 }
        );
        observer.observe(observerRef.current);
        return () => observer.disconnect();
    }, [observerRef.current, loading, hasMore, loadMore]);

    const statusText = hasMore
        ? `Загружено ${rows.length} строк. Прокрутите для загрузки ещё...`
        : `✅ Все данные загружены (${rows.length} строк)`;

    return (
        <div>
            <div className="data-card">
                <h3>📄 Данные файла #{fileId}</h3>
                <div className="filters" style={{ marginBottom: '0.8rem', justifyContent: 'space-between' }}>
                    <div className="filter-group">
                        <label>ВЕРСИЯ</label>
                        <select value={version} onChange={(e) => setVersion(e.target.value)}>
                            <option value="original">Исходная</option>
                            <option value="corrected">Скорректированная</option>
                        </select>
                    </div>
                    <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center' }}>
                        <div className="status-info" style={{ fontSize: '0.75rem', color: '#6b5b95' }}>
                            {loading ? 'Загрузка...' : statusText}
                        </div>
                        <div className="filter-actions">
                            <button
                                onClick={() => {
                                    setRows([]);
                                    setOffset(0);
                                    setHasMore(true);
                                    loadMore();
                                }}
                            >
                                Обновить
                            </button>
                        </div>
                    </div>
                </div>
                <div className="table-container">
                    <DataTable rows={rows} />
                </div>
                {/* Невидимый триггер для подгрузки */}
                {hasMore && <div ref={observerRef} style={{ height: '20px', marginTop: '0.5rem' }} />}
            </div>
        </div>
    );
}