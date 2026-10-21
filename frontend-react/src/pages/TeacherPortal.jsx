import { useState, useEffect } from 'react';
import { api, clearCache } from '../api';
import { useToast } from '../App';
import ChangePassword from '../components/ChangePassword';

export default function TeacherPortal({ user, currentNav }) {
    const toast = useToast();
    const [dashboard, setDashboard] = useState(null);
    const [loading, setLoading]     = useState(true);

    // ── Attendance state ──────────────────────────────────
    const [myClasses, setMyClasses]               = useState([]);
    const [selectedClassId, setSelectedClassId]   = useState('');
    const [todaySession, setTodaySession]         = useState(null);
    const [roster, setRoster]                     = useState([]);
    const [attendanceRecords, setAttendanceRecords] = useState({});
    const [attendanceSummary, setAttendanceSummary] = useState([]);
    const [sessionLoading, setSessionLoading]     = useState(false);

    // ── Upload state ──────────────────────────────────────
    const [uploading, setUploading] = useState(false);
    const [materials, setMaterials] = useState([]);
    const [selectedClassroomForUpload, setSelectedClassroomForUpload] = useState('');
    const [classroomsList, setClassroomsList] = useState([]);

    // ── Classroom admin state ─────────────────────────────
    const [newClassName, setNewClassName]           = useState('');
    const [allClassrooms, setAllClassrooms]         = useState([]);
    const [adminSelectedClass, setAdminSelectedClass] = useState('');
    const [enrollName, setEnrollName]               = useState('');
    const [enrollId, setEnrollId]                   = useState('');
    const [enrollEmail, setEnrollEmail]             = useState('');
    const [adminRoster, setAdminRoster]             = useState([]);

    // ── Add Marks state ───────────────────────────────────
    const [marksClassId, setMarksClassId]     = useState('');
    const [marksSubjectId, setMarksSubjectId] = useState('');
    const [marksRoster, setMarksRoster]       = useState([]);
    const [marksSubjects, setMarksSubjects]   = useState([]);
    const [marksData, setMarksData]           = useState([]);
    const [examName, setExamName]             = useState('');
    const [maxMarks, setMaxMarks]             = useState('100');
    const [marksInput, setMarksInput]         = useState({}); // {student_db_id: value}
    const [savingMarks, setSavingMarks]       = useState(false);

    // ── Search Student state ──────────────────────────────
    const [searchEnroll, setSearchEnroll]     = useState('');
    const [searchResult, setSearchResult]     = useState(null);
    const [searchLoading, setSearchLoading]   = useState(false);

    // ── Create Quiz state ─────────────────────────────────
    const [quizTitle, setQuizTitle]           = useState('');
    const [quizClassId, setQuizClassId]       = useState('');
    const [quizSubjectId, setQuizSubjectId]   = useState('');
    const [quizQuestions, setQuizQuestions]   = useState([
        { id: '1', question: '', options: { A: '', B: '', C: '', D: '' }, correct: 'A' },
    ]);
    const [creatingQuiz, setCreatingQuiz]     = useState(false);

    // ── My Quizzes state ─────────────────────────────────
    const [myQuizzes, setMyQuizzes]           = useState([]);
    const [selectedQuiz, setSelectedQuiz]     = useState(null);
    const [quizResults, setQuizResults]       = useState([]);

    // ── All subjects (for quiz/marks) ─────────────────────
    const [allSubjects, setAllSubjects]       = useState([]);

    // ── Fetch dashboard ───────────────────────────────────
    const fetchDashboard = async () => {
        try {
            const data = await api.fetchTeacherDashboard(user.id);
            setDashboard(data);
        } catch (err) {
            toast(err.message, 'error');
        } finally { setLoading(false); }
    };

    useEffect(() => { fetchDashboard(); }, [user.id]);

    useEffect(() => {
        if (currentNav === 'Take Attendance')          loadTeacherClasses();
        else if (currentNav === 'Course Material')     loadMaterials();
        else if (currentNav === 'Classroom Administration') loadAllClassrooms();
        else if (currentNav === 'Add Marks')           initMarksSection();
        else if (currentNav === 'Create Quiz')         initQuizSection();
        else if (currentNav === 'My Quizzes')          loadMyQuizzes();
    }, [currentNav]);

    const loadTeacherClasses = async () => {
        try {
            const classes = await api.fetchTeacherClasses(user.id);
            setMyClasses(classes);
            if (classes.length > 0 && !selectedClassId)
                setSelectedClassId(classes[0].assignment_id.toString());
        } catch (e) { toast('Could not load classes.', 'error'); }
    };

    const loadMaterials = async () => {
        try {
            const [m, c] = await Promise.all([
                api.fetchMaterials(),
                api.fetchClassrooms()
            ]);
            setMaterials(m || []);
            setClassroomsList(c || []);
        } catch {}
    };

    const loadAllClassrooms = async () => {
        try {
            const data = await api.fetchClassrooms();
            setAllClassrooms(data);
            if (data.length > 0 && !adminSelectedClass)
                setAdminSelectedClass(data[0].id.toString());
        } catch {}
    };

    // ── Marks init ────────────────────────────────────────
    const initMarksSection = async () => {
        try {
            const [classes, subjects] = await Promise.all([
                api.fetchTeacherClasses(user.id),
                api.fetchClassrooms(),
            ]);
            setMyClasses(classes);
            // subjects already loaded from teacher classes below
            // Load subjects from teacher's classes
            const uniqueSubjects = [];
            const seen = new Set();
            classes.forEach(c => {
                if (!seen.has(c.subject_id)) {
                    seen.add(c.subject_id);
                    uniqueSubjects.push({ id: c.subject_id, name: c.subject_name, code: c.subject_code });
                }
            });
            setAllSubjects(uniqueSubjects);
            if (classes.length > 0) {
                const firstClass = classes[0];
                setMarksClassId(firstClass.classroom_id.toString());
                setMarksSubjectId(firstClass.subject_id.toString());
                await loadMarksRosterAndData(firstClass.classroom_id, firstClass.subject_id);
            }
        } catch (e) { toast('Could not initialize marks section.', 'error'); }
    };

    const loadMarksRosterAndData = async (classroomId, subjectId) => {
        try {
            const [roster, marks] = await Promise.all([
                api.fetchStudents(classroomId),
                api.fetchClassroomMarks(classroomId, subjectId || undefined),
            ]);
            setMarksRoster(roster);
            setMarksData(marks);
            setMarksInput({});
        } catch {}
    };

    const handleSaveMarks = async () => {
        if (!examName.trim()) { toast('Please enter an exam name.', 'error'); return; }
        if (!maxMarks || parseFloat(maxMarks) <= 0) { toast('Max marks must be > 0.', 'error'); return; }
        const entries = Object.entries(marksInput).filter(([, v]) => v !== '' && v !== undefined);
        if (entries.length === 0) { toast('Enter marks for at least one student.', 'error'); return; }
        setSavingMarks(true);
        try {
            await Promise.all(
                entries.map(([studentDbId, val]) =>
                    api.addMark({
                        student_db_id: parseInt(studentDbId),
                        subject_id: parseInt(marksSubjectId),
                        exam_name: examName.trim(),
                        marks_obtained: parseFloat(val),
                        max_marks: parseFloat(maxMarks),
                    })
                )
            );
            toast(`Marks saved for ${entries.length} student(s) ✓`, 'success');
            clearCache();
            setMarksInput({});
            await loadMarksRosterAndData(parseInt(marksClassId), parseInt(marksSubjectId));
        } catch (e) { toast(e.message, 'error'); }
        finally { setSavingMarks(false); }
    };

    // ── Search Student ────────────────────────────────────
    const handleSearch = async () => {
        if (!searchEnroll.trim()) return;
        setSearchLoading(true);
        setSearchResult(null);
        try {
            const result = await api.searchStudentByEnrollment(searchEnroll.trim());
            setSearchResult(result);
        } catch (e) { toast(e.message, 'error'); }
        finally { setSearchLoading(false); }
    };

    // ── Attendance logic ───────────────────────────────────
    const selectedClass = myClasses.find(c => c.assignment_id.toString() === selectedClassId);

    useEffect(() => {
        if (selectedClass && currentNav === 'Take Attendance') {
            setRoster([]);
            setAttendanceRecords({});
            setAttendanceSummary([]);
            checkTodaySession();
        }
    }, [selectedClassId, currentNav]);

    const checkTodaySession = async () => {
        if (!selectedClass) return;
        setSessionLoading(true);
        try {
            const [sess, stu] = await Promise.all([
                api.getTodaySession(selectedClass.classroom_id, selectedClass.subject_id, user.id),
                api.fetchStudents(selectedClass.classroom_id)
            ]);
            setRoster(stu || []);
            if (sess?.id) {
                setTodaySession(sess);
                loadSessionDetails(sess.id, selectedClass.classroom_id, selectedClass.subject_id);
            } else {
                setTodaySession(null);
                const summary = await api.getAttendanceSummary(selectedClass.classroom_id, selectedClass.subject_id);
                setAttendanceSummary(summary || []);
            }
        } catch {} finally { setSessionLoading(false); }
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
        } catch {}
    };

    const handleStartSession = async () => {
        if (!selectedClass) return;
        setSessionLoading(true);
        try {
            await api.startSession(selectedClass.classroom_id, selectedClass.subject_id, user.id);
            toast('Session started! Take attendance now.', 'success');
            clearCache();
            await fetchDashboard();
            checkTodaySession();
        } catch (e) { toast(e.message, 'error'); }
        finally { setSessionLoading(false); }
    };

    const handleEndSession = async () => {
        if (!todaySession) return;
        try {
            await api.endSession(todaySession.id);
            toast('Session ended and saved ✓', 'success');
            clearCache();
            await fetchDashboard();
            setTodaySession(null);
        } catch (e) { toast(e.message, 'error'); }
    };

    const markStudent = async (studentId, status) => {
        if (!todaySession) return;
        try {
            await api.markAttendance(todaySession.id, studentId, status);
            setAttendanceRecords(prev => ({ ...prev, [studentId]: status }));
            const summary = await api.getAttendanceSummary(selectedClass.classroom_id, selectedClass.subject_id);
            setAttendanceSummary(summary);
        } catch (e) { toast(e.message, 'error'); }
    };

    const atRiskStudents = attendanceSummary.filter(s => s.percentage < 75 && s.total_classes >= 3);

    const aiInsight = (() => {
        if (!attendanceSummary.length) return null;
        const avg = Math.round(attendanceSummary.reduce((a, s) => a + s.percentage, 0) / attendanceSummary.length);
        const low = attendanceSummary.filter(s => s.percentage < 75).length;
        if (low > 0) return `⚠️ ${low} student${low > 1 ? 's are' : ' is'} below 75% attendance. Class average is ${avg}% — consider a revision session.`;
        if (avg >= 90) return `🌟 Excellent! Class average attendance is ${avg}%. Your students are highly engaged.`;
        return `📊 Class attendance average is ${avg}%. All students are above the 75% threshold.`;
    })();

    // ── Quiz helpers ──────────────────────────────────────
    const initQuizSection = async () => {
        try {
            const [classes, allCls, allSubs] = await Promise.all([
                api.fetchTeacherClasses(user.id),
                api.fetchClassrooms(),
                api.fetchSubjects()
            ]);
            setMyClasses(classes || []);
            setAllClassrooms(allCls || []);
            setAllSubjects(allSubs || []);

            const defaultCid = (allCls && allCls.length > 0) ? allCls[0].id.toString() : (classes && classes.length > 0) ? classes[0].classroom_id.toString() : '';
            const defaultSid = (allSubs && allSubs.length > 0) ? allSubs[0].id.toString() : (classes && classes.length > 0) ? classes[0].subject_id.toString() : '';

            if (defaultCid) setQuizClassId(defaultCid);
            if (defaultSid) setQuizSubjectId(defaultSid);
        } catch {}
    };

    const loadMyQuizzes = async () => {
        try {
            const data = await api.fetchTeacherQuizzes(user.id);
            setMyQuizzes(data.quizzes || []);
        } catch {}
    };

    const addQuestion = () => {
        const newId = String(quizQuestions.length + 1);
        setQuizQuestions(prev => [...prev, { id: newId, question: '', options: { A: '', B: '', C: '', D: '' }, correct: 'A' }]);
    };

    const removeQuestion = (idx) => {
        setQuizQuestions(prev => prev.filter((_, i) => i !== idx));
    };

    const updateQuestion = (idx, field, value) => {
        setQuizQuestions(prev => {
            const updated = [...prev];
            if (field.startsWith('opt_')) {
                const optKey = field.replace('opt_', '');
                updated[idx] = { ...updated[idx], options: { ...updated[idx].options, [optKey]: value } };
            } else {
                updated[idx] = { ...updated[idx], [field]: value };
            }
            return updated;
        });
    };

    const handleCreateQuiz = async () => {
        if (!quizTitle.trim()) { toast('Enter a quiz title.', 'error'); return; }
        if (!quizClassId || !quizSubjectId) { toast('Select a class and subject.', 'error'); return; }
        const hasEmpty = quizQuestions.some(q => !q.question.trim() || Object.values(q.options).some(v => !v.trim()));
        if (hasEmpty) { toast('Fill in all question fields.', 'error'); return; }
        setCreatingQuiz(true);
        try {
            await api.createQuiz({
                title: quizTitle.trim(),
                subject_id: parseInt(quizSubjectId),
                teacher_id: user.id,
                classroom_id: parseInt(quizClassId),
                questions: quizQuestions,
            });
            toast(`Quiz "${quizTitle}" published! ✓`, 'success');
            clearCache();
            setQuizTitle('');
            setQuizQuestions([{ id: '1', question: '', options: { A: '', B: '', C: '', D: '' }, correct: 'A' }]);
        } catch (e) { toast(e.message, 'error'); }
        finally { setCreatingQuiz(false); }
    };

    const handleViewResults = async (quiz) => {
        setSelectedQuiz(quiz);
        try {
            const data = await api.fetchQuizResults(quiz.id);
            setQuizResults(data.results || []);
        } catch { setQuizResults([]); }
    };

    const handleToggleQuiz = async (quiz) => {
        try {
            await api.toggleQuiz(quiz.id, user.id, !quiz.is_active);
            toast(`Quiz ${quiz.is_active ? 'deactivated' : 'activated'} ✓`, 'success');
            clearCache();
            loadMyQuizzes();
        } catch (e) { toast(e.message, 'error'); }
    };

    // Get unique classes for the marks section dropdown
    const uniqueClassesForMarks = myClasses.reduce((acc, c) => {
        if (!acc.find(x => x.classroom_id === c.classroom_id)) acc.push(c);
        return acc;
    }, []);

    const subjectsForSelectedClass = myClasses.filter(c => c.classroom_id.toString() === marksClassId);

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: '14px', color: 'var(--text-muted)' }}>
            <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} /> Loading portal...
        </div>
    );

    return (
        <div>
            {/* Hero */}
            <div className="hero-banner">
                <div className="hero-badge">🎓 Teacher Operations Workspace</div>
                <div className="hero-title">Welcome back, {user.name}</div>
                <div className="hero-subtitle">
                    {dashboard?.current_topic ? `Active Topic: ${dashboard.current_topic}` : 'Manage attendance, marks, quizzes and materials.'}
                </div>
            </div>

            {/* Metrics */}
            <div className="metrics-grid">
                {[
                    { icon: '🏫', label: 'Active Classes',   value: dashboard?.classroom_count  || 0, caption: 'Assigned sections'    },
                    { icon: '📋', label: 'Total Sessions',   value: dashboard?.session_count    || 0, caption: 'Recorded lectures'    },
                    { icon: '📄', label: 'Course Resources', value: dashboard?.materials_available || 0, caption: 'Indexed documents' },
                    { icon: '⏱️', label: 'Weekly Load',      value: `${dashboard?.weekly_hours  || 0}h`, caption: 'Instructional hours' },
                ].map(m => (
                    <div className="metric-card" key={m.label}>
                        <div className="metric-icon">{m.icon}</div>
                        <div className="metric-label">{m.label}</div>
                        <div className="metric-value">{m.value}</div>
                        <div className="metric-caption">{m.caption}</div>
                    </div>
                ))}
            </div>

            {/* ── DASHBOARD ── */}
            {currentNav === 'Dashboard' && (
                <>
                    {aiInsight && (
                        <div className="ai-insight-card">
                            <div className="ai-insight-label">✦ AI Class Insight</div>
                            <div className="ai-insight-text">{aiInsight}</div>
                        </div>
                    )}
                    <div className="content-card">
                        <div className="card-title">🏠 Dashboard</div>
                        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                            You're teaching <strong>{dashboard?.classroom_count || 0}</strong> class section(s) and have run{' '}
                            <strong>{dashboard?.session_count || 0}</strong> sessions so far.{' '}
                            <strong>{dashboard?.materials_available || 0}</strong> course document(s) are indexed for AI assistance.
                        </p>
                        <p className="text-caption" style={{ marginTop: '10px' }}>
                            Use the navigation on the left to take attendance, add marks, create quizzes, or manage course materials.
                        </p>
                    </div>
                </>
            )}

            {/* ── TAKE ATTENDANCE ── */}
            {currentNav === 'Take Attendance' && (
                <div className="content-card">
                    <div className="card-title">✅ Take Attendance</div>
                    <p className="text-caption" style={{ marginBottom: '16px' }}>
                        Select a class, start today's session, then mark each student.
                    </p>

                    {myClasses.length === 0 ? (
                        <div className="alert alert-info">ℹ You are not yet assigned to teach any classroom/subject.</div>
                    ) : (
                        <>
                            <div className="input-group" style={{ maxWidth: '420px' }}>
                                <label>Select Your Class</label>
                                <select className="input-control" value={selectedClassId}
                                    onChange={e => setSelectedClassId(e.target.value)}>
                                    {myClasses.map(c => (
                                        <option key={c.assignment_id} value={c.assignment_id}>
                                            {c.classroom_name} — {c.subject_name} ({c.subject_code})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {sessionLoading ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)' }}>
                                    <span className="spinner" /> Loading session...
                                </div>
                            ) : !todaySession ? (
                                <button className="btn btn-primary" onClick={handleStartSession}>
                                    ▶ Start Today's Session
                                </button>
                            ) : (
                                <>
                                    <div className="alert alert-success">
                                        ✓ Session active — started {new Date(todaySession.session_date).toLocaleString()}
                                    </div>

                                    {atRiskStudents.length > 0 && (
                                        <div style={{ marginBottom: '16px' }}>
                                            <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', color: '#fca5a5', marginBottom: '8px', letterSpacing: '0.06em' }}>
                                                ⚠ At-Risk Students (below 75%)
                                            </div>
                                            {atRiskStudents.map(s => (
                                                <div className="risk-card" key={s.student_id}>
                                                    <div>
                                                        <strong style={{ color: 'var(--text-primary)' }}>{s.name}</strong>
                                                        <span style={{ color: 'var(--text-muted)', fontSize: '0.84rem', marginLeft: 8 }}>{s.roll_no}</span>
                                                    </div>
                                                    <span className="risk-badge">⚠ {s.percentage}% attendance</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {roster.length === 0 ? (
                                        <div className="alert alert-info">No students enrolled in this classroom yet.</div>
                                    ) : (
                                        <>
                                            <p style={{ fontWeight: 600, marginBottom: '12px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                                                Click a student to mark Present / Absent
                                            </p>
                                            {roster.map(student => {
                                                const status = attendanceRecords[student.id];
                                                return (
                                                    <div key={student.id} style={{
                                                        display: 'flex', alignItems: 'center', gap: '12px',
                                                        padding: '10px 0', borderBottom: '1px solid var(--border)',
                                                    }}>
                                                        <div style={{ flex: '2.5' }}>
                                                            <strong style={{ color: 'var(--text-primary)' }}>{student.name}</strong>
                                                            {' '}{status && (
                                                                <span className={`text-badge ${status === 'present' ? 'badge-present' : 'badge-absent'}`}>
                                                                    {status.toUpperCase()}
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div style={{ flex: 1, color: 'var(--text-muted)', fontSize: '0.84rem' }}>{student.student_id}</div>
                                                        <button className="btn btn-sm btn-teal" onClick={() => markStudent(student.id, 'present')}>✓ Present</button>
                                                        <button className="btn btn-sm btn-danger" onClick={() => markStudent(student.id, 'absent')}>✕ Absent</button>
                                                    </div>
                                                );
                                            })}

                                            <div className="divider" />
                                            <p style={{ fontWeight: 600, marginBottom: '12px', color: 'var(--text-primary)' }}>
                                                Attendance Summary — this subject
                                            </p>
                                            {attendanceSummary.length > 0 ? (
                                                <table className="data-table">
                                                    <thead><tr>
                                                        <th>Student</th><th>Roll No</th>
                                                        <th>Classes Held</th><th>Attended</th><th>Attendance %</th>
                                                    </tr></thead>
                                                    <tbody>
                                                        {attendanceSummary.map(s => (
                                                            <tr key={s.student_id}>
                                                                <td>{s.name}</td>
                                                                <td>{s.roll_no}</td>
                                                                <td>{s.total_classes}</td>
                                                                <td>{s.attended}</td>
                                                                <td>
                                                                    <span className={`text-badge ${s.percentage < 75 ? 'badge-absent' : 'badge-present'}`}>
                                                                        {s.percentage}%
                                                                    </span>
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            ) : (
                                                <p className="text-caption">No attendance history yet for this subject.</p>
                                            )}

                                            <div className="divider" />
                                            <button className="btn btn-danger" onClick={handleEndSession}>
                                                ⏹ End Today's Session
                                            </button>
                                        </>
                                    )}
                                </>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* ── ADD MARKS ── */}
            {currentNav === 'Add Marks' && (
                <div className="content-card">
                    <div className="card-title">📝 Add / Update Student Marks</div>
                    <p className="text-caption" style={{ marginBottom: '16px' }}>
                        Select a class and subject, enter an exam name, then fill in each student's marks.
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Classroom</label>
                            <select className="input-control" value={marksClassId}
                                onChange={async e => {
                                    setMarksClassId(e.target.value);
                                    const subs = myClasses.filter(c => c.classroom_id.toString() === e.target.value);
                                    if (subs.length > 0) {
                                        setMarksSubjectId(subs[0].subject_id.toString());
                                        await loadMarksRosterAndData(parseInt(e.target.value), subs[0].subject_id);
                                    }
                                }}>
                                {uniqueClassesForMarks.map(c => (
                                    <option key={c.classroom_id} value={c.classroom_id}>{c.classroom_name}</option>
                                ))}
                            </select>
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Subject</label>
                            <select className="input-control" value={marksSubjectId}
                                onChange={async e => {
                                    setMarksSubjectId(e.target.value);
                                    await loadMarksRosterAndData(parseInt(marksClassId), parseInt(e.target.value));
                                }}>
                                {subjectsForSelectedClass.map(c => (
                                    <option key={c.subject_id} value={c.subject_id}>{c.subject_name} ({c.subject_code})</option>
                                ))}
                            </select>
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Exam Name</label>
                            <input type="text" className="input-control" placeholder="e.g. Midterm, Final, Quiz 1"
                                value={examName} onChange={e => setExamName(e.target.value)} />
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Max Marks</label>
                            <input type="number" className="input-control" min="1" value={maxMarks}
                                onChange={e => setMaxMarks(e.target.value)} />
                        </div>
                    </div>

                    {marksRoster.length > 0 ? (
                        <>
                            <table className="data-table" style={{ marginBottom: '16px' }}>
                                <thead><tr>
                                    <th>Student</th><th>Enrollment No</th>
                                    <th>Marks Obtained <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>/ {maxMarks}</span></th>
                                </tr></thead>
                                <tbody>
                                    {marksRoster.map(s => (
                                        <tr key={s.id}>
                                            <td><strong style={{ color: 'var(--text-primary)' }}>{s.name}</strong></td>
                                            <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{s.student_id}</td>
                                            <td>
                                                <input
                                                    type="number" min="0" max={maxMarks} step="0.5"
                                                    className="input-control"
                                                    style={{ width: '120px', padding: '6px 10px', marginBottom: 0 }}
                                                    placeholder="—"
                                                    value={marksInput[s.id] ?? ''}
                                                    onChange={e => setMarksInput(prev => ({ ...prev, [s.id]: e.target.value }))}
                                                />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            <button className="btn btn-primary" onClick={handleSaveMarks} disabled={savingMarks}>
                                {savingMarks ? <><span className="spinner" /> Saving...</> : '💾 Save Marks'}
                            </button>
                        </>
                    ) : (
                        <div className="alert alert-info">ℹ No students found for the selected classroom. Enroll students first.</div>
                    )}

                    {/* Existing marks for this class/subject */}
                    {marksData.filter(m => m.exam_name).length > 0 && (
                        <>
                            <div className="divider" />
                            <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
                                📊 Existing Marks — {subjectsForSelectedClass.find(c => c.subject_id.toString() === marksSubjectId)?.subject_name || ''}
                            </p>
                            <table className="data-table">
                                <thead><tr>
                                    <th>Student</th><th>Enrollment</th><th>Exam</th><th>Marks</th><th>Max</th><th>%</th>
                                </tr></thead>
                                <tbody>
                                    {marksData.filter(m => m.exam_name).map((m, i) => (
                                        <tr key={i}>
                                            <td>{m.student_name}</td>
                                            <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{m.enrollment_no}</td>
                                            <td>{m.exam_name}</td>
                                            <td><strong>{m.marks_obtained}</strong></td>
                                            <td style={{ color: 'var(--text-muted)' }}>{m.max_marks}</td>
                                            <td>
                                                <span className={`text-badge ${(m.marks_obtained / m.max_marks * 100) < 40 ? 'badge-absent' : 'badge-present'}`}>
                                                    {Math.round(m.marks_obtained / m.max_marks * 100)}%
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </>
                    )}
                </div>
            )}

            {/* ── SEARCH STUDENT ── */}
            {currentNav === 'Search Student' && (
                <div className="content-card">
                    <div className="card-title">🔍 Search Student by Enrollment Number</div>
                    <p className="text-caption" style={{ marginBottom: '16px' }}>
                        Enter a student's enrollment / roll number to see their full attendance and marks report.
                    </p>

                    <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', marginBottom: '20px' }}>
                        <div className="input-group" style={{ flex: 1, marginBottom: 0 }}>
                            <label>Enrollment / Roll Number</label>
                            <input type="text" className="input-control" placeholder="e.g. STU-2026-001"
                                value={searchEnroll} onChange={e => setSearchEnroll(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleSearch()} />
                        </div>
                        <button className="btn btn-primary" onClick={handleSearch} disabled={searchLoading}
                            style={{ whiteSpace: 'nowrap' }}>
                            {searchLoading ? <><span className="spinner" /> Searching...</> : '🔍 Search'}
                        </button>
                    </div>

                    {searchResult && (
                        <>
                            <div style={{
                                padding: '16px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)',
                                border: '1px solid var(--border-strong)', marginBottom: '20px',
                                display: 'flex', gap: '20px', flexWrap: 'wrap',
                            }}>
                                <div>
                                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Student</div>
                                    <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-primary)' }}>{searchResult.name}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Enrollment</div>
                                    <div style={{ fontWeight: 600, color: 'var(--accent-light)' }}>{searchResult.enrollment_no}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Overall Attendance</div>
                                    <div style={{ fontWeight: 700, color: searchResult.overall_attendance < 75 ? '#fca5a5' : '#6ee7b7' }}>
                                        {searchResult.overall_attendance}%
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Overall Marks</div>
                                    <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{searchResult.overall_marks_pct}%</div>
                                </div>
                            </div>

                            {/* Per-subject breakdown */}
                            {searchResult.subjects?.map(subj => (
                                <div key={subj.subject_id} style={{ marginBottom: '20px', padding: '16px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                                    <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
                                        {subj.subject_name}
                                        <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: '0.88rem', marginLeft: '8px' }}>({subj.subject_code})</span>
                                    </p>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                                        <div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                                                <span style={{ color: 'var(--text-secondary)' }}>Attendance</span>
                                                <strong>{subj.attended}/{subj.sessions_held}</strong>
                                            </div>
                                            <div className="progress-bar-bg">
                                                <div className={`progress-bar-fill ${subj.attendance_pct < 75 ? 'danger' : ''}`}
                                                    style={{ width: `${Math.min(100, subj.attendance_pct)}%` }} />
                                            </div>
                                            <div className="text-caption">{subj.attendance_pct}%
                                                {subj.attendance_pct < 75 && <span style={{ color: '#fca5a5', marginLeft: 6 }}>⚠ Below 75%</span>}
                                            </div>
                                        </div>
                                        <div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                                                <span style={{ color: 'var(--text-secondary)' }}>Marks Score</span>
                                                <strong>{subj.marks_pct}%</strong>
                                            </div>
                                            <div className="progress-bar-bg">
                                                <div className="progress-bar-fill" style={{ width: `${Math.min(100, subj.marks_pct)}%` }} />
                                            </div>
                                        </div>
                                    </div>
                                    {subj.marks?.length > 0 && (
                                        <table className="data-table">
                                            <thead><tr><th>Exam</th><th>Obtained</th><th>Max</th></tr></thead>
                                            <tbody>
                                                {subj.marks.map((m, i) => (
                                                    <tr key={i}>
                                                        <td>{m.exam_name}</td>
                                                        <td><strong>{m.marks_obtained}</strong></td>
                                                        <td style={{ color: 'var(--text-muted)' }}>{m.max_marks}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    )}
                                </div>
                            ))}
                        </>
                    )}
                </div>
            )}

            {/* ── CREATE QUIZ ── */}
            {currentNav === 'Create Quiz' && (
                <div className="content-card">
                    <div className="card-title">🎯 Create a Quiz</div>
                    <p className="text-caption" style={{ marginBottom: '16px' }}>
                        Build a quiz for your students. Add questions with 4 options (A–D) and mark the correct answer.
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                        <div className="input-group" style={{ gridColumn: '1 / -1', marginBottom: 0 }}>
                            <label>Quiz Title</label>
                            <input type="text" className="input-control" placeholder="e.g. Week 3 — Arrays & Linked Lists Quiz"
                                value={quizTitle} onChange={e => setQuizTitle(e.target.value)} />
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Classroom / Semester</label>
                            <select className="input-control" value={quizClassId}
                                onChange={e => setQuizClassId(e.target.value)}>
                                {(allClassrooms.length > 0
                                    ? allClassrooms
                                    : [...new Map(myClasses.map(c => [c.classroom_id, { id: c.classroom_id, name: c.classroom_name }])).values()]
                                ).map(c => (
                                    <option key={c.id} value={c.id}>🏫 {c.name}</option>
                                ))}
                            </select>
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label>Subject</label>
                            <select className="input-control" value={quizSubjectId}
                                onChange={e => setQuizSubjectId(e.target.value)}>
                                {(allSubjects.length > 0
                                    ? allSubjects
                                    : myClasses.map(c => ({ id: c.subject_id, name: c.subject_name, code: c.subject_code }))
                                ).map(s => (
                                    <option key={s.id} value={s.id}>📖 {s.name} ({s.code})</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Questions */}
                    {quizQuestions.map((q, idx) => (
                        <div key={idx} style={{
                            padding: '16px', background: 'var(--bg-surface)', border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-sm)', marginBottom: '16px',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                                    Question {idx + 1}
                                </span>
                                {quizQuestions.length > 1 && (
                                    <button className="btn btn-sm btn-danger" onClick={() => removeQuestion(idx)}>✕ Remove</button>
                                )}
                            </div>
                            <div className="input-group">
                                <label>Question Text</label>
                                <input type="text" className="input-control"
                                    placeholder="Enter your question here..."
                                    value={q.question}
                                    onChange={e => updateQuestion(idx, 'question', e.target.value)} />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                                {['A', 'B', 'C', 'D'].map(opt => (
                                    <div className="input-group" key={opt} style={{ marginBottom: 0 }}>
                                        <label>Option {opt}</label>
                                        <input type="text" className="input-control"
                                            placeholder={`Option ${opt}`}
                                            value={q.options[opt]}
                                            onChange={e => updateQuestion(idx, `opt_${opt}`, e.target.value)} />
                                    </div>
                                ))}
                            </div>
                            <div className="input-group" style={{ marginBottom: 0 }}>
                                <label>Correct Answer</label>
                                <select className="input-control" style={{ maxWidth: '140px' }}
                                    value={q.correct}
                                    onChange={e => updateQuestion(idx, 'correct', e.target.value)}>
                                    {['A', 'B', 'C', 'D'].map(opt => (
                                        <option key={opt} value={opt}>Option {opt}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    ))}

                    <div style={{ display: 'flex', gap: '12px', marginTop: '4px' }}>
                        <button className="btn" onClick={addQuestion}>+ Add Question</button>
                        <button className="btn btn-primary" onClick={handleCreateQuiz} disabled={creatingQuiz}>
                            {creatingQuiz ? <><span className="spinner" /> Publishing...</> : '🚀 Publish Quiz'}
                        </button>
                    </div>
                </div>
            )}

            {/* ── MY QUIZZES ── */}
            {currentNav === 'My Quizzes' && (
                <div>
                    <div className="content-card">
                        <div className="card-title">📋 My Quizzes</div>
                        {myQuizzes.length === 0 ? (
                            <div className="alert alert-info">ℹ No quizzes created yet. Use "Create Quiz" to publish one.</div>
                        ) : (
                            <table className="data-table">
                                <thead><tr>
                                    <th>Title</th><th>Subject</th><th>Classroom</th>
                                    <th>Questions</th><th>Status</th><th>Actions</th>
                                </tr></thead>
                                <tbody>
                                    {myQuizzes.map(q => (
                                        <tr key={q.id}>
                                            <td><strong style={{ color: 'var(--text-primary)' }}>{q.title}</strong></td>
                                            <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{q.subject_name}</td>
                                            <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{q.classroom_name}</td>
                                            <td style={{ textAlign: 'center' }}>{q.question_count}</td>
                                            <td>
                                                <span className={`text-badge ${q.is_active ? 'badge-present' : 'badge-absent'}`}>
                                                    {q.is_active ? 'Active' : 'Closed'}
                                                </span>
                                            </td>
                                            <td style={{ display: 'flex', gap: '8px' }}>
                                                <button className="btn btn-sm btn-teal" onClick={() => handleViewResults(q)}>
                                                    📊 Results
                                                </button>
                                                <button className="btn btn-sm" onClick={() => handleToggleQuiz(q)}
                                                    style={{ background: q.is_active ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)', color: q.is_active ? '#fca5a5' : '#6ee7b7', border: 'none' }}>
                                                    {q.is_active ? '⏸ Close' : '▶ Reopen'}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {selectedQuiz && (
                        <div className="content-card">
                            <div className="card-title">📊 Results — {selectedQuiz.title}</div>
                            {quizResults.length === 0 ? (
                                <div className="alert alert-info">ℹ No students have submitted this quiz yet.</div>
                            ) : (
                                <table className="data-table">
                                    <thead><tr>
                                        <th>Student</th><th>Score</th><th>Out Of</th><th>%</th><th>Submitted At</th>
                                    </tr></thead>
                                    <tbody>
                                        {quizResults.map((r, i) => (
                                            <tr key={i}>
                                                <td><strong style={{ color: 'var(--text-primary)' }}>{r.name}</strong></td>
                                                <td><strong>{r.score}</strong></td>
                                                <td style={{ color: 'var(--text-muted)' }}>{r.total}</td>
                                                <td>
                                                    <span className={`text-badge ${r.score / r.total >= 0.5 ? 'badge-present' : 'badge-absent'}`}>
                                                        {Math.round(r.score / r.total * 100)}%
                                                    </span>
                                                </td>
                                                <td style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                                                    {new Date(r.submitted_at).toLocaleString()}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* ── COURSE MATERIAL ── */}
            {currentNav === 'Course Material' && (
                <>
                    <div className="content-card">
                        <div className="card-title">📄 Upload Course Material</div>
                        <p className="text-caption" style={{ marginBottom: '12px' }}>
                            PDFs are indexed for the AI study assistant. PPT/PPTX files are stored for student download.
                        </p>

                        <div className="input-group" style={{ marginBottom: '14px' }}>
                            <label style={{ fontWeight: 600, fontSize: '0.88rem' }}>Target Classroom / Semester</label>
                            <select className="input-control" value={selectedClassroomForUpload} onChange={e => setSelectedClassroomForUpload(e.target.value)}>
                                <option value="">🌐 All Classrooms / Semesters (Visible to all students)</option>
                                {classroomsList.map(c => (
                                    <option key={c.id} value={c.id}>🏫 {c.name}</option>
                                ))}
                            </select>
                        </div>

                        <input type="file" accept=".pdf,.ppt,.pptx" className="input-control"
                            style={{ cursor: 'pointer', marginBottom: '8px' }}
                            disabled={uploading}
                            onChange={async (e) => {
                                if (e.target.files?.[0]) {
                                    setUploading(true);
                                    try {
                                        await api.uploadMaterial(e.target.files[0], selectedClassroomForUpload || null);
                                        toast('File uploaded successfully! ✓', 'success');
                                        clearCache();
                                        loadMaterials();
                                    } catch (err) {
                                        toast('Upload failed: ' + err.message, 'error');
                                    } finally { setUploading(false); e.target.value = ''; }
                                }
                            }}
                        />
                        {uploading && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                                <span className="spinner" /> Uploading file...
                            </div>
                        )}
                    </div>

                    <div className="content-card">
                        <div className="card-title">📚 Uploaded Materials</div>
                        {materials.length > 0 ? (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Filename</th>
                                        <th>Target Classroom / Semester</th>
                                        <th>Type</th>
                                        <th>Uploaded</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {materials.map((m, i) => {
                                        const ext = m.filename.split('.').pop().toUpperCase();
                                        return (
                                            <tr key={i}>
                                                <td>
                                                    <span style={{ marginRight: 8 }}>{ext === 'PDF' ? '📄' : '📊'}</span>
                                                    {m.filename}
                                                </td>
                                                <td>
                                                    <span className={`text-badge ${m.classroom_name ? 'badge-primary' : 'badge-dark'}`}>
                                                        {m.classroom_name ? `🏫 ${m.classroom_name}` : '🌐 All Classrooms'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <span className={`text-badge ${ext === 'PDF' ? 'badge-dark' : 'badge-success'}`}>{ext}</span>
                                                </td>
                                                <td style={{ color: 'var(--text-muted)' }}>{new Date(m.uploaded_at).toLocaleString()}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        ) : (
                            <div className="alert alert-info">ℹ No course materials uploaded yet.</div>
                        )}
                    </div>
                </>
            )}

            {/* ── CLASSROOM ADMINISTRATION ── */}
            {currentNav === 'Classroom Administration' && (
                <div className="content-card">
                    <div className="card-title">🏫 Classroom Administration</div>
                    <form onSubmit={async (e) => {
                        e.preventDefault();
                        if (!newClassName.trim()) return;
                        try {
                            await api.createClassroom(newClassName);
                            toast('Classroom created! ✓', 'success');
                            setNewClassName('');
                            clearCache();
                            loadAllClassrooms();
                        } catch (err) { toast(err.message, 'error'); }
                    }}>
                        <div className="input-group">
                            <label>Create New Classroom Section</label>
                            <input type="text" className="input-control" placeholder="e.g. CS-101 Section A"
                                value={newClassName} onChange={e => setNewClassName(e.target.value)} />
                        </div>
                        <button className="btn btn-primary" type="submit">+ Create Classroom</button>
                    </form>

                    <div className="divider" />

                    {allClassrooms.length > 0 ? (
                        <>
                            <div className="input-group" style={{ maxWidth: '400px' }}>
                                <label>Select Classroom Section</label>
                                <select className="input-control" value={adminSelectedClass}
                                    onChange={async (e) => {
                                        setAdminSelectedClass(e.target.value);
                                        setAdminRoster(await api.fetchStudents(e.target.value));
                                    }}>
                                    {allClassrooms.map(c => (
                                        <option key={c.id} value={c.id}>{c.name}</option>
                                    ))}
                                </select>
                            </div>

                            <details style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', marginBottom: '1rem' }}>
                                <summary style={{ fontWeight: 600, cursor: 'pointer', color: 'var(--text-secondary)' }}>+ Enroll Student to Section</summary>
                                <form style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '12px' }}
                                    onSubmit={async (e) => {
                                        e.preventDefault();
                                        if (!enrollName.trim() || !enrollId.trim()) return;
                                        try {
                                            await api.enrollStudent(adminSelectedClass, { name: enrollName, student_id: enrollId, email: enrollEmail || null });
                                            toast(`${enrollName} enrolled successfully ✓`, 'success');
                                            setEnrollName(''); setEnrollId(''); setEnrollEmail('');
                                            setAdminRoster(await api.fetchStudents(adminSelectedClass));
                                        } catch (err) { toast(err.message, 'error'); }
                                    }}>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                        <div className="input-group" style={{ marginBottom: 0 }}>
                                            <label>Student Name</label>
                                            <input type="text" className="input-control" value={enrollName} onChange={e => setEnrollName(e.target.value)} />
                                        </div>
                                        <div className="input-group" style={{ marginBottom: 0 }}>
                                            <label>Roll / ID</label>
                                            <input type="text" className="input-control" value={enrollId} onChange={e => setEnrollId(e.target.value)} />
                                        </div>
                                    </div>
                                    <div className="input-group" style={{ marginBottom: 0 }}>
                                        <label>Login Email (optional)</label>
                                        <input type="email" className="input-control" value={enrollEmail} onChange={e => setEnrollEmail(e.target.value)} />
                                    </div>
                                    <button type="submit" className="btn btn-primary btn-full">Enroll Student</button>
                                </form>
                            </details>

                            <button className="btn" style={{ marginBottom: '12px' }} onClick={async () => {
                                if (adminSelectedClass) setAdminRoster(await api.fetchStudents(adminSelectedClass));
                            }}>↻ Load Roster</button>

                            {adminRoster.length > 0 ? (
                                <table className="data-table">
                                    <thead><tr><th>Student Name</th><th>Student ID</th></tr></thead>
                                    <tbody>
                                        {adminRoster.map(s => (
                                            <tr key={s.id}><td>{s.name}</td><td style={{ color: 'var(--text-muted)' }}>{s.student_id}</td></tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <p className="text-caption">No students enrolled yet — use the form above.</p>
                            )}
                        </>
                    ) : (
                        <div className="alert alert-info">ℹ No classrooms created yet.</div>
                    )}
                </div>
            )}
            {currentNav === 'Change Password' && (
                <ChangePassword user={user} />
            )}
        </div>
    );
}
