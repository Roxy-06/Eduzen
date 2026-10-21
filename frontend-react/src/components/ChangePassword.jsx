import { useState } from 'react';
import { api } from '../api';
import { useToast } from '../App';

export default function ChangePassword({ user }) {
    const toast = useToast();
    const [current,  setCurrent]  = useState('');
    const [newPass,  setNewPass]  = useState('');
    const [confirm,  setConfirm]  = useState('');
    const [loading,  setLoading]  = useState(false);
    const [strength, setStrength] = useState(0); // 0-4

    const calcStrength = (val) => {
        let score = 0;
        if (val.length >= 8)               score++;
        if (/[A-Z]/.test(val))             score++;
        if (/[0-9]/.test(val))             score++;
        if (/[^A-Za-z0-9]/.test(val))     score++;
        return score;
    };

    const handleNewPass = (val) => {
        setNewPass(val);
        setStrength(calcStrength(val));
    };

    const strengthLabel = ['', 'Weak', 'Fair', 'Good', 'Strong'][strength];
    const strengthColor = ['', '#ef4444', '#f59e0b', '#3b82f6', '#10b981'][strength];

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!current || !newPass || !confirm) {
            toast('Please fill in all fields.', 'error'); return;
        }
        if (newPass !== confirm) {
            toast('New passwords do not match.', 'error'); return;
        }
        if (newPass.length < 6) {
            toast('New password must be at least 6 characters.', 'error'); return;
        }
        if (newPass === current) {
            toast('New password must be different from current.', 'error'); return;
        }
        setLoading(true);
        try {
            await api.changePassword(user.id, current, newPass);
            toast('✓ Password changed successfully!', 'success');
            setCurrent(''); setNewPass(''); setConfirm(''); setStrength(0);
        } catch (err) {
            toast(err.message || 'Password change failed.', 'error');
        } finally { setLoading(false); }
    };

    return (
        <div className="content-card" style={{ maxWidth: '480px' }}>
            <div className="card-title">🔑 Change Password</div>
            <p className="text-caption" style={{ marginBottom: '20px' }}>
                Choose a strong password that you haven't used before.
            </p>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Current password */}
                <div className="input-group" style={{ marginBottom: 0 }}>
                    <label>Current Password</label>
                    <input
                        type="password"
                        className="input-control"
                        placeholder="Enter your current password"
                        value={current}
                        onChange={e => setCurrent(e.target.value)}
                        autoComplete="current-password"
                    />
                </div>

                {/* New password */}
                <div className="input-group" style={{ marginBottom: 0 }}>
                    <label>New Password</label>
                    <input
                        type="password"
                        className="input-control"
                        placeholder="At least 6 characters"
                        value={newPass}
                        onChange={e => handleNewPass(e.target.value)}
                        autoComplete="new-password"
                    />
                    {/* Strength bar */}
                    {newPass && (
                        <div style={{ marginTop: '8px' }}>
                            <div style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
                                {[1,2,3,4].map(i => (
                                    <div key={i} style={{
                                        flex: 1, height: '4px', borderRadius: '4px',
                                        background: i <= strength ? strengthColor : 'var(--border)',
                                        transition: 'background 0.3s ease',
                                    }} />
                                ))}
                            </div>
                            <span style={{ fontSize: '0.75rem', color: strengthColor, fontWeight: 600 }}>
                                {strengthLabel}
                            </span>
                        </div>
                    )}
                </div>

                {/* Confirm */}
                <div className="input-group" style={{ marginBottom: 0 }}>
                    <label>Confirm New Password</label>
                    <input
                        type="password"
                        className="input-control"
                        placeholder="Re-enter new password"
                        value={confirm}
                        onChange={e => setConfirm(e.target.value)}
                        autoComplete="new-password"
                        style={{
                            borderColor: confirm && newPass
                                ? confirm === newPass ? 'rgba(16,185,129,0.6)' : 'rgba(239,68,68,0.6)'
                                : undefined
                        }}
                    />
                    {confirm && newPass && (
                        <div style={{
                            fontSize: '0.78rem',
                            marginTop: '5px',
                            color: confirm === newPass ? '#6ee7b7' : '#fca5a5',
                            fontWeight: 500,
                        }}>
                            {confirm === newPass ? '✓ Passwords match' : '✕ Passwords do not match'}
                        </div>
                    )}
                </div>

                <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                    style={{ marginTop: '4px', alignSelf: 'flex-start', minWidth: '180px' }}
                >
                    {loading ? <><span className="spinner" /> Updating...</> : '🔑 Update Password'}
                </button>
            </form>

            <div className="divider" style={{ marginTop: '24px' }} />
            <p className="text-caption">
                Tips: Use a mix of uppercase, numbers, and symbols for a strong password.
            </p>
        </div>
    );
}
