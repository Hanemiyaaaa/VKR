import { Link, useLocation } from 'react-router-dom';

export default function Layout({ children }) {
    const location = useLocation();
    const navItems = [
        { path: '/files', label: 'Файлы', icon: '📁' },
        { path: '/balances', label: 'Балансы', icon: '💰' },
        { path: '/regulatory', label: 'Отчёты', icon: '📊' },
        { path: '/loans-deposits', label: 'Кредиты/Депозиты', icon: '💳' },
        { path: '/tools', label: 'Инструменты', icon: '⚙️' },
    ];

    return (
        <div className="app-layout">
            <header className="app-header">
                <div className="header-container">
                    <h1>📋 Управление данными</h1>
                    <nav className="main-nav">
                        {navItems.map(item => (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
                            >
                                <span className="nav-icon">{item.icon}</span>
                                <span className="nav-label">{item.label}</span>
                            </Link>
                        ))}
                    </nav>
                </div>
            </header>
            <main className="app-main">{children}</main>
        </div>
    );
}