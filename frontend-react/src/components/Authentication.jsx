import { useState } from 'react';
import { api, setToken, clearCache } from '../api';
import { useToast } from '../App';

export default function Authentication({ onLogin }) {
    const toast = useToast();
    const [loading, setLoading]         = useState(false);
    const [loginEmail, setLoginEmail]   = useState('');
    const [loginPassword, setLoginPassword] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        if (!loginEmail || !loginPassword) { toast('Please fill in all fields.', 'error'); return; }
        setLoading(true);
        try {
            const data = await api.login(loginEmail, loginPassword);
            setToken(data.access_token);
            clearCache();
            toast(`Welcome back, ${data.user.name}! 👋`, 'success');
            onLogin(data.user);
        } catch (err) {
            toast(err.message || 'Invalid credentials.', 'error');
        } finally { setLoading(false); }
    };

    return (
        <div className="auth-page">
            <div className="auth-container">
                {/* Header */}
                <div className="auth-header">
                    <div className="auth-logo">SVMIT</div>
                </div>

                <div className="auth-card">

                    <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Email Address</label>
                            <input type="email" className="input-control" placeholder="you@university.edu"
                                value={loginEmail} onChange={e => setLoginEmail(e.target.value)} />
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Password</label>
                            <input type="password" className="input-control" placeholder="••••••••"
                                value={loginPassword} onChange={e => setLoginPassword(e.target.value)} />
                        </div>
                        <button type="submit" className="btn btn-primary btn-full" disabled={loading} style={{ marginTop: '6px' }}>
                            {loading ? <><span className="spinner" /> Authenticating...</> : '→ Access Portal'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
