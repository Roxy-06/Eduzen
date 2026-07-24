import { useState, useEffect } from 'react';
import { api } from '../api';

export default function StudentPortal({ user, currentNav }) {
    const [dashboard, setDashboard] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [aiTab, setAiTab] = useState('QA');
    const [qaQuery, setQaQuery] = useState('');
    const [qaResponse, setQaResponse] = useState('');

    const [sumQuery, setSumQuery] = useState('');
    const [sumResponse, setSumResponse] = useState('');

    const [quizTopic, setQuizTopic] = useState('');
    const [quizData, setQuizData] = useState(null);
    const [quizIdx, setQuizIdx] = useState(0);
    const [quizScore, setQuizScore] = useState(0);
    const [quizAnswered, setQuizAnswered] = useState(false);
    const [quizSelected, setQuizSelected] = useState(null);

    const [cardTopic, setCardTopic] = useState('');
    const [cardsData, setCardsData] = useState(null);
    const [cardIdx, setCardIdx] = useState(0);
    const [cardFlipped, setCardFlipped] = useState(false);

    const [report, setReport] = useState({ subjects: [] });
    const [materials, setMaterials] = useState([]);

    useEffect(() => {
        fetchDashboard();
    }, [user.id]);

    const fetchDashboard = async () => {
        try {
            const data = await api.fetchStudentDashboard(user.id);
            setDashboard(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (currentNav === 'My Attendance & Marks') {
            api.fetchStudentReport(user.id).then(r => setReport(r)).catch(() => { });
        } else if (currentNav === 'Course Repository') {
            api.fetchMaterials().then(m => setMaterials(m)).catch(() => { });
        }
    }, [currentNav, user.id]);

    const parseJsonFallback = (raw) => {
        let text = raw.trim();
        if (text.startsWith('```')) {
            text = text.replace(/^```(json)?/, '').replace(/```$/, '').trim();
        }
        return JSON.parse(text);
    };

    const handleAIQA = async () => {
        if (!qaQuery.trim()) return;
        try {
            const res = await api.generateAI('qa', qaQuery);
            setQaResponse(res.response);
        } catch (e) {
            alert(e.message);
        }
    };

    const handleAISummary = async () => {
        try {
            const res = await api.generateAI('summary', sumQuery);
            setSumResponse(res.response);
        } catch (e) {
            alert(e.message);
        }
    };

    const handleAIQuiz = async () => {
        try {
            const res = await api.generateAI('quiz', quizTopic);
            try {
                const parsed = parseJsonFallback(res.response);
                setQuizData(parsed.questions || []);
                setQuizIdx(0);
                setQuizScore(0);
                setQuizAnswered(false);
                setQuizSelected(null);
            } catch (e) {
                alert("Couldn't parse quiz data correctly from AI.");
            }
        } catch (e) {
            alert(e.message);
        }
    };

    const handleAICards = async () => {
        try {
            const res = await api.generateAI('flashcards', cardTopic);
            try {
                const parsed = parseJsonFallback(res.response);
                setCardsData(parsed.cards || []);
                setCardIdx(0);
                setCardFlipped(false);
            } catch (e) {
                alert("Couldn't parse flashcard data correctly from AI.");
            }
        } catch (e) {
            alert(e.message);
        }
    };

    if (loading) return <div>Loading portal...</div>;
    if (error) return <div className="alert alert-error">{error}</div>;

    return (
        <div>
            <div className="hero-banner">
                <span className="text-badge badge-success" style={{ marginBottom: '10px' }}>STUDENT ACADEMIC HUB</span>
                <div className="hero-title">Welcome, {user.name}</div>
                <div className="hero-subtitle">
                    Attendance Status: {dashboard?.attendance_rate || 0}% | Academic Progress: {dashboard?.progress_score || 0}%
                </div>
            </div>

            <div className="metrics-grid">
                <div className="metric-card">
                    <div className="metric-label">Attendance Rate</div>
                    <div className="metric-value">{dashboard?.attendance_rate || 0}%</div>
                    <div className="metric-caption">Across all subjects</div>
                </div>
                <div className="metric-card">
                    <div className="metric-label">Marks Score</div>
                    <div className="metric-value">{dashboard?.progress_score || 0}%</div>
                    <div className="metric-caption">Across all subjects</div>
                </div>
                <div className="metric-card">
                    <div className="metric-label">Subjects</div>
                    <div className="metric-value">{dashboard?.topics_completed || 0}</div>
                    <div className="metric-caption">Enrolled this term</div>
                </div>
                <div className="metric-card">
                    <div className="metric-label">Available Materials</div>
                    <div className="metric-value">{dashboard?.materials_available || 0}</div>
                    <div className="metric-caption">Course resources</div>
                </div>
            </div>

            {currentNav === 'Overview' && (
                <div className="content-card">
                    <div className="card-title">Welcome back</div>
                    <p>
                        You're at <strong>{dashboard?.attendance_rate || 0}%</strong> attendance and <strong>{dashboard?.progress_score || 0}%</strong>
                        marks score across <strong>{dashboard?.topics_completed || 0}</strong> subject(s) this term.
                    </p>
                    <p className="text-caption">Use the navigation on the left to chat with the AI assistant, check attendance & marks, or view your academic standing.</p>
                </div>
            )}

            {currentNav === 'AI Curriculum Assistant' && (
                <div className="content-card">
                    <div className="card-title">AI Curriculum Assistant</div>
                    <p className="text-caption">Powered by vector retrieval grounded in your professor's uploaded syllabus.</p>

                    <div className="tabs-header">
                        {['QA', 'Summary', 'Quiz', 'Flashcards'].map(tab => (
                            <button key={tab} className={`tab-btn ${aiTab === tab ? 'active' : ''}`} onClick={() => setAiTab(tab)}>
                                {tab === 'QA' ? 'Q&A Assistant' : tab === 'Summary' ? 'Module Summarizer' : tab === 'Quiz' ? 'Practice Quiz' : 'Flashcards'}
                            </button>
                        ))}
                    </div>

                    {aiTab === 'QA' && (
                        <div>
                            <textarea
                                className="input-control mb-4"
                                rows="4"
                                placeholder="Ask a question about your course materials..."
                                value={qaQuery} onChange={e => setQaQuery(e.target.value)}
                            />
                            <button className="btn btn-primary" onClick={handleAIQA}>Generate Answer</button>
                            {qaResponse && (
                                <div style={{ marginTop: '1rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                                    <strong>Response</strong>
                                    <p style={{ whiteSpace: 'pre-wrap', margin: '8px 0 0' }}>{qaResponse}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {aiTab === 'Summary' && (
                        <div>
                            <p>Generate a structured executive summary of core concepts.</p>
                            <input
                                type="text"
                                className="input-control mb-4"
                                placeholder="Specific Focus e.g., Chapter 3 key definitions"
                                value={sumQuery} onChange={e => setSumQuery(e.target.value)}
                            />
                            <button className="btn btn-primary" onClick={handleAISummary}>Generate Course Summary</button>
                            {sumResponse && (
                                <div style={{ marginTop: '1rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                                    <strong>Summary</strong>
                                    <p style={{ whiteSpace: 'pre-wrap', margin: '8px 0 0' }}>{sumResponse}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {aiTab === 'Quiz' && (
                        <div>
                            <p>Generate a practice self-assessment quiz from lecture notes.</p>
                            <input
                                type="text"
                                className="input-control mb-4"
                                placeholder="Topic Focus e.g., Data Structures"
                                value={quizTopic} onChange={e => setQuizTopic(e.target.value)}
                            />
                            <button className="btn btn-primary" onClick={handleAIQuiz}>Generate 3-Question Practice Quiz</button>

                            {quizData && quizIdx < quizData.length && (
                                <div style={{ marginTop: '1.5rem' }}>
                                    <strong>Question {quizIdx + 1} of {quizData.length}</strong>
                                    <p>{quizData[quizIdx].question}</p>

                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        {Object.entries(quizData[quizIdx].options).map(([k, v]) => (
                                            <button
                                                key={k}
                                                className={`btn ${quizAnswered ? (k === quizData[quizIdx].correct ? 'alert-success' : k === quizSelected ? 'alert-error' : '') : ''}`}
                                                onClick={() => {
                                                    if (!quizAnswered) {
                                                        setQuizAnswered(true);
                                                        setQuizSelected(k);
                                                        if (k === quizData[quizIdx].correct) setQuizScore(s => s + 1);
                                                    }
                                                }}
                                            >
                                                {k}. {v} {quizAnswered && k === quizData[quizIdx].correct && "  ✓ Correct answer"}
                                                {quizAnswered && k === quizSelected && k !== quizData[quizIdx].correct && "  ✗ Your answer"}
                                            </button>
                                        ))}
                                    </div>

                                    {quizAnswered && (
                                        <div style={{ marginTop: '1rem' }}>
                                            {quizSelected === quizData[quizIdx].correct ? (
                                                <div className="alert alert-success">Correct!</div>
                                            ) : (
                                                <div className="alert alert-error">Not quite — the correct answer was {quizData[quizIdx].correct}.</div>
                                            )}

                                            {quizIdx + 1 < quizData.length ? (
                                                <button className="btn btn-primary" onClick={() => { setQuizIdx(i => i + 1); setQuizAnswered(false); setQuizSelected(null); }}>Next Question</button>
                                            ) : (
                                                <button className="btn btn-primary" onClick={() => setQuizIdx(i => i + 1)}>See Final Score</button>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                            {quizData && quizIdx >= quizData.length && (
                                <div style={{ marginTop: '1.5rem' }}>
                                    <h3>Quiz complete — {quizScore} / {quizData.length} correct</h3>
                                    <button className="btn" onClick={() => { setQuizIdx(0); setQuizScore(0); setQuizAnswered(false); setQuizSelected(null); }}>Retake Quiz</button>
                                </div>
                            )}
                        </div>
                    )}

                    {aiTab === 'Flashcards' && (
                        <div>
                            <p>Generate revision flashcards for key terms and definitions.</p>
                            <input
                                type="text"
                                className="input-control mb-4"
                                placeholder="Concept Focus e.g., Formulas"
                                value={cardTopic} onChange={e => setCardTopic(e.target.value)}
                            />
                            <button className="btn btn-primary" onClick={handleAICards}>Generate Study Flashcards</button>

                            {cardsData && cardsData.length > 0 && (
                                <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                                    <p>Card {cardIdx + 1} of {cardsData.length}</p>
                                    <div className="flip-card">
                                        <div className={`flip-card-inner ${cardFlipped ? 'is-flipped' : ''}`}>
                                            <div className="flip-card-face flip-card-front">
                                                <div className="flip-label">Question</div>
                                                <div className="flip-text">{cardsData[cardIdx].question}</div>
                                            </div>
                                            <div className="flip-card-face flip-card-back">
                                                <div className="flip-label">Answer</div>
                                                <div className="flip-text">{cardsData[cardIdx].answer}</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                                        <button className="btn btn-primary" style={{ flex: 1 }} disabled={cardIdx === 0} onClick={() => { setCardIdx(i => i - 1); setCardFlipped(false); }}>Previous</button>
                                        <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => setCardFlipped(!cardFlipped)}>Flip Card</button>
                                        <button className="btn btn-primary" style={{ flex: 1 }} disabled={cardIdx === cardsData.length - 1} onClick={() => { setCardIdx(i => i + 1); setCardFlipped(false); }}>Next</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {currentNav === 'My Attendance & Marks' && (
                <div className="content-card">
                    <div className="card-title">My Attendance & Marks — By Subject</div>
                    {report.subjects && report.subjects.length > 0 ? (
                        report.subjects.map((subj) => (
                            <div key={subj.subject_id} style={{ marginBottom: '1.5rem' }}>
                                <p><strong>{subj.subject_name}</strong> ({subj.subject_code})</p>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <div>Attendance: {subj.attended} / {subj.sessions_held} classes</div>
                                        <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', margin: '4px 0' }}>
                                            <div style={{ background: '#065f46', height: '100%', borderRadius: '4px', width: `${Math.min(100, subj.attendance_pct)}%` }}></div>
                                        </div>
                                        <div className="text-caption">{subj.attendance_pct}% attendance</div>
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <div>Marks Score: {subj.marks_pct}%</div>
                                        {subj.marks && subj.marks.length > 0 ? (
                                            <table className="data-table">
                                                <thead><tr><th>Exam</th><th>Marks Obtained</th><th>Out Of</th></tr></thead>
                                                <tbody>
                                                    {subj.marks.map((m, idx) => (
                                                        <tr key={idx}><td>{m.exam_name}</td><td>{m.marks_obtained}</td><td>{m.max_marks}</td></tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        ) : (
                                            <div className="text-caption">No marks posted yet.</div>
                                        )}
                                    </div>
                                </div>
                                <div className="divider"></div>
                            </div>
                        ))
                    ) : (
                        <div className="alert alert-info">No subject data available yet — check back once your teacher has taken attendance and posted marks.</div>
                    )}
                </div>
            )}

            {currentNav === 'Academic Standing' && (
                <div className="content-card">
                    <div className="card-title">Academic Standing</div>

                    <div className="mb-4">
                        <div className="mb-2">Overall Marks Score: {dashboard?.progress_score || 0}%</div>
                        <div style={{ background: '#e2e8f0', height: '12px', borderRadius: '6px' }}>
                            <div style={{ background: '#70020f', height: '100%', borderRadius: '6px', width: `${Math.min(100, dashboard?.progress_score || 0)}%` }}></div>
                        </div>
                    </div>

                    <div className="mb-4">
                        <div className="mb-2">Overall Attendance: {dashboard?.attendance_rate || 0}%</div>
                        <div style={{ background: '#e2e8f0', height: '12px', borderRadius: '6px' }}>
                            <div style={{ background: '#70020f', height: '100%', borderRadius: '6px', width: `${Math.min(100, dashboard?.attendance_rate || 0)}%` }}></div>
                        </div>
                    </div>

                    <div className="divider"></div>
                    <p><strong>Latest Activity:</strong> {dashboard?.latest_activity || 'N/A'}</p>
                    <p><strong>Next Academic Goal:</strong> {dashboard?.next_goal || 'N/A'}</p>
                </div>
            )}

            {currentNav === 'Course Repository' && (
                <div className="content-card">
                    <div className="card-title">Course Repository Access</div>
                    {materials.length > 0 ? (
                        <ul style={{ paddingLeft: '20px' }}>
                            {materials.map((item, idx) => (
                                <li key={idx}><strong>{item.filename}</strong> (Uploaded: {new Date(item.uploaded_at).toLocaleString()})</li>
                            ))}
                        </ul>
                    ) : (
                        <div className="alert alert-info">No materials published by faculty yet.</div>
                    )}
                </div>
            )}
        </div>
    );
}
