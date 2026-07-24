import { useState, useEffect } from 'react';
import { api } from '../api';

export default function TeacherPortal({ user, currentNav }) {
    const [dashboard, setDashboard] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // States for sub-components
    const [myClasses, setMyClasses] = useState([]);
    const [selectedClassId, setSelectedClassId] = useState('');
    const [todaySession, setTodaySession] = useState(null);
    const [roster, setRoster] = useState([]);
    const [attendanceRecords, setAttendanceRecords] = useState({});
    const [attendanceSummary, setAttendanceSummary] = useState([]);

    // States for course Material
    const [uploading, setUploading] = useState(false);
    const [materials, setMaterials] = useState([]);

    // States for Admin
    const [newClassName, setNewClassName] = useState('');
    const [allClassrooms, setAllClassrooms] = useState([]);
    const [adminSelectedClass, setAdminSelectedClass] = useState('');
    const [enrollName, setEnrollName] = useState('');
    const [enrollId, setEnrollId] = useState('');
    const [enrollEmail, setEnrollEmail] = useState('');
    const [adminRoster, setAdminRoster] = useState([]);

    useEffect(() => {
        fetchDashboard();
    }, [user.id]);

    const fetchDashboard = async () => {
        try {
            const data = await api.fetchTeacherDashboard(user.id);
            setDashboard(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (currentNav === 'Take Attendance') {
            loadTeacherClasses();
        } else if (currentNav === 'Course Material') {
            loadMaterials();
        } else if (currentNav === 'Classroom Administration') {
            loadAllClassrooms();
        }
    }, [currentNav]);

    const loadTeacherClasses = async () => {
        try {
            const classes = await api.fetchTeacherClasses(user.id);
            setMyClasses(classes);
            if (classes.length > 0 && !selectedClassId) {
                setSelectedClassId(classes[0].assignment_id.toString());
            }
        } catch (e) {
            console.error(e);
        }
    };

    const loadMaterials = async () => {
        try {
            const data = await api.fetchMaterials();
            setMaterials(data);
        } catch (e) { }
    };

    const loadAllClassrooms = async () => {
        try {
            const data = await api.fetchClassrooms();
            setAllClassrooms(data);
            if (data.length > 0 && !adminSelectedClass) {
                setAdminSelectedClass(data[0].id.toString());
            }
        } catch (e) { }
    };

    // -------------------------------------------------------------
    // TAKE ATTENDANCE LOGIC
    // -------------------------------------------------------------
    const selectedClass = myClasses.find(c => c.assignment_id.toString() === selectedClassId);

    useEffect(() => {
        if (selectedClass && currentNav === 'Take Attendance') {
            checkTodaySession();
        }
    }, [selectedClassId, currentNav]);

    const checkTodaySession = async () => {
        if (!selectedClass) return;
        try {
            const sess = await api.getTodaySession(selectedClass.classroom_id, selectedClass.subject_id, user.id);
            if (sess && sess.id) {
                setTodaySession(sess);
                loadSessionDetails(sess.id, selectedClass.classroom_id, selectedClass.subject_id);
            } else {
                setTodaySession(null);
            }
        } catch (e) { }
    };

    const loadSessionDetails = async (sessId, classroomId, subjectId) => {
        try {
            const [stu, att, summary] = await Promise.all([
                api.fetchStudents(classroomId),
                api.getAttendance(sessId),
                api.getAttendanceSummary(classroomId, subjectId)
            ]);
            setRoster(stu);
            setAttendanceRecords(att);
            setAttendanceSummary(summary);
        } catch (e) { }
    };

    const handleStartSession = async () => {
        if (!selectedClass) return;
        try {
            await api.startSession(selectedClass.classroom_id, selectedClass.subject_id, user.id);
            await fetchDashboard();
            checkTodaySession();
        } catch (e) {
            alert(e.message);
        }
    };

    const handleEndSession = async () => {
        if (!todaySession) return;
        try {
            await api.endSession(todaySession.id);
            await fetchDashboard();
            setTodaySession(null);
            alert('Session ended and saved to the database.');
        } catch (e) {
            alert(e.message);
        }
    };

    const markStudent = async (studentId, status) => {
        if (!todaySession) return;
        try {
            await api.markAttendance(todaySession.id, studentId, status);
            setAttendanceRecords(prev => ({ ...prev, [studentId]: status }));
            const summary = await api.getAttendanceSummary(selectedClass.classroom_id, selectedClass.subject_id);
            setAttendanceSummary(summary);
        } catch (e) {
            alert(e.message);
        }
    };


    // -------------------------------------------------------------
    // RENDER HELPERS
    // -------------------------------------------------------------

    if (loading) return <div>Loading portal...</div>;
    if (error) return <div className="alert alert-error">{error}</div>;

    return (
        <div>
            <div className="hero-banner">
                <span className="text-badge badge-primary" style={{ marginBottom: '10px' }}>TEACHER OPERATIONS WORKSPACE</span>
                <div className="hero-title">Welcome back, {user.name}</div>
                <div className="hero-subtitle">Active Focus: {dashboard?.current_topic || 'N/A'}</div>
            </div>

            <div className="metrics-grid">
                <div className="metric-card">
                    <div className="metric-label">Active Classes</div>
                    <div className="metric-value">{dashboard?.classroom_count || 0}</div>
                    <div className="metric-caption">Assigned sections</div>
                </div>
                <div className="metric-card">
                    <div className="metric-label">Total Sessions</div>
                    <div className="metric-value">{dashboard?.session_count || 0}</div>
                    <div className="metric-caption">Recorded lectures</div>
                </div>
                <div className="metric-card">
                    <div className="metric-label">Course Resources</div>
                    <div className="metric-value">{dashboard?.materials_available || 0}</div>
                    <div className="metric-caption">Indexed documents</div>
                </div>
                <div className="metric-card">
                    <div className="metric-label">Weekly Load</div>
                    <div className="metric-value">{dashboard?.weekly_hours || 0}h</div>
                    <div className="metric-caption">Instructional hours</div>
                </div>
            </div>

            {/* OVERVIEW */}
            {currentNav === 'Overview' && (
                <div className="content-card">
                    <div className="card-title">Welcome back</div>
                    <p>
                        You're teaching <strong>{dashboard?.classroom_count || 0}</strong> class section(s) and have run{' '}
                        <strong>{dashboard?.session_count || 0}</strong> sessions so far.{' '}
                        <strong>{dashboard?.materials_available || 0}</strong> course document(s) are indexed for your students.
                    </p>
                    <p className="text-caption">Use the navigation on the left to take attendance, manage course material, or administer classrooms.</p>
                </div>
            )}

            {/* TAKE ATTENDANCE */}
            {currentNav === 'Take Attendance' && (
                <div className="content-card">
                    <div className="card-title">Take Attendance</div>
                    <p className="text-caption">Select one of your classes, start today's session, then click each student to mark them present or absent.</p>

                    {myClasses.length === 0 ? (
                        <div className="alert alert-info">You are not yet assigned to teach any classroom/subject.</div>
                    ) : (
                        <>
                            <div className="input-group" style={{ maxWidth: '400px' }}>
                                <label>Select Your Class</label>
                                <select
                                    className="input-control"
                                    value={selectedClassId}
                                    onChange={(e) => setSelectedClassId(e.target.value)}
                                >
                                    {myClasses.map(c => (
                                        <option key={c.assignment_id} value={c.assignment_id}>
                                            {c.classroom_name} — {c.subject_name} ({c.subject_code})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {!todaySession ? (
                                <button className="btn btn-primary" onClick={handleStartSession}>
                                    Start Today's Session
                                </button>
                            ) : (
                                <>
                                    <div className="alert alert-success">Session active — started {new Date(todaySession.session_date).toLocaleString()}</div>
                                    {roster.length === 0 ? (
                                        <div className="alert alert-info">No students enrolled in this classroom yet.</div>
                                    ) : (
                                        <>
                                            <p><strong>Click a student to mark Present / Absent</strong></p>
                                            {roster.map(student => {
                                                const status = attendanceRecords[student.id];
                                                let badgeClass = "badge-primary";
                                                let badgeText = "NOT MARKED";
                                                if (status === 'present') { badgeClass = "badge-present"; badgeText = "PRESENT"; }
                                                else if (status === 'absent') { badgeClass = "badge-absent"; badgeText = "ABSENT"; }

                                                return (
                                                    <div key={student.id} className="flex items-center gap-4 mb-2" style={{ padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                                                        <div style={{ flex: '2.2' }}>
                                                            <strong>{student.name}</strong> &nbsp;
                                                            <span className={`text-badge ${badgeClass}`}>{badgeText}</span>
                                                        </div>
                                                        <div style={{ flex: '1' }} className="text-caption">{student.student_id}</div>
                                                        <div style={{ flex: '1' }}>
                                                            <button className="btn btn-sm" onClick={() => markStudent(student.id, 'present')}>Present</button>
                                                        </div>
                                                        <div style={{ flex: '1' }}>
                                                            <button className="btn btn-sm" onClick={() => markStudent(student.id, 'absent')}>Absent</button>
                                                        </div>
                                                    </div>
                                                )
                                            })}

                                            <div className="divider"></div>
                                            <p><strong>Attendance Summary — this subject</strong></p>
                                            {attendanceSummary.length > 0 ? (
                                                <table className="data-table">
                                                    <thead>
                                                        <tr>
                                                            <th>Student</th>
                                                            <th>Roll No</th>
                                                            <th>Classes Held</th>
                                                            <th>Attended</th>
                                                            <th>Attendance %</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {attendanceSummary.map(s => (
                                                            <tr key={s.student_id}>
                                                                <td>{s.name}</td>
                                                                <td>{s.roll_no}</td>
                                                                <td>{s.total_classes}</td>
                                                                <td>{s.attended}</td>
                                                                <td>{s.percentage}%</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            ) : (
                                                <p className="text-caption">No attendance history yet for this subject.</p>
                                            )}

                                            <div className="divider"></div>
                                            <button className="btn btn-primary" onClick={handleEndSession}>
                                                End Today's Session
                                            </button>
                                        </>
                                    )}
                                </>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* COURSE MATERIAL */}
            {currentNav === 'Course Material' && (
                <>
                    <div className="content-card">
                        <div className="card-title">Upload Course Material (PDF)</div>
                        <p className="text-caption">Uploaded documents are indexed into vector storage for student AI assistance.</p>
                        <input
                            type="file"
                            accept=".pdf"
                            className="input-control mb-4"
                            onChange={async (e) => {
                                if (e.target.files && e.target.files[0]) {
                                    setUploading(true);
                                    try {
                                        const res = await api.uploadMaterial(e.target.files[0]);
                                        alert(res.message);
                                        loadMaterials();
                                    } catch (err) {
                                        alert('Upload failed: ' + err.message);
                                    } finally {
                                        setUploading(false);
                                        e.target.value = '';
                                    }
                                }
                            }}
                            disabled={uploading}
                        />
                        {uploading && <p className="text-caption">Uploading and indexing document, please wait...</p>}
                    </div>

                    <div className="content-card">
                        <div className="card-title">Indexed Repository</div>
                        {materials.length > 0 ? (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Filename</th>
                                        <th>Uploaded Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {materials.map((m, idx) => (
                                        <tr key={idx}>
                                            <td>{m.filename}</td>
                                            <td>{new Date(m.uploaded_at).toLocaleString()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="alert alert-info">No course materials indexed yet.</div>
                        )}
                    </div>
                </>
            )}

            {/* CLASSROOM ADMINISTRATION */}
            {currentNav === 'Classroom Administration' && (
                <div className="content-card">
                    <div className="card-title">Classroom Administration</div>
                    <form
                        onSubmit={async (e) => {
                            e.preventDefault();
                            if (newClassName.trim()) {
                                try {
                                    await api.createClassroom(newClassName);
                                    alert('Classroom created');
                                    setNewClassName('');
                                    loadAllClassrooms();
                                } catch (err) {
                                    alert(err.message);
                                }
                            }
                        }}
                    >
                        <div className="input-group">
                            <label>Create New Classroom Section</label>
                            <input type="text" className="input-control" placeholder="e.g. CS-101 Section A" value={newClassName} onChange={e => setNewClassName(e.target.value)} />
                        </div>
                        <button className="btn btn-primary" type="submit">Create Classroom</button>
                    </form>

                    <div className="divider"></div>

                    {allClassrooms.length > 0 ? (
                        <>
                            <div className="input-group" style={{ maxWidth: '400px' }}>
                                <label>Select Classroom Section</label>
                                <select
                                    className="input-control"
                                    value={adminSelectedClass}
                                    onChange={async (e) => {
                                        setAdminSelectedClass(e.target.value);
                                        const list = await api.fetchStudents(e.target.value);
                                        setAdminRoster(list);
                                    }}
                                >
                                    {allClassrooms.map(c => (
                                        <option key={c.id} value={c.id}>{c.name}</option>
                                    ))}
                                </select>
                            </div>

                            <details style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '1rem' }}>
                                <summary style={{ fontWeight: 600, cursor: 'pointer' }}>Enroll Student to Section</summary>
                                <form
                                    style={{ marginTop: '1rem' }}
                                    onSubmit={async (e) => {
                                        e.preventDefault();
                                        if (enrollName.trim() && enrollId.trim()) {
                                            try {
                                                await api.enrollStudent(adminSelectedClass, {
                                                    name: enrollName,
                                                    student_id: enrollId,
                                                    email: enrollEmail || null
                                                });
                                                alert('Student assigned successfully.');
                                                setEnrollName('');
                                                setEnrollId('');
                                                setEnrollEmail('');
                                                const list = await api.fetchStudents(adminSelectedClass);
                                                setAdminRoster(list);
                                            } catch (err) {
                                                alert(err.message);
                                            }
                                        }
                                    }}
                                >
                                    <div className="input-group">
                                        <label>Student Name</label>
                                        <input type="text" className="input-control" value={enrollName} onChange={e => setEnrollName(e.target.value)} />
                                    </div>
                                    <div className="input-group">
                                        <label>Institutional Roll/ID</label>
                                        <input type="text" className="input-control" value={enrollId} onChange={e => setEnrollId(e.target.value)} />
                                    </div>
                                    <div className="input-group">
                                        <label>Student Login Email (optional)</label>
                                        <input type="text" className="input-control" value={enrollEmail} onChange={e => setEnrollEmail(e.target.value)} />
                                    </div>
                                    <button type="submit" className="btn btn-primary btn-full">Enroll Student</button>
                                </form>
                            </details>

                            <button className="btn" onClick={async () => {
                                if (adminSelectedClass) {
                                    const list = await api.fetchStudents(adminSelectedClass);
                                    setAdminRoster(list);
                                }
                            }}>Load Roster</button>

                            {adminRoster.length > 0 ? (
                                <table className="data-table" style={{ marginTop: '1rem' }}>
                                    <thead>
                                        <tr>
                                            <th>Student Name</th>
                                            <th>Student ID</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {adminRoster.map(s => (
                                            <tr key={s.id}>
                                                <td>{s.name}</td>
                                                <td>{s.student_id}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <p className="text-caption mt-2">No students enrolled in this section yet or click Load Roster.</p>
                            )}
                        </>
                    ) : (
                        <div className="alert alert-info">No active classrooms created.</div>
                    )}
                </div>
            )}
        </div>
    );
}
