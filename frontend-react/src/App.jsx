import { useState } from 'react'
import Authentication from './components/Authentication'
import Sidebar from './components/Sidebar'
import TeacherPortal from './pages/TeacherPortal'
import StudentPortal from './pages/StudentPortal'

function App() {
  const [user, setUser] = useState(null)

  // Navigation states based on role
  const TEACHER_NAV = ["Overview", "Take Attendance", "Course Material", "Classroom Administration"]
  const STUDENT_NAV = ["Overview", "AI Curriculum Assistant", "My Attendance & Marks", "Academic Standing", "Course Repository"]

  const [currentNav, setCurrentNav] = useState("Overview")

  if (!user) {
    return <Authentication onLogin={setUser} />
  }

  const navItems = user.role === 'teacher' ? TEACHER_NAV : STUDENT_NAV;

  return (
    <>
      <Sidebar
        user={user}
        onLogout={() => setUser(null)}
        navItems={navItems}
        currentNav={currentNav}
        onNavChange={setCurrentNav}
      />
      <div className="main-content">
        {user.role === 'teacher' ? (
          <TeacherPortal user={user} currentNav={currentNav} />
        ) : (
          <StudentPortal user={user} currentNav={currentNav} />
        )}
      </div>
    </>
  )
}

export default App
