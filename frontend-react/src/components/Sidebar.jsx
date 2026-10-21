import { clearCache } from '../api';
import { useToast } from '../App';

export default function Sidebar({ user, onLogout, navItems, currentNav, onNavChange, role }) {
    const toast = useToast();
    const isTeacher = role === 'teacher';

    const handleLogout = () => {
        clearCache();
        toast('Signed out successfully.', 'info');
        onLogout();
    };

    const initials = user.name
        .split(' ')
        .map(w => w[0])
        .join('')
        .slice(0, 2)
        .toUpperCase();

    return (
        <div className="sidebar">
            {/* Logo */}
            <div className="sidebar-logo">SVMIT</div>
            <div className="sidebar-version">Academic ERP · v2.0</div>
            <div className="divider" />

            {/* Profile */}
            <div className="profile-card">
                <div className="profile-avatar">{initials}</div>
                <div className="profile-name">{user.name}</div>
                <div className="profile-meta">
                    <span className={`text-badge ${isTeacher ? 'badge-dark' : 'badge-success'}`}>
                        {user.role.toUpperCase()}
                    </span>
                </div>
                <div className="profile-meta" style={{ marginTop: '6px' }}>
                    {user.department}
                </div>
            </div>

            {/* Nav */}
            <div className="nav-label">Navigation</div>
            <div className="sidebar-nav">
                {navItems.map(item => {
                    const label = typeof item === 'string' ? item : item.label;
                    const emoji = typeof item === 'string' ? '' : item.emoji;
                    const isActive = currentNav === label;
                    return (
                        <div
                            key={label}
                            className={`nav-item ${isActive ? `active ${!isTeacher ? 'teal-active' : ''}` : ''}`}
                            onClick={() => onNavChange(label)}
                        >
                            {emoji && <span className="nav-emoji">{emoji}</span>}
                            {label}
                        </div>
                    );
                })}
            </div>

            {/* Logout */}
            <div className="divider" style={{ marginTop: 'auto' }} />
            <button onClick={handleLogout} className="btn btn-danger btn-full">
                ↩ Sign Out
            </button>
        </div>
    );
}
