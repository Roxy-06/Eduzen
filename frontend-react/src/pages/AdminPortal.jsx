import { useState, useEffect } from 'react';
import { api, clearCache } from '../api';
import { useToast } from '../App';

const ROLES = ['student', 'teacher'];

export default function AdminPortal({ user, currentNav }) {
    const toast = useToast();
    const [users, setUsers]     = useState([]);
    const [loading, setLoading] = useState(false);
    const [filter, setFilter]   = useState('all'); // all | teacher | student

    // Create form state
    const [name, setName]       = useState('');
    const [email, setEmail]     = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole]       = useState('student');
    const [dept, setDept]       = useState('');
    const [enrollNo, setEnrollNo] = useState('');
    const [selectedClassroomForUser, setSelectedClassroomForUser] = useState('');
    const [creating, setCreating] = useState(false);

    const loadUsers = async () => {
        setLoading(true);
        try {
            const [usrData, clsData] = await Promise.all([
                api.adminListUsers(user.id),
                api.fetchClassrooms()
            ]);
            setUsers(usrData.users || []);
            setClassroomsList(clsData || []);
            if (clsData && clsData.length > 0 && !selectedClassroomForUser) {
                setSelectedClassroomForUser(clsData[0].id.toString());
            }
        } catch (e) { toast(e.message, 'error'); }
        finally { setLoading(false); }
    };

    const [overview, setOverview] = useState([]);
    const [overviewLoading, setOverviewLoading] = useState(false);

    // ── Manage Subjects state ─────────────────────────────
    const [subjectsList, setSubjectsList]               = useState([]);
    const [subjectName, setSubjectName]                 = useState('');
    const [subjectCode, setSubjectCode]                 = useState('');
    const [creatingSubject, setCreatingSubject]         = useState(false);
    const [classroomsList, setClassroomsList]           = useState([]);
    const [assignClassId, setAssignClassId]             = useState('');
    const [assignSubjectId, setAssignSubjectId]         = useState('');
    const [assignTeacherId, setAssignTeacherId]         = useState('');
    const [assigningSubject, setAssigningSubject]       = useState(false);

    const loadOverview = async () => {
        setOverviewLoading(true);
        try {
            const data = await api.fetchAdminAttendanceOverview(user.id);
            setOverview(data.classrooms || []);
        } catch (e) { toast(e.message, 'error'); }
        finally { setOverviewLoading(false); }
    };

    const loadSubjectsData = async () => {
        try {
            const [subs, cls, usrData] = await Promise.all([
                api.fetchSubjects(),
                api.fetchClassrooms(),
                api.adminListUsers(user.id)
            ]);
            setSubjectsList(subs || []);
            setClassroomsList(cls || []);
            const teachers = (usrData.users || []).filter(u => u.role === 'teacher');
            if (cls && cls.length > 0 && !assignClassId) setAssignClassId(cls[0].id.toString());
            if (subs && subs.length > 0 && !assignSubjectId) setAssignSubjectId(subs[0].id.toString());
            if (teachers && teachers.length > 0 && !assignTeacherId) setAssignTeacherId(teachers[0].id.toString());
        } catch (e) { toast(e.message, 'error'); }
    };

    useEffect(() => { loadUsers(); }, []);
    useEffect(() => {
        if (currentNav === 'Attendance Overview') loadOverview();
        else if (currentNav === 'Manage Subjects') loadSubjectsData();
    }, [currentNav]);

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!name || !email || !password || !dept) {
            toast('Please complete all fields.', 'error'); return;
        }
        setCreating(true);
        try {
            const data = await api.adminCreateUser(user.id, {
                name,
                email,
                password,
                role,
                department: dept,
                enrollment_no: enrollNo || undefined,
                classroom_id: role === 'student' && selectedClassroomForUser ? parseInt(selectedClassroomForUser) : undefined
            });
            toast(`✓ ${data.user.name} created as ${role}.`, 'success');
            setName(''); setEmail(''); setPassword(''); setDept(''); setRole('student'); setEnrollNo('');
            clearCache();
            loadUsers();
        } catch (e) { toast(e.message, 'error'); }
        finally { setCreating(false); }
    };

    const handleUpdateStudentClassroom = async (studentUserId, newClassroomId) => {
        try {
            await api.updateStudentClassroom(user.id, studentUserId, newClassroomId);
            toast('✓ Student classroom updated successfully!', 'success');
            clearCache();
            setUsers(prev => prev.map(u => u.id === studentUserId ? { ...u, classroom_id: parseInt(newClassroomId) } : u));
        } catch (e) { toast(e.message, 'error'); }
    };

    const handleDelete = async (targetUser) => {
        if (!window.confirm(`Delete ${targetUser.name}? This cannot be undone.`)) return;
        try {
            await api.adminDeleteUser(user.id, targetUser.id);
            toast(`${targetUser.name} removed.`, 'info');
            clearCache();
            setUsers(prev => prev.filter(u => u.id !== targetUser.id));
        } catch (e) { toast(e.message, 'error'); }
    };

    const handleCreateSubject = async (e) => {
        e.preventDefault();
        if (!subjectName || !subjectCode) {
            toast('Please enter subject name and code.', 'error');
            return;
        }
        setCreatingSubject(true);
        try {
            const res = await api.createSubject(subjectName, subjectCode);
            toast(`✓ Subject '${res.subject.name} (${res.subject.code})' created successfully!`, 'success');
            setSubjectName('');
            setSubjectCode('');
            clearCache();
            loadSubjectsData();
        } catch (e) { toast(e.message, 'error'); }
        finally { setCreatingSubject(false); }
    };

    const handleAssignSubject = async (e) => {
        e.preventDefault();
        if (!assignClassId || !assignSubjectId || !assignTeacherId) {
            toast('Please select classroom, subject, and teacher.', 'error');
            return;
        }
        setAssigningSubject(true);
        try {
            await api.assignSubjectToClassroom(assignClassId, assignSubjectId, assignTeacherId);
            toast('✓ Subject assigned to classroom and teacher!', 'success');
            clearCache();
        } catch (e) { toast(e.message, 'error'); }
        finally { setAssigningSubject(false); }
    };

    const filtered = filter === 'all' ? users : users.filter(u => u.role === filter);
    const teacherCount = users.filter(u => u.role === 'teacher').length;
    const studentCount = users.filter(u => u.role === 'student').length;

    return (
        <div>
            {/* Hero */}
            <div className="hero-banner">
                <div className="hero-badge" style={{ background: 'rgba(253,224,71,0.15)', borderColor: 'rgba(253,224,71,0.3)', color: '#fde047' }}>
                    🛡 Admin Control Panel
                </div>
                <div className="hero-title">Institution Management</div>
                <div className="hero-subtitle">
                    Create, manage and remove teacher & student accounts across your institution.
                </div>
            </div>

            {/* Stats */}
            <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                {[
                    { icon: '👥', label: 'Total Users',  value: users.length,   caption: 'Teachers + students' },
                    { icon: '🎓', label: 'Teachers',     value: teacherCount,   caption: 'Faculty accounts' },
                    { icon: '📚', label: 'Students',     value: studentCount,   caption: 'Student accounts' },
                ].map(m => (
                    <div className="metric-card" key={m.label}>
                        <div className="metric-icon">{m.icon}</div>
                        <div className="metric-label">{m.label}</div>
                        <div className="metric-value" style={{ background: 'linear-gradient(135deg, #fde047, #f59e0b)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>{m.value}</div>
                        <div className="metric-caption">{m.caption}</div>
                    </div>
                ))}
            </div>

            {/* Create User */}
            {currentNav === 'Create User' && (
                <div className="content-card">
                    <div className="card-title">➕ Create New Account</div>
                    <p className="text-caption" style={{ marginBottom: '20px' }}>
                        Create a teacher or student account. Share credentials with them directly.
                    </p>
                    <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Full Name</label>
                            <input type="text" className="input-control" placeholder="e.g. Dr. Sarah Lee"
                                value={name} onChange={e => setName(e.target.value)} />
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Email Address</label>
                            <input type="email" className="input-control" placeholder="sarah@university.edu"
                                value={email} onChange={e => setEmail(e.target.value)} />
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Temporary Password</label>
                            <input type="text" className="input-control" placeholder="e.g. Welcome@2026"
                                value={password} onChange={e => setPassword(e.target.value)} />
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Department</label>
                            <input type="text" className="input-control" placeholder="e.g. Computer Science"
                                value={dept} onChange={e => setDept(e.target.value)} />
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Role</label>
                            <select className="input-control" value={role} onChange={e => setRole(e.target.value)}>
                                <option value="student">Student</option>
                                <option value="teacher">Teacher</option>
                            </select>
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>
                                {role === 'student' ? 'Enrollment Number' : 'Faculty ID'}
                                {' '}<span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional — auto-generated if blank)</span>
                            </label>
                            <input type="text" className="input-control"
                                placeholder={role === 'student' ? 'e.g. 22CE001' : 'e.g. FAC001'}
                                value={enrollNo} onChange={e => setEnrollNo(e.target.value)} />
                        </div>
                        {role === 'student' && (
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Assign Classroom / Semester</label>
                                <select className="input-control" value={selectedClassroomForUser} onChange={e => setSelectedClassroomForUser(e.target.value)}>
                                    <option value="">Select Classroom / Semester...</option>
                                    {classroomsList.map(c => (
                                        <option key={c.id} value={c.id}>🏫 {c.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                        <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                            <button type="submit" className="btn btn-primary btn-full" disabled={creating}
                                style={{ background: 'linear-gradient(135deg, #d97706, #b45309)', boxShadow: '0 4px 14px rgba(217,119,6,0.35)' }}>
                                {creating ? <><span className="spinner" /> Creating...</> : `➕ Create ${role.charAt(0).toUpperCase() + role.slice(1)}`}
                            </button>
                        </div>
                    </form>
                </div>
            )}


            {/* User Management */}
            {currentNav === 'User Management' && (
                <div className="content-card">
                    <div className="card-title">👥 All Users</div>

                    {/* Filter tabs */}
                    <div className="tabs-header">
                        {['all', 'teacher', 'student'].map(f => (
                            <button key={f} className={`tab-btn ${filter === f ? 'active' : ''}`}
                                onClick={() => setFilter(f)}>
                                {f === 'all' ? 'All Users' : f === 'teacher' ? '🎓 Teachers' : '📚 Students'}
                                <span style={{ marginLeft: 6, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                    ({f === 'all' ? users.length : users.filter(u => u.role === f).length})
                                </span>
                            </button>
                        ))}
                    </div>

                    {loading ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)', padding: '20px 0' }}>
                            <span className="spinner" /> Loading users...
                        </div>
                    ) : filtered.length === 0 ? (
                        <div className="alert alert-info">ℹ No {filter === 'all' ? '' : filter} accounts yet. Create one above.</div>
                    ) : (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Classroom / Semester</th>
                                    <th>Department</th>
                                    <th>Created</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map(u => (
                                    <tr key={u.id}>
                                        <td>
                                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.name}</div>
                                        </td>
                                        <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{u.email}</td>
                                        <td>
                                            <span className={`text-badge ${u.role === 'teacher' ? 'badge-dark' : 'badge-success'}`}>
                                                {u.role.toUpperCase()}
                                            </span>
                                        </td>
                                        <td>
                                            {u.role === 'student' ? (
                                                <select
                                                    className="input-control"
                                                    style={{ padding: '4px 8px', fontSize: '0.82rem', width: 'auto' }}
                                                    value={u.classroom_id || ''}
                                                    onChange={e => handleUpdateStudentClassroom(u.id, e.target.value)}
                                                >
                                                    <option value="">Unassigned</option>
                                                    {classroomsList.map(c => (
                                                        <option key={c.id} value={c.id}>🏫 {c.name}</option>
                                                    ))}
                                                </select>
                                            ) : (
                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Faculty</span>
                                            )}
                                        </td>
                                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>{u.department}</td>
                                        <td style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                                            {new Date(u.created_at).toLocaleDateString()}
                                        </td>
                                        <td>
                                            <button
                                                className="btn btn-danger btn-sm"
                                                onClick={() => handleDelete(u)}
                                            >
                                                🗑 Remove
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {/* Dashboard */}
            {currentNav === 'Dashboard' && (
                <div className="content-card">
                    <div className="card-title">🛡 Admin Dashboard</div>
                    <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                        You are logged in as the <strong>SVMIT Administrator</strong>. Your responsibilities:
                    </p>
                    <ul style={{ color: 'var(--text-secondary)', lineHeight: 2, marginTop: '10px', paddingLeft: '20px' }}>
                        <li>Create and manage <strong>teacher</strong> and <strong>student</strong> accounts</li>
                        <li>Remove accounts when no longer needed</li>
                        <li>Ensure each teacher is assigned to the correct classroom (via Classroom Administration)</li>
                        <li>All account credentials are shared with users directly by you</li>
                    </ul>
                    <div className="alert alert-warning" style={{ marginTop: '16px' }}>
                        ⚠ Public self-registration is <strong>disabled</strong>. Only you can create accounts on this platform.
                    </div>
                    <div style={{ marginTop: '16px', display: 'flex', gap: '10px' }}>
                        <div style={{ flex: 1, background: 'rgba(217,119,6,0.1)', border: '1px solid rgba(217,119,6,0.3)', borderRadius: 'var(--radius-sm)', padding: '16px', textAlign: 'center' }}>
                            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fbbf24' }}>{teacherCount}</div>
                            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Faculty Members</div>
                        </div>
                        <div style={{ flex: 1, background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)', borderRadius: 'var(--radius-sm)', padding: '16px', textAlign: 'center' }}>
                            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#6ee7b7' }}>{studentCount}</div>
                            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Enrolled Students</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Manage Subjects */}
            {currentNav === 'Manage Subjects' && (
                <div>
                    <div className="content-card" style={{ marginBottom: '20px' }}>
                        <div className="card-title">📖 Add New Subject</div>
                        <form onSubmit={handleCreateSubject} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '14px', alignItems: 'flex-end' }}>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Subject Name</label>
                                <input type="text" className="input-control" placeholder="e.g. Machine Learning"
                                    value={subjectName} onChange={e => setSubjectName(e.target.value)} />
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Subject Code</label>
                                <input type="text" className="input-control" placeholder="e.g. CS402"
                                    value={subjectCode} onChange={e => setSubjectCode(e.target.value)} />
                            </div>
                            <button type="submit" className="btn btn-primary" disabled={creatingSubject} style={{ background: 'linear-gradient(135deg, #1d4ed8, #1e40af)' }}>
                                {creatingSubject ? <><span className="spinner" /> Creating...</> : '➕ Create Subject'}
                            </button>
                        </form>
                    </div>

                    <div className="content-card" style={{ marginBottom: '20px' }}>
                        <div className="card-title">🔗 Assign Subject to Classroom &amp; Teacher</div>
                        <form onSubmit={handleAssignSubject} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '14px', alignItems: 'flex-end' }}>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Select Classroom</label>
                                <select className="input-control" value={assignClassId} onChange={e => setAssignClassId(e.target.value)}>
                                    {classroomsList.map(c => (
                                        <option key={c.id} value={c.id}>🏫 {c.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Select Subject</label>
                                <select className="input-control" value={assignSubjectId} onChange={e => setAssignSubjectId(e.target.value)}>
                                    {subjectsList.map(s => (
                                        <option key={s.id} value={s.id}>📖 {s.name} ({s.code})</option>
                                    ))}
                                </select>
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Assigned Teacher</label>
                                <select className="input-control" value={assignTeacherId} onChange={e => setAssignTeacherId(e.target.value)}>
                                    {users.filter(u => u.role === 'teacher').map(t => (
                                        <option key={t.id} value={t.id}>🎓 {t.name}</option>
                                    ))}
                                </select>
                            </div>
                            <button type="submit" className="btn btn-teal" disabled={assigningSubject}>
                                {assigningSubject ? <><span className="spinner" /> Assigning...</> : '🔗 Assign Subject'}
                            </button>
                        </form>
                    </div>

                    <div className="content-card">
                        <div className="card-title">📚 All Course Subjects</div>
                        {subjectsList.length > 0 ? (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Subject Name</th>
                                        <th>Subject Code</th>
                                        <th>Subject ID</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {subjectsList.map(s => (
                                        <tr key={s.id}>
                                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>📖 {s.name}</td>
                                            <td><span className="text-badge badge-dark">{s.code}</span></td>
                                            <td style={{ color: 'var(--text-muted)' }}>#{s.id}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="alert alert-info">ℹ No subjects found. Create your first subject above.</div>
                        )}
                    </div>
                </div>
            )}
            {/* Attendance Overview */}
            {currentNav === 'Attendance Overview' && (
                <div>
                    {overviewLoading ? (
                        <div className="content-card">
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)' }}>
                                <span className="spinner" /> Loading attendance data...
                            </div>
                        </div>
                    ) : overview.length === 0 ? (
                        <div className="content-card">
                            <div className="alert alert-info">ℹ No classroom data available yet.</div>
                        </div>
                    ) : overview.map(cls => (
                        <div className="content-card" key={cls.classroom_id} style={{ marginBottom: '16px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <div>
                                    <div className="card-title" style={{ marginBottom: 0 }}>🏫 {cls.classroom_name}</div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: '4px' }}>
                                        {cls.student_count} student{cls.student_count !== 1 ? 's' : ''} enrolled
                                    </div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>Overall Attendance</div>
                                    <div style={{
                                        fontFamily: 'Outfit', fontSize: '1.6rem', fontWeight: 800,
                                        color: cls.overall_attendance_pct < 75 ? '#fca5a5' : '#6ee7b7',
                                    }}>
                                        {cls.overall_attendance_pct}%
                                    </div>
                                </div>
                            </div>

                            {/* Overall progress bar */}
                            <div className="progress-bar-bg" style={{ height: '10px', marginBottom: '20px' }}>
                                <div
                                    className={`progress-bar-fill ${cls.overall_attendance_pct < 75 ? 'danger' : ''}`}
                                    style={{ width: `${Math.min(100, cls.overall_attendance_pct)}%` }}
                                />
                            </div>

                            {/* Per-subject breakdown */}
                            {cls.subjects.length > 0 ? (
                                <table className="data-table">
                                    <thead><tr>
                                        <th>Subject</th>
                                        <th>Code</th>
                                        <th>Sessions Held</th>
                                        <th>Avg Attendance</th>
                                        <th style={{ width: '180px' }}>Progress</th>
                                    </tr></thead>
                                    <tbody>
                                        {cls.subjects.map(sub => (
                                            <tr key={sub.subject_id}>
                                                <td><strong style={{ color: 'var(--text-primary)' }}>{sub.subject_name}</strong></td>
                                                <td style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>{sub.subject_code}</td>
                                                <td style={{ textAlign: 'center' }}>{sub.sessions_held}</td>
                                                <td>
                                                    <span className={`text-badge ${sub.avg_attendance_pct < 75 ? 'badge-absent' : 'badge-present'}`}>
                                                        {sub.avg_attendance_pct}%
                                                    </span>
                                                </td>
                                                <td>
                                                    <div className="progress-bar-bg" style={{ height: '7px' }}>
                                                        <div
                                                            className={`progress-bar-fill ${sub.avg_attendance_pct < 75 ? 'danger' : ''}`}
                                                            style={{ width: `${Math.min(100, sub.avg_attendance_pct)}%` }}
                                                        />
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <p className="text-caption">No subjects assigned to this classroom yet.</p>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
