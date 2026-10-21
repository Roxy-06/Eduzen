import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { useToast } from '../App';
import ChangePassword from '../components/ChangePassword';

// ─── Confetti ─────────────────────────────────────────────
function launchConfetti() {
    const canvas = document.createElement('canvas');
    canvas.id = 'confetti-canvas';
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9998;';
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const pieces = Array.from({ length: 120 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * -canvas.height,
        r: Math.random() * 8 + 4,
        d: Math.random() * 80 + 20,
        color: ['#a78bfa','#5eead4','#fcd34d','#f472b6','#60a5fa'][Math.floor(Math.random()*5)],
        tilt: Math.random() * 10 - 10,
        tiltAngle: 0,
        tiltSpeed: Math.random() * 0.1 + 0.05,
    }));

    let frame = 0;
    const draw = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        pieces.forEach(p => {
            ctx.beginPath();
            ctx.lineWidth = p.r / 2;
            ctx.strokeStyle = p.color;
            ctx.moveTo(p.x + p.tilt + p.r / 3, p.y);
            ctx.lineTo(p.x + p.tilt, p.y + p.tilt + p.r);
            ctx.stroke();
        });
        pieces.forEach(p => {
            p.tiltAngle += p.tiltSpeed;
            p.y += (Math.cos(frame / 22) + p.d / 20) * 1.5;
            p.tilt = Math.sin(p.tiltAngle - frame / 3) * 12;
            if (p.y > canvas.height) { p.y = -20; p.x = Math.random() * canvas.width; }
        });
        frame++;
        if (frame < 180) requestAnimationFrame(draw);
        else canvas.remove();
    };
    draw();
}

// ─── Typing animation hook ────────────────────────────────
function useTypingEffect(text, speed = 18) {
    const [displayed, setDisplayed] = useState('');
    const [done, setDone] = useState(false);
    useEffect(() => {
        if (!text) { setDisplayed(''); setDone(false); return; }
        setDisplayed('');
        setDone(false);
        let i = 0;
        const timer = setInterval(() => {
            setDisplayed(text.slice(0, i + 1));
            i++;
            if (i >= text.length) { clearInterval(timer); setDone(true); }
        }, speed);
        return () => clearInterval(timer);
    }, [text]);
    return { displayed, done };
}

