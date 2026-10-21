import { useState, useCallback, useEffect, createContext, useContext } from 'react'
import Authentication from './components/Authentication'
import Sidebar from './components/Sidebar'
import TeacherPortal from './pages/TeacherPortal'
import StudentPortal from './pages/StudentPortal'
import AdminPortal from './pages/AdminPortal'
import { getToken, setToken, clearCache, setUnauthorizedHandler } from './api'

// ─── Toast Context ──────────────────────────────────────────
export const ToastContext = createContext(null);

export function useToast() {
  return useContext(ToastContext);
}

function ToastContainer({ toasts }) {
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span>{t.type === 'success' ? '✓' : t.type === 'error' ? '✕' : 'ℹ'}</span>
          {t.message}
        </div>
      ))}
    </div>
  );
}

// ─── Nav config ────────────────────────────────────────────
const TEACHER_NAV = [
  { label: "Dashboard",                 emoji: "🏠" },
  { label: "Take Attendance",           emoji: "✅" },
  { label: "Add Marks",                 emoji: "📝" },
  { label: "Search Student",            emoji: "🔍" },
  { label: "Create Quiz",               emoji: "🎯" },
  { label: "My Quizzes",                emoji: "📋" },
  { label: "Course Material",           emoji: "📄" },
  { label: "Classroom Administration",  emoji: "🏫" },
  { label: "Change Password",           emoji: "🔑" },
];

const STUDENT_NAV = [
  { label: "Dashboard",                 emoji: "🏠" },
  { label: "AI Curriculum Assistant",   emoji: "🤖" },
  { label: "Live Quizzes",              emoji: "🎯" },
  { label: "My Attendance & Marks",     emoji: "📊" },
  { label: "Academic Standing",         emoji: "🎓" },
  { label: "Course Repository",         emoji: "📚" },
  { label: "Change Password",           emoji: "🔑" },
];

const ADMIN_NAV = [
  { label: "Dashboard",            emoji: "🛡" },
  { label: "Create User",          emoji: "➕" },
  { label: "User Management",      emoji: "👥" },
  { label: "Manage Subjects",      emoji: "📖" },
  { label: "Attendance Overview",  emoji: "📊" },
];

export default function App() {
  // Persist login across refreshes
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('svmit_user');
      // A saved user without a token is from before login tokens existed: log in again.
      return stored && getToken() ? JSON.parse(stored) : null;
    } catch { return null; }
  });

  const [currentNav, setCurrentNav] = useState("Dashboard");
  const [toasts, setToasts] = useState([]);

  const handleLogin = useCallback((userData) => {
    setUser(userData);
    localStorage.setItem('svmit_user', JSON.stringify(userData));
    setCurrentNav("Dashboard");
  }, []);

  const handleLogout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('svmit_user');
    setToken(null);
    clearCache();
    setCurrentNav("Dashboard");
  }, []);

  // If the server says the token is expired or invalid, send the user back to login.
  useEffect(() => {
    setUnauthorizedHandler(handleLogout);
    return () => setUnauthorizedHandler(null);
  }, [handleLogout]);

  // Toast system
  const showToast = useCallback((message, type = 'info', duration = 3500) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration);
  }, []);

  if (!user) {
    return (
      <ToastContext.Provider value={showToast}>
        <ToastContainer toasts={toasts} />
        <Authentication onLogin={handleLogin} />
      </ToastContext.Provider>
    );
  }

  const navItems = user.role === 'teacher' ? TEACHER_NAV
               : user.role === 'admin'   ? ADMIN_NAV
               : STUDENT_NAV;

  return (
    <ToastContext.Provider value={showToast}>
      <ToastContainer toasts={toasts} />
      <Sidebar
        user={user}
        onLogout={handleLogout}
        navItems={navItems}
        currentNav={currentNav}
        onNavChange={setCurrentNav}
        role={user.role}
      />
      <div className="main-content">
        {user.role === 'admin' ? (
          <AdminPortal user={user} currentNav={currentNav} />
        ) : user.role === 'teacher' ? (
          <TeacherPortal user={user} currentNav={currentNav} />
        ) : (
          <StudentPortal user={user} currentNav={currentNav} />
        )}
      </div>
    </ToastContext.Provider>
  );
}
