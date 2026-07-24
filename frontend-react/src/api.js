const API_URL = '/api';

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

    const response = await fetch(url, options);
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
    fetchTeacherClasses: (teacherId) => fetchWithCache(`${API_URL}/teachers/${teacherId}/classes`, 30),
    fetchStudents: (classroomId) => fetchWithCache(`${API_URL}/classrooms/${classroomId}/students`, 15),
    fetchMaterials: () => fetchWithCache(`${API_URL}/materials`, 10),
    fetchTeacherDashboard: (userId) => fetchWithCache(`${API_URL}/dashboard/teacher/${userId}`, 8),
    fetchStudentDashboard: (userId) => fetchWithCache(`${API_URL}/dashboard/student/${userId}`, 8),
    fetchStudentReport: (userId) => fetchWithCache(`${API_URL}/students/user/${userId}/report`, 8),

    login: async (email, password) => {
        const res = await fetch(`${API_URL}/auth/login`, {
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
        const res = await fetch(`${API_URL}/auth/register`, {
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

    startSession: async (classroomId, subjectId, teacherId) => {
        const res = await fetch(`${API_URL}/classrooms/${classroomId}/subjects/${subjectId}/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ teacher_id: teacherId })
        });
        if (!res.ok) throw new Error('Failed to start session');
        return res.json();
    },

    getTodaySession: async (classroomId, subjectId, teacherId) => {
        const res = await fetch(`${API_URL}/classrooms/${classroomId}/subjects/${subjectId}/today-session?teacher_id=${teacherId}`);
        return res.json(); // May return {} if no session
    },

    endSession: async (sessionId) => {
        const res = await fetch(`${API_URL}/sessions/${sessionId}/end`, { method: 'POST' });
        if (!res.ok) throw new Error('Failed to end session');
        return res.json();
    },

    markAttendance: async (sessionId, studentId, status) => {
        const res = await fetch(`${API_URL}/sessions/${sessionId}/attendance/${studentId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        if (!res.ok) throw new Error('Failed to mark attendance');
        return res.json();
    },

    getAttendance: async (sessionId) => {
        const res = await fetch(`${API_URL}/sessions/${sessionId}/attendance`);
        return res.json(); // Returns dict of studentId: status
    },

    getAttendanceSummary: async (classroomId, subjectId) => {
        const url = subjectId
            ? `${API_URL}/classrooms/${classroomId}/attendance-summary?subject_id=${subjectId}`
            : `${API_URL}/classrooms/${classroomId}/attendance-summary`;
        const res = await fetch(url);
        return res.json();
    },

    uploadMaterial: async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData // allow browser to infer multipart content-type boundary
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Upload failed');
        }
        return res.json();
    },

    createClassroom: async (name) => {
        const res = await fetch(`${API_URL}/classrooms`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (!res.ok) throw new Error('Failed to create classroom');
        return res.json();
    },

    enrollStudent: async (classroomId, payload) => {
        const res = await fetch(`${API_URL}/classrooms/${classroomId}/students`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Failed to enroll student');
        return res.json();
    },

    generateAI: async (mode, query) => {
        const res = await fetch(`${API_URL}/ai/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode, query })
        });
        if (!res.ok) throw new Error('AI generation failed');
        return res.json(); // { response: "stringified json or text" }
    }
};