export default function StudentPortal({ user, currentNav }) {
    const toast = useToast();
    const [dashboard, setDashboard] = useState(null);
    const [loading, setLoading]     = useState(true);

    const [aiTab, setAiTab]         = useState('QA');
    const [aiLoading, setAiLoading] = useState(false);

    const [qaQuery, setQaQuery]     = useState('');
    const [qaRaw, setQaRaw]         = useState('');

    const [sumQuery, setSumQuery]   = useState('');
    const [sumRaw, setSumRaw]       = useState('');

    const [quizTopic, setQuizTopic] = useState('');
    const [quizData, setQuizData]   = useState(null);
    const [quizIdx, setQuizIdx]     = useState(0);
    const [quizScore, setQuizScore] = useState(0);
    const [quizAnswered, setQuizAnswered] = useState(false);
    const [quizSelected, setQuizSelected] = useState(null);

    const [cardTopic, setCardTopic] = useState('');
    const [cardsData, setCardsData] = useState(null);
    const [cardIdx, setCardIdx]     = useState(0);
    const [cardFlipped, setCardFlipped] = useState(false);

    const [report, setReport]       = useState({ subjects: [] });
    const [materials, setMaterials] = useState([]);

    // ── Live Quizzes state ────────────────────────────────
    const [quizList, setQuizList]         = useState([]);
    const [activeQuiz, setActiveQuiz]     = useState(null);
    const [quizAnswers, setQuizAnswers]   = useState({});
    const [quizSubmitted, setQuizSubmitted] = useState(false);
    const [quizScoreResult, setQuizScoreResult] = useState(null);
    const [quizSubmitting, setQuizSubmitting]   = useState(false);
    const [quizCurrIdx, setQuizCurrIdx]   = useState(0);

    // Typing effects
    const { displayed: qaDisplay, done: qaDone }   = useTypingEffect(qaRaw);
    const { displayed: sumDisplay, done: sumDone }  = useTypingEffect(sumRaw);

    useEffect(() => { fetchDashboard(); }, [user.id]);

    const fetchDashboard = async () => {
        try {
            const data = await api.fetchStudentDashboard(user.id);
            setDashboard(data);
        } catch (err) { toast(err.message, 'error'); }
        finally { setLoading(false); }
    };

    useEffect(() => {
        if (currentNav === 'My Attendance & Marks')
            api.fetchStudentReport(user.id).then(r => setReport(r)).catch(() => {});
        else if (currentNav === 'Course Repository')
            api.fetchMaterials(user.id).then(m => setMaterials(m)).catch(() => {});
        else if (currentNav === 'Live Quizzes') {
            api.fetchStudentQuizzes(user.id).then(d => setQuizList(d.quizzes || [])).catch(() => {});
            setActiveQuiz(null); setQuizAnswers({}); setQuizSubmitted(false); setQuizScoreResult(null); setQuizCurrIdx(0);
        }
    }, [currentNav, user.id]);

    const parseJsonFallback = (raw) => {
        let text = raw.trim();
        if (text.startsWith('```')) text = text.replace(/^```(json)?/, '').replace(/```$/, '').trim();
        return JSON.parse(text);
    };

    const handleAIQA = async () => {
        if (!qaQuery.trim()) return;
        setAiLoading(true); setQaRaw('');
        try {
            const res = await api.generateAI('qa', qaQuery);
            setQaRaw(res.response);
        } catch (e) { toast(e.message, 'error'); }
        finally { setAiLoading(false); }
    };

    const handleAISummary = async () => {
        setAiLoading(true); setSumRaw('');
        try {
            const res = await api.generateAI('summary', sumQuery);
            setSumRaw(res.response);
        } catch (e) { toast(e.message, 'error'); }
        finally { setAiLoading(false); }
    };

    const handleAIQuiz = async () => {
        setAiLoading(true); setQuizData(null);
        try {
            const res = await api.generateAI('quiz', quizTopic);
            const parsed = parseJsonFallback(res.response);
            setQuizData(parsed.questions || []);
            setQuizIdx(0); setQuizScore(0); setQuizAnswered(false); setQuizSelected(null);
        } catch (e) { toast("Couldn't generate quiz. Try uploading materials first.", 'error'); }
        finally { setAiLoading(false); }
    };

    const handleAICards = async () => {
        setAiLoading(true); setCardsData(null);
        try {
            const res = await api.generateAI('flashcards', cardTopic);
            const parsed = parseJsonFallback(res.response);
            setCardsData(parsed.cards || []);
            setCardIdx(0); setCardFlipped(false);
        } catch (e) { toast("Couldn't generate flashcards.", 'error'); }
        finally { setAiLoading(false); }
    };

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: '14px', color: 'var(--text-muted)' }}>
            <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} /> Loading portal...
        </div>
    );

    const attRate = dashboard?.attendance_rate || 0;
    const markRate = dashboard?.progress_score || 0;

    return (
        <div>
            {/* Hero */}
            <div className="hero-banner">
                <div className="hero-badge" style={{ background: 'rgba(94,234,212,0.15)', borderColor: 'rgba(94,234,212,0.3)' }}>
                    🎓 Student Academic Hub
                </div>
                <div className="hero-title">Welcome, {user.name}</div>
                <div className="hero-subtitle">
                    Attendance: {attRate}% &nbsp;·&nbsp; Marks Score: {markRate}%
                </div>
            </div>

            {/* Metrics */}
            <div className="metrics-grid">
                {[
                    { icon: '📅', label: 'Attendance Rate', value: `${attRate}%`, caption: 'Across all subjects' },
                    { icon: '🏆', label: 'Marks Score',     value: `${markRate}%`, caption: 'Academic performance' },
                    { icon: '📖', label: 'Subjects',         value: dashboard?.topics_completed || 0, caption: 'Enrolled this term' },
                    { icon: '📄', label: 'Materials',         value: dashboard?.materials_available || 0, caption: 'Available resources' },
                ].map(m => (
                    <div className="metric-card" key={m.label} style={{ '--accent': '#0d9488', '--teal': '#7c3aed' }}>
                        <div className="metric-icon">{m.icon}</div>
                        <div className="metric-label">{m.label}</div>
                        <div className="metric-value" style={{ background: 'linear-gradient(135deg, var(--text-primary), var(--teal-light, #5eead4))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>{m.value}</div>
                        <div className="metric-caption">{m.caption}</div>
                    </div>
                ))}
            </div>

            {/* ── DASHBOARD ── */}
            {currentNav === 'Dashboard' && (
                <div className="content-card">
                    <div className="card-title">🏠 Dashboard</div>
                    <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                        You're at <strong>{attRate}%</strong> attendance and <strong>{markRate}%</strong> marks score
                        across <strong>{dashboard?.topics_completed || 0}</strong> subject(s) this term.
                    </p>
                    <p className="text-caption" style={{ marginTop: '10px' }}>
                        Use the AI Curriculum Assistant to chat with your course materials, generate quizzes, and create flashcards.
                    </p>
                    {attRate < 75 && (
                        <div className="alert alert-warning" style={{ marginTop: '16px' }}>
                            ⚠ Your overall attendance is below 75%. Please attend classes regularly to avoid academic penalties.
                        </div>
                    )}
                </div>
            )}

            {/* ── AI CURRICULUM ASSISTANT ── */}
            {currentNav === 'AI Curriculum Assistant' && (
                <div className="content-card">
                    <div className="card-title">🤖 AI Curriculum Assistant</div>
                    <p className="text-caption" style={{ marginBottom: '16px' }}>
                        Powered by Google Gemini + FAISS vector retrieval — grounded in your professor's uploaded materials.
                    </p>

                    <div className="tabs-header">
                        {[
                            { id: 'QA', label: '💬 Q&A Assistant' },
                            { id: 'Summary', label: '📝 Summarizer' },
                            { id: 'Quiz', label: '🎯 Practice Quiz' },
                            { id: 'Flashcards', label: '🃏 Flashcards' },
                        ].map(t => (
                            <button key={t.id} className={`tab-btn ${aiTab === t.id ? 'active' : ''}`}
                                onClick={() => setAiTab(t.id)}>{t.label}</button>
                        ))}
                    </div>

                    {/* Q&A */}
                    {aiTab === 'QA' && (
                        <div>
                            <textarea className="input-control mb-4" rows="4"
                                placeholder="Ask anything about your course materials..."
                                value={qaQuery} onChange={e => setQaQuery(e.target.value)}
                                onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleAIQA(); }}
                            />
                            <button className="btn btn-primary" onClick={handleAIQA} disabled={aiLoading}>
                                {aiLoading ? <><span className="spinner" /> Thinking...</> : '→ Get Answer'}
                            </button>
                            {(qaDisplay || aiLoading) && (
                                <div style={{ marginTop: '16px', padding: '18px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                                    <div style={{ fontSize: '0.72rem', color: 'var(--accent-light)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>
                                        ✦ AI Response
                                    </div>
                                    <p style={{ whiteSpace: 'pre-wrap', color: 'var(--text-primary)', lineHeight: 1.7 }}
                                        className={!qaDone ? 'typing-cursor' : ''}>{qaDisplay}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Summary */}
                    {aiTab === 'Summary' && (
                        <div>
                            <p style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>Generate a structured summary of your course material.</p>
                            <input type="text" className="input-control mb-4"
                                placeholder="Topic focus e.g. Chapter 3 key definitions (optional)"
                                value={sumQuery} onChange={e => setSumQuery(e.target.value)} />
                            <button className="btn btn-primary" onClick={handleAISummary} disabled={aiLoading}>
                                {aiLoading ? <><span className="spinner" /> Generating...</> : '→ Generate Summary'}
                            </button>
                            {(sumDisplay || aiLoading) && (
                                <div style={{ marginTop: '16px', padding: '18px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                                    <div style={{ fontSize: '0.72rem', color: 'var(--teal-light)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>
                                        📝 Summary
                                    </div>
                                    <p style={{ whiteSpace: 'pre-wrap', color: 'var(--text-primary)', lineHeight: 1.7 }}
                                        className={!sumDone ? 'typing-cursor' : ''}>{sumDisplay}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Quiz */}
                    {aiTab === 'Quiz' && (
                        <div>
                            <p style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>Generate a 3-question self-assessment quiz.</p>
                            <input type="text" className="input-control mb-4"
                                placeholder="Topic focus e.g. Data Structures (optional)"
                                value={quizTopic} onChange={e => setQuizTopic(e.target.value)} />
                            <button className="btn btn-primary" onClick={handleAIQuiz} disabled={aiLoading}>
                                {aiLoading ? <><span className="spinner" /> Generating quiz...</> : '🎯 Generate Practice Quiz'}
                            </button>

                            {quizData && quizIdx < quizData.length && (
                                <div style={{ marginTop: '24px', padding: '20px', background: 'var(--bg-surface)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                                        Question {quizIdx + 1} of {quizData.length} · Score: {quizScore}/{quizData.length}
                                    </div>
                                    <p style={{ fontWeight: 600, fontSize: '1.05rem', color: 'var(--text-primary)', marginBottom: '16px' }}>
                                        {quizData[quizIdx].question}
                                    </p>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        {Object.entries(quizData[quizIdx].options).map(([k, v]) => {
                                            const isCorrect = k === quizData[quizIdx].correct;
                                            const isSelected = k === quizSelected;
                                            let bg = 'var(--bg-surface-hover)';
                                            let border = 'var(--border)';
                                            let color = 'var(--text-primary)';
                                            if (quizAnswered && isCorrect)  { bg = 'rgba(16,185,129,0.15)'; border = 'rgba(16,185,129,0.5)'; color = '#6ee7b7'; }
                                            if (quizAnswered && isSelected && !isCorrect) { bg = 'rgba(239,68,68,0.15)'; border = 'rgba(239,68,68,0.5)'; color = '#fca5a5'; }
                                            return (
                                                <button key={k} disabled={quizAnswered}
                                                    style={{ background: bg, border: `1px solid ${border}`, color, borderRadius: 'var(--radius-sm)', padding: '12px 16px', textAlign: 'left', cursor: quizAnswered ? 'default' : 'pointer', transition: 'all 0.2s', fontFamily: 'Inter, sans-serif', fontSize: '0.92rem' }}
                                                    onClick={() => {
                                                        if (quizAnswered) return;
                                                        setQuizAnswered(true); setQuizSelected(k);
                                                        if (k === quizData[quizIdx].correct) setQuizScore(s => s + 1);
                                                    }}>
                                                    <strong>{k}.</strong> {v}
                                                    {quizAnswered && isCorrect && ' ✓'}
                                                    {quizAnswered && isSelected && !isCorrect && ' ✗'}
                                                </button>
                                            );
                                        })}
                                    </div>
                                    {quizAnswered && (
                                        <div style={{ marginTop: '14px' }}>
                                            {quizSelected === quizData[quizIdx].correct
                                                ? <div className="alert alert-success">✓ Correct!</div>
                                                : <div className="alert alert-error">✕ The correct answer was <strong>{quizData[quizIdx].correct}</strong>.</div>
                                            }
                                            {quizIdx + 1 < quizData.length ? (
                                                <button className="btn btn-primary" onClick={() => { setQuizIdx(i => i + 1); setQuizAnswered(false); setQuizSelected(null); }}>
                                                    Next Question →
                                                </button>
                                            ) : (
                                                <button className="btn btn-primary" onClick={() => setQuizIdx(i => i + 1)}>
                                                    See Final Score 🏆
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            {quizData && quizIdx >= quizData.length && (() => {
                                const perfect = quizScore === quizData.length;
                                if (perfect) setTimeout(launchConfetti, 100);
                                return (
                                    <div style={{ marginTop: '24px', textAlign: 'center', padding: '28px', background: 'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(13,148,136,0.1))', borderRadius: 'var(--radius)', border: '1px solid var(--border-strong)' }}>
                                        <div style={{ fontSize: '3rem', marginBottom: '10px' }}>{perfect ? '🎉' : quizScore >= 2 ? '👍' : '📚'}</div>
                                        <div style={{ fontFamily: 'Outfit', fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                                            {quizScore} / {quizData.length} Correct
                                        </div>
                                        <div style={{ color: 'var(--text-muted)', marginTop: '6px', marginBottom: '18px' }}>
                                            {perfect ? 'Perfect score! 🌟' : quizScore >= 2 ? 'Great job! Keep it up.' : 'Review the material and try again.'}
                                        </div>
                                        <button className="btn btn-primary" onClick={() => { setQuizIdx(0); setQuizScore(0); setQuizAnswered(false); setQuizSelected(null); }}>
                                            ↩ Retake Quiz
                                        </button>
                                    </div>
                                );
                            })()}
                        </div>
                    )}

                    {/* Flashcards */}
                    {aiTab === 'Flashcards' && (
                        <div>
                            <p style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>Generate revision flashcards for key terms and definitions.</p>
                            <input type="text" className="input-control mb-4"
                                placeholder="Concept focus e.g. Formulas, Key Terms (optional)"
                                value={cardTopic} onChange={e => setCardTopic(e.target.value)} />
                            <button className="btn btn-primary" onClick={handleAICards} disabled={aiLoading}>
                                {aiLoading ? <><span className="spinner" /> Generating cards...</> : '🃏 Generate Flashcards'}
                            </button>

                            {cardsData && cardsData.length > 0 && (
                                <div style={{ marginTop: '24px', textAlign: 'center' }}>
                                    <p style={{ color: 'var(--text-muted)', marginBottom: '12px' }}>
                                        Card {cardIdx + 1} of {cardsData.length} — click to flip
                                    </p>
                                    <div className="flip-card" onClick={() => setCardFlipped(!cardFlipped)} style={{ cursor: 'pointer' }}>
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
                                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '8px' }}>
                                        <button className="btn btn-primary" disabled={cardIdx === 0}
                                            onClick={() => { setCardIdx(i => i - 1); setCardFlipped(false); }}>← Prev</button>
                                        <button className="btn" onClick={() => setCardFlipped(!cardFlipped)}>Flip</button>
                                        <button className="btn btn-primary" disabled={cardIdx === cardsData.length - 1}
                                            onClick={() => { setCardIdx(i => i + 1); setCardFlipped(false); }}>Next →</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* ── LIVE QUIZZES ── */}
            {currentNav === 'Live Quizzes' && (
                <div className="content-card">
                    <div className="card-title">🎯 Live Quizzes</div>

                    {!activeQuiz ? (
                        <>
                            <p className="text-caption" style={{ marginBottom: '16px' }}>
                                Quizzes published by your teachers for your classroom. Take each quiz once.
                            </p>
                            {quizList.length === 0 ? (
                                <div className="alert alert-info">ℹ No active quizzes available right now. Check back later.</div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    {quizList.map(q => (
                                        <div key={q.id} style={{
                                            display: 'flex', alignItems: 'center', gap: '16px',
                                            padding: '16px', background: 'var(--bg-surface)',
                                            borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)',
                                        }}>
                                            <div style={{ fontSize: '1.8rem' }}>{q.submitted ? '✅' : '🎯'}</div>
                                            <div style={{ flex: 1 }}>
                                                <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '1rem' }}>{q.title}</div>
                                                <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: '2px' }}>
                                                    {q.subject_name} · {q.classroom_name} · {q.question_count} questions
                                                </div>
                                                {q.submitted && (
                                                    <div style={{ marginTop: '4px', fontSize: '0.85rem', color: '#6ee7b7' }}>
                                                        ✓ Scored {q.score}/{q.total} ({Math.round(q.score/q.total*100)}%)
                                                    </div>
                                                )}
                                            </div>
                                            {q.submitted ? (
                                                <span className="text-badge badge-present">Submitted</span>
                                            ) : (
                                                <button className="btn btn-primary"
                                                    onClick={() => {
                                                        setActiveQuiz(q);
                                                        setQuizAnswers({});
                                                        setQuizSubmitted(false);
                                                        setQuizScoreResult(null);
                                                        setQuizCurrIdx(0);
                                                    }}>
                                                    ▶ Start Quiz
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </>
                    ) : !quizSubmitted ? (
                        <>
                            <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)' }}>{activeQuiz.title}</div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>{activeQuiz.subject_name} · {activeQuiz.classroom_name}</div>
                                </div>
                                <button className="btn" onClick={() => setActiveQuiz(null)}>← Back</button>
                            </div>

                            {/* Question navigator */}
                            <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
                                {activeQuiz.questions.map((_, idx) => (
                                    <button key={idx}
                                        onClick={() => setQuizCurrIdx(idx)}
                                        style={{
                                            width: 36, height: 36, borderRadius: '50%', border: 'none', cursor: 'pointer',
                                            fontWeight: 700, fontSize: '0.85rem',
                                            background: quizAnswers[String(idx)] ? 'var(--accent)' : (quizCurrIdx === idx ? 'var(--border-strong)' : 'var(--bg-surface)'),
                                            color: quizAnswers[String(idx)] ? '#fff' : 'var(--text-secondary)',
                                        }}>
                                        {idx + 1}
                                    </button>
                                ))}
                            </div>

                            {/* Current question */}
                            {(() => {
                                const q = activeQuiz.questions[quizCurrIdx];
                                const selectedOpt = quizAnswers[String(quizCurrIdx)];
                                return (
                                    <div style={{ padding: '20px', background: 'var(--bg-surface)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                                            Question {quizCurrIdx + 1} of {activeQuiz.questions.length}
                                        </div>
                                        <p style={{ fontWeight: 600, fontSize: '1.05rem', color: 'var(--text-primary)', marginBottom: '18px' }}>
                                            {q.question}
                                        </p>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                            {Object.entries(q.options).map(([k, v]) => (
                                                <button key={k}
                                                    onClick={() => setQuizAnswers(prev => ({ ...prev, [String(quizCurrIdx)]: k }))}
                                                    style={{
                                                        textAlign: 'left', padding: '12px 16px', borderRadius: 'var(--radius-sm)',
                                                        border: `2px solid ${selectedOpt === k ? 'var(--accent)' : 'var(--border)'}`,
                                                        background: selectedOpt === k ? 'rgba(124,58,237,0.15)' : 'var(--bg-surface-hover)',
                                                        color: 'var(--text-primary)', cursor: 'pointer',
                                                        fontFamily: 'Inter, sans-serif', fontSize: '0.92rem', transition: 'all 0.15s',
                                                    }}>
                                                    <strong>{k}.</strong> {v}
                                                    {selectedOpt === k && ' ✓'}
                                                </button>
                                            ))}
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
                                            <button className="btn" disabled={quizCurrIdx === 0}
                                                onClick={() => setQuizCurrIdx(i => i - 1)}>← Prev</button>
                                            {quizCurrIdx < activeQuiz.questions.length - 1 ? (
                                                <button className="btn btn-primary"
                                                    onClick={() => setQuizCurrIdx(i => i + 1)}>Next →</button>
                                            ) : (
                                                <button className="btn btn-primary"
                                                    disabled={quizSubmitting}
                                                    onClick={async () => {
                                                        // Build answers keyed by question id
                                                        const mapped = {};
                                                        activeQuiz.questions.forEach((q, idx) => {
                                                            const qid = String(q.id ?? q.question);
                                                            if (quizAnswers[String(idx)]) mapped[qid] = quizAnswers[String(idx)];
                                                        });
                                                        setQuizSubmitting(true);
                                                        try {
                                                            const res = await api.submitQuiz(activeQuiz.id, user.id, mapped);
                                                            setQuizScoreResult(res);
                                                            setQuizSubmitted(true);
                                                        } catch (e) { toast(e.message, 'error'); }
                                                        finally { setQuizSubmitting(false); }
                                                    }}>
                                                    {quizSubmitting ? <><span className="spinner" /> Submitting...</> : '🏁 Submit Quiz'}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })()}
                        </>
                    ) : (
                        // Score screen
                        <div style={{ textAlign: 'center', padding: '32px', background: 'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(13,148,136,0.1))', borderRadius: 'var(--radius)', border: '1px solid var(--border-strong)' }}>
                            <div style={{ fontSize: '3.5rem', marginBottom: '12px' }}>
                                {quizScoreResult?.score === quizScoreResult?.total ? '🎉' : quizScoreResult?.score >= quizScoreResult?.total / 2 ? '👍' : '📚'}
                            </div>
                            <div style={{ fontFamily: 'Outfit', fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px' }}>
                                {quizScoreResult?.score} / {quizScoreResult?.total} Correct
                            </div>
                            <div style={{ color: 'var(--text-muted)', marginBottom: '6px' }}>
                                {Math.round(quizScoreResult?.score / quizScoreResult?.total * 100)}% score
                            </div>
                            <div style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
                                {quizScoreResult?.score === quizScoreResult?.total ? 'Perfect score! 🌟' :
                                    quizScoreResult?.score >= quizScoreResult?.total / 2 ? 'Great effort! Keep it up.' :
                                    'Review the material and discuss with your teacher.'}
                            </div>
                            <button className="btn btn-primary" onClick={() => {
                                setActiveQuiz(null);
                                api.fetchStudentQuizzes(user.id).then(d => setQuizList(d.quizzes || [])).catch(() => {});
                            }}>
                                ← Back to Quizzes
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* ── MY ATTENDANCE & MARKS ── */}
            {currentNav === 'My Attendance & Marks' && (
                <div className="content-card">
                    <div className="card-title">📊 Attendance & Marks — By Subject</div>
                    {report.subjects?.length > 0 ? report.subjects.map(subj => (
                        <div key={subj.subject_id} style={{ marginBottom: '24px' }}>
                            <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
                                {subj.subject_name}
                                <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: '0.88rem', marginLeft: '8px' }}>({subj.subject_code})</span>
                            </p>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.88rem' }}>
                                        <span style={{ color: 'var(--text-secondary)' }}>Attendance</span>
                                        <strong>{subj.attended}/{subj.sessions_held} classes</strong>
                                    </div>
                                    <div className="progress-bar-bg">
                                        <div className={`progress-bar-fill ${subj.attendance_pct < 75 ? 'danger' : ''}`}
                                            style={{ width: `${Math.min(100, subj.attendance_pct)}%` }} />
                                    </div>
                                    <div className="text-caption">{subj.attendance_pct}%
                                        {subj.attendance_pct < 75 && <span style={{ color: '#fca5a5', marginLeft: 6 }}>⚠ Below threshold</span>}
                                    </div>
                                </div>
                                <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.88rem' }}>
                                        <span style={{ color: 'var(--text-secondary)' }}>Marks Score</span>
                                        <strong>{subj.marks_pct}%</strong>
                                    </div>
                                    <div className="progress-bar-bg">
                                        <div className="progress-bar-fill" style={{ width: `${Math.min(100, subj.marks_pct)}%` }} />
                                    </div>
                                    <div className="text-caption">Performance score</div>
                                </div>
                            </div>
                            {subj.marks?.length > 0 && (
                                <table className="data-table" style={{ marginTop: '12px' }}>
                                    <thead><tr><th>Exam</th><th>Marks Obtained</th><th>Out Of</th></tr></thead>
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
                            <div className="divider" />
                        </div>
                    )) : (
                        <div className="alert alert-info">ℹ No subject data yet — check back after your teacher takes attendance.</div>
                    )}
                </div>
            )}

            {/* ── ACADEMIC STANDING ── */}
            {currentNav === 'Academic Standing' && (
                <div className="content-card">
                    <div className="card-title">🎓 Academic Standing</div>
                    <div style={{ marginBottom: '20px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Overall Marks Score</span>
                            <strong>{markRate}%</strong>
                        </div>
                        <div className="progress-bar-bg" style={{ height: '12px' }}>
                            <div className="progress-bar-fill" style={{ width: `${Math.min(100, markRate)}%` }} />
                        </div>
                    </div>
                    <div style={{ marginBottom: '20px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Overall Attendance</span>
                            <strong>{attRate}%</strong>
                        </div>
                        <div className="progress-bar-bg" style={{ height: '12px' }}>
                            <div className={`progress-bar-fill ${attRate < 75 ? 'danger' : ''}`}
                                style={{ width: `${Math.min(100, attRate)}%` }} />
                        </div>
                        {attRate < 75 && <div style={{ color: '#fca5a5', fontSize: '0.84rem', marginTop: '6px' }}>⚠ Below 75% — academic risk</div>}
                    </div>
                    <div className="divider" />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <p><span style={{ color: 'var(--text-muted)' }}>Latest Activity: </span><strong>{dashboard?.latest_activity || 'N/A'}</strong></p>
                        <p><span style={{ color: 'var(--text-muted)' }}>Next Academic Goal: </span><strong>{dashboard?.next_goal || 'N/A'}</strong></p>
                    </div>
                </div>
            )}

            {/* ── COURSE REPOSITORY ── */}
            {currentNav === 'Course Repository' && (
                <div className="content-card">
                    <div className="card-title">📚 Course Repository</div>
                    {materials.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {materials.map((item, i) => {
                                const ext = item.filename.split('.').pop().toUpperCase();
                                const isPdf = ext === 'PDF';
                                return (
                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '14px', padding: '14px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                                        <span style={{ fontSize: '1.5rem' }}>{isPdf ? '📄' : '📊'}</span>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                {item.filename}
                                                <span className={`text-badge ${item.classroom_name ? 'badge-primary' : 'badge-dark'}`} style={{ fontSize: '0.68rem' }}>
                                                    {item.classroom_name ? `🏫 ${item.classroom_name}` : '🌐 All Classrooms'}
                                                </span>
                                            </div>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                                {ext} · Uploaded {new Date(item.uploaded_at).toLocaleString()}
                                            </div>
                                        </div>
                                        <a
                                            href={api.getDownloadUrl(item.filename)}
                                            download={item.filename}
                                            className="btn btn-sm btn-teal"
                                            style={{ textDecoration: 'none' }}
                                        >
                                            ⬇ Download
                                        </a>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="alert alert-info">ℹ No materials published by faculty yet.</div>
                    )}
                </div>
            )}
            {currentNav === 'Change Password' && (
                <ChangePassword user={user} />
            )}
        </div>
    );
}
