import { useState } from 'react';
import { api } from '../api';

export default function Authentication({ onLogin }) {
    const [activeTab, setActiveTab] = useState('signin');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Login State
    const [loginEmail, setLoginEmail] = useState('');
    const [loginPassword, setLoginPassword] = useState('');

    // Register State
    const [regName, setRegName] = useState('');
    const [regEmail, setRegEmail] = useState('');
    const [regPassword, setRegPassword] = useState('');
    const [regRole, setRegRole] = useState('student');
    const [regDept, setRegDept] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        if (!loginEmail || !loginPassword) {
            setError('Please enter complete login credentials.');
            return;
        }
        setLoading(true);
        setError('');
        try {
            const data = await api.login(loginEmail, loginPassword);
            onLogin(data.user);
        } catch (err) {
            setError(err.message || 'Invalid credentials provided.');
        } finally {
            setLoading(false);
        }
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        if (!regName || !regEmail || !regPassword || !regDept) {
            setError('Please complete all required fields.');
            return;
        }
        setLoading(true);
        setError('');
        try {
            const data = await api.register({
                name: regName,
                email: regEmail,
                password: regPassword,
                role: regRole,
                department: regDept
            });
            setSuccess('Account successfully created.');
            setTimeout(() => onLogin(data.user), 1000); // Auto login
        } catch (err) {
            setError(err.message || 'Registration failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="main-content" style={{ maxWidth: '800px', margin: '40px auto' }}>
            <div className="hero-banner">
                <span className="text-badge badge-dark" style={{ marginBottom: '10px' }}>ACADEMIC MANAGEMENT PLATFORM</span>
                <div className="hero-title">EduZen Unified Portal</div>
                <div className="hero-subtitle">Role-based workspace for instruction, curriculum intelligence, and learning analytics.</div>
            </div>

            <div className="content-card">
                <div className="tabs-header">
                    <button
                        className={`tab-btn ${activeTab === 'signin' ? 'active' : ''}`}
                        onClick={() => { setActiveTab('signin'); setError(''); }}
                    >
                        Sign In
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'register' ? 'active' : ''}`}
                        onClick={() => { setActiveTab('register'); setError(''); }}
                    >
                        Register Account
                    </button>
                </div>

                {error && <div className="alert alert-error">{error}</div>}
                {success && <div className="alert alert-success">{success}</div>}

                {activeTab === 'signin' ? (
                    <div>
                        <p className="text-caption mb-4">Access your registered teacher or student profile.</p>

                        <details style={{ marginBottom: '1rem' }}>
                            <summary className="text-caption" style={{ cursor: 'pointer' }}>Demo accounts already in the database</summary>
                            <div style={{ padding: '10px', fontSize: '0.85rem', backgroundColor: '#f8fafc', borderRadius: '6px', marginTop: '10px' }}>
                                <strong>Teachers</strong> (Password: <code>teacher123</code>)<br />
                                - teacher@eduzone.com<br />
                                - reyes@eduzone.com<br />
                                - nair@eduzone.com<br /><br />
                                <strong>Students</strong> (Password: <code>student123</code>)<br />
                                - student@eduzone.com<br />
                                - karan.mehta@eduzone.com<br />
                                - and others...
                            </div>
                        </details>

                        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Email Address</label>
                                <input
                                    type="email"
                                    className="input-control"
                                    value={loginEmail}
                                    onChange={(e) => setLoginEmail(e.target.value)}
                                />
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Password</label>
                                <input
                                    type="password"
                                    className="input-control"
                                    value={loginPassword}
                                    onChange={(e) => setLoginPassword(e.target.value)}
                                />
                            </div>
                            <button type="submit" className="btn btn-primary btn-full" disabled={loading} style={{ marginTop: '1rem' }}>
                                {loading ? 'Authenticating...' : 'Access Portal'}
                            </button>
                        </form>
                    </div>
                ) : (
                    <div>
                        <p className="text-caption mb-4">Create a new institutional profile.</p>
                        <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Full Name</label>
                                <input type="text" className="input-control" value={regName} onChange={e => setRegName(e.target.value)} />
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Email Address</label>
                                <input type="email" className="input-control" value={regEmail} onChange={e => setRegEmail(e.target.value)} />
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Create Password</label>
                                <input type="password" className="input-control" value={regPassword} onChange={e => setRegPassword(e.target.value)} />
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Role Assignment</label>
                                <select className="input-control" value={regRole} onChange={e => setRegRole(e.target.value)}>
                                    <option value="student">Student</option>
                                    <option value="teacher">Teacher</option>
                                </select>
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Academic Department</label>
                                <input type="text" className="input-control" value={regDept} onChange={e => setRegDept(e.target.value)} />
                            </div>
                            <button type="submit" className="btn btn-primary btn-full" disabled={loading} style={{ marginTop: '1rem' }}>
                                {loading ? 'Creating...' : 'Create Account'}
                            </button>
                        </form>
                    </div>
                )}
            </div>
        </div>
    );
}
