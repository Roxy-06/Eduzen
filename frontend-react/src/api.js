const API_URL = '/api';
const TOKEN_KEY = 'svmit_token';

export function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export function setToken(token) {
    try {
        if (token) localStorage.setItem(TOKEN_KEY, token);
        else localStorage.removeItem(TOKEN_KEY);
    } catch { /* storage unavailable */ }
}

// Called when the server rejects the token (expired or invalid).
let onUnauthorized = null;
export function setUnauthorizedHandler(fn) {
    onUnauthorized = fn;
}

async function authFetch(url, options = {}) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401 && token && onUnauthorized) {
        onUnauthorized();
    }
    return response;
}

const cache = new Map();

async function fetchWithCache(url, ttlSec = 15, options = {}) {
    const cacheKey = JSON.stringify({ url, options });
    const now = Date.now();

    if (cache.has(cacheKey)) {
        const cached = cache.get(cacheKey);
        if (now < cached.expiry) {
            return cached.data;
        }
    }

    const response = await authFetch(url, options);
    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Request failed with status ${response.status}`);
    }

    const data = await response.json();

    cache.set(cacheKey, {
        data,
        expiry: now + (ttlSec * 1000)
    });

    return data;
}

export function clearCache() {
    cache.clear();
}

export const api = {
    fetchClassrooms: () => fetchWithCache(`${API_URL}/classrooms`, 15),
    fetchSubjects: () => fetchWithCache(`${API_URL}/subjects`, 15),
    createSubject: async (name, code) => {
        const res = await authFetch(`${API_URL}/subjects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, code })
        });
        if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Failed to create subject'); }
        return res.json();
    },
    assignSubjectToClassroom: async (classroomId, subjectId, teacherId) => {
        const res = await authFetch(`${API_URL}/classrooms/${classroomId}/assign-subject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject_id: parseInt(subjectId), teacher_id: parseInt(teacherId) })
        });
        if (!res.ok) throw new Error('Failed to assign subject');
        return res.json();
    },
    fetchTeacherClasses: (teacherId) => fetchWithCache(`${API_URL}/teachers/${teacherId}/classes`, 30),
    fetchStudents: (classroomId) => fetchWithCache(`${API_URL}/classrooms/${classroomId}/students`, 15),
    fetchMaterials: (userId = null, classroomId = null) => {
        let url = `${API_URL}/materials`;
        const params = new URLSearchParams();
        if (userId) params.append('user_id', userId);
        if (classroomId) params.append('classroom_id', classroomId);
        if (params.toString()) url += `?${params.toString()}`;
        return fetchWithCache(url, 10);
    },
    fetchTeacherDashboard: (userId) => fetchWithCache(`${API_URL}/dashboard/teacher/${userId}`, 8),
    fetchStudentDashboard: (userId) => fetchWithCache(`${API_URL}/dashboard/student/${userId}`, 8),
    fetchStudentReport: (userId) => fetchWithCache(`${API_URL}/students/user/${userId}/report`, 8),

    login: async (email, password) => {
        const res = await authFetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Login failed');
        }
        return res.json();
    },

    register: async (payload) => {
        const res = await authFetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Registration failed');
        }
        return res.json();
    },

    startSession: async (classroomId, subjectId, _teacherId) => {
        const res = await authFetch(`${API_URL}/classrooms/${classroomId}/subjects/${subjectId}/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        if (!res.ok) throw new Error('Failed to start session');
        return res.json();
    },

    getTodaySession: async (classroomId, subjectId, _teacherId) => {
        const res = await authFetch(`${API_URL}/classrooms/${classroomId}/subjects/${subjectId}/today-session`);
        return res.json(); // May return {} if no session
    },

    endSession: async (sessionId) => {
        const res = await authFetch(`${API_URL}/sessions/${sessionId}/end`, { method: 'POST' });
        if (!res.ok) throw new Error('Failed to end session');
        return res.json();
    },

    markAttendance: async (sessionId, studentId, status) => {
        const res = await authFetch(`${API_URL}/sessions/${sessionId}/attendance/${studentId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        if (!res.ok) throw new Error('Failed to mark attendance');
        return res.json();
    },

    getAttendance: async (sessionId) => {
        const res = await authFetch(`${API_URL}/sessions/${sessionId}/attendance`);
        return res.json(); // Returns dict of studentId: status
    },

    getAttendanceSummary: async (classroomId, subjectId) => {
        const url = subjectId
            ? `${API_URL}/classrooms/${classroomId}/attendance-summary?subject_id=${subjectId}`
            : `${API_URL}/classrooms/${classroomId}/attendance-summary`;
        const res = await authFetch(url);
        return res.json();
    },

    uploadMaterial: async (file, classroomId = null) => {
        const formData = new FormData();
        formData.append('file', file);
        if (classroomId) {
            formData.append('classroom_id', classroomId);
        }
        const res = await authFetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Upload failed');
        }
        return res.json();
    },

    createClassroom: async (name) => {
        const res = await authFetch(`${API_URL}/classrooms`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (!res.ok) throw new Error('Failed to create classroom');
        return res.json();
    },

    enrollStudent: async (classroomId, payload) => {
        const res = await authFetch(`${API_URL}/classrooms/${classroomId}/students`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Failed to enroll student');
        return res.json();
    },

    generateAI: async (mode, query) => {
        const res = await authFetch(`${API_URL}/ai/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode, query })
        });
        if (!res.ok) throw new Error('AI generation failed');
        return res.json();
    },

    adminListUsers: async (_adminId) => {
        const res = await authFetch(`${API_URL}/admin/users`);
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load users'); }
        return res.json();
    },

    adminCreateUser: async (adminId, payload) => {
        const res = await authFetch(`${API_URL}/admin/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to create user'); }
        return res.json();
    },

    adminDeleteUser: async (adminId, userId) => {
        const res = await authFetch(`${API_URL}/admin/users/${userId}`, { method: 'DELETE' });
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to delete user'); }
        return res.json();
    },

    updateStudentClassroom: async (adminId, userId, classroomId) => {
        const res = await authFetch(`${API_URL}/admin/students/${userId}/classroom`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ classroom_id: parseInt(classroomId) })
        });
        if (!res.ok) throw new Error('Failed to update student classroom');
        return res.json();
    },

    changePassword: async (userId, currentPassword, newPassword) => {
        const res = await authFetch(`${API_URL}/auth/change-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
        });
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Password change failed'); }
        return res.json();
    },

    // ── MARKS ───────────────────────────────────────────────
    addMark: async (payload) => {
        const res = await authFetch(`${API_URL}/marks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to save marks'); }
        return res.json();
    },

    fetchClassroomMarks: (classroomId, subjectId) => {
        const url = subjectId
            ? `${API_URL}/classrooms/${classroomId}/marks?subject_id=${subjectId}`
            : `${API_URL}/classrooms/${classroomId}/marks`;
        return fetchWithCache(url, 5);
    },

    // ── STUDENT SEARCH ──────────────────────────────────────
    searchStudentByEnrollment: async (enrollmentNo) => {
        const res = await authFetch(`${API_URL}/students/search?enrollment_no=${encodeURIComponent(enrollmentNo)}`);
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Student not found'); }
        return res.json();
    },

    // ── QUIZZES ─────────────────────────────────────────────
    createQuiz: async (payload) => {
        const res = await authFetch(`${API_URL}/quizzes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to create quiz'); }
        return res.json();
    },

    fetchTeacherQuizzes: (teacherId) => fetchWithCache(`${API_URL}/quizzes/teacher/${teacherId}`, 5),

    fetchStudentQuizzes: (userId) => fetchWithCache(`${API_URL}/quizzes/student/${userId}`, 5),

    submitQuiz: async (quizId, userId, answers) => {
        const res = await authFetch(`${API_URL}/quizzes/${quizId}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers }),
        });
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to submit quiz'); }
        return res.json();
    },

    fetchQuizResults: (quizId) => fetchWithCache(`${API_URL}/quizzes/${quizId}/results`, 5),

    toggleQuiz: async (quizId, teacherId, isActive) => {
        const res = await authFetch(`${API_URL}/quizzes/${quizId}/toggle`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: isActive }),
        });
        if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to toggle quiz'); }
        return res.json();
    },

    // ── FILE DOWNLOAD ────────────────────────────────────────
    // Plain links can't send headers, so the token goes in the query string.
    getDownloadUrl: (filename) =>
        `${API_URL}/uploads/${encodeURIComponent(filename)}?token=${encodeURIComponent(getToken() || '')}`,

    // ── ADMIN ATTENDANCE OVERVIEW ────────────────────────────
    fetchAdminAttendanceOverview: (_adminId) =>
        fetchWithCache(`${API_URL}/admin/attendance-overview`, 10),
};

