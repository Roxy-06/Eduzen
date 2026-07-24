import { api } from '../api';

export default function Sidebar({ user, onLogout, navItems, currentNav, onNavChange }) {

    const handleLogout = () => {
        // Clear API cache when logging out
        import('../api').then(({ clearCache }) => clearCache());
        onLogout();
    };

    return (
        <div className="sidebar">
            <h2>EduZen</h2>
            <div className="sidebar-caption">System Dashboard v2.0</div>
            <div className="divider"></div>

            <div className="profile-card">
                <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>CURRENT USER</div>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '2px' }}>{user.name}</div>
                <div style={{ marginTop: '6px' }}>
                    <span className="text-badge badge-primary">{user.role.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: '0.8rem', marginTop: '8px' }}>Department: {user.department}</div>
            </div>

            <div className="nav-label">Navigate</div>
            <div className="sidebar-nav">
                {navItems.map(item => (
                    <div
                        key={item}
                        className={`nav-item ${currentNav === item ? 'active' : ''}`}
                        onClick={() => onNavChange(item)}
                    >
                        {item}
                    </div>
                ))}
            </div>

            <div className="divider" style={{ marginTop: 'auto' }}></div>
            <button onClick={handleLogout} className="btn btn-primary btn-full">
                Sign Out
            </button>
        </div>
    );
}
