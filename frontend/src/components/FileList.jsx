import { useNavigate } from 'react-router-dom';

export default function FileList({ files }) {
    const navigate = useNavigate();

    return (
        <div className="file-list">
            {files.map(file => (
                <div key={file.id} className="file-card" onClick={() => navigate(`/file/${file.id}`)}>
                    <div>
                        <strong>{file.filename}</strong> (ID: {file.id})
                        <div>Пользователь: {file.user_name}</div>
                        <div>Бизнес-дата: {file.business_date}</div>
                        <div>Загрузка: {new Date(file.upload_date).toLocaleDateString()}</div>
                    </div>
                </div>
            ))}
        </div>
    );
}